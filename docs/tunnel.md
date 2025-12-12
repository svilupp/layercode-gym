# Cloudflare Tunnel

Quickly expose your local development server to the internet with a Cloudflare tunnel. This is essential for testing LayerCode webhooks during local development.

## Overview

The `tunnel` command provides:

- **Quick public URL**: Expose any local port via Cloudflare's quick tunnel service
- **Automatic webhook update**: Optionally update your LayerCode agent's webhook URL
- **Automatic restore**: Previous webhook URL is restored when the tunnel stops
- **Debug logging**: Full tunnel logs saved to timestamped files

## Prerequisites

**Required:** [cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/) must be installed.

### Install cloudflared

**macOS:**
```bash
brew install cloudflare/cloudflare/cloudflared
```

**Linux:**
```bash
# Debian/Ubuntu
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb

# Or via package manager
sudo apt-get update && sudo apt-get install cloudflared
```

**Windows:**
```bash
winget install --id Cloudflare.cloudflared
```

**Verify installation:**
```bash
cloudflared --version
```

---

## Quick Start

```bash
# Basic tunnel - displays webhook URL to copy manually
layercode-gym tunnel --port 8000

# Or specify a full URL directly
layercode-gym tunnel --url http://localhost:8000

# Auto-update agent webhook (recommended)
layercode-gym tunnel --port 8000 --unsafe-update-webhook
```

When the tunnel starts, you'll see a banner like:

```
======================================================================
======================================================================
  CLOUDFLARE TUNNEL ESTABLISHED
======================================================================

  Tunnel URL: https://random-words-here.trycloudflare.com

======================================================================
  IMPORTANT: Add this URL to your LayerCode agent webhook:
  https://dash.layercode.com/

  TIP: Use --unsafe-update-webhook to automatically update
       the webhook for your agent (requires --agent-id)
======================================================================
  Press Ctrl+C to stop
======================================================================
======================================================================
```

---

## Command Reference

```bash
layercode-gym tunnel (--port PORT | --url URL) [OPTIONS]
```

### Target Arguments (one required)

| Argument | Description |
|----------|-------------|
| `--port PORT` | Local port to expose via tunnel (uses `--host`, default: localhost) |
| `--url URL` | Full URL to expose (e.g., `http://localhost:8000`) |

### Webhook Update Options

