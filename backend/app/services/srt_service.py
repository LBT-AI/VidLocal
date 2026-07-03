import re
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class SRTCue:
    index: int
    start_ms: int
    end_ms: int
    text: str


class SRTService:
    @staticmethod
    def ms_to_srt_time(ms: int) -> str:
        hours = ms // 3600000
        minutes = (ms % 3600000) // 60000
        seconds = (ms % 60000) // 1000
        millis = ms % 1000
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"

    @staticmethod
    def srt_time_to_ms(time_str: str) -> int:
        time_str = time_str.replace(".", ",")
        match = re.match(r"(\d+):(\d+):(\d+),(\d+)", time_str.strip())
        if not match:
            return 0
        h, m, s, ms = map(int, match.groups())
        return h * 3600000 + m * 60000 + s * 1000 + ms

    @staticmethod
    def parse(srt_content: str) -> List[SRTCue]:
        cues = []
        blocks = re.split(r'\n\s*\n', srt_content.strip())
        for block in blocks:
            lines = [l.strip() for l in block.strip().split('\n') if l.strip()]
            if len(lines) < 3:
                continue
            try:
                index = int(lines[0])
                time_line = lines[1]
                parts = time_line.split('-->')
                start_str = parts[0].strip().split()[0] if ' ' in parts[0].strip() else parts[0].strip()
                end_str = parts[1].strip().split()[0] if ' ' in parts[1].strip() else parts[1].strip()
                text = '\n'.join(lines[2:])
                cues.append(SRTCue(
                    index=index,
                    start_ms=SRTService.srt_time_to_ms(start_str),
                    end_ms=SRTService.srt_time_to_ms(end_str),
                    text=text
                ))
            except (ValueError, IndexError):
                continue
        return cues

    @staticmethod
    def generate(cues: List[SRTCue]) -> str:
        lines = []
        for cue in cues:
            lines.append(str(cue.index))
            lines.append(f"{SRTService.ms_to_srt_time(cue.start_ms)} --> {SRTService.ms_to_srt_time(cue.end_ms)}")
            lines.append(cue.text)
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def generate_bilingual(original_cues: List[SRTCue], translated_cues: List[SRTCue]) -> str:
        translated_by_index = {cue.index: cue for cue in translated_cues}
        lines = []
        for cue in original_cues:
            translated = translated_by_index.get(cue.index)
            lines.append(str(cue.index))
            lines.append(f"{SRTService.ms_to_srt_time(cue.start_ms)} --> {SRTService.ms_to_srt_time(cue.end_ms)}")
            if cue.text:
                lines.append(cue.text)
            if translated and translated.text:
                lines.append(translated.text)
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def cues_to_json(cues: List[SRTCue]) -> List[Dict[str, Any]]:
        return [
            {"cue_index": c.index, "start_ms": c.start_ms, "end_ms": c.end_ms, "text": c.text}
            for c in cues
        ]

    @staticmethod
    def json_to_cues(data: List[Dict[str, Any]]) -> List[SRTCue]:
        return [
            SRTCue(
                index=d["cue_index"],
                start_ms=d["start_ms"],
                end_ms=d["end_ms"],
                text=d.get("text") or d.get("vi_text") or d.get("zh_text", "")
            )
            for d in data
        ]


srt_service = SRTService()
