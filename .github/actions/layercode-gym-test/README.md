# LayerCode Gym Test Action

A GitHub Action for running automated conversational AI tests using LayerCode Gym. Test your voice agents with multiple personas in parallel and get automated quality evaluations.

## Features

- 🎭 **Multiple Personas**: Test with multiple user personas simultaneously
- ⚡ **Parallel Execution**: All conversations run concurrently for maximum speed
- 🏛️ **Automated Judging**: Optional LLM-based evaluation with pass/fail criteria
- 📊 **Detailed Reports**: Conversation transcripts, audio recordings, and judge feedback
- 🔍 **Observability**: Optional LogFire integration for deep insights
- 💾 **Artifacts**: Automatic upload of all test results

## Quick Start

```yaml
name: Test Voice Agent
on: [push, pull_request]

jobs:
  test-agent:
    runs-on: ubuntu-latest

    # IMPORTANT: Prevent concurrent runs for the same agent
    # LayerCode agents support one webhook at a time
    concurrency:
      group: layercode-gym-${{ secrets.LAYERCODE_AGENT_ID }}
      cancel-in-progress: false

    steps:
      - uses: actions/checkout@v4

      - name: Test with LayerCode Gym
        uses: ./.github/actions/layercode-gym-test
        with:
          personas: |
            [
              {
                "background": "You are a 35-year-old small business owner interested in AI",
                "intent": "Learn about voice AI capabilities and pricing"
              },
              {
                "background": "You are a technical developer evaluating voice APIs",
                "intent": "Understand technical integration requirements"
              }
            ]
          max-turns: 5
          judge-enabled: true
          judge-criteria: "The agent must provide clear information and offer a demo or next steps"
          server-url: ${{ secrets.SERVER_URL }}
          layercode-agent-id: ${{ secrets.LAYERCODE_AGENT_ID }}
          layercode-api-key: ${{ secrets.LAYERCODE_API_KEY }}
          openai-api-key: ${{ secrets.OPENAI_API_KEY }}
          logfire-token: ${{ secrets.LOGFIRE_TOKEN }}
```

## Inputs

### Required Inputs

#### `personas`
**Type**: JSON array
**Description**: Array of persona objects to test. Each persona must have:
- `background`: Who the user is (context, role, characteristics)
- `intent`: What they want to achieve

**Example**:
```json
[
  {
    "background": "You are a frustrated customer who has been waiting on hold",
    "intent": "Cancel your subscription immediately"
  },
  {
    "background": "You are a potential customer researching solutions",
    "intent": "Learn about features and pricing"
  }
]
```

#### `server-url`
**Type**: String
**Description**: Your backend server URL that communicates with LayerCode
**Example**: `https://your-backend.com`

#### `layercode-agent-id`
**Type**: String (secret)
**Description**: Your LayerCode agent ID from the dashboard
**Where to find**: LayerCode Dashboard → Your Agent → Settings

