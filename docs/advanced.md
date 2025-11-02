# Advanced Usage

Advanced features and customization options for power users.

## LogFire Integration

LayerCode Gym integrates with [LogFire](https://logfire.pydantic.dev/) for real-time observability and debugging.

### Setup

```bash
# Install LogFire dependencies (already included in layercode-gym)
uv add logfire

# Configure LogFire
logfire configure
```

### Enable in LayerCode Gym

LogFire is automatically enabled when you provide a `LOGFIRE_TOKEN`:

```bash
export LOGFIRE_TOKEN="your_token_here"
```

LayerCode Gym automatically instruments PydanticAI and OpenAI when a LogFire token is present.

### What You Get

With LogFire enabled, you get:

- Real-time conversation tracking in the LogFire UI
- Performance metrics and spans for each operation
- WebSocket event streaming visualization
- Error tracking and stack traces
- Timeline view of conversation flow

### View in LogFire Dashboard

```bash
# Start LogFire UI
logfire view

# Or visit https://logfire.pydantic.dev
```

You'll see:

- Conversation spans with nested operations
- WebSocket events (connect, message, disconnect)
- TTS synthesis operations
- LLM API calls (for AI personas)
- Timing metrics for each operation

### Custom LogFire Spans

Add your own instrumentation:

```python
import logfire

async def my_custom_callback(
    turn_number: int,
    user_message: str,
    agent_message: str,
    conversation_id: str
) -> None:
    with logfire.span("custom_analysis"):
        # Your analysis code
        sentiment = analyze_sentiment(agent_message)
        logfire.info(
            "Sentiment analysis",
            turn=turn_number,
            sentiment=sentiment
        )

client = LayercodeClient(
    simulator=simulator,
    turn_callback=my_custom_callback
)
```

---

## Custom TTS Engines

Use alternative TTS providers like ElevenLabs, Azure, or local engines.

### ElevenLabs Example

```python
from pathlib import Path
import httpx
from layercode_gym.simulator import TTSEngineProtocol

class ElevenLabsTTS(TTSEngineProtocol):
    def __init__(self, api_key: str, voice_id: str):
        self.api_key = api_key
        self.voice_id = voice_id
        self.base_url = "https://api.elevenlabs.io/v1"

    async def synthesize(self, text: str, **kwargs) -> Path:
        url = f"{self.base_url}/text-to-speech/{self.voice_id}"
        headers = {"xi-api-key": self.api_key}
        data = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=data)
            response.raise_for_status()

        # Save audio
        output_path = Path(f"tts_{hash(text)}.mp3")
        output_path.write_bytes(response.content)

        return output_path

# Use it
tts = ElevenLabsTTS(
    api_key="your_elevenlabs_key",
    voice_id="your_voice_id"
)

simulator = UserSimulator.from_text(
    messages=["Hello!", "How are you?"],
    send_as_text=False,
    tts_engine=tts
)
```

### Azure TTS Example

```python
import azure.cognitiveservices.speech as speechsdk
from pathlib import Path
from layercode_gym.simulator import TTSEngineProtocol

class AzureTTS(TTSEngineProtocol):
    def __init__(self, subscription_key: str, region: str):
        self.speech_config = speechsdk.SpeechConfig(
            subscription=subscription_key,
            region=region
        )
        self.speech_config.speech_synthesis_voice_name = "en-US-JennyNeural"

    async def synthesize(self, text: str, **kwargs) -> Path:
        output_path = Path(f"tts_{hash(text)}.wav")

        audio_config = speechsdk.audio.AudioOutputConfig(
            filename=str(output_path)
        )

        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=self.speech_config,
            audio_config=audio_config
        )

        result = synthesizer.speak_text_async(text).get()

        if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
            raise Exception(f"TTS failed: {result.reason}")

        return output_path
```

---

## Custom LLM Providers

LayerCode Gym uses PydanticAI, which supports many LLM providers.

### Anthropic Claude

```python
from layercode_gym import UserSimulator, Persona

simulator = UserSimulator.from_agent(
    persona=Persona(
        background_context="You are a technical user",
        intent="You want detailed information"
    ),
    model="anthropic:claude-3-5-sonnet",  # Use Claude
    max_turns=5
)
```

### Local Models (Ollama)

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model
ollama pull llama3
```

```python
simulator = UserSimulator.from_agent(
    persona=Persona(
        background_context="You are a casual user",
        intent="You want simple answers"
    ),
    model="ollama:llama3",  # Use local model
    max_turns=5
)
```

### Google Gemini

```python
simulator = UserSimulator.from_agent(
    persona=Persona(
        background_context="You are a researcher",
        intent="You want comprehensive information"
    ),
    model="gemini:gemini-1.5-pro",  # Use Gemini
    max_turns=5
)
```

### Custom PydanticAI Agent

For full control, create a custom agent:

```python
from pydantic_ai import Agent
from layercode_gym import UserSimulator

# Define dependencies
class ConversationDeps:
    def __init__(self):
        self.history = []

    def add_message(self, role: str, content: str):
        self.history.append({"role": role, "content": content})

# Create custom agent
agent = Agent(
    "openai:gpt-4o",
    system_prompt="""
    You are simulating a frustrated customer who has been on hold
    for 30 minutes. You are impatient and want quick resolution.
    """,
    deps_type=ConversationDeps
)

# Use it
deps = ConversationDeps()
simulator = UserSimulator.from_agent(
    agent=agent,
    deps=deps,
    max_turns=5
)
```

---

## Audio Processing

### Background Noise Injection

Add realistic background noise to test transcription:

```python
from pydub import AudioSegment
from pydub.generators import WhiteNoise
from pathlib import Path

def add_background_noise(
    audio_path: Path,
    noise_level: float = 0.1
) -> Path:
    # Load audio
    audio = AudioSegment.from_wav(audio_path)

    # Generate white noise
    noise = WhiteNoise().to_audio_segment(
        duration=len(audio),
        volume=noise_level
    )

    # Mix audio with noise
    mixed = audio.overlay(noise)

    # Save
    output_path = audio_path.parent / f"{audio_path.stem}_noisy.wav"
    mixed.export(output_path, format="wav")

    return output_path

# Use in simulator
from layercode_gym import UserSimulator

# Generate noisy versions of audio files
noisy_files = [
    add_background_noise(Path("audio/msg1.wav")),
    add_background_noise(Path("audio/msg2.wav"))
]

simulator = UserSimulator.from_files(files=noisy_files)
```

### Speed Variation

Test with different speaking speeds:

```python
from pydub import AudioSegment
from pydub.playback import play

def change_speed(audio_path: Path, speed: float = 1.0) -> Path:
    # speed > 1.0 = faster, speed < 1.0 = slower
    audio = AudioSegment.from_wav(audio_path)

    # Change frame rate
    sound_with_altered_frame_rate = audio._spawn(
        audio.raw_data,
        overrides={"frame_rate": int(audio.frame_rate * speed)}
    )

    # Convert back to original frame rate
    return sound_with_altered_frame_rate.set_frame_rate(audio.frame_rate)
```

---

## Batch Processing Patterns

### Parallel Processing with Resource Limits

```python
import asyncio
from layercode_gym import LayercodeClient, UserSimulator

async def run_with_semaphore(
    message: str,
    semaphore: asyncio.Semaphore
) -> str:
    async with semaphore:
        simulator = UserSimulator.from_text(
            messages=[message],
            send_as_text=True
        )
        client = LayercodeClient(simulator=simulator)
        return await client.run()

async def main():
    # Limit to 10 concurrent conversations
    semaphore = asyncio.Semaphore(10)

    scenarios = ["Message " + str(i) for i in range(100)]
    tasks = [
        run_with_semaphore(msg, semaphore)
        for msg in scenarios
    ]

    results = await asyncio.gather(*tasks)
    print(f"Completed {len(results)} conversations")

asyncio.run(main())
```

### Retry Logic

```python
import asyncio
from typing import Optional

async def run_with_retry(
    simulator: UserSimulatorProtocol,
    max_retries: int = 3
) -> Optional[str]:
    for attempt in range(max_retries):
        try:
            client = LayercodeClient(simulator=simulator)
            return await client.run()
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"Failed after {max_retries} attempts: {e}")
                return None
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

