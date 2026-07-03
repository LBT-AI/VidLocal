import asyncio
import logging
from celery import shared_task

from app.flows.tiktok_to_youtube_flow import TikTokToYouTubeFlow

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="workers.tiktok_to_youtube_worker.process")
def process(self, job_id: str):
    flow = TikTokToYouTubeFlow(task=self)
    asyncio.run(flow.run_process(job_id))


@shared_task(bind=True, name="workers.tiktok_to_youtube_worker.upload_approved")
def upload_approved(self, job_id: str):
    flow = TikTokToYouTubeFlow(task=self)
    asyncio.run(flow.run_upload(job_id))


@shared_task(bind=True, name="workers.tiktok_to_youtube_worker.process_after_glossary")
def process_after_glossary(self, job_id: str):
    flow = TikTokToYouTubeFlow(task=self)
    asyncio.run(flow.run_process_after_glossary(job_id))
