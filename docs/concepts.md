# Core Concepts

Understanding these core concepts will help you get the most out of LayerCode Gym.

## Architecture Overview

LayerCode Gym sits between your test code and the Layercode platform, simulating real voice clients.

```
┌──────────────┐     ┌─────────────────┐     ┌──────────────┐
│  Your Test   │────▶│  LayerCode Gym  │────▶│ Your Backend │
│    Code      │     │     Client      │     │    Server    │
└──────────────┘     └─────────────────┘     └──────────────┘
                              │                       │
                              │                       ▼
                              │                ┌──────────────┐
                              └───────────────▶│  Layercode   │
                                               │   Platform   │
                                               └──────────────┘
```

### Authorization Flow

1. **Test code** creates a `LayercodeClient` with a `UserSimulator`
2. **Client** requests authorization from YOUR backend server (`SERVER_URL`)
3. **Backend** returns a `client_session_key` from Layercode
4. **Client** connects to Layercode WebSocket using that key
5. **Conversation** proceeds with the UserSimulator providing responses

The client never hits Layercode's API directly - it always goes through your backend first.

## User Simulators

The `UserSimulator` is the heart of LayerCode Gym. It generates user responses during conversations.

### Three Factory Methods

#### 1. from_text() - Fixed Messages

Best for regression testing and fast iteration:

```python
from layercode_gym import UserSimulator

simulator = UserSimulator.from_text(
    messages=[
        "Hello! I'm interested in your services.",
        "Tell me more about pricing.",
        "Thank you, goodbye."
    ],
    send_as_text=True  # Fast mode - no TTS needed
)
```

**When to use:**
- Regression testing with known scenarios
- Quick debugging of conversation flow
- Testing specific edge cases
- CI/CD pipelines (fastest execution)

#### 2. from_files() - Pre-recorded Audio

Best for testing transcription and audio handling:

```python
from pathlib import Path

simulator = UserSimulator.from_files(
    files=[
        Path("audio/intro.wav"),
        Path("audio/question.wav"),
        Path("audio/goodbye.wav")
    ]
)
```

**When to use:**
- Testing transcription accuracy
- Stress testing with various audio qualities
- Testing different accents and speaking styles
- Testing background noise handling

#### 3. from_agent() - AI-Driven Personas

Best for realistic, dynamic conversations:

```python
from layercode_gym import Persona

persona = Persona(
    background_context="You are a 35-year-old small business owner",
    intent="You want to understand pricing and features"
)

simulator = UserSimulator.from_agent(
    persona=persona,
    model="openai:gpt-5-mini",  # or "anthropic:claude-3-5-sonnet"
    max_turns=5,
    send_as_text=False  # Auto-creates TTS engine
)
```

**When to use:**
- Simulating realistic user behavior
- Testing conversation flow and context handling
- Exploratory testing of edge cases
- Evaluating agent personality and tone

### Wait Handling for AI Agents

When testing voice agents that perform long-running operations (API calls, database queries, file processing), the AI simulator needs to wait intelligently rather than responding immediately.

**How it works:**

1. Assistant says "Please wait while I process that..." or "This takes about 10 seconds..."
2. AI simulator returns `WaitForAssistant(wait_seconds=12)` instead of responding
3. System waits, then re-invokes the simulator with the updated assistant message
4. Simulator sees the full accumulated message and decides: wait more or respond

**The `WaitContext`:**

When waits occur, the simulator receives context about its waiting history:

```python
# In your custom simulator or agent
def handle_request(request: UserRequest):
    if request.wait_context:
        print(f"Waited {request.wait_context.wait_count} times")
        print(f"Total wait: {request.wait_context.total_wait_seconds}s")

        if request.wait_context.has_new_content(len(request.text or "")):
            print("New content arrived since last wait!")
```

**When to wait vs respond:**

