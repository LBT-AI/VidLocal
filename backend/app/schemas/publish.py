from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from uuid import UUID


class PublishRequest(BaseModel):
    platform: str
    title: str
    description: str = ""
    tags: List[str] = []
    privacy: str = "private"
    scheduled_at: Optional[datetime] = None


class PublishJobOut(BaseModel):
    id: UUID
    project_id: UUID
    platform: str
    title: Optional[str]
    status: str
    privacy: str
    published_url: Optional[str]
    error_message: Optional[str]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True
