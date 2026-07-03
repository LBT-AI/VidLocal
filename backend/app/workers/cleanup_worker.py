import asyncio
import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="workers.cleanup_worker.cleanup_storage")
def cleanup_storage(self):
    from app.scripts.cleanup_storage import run_cleanup
    logger.info("Periodic cleanup worker started")
    asyncio.run(run_cleanup(dry_run=False))
    logger.info("Periodic cleanup worker finished")
