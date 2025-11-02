# API Reference

Complete API documentation for LayerCode Gym.

## Core Classes

### LayercodeClient

The main client for running voice agent conversations.

```python
from layercode_gym import LayercodeClient
```

#### Constructor

```python
LayercodeClient(
    simulator: UserSimulatorProtocol,
    settings: Settings | None = None,
    turn_callback: TurnCallback | None = None,
    conversation_callback: ConversationCallback | None = None
)
```

**Parameters:**

- `simulator`: UserSimulator instance that generates user responses
- `settings`: Optional Settings object (defaults to environment variables)
- `turn_callback`: Optional callback called after each turn
- `conversation_callback`: Optional callback called at conversation end

#### Methods

##### run()

```python
async def run() -> str
```

Run the conversation and return the conversation ID.

**Returns:** `str` - Unique conversation ID

**Example:**

```python
client = LayercodeClient(simulator=simulator)
conversation_id = await client.run()
```

---

### UserSimulator

Factory class for creating user simulators.

```python
from layercode_gym import UserSimulator
```

#### Factory Methods

##### from_text()

```python
@classmethod
def from_text(
    cls,
    messages: list[str],
    send_as_text: bool = True,
    tts_engine: TTSEngineProtocol | None = None,
    settings: Settings | None = None
) -> UserSimulatorProtocol
```

Create a simulator with fixed text messages.

**Parameters:**

- `messages`: List of text messages to send
- `send_as_text`: If True, send as text; if False, convert to audio via TTS
- `tts_engine`: Optional custom TTS engine (auto-created if None and send_as_text=False)
- `settings`: Optional Settings object

**Returns:** `UserSimulatorProtocol` instance

**Example:**

```python
simulator = UserSimulator.from_text(
    messages=["Hello!", "How are you?"],
    send_as_text=True
)
```

##### from_files()

```python
@classmethod
def from_files(
    cls,
    files: list[Path]
) -> UserSimulatorProtocol
```

Create a simulator that streams pre-recorded audio files.

**Parameters:**

- `files`: List of Path objects pointing to audio files (WAV or MP3)

**Returns:** `UserSimulatorProtocol` instance

**Example:**

```python
from pathlib import Path

simulator = UserSimulator.from_files(
    files=[Path("audio1.wav"), Path("audio2.wav")]
)
```

##### from_agent()

```python
@classmethod
def from_agent(
    cls,
    persona: Persona | None = None,
    agent: Agent | None = None,
    deps: Any = None,
    model: str = "openai:gpt-4o-mini",
    max_turns: int = 5,
    send_as_text: bool = False,
    tts_engine: TTSEngineProtocol | None = None,
    settings: Settings | None = None
) -> UserSimulatorProtocol
```

Create an AI-driven simulator with dynamic responses.

**Parameters:**

- `persona`: Persona object defining user background and intent
- `agent`: Optional custom PydanticAI Agent (overrides persona)
- `deps`: Optional dependencies for custom agent
- `model`: Model name (e.g., "openai:gpt-4o-mini", "anthropic:claude-3-5-sonnet")
- `max_turns`: Maximum number of turns before ending
- `send_as_text`: If True, send as text; if False, use TTS
- `tts_engine`: Optional custom TTS engine
- `settings`: Optional Settings object

**Returns:** `UserSimulatorProtocol` instance

**Example:**

```python
simulator = UserSimulator.from_agent(
    persona=Persona(
        background_context="You are a busy executive",
        intent="You want quick answers"
    ),
    model="openai:gpt-4o-mini",
    max_turns=5
)
```

---

### Persona

Defines user persona for AI-driven simulators.

```python
from layercode_gym import Persona
```

#### Constructor

```python
Persona(
    background_context: str,
    intent: str
)
```

**Parameters:**

- `background_context`: Description of user's background, personality, and situation
- `intent`: User's goal or intent for the conversation

**Example:**

```python
persona = Persona(
    background_context="""
    You are Sarah, a 35-year-old small business owner.
    You're tech-savvy but busy.
    """,
    intent="You want to understand pricing and features."
)
```

