import os
import shutil
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from app.config import settings
from app.models.video_job import VideoJob
from app.services.r2_storage_service import r2_storage

logger = logging.getLogger(__name__)


class StorageCleanupService:
    @staticmethod
    def get_job_dir(job: VideoJob) -> str:
        return job.temp_dir or os.path.join(
            settings.PROJECT_DATA_DIR, "facebook_downloads", str(job.id)
        )

    @staticmethod
    async def cleanup_job_files(job: VideoJob):
        if job.r2_key:
            from app.services.r2_storage_service import r2_storage
            try:
                result = r2_storage.delete_job_files(str(job.id))
                if result.get("deleted", 0):
                    logger.info(
                        "R2 cleanup for job %s: %d objects, %d bytes",
                        job.id, result["deleted"], result.get("bytes", 0),
                    )
            except Exception as e:
                logger.warning("R2 cleanup failed for job %s: %s", job.id, e)

        job_dir = StorageCleanupService.get_job_dir(job)
        if os.path.exists(job_dir):
            try:
                total_size = sum(
                    os.path.getsize(os.path.join(dirpath, f))
                    for dirpath, _, filenames in os.walk(job_dir)
                    for f in filenames
                )
                shutil.rmtree(job_dir)
                logger.info("Local cleanup for job %s: %d bytes removed", job.id, total_size)
            except OSError as e:
                logger.warning("Local cleanup failed for job %s: %s", job.id, e)

    @staticmethod
    async def backup_to_r2(job: VideoJob, source_path: str):
        if not r2_storage.enabled:
            return
        if not os.path.exists(source_path):
            logger.warning("R2 backup skipped: source file not found at %s", source_path)
            return
        try:
            r2_key = r2_storage.upload_file(source_path, str(job.id), "source.mp4")
            job_dir = StorageCleanupService.get_job_dir(job)
            normalized_path = os.path.join(job_dir, "normalized.mp4")
            if os.path.exists(normalized_path):
                r2_storage.upload_file(normalized_path, str(job.id), "normalized.mp4")
            job.r2_key = r2_key
            job.r2_uploaded_at = datetime.now(timezone.utc)
            job.r2_expires_at = datetime.now(timezone.utc) + timedelta(days=settings.R2_RETENTION_DAYS)
            logger.info("R2 backup complete for job %s, key=%s", job.id, r2_key)
        except Exception as e:
            logger.warning("R2 backup failed for job %s: %s", job.id, e)


storage_cleanup = StorageCleanupService()
