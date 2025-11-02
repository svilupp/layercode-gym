from __future__ import annotations

"""Text-to-speech implementations used by simulators."""

import asyncio
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from openai import OpenAI

from .protocols import TTSEngineProtocol


@dataclass(slots=True)
class OpenAITTSEngine(TTSEngineProtocol):
    model: str = "gpt-4o-mini-tts"
    default_voice: str = "coral"
    default_instructions: str | None = None
    output_dir: Path | None = None
    client_kwargs: dict[str, Any] | None = None
    _client: OpenAI | None = None

    def __post_init__(self) -> None:
        if self.output_dir is None:
            # Use system temp directory to avoid cluttering project root
            temp_dir = Path(tempfile.gettempdir()) / "layercode_gym_tts"
            temp_dir.mkdir(parents=True, exist_ok=True)
            self.output_dir = temp_dir
        else:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        if self.client_kwargs is None:
            self.client_kwargs = {}
        if self._client is None:
            self._client = OpenAI(**self.client_kwargs)

    async def synthesize(
        self,
        text: str,
        *,
        voice: str | None = None,
        instructions: str | None = None,
        conversation_id: str | None = None,
        turn_id: str | None = None,
    ) -> Path:
        resolved_voice = voice or self.default_voice
        resolved_instructions = instructions or self.default_instructions
        base_dir = self.output_dir
        if base_dir is None:  # pragma: no cover - should not happen
            msg = "output_dir should be initialised in __post_init__"
            raise RuntimeError(msg)
        file_name = self._build_filename(conversation_id, turn_id)
        target_path = base_dir / file_name

        client = self._client
        if client is None:  # pragma: no cover - defensive
            msg = "OpenAITTSEngine client not initialised"
            raise RuntimeError(msg)

        def _generate() -> Path:
            kwargs: dict[str, Any] = {
                "model": self.model,
                "voice": resolved_voice,
                "input": text,
            }
            if resolved_instructions is not None:
                kwargs["instructions"] = resolved_instructions
            with client.audio.speech.with_streaming_response.create(
                **kwargs
            ) as response:
                response.stream_to_file(target_path)
            return target_path

        return await asyncio.to_thread(_generate)

    def _build_filename(self, conversation_id: str | None, turn_id: str | None) -> str:
        prefix_parts: list[str] = []
        if conversation_id:
            prefix_parts.append(conversation_id)
        if turn_id:
            prefix_parts.append(turn_id)
        if not prefix_parts:
            prefix_parts.append("tts")
        prefix = "-".join(prefix_parts)
        unique = uuid4().hex[:8]
        return f"{prefix}-{unique}.mp3"

    def cleanup_temp_files(self, conversation_id: str | None = None) -> int:
        """Remove temporary TTS files for a conversation or all files.

        Args:
            conversation_id: If provided, only delete files for this conversation.
                           If None, delete all TTS temp files.

        Returns:
            Number of files deleted.
        """
        if self.output_dir is None or not self.output_dir.exists():
            return 0

        deleted = 0
        pattern = f"{conversation_id}-*.mp3" if conversation_id else "*.mp3"
        for file in self.output_dir.glob(pattern):
            try:
                file.unlink()
                deleted += 1
            except OSError:
                pass
        return deleted
