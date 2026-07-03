"""
Cleanup script for local temp files and R2 objects.

Usage:
  python -m backend.app.scripts.cleanup_storage

Dry-run mode:
  python -m backend.app.scripts.cleanup_storage --dry-run
"""
import os
import sys
import asyncio
import logging
import argparse
from datetime import datetime, timezone, timedelta

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("cleanup_storage")

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.config import settings
from app.database import get_async_session
from app.models.video_job import VideoJob
from app.services.r2_storage_service import r2_storage

from sqlalchemy import select, and_


STORAGE_PREFIXES = ["facebook_downloads", "tiktok_downloads"]


async def _clean_job_dir(job_dir: str, job, dry_run: bool, total_deleted: int, total_bytes: int) -> tuple:
    if not os.path.exists(job_dir):
        return total_deleted, total_bytes
    job_age = datetime.now(timezone.utc) - (job.updated_at or job.created_at)
    if job_age < timedelta(hours=24):
        return total_deleted, total_bytes

    dir_size = sum(
        os.path.getsize(os.path.join(dirpath, f))
        for dirpath, _, filenames in os.walk(job_dir)
        for f in filenames
    )

    if dry_run:
        logger.info("[DRY-RUN] Would delete: %s (%d bytes, age=%s)", job_dir, dir_size, job_age)
        return total_deleted + 1, total_bytes + dir_size

    try:
        import shutil
        shutil.rmtree(job_dir)
        logger.info("Deleted: %s (%d bytes, age=%s)", job_dir, dir_size, job_age)
        return total_deleted + 1, total_bytes + dir_size
    except OSError as e:
        logger.warning("Failed to delete %s: %s", job_dir, e)
        return total_deleted, total_bytes


async def clean_local_temp(dry_run: bool = False) -> dict:
    total_deleted = 0
    total_bytes = 0

    async_session = get_async_session()
    async with async_session() as db:
        result = await db.execute(
            select(VideoJob).where(
                and_(
                    VideoJob.status.in_(["completed", "cancelled", "upload_failed", "failed"]),
                )
            )
        )
        jobs = result.scalars().all()

    # Clean by temp_dir from DB
    for job in jobs:
        if job.temp_dir:
            total_deleted, total_bytes = await _clean_job_dir(job.temp_dir, job, dry_run, total_deleted, total_bytes)
            continue
        for prefix in STORAGE_PREFIXES:
            job_dir = os.path.join(settings.PROJECT_DATA_DIR, prefix, str(job.id))
            total_deleted, total_bytes = await _clean_job_dir(job_dir, job, dry_run, total_deleted, total_bytes)

    # Clean orphan dirs from all storage prefixes
    existing_ids = {str(job.id) for job in jobs}
    for prefix in STORAGE_PREFIXES:
        local_base = os.path.join(settings.PROJECT_DATA_DIR, prefix)
        if not os.path.exists(local_base):
            continue
        for entry in os.listdir(local_base):
            entry_path = os.path.join(local_base, entry)
            if not os.path.isdir(entry_path):
                continue
            if entry in existing_ids:
                continue
            dir_size = sum(
                os.path.getsize(os.path.join(dirpath, f))
                for dirpath, _, filenames in os.walk(entry_path)
                for f in filenames
            )
            if dry_run:
                logger.info("[DRY-RUN] Would delete orphan: %s (%d bytes)", entry_path, dir_size)
                total_deleted += 1
                total_bytes += dir_size
            else:
                try:
                    import shutil
                    shutil.rmtree(entry_path)
                    logger.info("Deleted orphan: %s (%d bytes)", entry_path, dir_size)
                    total_deleted += 1
                    total_bytes += dir_size
                except OSError as e:
                    logger.warning("Failed to delete orphan %s: %s", entry_path, e)

    return {"deleted": total_deleted, "bytes": total_bytes}


async def clean_r2_objects(dry_run: bool = False) -> dict:
    if not r2_storage.enabled:
        logger.info("R2 is not enabled, skipping R2 cleanup")
        return {"deleted": 0, "bytes": 0}

    retention_days = settings.R2_RETENTION_DAYS
    old_objects = r2_storage.list_old_objects(retention_days)
    if not old_objects:
        logger.info("No old R2 objects found (retention=%d days)", retention_days)
        return {"deleted": 0, "bytes": 0}

    total_bytes = sum(obj.get("size", 0) for obj in old_objects)
    logger.info("Found %d old R2 objects (%d bytes, older than %d days)", len(old_objects), total_bytes, retention_days)

    if dry_run:
        for obj in old_objects:
            logger.info("[DRY-RUN] Would delete R2: %s (%d bytes, modified=%s)", obj["key"], obj["size"], obj["last_modified"])
        return {"deleted": len(old_objects), "bytes": total_bytes}
    else:
        result = r2_storage.delete_objects(old_objects)
        return result


async def clean_failed_jobs(dry_run: bool = False) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    async_session = get_async_session()
    deleted_count = 0
    async with async_session() as db:
        result = await db.execute(
            select(VideoJob).where(
                and_(
                    VideoJob.type == "facebook_to_youtube",
                    VideoJob.status.in_(["failed", "upload_failed"]),
                    VideoJob.updated_at < cutoff,
                )
            )
        )
        old_failed = result.scalars().all()
        for job in old_failed:
            if dry_run:
                logger.info("[DRY-RUN] Would delete failed job record: %s (status=%s, updated=%s)", job.id, job.status, job.updated_at)
                deleted_count += 1
            else:
                await db.delete(job)
                deleted_count += 1
        if not dry_run and old_failed:
            await db.commit()
    if deleted_count:
        logger.info("Cleaned %d old failed job records", deleted_count)
    return deleted_count


async def run_cleanup(dry_run: bool = False):
    logger.info("=== Storage Cleanup %s ===", "DRY-RUN" if dry_run else "START")
    for prefix in STORAGE_PREFIXES:
        logger.info("Local temp dir: %s", os.path.join(settings.PROJECT_DATA_DIR, prefix))
    logger.info("R2 enabled: %s", r2_storage.enabled)

    local_result = await clean_local_temp(dry_run)
    logger.info("Local cleanup: %d items, %d bytes", local_result["deleted"], local_result["bytes"])

    r2_result = await clean_r2_objects(dry_run)
    logger.info("R2 cleanup: %d items, %d bytes", r2_result.get("deleted", 0), r2_result.get("bytes", 0))

    failed_count = await clean_failed_jobs(dry_run)
    logger.info("Failed jobs cleaned: %d", failed_count)

    logger.info("=== Storage Cleanup %s ===", "DRY-RUN" if dry_run else "DONE")


def main():
    parser = argparse.ArgumentParser(description="Clean up local temp files and R2 objects")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without deleting")
    args = parser.parse_args()
    asyncio.run(run_cleanup(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
