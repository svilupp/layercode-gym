# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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