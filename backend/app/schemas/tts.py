from typing import Optional
from pydantic import BaseModel


class TTSRequest(BaseModel):
    voice: str = "vi-VN-HoaiMyNeural"
    cue_indices: Optional[list[int]] = None


class TTSSegmentOut(BaseModel):
    id: int
    project_id: str
    cue_index: int
    audio_path: Optional[str]
    duration_ms: Optional[int]
    sync_status: str

    class Config:
        from_attributes = True
