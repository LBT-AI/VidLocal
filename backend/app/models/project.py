import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    title = Column(Text, nullable=False)
    source_url = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="pending", index=True)
    original_video_path = Column(Text, nullable=True)
    audio_path = Column(Text, nullable=True)
    zh_srt_path = Column(Text, nullable=True)
    vi_srt_path = Column(Text, nullable=True)
    final_video_path = Column(Text, nullable=True)
    metadata_json = Column("metadata", JSON, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Project(id={self.id}, title={self.title}, status={self.status})>"
