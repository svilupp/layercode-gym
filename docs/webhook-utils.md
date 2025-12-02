# Webhook Management Utilities

Standalone utilities for managing LayerCode agent webhooks in CI/CD workflows.

## Overview

LayerCode agents support a single webhook URL at a time. When testing changes in CI (like testing a PR's backend), you need to:

1. Save the current webhook URL
2. Update to your test backend URL
3. Run tests
4. Restore the original webhook URL

These utilities simplify this process for shell scripts and CI workflows.

## CLI Commands

### Get Current Webhook

```bash
# Human-readable output
layercode-gym webhook get --agent-id ag-123456

# JSON output (for scripting)
layercode-gym webhook get --agent-id ag-123456 --json
```

**Output (human-readable)**:
```
Agent ID: ag-123456
Name: My Voice Agent
Webhook URL: https://production.example.com/webhook
```

**Output (JSON)**:
```json
{
  "agent_id": "ag-123456",
  "webhook_url": "https://production.example.com/webhook",
  "name": "My Voice Agent"
}
```

### Update Webhook

```bash
layercode-gym webhook update \
  --agent-id ag-123456 \
  --url https://test-backend.com/webhook
```

**Output**:
```
✓ Updated webhook for agent 'ag-123456'
  New URL: https://test-backend.com/webhook
```

## CI Workflow Pattern

### Basic Pattern (Shell Script)

```bash
#!/bin/bash
set -e

# Save original webhook
ORIGINAL=$(layercode-gym webhook get \
  --agent-id $LAYERCODE_AGENT_ID \
  --json | jq -r .webhook_url)

echo "Original webhook: $ORIGINAL"

# Update to test backend
layercode-gym webhook update \
  --agent-id $LAYERCODE_AGENT_ID \
  --url https://pr-${PR_NUMBER}.example.com/webhook

# Run tests
python run_tests.py

# Restore original (even if tests fail)
trap "layercode-gym webhook update --agent-id $LAYERCODE_AGENT_ID --url '$ORIGINAL'" EXIT
```

### GitHub Actions Workflow

```yaml
name: Test with PR Backend

on: pull_request

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Save original webhook
        id: webhook
        run: |
          ORIGINAL=$(layercode-gym webhook get \
            --agent-id ${{ secrets.LAYERCODE_AGENT_ID }} \
            --json | jq -r .webhook_url)
          echo "original=$ORIGINAL" >> $GITHUB_OUTPUT
        env:
          LAYERCODE_API_KEY: ${{ secrets.LAYERCODE_API_KEY }}

      - name: Update webhook to PR backend
        run: |
          layercode-gym webhook update \
            --agent-id ${{ secrets.LAYERCODE_AGENT_ID }} \
            --url https://pr-${{ github.event.pull_request.number }}.example.com/webhook
        env:
          LAYERCODE_API_KEY: ${{ secrets.LAYERCODE_API_KEY }}

      - name: Run tests
        run: python run_tests.py

      - name: Restore webhook
        if: always()
        run: |
          layercode-gym webhook update \
            --agent-id ${{ secrets.LAYERCODE_AGENT_ID }} \
            --url ${{ steps.webhook.outputs.original }}
        env:
          LAYERCODE_API_KEY: ${{ secrets.LAYERCODE_API_KEY }}
```

## Authentication

API key can be provided in two ways:

1. **Environment variable** (recommended):
   ```bash
   export LAYERCODE_API_KEY="your-api-key"
   layercode-gym webhook get --agent-id ag-123456
   ```

2. **Command-line flag**:
   ```bash
   layercode-gym webhook get \
     --agent-id ag-123456 \
     --api-key your-api-key
   ```

## Error Handling

### Invalid API Key (401)
```bash
$ layercode-gym webhook get --agent-id ag-123 --api-key invalid
Error: Invalid API key
```

### Agent Not Found (404)
```bash
$ layercode-gym webhook get --agent-id ag-nonexistent
Error: Agent 'ag-nonexistent' not found
```

### Network Errors
```bash
$ layercode-gym webhook get --agent-id ag-123
Error: Network error - Connection timeout
```

## Best Practices

### 1. Always Restore Webhooks

Use trap in bash or `if: always()` in GitHub Actions:

```bash
# Bash
trap "restore_webhook" EXIT

# GitHub Actions
- name: Restore webhook
  if: always()
  run: restore_webhook.sh
```

### 2. Use JSON Output for Scripting

```bash
# Good: Parse JSON
WEBHOOK=$(layercode-gym webhook get --agent-id ag-123 --json | jq -r .webhook_url)

# Bad: Parse human-readable output
WEBHOOK=$(layercode-gym webhook get --agent-id ag-123 | grep "Webhook" | cut -d: -f2)
```

### 3. Check Webhook Before Tests

```bash
# Verify webhook was updated
CURRENT=$(layercode-gym webhook get --agent-id ag-123 --json | jq -r .webhook_url)
EXPECTED="https://test.example.com/webhook"

if [ "$CURRENT" != "$EXPECTED" ]; then
  echo "Error: Webhook not updated correctly"
  exit 1
fi
```

### 4. Handle Concurrent Runs

Use GitHub Actions concurrency groups:

```yaml
concurrency:
  group: webhook-${{ secrets.LAYERCODE_AGENT_ID }}
  cancel-in-progress: false  # Wait for other runs to finish
```

## Advanced Usage

### Conditional Webhook Updates

Only update if different:

```bash
CURRENT=$(layercode-gym webhook get --agent-id ag-123 --json | jq -r .webhook_url)
DESIRED="https://test.example.com/webhook"

if [ "$CURRENT" != "$DESIRED" ]; then
  echo "Updating webhook from $CURRENT to $DESIRED"
  layercode-gym webhook update --agent-id ag-123 --url "$DESIRED"
else
  echo "Webhook already set to $DESIRED"
fi
```

### Multiple Agents

```bash
AGENTS=("ag-123" "ag-456" "ag-789")

for AGENT in "${AGENTS[@]}"; do
  echo "Updating $AGENT..."
  layercode-gym webhook update \
    --agent-id $AGENT \
    --url https://test.example.com/webhook
done
```

### Retry Logic

```bash
update_webhook_with_retry() {
  local agent_id=$1
  local url=$2
  local max_attempts=3

  for attempt in $(seq 1 $max_attempts); do
    if layercode-gym webhook update --agent-id $agent_id --url $url; then
      echo "Webhook updated successfully"
      return 0
    fi

    if [ $attempt -lt $max_attempts ]; then
      echo "Attempt $attempt failed, retrying..."
      sleep $((2 ** attempt))  # Exponential backoff
    fi
  done

  echo "Failed to update webhook after $max_attempts attempts"
  return 1
}
```

## API Reference

### `layercode-gym webhook get`

Get current webhook configuration for an agent.

**Arguments:**
- `--agent-id ID` (required): LayerCode agent ID
- `--api-key KEY` (optional): API key (or use `LAYERCODE_API_KEY` env var)
- `--json` (optional): Output as JSON

**Exit Codes:**
- `0`: Success
- `1`: Error (invalid API key, agent not found, network error)

### `layercode-gym webhook update`

Update webhook URL for an agent.

**Arguments:**
- `--agent-id ID` (required): LayerCode agent ID
- `--url URL` (required): New webhook URL
- `--api-key KEY` (optional): API key (or use `LAYERCODE_API_KEY` env var)
- `--json` (optional): Output as JSON

**Exit Codes:**
- `0`: Success
- `1`: Error (invalid API key, agent not found, network error, invalid URL)

## Python API

While these utilities are primarily CLI-focused, you can also use them programmatically:

```python
from layercode_gym.webhook_utils import (
    get_agent_webhook,
    update_agent_webhook,
)

# Get current webhook
info = get_agent_webhook(agent_id="ag-123456", api_key="your-key")
print(f"Current webhook: {info.webhook_url}")

# Update webhook
updated = update_agent_webhook(
    agent_id="ag-123456",
    api_key="your-key",
    webhook_url="https://new-backend.com/webhook"
)
print(f"Updated to: {updated.webhook_url}")
```

## Troubleshooting

### "Error: API key required"

Set the `LAYERCODE_API_KEY` environment variable or use `--api-key`:

```bash
export LAYERCODE_API_KEY="your-api-key"
# or
layercode-gym webhook get --agent-id ag-123 --api-key your-key
```

### "Error: Invalid API key"

Your API key may be expired or incorrect. Get a new one from [LayerCode Dashboard](https://layercode.com/dashboard) → API Keys.

### "Error: Agent not found"

Check your agent ID in the [LayerCode Dashboard](https://layercode.com/dashboard). Agent IDs start with `ag-`.

### Webhook not updating

1. Check you have the correct permissions for the API key
2. Verify the webhook URL is valid and accessible
3. Try with `--json` flag to see detailed error messages

## Related

- [LayerCode REST API Documentation](https://docs.layercode.com/api-reference/rest-api)
- [GitHub Actions Integration](github-action.md)
- [CI/CD Best Practices](advanced.md#cicd-integration)
