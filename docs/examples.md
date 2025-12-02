# Examples

This guide walks through all the examples in the `examples/` directory with detailed explanations.

## Example 01: Text Messages

The simplest and fastest way to test your agent.

**File:** `examples/01_text_messages.py`

```python
import asyncio
from layercode_gym import LayercodeClient, UserSimulator

async def main():
    # Create simulator with fixed text messages
    simulator = UserSimulator.from_text(
        messages=[
            "Hello! I'm interested in your services.",
            "Can you tell me more about pricing?",
            "What's included in the basic plan?",
            "Thank you, that's helpful. Goodbye."
        ],
        send_as_text=True  # Fast mode - no TTS needed
    )

    # Create client and run
    client = LayercodeClient(simulator=simulator)
    conversation_id = await client.run()

    print(f"Conversation ID: {conversation_id}")

if __name__ == "__main__":
    asyncio.run(main())
```

**Run it:**
```bash
python examples/01_text_messages.py
```

**Use cases:**
- Regression testing with known scenarios
- Quick debugging during development
- CI/CD pipelines (fastest execution)
- Testing specific edge cases

## Example 02: Audio Files

Test how your agent handles real audio with background noise, accents, etc.

**File:** `examples/02_audio_file.py`

```python
import asyncio
from pathlib import Path
from layercode_gym import LayercodeClient, UserSimulator

async def main():
    # Create simulator with pre-recorded audio files
    simulator = UserSimulator.from_files(
        files=[
            Path("audio/greeting.wav"),
            Path("audio/pricing_question.wav"),
            Path("audio/followup.wav"),
            Path("audio/goodbye.wav")
        ]
    )

    client = LayercodeClient(simulator=simulator)
    conversation_id = await client.run()

    print(f"Conversation ID: {conversation_id}")

if __name__ == "__main__":
    asyncio.run(main())
```

**Recording audio files:**

You can create test audio files using:

- Your computer's voice recorder
- Text-to-speech tools (OpenAI TTS, ElevenLabs, etc.)
- Real user recordings (with permission)

**Audio requirements:**

- Format: WAV recommended (MP3 also supported)
- Sample rate: 16kHz or 24kHz recommended
- Mono or stereo

**Use cases:**
- Testing transcription accuracy
- Stress testing with various audio qualities
- Testing different accents and speaking styles
- Testing background noise handling

## Example 03: AI Agent Persona

Simulate realistic users with dynamic responses.

**File:** `examples/03_agent_persona.py`

```python
import asyncio
from layercode_gym import LayercodeClient, UserSimulator, Persona

async def main():
    # Define a persona
    persona = Persona(
        background_context="""
        You are Sarah, a 35-year-old small business owner who runs a
        local bakery. You're tech-savvy but busy and appreciate clear,
        concise information.
        """,
        intent="""
        You want to understand if this service can help you manage
        customer orders more efficiently. You're particularly interested
        in pricing and ease of use.
        """
    )

    # Create AI-driven simulator
    simulator = UserSimulator.from_agent(
        persona=persona,
        model="openai:gpt-5-mini",  # Fast and cost-effective
        max_turns=6,
        send_as_text=False  # Use TTS for realistic audio
    )

    client = LayercodeClient(simulator=simulator)
    conversation_id = await client.run()

    print(f"Conversation ID: {conversation_id}")

if __name__ == "__main__":
    asyncio.run(main())
```

**Persona tips:**

- Be specific about background and goals
- Include personality traits (patient, impatient, technical, non-technical)
- Specify constraints (budget-conscious, time-sensitive, etc.)
- Add emotional context when relevant

**Model options:**

```python
# OpenAI (fast, cost-effective)
model="openai:gpt-5-mini"

# Anthropic (higher quality, more expensive)
model="anthropic:claude-3-5-sonnet"

# Local (free, requires Ollama)
model="ollama:llama3"

# Google (alternative)
model="gemini:gemini-1.5-pro"
```

**Use cases:**
- Simulating realistic user behavior
- Testing conversation flow and context
- Exploratory testing
- Training data generation

## Example 04: CriteriaJudge Evaluation

Automatically evaluate conversation quality with pass/fail criteria.

**File:** `examples/04_callbacks_judge.py`

