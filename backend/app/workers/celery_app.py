from celery import Celery
from celery.schedules import crontab
from app.config import settings

celery_app = Celery(
    "vidlocal",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.workers.transcribe_worker",
        "app.workers.translate_worker",
        "app.workers.tts_worker",
        "app.workers.render_worker",
        "app.workers.publish_worker",
        "app.workers.facebook_to_youtube_worker",
        "app.workers.tiktok_to_youtube_worker",
        "app.workers.cleanup_worker",
    ]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=7200,
    worker_prefetch_multiplier=1,
    result_expires=3600 * 24 * 7,
    beat_schedule={
        "cleanup-storage-every-6h": {
            "task": "workers.cleanup_worker.cleanup_storage",
            "schedule": crontab(hour="*/6", minute="0"),
        },
    },
)
