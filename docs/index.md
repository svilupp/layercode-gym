# LayerCode Gym

**Does your voice AI agent even lift, bro?**

!!! warning "v0.0.1-alpha"
    This toolkit is an early alpha and may contain bugs or breaking changes. Please test thoroughly before using in production.

LayerCode Gym is an **unofficial** testing environment for voice AI agents built on [Layercode.com](https://layercode.com). It simulates real voice clients end-to-end, allowing you to run hundreds of test scenarios and understand how your agent will perform in production.

## Why LayerCode Gym?

Voice AI agents are complex systems with many failure modes:

- Transcription errors under various audio conditions
- Response latency and timing issues
- Conversation flow and context handling
- Edge cases and unexpected user inputs

LayerCode Gym helps you catch these issues before production by providing a comprehensive testing framework that simulates real-world usage at scale.

## Key Features

### Three Types of User Simulators

1. **Fixed Text Messages** - Send predetermined text responses (fastest, perfect for regression testing)
2. **Pre-recorded Audio Files** - Stream audio files to stress-test transcription and agent behavior
3. **AI Agent Personas** - Use PydanticAI to simulate realistic users with specific personalities and goals

### Comprehensive Analytics

After each conversation, get:

- Full transcript with timing metrics (TTFAB, latency stats)
- Combined audio file for playback review
- Turn-by-turn conversation logs
- Optional LLM-as-judge scoring via callbacks

### Scale Testing

- Run hundreds of conversations concurrently
- Batch evaluation with progress tracking
- Automated regression detection
- Load testing capabilities

### Pluggable Architecture

- Custom TTS engines (ElevenLabs, Azure, etc.)
- Custom LLM providers via PydanticAI
- Custom evaluation callbacks
- Extensible simulator protocols

## Quick Example

```python
from layercode_gym import LayercodeClient, UserSimulator

# Create a simple text-based simulator
simulator = UserSimulator.from_text(
    messages=[
        "Hello! I'm interested in your services.",
        "Tell me more about pricing.",
        "Thank you, goodbye."
    ],
    send_as_text=True  # Fast, no TTS needed
)

# Run the conversation
client = LayercodeClient(simulator=simulator)
conversation_id = await client.run()

# Results saved to conversations/<conversation_id>/
```

## Who Is This For?

- **Voice AI developers** building production agents on Layercode
- **QA teams** needing automated testing for voice interfaces
- **Product teams** evaluating agent performance before launch
- **Researchers** studying voice AI behavior at scale

## What's Different?

Unlike manual testing in the Layercode dashboard:

- **Automated**: Run tests programmatically without manual intervention
- **Scalable**: Test hundreds of scenarios concurrently
- **Reproducible**: Version control your test scenarios
- **Measurable**: Get detailed metrics and analytics
- **Continuous**: Integrate with CI/CD pipelines

## Getting Started

Ready to test your voice AI agent? Head over to [Getting Started](getting-started.md) to set up LayerCode Gym and run your first test.

## Project Status

This is an **unofficial** project - not affiliated with or supported by Layercode. It's a community tool for developers who want to test their Layercode agents more thoroughly.

Contributions, bug reports, and feature requests are welcome on [GitHub](https://github.com/svilupp/layercode-gym).
