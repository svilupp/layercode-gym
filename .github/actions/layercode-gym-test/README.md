# LayerCode Gym Test Action

A GitHub Action for running automated conversational AI tests using LayerCode Gym. Test your voice agents with multiple personas in parallel and get automated quality evaluations.

## Features

- **Multiple Personas**: Test with multiple user personas simultaneously
- **Scripted Conversations**: Run deterministic tests with fixed message sequences
- **Parallel Execution**: All conversations run concurrently for maximum speed
- **Automated Judging**: Optional LLM-based evaluation with pass/fail criteria
- **Detailed Reports**: Conversation transcripts, audio recordings, and judge feedback
- **Observability**: Optional LogFire integration for deep insights
- **Artifacts**: Automatic upload of all test results

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
            - background: You are a 35-year-old small business owner interested in AI
              intent: Learn about voice AI capabilities and pricing

            - background: You are a technical developer evaluating voice APIs
              intent: Understand technical integration requirements
          max-turns: 5
          judge-enabled: true
          judge-criteria: |
            - Did the agent provide clear information?
            - Did the agent offer a demo or next steps?
          server-url: ${{ secrets.SERVER_URL }}
          layercode-agent-id: ${{ secrets.LAYERCODE_AGENT_ID }}
          openai-api-key: ${{ secrets.OPENAI_API_KEY }}
          logfire-token: ${{ secrets.LOGFIRE_TOKEN }}
```

## Inputs

### Required Inputs

#### `personas`
**Type**: YAML list
**Description**: List of conversation configurations. Supports two formats that can be mixed:

**1. AI Persona (dynamic, AI-driven responses)**:
- `background`: Who the user is (context, role, characteristics)
- `intent`: What they want to achieve

**2. Scripted Messages (deterministic, fixed responses)**:
- `messages`: List of exact messages to send in sequence

**Example (AI personas)**:
```yaml
personas: |
  - background: You are a frustrated customer who has been waiting on hold
    intent: Cancel your subscription immediately

  - background: You are a potential customer researching solutions
    intent: Learn about features and pricing
```

**Example (scripted conversations)**:
```yaml
personas: |
  - messages:
      - Hello, I need to check my account balance
      - Yes, my account number is 12345
      - Thank you, goodbye
```

**Example (mixed)**:
```yaml
personas: |
  # AI-driven persona for dynamic testing
  - background: You are a frustrated customer
    intent: Get a refund for a broken product

  # Scripted conversation for regression testing
  - messages:
      - Hello, what are your business hours?
      - Do you have weekend support?
      - Thanks, goodbye
```

#### `server-url`
**Type**: String
**Description**: Your backend server URL that communicates with LayerCode
**Example**: `https://your-backend.com`

#### `layercode-agent-id`
**Type**: String (secret)
**Description**: Your LayerCode agent ID from the dashboard
**Where to find**: LayerCode Dashboard → Your Agent → Settings

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
**Type**: YAML list (one criterion per line, prefixed with `- `)
**Default**: `- Did the assistant provide helpful and accurate information?`
**Description**: List of yes/no criteria for the judge to evaluate. Each criterion is evaluated independently, and all must pass for overall success.

**Example**:
```yaml
judge-criteria: |
  - Did the agent greet the user appropriately?
  - Did the agent provide accurate pricing information?
  - Did the agent offer a demo or next steps?
```

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
**Default**: `openai:gpt-5-mini`
**Description**: AI model for personas
**Options**:
- `openai:gpt-5-mini` (fast, cost-effective)
- `openai:gpt-5` (more capable)
- `anthropic:claude-sonnet-4-5` (highest quality)
- `anthropic:claude-haiku-4` (fast)

#### `upload-artifacts`
**Type**: Boolean
**Default**: `true`
**Description**: Upload conversation transcripts and recordings as GitHub artifacts