#### `layercode-api-key`
**Type**: String (secret)
**Description**: Your LayerCode API key for webhook configuration
**Where to find**: LayerCode Dashboard → API Keys
**Docs**: [LayerCode REST API](https://docs.layercode.com/api-reference/rest-api)

#### `openai-api-key`
**Type**: String (secret)
**Description**: OpenAI API key for AI personas and TTS
**Required for**: Agent-based personas (recommended for CI)

### Optional Inputs

#### `max-turns`
**Type**: Integer
**Default**: `5`
**Description**: Maximum number of conversation turns per persona

#### `judge-enabled`
**Type**: Boolean
**Default**: `false`
**Description**: Enable automated LLM-based judging of conversations

#### `judge-criteria`
**Type**: String
**Default**: `"The assistant provided helpful and accurate information"`
**Description**: Pass/fail criteria for the judge to evaluate
**Example**: `"The agent must mention pricing, offer a demo, and be professional"`

#### `fail-on-judge-failure`
**Type**: Boolean
**Default**: `true`
**Description**: Whether to fail the CI pipeline if judge evaluation fails
**Note**: Only applies when `judge-enabled: true`

#### `logfire-token`
**Type**: String (secret, optional)
**Default**: `""`
**Description**: LogFire token for observability and debugging
**Recommended**: Highly recommended for production testing

#### `model`
**Type**: String
**Default**: `openai:gpt-4o-mini`
**Description**: AI model for personas
**Options**:
- `openai:gpt-4o-mini` (fast, cost-effective)
- `openai:gpt-4o` (more capable)
- `anthropic:claude-sonnet-4-5` (highest quality)
- `anthropic:claude-haiku-4` (fast)

#### `upload-artifacts`
**Type**: Boolean
**Default**: `true`
**Description**: Upload conversation transcripts and recordings as GitHub artifacts

## Outputs

### `conversations-run`
**Type**: Integer
**Description**: Number of conversations executed

### `conversations-passed`
**Type**: Integer
**Description**: Number of conversations that passed judge evaluation
**Note**: Only available when `judge-enabled: true`

### `conversations-failed`
**Type**: Integer
**Description**: Number of conversations that failed judge evaluation
**Note**: Only available when `judge-enabled: true`

### `results-path`
**Type**: String
**Description**: Path to the results directory (`conversations/`)

## Required GitHub Secrets

Set these in your repository: **Settings → Secrets and variables → Actions → New repository secret**

| Secret Name | Description | Where to Get |
|------------|-------------|--------------|
| `SERVER_URL` | Your backend server URL | Your infrastructure |
| `LAYERCODE_AGENT_ID` | LayerCode agent ID | [LayerCode Dashboard](https://layercode.com/dashboard) |
| `LAYERCODE_API_KEY` | LayerCode API key | [LayerCode Dashboard → API Keys](https://layercode.com/dashboard) |
| `OPENAI_API_KEY` | OpenAI API key | [OpenAI Platform](https://platform.openai.com/api-keys) |
| `LOGFIRE_TOKEN` | LogFire token (optional) | [LogFire](https://logfire.pydantic.dev/) |

## Complete Example

```yaml
name: Voice Agent Quality Tests

on:
  push:
    branches: [main]
  pull_request:
  schedule:
    - cron: '0 0 * * *'  # Daily at midnight
  workflow_dispatch:  # Manual trigger

jobs:
  test-customer-personas:
    name: Test Customer Scenarios
    runs-on: ubuntu-latest

    # Prevent concurrent runs - LayerCode supports one webhook per agent
    concurrency:
      group: layercode-gym-${{ secrets.LAYERCODE_AGENT_ID }}
      cancel-in-progress: false

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Run customer persona tests
        uses: ./.github/actions/layercode-gym-test
        with:
          personas: |
            [
              {
                "background": "You are a frustrated customer who has been overcharged",
                "intent": "Get a refund and explanation"
              },
              {
                "background": "You are a happy customer wanting to upgrade",
                "intent": "Learn about premium features"
              },
              {
                "background": "You are a confused new user",
                "intent": "Understand how to get started"
              }
            ]
          max-turns: 7
          judge-enabled: true
          judge-criteria: |
            The agent must:
            1. Address the customer's concern directly
            2. Be empathetic and professional
            3. Provide clear next steps or solutions
            4. Not leave the customer confused
          fail-on-judge-failure: true
          model: openai:gpt-4o-mini
          server-url: ${{ secrets.SERVER_URL }}
          layercode-agent-id: ${{ secrets.LAYERCODE_AGENT_ID }}
          layercode-api-key: ${{ secrets.LAYERCODE_API_KEY }}
          openai-api-key: ${{ secrets.OPENAI_API_KEY }}
          logfire-token: ${{ secrets.LOGFIRE_TOKEN }}

      - name: Report results
        if: always()
        run: |
          echo "Conversations run: ${{ steps.test.outputs.conversations-run }}"
          echo "Passed: ${{ steps.test.outputs.conversations-passed }}"
          echo "Failed: ${{ steps.test.outputs.conversations-failed }}"

  test-technical-personas:
    name: Test Technical Scenarios
    runs-on: ubuntu-latest

    concurrency:
      group: layercode-gym-${{ secrets.LAYERCODE_AGENT_ID }}
      cancel-in-progress: false

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Run technical persona tests
        uses: ./.github/actions/layercode-gym-test
        with:
          personas: |
            [
              {
                "background": "You are a developer evaluating the API",
                "intent": "Understand authentication, rate limits, and SDKs"
              },
              {
                "background": "You are a DevOps engineer setting up monitoring",
                "intent": "Learn about webhooks, logging, and error handling"
              }
            ]
          max-turns: 10
          judge-enabled: true
          judge-criteria: "The agent provides accurate technical information and documentation links"
          model: anthropic:claude-sonnet-4-5
          server-url: ${{ secrets.SERVER_URL }}
          layercode-agent-id: ${{ secrets.LAYERCODE_AGENT_ID }}
          layercode-api-key: ${{ secrets.LAYERCODE_API_KEY }}
          openai-api-key: ${{ secrets.OPENAI_API_KEY }}
          logfire-token: ${{ secrets.LOGFIRE_TOKEN }}
```

## Artifacts

When `upload-artifacts: true` (default), the action uploads:

```
layercode-gym-results-<run-id>/
├── <conversation-id-1>/
│   ├── transcript.json          # Full conversation with timing
│   ├── judge_evaluation.json    # Judge results (if enabled)
│   ├── conversation_mix.wav     # Combined audio recording
│   ├── user_0.wav               # Individual user messages
│   └── assistant_0.wav          # Individual assistant responses
├── <conversation-id-2>/
│   └── ...
└── ...
```

**Access artifacts**: GitHub Actions → Workflow run → Artifacts section

## Best Practices

### 1. Use Concurrency Control

Always add concurrency control to prevent webhook conflicts:

```yaml
concurrency:
  group: layercode-gym-${{ secrets.LAYERCODE_AGENT_ID }}
  cancel-in-progress: false
```

### 2. Separate Jobs for Different Test Suites

Run different persona sets in separate jobs:

```yaml
jobs:
  test-happy-path:
    # ... customer success scenarios

  test-edge-cases:
    # ... error handling, edge cases

  test-security:
    # ... authentication, authorization
```

### 3. Use Scheduled Tests

Run regression tests daily:

```yaml
on:
  schedule:
    - cron: '0 0 * * *'  # Daily at midnight
```

### 4. Enable LogFire for Debugging

Set `LOGFIRE_TOKEN` secret for deep observability:
- See real-time conversation flow
- Debug timing issues
- Track agent performance metrics

### 5. Write Specific Judge Criteria

Good criteria are specific and measurable:

```yaml
judge-criteria: |
  The agent must:
  1. Greet the user by name if provided
  2. Provide at least 2 specific product recommendations
  3. Mention the return policy
  4. End with a clear call-to-action
```

### 6. Use Different Models for Different Needs

- `openai:gpt-4o-mini`: Fast, cost-effective, good for most tests
- `anthropic:claude-sonnet-4-5`: Complex conversations, high accuracy
- `openai:gpt-4o`: Balance of speed and capability

## Troubleshooting

### "Failed to configure webhook"

**Cause**: Invalid `LAYERCODE_API_KEY` or `LAYERCODE_AGENT_ID`

**Solution**:
1. Verify your API key in [LayerCode Dashboard → API Keys](https://layercode.com/dashboard)
2. Confirm agent ID in LayerCode Dashboard → Your Agent → Settings
3. Ensure secrets are set correctly in GitHub repository settings

### "No module named 'layercode_gym'"

**Cause**: Installation issue with `uvx`

**Solution**: This should auto-resolve. If persistent, file an issue at [layercode-gym repo](https://github.com/yourusername/layercode-gym/issues)

### Conversations Timing Out

**Cause**: Server not responding or network issues

**Solution**:
1. Verify `SERVER_URL` is correct and accessible
2. Check server logs for errors
3. Increase `max-turns` if conversations are legitimately long

### Judge Always Failing

**Cause**: Criteria too strict or agent not meeting requirements

**Solution**:
1. Review judge feedback in artifacts
2. Adjust `judge-criteria` to be more realistic
3. Test locally first with `layercode-gym` CLI
4. Set `fail-on-judge-failure: false` for informational-only judging

### Concurrent Run Conflicts

**Cause**: Multiple workflows running with same agent ID

**Solution**: Ensure all workflows using the same agent have matching concurrency groups:

```yaml
concurrency:
  group: layercode-gym-${{ secrets.LAYERCODE_AGENT_ID }}
  cancel-in-progress: false
```

## Advanced Usage

### Conditional Judging

Enable judge only on main branch:

```yaml
- uses: ./.github/actions/layercode-gym-test
  with:
    judge-enabled: ${{ github.ref == 'refs/heads/main' }}
    judge-criteria: "..."
```

### Matrix Testing

Test multiple scenarios with matrix strategy:

```yaml
strategy:
  matrix:
    persona-type: [customer, developer, partner]

steps:
  - uses: ./.github/actions/layercode-gym-test
    with:
      personas: ${{ matrix.persona-type == 'customer' && '...' || '...' }}
```

### Custom Artifact Naming

```yaml
- uses: actions/upload-artifact@v4
  with:
    name: gym-results-${{ matrix.persona-type }}-${{ github.sha }}
    path: conversations/
```

## Related Resources

- [LayerCode Gym Documentation](../../../docs/)
- [LayerCode REST API Docs](https://docs.layercode.com/api-reference/rest-api)
- [Example Workflows](../../workflows/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)

## Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/layercode-gym/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/layercode-gym/discussions)
- **LayerCode Docs**: [docs.layercode.com](https://docs.layercode.com)
