from __future__ import annotations

"""Audio utilities built on top of pydub."""

from io import BytesIO
from pathlib import Path
import base64

from pydub import AudioSegment


DEFAULT_SAMPLE_RATE = 8_000  # LayerCode requires 8kHz for WebSocket audio


def load_audio(path: Path) -> AudioSegment:
    return AudioSegment.from_file(path)


def ensure_mono_pcm16(
    segment: AudioSegment, sample_rate: int = DEFAULT_SAMPLE_RATE
) -> AudioSegment:
    processed = segment.set_frame_rate(sample_rate).set_sample_width(2).set_channels(1)
    return processed


def segment_to_base64(segment: AudioSegment, format_: str = "wav") -> str:
    buffer = BytesIO()
    segment.export(buffer, format=format_)
    raw_bytes = buffer.getvalue()
    return base64.b64encode(raw_bytes).decode("ascii")


def base64_to_segment(
    content: str, sample_rate: int = DEFAULT_SAMPLE_RATE
) -> AudioSegment:
    raw_bytes = base64.b64decode(content)
    return AudioSegment(
        data=raw_bytes,
        sample_width=2,
        frame_rate=sample_rate,
        channels=1,
    )


def concatenate_with_gap(
    segments: list[AudioSegment], gap_ms: int = 300
) -> AudioSegment:
    if not segments:
        return AudioSegment.silent(duration=gap_ms)
    gap = AudioSegment.silent(duration=gap_ms)
    mixed = segments[0]
    for segment in segments[1:]:
        mixed += gap + segment
    return mixed
