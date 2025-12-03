# LayerCode Gym

[![CI](https://github.com/svilupp/layercode-gym/actions/workflows/ci.yml/badge.svg)](https://github.com/svilupp/layercode-gym/actions/workflows/ci.yml)
[![Docs](https://github.com/svilupp/layercode-gym/actions/workflows/docs.yml/badge.svg)](https://github.com/svilupp/layercode-gym/actions/workflows/docs.yml)
[![Documentation](https://img.shields.io/badge/docs-latest-blue.svg)](https://svilupp.github.io/layercode-gym)

> **Warning (v0.1.0):** This toolkit is an early release and may contain bugs or breaking changes. Please test thoroughly before using in production.

A testing toolkit for voice AI agents built on [Layercode.com](https://layercode.com). Quickly spin up a testing environment to run through hundreds of scenarios and understand how your agent will perform in production.

**Note:** This is an unofficial, community-maintained project.

Perfect for regression testing, load testing, and automated evaluation of your voice AI agents.

## Features

- **Three User Simulator Types**: Fixed text, pre-recorded audio, or AI-driven personas
- **Captured Analytics**: Full transcripts with TTFAB, latency stats, and audio recordings
- **LogFire Integration**: Real-time observability and debugging
- **Batch Testing**: Run hundreds of conversations concurrently
- **CLI & Python API**: Quick testing via CLI or programmatic control, plus `api-agents` CLI to swap webhook URLs for CI
- **LLM-as-Judge**: Bring your own quality evaluation with customizable criteria as a conversational hook
- **GitHub Actions Integration**: Automated CI/CD testing with parallel persona execution

See `examples/` for reference!

## Quick Start

**Prerequisites:** Backend server configured in [Layercode dashboard](https://dash.layercode.com).

No server yet? Launch one quickly:
```bash
uvx layercode-create-app run --tunnel --unsafe-update-webhook
# Displays tunnel URL to enter in Layercode dashboard
```
!! Caution: `--unsafe-update-webhook` automatically updates the webhook URL in the Layercode dashboard!

### CLI Quick Test (No Installation)

```bash
# Set environment
export SERVER_URL="http://localhost:8001"
export LAYERCODE_AGENT_ID="your_agent_id"

# Run instantly with uvx (no installation)
uvx layercode-gym run --text "Hello, I need help with my account"

# Multiple messages
uvx layercode-gym run --text "Hi" --text "Tell me more" --text "Goodbye"

# Audio file
uvx layercode-gym run --file recording.wav

# AI agent with persona
uvx layercode-gym run --agent \
  --persona-background "You are a frustrated customer" \
  --persona-intent "Cancel your subscription"
```

Run `uvx layercode-gym --help` to see available commands, or `uvx layercode-gym run --help` for all run options.

### Manage Agent Webhooks (for CI)

```bash
# List all agents
uvx layercode-gym api-agents list

# Get agent details (use --json for full pipeline config)
uvx layercode-gym api-agents get --agent-id ag-123

# Update webhook URL (useful for PR testing)
uvx layercode-gym api-agents update --agent-id ag-123 --webhook-url https://pr-backend.com/webhook
```

### Python API

```bash
# Install
uv add layercode-gym

# Set environment
export SERVER_URL="http://localhost:8001"
export LAYERCODE_AGENT_ID="your_agent_id"
export OPENAI_API_KEY="sk-..."  # For TTS and AI personas
```

```python
from layercode_gym import LayercodeClient, UserSimulator

# Simple text messages
simulator = UserSimulator.from_text(
    messages=["Hello!", "Tell me about pricing", "Thank you"],
    send_as_text=True
)

client = LayercodeClient(simulator=simulator)
conversation_id = await client.run()
```

## Architecture

```
┌─────────────┐                    ┌──────────────┐
│  Your Test  │──1. Authorize──────▶│ Your Backend │
│    Code     │                     │   Server     │
└─────────────┘                     └──────────────┘
       │                                    │
       │                             2. Return
       │                           client_session_key
       │                                    │
       └──────3. Connect with key───────────┘
                      │
                      ▼
              ┌──────────────┐
              │  Layercode   │
              │   Platform   │
              └──────────────┘
```

**Flow:**
1. Client authorizes through YOUR backend server (`SERVER_URL`)
2. Backend returns `client_session_key` from LayerCode
3. Client connects to LayerCode WebSocket with that key

The client never hits LayerCode's API directly - it always goes through your backend first.

## User Simulators

Three types for different testing needs:

### 1. Fixed Text Messages
Fastest option, perfect for regression testing:
```python
simulator = UserSimulator.from_text(
    messages=["Hello", "Tell me more", "Goodbye"],
    send_as_text=True  # or False to use TTS
)
```

### 2. Pre-recorded Audio Files
Test transcription and audio handling:
```python
from pathlib import Path

simulator = UserSimulator.from_files(
    files=[Path("greeting.wav"), Path("question.wav")]
)
```

### 3. AI Agent Personas
Realistic, dynamic conversations using PydanticAI:
```python
from layercode_gym import Persona

simulator = UserSimulator.from_agent(
    persona=Persona(
        background_context="You are a 35-year-old small business owner",
        intent="You want to understand pricing and features"
    ),
    model="openai:gpt-5-mini",
    max_turns=5
)
```

## Examples

The `examples/` directory contains ready-to-run scripts:

- **01_text_messages.py** - Simple text conversation for quick testing
- **02_audio_file.py** - Stream pre-recorded audio to test transcription
- **03_agent_persona.py** - AI-driven user with dynamic responses
- **04_callbacks_judge.py** - CriteriaJudge for automated pass/fail evaluation
- **05_batch_evaluation.py** - Run multiple conversations concurrently
- **06_outdoor_shop_eval.py** - Custom data processor with domain-specific criteria
- **07_custom_judge.py** - Build your own judge with custom PydanticAI output types

Run any example:
```bash
python examples/01_text_messages.py
```

See [full documentation](https://svilupp.github.io/layercode-gym/examples) for detailed explanations.

## LLM-as-Judge Evaluation

Evaluate conversations against pass/fail criteria using `CriteriaJudge`:

```python
from layercode_gym import CriteriaJudge, LayercodeClient, Settings

judge = CriteriaJudge(
    criteria=[
        "Did the agent answer all user questions?",
        "Was the agent polite and professional?",
        "Did the conversation flow naturally?"
    ],
    # Note: gpt-5-mini is fast/cheap for testing; use gpt-5 for production
    model="openai:gpt-5-mini"
)

async def on_end(log):
    result = await judge.evaluate(log)
    print(f"Overall: {'PASS' if result.overall_pass else 'FAIL'}")
    judge.save_results(result, log.conversation_id, Settings.load().output_root)

client = LayercodeClient(
    simulator=simulator,
    conversation_callback=on_end
)
```

Results saved to `conversations/<id>/judge_evaluation.json` with reasoning and per-criterion pass/fail.

## Batch Testing

Run hundreds of conversations concurrently:

```python
import asyncio
from tqdm.asyncio import tqdm_asyncio

scenarios = ["Message 1", "Message 2", "Message 3"]
tasks = [run_conversation(msg) for msg in scenarios]

results = await tqdm_asyncio.gather(*tasks, desc="Running conversations")
```

See `examples/05_batch_evaluation.py` for the complete pattern.

## GitHub Actions CI/CD

Run automated tests in your CI pipeline with multiple personas in parallel:

```yaml
- uses: ./.github/actions/layercode-gym-test
  with:
    personas: |
      - background: You are a potential customer
        intent: Learn about pricing and features

      - background: You are a frustrated user
        intent: Get help with a problem
    judge-enabled: true
    judge-criteria: |
      - Did the agent provide clear and helpful responses?
    server-url: ${{ secrets.SERVER_URL }}
    layercode-agent-id: ${{ secrets.LAYERCODE_AGENT_ID }}
    openai-api-key: ${{ secrets.OPENAI_API_KEY }}
```

**Features:**
- Run multiple personas in parallel for maximum speed
- Automated quality evaluation with LLM judge
- Detailed artifacts with transcripts and audio recordings
- Optional LogFire observability integration

**Tip:** Use the `api-agents` CLI to update your agent's webhook URL for PR testing:
```bash
# Point agent to PR-specific backend before running tests
layercode-gym api-agents update --agent-id ag-123 --webhook-url https://pr-456.example.com/webhook

# Restore original after tests
layercode-gym api-agents update --agent-id ag-123 --webhook-url https://production.example.com/webhook
```

See [GitHub Actions documentation](docs/github-action.md) for complete setup guide, or [`api-agents` CLI docs](docs/api-agents.md) for webhook management.

## Conversation Outputs

After each conversation:

```
conversations/<conversation_id>/
├── transcript.json          # Full log with timing metrics
├── conversation_mix.wav     # Combined audio (user + assistant)
├── user_0.wav              # Individual user turns
├── assistant_0.wav         # Individual assistant turns
└── judge_evaluation.json   # CriteriaJudge results (if enabled)
```

Transcript includes TTFAB, latency stats, turn counts, and full message history.

## Custom Implementations

### Custom TTS Engine

```python
from layercode_gym.simulator import TTSEngineProtocol
from pathlib import Path

class MyTTSEngine(TTSEngineProtocol):
    async def synthesize(self, text: str, **kwargs) -> Path:
        # Your TTS service (ElevenLabs, Azure, etc.)
        return audio_file_path

simulator = UserSimulator.from_text(
    messages=["Hello!"],
    send_as_text=False,
    tts_engine=MyTTSEngine()
)
```

### Custom LLM for Agents

Use any LLM supported by PydanticAI. **Important:** You must define the system prompt with proper placeholders.

```python
from pydantic_ai import Agent
from textprompts import TextTemplates

# Load the required prompt template
templates = TextTemplates("src/layercode_gym/simulator/prompts")
system_prompt = templates.render(
    "basic_agent.txt",
    background_context="Your background",
    intent="Your intent"
)

# Create custom agent with proper system prompt
agent = Agent(
    "anthropic:claude-3-5-sonnet",
    system_prompt=system_prompt
)

simulator = UserSimulator.from_agent(agent=agent, deps=my_deps)
```

**Available models:**
- `openai:gpt-5` / `openai:gpt-5-mini`
- `anthropic:claude-3-5-sonnet`
- `ollama:llama3` (local)
- `gemini:gemini-1.5-pro`

**Prompt requirements:** The system prompt must include `{background_context}` and `{intent}` placeholders. See `src/layercode_gym/simulator/prompts/basic_agent.txt` for the default template.

### Custom Simulator

Full control via protocol implementation:

```python
from layercode_gym.simulator import UserSimulatorProtocol, UserRequest, UserResponse

class MyCustomSimulator(UserSimulatorProtocol):
    async def get_response(self, request: UserRequest) -> UserResponse | None:
        # Your logic here
        return UserResponse(text="Hello!", audio_path=None, data=())
```

## Environment Variables

**Required:**
```bash
SERVER_URL="http://localhost:8001"       # Your backend server
LAYERCODE_AGENT_ID="your_agent_id"       # LayerCode agent ID
```

**Optional:**
```bash
OPENAI_API_KEY="sk-..."                  # For TTS and AI agents
OPENAI_TTS_MODEL="gpt-4o-mini-tts"       # TTS model
OPENAI_TTS_VOICE="coral"                 # Voice (alloy, echo, fable, onyx, nova, shimmer, coral)
LAYERCODE_OUTPUT_ROOT="./conversations"  # Save location
LOGFIRE_TOKEN="..."                      # Enable LogFire observability
```

## LogFire Integration

Real-time observability and debugging with [LogFire](https://logfire.pydantic.dev/):

```bash
export LOGFIRE_TOKEN="your_token_here"
```

Automatically instruments PydanticAI and OpenAI calls, providing:
- Real-time conversation tracking
- Performance metrics and spans
- Error tracking with stack traces
- Beautiful UI for exploring conversations

## Type Safety

Enforces `mypy --strict` throughout. All event schemas use `TypedDict` or dataclasses.

```bash
uv run mypy src/layercode_gym
```

## Related Projects

- **[layercode-create-app](https://github.com/svilupp/layercode-create-app)** - CLI to scaffold LayerCode backends with tunneling
- **[layercode-examples](https://github.com/svilupp/layercode-examples)** - Agent patterns and integration recipes

## Documentation

Full documentation at [svilupp.github.io/layercode-gym](https://svilupp.github.io/layercode-gym)

- [Getting Started](https://svilupp.github.io/layercode-gym/getting-started)
- [Core Concepts](https://svilupp.github.io/layercode-gym/concepts)
- [Examples](https://svilupp.github.io/layercode-gym/examples)
- [API Reference](https://svilupp.github.io/layercode-gym/api-reference)
- [Advanced Usage](https://svilupp.github.io/layercode-gym/advanced)

## Contributing

This is a minimal, focused toolkit. Extensions should be done via:
- Custom simulator strategies (implement `UserSimulatorProtocol`)
- Custom callbacks (implement `TurnCallback` or `ConversationCallback`)
- Custom TTS engines (implement `TTSEngineProtocol`)

Keep the core simple and extensible.

## License

MIT - See [LICENSE](LICENSE) file for details.