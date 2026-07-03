from typing import Optional
from pydantic import BaseModel, Field


class SubtitleCueCreate(BaseModel):
    cue_index: int = Field(..., ge=0)
    start_ms: int = Field(..., ge=0)
    end_ms: int = Field(..., ge=0)
    zh_text: Optional[str] = None
    vi_text: Optional[str] = None


class SubtitleCueUpdate(BaseModel):
    start_ms: Optional[int] = None
    end_ms: Optional[int] = None
    zh_text: Optional[str] = None
    vi_text: Optional[str] = None
    status: Optional[str] = None


class SubtitleCueOut(BaseModel):
    id: int
    project_id: str
    cue_index: int
    start_ms: int
    end_ms: int
    zh_text: Optional[str]
    vi_text: Optional[str]
    cps: Optional[float]
    status: str

    class Config:
        from_attributes = True


class TranslateRequest(BaseModel):
    provider: Optional[str] = None
    auto_fix_cps: bool = True
    subtitle_output_mode: Optional[str] = None


class FixCPSRequest(BaseModel):
    cue_indices: Optional[list[int]] = None
