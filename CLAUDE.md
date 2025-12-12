# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LayerCode Gym is a testing toolkit for voice AI agents built on LayerCode.com. It enables regression testing, load testing, and automated evaluation of voice agents through simulated conversations.

## Development Commands

```bash
# Install dependencies
uv sync

# Install with dev dependencies
uv sync --group dev

# Run linting
uv run ruff check src/
uv run ruff format --check src/

# Run type checking
uv run ty check src/ tests/

# Test package imports
uv run python -c "from layercode_gym import LayercodeClient, UserSimulator, Persona, Settings"

# Run CLI directly
uvx layercode-gym run --text "Hello"

# Run an example
python examples/01_text_messages.py
```

## Architecture

### Core Components

- **LayercodeClient** (`client.py`): Async WebSocket client that orchestrates conversations. Handles authorization through user's backend server, manages turn-taking between user simulator and assistant.

- **UserSimulator** (`simulator/base.py`): Facade providing three factory methods:
  - `from_text()`: Fixed text messages (with optional TTS)
  - `from_files()`: Pre-recorded audio files
  - `from_agent()`: AI-driven dynamic responses using PydanticAI

- **Protocols** (`simulator/protocols.py`): Defines extension points:
  - `UserSimulatorProtocol`: For custom simulators
  - `TTSEngineProtocol`: For custom TTS engines
  - `SimulatorHook`: For pre/post response hooks

- **Callbacks** (`callbacks.py`): `TurnCallback` and `ConversationCallback` protocols for hooking into conversation lifecycle.

### Data Flow

1. Client authorizes via user's backend server (`SERVER_URL` + `/api/authorize`)
2. Backend returns `client_session_key` from LayerCode
3. Client connects to LayerCode WebSocket with that key
4. UserSimulator generates responses based on its strategy
5. Results saved to `conversations/<id>/` with transcripts and audio

### Key Patterns

- Uses `dataclass(slots=True)` throughout for performance
- Async/await with `websockets` and `httpx`
- Strategy pattern for simulator types (`TextScriptStrategy`, `FileScriptStrategy`, `AgentTurnStrategy`)
- Protocol classes for extensibility (not abstract base classes)

## Model References

This project uses OpenAI's GPT-5 models. Do NOT change these to older models:
- `gpt-5-mini` - Fast/cheap model for testing and examples
- `gpt-5` - Production-quality model for accurate evaluation

These models are released and available. Do not "fix" them to gpt-4o or other older models.

## Environment Variables

Required:
- `SERVER_URL`: Your backend server URL (default: `http://localhost:8001`)
- `LAYERCODE_AGENT_ID`: LayerCode agent ID

Optional:
- `OPENAI_API_KEY`: For TTS and AI personas
- `OPENAI_TTS_MODEL`, `OPENAI_TTS_VOICE`: TTS configuration
- `LAYERCODE_OUTPUT_ROOT`: Output directory (default: `./conversations`)
- `LAYERCODE_STORE_AUDIO`: Set to `false` to skip audio file storage (default: `true`). Useful for CI where ffmpeg may not be available.
- `AUTHORIZE_PATH`: Authorization endpoint path (default: `/api/authorize`)
- `LAYERCODE_CUSTOM_METADATA`: JSON object with custom metadata for authorization (e.g., `'{"tenant_id": "t_42"}'`)
- `LAYERCODE_CUSTOM_HEADERS`: JSON object with custom headers for outbound webhooks (e.g., `'{"x-tenant-id": "t_42"}'`)
- `LAYERCODE_AUTH_HEADERS`: JSON object with headers to send TO the authorization endpoint (e.g., `'{"Authorization": "Bearer token"}'`)
