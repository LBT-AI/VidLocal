import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, get_current_user_optional
from app.models.character_glossary import CharacterGlossary
from app.schemas.common import APIResponse
from pydantic import BaseModel

router = APIRouter()


class GlossaryEntryCreate(BaseModel):
    source_name: str
    target_name: str
    project_id: Optional[uuid.UUID] = None
    aliases: Optional[List[str]] = None
    gender: Optional[str] = None
    role: Optional[str] = None
    pronoun_style: Optional[str] = None
    note: Optional[str] = None


class GlossaryEntryOut(BaseModel):
    id: uuid.UUID
    project_id: Optional[uuid.UUID]
    user_id: Optional[uuid.UUID]
    source_name: str
    target_name: str
    aliases: Optional[List[str]]
    gender: Optional[str]
    role: Optional[str]
    pronoun_style: Optional[str]
    note: Optional[str]

    class Config:
        from_attributes = True


@router.get("", response_model=APIResponse[List[GlossaryEntryOut]])
async def list_glossary(
    project_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Depends(get_current_user_optional),
):
    if not user_id:
        return APIResponse(data=[])
    uid = uuid.UUID(user_id)
    conditions = [or_(CharacterGlossary.user_id == uid, CharacterGlossary.user_id.is_(None))]
    if project_id:
        conditions.append(or_(CharacterGlossary.project_id == project_id, CharacterGlossary.project_id.is_(None)))
    result = await db.execute(
        select(CharacterGlossary).where(*conditions).order_by(CharacterGlossary.source_name)
    )
    entries = result.scalars().all()
    return APIResponse(data=[GlossaryEntryOut.model_validate(e) for e in entries])


@router.post("", response_model=APIResponse[GlossaryEntryOut])
async def create_glossary_entry(
    data: GlossaryEntryCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Depends(get_current_user_optional),
):
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    entry = CharacterGlossary(
        project_id=data.project_id,
        user_id=uuid.UUID(user_id),
        source_name=data.source_name.strip(),
        target_name=data.target_name.strip(),
        aliases=data.aliases or [],
        gender=data.gender,
        role=data.role,
        pronoun_style=data.pronoun_style,
        note=data.note,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return APIResponse(data=GlossaryEntryOut.model_validate(entry))


@router.delete("/{entry_id}", response_model=APIResponse[dict])
async def delete_glossary_entry(
    entry_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Depends(get_current_user_optional),
):
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    uid = uuid.UUID(user_id)
    result = await db.execute(
        select(CharacterGlossary).where(
            CharacterGlossary.id == entry_id,
            or_(CharacterGlossary.user_id == uid, CharacterGlossary.user_id.is_(None)),
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    await db.delete(entry)
    await db.commit()
    return APIResponse(data={"deleted": True})