| Wait when... | Respond when... |
|--------------|-----------------|
| "Please wait", "one moment" | Results delivered |
| "Processing...", "Loading..." | Question asked to you |
| Time estimate given ("~10 seconds") | Task completed |
| Clearly still working | Information you can act on |

**Built-in safety:**

- Maximum wait time: 300 seconds per wait
- Maximum consecutive waits: configurable (prevents infinite loops)
- Minimum wait: 2 seconds

### TTS Auto-Creation

When using `send_as_text=False`, LayerCode Gym automatically creates an OpenAI TTS engine:

```python
# This works out of the box
simulator = UserSimulator.from_text(
    messages=["Hello!"],
    send_as_text=False  # TTS engine auto-created
)
```

Configure via environment variables:

```bash
export OPENAI_TTS_MODEL="gpt-4o-mini-tts"
export OPENAI_TTS_VOICE="coral"  # alloy, echo, fable, onyx, nova, shimmer, coral
export OPENAI_TTS_INSTRUCTIONS="Speak slowly and clearly"
```

Or pass custom settings:

```python
from layercode_gym import Settings

settings = Settings(
    tts_model="gpt-4o-mini-tts",
    tts_voice="alloy",
    tts_instructions="Speak with a British accent"
)

simulator = UserSimulator.from_text(
    messages=["Hello!"],
    send_as_text=False,
    settings=settings
)
```

### Custom Simulators

For full control, implement the `UserSimulatorProtocol`:

```python
from layercode_gym.simulator import (
    UserSimulatorProtocol,
    UserRequest,
    UserResponse
)

class MyCustomSimulator(UserSimulatorProtocol):
    async def get_response(
        self,
        request: UserRequest
    ) -> UserResponse | None:
        # Your custom logic here
        # - request.agent_transcript: list of agent messages so far
        # - request.turn_number: current turn
        # - request.conversation_id: unique ID

        if request.turn_number > 5:
            return None  # End conversation

        return UserResponse(
            text="Custom response based on context",
            audio_path=None,  # or Path to audio file
            data=()  # optional additional data
        )
```

## Callbacks

Callbacks allow you to hook into the conversation lifecycle for monitoring, evaluation, and custom logic.

### Turn Callbacks

Called after each conversation turn:

```python
from layercode_gym.callbacks import TurnCallback

async def my_turn_callback(
    turn_number: int,
    user_message: str,
    agent_message: str,
    conversation_id: str
) -> None:
    print(f"Turn {turn_number}:")
    print(f"  User: {user_message}")
    print(f"  Agent: {agent_message}")

client = LayercodeClient(
    simulator=simulator,
    turn_callback=my_turn_callback
)
```

### Conversation Callbacks

Called once at the end of the conversation:

```python
from layercode_gym.callbacks import ConversationCallback
from layercode_gym.models import ConversationLog

async def my_conversation_callback(
    conversation_log: ConversationLog
) -> None:
    stats = conversation_log.stats
    print(f"Conversation complete!")
    print(f"  Total turns: {stats['total_turns']}")
    print(f"  Duration: {stats['duration_seconds']}s")
    print(f"  Avg latency: {stats['avg_latency_ms']}ms")

client = LayercodeClient(
    simulator=simulator,
    conversation_callback=my_conversation_callback
)
```

### CriteriaJudge

Built-in judge for automated pass/fail evaluation against criteria:

```python
from layercode_gym import CriteriaJudge, Settings

judge = CriteriaJudge(
    criteria=[
        "Did the agent answer all user questions?",
        "Was the agent polite and professional?",
        "Did the conversation flow naturally?"
    ],
    # Note: gpt-5-mini is fast/cheap for testing; use gpt-5 for production
    model="openai:gpt-5-mini"
)

async def conversation_callback(log):
    result = await judge.evaluate(log)
    print(f"Overall: {'PASS' if result.overall_pass else 'FAIL'}")
    judge.save_results(result, log.conversation_id, Settings.load().output_root)

client = LayercodeClient(
    simulator=simulator,
    conversation_callback=conversation_callback
)
```

