# Roadmap

Planned enhancements and future features for LayerCode Gym.

## Short-term (Next Release)

### Audio Effects

Leverage Pydub to simulate real-world audio conditions:

- **Background Noise Injection**: Add cafe chatter, office sounds, street noise
- **Loud Conversations**: Simulate users in noisy environments
- **Accent Stress Testing**: Use TTS with accent instructions to test transcription
- **Audio Quality Degradation**: Test with compressed/low-quality audio
- **Connection Quality**: Simulate packet loss and bandwidth limitations

**Example API:**

```python
from layercode_gym.audio import AudioEffects

effects = AudioEffects(
    background_noise="cafe",  # cafe, office, street, none
    noise_level=0.3,          # 0.0 to 1.0
    quality="medium"          # low, medium, high
)

simulator = UserSimulator.from_text(
    messages=["Hello!"],
    send_as_text=False,
    audio_effects=effects
)
```

### Enhanced Simulators

- **CSV-driven Scenarios**: Load test scenarios from CSV files
- **Interrupt Patterns**: Test barge-in and interruption handling
- **Multi-language Personas**: Built-in support for multiple languages
- **Emotion Simulation**: Add emotional context to personas

**Example API:**

```python
# CSV-driven scenarios
simulator = UserSimulator.from_csv(
    file="scenarios.csv",
    text_column="user_message",
    metadata_columns=["expected_intent", "difficulty"]
)

# Interrupt patterns
simulator = UserSimulator.from_interrupts(
    base_messages=["Hello", "I want to..."],
    interrupt_probability=0.3,  # 30% chance to interrupt
    interrupt_messages=["Wait!", "Hold on"]
)
```

---

## Mid-term (Next 3 Months)

### Evaluation Tools

Built-in metrics and scoring:

- **Conversation Quality Metrics**: Automated scoring for fluency, coherence, task completion
- **Intent Recognition Accuracy**: Track if agent understood user intent
- **Regression Detection**: Automatically detect performance degradation
- **Benchmark Suites**: Pre-built test suites for common use cases

**Example API:**

```python
from layercode_gym.evaluation import (
    IntentAccuracyMetric,
    FlowCoherenceMetric,
    RegressionDetector
)

# Add metrics
metrics = [
    IntentAccuracyMetric(expected_intents=["pricing", "features"]),
    FlowCoherenceMetric(min_score=0.7)
]

client = LayercodeClient(
    simulator=simulator,
    metrics=metrics
)

# Regression detection
detector = RegressionDetector(
    baseline_dir="conversations/baseline/",
    threshold=0.1  # 10% degradation tolerance
)

is_regression = detector.check(conversation_id)
```

### A/B Testing Framework

Simplified A/B testing:

```python
from layercode_gym.testing import ABTest

test = ABTest(
    name="greeting_test",
    variant_a_agent_id="agent_v1",
    variant_b_agent_id="agent_v2",
    scenarios=["Hello!", "Hi there!", "Good morning!"],
    num_runs_per_variant=50
)

results = await test.run()
print(results.summary())  # Statistical comparison
```

### Dataset Generation

Generate training datasets from conversations:

```python
from layercode_gym.datasets import ConversationDataset

# Generate dataset from conversations
dataset = ConversationDataset.from_conversations(
    conversations_dir="conversations/",
    format="jsonl",  # jsonl, csv, parquet
    include_audio=True
)

# Export for fine-tuning
dataset.export("training_data.jsonl")
```

---

## Long-term (Next 6-12 Months)

### Real-time Monitoring Dashboard

Web-based dashboard for live conversation monitoring:

- Real-time conversation visualization
- Performance metrics graphs
- Alert system for failures
- Historical trend analysis

```bash
# Start monitoring server
layercode-gym monitor --port 8080

# View at http://localhost:8080
```

### Multi-Agent Scenarios

Support for multi-party conversations:

```python
# Simulate group conversation
scenario = MultiAgentScenario(
    agents=[
        ("customer", customer_persona),
        ("support", support_agent_id),
        ("manager", manager_agent_id)
    ],
    conversation_flow="customer escalates to manager"
)
```

### Integration Testing

Test complete flows including backend logic:

