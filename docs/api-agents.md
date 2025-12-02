# LayerCode Agents REST API CLI

Direct access to the LayerCode REST API for agent management.

## Overview

The `api-agents` command provides a clean CLI interface to the [LayerCode REST API](https://docs.layercode.com/api-reference/rest-api) for managing your voice agents.

**Three simple commands:**
- `list` - List all agents in your account
- `get` - Get agent details by ID
- `update` - Update agent configuration

## Installation

The command is included with layercode-gym:

```bash
# Via uv (no installation needed)
uvx layercode-gym api-agents --help

# Or install it
uv add layercode-gym
```

## Quick Start

```bash
# Set your API key
export LAYERCODE_API_KEY="your-api-key-here"

# List all agents
layercode-gym api-agents list

# Get specific agent
layercode-gym api-agents get --agent-id ag-123456

# Update agent webhook
layercode-gym api-agents update \
  --agent-id ag-123456 \
  --webhook-url https://new-backend.com/webhook
```

## Commands

### `list` - List All Agents

List all agents in your LayerCode account.

```bash
layercode-gym api-agents list [--json]
```

**Example Output (human-readable)**:
```
Found 3 agent(s):

1. Production Voice Agent (ag-123456)
   Webhook: https://production.example.com/webhook

2. Staging Agent (ag-789012)
   Webhook: https://staging.example.com/webhook

3. Test Agent (ag-345678)
   Webhook: (not set)
```

**Example Output (JSON)**:
```json
[
  {
    "agent_id": "ag-123456",
    "name": "Production Voice Agent",
    "webhook_url": "https://production.example.com/webhook"
  },
  {
    "agent_id": "ag-789012",
    "name": "Staging Agent",
    "webhook_url": "https://staging.example.com/webhook"
  },
  {
    "agent_id": "ag-345678",
    "name": "Test Agent",
    "webhook_url": null
  }
]
```

**Options**:
- `--json` - Output as JSON array
- `--api-key KEY` - API key (or use `LAYERCODE_API_KEY` env var)

---

### `get` - Get Agent Details

Get detailed information about a specific agent.

```bash
layercode-gym api-agents get --agent-id ag-123456 [--json]
```

**Example Output (human-readable)**:
```
Agent ID: ag-123456
Name: Production Voice Agent
Webhook URL: https://production.example.com/webhook
```

**Example Output (JSON)**:
```json
{
  "agent_id": "ag-123456",
  "name": "Production Voice Agent",
  "webhook_url": "https://production.example.com/webhook"
}
```

**Options**:
- `--agent-id ID` (required) - Agent ID (e.g., ag-123456)
- `--json` - Output as JSON object
- `--api-key KEY` - API key (or use `LAYERCODE_API_KEY` env var)

---

### `update` - Update Agent Configuration

Update agent fields like webhook URL, name, or other configuration.

#### Update Single Field

```bash
# Update webhook URL
layercode-gym api-agents update \
  --agent-id ag-123456 \
  --webhook-url https://new-backend.com/webhook

# Update agent name
layercode-gym api-agents update \
  --agent-id ag-123456 \
  --name "New Agent Name"
```

#### Update Multiple Fields

```bash
# Update both webhook and name
layercode-gym api-agents update \
  --agent-id ag-123456 \
  --webhook-url https://new-backend.com/webhook \
  --name "Updated Agent"
```

#### Update with JSON Data

For complex updates, use `--json-data`:

```bash
layercode-gym api-agents update \
  --agent-id ag-123456 \
  --json-data '{
    "webhook_url": "https://new-backend.com/webhook",
    "name": "Updated Agent"
  }'
```

**Example Output**:
```
✓ Updated agent 'ag-123456'
  webhook_url: https://new-backend.com/webhook
  name: Updated Agent
```

**Options**:
- `--agent-id ID` (required) - Agent ID
- `--webhook-url URL` - Update webhook URL
- `--name NAME` - Update agent name
- `--json-data JSON` - Update with JSON string (cannot mix with other flags)
- `--json` - Output response as JSON
- `--api-key KEY` - API key (or use `LAYERCODE_API_KEY` env var)

---

## CI/CD Workflow Patterns

### Pattern 1: Save & Restore Webhook

Common pattern for testing PR backends:

```bash
#!/bin/bash
set -e

# Save original webhook
ORIGINAL=$(layercode-gym api-agents get \
  --agent-id $LAYERCODE_AGENT_ID \
  --json | jq -r .webhook_url)

echo "Original webhook: $ORIGINAL"

# Update to PR backend
layercode-gym api-agents update \
  --agent-id $LAYERCODE_AGENT_ID \
  --webhook-url https://pr-${PR_NUMBER}.example.com/webhook

# Run tests
python run_tests.py

# Restore original
layercode-gym api-agents update \
  --agent-id $LAYERCODE_AGENT_ID \
  --webhook-url "$ORIGINAL"
```

### Pattern 2: GitHub Actions

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
          ORIGINAL=$(layercode-gym api-agents get \
            --agent-id ${{ secrets.LAYERCODE_AGENT_ID }} \
            --json | jq -r .webhook_url)
          echo "original=$ORIGINAL" >> $GITHUB_OUTPUT
        env:
          LAYERCODE_API_KEY: ${{ secrets.LAYERCODE_API_KEY }}

      - name: Update to PR backend
        run: |
          layercode-gym api-agents update \
            --agent-id ${{ secrets.LAYERCODE_AGENT_ID }} \
            --webhook-url https://pr-${{ github.event.pull_request.number }}.example.com
        env:
          LAYERCODE_API_KEY: ${{ secrets.LAYERCODE_API_KEY }}

      - name: Run tests
        run: python run_tests.py

      - name: Restore webhook
        if: always()
        run: |
          layercode-gym api-agents update \
            --agent-id ${{ secrets.LAYERCODE_AGENT_ID }} \
            --webhook-url ${{ steps.webhook.outputs.original }}
        env:
          LAYERCODE_API_KEY: ${{ secrets.LAYERCODE_API_KEY }}
```

### Pattern 3: Bulk Update Webhooks

Update all agents to point to new backend:

```bash
# Get all agent IDs
AGENT_IDS=$(layercode-gym api-agents list --json | jq -r '.[].agent_id')

# Update each agent
for agent_id in $AGENT_IDS; do
  echo "Updating $agent_id..."
  layercode-gym api-agents update \
    --agent-id $agent_id \
    --webhook-url https://new-backend.com/webhook
done
```

### Pattern 4: Configuration Backup

Backup agent configurations:

```bash
# Create backup directory
mkdir -p agent-backups

# List and backup each agent
layercode-gym api-agents list --json | jq -r '.[].agent_id' | while read agent_id; do
  layercode-gym api-agents get --agent-id $agent_id --json > \
    "agent-backups/${agent_id}.json"
  echo "Backed up $agent_id"
done
```

---

## Authentication

The API key can be provided in two ways:

### 1. Environment Variable (Recommended)

```bash
export LAYERCODE_API_KEY="your-api-key"
layercode-gym api-agents list
```

### 2. Command-Line Flag

```bash
layercode-gym api-agents list --api-key your-api-key
```

**Where to get your API key:**
1. Go to [LayerCode Dashboard](https://layercode.com/dashboard)
2. Navigate to API Keys section
3. Create a new API key
4. Copy and store securely

---

## Error Handling

### Invalid API Key (401)
```bash
$ layercode-gym api-agents list --api-key invalid
Error: Invalid API key
```

**Solution**: Check your API key in the LayerCode Dashboard

### Agent Not Found (404)
```bash
$ layercode-gym api-agents get --agent-id ag-nonexistent
Error: Agent 'ag-nonexistent' not found
```

**Solution**: Verify the agent ID with `layercode-gym api-agents list`

### Network Errors
```bash
$ layercode-gym api-agents list
Error: Network error - Connection timeout
```

**Solution**: Check your internet connection and try again

### Missing Update Fields
```bash
$ layercode-gym api-agents update --agent-id ag-123
Error: No update fields provided. Use --webhook-url, --name, or --json-data
```

**Solution**: Provide at least one field to update

### Conflicting Update Options
```bash
$ layercode-gym api-agents update --agent-id ag-123 \
  --webhook-url https://test.com \
  --json-data '{"name":"test"}'
Error: Cannot use --json-data with --webhook-url or --name
```

**Solution**: Use either individual flags OR `--json-data`, not both

---

## Best Practices

### 1. Use Environment Variables for API Keys

```bash
# Good: API key in environment
export LAYERCODE_API_KEY="your-key"
layercode-gym api-agents list

# Bad: API key in command (visible in history)
layercode-gym api-agents list --api-key your-key
```

### 2. Always Use JSON Output for Scripting

```bash
# Good: Parse JSON
WEBHOOK=$(layercode-gym api-agents get --agent-id ag-123 --json | jq -r .webhook_url)

# Bad: Parse human-readable output
WEBHOOK=$(layercode-gym api-agents get --agent-id ag-123 | grep "Webhook" | cut -d: -f2)
```

### 3. Verify Updates

```bash
# Update webhook
layercode-gym api-agents update --agent-id ag-123 --webhook-url https://new.com

# Verify it worked
CURRENT=$(layercode-gym api-agents get --agent-id ag-123 --json | jq -r .webhook_url)
if [ "$CURRENT" == "https://new.com" ]; then
  echo "✓ Webhook updated successfully"
else
  echo "✗ Webhook update failed"
  exit 1
fi
```

### 4. Use `if: always()` in GitHub Actions

Always restore webhooks even if tests fail:

```yaml
- name: Restore webhook
  if: always()  # Run even if previous steps failed
  run: |
    layercode-gym api-agents update \
      --agent-id ${{ secrets.LAYERCODE_AGENT_ID }} \
      --webhook-url ${{ steps.webhook.outputs.original }}
```

### 5. Handle Concurrent Runs

Use concurrency groups to prevent race conditions:

```yaml
concurrency:
  group: api-agents-${{ secrets.LAYERCODE_AGENT_ID }}
  cancel-in-progress: false  # Wait for other runs
```

---

## Comparison with GitHub Action

| Feature | `api-agents` CLI | GitHub Action |
|---------|-----------------|---------------|
| **Purpose** | Direct API access | Full test workflows |
| **Use Case** | CI scripts, automation | Comprehensive testing |
| **Webhook Management** | ✅ Manual control | ✅ Automatic |
| **Run Tests** | ❌ Separate step | ✅ Built-in |
| **Judge Evaluation** | ❌ No | ✅ Yes |
| **Parallel Personas** | ❌ No | ✅ Yes |
| **Complexity** | Simple, flexible | More setup |

**When to use each:**
- Use `api-agents` for: Simple webhook swaps, bulk updates, agent discovery
- Use [GitHub Action](github-action.md) for: Full test workflows with personas and judging

---

## Related Documentation

- [LayerCode REST API Reference](https://docs.layercode.com/api-reference/rest-api)
- [GitHub Actions Integration](github-action.md)
- [Getting Started](getting-started.md)
- [Advanced Usage](advanced.md)

---

## Troubleshooting

### "Error: API key required"

Set the `LAYERCODE_API_KEY` environment variable:

```bash
export LAYERCODE_API_KEY="your-api-key"
```

Or use the `--api-key` flag.

### "Command not found: api-agents"

Make sure you're using the full command:

```bash
# Correct
layercode-gym api-agents list

# Wrong
layercode-gym api agents list  # No hyphen
api-agents list  # Missing layercode-gym prefix
```

### JSON Parsing Errors

Make sure `jq` is installed for JSON parsing:

```bash
# Install jq
# macOS
brew install jq

# Ubuntu/Debian
sudo apt-get install jq

# Or use python
layercode-gym api-agents get --agent-id ag-123 --json | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['webhook_url'])"
```

### Webhook Not Updating

1. Check the agent ID is correct
2. Verify the webhook URL is valid and accessible
3. Try getting the agent first to ensure it exists:

```bash
layercode-gym api-agents get --agent-id ag-123456
```

---

## Examples

### Example 1: Find Agent by Name

```bash
# List all agents and filter by name
layercode-gym api-agents list --json | \
  jq -r '.[] | select(.name == "Production Voice Agent") | .agent_id'