Results are saved to `conversations/<id>/judge_evaluation.json` with full metadata:

```json
{
  "schema_version": "1.0",
  "evaluated_at": "2025-12-05T13:15:41.124793+00:00",
  "model": "openai:gpt-5-mini",
  "criteria": [
    {"id": 1, "criterion": "Did the agent answer all user questions?"},
    {"id": 2, "criterion": "Was the agent polite and professional?"},
    {"id": 3, "criterion": "Did the conversation flow naturally?"}
  ],
  "additional_context": "Optional context about the scenario",
  "judgment": {
    "criteria_results": [
      {"criterion_id": 1, "passed": true},
      {"criterion_id": 2, "passed": true},
      {"criterion_id": 3, "passed": false}
    ],
    "overall_pass": false,
    "reasoning": "The agent answered questions well but responses felt scripted..."
  },
  "results_summary": [
    {"id": 1, "criterion": "Did the agent answer all user questions?", "passed": true},
    {"id": 2, "criterion": "Was the agent polite and professional?", "passed": true},
    {"id": 3, "criterion": "Did the conversation flow naturally?", "passed": false}
  ]
}
```

The file includes the model used, timestamp, original criteria, and both raw judgment output and a combined summary for easy reading.

## Conversation Outputs

After each conversation, LayerCode Gym creates a structured output directory:

```
conversations/<conversation_id>/
├── transcript.json          # Full conversation log with stats
├── conversation_mix.wav     # Combined audio (user + assistant)
├── user_0.wav              # Individual user audio files
├── user_1.wav
├── assistant_0.wav         # Individual assistant audio files
├── assistant_1.wav
└── judge_evaluation.json   # If using CriteriaJudge
```

### Transcript Structure

```json
{
  "conversation_id": "conv_abc123",
  "agent_id": "your_agent_id",
  "started_at": "2025-01-15T10:30:00Z",
  "ended_at": "2025-01-15T10:32:15Z",
  "turns": [
    {
      "turn_number": 0,
      "user_message": {
        "text": "Hello!",
        "timestamp": "2025-01-15T10:30:00Z",
        "audio_path": "user_0.wav"
      },
      "agent_message": {
        "text": "Hi there! How can I help you?",
        "timestamp": "2025-01-15T10:30:01.234Z",
        "audio_path": "assistant_0.wav",
        "ttfab_ms": 234
      }
    }
  ],
  "stats": {
    "total_turns": 3,
    "duration_seconds": 135.5,
    "avg_latency_ms": 245,
    "avg_ttfab_ms": 234,
    "total_user_words": 45,
    "total_agent_words": 123
  }
}
```

### Key Metrics

- **TTFAB (Time To First Audio Byte)**: How long until the agent starts speaking
- **Latency**: Total time from user message to agent response
- **Turn count**: Number of back-and-forth exchanges
- **Duration**: Total conversation length

## Settings and Configuration

All configuration is managed through the `Settings` class:

```python
from layercode_gym import Settings

settings = Settings(
    # Required
    server_url="http://localhost:8001",
    agent_id="your_agent_id",

    # TTS Configuration
    tts_model="gpt-4o-mini-tts",
    tts_voice="coral",
    tts_instructions="Speak clearly",

    # Audio Chunking
    chunk_ms=100,
    chunk_interval=0.0,

    # Storage
    output_root="./conversations"
)

# Use in client
client = LayercodeClient(
    simulator=simulator,
    settings=settings
)
```

Settings can also be loaded from environment variables (see [Getting Started](getting-started.md#configuration)).

## Next Steps

- [Examples](examples.md) - See detailed code examples
- [API Reference](api-reference.md) - Full API documentation
- [Advanced Usage](advanced.md) - Custom implementations and LogFire integration