```python
from layercode_gym.integration import IntegrationTest

test = IntegrationTest(
    name="booking_flow",
    steps=[
        ("user", "I want to book an appointment"),
        ("agent", "What day works for you?"),
        ("user", "Tomorrow at 2pm"),
        ("verify_database", "appointment_created"),
        ("verify_email", "confirmation_sent")
    ]
)
```

### Performance Benchmarking

Compare against industry benchmarks:

```python
from layercode_gym.benchmarks import IndustryBenchmark

benchmark = IndustryBenchmark(
    category="customer_support",
    metrics=["response_time", "resolution_rate", "satisfaction"]
)

score = benchmark.compare(conversation_ids)
print(f"Your agent scores {score.percentile}th percentile")
```

---

## Community Requests

Features requested by the community:

### Voice Biometrics Testing

Test speaker verification and identification:

```python
simulator = UserSimulator.from_voice_samples(
    speaker_profiles=["speaker1.wav", "speaker2.wav"],
    test_speaker_id=True
)
```

### Conversation Replay

Replay and modify past conversations:

```python
from layercode_gym.replay import ConversationReplay

replay = ConversationReplay(
    conversation_id="conv_abc123",
    modify_turn=3,  # Change turn 3
    new_message="Different response"
)

new_conv_id = await replay.run()
```

### Webhook Integration

Real-time notifications:

```python
from layercode_gym.webhooks import WebhookNotifier

notifier = WebhookNotifier(
    url="https://your-server.com/webhook",
    events=["conversation_end", "error"]
)

client = LayercodeClient(
    simulator=simulator,
    notifier=notifier
)
```

### Export to Video

Generate video demonstrations:

```python
from layercode_gym.export import VideoExporter

exporter = VideoExporter()
exporter.create_video(
    conversation_id="conv_abc123",
    output="demo.mp4",
    include_subtitles=True,
    avatar="default"  # Animated avatar
)
```

---

## Platform Support

### Additional LLM Providers

- Cohere
- Together AI
- Replicate
- Local LLaMA via llama.cpp

### Additional TTS Providers

- Google Cloud TTS
- Amazon Polly
- PlayHT
- Coqui TTS (local)

### Additional Observability

- Datadog integration
- New Relic integration
- Prometheus metrics
- Grafana dashboards

---

## Developer Experience

### CLI Tool

```bash
# Quick start
layercode-gym init my-project
layercode-gym run scenario.yml
layercode-gym analyze conversations/

# Report generation
layercode-gym report --format html conversations/

# Continuous testing
layercode-gym watch tests/ --on-change run
```

### VS Code Extension

- Syntax highlighting for scenario files
- IntelliSense for API
- Run tests from editor
- View results inline

### Docker Support

```bash
# Run in container
docker run layercode-gym \
  -e SERVER_URL=http://host.docker.internal:8001 \
  -e AGENT_ID=your_agent_id \
  -v $(pwd)/conversations:/conversations \
  python examples/01_text_messages.py
```

---

## Performance Goals

Target metrics for future releases:

- **Conversation Throughput**: 1000+ concurrent conversations
- **Startup Time**: < 100ms per conversation
- **Memory Usage**: < 50MB per active conversation
- **Test Execution**: < 1s for simple text scenarios

---

## Contributing

Want to help build these features?

- Check [GitHub Issues](https://github.com/svilupp/layercode-gym/issues) for current work
- Join discussions in GitHub Discussions
- Submit PRs for features you'd like to see
- Share your use cases and requirements

## Feedback

Have ideas for the roadmap?

- Open a feature request on GitHub
- Share your use case
- Vote on existing proposals
- Contribute to discussions

---

## Version History

### v0.0.1 (Current)

- Core client implementation
- Three simulator types (text, files, agent)
- LogFire integration
- Basic callbacks and evaluation
- Example scripts

### Planned Releases

- **v0.1.0**: Audio effects, CSV scenarios, enhanced metrics
- **v0.2.0**: A/B testing framework, regression detection
- **v0.3.0**: Real-time dashboard, dataset generation
- **v1.0.0**: Production-ready with full feature set

---

## Community

This is an unofficial project maintained by the community. Contributions and feedback are always welcome.

- [GitHub Repository](https://github.com/svilupp/layercode-gym)
- [Issue Tracker](https://github.com/svilupp/layercode-gym/issues)
- [Discussions](https://github.com/svilupp/layercode-gym/discussions)
