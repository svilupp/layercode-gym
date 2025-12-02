from __future__ import annotations

"""Environment-backed configuration suitable for mypy strict."""

from dataclasses import dataclass
from pathlib import Path
import os
from typing import Final

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True, slots=True)
class Settings:
    """Immutable settings sourced from environment variables."""

    server_url: str
    authorize_path: str
    websocket_url: str
    agent_id: str | None
    output_root: Path
    openai_api_key: str | None
    # TTS configuration (defaults from simple_ai_client.py)
    tts_model: str
    tts_voice: str
    tts_instructions: str | None
    # Audio chunking configuration (defaults from simple_ai_client.py)
    chunk_ms: int  # Milliseconds of audio per chunk (default: 100)
    chunk_interval: float  # Delay between chunks in seconds (default: 0.0)
    # Audio storage (can be disabled for CI to skip ffmpeg dependency)
    store_audio: bool  # Whether to store audio files (default: True)

    @classmethod
    def load(cls) -> "Settings":
        # User's backend server (for authorization)
        server_url = os.getenv("SERVER_URL", "http://localhost:8001")
        authorize_path = os.getenv("AUTHORIZE_PATH", "/api/authorize")
        # LayerCode WebSocket endpoint (hardcoded, not user-configurable)
        websocket_url = "wss://api.layercode.com/v1/agents/web/websocket"
        agent_id = os.getenv("LAYERCODE_AGENT_ID")
        output_root = Path(
            os.getenv("LAYERCODE_OUTPUT_ROOT", "./conversations")
        ).resolve()
        openai_api_key = os.getenv("OPENAI_API_KEY")

        # TTS configuration with defaults from simple_ai_client.py
        tts_model = os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
        tts_voice = os.getenv("OPENAI_TTS_VOICE", "coral")
        tts_instructions = os.getenv("OPENAI_TTS_INSTRUCTIONS")

        # Audio chunking configuration with defaults from simple_ai_client.py
        chunk_ms = int(os.getenv("LAYERCODE_CHUNK_MS", "100"))
        chunk_interval = float(os.getenv("LAYERCODE_CHUNK_INTERVAL", "0.0"))

        # Audio storage (can be disabled for CI to skip ffmpeg dependency)
        store_audio = os.getenv("LAYERCODE_STORE_AUDIO", "true").lower() == "true"

        return cls(
            server_url=server_url,
            authorize_path=authorize_path,
            websocket_url=websocket_url,
            agent_id=agent_id,
            output_root=output_root,
            openai_api_key=openai_api_key,
            tts_model=tts_model,
            tts_voice=tts_voice,
            tts_instructions=tts_instructions,
            chunk_ms=chunk_ms,
            chunk_interval=chunk_interval,
            store_audio=store_audio,
        )


DEFAULT_SETTINGS: Final[Settings] = Settings.load()
