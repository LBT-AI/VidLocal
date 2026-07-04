import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class VideoJob(Base):
    __tablename__ = "video_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(String(50), nullable=False, default="facebook_to_youtube", index=True)
    source_url = Column(Text, nullable=False)
    video_id = Column(Text, nullable=True)
    resolved_url = Column(Text, nullable=True)
    normalized_url = Column(Text, nullable=True)
    source_platform = Column(String(50), nullable=False, default="facebook")
    target_platform = Column(String(50), nullable=False, default="youtube")
    status = Column(String(50), nullable=False, default="pending", index=True)
    progress = Column(Integer, nullable=False, default=0)
    current_step = Column(String(50), nullable=True, default="download")
    review_state = Column(String(50), nullable=False, default="none")
    stage_progress = Column(Integer, nullable=False, default=0)
    input_file = Column(Text, nullable=True)
    output_file = Column(Text, nullable=True)
    youtube_video_id = Column(Text, nullable=True)
    youtube_url = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    error_code = Column(String(100), nullable=True)
    admin_chat_id = Column(String(50), nullable=True)
    telegram_message_id = Column(Integer, nullable=True)

    transcript = Column(Text, nullable=True)
    transcript_language = Column(String(10), nullable=True)
    ai_title = Column(Text, nullable=True)
    ai_description = Column(Text, nullable=True)
    ai_tags = Column(Text, nullable=True)
    ai_hashtags = Column(Text, nullable=True)
    ai_summary = Column(Text, nullable=True)
    ai_hook = Column(Text, nullable=True)
    ai_category = Column(Text, nullable=True)
    risk_flags = Column(Text, nullable=True)
    metadata_status = Column(String(20), nullable=False, default="pending")
    glossary_status = Column(String(20), nullable=True, default=None)
    glossary_draft_id = Column(UUID(as_uuid=True), nullable=True)

    transcript_srt_path = Column(Text, nullable=True)
    transcript_text_path = Column(Text, nullable=True)
    transcript_review_status = Column(String(20), nullable=True, default=None)  # pending, approved, skipped
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    thumbnail_prompts = Column(Text, nullable=True)
    thumbnail_path = Column(Text, nullable=True)
    thumbnail_status = Column(String(20), nullable=False, default="pending")
    thumbnail_reference_frames = Column(Text, nullable=True)
    selected_thumbnail_reference = Column(Integer, nullable=True)
    thumbnail_prompt = Column(Text, nullable=True)

    r2_key = Column(Text, nullable=True)
    r2_uploaded_at = Column(DateTime(timezone=True), nullable=True)
    r2_expires_at = Column(DateTime(timezone=True), nullable=True)

    temp_dir = Column(Text, nullable=True)
    file_path = Column(Text, nullable=True)
    source_file_path = Column(Text, nullable=True)
    watermarked_file_path = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<VideoJob(id={self.id}, type={self.type}, status={self.status})>"
