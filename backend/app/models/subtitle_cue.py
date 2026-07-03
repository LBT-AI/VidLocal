from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class SubtitleCue(Base):
    __tablename__ = "subtitle_cues"
    __table_args__ = (UniqueConstraint("project_id", "cue_index", name="uq_project_cue"),)

    id = Column(Integer, primary_key=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    cue_index = Column(Integer, nullable=False)
    start_ms = Column(Integer, nullable=False)
    end_ms = Column(Integer, nullable=False)
    zh_text = Column(Text, nullable=True)
    vi_text = Column(Text, nullable=True)
    cps = Column(Float, nullable=True)
    status = Column(String(50), nullable=False, default="ok")

    def __repr__(self):
        return f"<SubtitleCue(project={self.project_id}, idx={self.cue_index}, status={self.status})>"