| Option | Description |
|--------|-------------|
| `--unsafe-update-webhook` | Automatically update agent webhook to tunnel URL |
| `--agent-id ID` | LayerCode agent ID to update (default: `LAYERCODE_AGENT_ID` env var) |
| `--api-key KEY` | LayerCode API key (default: `LAYERCODE_API_KEY` env var) |
| `--agent-path PATH` | Path to append to tunnel URL (see [Webhook URL Composition](#webhook-url-composition)) |

### Tunnel Configuration

| Option | Default | Description |
|--------|---------|-------------|
| `--host HOST` | `localhost` | Local host to tunnel to |
| `--timeout SECONDS` | `30` | Timeout waiting for tunnel to establish |

---

## Usage Examples

### Basic Tunnel

Expose port 8000 and manually copy the webhook URL:

```bash
layercode-gym tunnel --port 8000

# Or with a full URL
layercode-gym tunnel --url http://localhost:8000
```

### Auto-Update Webhook (Recommended)

Automatically update your agent's webhook and restore it on exit:

```bash
# Using environment variables
export LAYERCODE_AGENT_ID="ag-123456"
export LAYERCODE_API_KEY="your-api-key"

layercode-gym tunnel --port 8000 --unsafe-update-webhook
```

### Explicit Agent ID

Override the environment variable:

```bash
layercode-gym tunnel --port 8000 \
  --agent-id ag-different-agent \
  --unsafe-update-webhook
```

### Custom Host

Tunnel to a different host:

```bash
layercode-gym tunnel --port 8000 \
  --host 127.0.0.1 \
  --unsafe-update-webhook
```

---

## How It Works

### Tunnel Lifecycle

1. **Start**: `cloudflared tunnel --url http://localhost:PORT` subprocess launches
2. **URL Detection**: Parses tunnel URL from cloudflared output
3. **Webhook Update** (if enabled):
   - Fetches current webhook URL from LayerCode API
   - Saves it for later restoration
   - Updates webhook to tunnel URL
4. **Running**: Tunnel stays open until Ctrl+C
5. **Shutdown**:
   - Checks if webhook is still our tunnel URL (not changed externally)
   - Restores previous webhook URL
   - Terminates cloudflared process

### Webhook URL Composition

When `--unsafe-update-webhook` is enabled, the final webhook URL is composed from two parts:

```
Full Webhook URL = Tunnel Base URL + Agent Path
```

**Example:**
```
Tunnel Base URL: https://random-words.trycloudflare.com
Agent Path:      /api/agent
Final URL:       https://random-words.trycloudflare.com/api/agent
```

**Agent Path Resolution Priority:**

The agent path is resolved in this order (first match wins):

1. **Explicit `--agent-path`** - If you provide `--agent-path /custom/endpoint`, it's used directly
2. **Existing webhook path** - If no explicit path, the path is extracted from your agent's current webhook URL
3. **Default `/api/agent`** - If no other source available

This means if your agent's webhook is currently `https://example.com/api/voice-handler`, the tunnel will automatically use `/api/voice-handler` as the path—no configuration needed.

**Examples:**

```bash
# Use explicit path
layercode-gym tunnel --port 8000 --unsafe-update-webhook --agent-path /webhooks/voice
# Result: https://random.trycloudflare.com/webhooks/voice

# Use path from existing webhook (automatic)
# If current webhook is https://example.com/api/voice-agent
layercode-gym tunnel --port 8000 --unsafe-update-webhook
# Result: https://random.trycloudflare.com/api/voice-agent

# Use default when no existing webhook
layercode-gym tunnel --port 8000 --unsafe-update-webhook
# Result: https://random.trycloudflare.com/api/agent
```

### Webhook Restore Logic

The restore is **intelligent** - it only restores if:

1. The current webhook URL matches our tunnel URL
2. If yes: restores the saved previous webhook (or clears if there was none)
3. If no: leaves it alone (someone else changed it)

This prevents accidentally overwriting webhook changes made during your session.

---

## Environment Variables

| Variable | Description | Used For |
|----------|-------------|----------|
| `LAYERCODE_AGENT_ID` | Default agent ID | `--unsafe-update-webhook` |
| `LAYERCODE_API_KEY` | API key for LayerCode API | `--unsafe-update-webhook` |
| `LAYERCODE_AGENT_PATH` | Path to append to tunnel URL (e.g., `/api/agent`) | `--unsafe-update-webhook` |

---

## Logging

Tunnel debug output is saved to timestamped log files:

```
cloudflare_tunnel_20251211_143022.log
```

The log file path is displayed when the tunnel starts:

```
Tunnel logs: /path/to/cloudflare_tunnel_20251211_143022.log
```

This keeps your terminal clean while preserving full debug information.

---

## Error Handling

### cloudflared Not Installed

```
Error: cloudflared binary not found.
Install from: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/
```

**Solution:** Install cloudflared (see [Prerequisites](#prerequisites))

### Tunnel Timeout

```
Error: Timed out waiting for tunnel URL after 30s. Check logs at: cloudflare_tunnel_20251211_143022.log
```

**Solution:**
1. Check the log file for cloudflared errors
2. Verify internet connectivity
3. Try increasing timeout: `--timeout 60`

### Missing Agent ID

```
Error: --unsafe-update-webhook requires --agent-id or LAYERCODE_AGENT_ID env var
```

**Solution:** Set the environment variable or provide `--agent-id`

### Missing API Key

```
Error: --unsafe-update-webhook requires --api-key or LAYERCODE_API_KEY env var
```

**Solution:** Set `LAYERCODE_API_KEY` environment variable or provide `--api-key`

### Webhook Update Failed

```
Warning: Failed to update webhook: <error details>
Continuing with tunnel anyway...
```

The tunnel continues running even if webhook update fails. You can manually copy the webhook URL.

---

## Best Practices

### 1. Use Environment Variables

```bash
# Add to your .env or shell profile
export LAYERCODE_AGENT_ID="ag-your-dev-agent"
export LAYERCODE_API_KEY="your-api-key"

# Then just run
layercode-gym tunnel --port 8000 --unsafe-update-webhook
```

### 2. Use a Dedicated Development Agent

Create a separate agent in LayerCode for local development:

```bash
# Production agent - never auto-update
layercode-gym api-agents get --agent-id ag-production

# Development agent - safe to auto-update
export LAYERCODE_AGENT_ID="ag-development"
layercode-gym tunnel --port 8000 --unsafe-update-webhook
```

### 3. Start Server Before Tunnel

The tunnel just exposes a port - make sure something is listening:

```bash
# Terminal 1: Start your server
python -m uvicorn myapp:app --port 8000

# Terminal 2: Start the tunnel
layercode-gym tunnel --port 8000 --unsafe-update-webhook
```

### 4. Check Logs on Issues

If the tunnel misbehaves, check the log file:

```bash
cat cloudflare_tunnel_*.log | tail -100
```

---

## Comparison with layercode-create-app

| Feature | `layercode-gym tunnel` | `layercode-create-app --tunnel` |
|---------|----------------------|--------------------------------|
| **Purpose** | Expose any server | Run built-in server + tunnel |
| **Server** | Bring your own | Included (FastAPI) |
| **Webhook Update** | Yes | Yes |
| **Webhook Restore** | Yes | Yes |
| **Use Case** | Custom backends | Quick prototyping |

**When to use each:**

- Use `layercode-gym tunnel` when you have your own backend server
- Use `layercode-create-app --tunnel` for quick prototyping with built-in agents

---

## Troubleshooting

### Tunnel Connects but Webhooks Don't Work

1. Verify your server is running on the correct port
2. Check that your webhook endpoint path is correct
3. Test the local endpoint: `curl http://localhost:8000/your-webhook-path`

### Webhook Not Restored on Exit

This can happen if:
- The tunnel was killed (SIGKILL) instead of interrupted (Ctrl+C)
- The webhook was changed during the session
- Network issues during shutdown

Manual restore:
```bash
layercode-gym api-agents update \
  --agent-id ag-123456 \
  --webhook-url https://your-original-webhook.com
```

### Multiple Tunnels Conflict

Only run one tunnel per agent at a time. If you need multiple tunnels, use different agents:

```bash
# Terminal 1
LAYERCODE_AGENT_ID=ag-dev-1 layercode-gym tunnel --port 8000 --unsafe-update-webhook

# Terminal 2
LAYERCODE_AGENT_ID=ag-dev-2 layercode-gym tunnel --port 8001 --unsafe-update-webhook
```

---

## Related Documentation

- [Getting Started](getting-started.md) - Full setup guide
- [API Agents CLI](api-agents.md) - Manual webhook management
- [GitHub Actions](github-action.md) - CI/CD integration

---

## Support

- **Issues**: [GitHub Issues](https://github.com/svilupp/layercode-gym/issues)
- **Discussions**: [GitHub Discussions](https://github.com/svilupp/layercode-gym/discussions)
- **cloudflared docs**: [Cloudflare Tunnel Documentation](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