---

### Settings

Configuration settings for LayerCode Gym.

```python
from layercode_gym import Settings
```

#### Constructor

```python
Settings(
    server_url: str,
    agent_id: str,
    tts_model: str = "gpt-4o-mini-tts",
    tts_voice: str = "coral",
    tts_instructions: str = "",
    chunk_ms: int = 100,
    chunk_interval: float = 0.0,
    output_root: str = "./conversations"
)
```

**Parameters:**

- `server_url`: Your backend server URL
- `agent_id`: Your Layercode agent ID
- `tts_model`: OpenAI TTS model name
- `tts_voice`: TTS voice (alloy, echo, fable, onyx, nova, shimmer, coral)
- `tts_instructions`: Optional voice instructions
- `chunk_ms`: Audio chunk size in milliseconds
- `chunk_interval`: Delay between chunks in seconds
- `output_root`: Directory for saving conversation results

**Example:**

```python
settings = Settings(
    server_url="http://localhost:8001",
    agent_id="your_agent_id",
    tts_voice="alloy"
)
```

**Environment Variables:**

Settings can be loaded from environment variables:

```bash
SERVER_URL="http://localhost:8001"
LAYERCODE_AGENT_ID="your_agent_id"
OPENAI_TTS_MODEL="gpt-4o-mini-tts"
OPENAI_TTS_VOICE="coral"
OPENAI_TTS_INSTRUCTIONS="Speak clearly"
LAYERCODE_CHUNK_MS="100"
LAYERCODE_CHUNK_INTERVAL="0.0"
LAYERCODE_OUTPUT_ROOT="./conversations"
LOGFIRE_TOKEN="..."  # Optional: enable LogFire observability
```

---

## Callbacks

### create_judge_callback()

```python
from layercode_gym.callbacks import create_judge_callback

def create_judge_callback(
    criteria: list[str],
    model: str = "openai:gpt-4o"
) -> TurnCallback
```

Create an LLM-as-judge callback for evaluating conversation quality.

**Parameters:**

- `criteria`: List of evaluation criteria as questions
- `model`: Model to use for evaluation (e.g., "openai:gpt-4o", "anthropic:claude-3-5-sonnet")

**Returns:** `TurnCallback` function

**Example:**

```python
judge = create_judge_callback(
    criteria=[
        "Did the agent answer the user's question?",
        "Was the agent polite?"
    ],
    model="openai:gpt-4o"
)

client = LayercodeClient(
    simulator=simulator,
    turn_callback=judge
)
```

### TurnCallback

```python
from typing import Callable, Awaitable

TurnCallback = Callable[
    [int, str, str, str],
    Awaitable[None]
]
```

Callback function called after each conversation turn.

**Parameters:**

- `turn_number: int` - Current turn number (0-indexed)
- `user_message: str` - User's message text
- `agent_message: str` - Agent's response text
- `conversation_id: str` - Unique conversation ID

**Example:**

```python
async def my_callback(
    turn_number: int,
    user_message: str,
    agent_message: str,
    conversation_id: str
) -> None:
    print(f"Turn {turn_number}: User said '{user_message}'")
```

### ConversationCallback

```python
from typing import Callable, Awaitable
from layercode_gym.models import ConversationLog

ConversationCallback = Callable[
    [ConversationLog],
    Awaitable[None]
]
```

Callback function called at the end of a conversation.

**Parameters:**

- `conversation_log: ConversationLog` - Complete conversation data

**Example:**

```python
async def my_callback(log: ConversationLog) -> None:
    print(f"Conversation {log.conversation_id} complete")
    print(f"Total turns: {log.stats['total_turns']}")
```

---

## Protocols

### UserSimulatorProtocol

```python
from layercode_gym.simulator import UserSimulatorProtocol
```

Protocol for implementing custom user simulators.

#### Methods

##### get_response()

```python
async def get_response(
    self,
    request: UserRequest
) -> UserResponse | None
```

