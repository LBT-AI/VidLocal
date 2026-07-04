import asyncio
import logging
from celery import shared_task

from app.database import dispose_engine
from app.flows.facebook_to_youtube_flow import FacebookToYouTubeFlow

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="workers.facebook_to_youtube_worker.process")
def process(self, job_id: str):
    dispose_engine()
    flow = FacebookToYouTubeFlow(task=self)
    try:
        asyncio.run(flow.run_process(job_id))
    finally:
        dispose_engine()


@shared_task(bind=True, name="workers.facebook_to_youtube_worker.upload_approved")
def upload_approved(self, job_id: str):
    dispose_engine()
    flow = FacebookToYouTubeFlow(task=self)
    try:
        asyncio.run(flow.run_upload(job_id))
    finally:
        dispose_engine()


@shared_task(bind=True, name="workers.facebook_to_youtube_worker.process_after_glossary")
def process_after_glossary(self, job_id: str):
    dispose_engine()
    flow = FacebookToYouTubeFlow(task=self)
    try:
        asyncio.run(flow.run_process_after_glossary(job_id))
    finally:
        dispose_engine()


@shared_task(bind=True, name="workers.facebook_to_youtube_worker.process_after_srt")
def process_after_srt(self, job_id: str):
    dispose_engine()
    flow = FacebookToYouTubeFlow(task=self)
    try:
        asyncio.run(flow.run_process_after_srt(job_id))
    finally:
        dispose_engine()


@shared_task(bind=True, name="workers.facebook_to_youtube_worker.retry_transcribe")
def retry_transcribe(self, job_id: str):
    dispose_engine()
    flow = FacebookToYouTubeFlow(task=self)
    try:
        asyncio.run(flow.run_transcribe_only(job_id))
    finally:
        dispose_engine()
