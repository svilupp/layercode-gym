# LayerCode Gym

[![CI](https://github.com/svilupp/layercode-gym/actions/workflows/ci.yml/badge.svg)](https://github.com/svilupp/layercode-gym/actions/workflows/ci.yml)
[![Docs](https://github.com/svilupp/layercode-gym/actions/workflows/docs.yml/badge.svg)](https://github.com/svilupp/layercode-gym/actions/workflows/docs.yml)
[![Documentation](https://img.shields.io/badge/docs-latest-blue.svg)](https://svilupp.github.io/layercode-gym)

**Does your voice AI agent even lift, bro?**

> **Warning (v0.0.1-alpha):** This toolkit is an early alpha and may contain bugs or breaking changes. Please test thoroughly before using in production.

This is an **unofficial** testing gym for voice AI agents built on [Layercode.com](https://layercode.com). Quickly spin up a testing environment to run through hundreds of scenarios and understand how your agent will perform in production.

LayerCode Gym simulates clients end-to-end, driving the WebSocket API the same way a browser would. Run conversations concurrently, test different user scenarios, and get detailed analytics with transcripts and audio recordings.

Perfect for regression testing, load testing, and automated evaluation of your voice AI agents.

## What It Does

LayerCode Gym provides an environment that acts like a real voice client, with three types of user simulators:

1. **Fixed Text Messages** - Send predetermined text responses (fastest, good for regression testing)
2. **Pre-recorded Audio Files** - Stream audio files to stress-test transcription and agent behavior
3. **AI Agent Personas** - Use PydanticAI to simulate realistic users with specific personalities and goals

After each conversation, you get:
- Full transcript with timing metrics (TTFAB, latency stats)
- Combined audio file for playback review
- Turn-by-turn conversation logs
- Optional LLM-as-judge scoring via callbacks

## Quick Start

**IMPORTANT:** This assumes you have a backend server implemented and configured in the [Layercode dashboard](https://dash.layercode.com).

Don't have a server yet? Get started quickly:
```bash
# Launch a quickstart server with auto-tunneling (uses cloudflared under the hood - if you have it)
uvx layercode-create-app run --tunnel

# This will:
# - Start a local backend server
# - Create a Cloudflare tunnel for public access
# - Display the tunnel URL to enter in the Layercode dashboard
#
# Use -h to see all CLI options
```

Once you have a server running:

```bash
# 1. Set environment variables
export SERVER_URL="http://localhost:8001"    # Your backend server (NOT LayerCode API)
export LAYERCODE_AGENT_ID="your_agent_id"    # Your LayerCode agent ID
export OPENAI_API_KEY="sk-..."               # For TTS and AI personas (optional)

# 2. Run with uvx (no installation required!)
uvx layercode-gym --text "Hello, I need help with my account"

# Or install it
uv add layercode-gym

# 3. Use the CLI for quick testing
layercode-gym --text "Hello" --text "Can you help me?"
layercode-gym --file recording.wav
layercode-gym --agent --persona-intent "Book a flight to NYC"

# 4. Or use Python API for advanced scenarios
python examples/01_text_messages.py          # Basic text conversation
python examples/05_batch_evaluation.py       # Run 3 conversations concurrently
```

## CLI Quick Tester

The `layercode-gym` CLI provides the fastest way to test your LayerCode server without writing code.

### Basic Usage

```bash
# Simple text message
uvx layercode-gym --text "Hello, I need help"

# Multiple messages (sent one per turn)
uvx layercode-gym --text "Hi" --text "Tell me more" --text "Goodbye"

# Audio file playback
uvx layercode-gym --file recording.wav

# AI agent with persona
uvx layercode-gym --agent \
  --persona-background "You are a frustrated customer" \
  --persona-intent "Cancel your subscription"

# Custom server configuration
uvx layercode-gym --text "Hello" \
  --server-url http://localhost:3000 \
  --authorize-path /auth/layercode \
  --agent-id your_agent_id
```

### Available Options

Run `uvx layercode-gym --help` to see all options:

**Input Modes** (composable):
- `--text MESSAGE` - Send text message(s)
- `--file PATH` - Play audio file(s)
- `--agent` - Use AI agent with optional persona

**Server Configuration**:
- `--server-url URL` - Your backend server (default: `SERVER_URL` env var)
- `--authorize-path PATH` - Auth endpoint (default: `/api/authorize`)
- `--agent-id ID` - LayerCode agent ID (default: `LAYERCODE_AGENT_ID` env var)

**Conversation Control**:
- `--max-turns N` - Limit conversation turns
- `--output-dir PATH` - Save location for conversation logs

**TTS Options** (for agent mode):
- `--tts-model MODEL` - OpenAI TTS model
- `--tts-voice VOICE` - Voice (alloy, echo, fable, onyx, nova, shimmer, coral)
- `--tts-instructions TEXT` - Voice style instructions

**Debugging**:
- `--verbose, -v` - Show detailed configuration and logs
- `--use-logfire` - Enable LogFire observability

### No Installation Required

Use `uvx` to run without installing:

```bash
# First run downloads and caches the package
uvx layercode-gym --text "Hello"

# Subsequent runs use cached version
uvx layercode-gym --agent --persona-intent "Book a flight"
```

Or install for faster startup:

```bash
uv add layercode-gym
layercode-gym --text "Hello"
```

## Architecture

**Authorization Flow:**
1. Client authorizes through YOUR backend server (`SERVER_URL`)
2. Backend returns `client_session_key` from LayerCode
3. Client connects to LayerCode WebSocket with that key

The client never hits LayerCode's API directly - it always goes through your backend first.

## Python API Examples

### 01: Text Messages (Fastest)
```python
from layercode_gym import LayercodeClient, UserSimulator

simulator = UserSimulator.from_text(
    messages=[
        "Hello! I'm interested in your services.",
        "Tell me more about pricing.",
        "Thank you, goodbye."
    ],
    send_as_text=True  # Fast, no TTS needed
)

client = LayercodeClient(simulator=simulator)
conversation_id = await client.run()
```

### 02: Audio Files (Stress Test Transcription)
```python
from pathlib import Path

simulator = UserSimulator.from_files(
    files=[
        Path("intro.wav"),
        Path("question.wav"),
        Path("goodbye.wav")
    ]
)

client = LayercodeClient(simulator=simulator)
conversation_id = await client.run()
```

### 03: AI Agent Personas (Realistic Simulation)
```python
from layercode_gym import Persona

persona = Persona(
    background_context="You are a 35-year-old small business owner",
    intent="You want to understand pricing and features"
)

simulator = UserSimulator.from_agent(
    persona=persona,
    max_turns=5,
    send_as_text=False  # Uses TTS automatically
)

client = LayercodeClient(simulator=simulator)
conversation_id = await client.run()
```

### 04: LLM-as-Judge Evaluation
```python
from layercode_gym.callbacks import create_judge_callback

judge = create_judge_callback(
    criteria=[
        "Did the agent answer all user questions?",
        "Was the agent polite and professional?",
        "Did the conversation flow naturally?"
    ],
    model="openai:gpt-4o"
)

client = LayercodeClient(
    simulator=simulator,
    turn_callback=judge  # Runs after each turn
)
conversation_id = await client.run()
```

### 05: Batch Evaluation (Scale Testing)
```python
import asyncio
from tqdm.asyncio import tqdm_asyncio

scenarios = [
    "Hello! I'm interested in learning about your services.",
    "Hi there! Can you help me with a question?",
    "Good morning! I'd like to know more about what you offer.",
]

tasks = [
    run_conversation(message) for message in scenarios
]

# Run all conversations concurrently with progress bar
results = await tqdm_asyncio.gather(*tasks, desc="Running conversations")
```

See `examples/05_batch_evaluation.py` for the full pattern.

## User Simulators (Core Concept)

The `UserSimulator` is the heart of LayerCode Gym. It generates user responses during conversations.

### Three Factory Methods

```python
# 1. from_text() - Fixed messages
UserSimulator.from_text(
    messages=["Hello", "Tell me more", "Goodbye"],
    send_as_text=True  # or False to auto-generate TTS audio
)

# 2. from_files() - Pre-recorded audio
UserSimulator.from_files(
    files=[Path("msg1.wav"), Path("msg2.wav")]
)

# 3. from_agent() - AI-driven with PydanticAI
UserSimulator.from_agent(
    persona=Persona(background_context="...", intent="..."),
    model="openai:gpt-4o-mini",  # or "anthropic:claude-3-5-sonnet"
    max_turns=5,
    send_as_text=False  # Auto-creates OpenAI TTS engine
)
```

### TTS Auto-Creation

When `send_as_text=False`, LayerCode Gym automatically creates an OpenAI TTS engine:

```python
# This works out of the box
simulator = UserSimulator.from_text(
    messages=["Hello!"],
    send_as_text=False  # TTS engine auto-created with defaults
)
```

Configure via environment:
```bash
export OPENAI_TTS_MODEL="gpt-4o-mini-tts"  # default
export OPENAI_TTS_VOICE="coral"            # default
export OPENAI_TTS_INSTRUCTIONS="Speak slowly and clearly"
```

Or pass custom settings:
```python
from layercode_gym import Settings

settings = Settings(
    server_url="http://localhost:8001",
    agent_id="your_agent_id",
    tts_model="gpt-4o-mini-tts",
    tts_voice="alloy",
    # ... other settings
)

simulator = UserSimulator.from_text(
    messages=["Hello!"],
    send_as_text=False,
    settings=settings
)
```

### Custom Simulators

Implement `UserSimulatorProtocol` for full control:

```python
from layercode_gym.simulator import UserSimulatorProtocol, UserRequest, UserResponse

class MyCustomSimulator(UserSimulatorProtocol):
    async def get_response(self, request: UserRequest) -> UserResponse | None:
        # Your logic here
        return UserResponse(text="Hello!", audio_path=None, data=())
```

## Environment Variables

Required:
```bash
SERVER_URL="http://localhost:8001"       # Your backend server
LAYERCODE_AGENT_ID="your_agent_id"       # LayerCode agent ID
```

Optional:
```bash
# OpenAI (for TTS and AI agents)
OPENAI_API_KEY="sk-..."

# TTS Configuration
OPENAI_TTS_MODEL="gpt-4o-mini-tts"       # default
OPENAI_TTS_VOICE="coral"                  # default: alloy, echo, fable, onyx, nova, shimmer, coral
OPENAI_TTS_INSTRUCTIONS="..."             # optional voice instructions

# Audio Chunking (advanced)
LAYERCODE_CHUNK_MS="100"                  # ms per audio chunk (default: 100)
LAYERCODE_CHUNK_INTERVAL="0.0"            # delay between chunks in seconds

# Storage
LAYERCODE_OUTPUT_ROOT="./conversations"   # where to save results

# Observability (optional)
LOGFIRE_TOKEN="..."                       # enable LogFire observability (if-token-present)
```

## Observability and Outputs

### LogFire Integration

LayerCode Gym integrates with [LogFire](https://logfire.pydantic.dev/) for real-time observability. Simply provide your LogFire token and it will automatically instrument PydanticAI and OpenAI:

```bash
export LOGFIRE_TOKEN="your_token_here"
```

This gives you:
- Real-time conversation tracking
- Performance metrics and spans
- Error tracking and debugging
- Beautiful UI for exploring conversations

### Conversation Outputs

After each conversation, LayerCode Gym creates:

```
conversations/<conversation_id>/
├── transcript.json          # Full conversation log with stats
├── conversation_mix.wav     # Combined audio (user + assistant)
├── user_0.wav              # Individual user audio files
├── assistant_0.wav         # Individual assistant audio files
└── judge_results.json      # If using judge callback
```

The transcript includes:
- Turn-by-turn messages with timestamps
- TTFAB (Time To First Audio Byte) metrics
- Latency statistics
- Conversation duration and turn counts

## Pluggable Components

LayerCode Gym is built around **OpenAI by default** but supports custom implementations:

### Custom TTS Engine
```python
from layercode_gym.simulator import TTSEngineProtocol

class MyTTSEngine(TTSEngineProtocol):
    async def synthesize(self, text: str, **kwargs) -> Path:
        # Use your TTS service (ElevenLabs, Azure, etc.)
        return audio_file_path

simulator = UserSimulator.from_text(
    messages=["Hello!"],
    send_as_text=False,
    tts_engine=MyTTSEngine()
)
```

### Custom LLM for Agents
```python
from pydantic_ai import Agent

# Use any LLM supported by PydanticAI
agent = Agent("anthropic:claude-3-5-sonnet")  # Anthropic
agent = Agent("openai:gpt-4o")                # OpenAI
agent = Agent("ollama:llama3")                # Ollama local
agent = Agent("gemini:gemini-1.5-pro")        # Google

simulator = UserSimulator.from_agent(agent=agent, deps=my_deps)
```

## File Structure

```
src/layercode_gym/
├── client.py              # Core WebSocket client
├── config.py              # Settings and environment variables
├── storage.py             # Conversation persistence
├── callbacks.py           # Turn/conversation callbacks, judge
├── simulator/
│   ├── base.py           # UserSimulator factory methods
│   ├── agent.py          # AgentTurnStrategy (PydanticAI)
│   ├── basic_agent.py    # Default persona agent
│   ├── tts.py            # OpenAI TTS engine
│   └── protocols.py      # Protocols for extension
└── models/
    ├── conversation.py    # ConversationLog, Turn, Message
    └── events.py          # WebSocket event schemas
```

## Roadmap

Planned enhancements:

### Audio Effects (via Pydub)
- Background noise injection
- Simulated loud conversations
- Accent stress testing via TTS instructions
- Audio quality degradation

### Additional Simulators
- CSV-driven scenarios
- Multi-language personas

### Evaluation Tools
- Built-in scoring metrics
- Regression detection

## Related Projects

- **[layercode-create-app](https://github.com/svilupp/layercode-create-app)** - CLI to scaffold LayerCode backends with tunneling
- **[layercode-examples](https://github.com/svilupp/layercode-examples)** - Agent patterns and integration recipes

## Learn More

- LayerCode docs: [docs.layercode.com](https://docs.layercode.com/)
- PydanticAI: [ai.pydantic.dev](https://ai.pydantic.dev/)
- LogFire: [logfire.pydantic.dev](https://logfire.pydantic.dev/)

## Type Safety

LayerCode Gym enforces `mypy --strict` throughout. All event schemas use `TypedDict` or dataclasses with precise typing.

Run type checks:
```bash
uv run mypy src/layercode_gym
```

## Contributing

This is a minimal, focused toolkit. Extensions should be done via:
- Custom simulator strategies (implement `UserSimulatorProtocol`)
- Custom callbacks (implement `TurnCallback` or `ConversationCallback`)
- Custom TTS engines (implement `TTSEngineProtocol`)

Keep the core simple and extensible.