```python
import asyncio
from layercode_gym import CriteriaJudge, LayercodeClient, Settings, UserSimulator

async def main():
    settings = Settings.load()

    # Create judge with true/false criteria
    judge = CriteriaJudge(
        criteria=[
            "Did the agent understand the user's problem?",
            "Did the agent provide clear next steps?",
            "Was the agent polite and professional?",
        ],
        # Note: gpt-5-mini is fast/cheap for testing; use gpt-5 for production
        model="openai:gpt-5-mini"
    )

    async def on_end(log):
        result = await judge.evaluate(log)
        print(f"Overall: {'PASS' if result.overall_pass else 'FAIL'}")
        print(f"Reasoning: {result.reasoning}")
        judge.save_results(result, log.conversation_id, settings.output_root)

    simulator = UserSimulator.from_text(
        messages=["Hello!", "I need help.", "Thanks!"],
        send_as_text=True
    )

    client = LayercodeClient(
        simulator=simulator,
        settings=settings,
        conversation_callback=on_end
    )
    await client.run()

if __name__ == "__main__":
    asyncio.run(main())
```

**Judge results:**

After the conversation, check `conversations/<id>/judge_evaluation.json`:

```json
{
  "criteria": [
    {"id": 1, "criterion": "Did the agent understand the user's problem?", "passed": true},
    {"id": 2, "criterion": "Did the agent provide clear next steps?", "passed": true},
    {"id": 3, "criterion": "Was the agent polite and professional?", "passed": true}
  ],
  "overall_pass": true,
  "reasoning": "The agent correctly identified the issue and provided helpful guidance..."
}
```

**Best practices:**

- Write criteria as yes/no questions that can be objectively answered
- Use `gpt-5-mini` for fast iteration, `gpt-5` for production
- Add `additional_context` to explain the scenario being tested
- Review reasoning to understand failures

**Use cases:**
- Automated quality assurance
- A/B testing different agent configurations
- Regression testing with known criteria
- Prompt compliance verification

## Example 05: Batch Evaluation

Run multiple conversations concurrently for scale testing.

**File:** `examples/05_batch_evaluation.py`

```python
import asyncio
from tqdm.asyncio import tqdm_asyncio
from layercode_gym import LayercodeClient, UserSimulator

async def run_conversation(message: str) -> str:
    """Run a single conversation"""
    simulator = UserSimulator.from_text(
        messages=[message, "Tell me more.", "Thank you!"],
        send_as_text=True
    )

    client = LayercodeClient(simulator=simulator)
    return await client.run()

async def main():
    # Define test scenarios
    scenarios = [
        "Hello! I'm interested in learning about your services.",
        "Hi there! Can you help me with a question?",
        "Good morning! I'd like to know more about what you offer.",
        "Hey! I saw your ad and wanted to learn more.",
        "Hi! A friend recommended your service.",
        "Hello! I need help with something.",
        "Hi! I'm looking for a solution to my problem.",
        "Good afternoon! I have a few questions.",
        "Hey there! Can you tell me about pricing?",
        "Hi! I'm interested in signing up.",
    ]

    # Create tasks for all scenarios
    tasks = [run_conversation(msg) for msg in scenarios]

    # Run all conversations concurrently with progress bar
    results = await tqdm_asyncio.gather(
        *tasks,
        desc="Running conversations"
    )

    print(f"\nCompleted {len(results)} conversations:")
    for i, conv_id in enumerate(results, 1):
        print(f"  {i}. {conv_id}")

if __name__ == "__main__":
    asyncio.run(main())
```

**Run it:**
```bash
python examples/05_batch_evaluation.py
```

**Output:**
```
Running conversations: 100%|██████████| 10/10 [00:15<00:00,  1.53s/it]

Completed 10 conversations:
  1. conv_abc123
  2. conv_def456
  ...
```

**Analyzing batch results:**

```python
# After running, analyze all conversations
import json
from pathlib import Path

results = []
for conv_dir in Path("conversations").iterdir():
    if conv_dir.is_dir():
        with open(conv_dir / "transcript.json") as f:
            data = json.load(f)
            results.append({
                "id": data["conversation_id"],
                "turns": data["stats"]["total_turns"],
                "duration": data["stats"]["duration_seconds"],
                "avg_latency": data["stats"]["avg_latency_ms"]
            })

# Calculate aggregate stats
avg_latency = sum(r["avg_latency"] for r in results) / len(results)
print(f"Average latency across all conversations: {avg_latency}ms")
```

**Use cases:**
- Load testing your agent
- Regression testing multiple scenarios
- Gathering statistics across conversations
- Finding edge cases and failure modes

## Example 06: Custom Data Processor

Process `response.data` events (tool calls, UI updates) into text the AI simulator can "see".

**File:** `examples/06_outdoor_shop_eval.py`

