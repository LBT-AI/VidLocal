import asyncio
import json
import logging
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from celery.result import AsyncResult
from app.workers.celery_app import celery_app
from app.schemas.common import APIResponse, JobStatusResponse

logger = logging.getLogger(__name__)
router = APIRouter()

sse_clients: list = []


@router.get("/stream")
async def job_stream():
    queue: asyncio.Queue = asyncio.Queue()
    sse_clients.append(queue)

    async def event_generator():
        try:
            while True:
                data = await queue.get()
                yield f"data: {json.dumps(data)}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            sse_clients.remove(queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/{job_id}", response_model=APIResponse[JobStatusResponse])
async def get_job_status(job_id: str):
    task = AsyncResult(job_id, app=celery_app)
    progress = None
    if task.info and isinstance(task.info, dict):
        progress = task.info.get("progress")
    return APIResponse(data=JobStatusResponse(
        job_id=job_id,
        status=task.status,
        progress=progress,
        error=str(task.result) if task.failed() else None
    ))
