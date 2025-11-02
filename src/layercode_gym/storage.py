from __future__ import annotations

"""Persistence helpers for conversation artefacts."""

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Any, Iterable

from pydub import AudioSegment

from .models.conversation import ConversationLog


@dataclass(frozen=True, slots=True)
class StoragePaths:
    root: Path
    audio_dir: Path
    data_dir: Path
    text_dir: Path


class ConversationStorage:
    def __init__(self, base_dir: Path, conversation_id: str) -> None:
        # Folder named by conversation_id only (no timestamp suffix)
        root = base_dir / conversation_id
        audio_dir = root / "audio"
        data_dir = root / "data"
        text_dir = root / "text"
        for directory in (audio_dir, data_dir, text_dir):
            directory.mkdir(parents=True, exist_ok=True)
        self.paths = StoragePaths(
            root=root, audio_dir=audio_dir, data_dir=data_dir, text_dir=text_dir
        )

    def store_audio_segment(
        self,
        segment: AudioSegment,
        *,
        role: str,
        turn_index: int,
        timestamp: datetime,
        suffix: str = "wav",
    ) -> Path:
        # Files include timestamp for chronological ordering
        ts_str = timestamp.strftime("%Y%m%d_%H%M%S_%f")[:-3]  # milliseconds
        filename = f"{role}_{ts_str}_turn{turn_index}.{suffix}"
        target = self.paths.audio_dir / filename
        segment.export(target, format=suffix)
        return target

    def store_text(
        self, text: str, *, role: str, turn_index: int, timestamp: datetime
    ) -> Path:
        # Files include timestamp for chronological ordering
        ts_str = timestamp.strftime("%Y%m%d_%H%M%S_%f")[:-3]  # milliseconds
        filename = f"{role}_{ts_str}_turn{turn_index}.txt"
        target = self.paths.text_dir / filename
        target.write_text(text, encoding="utf-8")
        return target

    def store_data_payload(self, payload: dict[str, Any], *, name: str) -> Path:
        target = self.paths.data_dir / f"{name}.json"
        target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return target

    def write_transcript(self, log: ConversationLog) -> Path:
        target = self.paths.root / "transcript.json"
        serialized = json.dumps(log.to_jsonable(), indent=2)
        target.write_text(serialized, encoding="utf-8")
        return target

    def export_combined_audio(
        self, segments: Iterable[AudioSegment], filename: str = "conversation_mix.wav"
    ) -> Path:
        combined = None
        for segment in segments:
            combined = (
                segment
                if combined is None
                else combined + AudioSegment.silent(duration=300) + segment
            )
        if combined is None:
            combined = AudioSegment.silent(duration=300)
        target = self.paths.audio_dir / filename
        combined.export(target, format="wav")
        return target
