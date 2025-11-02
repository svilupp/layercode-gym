# Getting Started

This guide will walk you through installing LayerCode Gym and running your first voice agent test.

## Prerequisites

### 1. Python 3.11+

LayerCode Gym requires Python 3.11 or higher. Check your version:

```bash
python --version
```

### 2. uv Package Manager

We recommend using [uv](https://github.com/astral-sh/uv) for fast, reliable dependency management:

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3. Backend Server

**IMPORTANT:** LayerCode Gym requires a backend server that's configured in the [Layercode dashboard](https://dash.layercode.com).

#### Option A: Use an Existing Server

If you already have a backend server running, skip to [Installation](#installation).

#### Option B: Quick Start Server

Don't have a server yet? Launch one quickly with auto-tunneling:

```bash
# Launch a quickstart server with Cloudflare tunnel
uvx layercode-create-app run --tunnel

# This will:
# - Start a local backend server
# - Create a Cloudflare tunnel for public access
# - Display the tunnel URL to enter in the Layercode dashboard
#
# Use -h to see all CLI options
```

The tunnel URL will look like: `https://random-name.trycloudflare.com`

Copy this URL and configure it in your [Layercode dashboard](https://dash.layercode.com) under your agent's settings.

## Installation

### Install LayerCode Gym

```bash
# Clone the repository (or use your preferred method)
git clone https://github.com/svilupp/layercode-gym.git
cd layercode-gym

# Install the package
uv add layercode-gym
```

For development:

```bash
# Install with dev dependencies
uv sync --group dev --group docs
```

## Configuration

### Environment Variables

Create a `.env` file in your project root or export these variables:

```bash
# Required
export SERVER_URL="http://localhost:8001"    # Your backend server URL
export LAYERCODE_AGENT_ID="your_agent_id"    # From Layercode dashboard

# Optional (for TTS and AI personas)
export OPENAI_API_KEY="sk-..."
```

#### Finding Your Agent ID

1. Go to [Layercode dashboard](https://dash.layercode.com)
2. Select your agent
3. Copy the Agent ID from the settings page

### Optional Configuration

```bash
# TTS Configuration (OpenAI)
export OPENAI_TTS_MODEL="gpt-4o-mini-tts"       # default
export OPENAI_TTS_VOICE="coral"                  # default
export OPENAI_TTS_INSTRUCTIONS="Speak slowly"    # optional

# Audio Chunking (advanced)
export LAYERCODE_CHUNK_MS="100"                  # ms per chunk (default: 100)
export LAYERCODE_CHUNK_INTERVAL="0.0"            # delay between chunks

# Storage
export LAYERCODE_OUTPUT_ROOT="./conversations"   # where to save results

# Observability (optional)
export LOGFIRE_TOKEN="..."                       # enable LogFire (if-token-present)
```

## First Test

Let's run your first voice agent test using fixed text messages (the fastest method).

### Create a Test Script

Create `my_first_test.py`:

```python
import asyncio
from layercode_gym import LayercodeClient, UserSimulator

async def main():
    # Create a simulator with fixed messages
    simulator = UserSimulator.from_text(
        messages=[
            "Hello! I'm interested in your services.",
            "Can you tell me about pricing?",
            "Thank you, goodbye."
        ],
        send_as_text=True  # Fast mode - no TTS needed
    )

    # Create client and run conversation
    client = LayercodeClient(simulator=simulator)
    conversation_id = await client.run()

    print(f"Conversation complete! ID: {conversation_id}")
    print(f"Results saved to: conversations/{conversation_id}/")

if __name__ == "__main__":
    asyncio.run(main())
```

### Run the Test

```bash
python my_first_test.py
```

You should see output like:

```
Conversation complete! ID: conv_abc123
Results saved to: conversations/conv_abc123/
```

### View Results

Check the output directory:

```bash
ls conversations/conv_abc123/

# You'll see:
# - transcript.json          # Full conversation log with stats
# - conversation_mix.wav     # Combined audio (user + assistant)
# - user_0.wav              # Individual user audio files
# - assistant_0.wav         # Individual assistant audio files
```

Open `transcript.json` to see detailed conversation metrics:

```json
{
  "conversation_id": "conv_abc123",
  "turns": [...],
  "stats": {
    "total_turns": 3,
    "duration_seconds": 45.2,
    "avg_latency_ms": 234
  }
}
```

## Next Steps

Congratulations! You've run your first test. Now explore:

- [Core Concepts](concepts.md) - Understand user simulators, callbacks, and architecture
- [Examples](examples.md) - Learn about audio files, AI personas, and batch evaluation
- [Advanced Usage](advanced.md) - Custom TTS engines, LogFire integration, and more

## Troubleshooting

### Connection Errors

If you see connection errors:

1. Verify your `SERVER_URL` is correct and the server is running
2. Check that your `LAYERCODE_AGENT_ID` is valid
3. Ensure your backend server is properly configured in the Layercode dashboard

### Import Errors

If you get import errors:

```bash
# Make sure you've installed the package
uv add layercode-gym

# Or for development
uv sync
```

### Permission Errors

If you see file permission errors:

```bash
# Check the output directory exists and is writable
mkdir -p conversations
chmod 755 conversations
```

## Getting Help

- Check the [Examples](examples.md) for common patterns
- Review the [API Reference](api-reference.md) for detailed documentation
- Open an issue on [GitHub](https://github.com/svilupp/layercode-gym/issues)
