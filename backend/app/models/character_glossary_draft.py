import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class CharacterGlossaryDraft(Base):
    __tablename__ = "character_glossary_drafts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    raw_json = Column(JSON, nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<CharacterGlossaryDraft(id={self.id}, job_id={self.job_id}, status={self.status})>"


class CharacterGlossaryItem(Base):
    __tablename__ = "character_glossary_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    draft_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    category = Column(String(20), nullable=False, default="character")
    source_name = Column(Text, nullable=False)
    target_name = Column(Text, nullable=False)
    aliases = Column(JSON, nullable=True, default=list)
    role = Column(Text, nullable=True)
    family_clan = Column(Text, nullable=True)
    gender = Column(String(20), nullable=True)
    relationships = Column(JSON, nullable=True, default=list)
    pronoun_style = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    approved = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<CharacterGlossaryItem(id={self.id}, source={self.source_name} -> {self.target_name})>"
