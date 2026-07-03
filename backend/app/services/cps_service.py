from typing import Dict, List
from app.services.srt_service import SRTCue


class CPSService:
    MAX_CPS = 22.0
    WARNING_CPS = 28.0
    CRITICAL_CPS = 35.0

    @staticmethod
    def check_cps(text: str, start_ms: int, end_ms: int) -> Dict:
        duration_sec = (end_ms - start_ms) / 1000
        char_count = len(text.replace("\n", "").replace(" ", ""))
        cps = char_count / duration_sec if duration_sec > 0 else 999.0
        status = "ok"
        if cps > CPSService.CRITICAL_CPS:
            status = "needs_review"
        elif cps > CPSService.WARNING_CPS:
            status = "cps_warning"
        elif cps > CPSService.MAX_CPS:
            status = "cps_warning"
        return {
            "cps": round(cps, 2),
            "char_count": char_count,
            "duration_sec": round(duration_sec, 2),
            "status": status
        }

    @staticmethod
    def split_lines(text: str, max_chars_per_line: int = 40) -> str:
        words = text.split()
        if len(text) <= max_chars_per_line:
            return text
        mid = len(text) // 2
        spaces = [i for i, c in enumerate(text) if c == ' ']
        if not spaces:
            return text
        best_split = min(spaces, key=lambda x: abs(x - mid))
        line1 = text[:best_split].strip()
        line2 = text[best_split:].strip()
        return f"{line1}\n{line2}"

    @staticmethod
    def auto_fix(cue: SRTCue) -> SRTCue:
        result = CPSService.check_cps(cue.text, cue.start_ms, cue.end_ms)
        cps = result["cps"]
        text = cue.text
        if cps <= CPSService.MAX_CPS:
            return cue
        if CPSService.MAX_CPS < cps <= CPSService.WARNING_CPS:
            text = CPSService.split_lines(text)
            new_result = CPSService.check_cps(text, cue.start_ms, cue.end_ms)
            if new_result["cps"] <= CPSService.WARNING_CPS:
                return SRTCue(index=cue.index, start_ms=cue.start_ms, end_ms=cue.end_ms, text=text)
        return SRTCue(index=cue.index, start_ms=cue.start_ms, end_ms=cue.end_ms, text=text)

    @staticmethod
    def batch_check(cues: List[SRTCue]) -> List[Dict]:
        return [CPSService.check_cps(c.text, c.start_ms, c.end_ms) for c in cues]


cps_service = CPSService()