Generate the next user response.

**Parameters:**

- `request: UserRequest` - Contains conversation context

**Returns:** `UserResponse` or `None` to end conversation

**Example:**

```python
from layercode_gym.simulator import (
    UserSimulatorProtocol,
    UserRequest,
    UserResponse
)

class MySimulator(UserSimulatorProtocol):
    async def get_response(
        self,
        request: UserRequest
    ) -> UserResponse | None:
        if request.turn_number > 5:
            return None  # End conversation

        return UserResponse(
            text="My response",
            audio_path=None,
            data=()
        )
```

### TTSEngineProtocol

```python
from layercode_gym.simulator import TTSEngineProtocol
```

Protocol for implementing custom TTS engines.

#### Methods

##### synthesize()

```python
async def synthesize(
    self,
    text: str,
    **kwargs
) -> Path
```

Convert text to speech audio file.

**Parameters:**

- `text: str` - Text to synthesize
- `**kwargs` - Additional parameters

**Returns:** `Path` - Path to generated audio file

**Example:**

```python
from pathlib import Path
from layercode_gym.simulator import TTSEngineProtocol

class MyTTSEngine(TTSEngineProtocol):
    async def synthesize(self, text: str, **kwargs) -> Path:
        # Call your TTS service
        audio_data = await my_tts_api.generate(text)

        # Save to file
        output_path = Path("output.wav")
        output_path.write_bytes(audio_data)

        return output_path
```

---

## Data Models

### UserRequest

```python
from layercode_gym.simulator import UserRequest
```

Request data passed to user simulator.

**Attributes:**

- `agent_transcript: list[str]` - All agent messages so far
- `turn_number: int` - Current turn number (0-indexed)
- `conversation_id: str` - Unique conversation ID

### UserResponse

```python
from layercode_gym.simulator import UserResponse
```

Response from user simulator.

**Attributes:**

- `text: str` - User message text
- `audio_path: Path | None` - Optional path to audio file
- `data: tuple` - Additional data (reserved for future use)

### ConversationLog

```python
from layercode_gym.models import ConversationLog
```

Complete conversation data.

**Attributes:**

- `conversation_id: str` - Unique ID
- `agent_id: str` - Agent ID
- `started_at: str` - ISO timestamp
- `ended_at: str` - ISO timestamp
- `turns: list[Turn]` - All conversation turns
- `stats: dict` - Aggregate statistics

**Stats Dictionary:**

```python
{
    "total_turns": int,
    "duration_seconds": float,
    "avg_latency_ms": float,
    "avg_ttfab_ms": float,
    "total_user_words": int,
    "total_agent_words": int
}
```

### Turn

```python
from layercode_gym.models import Turn
```

Single conversation turn.

**Attributes:**

- `turn_number: int` - Turn index
- `user_message: Message` - User's message
- `agent_message: Message` - Agent's response

### Message

```python
from layercode_gym.models import Message
```

Single message in conversation.

**Attributes:**

- `text: str` - Message text
- `timestamp: str` - ISO timestamp
- `audio_path: str | None` - Optional audio file path
- `ttfab_ms: int | None` - Time to first audio byte (agent messages only)

---

## Type Hints

LayerCode Gym is fully typed with `mypy --strict` compatibility.

```python
from layercode_gym import (
    LayercodeClient,
    UserSimulator,
    Persona,
    Settings
)
from layercode_gym.simulator import (
    UserSimulatorProtocol,
    TTSEngineProtocol,
    UserRequest,
    UserResponse
)
from layercode_gym.callbacks import (
    TurnCallback,
    ConversationCallback,
    create_judge_callback
)
from layercode_gym.models import (
    ConversationLog,
    Turn,
    Message
)
```

Run type checks:

```bash
uv run mypy src/layercode_gym
```

---

## Next Steps

- [Examples](examples.md) - See practical usage examples
- [Advanced Usage](advanced.md) - LogFire integration and custom implementations
- [Concepts](concepts.md) - Understand the architecture