#### `store-audio`
**Type**: Boolean
**Default**: `false`
**Description**: Store audio files for each conversation turn. Disabled by default for faster CI execution (judge only needs text transcripts).
**Note**: Requires ffmpeg to be installed on the runner if enabled.

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
            - background: You are a frustrated customer who has been overcharged
              intent: Get a refund and explanation

            - background: You are a happy customer wanting to upgrade
              intent: Learn about premium features

            - background: You are a confused new user
              intent: Understand how to get started
          max-turns: 7
          judge-enabled: true
          judge-criteria: |
            - Did the agent address the customer's concern directly?
            - Was the agent empathetic and professional?
            - Did the agent provide clear next steps or solutions?
            - Did the agent avoid leaving the customer confused?
          fail-on-judge-failure: true
          model: openai:gpt-5-mini
          server-url: ${{ secrets.SERVER_URL }}
          layercode-agent-id: ${{ secrets.LAYERCODE_AGENT_ID }}
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
            - background: You are a developer evaluating the API
              intent: Understand authentication, rate limits, and SDKs

            - background: You are a DevOps engineer setting up monitoring
              intent: Learn about webhooks, logging, and error handling
          max-turns: 10
          judge-enabled: true
          judge-criteria: |
            - Did the agent provide accurate technical information?
            - Did the agent provide relevant documentation links?
          model: anthropic:claude-sonnet-4-5
          server-url: ${{ secrets.SERVER_URL }}
          layercode-agent-id: ${{ secrets.LAYERCODE_AGENT_ID }}
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

**`judge_evaluation.json`** (when judge enabled) contains:
- `schema_version`: Format version for compatibility
- `evaluated_at`: ISO timestamp of evaluation
- `model`: Model used for judging (e.g., `openai:gpt-5-mini`)
- `criteria`: Original criteria definitions
- `judgment`: Raw model output with `criteria_results`, `overall_pass`, and `reasoning`
- `results_summary`: Combined view with criteria text and pass/fail status

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

Good criteria are specific, measurable yes/no questions:

```yaml
judge-criteria: |
  - Did the agent greet the user by name (if provided)?
  - Did the agent provide at least 2 specific product recommendations?
  - Did the agent mention the return policy?
  - Did the agent end with a clear call-to-action?
```

### 6. Use Different Models for Different Needs

- `openai:gpt-5-mini`: Fast, cost-effective, good for most tests
- `anthropic:claude-sonnet-4-5`: Complex conversations, high accuracy
- `openai:gpt-5`: Balance of speed and capability

## Troubleshooting

### "No module named 'layercode_gym'"

**Cause**: Installation issue with `uvx`

**Solution**: This should auto-resolve. If persistent, file an issue at [layercode-gym repo](https://github.com/svilupp/layercode-gym/issues)

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

### Update Webhook URL for PR Testing

Before running tests, you may need to point your LayerCode agent to a PR-specific backend URL. Use the `api-agents` CLI:

```yaml
steps:
  - name: Update webhook to PR backend
    run: |
      # Save original webhook
      ORIGINAL=$(uvx layercode-gym api-agents get \
        --agent-id ${{ secrets.LAYERCODE_AGENT_ID }} \
        --json | jq -r .webhook_url)
      echo "original=$ORIGINAL" >> $GITHUB_OUTPUT
    env:
      LAYERCODE_API_KEY: ${{ secrets.LAYERCODE_API_KEY }}

  - name: Point agent to PR backend
    run: |
      uvx layercode-gym api-agents update \
        --agent-id ${{ secrets.LAYERCODE_AGENT_ID }} \
        --webhook-url https://pr-${{ github.event.pull_request.number }}.example.com/webhook
    env:
      LAYERCODE_API_KEY: ${{ secrets.LAYERCODE_API_KEY }}

  - name: Run tests
    uses: ./.github/actions/layercode-gym-test
    with:
      # ... your config

  - name: Restore original webhook
    if: always()
    run: |
      uvx layercode-gym api-agents update \
        --agent-id ${{ secrets.LAYERCODE_AGENT_ID }} \
        --webhook-url ${{ steps.save-webhook.outputs.original }}
    env:
      LAYERCODE_API_KEY: ${{ secrets.LAYERCODE_API_KEY }}
```

See the [`api-agents` CLI documentation](../../../docs/api-agents.md) for more details.

### Conditional Judging

Enable judge only on main branch:

```yaml
- uses: ./.github/actions/layercode-gym-test
  with:
    judge-enabled: ${{ github.ref == 'refs/heads/main' }}
    judge-criteria: |
      - Did the agent provide accurate information?
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
- [`api-agents` CLI](../../../docs/api-agents.md) - Swap webhook URLs for PR backend testing
- [Example Workflows](../../workflows/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)

## Support

- **Issues**: [GitHub Issues](https://github.com/svilupp/layercode-gym/issues)
- **Discussions**: [GitHub Discussions](https://github.com/svilupp/layercode-gym/discussions)
- **LayerCode Docs**: [docs.layercode.com](https://docs.layercode.com)
