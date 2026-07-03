from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class TTSSegment(Base):
    __tablename__ = "tts_segments"

    id = Column(Integer, primary_key=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    cue_index = Column(Integer, nullable=False)
    audio_path = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    sync_status = Column(String(50), nullable=False, default="pending")

    def __repr__(self):
        return f"<TTSSegment(project={self.project_id}, idx={self.cue_index}, sync={self.sync_status})>"
