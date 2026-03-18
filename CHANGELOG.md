# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## 0.9.0 - 2026-03-18

### Fixed
- `_extract_webhook_url` now reads from `config.plugins[n].options.url` with fallback to `config.endpoint`, fixing false "Webhook update failed" errors after a vendor API schema change
- `tunnel` now passes `--config /dev/null` by default, preventing `~/.cloudflared/config.yml` ingress rules from silently returning 404 on quick tunnels

### Added
- `--cloudflared-args` CLI flag and `extra_cloudflared_args` constructor param to pass custom flags to `cloudflared tunnel`; replaces the default when provided

## 0.8.0 - 2025-02-02

### Fixed
- Race condition in playback acknowledgment where turn_id could change during sleep
- Premature WebSocket closure that could interrupt in-flight user messages
- Lost final assistant message when conversation concludes via max_turns
- Binary Event replaced with Queue for turn signals to prevent signal loss under load
- Empty assistant turns no longer recorded when idle timeout fires before content arrives

## 0.7.0 - 2026-01-01

### Added
- Wait/yield pattern for AI personas testing long-running operations (API calls, browser automation)
- Smart turn-taking with `enable_smart_turn_taking` option on `LayercodeClient`

### Breaking Changes
- **Custom agents must return `RespondToAssistant`/`WaitForAssistant` instead of `str`** - built-in agent handles this automatically

## 0.6.0 - 2025-12-12

### Added
- `--agent-path` CLI option and `LAYERCODE_AGENT_PATH` env var to customize webhook path (defaults to existing webhook path or `/api/agent`)

## 0.5.1 - 2025-12-12

### Fixed
- `tunnel` command now verifies webhook updates actually persist instead of assuming success

## 0.5.0 - 2025-12-11

### Added
- `tunnel` CLI command to start a Cloudflare tunnel with optional auto-webhook update (see the docs)
- `--request-timeout` CLI flag to configure authorization request timeout (default: 10s)

## 0.4.0 - 2025-12-05

### Added
- Enhanced `judge_evaluation.json` with full metadata: model, timestamp, criteria, additional context, and raw judgment output

## 0.3.0 - 2025-12-04

### Added
- Support for camelCase authorization response keys (`clientSessionKey`, `conversationId`) in addition to snake_case, enabling compatibility with more backend implementations

### Fixed
- Fixed idle timeout not triggering on resumed conversations where backend skips welcome message
- Made `turn_id` optional in `response.audio`, `response.text`, and `response.data` events for backend compatibility

## 0.2.0 - 2025-12-03

### Added
- Custom metadata, custom headers, and authorization headers support for LayerCode authorization requests (library, CLI, and GitHub Action)

## 0.1.1 - 2025-12-02

### Fixed
- Fixed JSON deserialization of conversation logs in CI runner's judge evaluation

## 0.1.0 - 2025-12-02

### Added
- CriteriaJudge: LLM-as-Judge for evaluating conversations against user-defined true/false criteria with structured output
- ResponseDataProcessor: Process `response.data` events into text so the AI simulator can "see" tool call results
- `api-agents` CLI to manage Layercode agents (eg, swap webhook URLs for CI to test PRs)
- GitHub Action for automated CI/CD testing with parallel personas and LLM judging

### Updated
- Changed default models to `gpt-5-mini` for more realistic conversation simulations
- Main gym runner grouped under `layercode-gym run` CLI command

## 0.0.1 - 2025-11-02

- Initial alpha release