### Progress Tracking

```python
from tqdm import tqdm
import asyncio

async def run_with_progress(scenarios: list[str]):
    results = []

    with tqdm(total=len(scenarios), desc="Running conversations") as pbar:
        for scenario in scenarios:
            simulator = UserSimulator.from_text(
                messages=[scenario],
                send_as_text=True
            )
            client = LayercodeClient(simulator=simulator)
            conv_id = await client.run()
            results.append(conv_id)
            pbar.update(1)

    return results
```

---

## Evaluation Frameworks

### Custom Scoring System

```python
from layercode_gym.models import ConversationLog
from typing import Dict

class ConversationScorer:
    def __init__(self):
        self.scores: Dict[str, float] = {}

    async def score_conversation(
        self,
        log: ConversationLog
    ) -> float:
        score = 0.0

        # Score based on duration (prefer shorter)
        if log.stats["duration_seconds"] < 60:
            score += 2.0
        elif log.stats["duration_seconds"] < 120:
            score += 1.0

        # Score based on latency
        if log.stats["avg_latency_ms"] < 500:
            score += 2.0
        elif log.stats["avg_latency_ms"] < 1000:
            score += 1.0

        # Score based on turn count
        if log.stats["total_turns"] >= 3:
            score += 1.0

        return score

# Use it
scorer = ConversationScorer()

async def evaluate_callback(log: ConversationLog) -> None:
    score = await scorer.score_conversation(log)
    print(f"Conversation {log.conversation_id} scored: {score}/5.0")

client = LayercodeClient(
    simulator=simulator,
    conversation_callback=evaluate_callback
)
```

