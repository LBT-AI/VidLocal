import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class CharacterGlossary(Base):
    __tablename__ = "character_glossary"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    source_name = Column(Text, nullable=False)
    target_name = Column(Text, nullable=False)
    aliases = Column(JSON, nullable=True, default=list)
    gender = Column(String(20), nullable=True)
    role = Column(String(100), nullable=True)
    pronoun_style = Column(String(100), nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<CharacterGlossary(id={self.id}, source={self.source_name} -> {self.target_name})>"
