import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.platform_connection import PlatformConnection
from app.schemas.common import APIResponse
from app.services.youtube_service import youtube_service

router = APIRouter()


@router.get("/{platform}/auth")
async def start_oauth(
    platform: str,
    request: Request,
    user_id: str = Depends(get_current_user)
):
    if platform == "youtube":
        url = youtube_service.get_auth_url(state=user_id)
        return APIResponse(data={"auth_url": url})
    raise HTTPException(status_code=400, detail="Platform not supported")


@router.get("/{platform}/callback")
async def oauth_callback(
    platform: str,
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db)
):
    user_id = state
    if platform == "youtube":
        tokens = youtube_service.exchange_code(code)
        existing = await db.execute(
            select(PlatformConnection).where(
                PlatformConnection.user_id == uuid.UUID(user_id),
                PlatformConnection.platform == "youtube"
            )
        )
        conn = existing.scalar_one_or_none()
        if conn:
            conn.access_token = tokens["access_token"]
            conn.refresh_token = tokens.get("refresh_token")
        else:
            conn = PlatformConnection(
                user_id=uuid.UUID(user_id),
                platform="youtube",
                access_token=tokens["access_token"],
                refresh_token=tokens.get("refresh_token")
            )
            db.add(conn)
        await db.commit()
        return APIResponse(data={"connected": True, "platform": "youtube"})
    raise HTTPException(status_code=400, detail="Platform not supported")


@router.get("")
async def list_connections(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    result = await db.execute(
        select(PlatformConnection).where(PlatformConnection.user_id == uuid.UUID(user_id))
    )
    conns = result.scalars().all()
    return APIResponse(data=[
        {
            "platform": c.platform,
            "channel_name": c.channel_name,
            "connected": bool(c.access_token)
        }
        for c in conns
    ])


@router.delete("/{platform}")
async def disconnect(
    platform: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    result = await db.execute(
        select(PlatformConnection).where(
            PlatformConnection.user_id == uuid.UUID(user_id),
            PlatformConnection.platform == platform
        )
    )
    conn = result.scalar_one_or_none()
    if conn:
        await db.delete(conn)
        await db.commit()
    return APIResponse(data={"disconnected": True})
