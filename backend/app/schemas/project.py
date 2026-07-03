from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID


class ProjectCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    source_url: Optional[str] = None


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None


class ProjectOut(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    source_url: Optional[str]
    status: str
    original_video_path: Optional[str]
    audio_path: Optional[str]
    zh_srt_path: Optional[str]
    vi_srt_path: Optional[str]
    final_video_path: Optional[str]
    metadata_json: Optional[Dict[str, Any]] = Field(alias="metadata")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True


class ProjectListOut(BaseModel):
    id: UUID
    title: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
