# Examples

Quick examples demonstrating layercode-gym features.

## Setup

```bash
# Install
uv sync

# Configure .env
SERVER_URL=http://localhost:8001         # Your backend server URL
LAYERCODE_AGENT_ID=your_agent_id         # LayerCode agent ID
OPENAI_API_KEY=your_openai_key           # For examples 03-07
```

**Architecture Note**: The client authorizes through YOUR backend server (SERVER_URL), which returns a `client_session_key`. The client then uses that key to connect to LayerCode's WebSocket endpoint.

## Examples

### 01 - Text Messages
Send canned text messages.
```bash
uv run python examples/01_text_messages.py
```

### 02 - Audio File
Send pre-recorded audio file.
```bash
uv run python examples/02_audio_file.py
```

### 03 - AI Agent with Persona
AI-driven responses with customizable persona.
```bash
uv run python examples/03_agent_persona.py
```

### 04 - CriteriaJudge Evaluation
Pass/fail evaluation against custom criteria.
```bash
uv run python examples/04_callbacks_judge.py
```

### 05 - Batch Evaluation
Run multiple conversations concurrently.
```bash
uv run python examples/05_batch_evaluation.py
```

### 06 - Custom Data Processor
Process response.data events (tool calls) for AI context.
```bash
uv run python examples/06_outdoor_shop_eval.py
```

### 07 - Custom Judge
Build your own judge with PydanticAI custom output types.
```bash
uv run python examples/07_custom_judge.py
```

### 08 - Long-Running Tasks
Test agents with wait handling for slow operations.
```bash
uv run python examples/08_long_running_task.py
```

### Run All
```bash
uv run python examples/run_all.py
```

## Output

Each conversation creates: `conversations/<conversation_id>/`
- `transcript.json` - Full conversation with stats
- `audio/` - Individual and combined audio files
- `judge_evaluation.json` - LLM judge results (example 04)