```python
from typing import Any
from layercode_gym import LayercodeClient, CriteriaJudge

def product_data_processor(data: dict[str, Any]) -> str:
    """Convert response.data to human-readable text."""
    tool = data.get("tool", "")
    if tool == "search_products":
        products = data.get("payload", {}).get("products", [])
        names = [p.get("name") for p in products[:3]]
        return f"[SCREEN: Products shown: {', '.join(names)}]"
    return ""

client = LayercodeClient(
    simulator=simulator,
    data_processor=product_data_processor,  # AI sees tool results
)
```

**Use cases:**
- Let AI users react to displayed products/orders/data
- Test tool call rendering and UI updates
- Verify response.data streaming works correctly

## Example 07: Custom Judge with PydanticAI

Build your own judge with custom output types for domain-specific evaluation.

**File:** `examples/07_custom_judge.py`

```python
from pydantic import BaseModel, Field
from pydantic_ai import Agent

class MyEvaluation(BaseModel):
    greeted_user: bool = Field(description="Did assistant greet appropriately?")
    answered_questions: bool = Field(description="Were all questions answered?")
    summary: str = Field(description="Brief explanation")

# Note: gpt-5-mini is fast/cheap for testing; use gpt-5 for production
custom_judge = Agent(
    "openai:gpt-5-mini",
    output_type=MyEvaluation,
    system_prompt="Evaluate the assistant's performance strictly."
)

async def evaluate(log):
    transcript = "\n".join(
        f"[{i}] {t.assistant_message.content}"
        for i, t in enumerate(log.turns) if t.assistant_message
    )
    result = await custom_judge.run(f"Evaluate:\n{transcript}")
    return result.output
```

**When to use custom judges:**
- You need numerical scores instead of pass/fail
- Domain-specific output fields (e.g., `tone_score`, `accuracy_rating`)
- Complex evaluation logic beyond simple criteria

## Advanced Examples

### Custom Turn Callback

Monitor and log specific events:

```python
from layercode_gym.callbacks import TurnCallback

async def custom_callback(
    turn_number: int,
    user_message: str,
    agent_message: str,
    conversation_id: str
) -> None:
    # Check for specific keywords
    if "error" in agent_message.lower():
        print(f"⚠️  Agent mentioned error in turn {turn_number}")

    # Track conversation length
    if turn_number > 10:
        print(f"⚠️  Conversation exceeding 10 turns")

    # Custom logging
    with open("conversation_log.txt", "a") as f:
        f.write(f"{conversation_id} - Turn {turn_number}\n")
        f.write(f"User: {user_message}\n")
        f.write(f"Agent: {agent_message}\n\n")

client = LayercodeClient(
    simulator=simulator,
    turn_callback=custom_callback
)
```

### Custom TTS Engine

Use a different TTS provider:

```python
from pathlib import Path
from layercode_gym.simulator import TTSEngineProtocol

class ElevenLabsTTS(TTSEngineProtocol):
    def __init__(self, api_key: str, voice_id: str):
        self.api_key = api_key
        self.voice_id = voice_id

    async def synthesize(self, text: str, **kwargs) -> Path:
        # Call ElevenLabs API
        # ... implementation details ...
        return Path("generated_audio.wav")

# Use custom TTS
tts_engine = ElevenLabsTTS(api_key="...", voice_id="...")
simulator = UserSimulator.from_text(
    messages=["Hello!"],
    send_as_text=False,
    tts_engine=tts_engine
)
```

### Conditional Conversation Flow

End conversation based on agent response:

```python
from layercode_gym.simulator import UserSimulatorProtocol, UserRequest, UserResponse

class ConditionalSimulator(UserSimulatorProtocol):
    def __init__(self, max_turns: int = 5):
        self.max_turns = max_turns
        self.responses = [
            "Hello!",
            "Tell me more.",
            "That's interesting.",
            "Goodbye!"
        ]

    async def get_response(self, request: UserRequest) -> UserResponse | None:
        # End if agent said goodbye
        if request.agent_transcript:
            last_msg = request.agent_transcript[-1]
            if "goodbye" in last_msg.lower():
                return None

        # End after max turns
        if request.turn_number >= self.max_turns:
            return None

        # Return next response
        if request.turn_number < len(self.responses):
            return UserResponse(
                text=self.responses[request.turn_number],
                audio_path=None,
                data=()
            )

        return None
```

## Next Steps

- [API Reference](api-reference.md) - Detailed API documentation
- [Advanced Usage](advanced.md) - LogFire integration, custom implementations
- [Concepts](concepts.md) - Deep dive into architecture and design