### A/B Testing

```python
from enum import Enum
from typing import List
import statistics

class AgentVersion(Enum):
    V1 = "agent_v1_id"
    V2 = "agent_v2_id"

async def ab_test(
    scenarios: List[str],
    num_runs_per_version: int = 10
):
    results = {AgentVersion.V1: [], AgentVersion.V2: []}

    for version in AgentVersion:
        settings = Settings(
            server_url="http://localhost:8001",
            agent_id=version.value
        )

        for scenario in scenarios[:num_runs_per_version]:
            simulator = UserSimulator.from_text(
                messages=[scenario],
                send_as_text=True
            )

            client = LayercodeClient(
                simulator=simulator,
                settings=settings
            )

            conv_id = await client.run()

            # Collect metrics
            # ... analyze conversation ...

            results[version].append(conv_id)

    # Compare results
    print("A/B Test Results:")
    for version, conv_ids in results.items():
        print(f"{version.name}: {len(conv_ids)} conversations")
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Voice Agent Tests

on:
  pull_request:
  push:
    branches: [main]

jobs:
  test-agent:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Install dependencies
        run: uv sync

      - name: Start backend server
        run: |
          uvx layercode-create-app run &
          sleep 5

      - name: Run tests
        env:
          SERVER_URL: http://localhost:8001
          LAYERCODE_AGENT_ID: ${{ secrets.AGENT_ID }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          python examples/01_text_messages.py
          python examples/05_batch_evaluation.py

      - name: Upload results
        uses: actions/upload-artifact@v4
        with:
          name: conversation-logs
          path: conversations/
```

---

## Performance Optimization

### Reuse WebSocket Connections

For high-volume testing, consider connection pooling (advanced, requires modification):

```python
# This is a conceptual example - would require changes to core client
class ClientPool:
    def __init__(self, pool_size: int = 10):
        self.pool_size = pool_size
        self.clients = []

    async def get_client(self) -> LayercodeClient:
        # Return a client from the pool
        # This would require refactoring LayercodeClient
        pass
```

### Disable Audio File Saving

If you only need metrics:

```python
# Modify storage settings (conceptual - would need implementation)
settings = Settings(
    server_url="http://localhost:8001",
    agent_id="your_agent_id",
    save_audio=False  # Don't save audio files
)
```

### Use Text Mode

For maximum speed:

```python
simulator = UserSimulator.from_text(
    messages=["Hello!"],
    send_as_text=True  # Fastest mode
)
```

---

## Next Steps

- [API Reference](api-reference.md) - Full API documentation
- [Examples](examples.md) - Practical usage examples
- [Roadmap](roadmap.md) - Upcoming features
