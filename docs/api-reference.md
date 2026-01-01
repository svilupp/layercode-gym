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
    conversation_callback: ConversationCallback | None = None,
    data_processor: ResponseDataProcessor | None = None
)
```

**Parameters:**

- `simulator`: UserSimulator instance that generates user responses
- `settings`: Optional Settings object (defaults to environment variables)
- `turn_callback`: Optional callback called after each turn
- `conversation_callback`: Optional callback called at conversation end
- `data_processor`: Optional processor for `response.data` events (tool calls, UI updates)

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
    model: str = "openai:gpt-5-mini",
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
- `model`: Model name (e.g., "openai:gpt-5-mini", "anthropic:claude-3-5-sonnet")
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
    model="openai:gpt-5-mini",
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

## Evaluation

### CriteriaJudge

```python
from layercode_gym import CriteriaJudge
```

LLM-as-judge for evaluating conversations against pass/fail criteria.

#### Constructor

```python
CriteriaJudge(
    criteria: Sequence[str],
    *,
    additional_context: str | None = None,
    model: str = "openai:gpt-5-mini"
)
```

**Parameters:**

- `criteria`: List of evaluation criteria as true/false questions
- `additional_context`: Optional context about the conversation's purpose
- `model`: LLM model for evaluation (use `gpt-5` for production accuracy)

#### Methods

##### evaluate()

```python
async def evaluate(log: ConversationLog) -> JudgeOutput
```

Evaluate a conversation against the defined criteria.

##### save_results()

```python
def save_results(output: JudgeOutput, conversation_id: str, output_root: Path) -> Path
```

Save evaluation results to `judge_evaluation.json` in the conversation folder.

**Example:**

```python
judge = CriteriaJudge(
    criteria=[
        "Did the agent answer the user's question?",
        "Was the agent polite?"
    ],
    # Note: gpt-5-mini is fast/cheap; use gpt-5 for production
    model="openai:gpt-5-mini"
)

async def on_end(log):
    result = await judge.evaluate(log)
    judge.save_results(result, log.conversation_id, settings.output_root)

client = LayercodeClient(
    simulator=simulator,
    conversation_callback=on_end
)
```

### JudgeOutput

```python
from layercode_gym import JudgeOutput
```

Structured output from CriteriaJudge.

**Attributes:**

- `reasoning: str` - Explanation of the evaluation
- `criteria_results: list[dict]` - Per-criterion results: `[{"criterion_id": 1, "passed": true}, ...]`
- `overall_pass: bool` - True only if ALL criteria passed

---

## Callbacks

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

### ResponseDataProcessor

```python
from layercode_gym import ResponseDataProcessor
```

Protocol for processing `response.data` events into text for AI context.

When the voice agent emits `response.data` events (tool calls, UI updates), this processor converts the raw data into human-readable text that the AI user simulator can "see" and react to.

#### Methods

##### \_\_call\_\_()

```python
def __call__(self, data: dict[str, Any]) -> str
```

Convert a response.data payload to text.

**Parameters:**

- `data: dict` - The raw data dictionary from response.data event

**Returns:** `str` - Human-readable description (empty string to skip)

**Example:**

```python
from typing import Any
from layercode_gym import ResponseDataProcessor

class ProductProcessor(ResponseDataProcessor):
    def __call__(self, data: dict[str, Any]) -> str:
        if data.get("tool") == "search_products":
            products = data.get("products", [])
            return f"[DISPLAYED: {len(products)} products]"
        return ""

client = LayercodeClient(
    simulator=simulator,
    data_processor=ProductProcessor()
)
```

**Built-in processors:**

```python
from layercode_gym import default_data_processor, XMLDataProcessor

# Default: formats data as XML (LLM-friendly)
client = LayercodeClient(data_processor=default_data_processor)

# Configurable XML processor
processor = XMLDataProcessor(root_tag="tool_result")
client = LayercodeClient(data_processor=processor)
```

---

## Data Models

### UserRequest

```python
from layercode_gym.simulator import UserRequest
```

Request data passed to user simulator.

**Attributes:**

- `conversation_id: str` - Unique conversation ID
- `turn_id: str | None` - Current turn identifier
- `text: str | None` - Full accumulated text from assistant (all content since last user response)
- `data: Sequence[dict]` - All accumulated `response.data` payloads from current turn
- `data_text: str | None` - Processed data as human-readable text (if data_processor set)
- `wait_context: WaitContext | None` - Context about waits during this turn (None if no waits yet)

### UserResponse

```python
from layercode_gym.simulator import UserResponse
```

Response from user simulator.

**Attributes:**

- `text: str | None` - User message text
- `audio_path: Path | None` - Optional path to audio file
- `data: Sequence[dict]` - Data payloads to send
- `wait_seconds: float | None` - If set, skip this turn and wait (2-300 seconds)

**Properties:**

- `has_payload: bool` - True if response has content to send
- `is_wait: bool` - True if this is a wait response

### WaitContext

```python
from layercode_gym.simulator import WaitContext
```

Context about waiting during the current assistant turn. Used by AI agent simulators to track wait state and make informed decisions.

**Attributes:**

- `wait_count: int` - Number of times we've waited during this turn
- `total_wait_seconds: float` - Total seconds waited during this turn
- `last_text_len: int` - Text length at last wait (to detect new content)

**Methods:**

- `record_wait(wait_seconds, current_text_len)` - Record a wait event
- `has_new_content(current_text_len) -> bool` - Check if new content arrived since last wait
- `reset()` - Reset context for new turn

### WaitForAssistant

```python
from layercode_gym.simulator import WaitForAssistant
```

Signal from AI agent to wait for the assistant to finish before responding. Use when the assistant says "please wait", "processing...", or gives a time estimate.

**Attributes:**

- `wait_seconds: float` - How long to wait (2-300 seconds). Add ~20% buffer to assistant's estimate.
- `reason: str | None` - Optional reason for waiting (for debugging/logging)

**Example:**

```python
WaitForAssistant(wait_seconds=10, reason="Assistant said processing takes ~8 seconds")
```

### RespondToAssistant

```python
from layercode_gym.simulator import RespondToAssistant
```

Signal from AI agent to send a message to the assistant.

**Attributes:**

- `message: str` - The message to send

**Example:**

```python
RespondToAssistant(message="Yes, I'd like to proceed with the order.")
```

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
    UserResponse,
    WaitContext,
    WaitForAssistant,
    RespondToAssistant
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
