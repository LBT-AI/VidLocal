from celery import shared_task
from sqlalchemy import select

from app.config import settings
from app.models.publish_job import PublishJob
from app.models.platform_connection import PlatformConnection
from app.services.youtube_service import youtube_service
from app.database import get_async_session


@shared_task(bind=True, name="workers.publish_worker.publish")
def publish(self, job_id: str):
    import asyncio
    asyncio.run(_publish_async(self, job_id))


async def _publish_async(task, job_id: str):
    async_session = get_async_session()
    async with async_session() as db:
        result = await db.execute(select(PublishJob).where(PublishJob.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            raise ValueError(f"Publish job {job_id} not found")
        task.update_state(state="STARTED", meta={"progress": 30})
        conn_result = await db.execute(
            select(PlatformConnection).where(
                PlatformConnection.user_id == job.project_id,
                PlatformConnection.platform == job.platform
            )
        )
        conn = conn_result.scalar_one_or_none()
        if not conn or not conn.access_token:
            job.status = "failed"
            job.error_message = "Platform not connected"
            await db.commit()
            raise ValueError("Platform not connected")
        try:
            if job.platform == "youtube":
                from app.models.project import Project
                proj_result = await db.execute(select(Project).where(Project.id == job.project_id))
                project = proj_result.scalar_one()
                url = youtube_service.upload_video(
                    conn.access_token,
                    project.final_video_path,
                    job.title,
                    job.description,
                    job.tags or [],
                    job.privacy,
                    refresh_token=conn.refresh_token,
                    expires_at=conn.expires_at.isoformat() if conn.expires_at else None,
                )
                job.published_url = url
                job.status = "published"
            else:
                job.status = "failed"
                job.error_message = "Platform not yet implemented"
        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
        await db.commit()
        task.update_state(state="SUCCESS", meta={"progress": 100})
        return {"status": job.status, "url": job.published_url}
