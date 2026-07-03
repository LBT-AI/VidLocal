import re
import json
import logging
from typing import List, Optional, Dict
from uuid import UUID
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_async_session
from app.models.character_glossary import CharacterGlossary

logger = logging.getLogger(__name__)


class GlossaryService:
    def __init__(self):
        self._enabled = settings.GLOSSARY_ENABLED

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def get_glossary(self, project_id: Optional[UUID] = None, user_id: Optional[UUID] = None) -> List[CharacterGlossary]:
        if not self._enabled:
            return []
        async_session = get_async_session()
        async with async_session() as db:
            conditions = []
            if project_id:
                conditions.append(CharacterGlossary.project_id == project_id)
            if user_id:
                conditions.append(CharacterGlossary.user_id == user_id)
            conditions.append(CharacterGlossary.project_id.is_(None))
            query = select(CharacterGlossary).where(or_(*conditions)).order_by(CharacterGlossary.source_name)
            result = await db.execute(query)
            return list(result.scalars().all())

    async def add_entry(
        self,
        source_name: str,
        target_name: str,
        project_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        aliases: Optional[List[str]] = None,
        gender: Optional[str] = None,
        role: Optional[str] = None,
        pronoun_style: Optional[str] = None,
        note: Optional[str] = None,
    ) -> CharacterGlossary:
        async_session = get_async_session()
        async with async_session() as db:
            entry = CharacterGlossary(
                project_id=project_id,
                user_id=user_id,
                source_name=source_name.strip(),
                target_name=target_name.strip(),
                aliases=aliases or [],
                gender=gender,
                role=role,
                pronoun_style=pronoun_style,
                note=note,
            )
            db.add(entry)
            await db.commit()
            await db.refresh(entry)
            logger.info("Glossary added: %s -> %s", source_name, target_name)
            return entry

    async def delete_entry(self, entry_id: UUID) -> bool:
        async_session = get_async_session()
        async with async_session() as db:
            result = await db.execute(select(CharacterGlossary).where(CharacterGlossary.id == entry_id))
            entry = result.scalar_one_or_none()
            if not entry:
                return False
            await db.delete(entry)
            await db.commit()
            logger.info("Glossary deleted: %s (%s -> %s)", entry_id, entry.source_name, entry.target_name)
            return True

    async def list_entries(self, project_id: Optional[UUID] = None, user_id: Optional[UUID] = None) -> List[CharacterGlossary]:
        return await self.get_glossary(project_id, user_id)

    def build_glossary_block(self, entries: List[CharacterGlossary]) -> str:
        if not entries:
            return ""
        lines = ["\n## Character Name Glossary (BẮT BUỘC tuân theo):"]
        for e in entries:
            names = [e.source_name]
            if e.aliases:
                names.extend(e.aliases)
            names_str = ", ".join(names)
            gender_str = f" ({e.gender})" if e.gender else ""
            role_str = f" - {e.role}" if e.role else ""
            pronoun_str = f" - xưng hô: {e.pronoun_style}" if e.pronoun_style else ""
            lines.append(f"- {names_str}{gender_str}{role_str}{pronoun_str} → {e.target_name}")
            if e.note:
                lines.append(f"  Ghi chú: {e.note}")
        lines.append("")
        lines.append("QUAN TRỌNG: Bạn PHẢI dùng target_name ở trên mỗi khi gặp các tên này. KHÔNG được dùng tên gốc.")
        lines.append("Nếu có tên nhân vật mới xuất hiện không có trong danh sách, hãy giữ nguyên tên gốc và báo lại.")
        return "\n".join(lines)

    def build_prompt_with_glossary(self, base_prompt: str, entries: List[CharacterGlossary]) -> str:
        glossary_block = self.build_glossary_block(entries)
        if not glossary_block:
            return base_prompt
        return glossary_block + "\n\n" + base_prompt

    def apply_glossary_to_text(self, text: str, entries: List[CharacterGlossary]) -> str:
        if not entries or not text:
            return text
        result = text
        for e in sorted(entries, key=lambda x: len(x.source_name), reverse=True):
            pattern = re.compile(re.escape(e.source_name), re.IGNORECASE)
            result = pattern.sub(e.target_name, result)
            if e.aliases:
                for alias in e.aliases:
                    alias_pattern = re.compile(re.escape(str(alias)), re.IGNORECASE)
                    result = alias_pattern.sub(e.target_name, result)
        return result

    def detect_unknown_names(self, text: str, entries: List[CharacterGlossary]) -> List[str]:
        if not text:
            return []
        known_names = {e.source_name.lower() for e in entries}
        if entries:
            for e in entries:
                if e.aliases:
                    known_names.update(str(a).lower() for a in e.aliases)
        name_pattern = re.compile(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b')
        candidates = set(name_pattern.findall(text))
        special_terms = {"Master", "Brother", "Sister", "Uncle", "Aunt", "Teacher", "Doctor", "Lord", "Lady", "King", "Queen", "Prince", "Princess", "General", "Captain"}
        for term in special_terms:
            if re.search(rf'\b{term}\b', text, re.IGNORECASE):
                candidates.add(term)
        unknown = []
        for name in candidates:
            name_lower = name.lower()
            if name_lower not in known_names:
                if len(name) >= 2:
                    unknown.append(name)
        return sorted(set(unknown))


glossary_service = GlossaryService()
