# GitHub Actions Integration

Run automated tests for your voice agents in CI/CD pipelines with the LayerCode Gym GitHub Action.

## Overview

The LayerCode Gym GitHub Action enables you to:

- **Test multiple personas** in parallel for maximum speed
- **Automated judging** with LLM-based quality evaluation
- **Track quality over time** with historical test results
- **Continuous regression testing** on every commit
- **Zero setup complexity** - just configure and run

## Quick Start

### 1. Set Up Secrets

Go to your repository: **Settings → Secrets and variables → Actions → New repository secret**

Add these required secrets:

| Secret Name | Description | Where to Get |
|------------|-------------|--------------|
| `SERVER_URL` | Your backend server URL | Your infrastructure |
| `LAYERCODE_AGENT_ID` | LayerCode agent ID | [LayerCode Dashboard](https://layercode.com/dashboard) |
| `OPENAI_API_KEY` | OpenAI API key | [OpenAI Platform](https://platform.openai.com/api-keys) |

Optional but recommended:

| Secret Name | Description |
|------------|-------------|
| `LOGFIRE_TOKEN` | LogFire token for observability |

### 2. Create Workflow File

Create `.github/workflows/test-agent.yml`:

```yaml
name: Test Voice Agent
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    # IMPORTANT: Prevent concurrent runs
    concurrency:
      group: layercode-gym-${{ secrets.LAYERCODE_AGENT_ID }}
      cancel-in-progress: false

    steps:
      - uses: actions/checkout@v4

      - name: Test agent
        uses: ./.github/actions/layercode-gym-test
        with:
          personas: |
            [
              {
                "background": "You are a potential customer",
                "intent": "Learn about pricing and features"
              }
            ]
          judge-enabled: true
          judge-criteria: "Agent provides clear pricing info"
          server-url: ${{ secrets.SERVER_URL }}
          layercode-agent-id: ${{ secrets.LAYERCODE_AGENT_ID }}
          openai-api-key: ${{ secrets.OPENAI_API_KEY }}
```

### 3. Run Your Tests

Push your code and watch the tests run automatically!

## Configuration

### Personas

Personas define the users you want to simulate. Each persona has:

- **`background`**: Who the user is (role, context, characteristics)
- **`intent`**: What they want to achieve

```yaml
personas: |
  [
    {
      "background": "You are a 35-year-old small business owner interested in AI",
      "intent": "Learn how voice AI can help your customer service"
    },
    {
      "background": "You are a technical developer evaluating APIs",
      "intent": "Understand integration requirements and documentation"
    }
  ]
```

**Tips for writing good personas:**

- Be specific about who the user is
- Include relevant context (frustrations, goals, technical level)
- Make intents clear and actionable
- Avoid making personas too similar
- Avoid making intents too vague

### Judge Criteria

The judge evaluates whether conversations meet your quality standards.

**Good criteria are:**
- Specific and measurable
- Focused on agent behavior
- Clear pass/fail conditions

**Examples:**

```yaml
# Simple criteria
judge-criteria: "Agent provides accurate product information"

# Detailed criteria
judge-criteria: |
  The agent must:
  1. Greet the user professionally
  2. Answer all questions with accurate information
  3. Offer next steps (demo, documentation, contact)
  4. Maintain a helpful and empathetic tone throughout

# Domain-specific criteria
judge-criteria: |
  Technical requirements:
  - Agent must mention API authentication methods
  - Agent must provide documentation links
  - Agent must explain rate limits
  - Agent must not provide incorrect technical details
```

### Full Configuration Options

See the [Action README](.github/actions/layercode-gym-test/README.md) for complete documentation of all inputs and outputs.

## Use Cases

### Regression Testing

Run tests on every push to catch regressions:

```yaml
name: Regression Tests
on: [push, pull_request]

jobs:
  regression:
    runs-on: ubuntu-latest
    concurrency:
      group: layercode-gym-${{ secrets.LAYERCODE_AGENT_ID }}
      cancel-in-progress: false

    steps:
      - uses: actions/checkout@v4
      - uses: ./.github/actions/layercode-gym-test
        with:
          personas: |
            [
              {"background": "Returning customer", "intent": "Check order status"},
              {"background": "New user", "intent": "Create account"},
              {"background": "Support case", "intent": "Report a bug"}
            ]
          judge-enabled: true
          judge-criteria: "Agent handles request correctly without errors"
          server-url: ${{ secrets.SERVER_URL }}
          layercode-agent-id: ${{ secrets.LAYERCODE_AGENT_ID }}
          openai-api-key: ${{ secrets.OPENAI_API_KEY }}
```

### Nightly Quality Checks

Run comprehensive tests daily:

```yaml
name: Nightly Quality Checks
on:
  schedule:
    - cron: '0 2 * * *'  # 2 AM daily

jobs:
  quality:
    runs-on: ubuntu-latest
    concurrency:
      group: layercode-gym-${{ secrets.LAYERCODE_AGENT_ID }}
      cancel-in-progress: false

    steps:
      - uses: actions/checkout@v4
      - uses: ./.github/actions/layercode-gym-test
        with:
          personas: |
            [
              {"background": "Happy customer", "intent": "Provide positive feedback"},
              {"background": "Angry customer", "intent": "Demand refund"},
              {"background": "Confused user", "intent": "Understand product features"},
              {"background": "Price-sensitive shopper", "intent": "Find cheapest option"},
              {"background": "Enterprise buyer", "intent": "Discuss bulk pricing"}
            ]
          max-turns: 10
          judge-enabled: true
          judge-criteria: |
            Agent must:
            - Adapt tone to user's emotional state
            - Provide accurate information
            - Offer appropriate solutions
            - Maintain professionalism
          model: anthropic:claude-sonnet-4-5  # Use best model for quality checks
          server-url: ${{ secrets.SERVER_URL }}
          layercode-agent-id: ${{ secrets.LAYERCODE_AGENT_ID }}
          openai-api-key: ${{ secrets.OPENAI_API_KEY }}
          logfire-token: ${{ secrets.LOGFIRE_TOKEN }}
```

### Pre-Deployment Validation

Require tests to pass before deploying:

```yaml
name: Deploy Pipeline
on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    concurrency:
      group: layercode-gym-${{ secrets.LAYERCODE_AGENT_ID }}
      cancel-in-progress: false

    steps:
      - uses: actions/checkout@v4
      - name: Run pre-deployment tests
        uses: ./.github/actions/layercode-gym-test
        with:
          personas: |
            [
              {"background": "Critical user journey 1", "intent": "Complete purchase"},
              {"background": "Critical user journey 2", "intent": "Get support"},
              {"background": "Critical user journey 3", "intent": "Update account"}
            ]
          judge-enabled: true
          judge-criteria: "All critical paths work without errors"
          fail-on-judge-failure: true  # Block deployment on failure
          server-url: ${{ secrets.SERVER_URL }}
          layercode-agent-id: ${{ secrets.LAYERCODE_AGENT_ID }}
          openai-api-key: ${{ secrets.OPENAI_API_KEY }}

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to production
        run: echo "Deploying..."
```

### A/B Testing Different Agent Versions

Test changes against baseline:

```yaml
name: A/B Test Agent Changes

on: [pull_request]

jobs:
  test-baseline:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: main  # Test against main branch

      - uses: ./.github/actions/layercode-gym-test
        id: baseline
        with:
          personas: ${{ env.TEST_PERSONAS }}
          judge-enabled: true
          # ... other config

  test-changes:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4  # Test with PR changes

      - uses: ./.github/actions/layercode-gym-test
        id: changes
        with:
          personas: ${{ env.TEST_PERSONAS }}
          judge-enabled: true
          # ... other config

  compare:
    needs: [test-baseline, test-changes]
    runs-on: ubuntu-latest
    steps:
      - name: Compare results
        run: |
          echo "Baseline: ${{ needs.test-baseline.outputs.conversations-passed }} passed"
          echo "Changes: ${{ needs.test-changes.outputs.conversations-passed }} passed"
```

## Best Practices

### 1. Use Concurrency Control

Always add concurrency control to prevent webhook conflicts:

```yaml
concurrency:
  group: layercode-gym-${{ secrets.LAYERCODE_AGENT_ID }}
  cancel-in-progress: false
```

LayerCode agents support one webhook at a time. The concurrency group ensures tests don't overlap.

### 2. Start Small, Scale Up

Begin with a few core personas and add more over time:

```yaml
# Week 1: Core happy paths
personas: [happy_customer, new_user]

# Week 2: Add edge cases
personas: [happy_customer, new_user, frustrated_customer]

# Week 3: Comprehensive coverage
personas: [happy_customer, new_user, frustrated_customer,
           technical_user, enterprise_buyer, ...]
```

### 3. Use Different Models for Different Tests

- **Fast CI (PR checks)**: `openai:gpt-4o-mini`
- **Nightly quality**: `anthropic:claude-sonnet-4-5`
- **Critical path**: `openai:gpt-4o`

```yaml
# Fast PR checks
- uses: ./.github/actions/layercode-gym-test
  with:
    model: openai:gpt-4o-mini  # Fast and cheap
    max-turns: 3

# Comprehensive nightly
- uses: ./.github/actions/layercode-gym-test
  with:
    model: anthropic:claude-sonnet-4-5  # High quality
    max-turns: 10
```

### 4. Enable LogFire for Production Tests

Set `LOGFIRE_TOKEN` for deep observability:

- Real-time conversation monitoring
- Performance metrics
- Debugging failed tests
- Historical trends

```yaml
- uses: ./.github/actions/layercode-gym-test
  with:
    logfire-token: ${{ secrets.LOGFIRE_TOKEN }}  # Enable observability
    # ... other config
```

### 5. Create Separate Jobs for Different Test Suites

Organize tests into logical groups:

```yaml
jobs:
  test-happy-paths:
    # Test successful scenarios

  test-error-handling:
    # Test edge cases and errors

  test-security:
    # Test authentication, authorization

  test-performance:
    # Test with long conversations
```

### 6. Archive Important Test Runs

Keep artifacts for critical tests:

```yaml
- uses: ./.github/actions/layercode-gym-test
  with:
    upload-artifacts: true

- uses: actions/upload-artifact@v4
  with:
    name: production-validation-${{ github.sha }}
    path: conversations/
    retention-days: 90  # Keep for 90 days
```

## Troubleshooting

### Tests Timing Out

**Symptom**: Conversations don't complete

**Solutions**:
- Verify `SERVER_URL` is correct and accessible
- Check server logs for errors
- Increase `max-turns` if legitimate
- Reduce number of personas to isolate issue

### Judge Always Failing

**Symptom**: All conversations fail judge evaluation

**Solutions**:
- Review judge feedback in artifacts
- Simplify criteria to isolate issue
- Test locally first with CLI
- Set `fail-on-judge-failure: false` temporarily

### Concurrent Run Conflicts

**Symptom**: Tests interfere with each other

**Solution**: Ensure all workflows have matching concurrency groups:

```yaml
concurrency:
  group: layercode-gym-${{ secrets.LAYERCODE_AGENT_ID }}
  cancel-in-progress: false
```

## Advanced Topics

### Custom Post-Processing

Process results after tests complete:

```yaml
- uses: ./.github/actions/layercode-gym-test
  id: test
  with:
    # ... config

- name: Analyze results
  run: |
    python scripts/analyze_results.py \
      --results-dir ${{ steps.test.outputs.results-path }} \
      --passed ${{ steps.test.outputs.conversations-passed }} \
      --failed ${{ steps.test.outputs.conversations-failed }}
```

### Integration with Other Tools

Send results to external systems:

```yaml
- name: Send to Slack
  if: failure()
  uses: slackapi/slack-github-action@v1
  with:
    payload: |
      {
        "text": "Voice agent tests failed: ${{ steps.test.outputs.conversations-failed }} conversations"
      }
```

### Matrix Testing

Test multiple configurations:

```yaml
strategy:
  matrix:
    agent-version: [v1, v2]
    model: [openai:gpt-4o-mini, anthropic:claude-sonnet-4-5]

steps:
  - uses: ./.github/actions/layercode-gym-test
    with:
      model: ${{ matrix.model }}
      # ... other config
```

## Next Steps

- [See complete action documentation](.github/actions/layercode-gym-test/README.md)
- [View example workflows](.github/workflows/example-gym-test.yml)
- [Read API reference](api-reference.md)
- [Explore advanced features](advanced.md)

## Support

- **Issues**: [GitHub Issues](https://github.com/svilupp/layercode-gym/issues)
- **Discussions**: [GitHub Discussions](https://github.com/svilupp/layercode-gym/discussions)
- **LayerCode Docs**: [docs.layercode.com](https://docs.layercode.com)