```

### Example 2: Update All Agents

```bash
#!/bin/bash
NEW_URL="https://new-backend.com/webhook"

layercode-gym api-agents list --json | jq -r '.[].agent_id' | while read agent_id; do
  echo "Updating $agent_id to $NEW_URL"
  layercode-gym api-agents update --agent-id $agent_id --webhook-url "$NEW_URL"
done
```

### Example 3: Check Webhook Configuration

```bash
#!/bin/bash
EXPECTED="https://production.example.com/webhook"

layercode-gym api-agents list --json | jq -r '.[]' | while read -r agent; do
  agent_id=$(echo "$agent" | jq -r '.agent_id')
  webhook=$(echo "$agent" | jq -r '.webhook_url')

  if [ "$webhook" != "$EXPECTED" ]; then
    echo "⚠️  Agent $agent_id has unexpected webhook: $webhook"
  else
    echo "✓ Agent $agent_id webhook correct"
  fi
done
```

### Example 4: Agent Inventory Report

```bash
#!/bin/bash
echo "Agent Inventory Report"
echo "====================="
echo ""

COUNT=$(layercode-gym api-agents list --json | jq 'length')
echo "Total Agents: $COUNT"
echo ""

echo "Agents without webhooks:"
layercode-gym api-agents list --json | \
  jq -r '.[] | select(.webhook_url == null) | "  - \(.name // "Unnamed") (\(.agent_id))"'
```

---

## Support

- **Issues**: [GitHub Issues](https://github.com/svilupp/layercode-gym/issues)
- **Discussions**: [GitHub Discussions](https://github.com/svilupp/layercode-gym/discussions)
- **LayerCode Docs**: [docs.layercode.com](https://docs.layercode.com)
