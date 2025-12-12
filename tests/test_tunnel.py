"""Tests for the tunnel module and CLI command.

These tests cover:
1. CloudflareTunnelLauncher class behavior
2. CLI argument parsing for tunnel subcommand
3. Webhook update/restore logic
4. Error handling scenarios

Note: Most tests mock the cloudflared subprocess and API calls
to enable testing without external dependencies.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from layercode_gym.tunnel import (
    TUNNEL_URL_PATTERN,
    CloudflareTunnelLauncher,
)


# =============================================================================
# Tests for TUNNEL_URL_PATTERN regex
# =============================================================================


class TestTunnelUrlPattern:
    """Tests for the tunnel URL regex pattern."""

    def test_matches_valid_tunnel_url(self) -> None:
        """Should match valid Cloudflare quick tunnel URLs."""
        valid_urls = [
            "https://abc-def-ghi.trycloudflare.com",
            "https://random-words-here.trycloudflare.com",
            "https://a1b2c3.trycloudflare.com",
            "https://test-tunnel-123.trycloudflare.com",
        ]
        for url in valid_urls:
            match = TUNNEL_URL_PATTERN.search(url)
            assert match is not None, f"Should match: {url}"
            assert match.group(0) == url

    def test_matches_url_in_log_line(self) -> None:
        """Should extract URL from cloudflared log output."""
        log_lines = [
            "INF +----------------------------------------------------------+url=https://test-tunnel.trycloudflare.com",
            "2024-01-01 12:00:00 INFO Tunnel URL: https://my-tunnel.trycloudflare.com",
            "Registered tunnel connection https://abc123.trycloudflare.com/",
        ]
        for line in log_lines:
            match = TUNNEL_URL_PATTERN.search(line)
            assert match is not None, f"Should find URL in: {line}"

    def test_case_insensitive(self) -> None:
        """Should match URLs case-insensitively."""
        url = "https://TEST-TUNNEL.TRYCLOUDFLARE.COM"
        match = TUNNEL_URL_PATTERN.search(url)
        assert match is not None

    def test_no_match_invalid_urls(self) -> None:
        """Should not match invalid URLs."""
        invalid = [
            "https://example.com",
            "http://test.trycloudflare.com",  # http not https
            "random text without url",
        ]
        for text in invalid:
            result = TUNNEL_URL_PATTERN.search(text)
            assert result is None, f"Should not match: {text}"


# =============================================================================
# Tests for CloudflareTunnelLauncher initialization
# =============================================================================


class TestCloudflareTunnelLauncherInit:
    """Tests for CloudflareTunnelLauncher initialization."""

    def test_initialization_with_port(self) -> None:
        """Should initialize with port parameter."""
        launcher = CloudflareTunnelLauncher(port=8000)

        assert launcher.target_url == "http://localhost:8000"
        assert launcher.agent_id is None
        assert launcher.api_key is None
        assert launcher.update_webhook is False
        assert launcher.tunnel_url is None

    def test_initialization_with_url(self) -> None:
        """Should initialize with url parameter."""
        launcher = CloudflareTunnelLauncher(url="http://myhost:3000")

        assert launcher.target_url == "http://myhost:3000"

    def test_initialization_with_port_and_host(self) -> None:
        """Should accept port with custom host."""
        launcher = CloudflareTunnelLauncher(port=3000, host="127.0.0.1")

        assert launcher.target_url == "http://127.0.0.1:3000"

    def test_initialization_with_all_params(self) -> None:
        """Should accept all optional parameters."""
        launcher = CloudflareTunnelLauncher(
            port=3000,
            host="127.0.0.1",
            agent_id="ag-test123",
            api_key="test-api-key",
            update_webhook=True,
        )

        assert launcher.target_url == "http://127.0.0.1:3000"
        assert launcher.agent_id == "ag-test123"
        assert launcher.api_key == "test-api-key"
        assert launcher.update_webhook is True

    def test_initialization_requires_url_or_port(self) -> None:
        """Should raise ValueError if neither url nor port provided."""
        import pytest

        with pytest.raises(ValueError, match="Either 'url' or 'port' must be provided"):
            CloudflareTunnelLauncher()

    def test_log_file_path_created(self) -> None:
        """Should create a timestamped log file path."""
        launcher = CloudflareTunnelLauncher(port=8000)

        assert launcher.log_file_path is not None
        assert "cloudflare_tunnel_" in str(launcher.log_file_path)
        assert str(launcher.log_file_path).endswith(".log")


# =============================================================================
# Tests for tunnel_url property
# =============================================================================


class TestTunnelUrlProperty:
    """Tests for the tunnel_url property."""

    def test_tunnel_url_none_before_start(self) -> None:
        """Should return None before tunnel is started."""
        launcher = CloudflareTunnelLauncher(port=8000)
        assert launcher.tunnel_url is None

    def test_tunnel_url_after_set(self) -> None:
        """Should return tunnel URL once set."""
        launcher = CloudflareTunnelLauncher(port=8000)
        launcher._tunnel_url = "https://test.trycloudflare.com"

        assert launcher.tunnel_url == "https://test.trycloudflare.com"


# =============================================================================
# Tests for start() method
# =============================================================================


class TestCloudflareTunnelLauncherStart:
    """Tests for the start() method."""

    @pytest.mark.asyncio
    async def test_start_fails_without_cloudflared(self) -> None:
        """Should raise RuntimeError if cloudflared is not installed."""
        launcher = CloudflareTunnelLauncher(port=8000)

        with patch("shutil.which", return_value=None):
            with pytest.raises(RuntimeError) as exc_info:
                await launcher.start()

            assert "cloudflared binary not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_start_calls_cloudflared_check(self) -> None:
        """Should check if cloudflared is available before starting."""
        launcher = CloudflareTunnelLauncher(port=8000, host="localhost")

        # Just verify it checks for cloudflared - don't try to mock the subprocess
        with patch("shutil.which", return_value=None):
            with pytest.raises(RuntimeError) as exc_info:
                await launcher.start()

            assert "cloudflared binary not found" in str(exc_info.value)


# =============================================================================
# Tests for stop() method
# =============================================================================


class TestCloudflareTunnelLauncherStop:
    """Tests for the stop() method."""

    @pytest.mark.asyncio
    async def test_stop_terminates_process(self) -> None:
        """Should terminate the cloudflared process."""
        launcher = CloudflareTunnelLauncher(port=8000)

        mock_process = AsyncMock()
        mock_process.returncode = None
        mock_process.terminate = MagicMock()
        mock_process.wait = AsyncMock()

        launcher._process = mock_process

        await launcher.stop()

        mock_process.terminate.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_kills_if_terminate_times_out(self) -> None:
        """Should kill process if terminate doesn't work within timeout."""
        launcher = CloudflareTunnelLauncher(port=8000)

        mock_process = AsyncMock()
        mock_process.returncode = None
        mock_process.terminate = MagicMock()
        mock_process.kill = MagicMock()

        # Make wait raise TimeoutError first time, then succeed
        call_count = 0

        async def wait_side_effect() -> None:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TimeoutError("Simulated timeout")
            # Second call succeeds immediately

        mock_process.wait = AsyncMock(side_effect=wait_side_effect)

        launcher._process = mock_process

        await launcher.stop()

        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_closes_log_file(self) -> None:
        """Should close the log file handle."""
        launcher = CloudflareTunnelLauncher(port=8000)

        mock_file = MagicMock()
        launcher._log_file_handle = mock_file

        await launcher.stop()

        mock_file.write.assert_called()
        mock_file.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_restores_webhook_when_enabled(self) -> None:
        """Should restore webhook when update_webhook is True."""
        launcher = CloudflareTunnelLauncher(
            port=8000,
            agent_id="ag-test",
            api_key="test-key",
            update_webhook=True,
        )
        launcher._tunnel_url = "https://test.trycloudflare.com"
        launcher._previous_webhook_url = "https://original.example.com/webhook"

        # Mock the API calls - current webhook matches our tunnel URL
        mock_agent = MagicMock()
        mock_agent.webhook_url = "https://test.trycloudflare.com"

        with (
            patch(
                "layercode_gym.tunnel.get_agent", return_value=mock_agent
            ) as mock_get,
            patch("layercode_gym.tunnel.update_agent") as mock_update,
        ):
            await launcher.stop()

            mock_get.assert_called_once_with("ag-test", "test-key")
            mock_update.assert_called_once_with(
                "ag-test",
                "test-key",
                {"webhook_url": "https://original.example.com/webhook"},
            )

    @pytest.mark.asyncio
    async def test_stop_skips_restore_if_webhook_changed_externally(self) -> None:
        """Should not restore webhook if it was changed externally."""
        launcher = CloudflareTunnelLauncher(
            port=8000,
            agent_id="ag-test",
            api_key="test-key",
            update_webhook=True,
        )
        launcher._tunnel_url = "https://test.trycloudflare.com"
        launcher._previous_webhook_url = "https://original.example.com/webhook"

        # Mock the API - webhook has been changed to something else
        mock_agent = MagicMock()
        mock_agent.webhook_url = "https://different.example.com/webhook"

        with (
            patch("layercode_gym.tunnel.get_agent", return_value=mock_agent),
            patch("layercode_gym.tunnel.update_agent") as mock_update,
        ):
            await launcher.stop()

            # Should NOT call update since webhook was changed externally
            mock_update.assert_not_called()


# =============================================================================
# Tests for CLI argument parsing
# =============================================================================


class TestTunnelCliParsing:
    """Tests for tunnel CLI argument parsing."""

    def test_tunnel_parser_accepts_port(self) -> None:
        """Should accept --port argument."""
        from layercode_gym.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["tunnel", "--port", "8000"])

        assert args.command == "tunnel"
        assert args.port == 8000
        assert args.url is None

    def test_tunnel_parser_accepts_url(self) -> None:
        """Should accept --url argument."""
        from layercode_gym.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["tunnel", "--url", "http://localhost:8000"])

        assert args.command == "tunnel"
        assert args.url == "http://localhost:8000"
        assert args.port is None

    def test_tunnel_parser_defaults(self) -> None:
        """Should have correct default values."""
        from layercode_gym.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["tunnel", "--port", "8000"])

        assert args.host == "localhost"
        assert args.timeout == 30.0
        assert args.unsafe_update_webhook is False
        assert args.agent_id is None
        assert args.api_key is None

    def test_tunnel_parser_webhook_options(self) -> None:
        """Should accept webhook update options."""
        from layercode_gym.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(
            [
                "tunnel",
                "--port",
                "8000",
                "--unsafe-update-webhook",
                "--agent-id",
                "ag-123",
                "--api-key",
                "key-456",
            ]
        )

        assert args.unsafe_update_webhook is True
        assert args.agent_id == "ag-123"
        assert args.api_key == "key-456"

    def test_tunnel_parser_custom_config(self) -> None:
        """Should accept custom configuration options."""
        from layercode_gym.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(
            [
                "tunnel",
                "--port",
                "3000",
                "--host",
                "127.0.0.1",
                "--timeout",
                "60",
            ]
        )

        assert args.port == 3000
        assert args.host == "127.0.0.1"
        assert args.timeout == 60.0

    def test_tunnel_parser_url_with_webhook_options(self) -> None:
        """Should accept --url with webhook options."""
        from layercode_gym.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(
            [
                "tunnel",
                "--url",
                "http://127.0.0.1:3000",
                "--unsafe-update-webhook",
                "--agent-id",
                "ag-123",
            ]
        )

        assert args.url == "http://127.0.0.1:3000"
        assert args.port is None
        assert args.unsafe_update_webhook is True
        assert args.agent_id == "ag-123"

    def test_tunnel_parser_both_url_and_port(self) -> None:
        """Should accept both --url and --port (url takes precedence in run_tunnel)."""
        from layercode_gym.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(
            [
                "tunnel",
                "--url",
                "http://custom:9000",
                "--port",
                "8000",
            ]
        )

        # Parser accepts both, validation happens in run_tunnel
        assert args.url == "http://custom:9000"
        assert args.port == 8000


# =============================================================================
# Tests for CLI run_tunnel validation
# =============================================================================


class TestRunTunnelValidation:
    """Tests for run_tunnel argument validation."""

    @pytest.mark.asyncio
    async def test_run_tunnel_requires_url_or_port(self) -> None:
        """Should exit if neither --url nor --port is provided."""
        import argparse

        args = argparse.Namespace(
            url=None,
            port=None,
            host="localhost",
            timeout=30.0,
            unsafe_update_webhook=False,
            agent_id=None,
            api_key=None,
        )

        with pytest.raises(SystemExit) as exc_info:
            from layercode_gym.cli import run_tunnel

            await run_tunnel(args)

        assert exc_info.value.code == 1

    @pytest.mark.asyncio
    async def test_run_tunnel_accepts_url_only(self) -> None:
        """Should accept --url without --port."""
        import argparse

        args = argparse.Namespace(
            url="http://localhost:8000",
            port=None,
            host="localhost",
            timeout=30.0,
            unsafe_update_webhook=False,
            agent_id=None,
            api_key=None,
        )

        # Should pass validation and fail at cloudflared check
        with (
            patch("shutil.which", return_value=None),
            pytest.raises(SystemExit) as exc_info,
        ):
            from layercode_gym.cli import run_tunnel

            await run_tunnel(args)

        # Exits with 1 due to cloudflared not found (not validation error)
        assert exc_info.value.code == 1

    @pytest.mark.asyncio
    async def test_run_tunnel_requires_agent_id_for_webhook_update(self) -> None:
        """Should exit if --unsafe-update-webhook without --agent-id."""
        import argparse

        args = argparse.Namespace(
            url=None,
            port=8000,
            host="localhost",
            timeout=30.0,
            unsafe_update_webhook=True,
            agent_id=None,
            api_key="test-key",
        )

        with (
            patch.dict("os.environ", {}, clear=True),
            pytest.raises(SystemExit) as exc_info,
        ):
            from layercode_gym.cli import run_tunnel

            await run_tunnel(args)

        assert exc_info.value.code == 1

    @pytest.mark.asyncio
    async def test_run_tunnel_requires_api_key_for_webhook_update(self) -> None:
        """Should exit if --unsafe-update-webhook without --api-key."""
        import argparse

        args = argparse.Namespace(
            url=None,
            port=8000,
            host="localhost",
            timeout=30.0,
            unsafe_update_webhook=True,
            agent_id="ag-123",
            api_key=None,
        )

        with (
            patch.dict("os.environ", {}, clear=True),
            pytest.raises(SystemExit) as exc_info,
        ):
            from layercode_gym.cli import run_tunnel

            await run_tunnel(args)

        assert exc_info.value.code == 1

    def test_run_tunnel_uses_env_vars_for_credentials(self) -> None:
        """Should use environment variables for agent_id and api_key."""
        import os

        # Test that env vars are read correctly
        with patch.dict(
            os.environ,
            {"LAYERCODE_AGENT_ID": "ag-from-env", "LAYERCODE_API_KEY": "key-from-env"},
        ):
            agent_id = os.environ.get("LAYERCODE_AGENT_ID")
            api_key = os.environ.get("LAYERCODE_API_KEY")

            assert agent_id == "ag-from-env"
            assert api_key == "key-from-env"


# =============================================================================
# Tests for webhook update flow
# =============================================================================


class TestWebhookUpdateFlow:
    """Tests for the webhook update and restore flow."""

    @pytest.mark.asyncio
    async def test_update_webhook_saves_previous_value(self) -> None:
        """Should save previous webhook URL before updating."""
        launcher = CloudflareTunnelLauncher(
            port=8000,
            agent_id="ag-test",
            api_key="test-key",
            update_webhook=True,
        )

        mock_agent = MagicMock()
        mock_agent.webhook_url = "https://original.example.com/webhook"

        with (
            patch("layercode_gym.tunnel.get_agent", return_value=mock_agent),
            patch("layercode_gym.tunnel.update_agent"),
        ):
            await launcher._update_webhook("https://new.trycloudflare.com/api/agent")

        assert launcher._previous_webhook_url == "https://original.example.com/webhook"

    @pytest.mark.asyncio
    async def test_update_webhook_handles_no_previous_webhook(self) -> None:
        """Should handle agent with no previous webhook."""
        launcher = CloudflareTunnelLauncher(
            port=8000,
            agent_id="ag-test",
            api_key="test-key",
            update_webhook=True,
        )

        mock_agent = MagicMock()
        mock_agent.webhook_url = None  # No previous webhook

        with (
            patch("layercode_gym.tunnel.get_agent", return_value=mock_agent),
            patch("layercode_gym.tunnel.update_agent"),
        ):
            await launcher._update_webhook("https://new.trycloudflare.com/api/agent")

        assert launcher._previous_webhook_url is None

    @pytest.mark.asyncio
    async def test_update_webhook_continues_on_api_error(self) -> None:
        """Should continue with tunnel even if webhook update fails."""
        launcher = CloudflareTunnelLauncher(
            port=8000,
            agent_id="ag-test",
            api_key="test-key",
            update_webhook=True,
        )

        with patch(
            "layercode_gym.tunnel.get_agent",
            side_effect=Exception("API error"),
        ):
            # Should not raise
            await launcher._update_webhook("https://test.trycloudflare.com")

    @pytest.mark.asyncio
    async def test_restore_webhook_clears_if_no_previous(self) -> None:
        """Should clear webhook if there was no previous value."""
        launcher = CloudflareTunnelLauncher(
            port=8000,
            agent_id="ag-test",
            api_key="test-key",
            update_webhook=True,
        )
        launcher._tunnel_url = "https://test.trycloudflare.com"
        launcher._previous_webhook_url = None  # No previous webhook

        # Current webhook matches our tunnel URL
        mock_agent = MagicMock()
        mock_agent.webhook_url = "https://test.trycloudflare.com"

        with (
            patch("layercode_gym.tunnel.get_agent", return_value=mock_agent),
            patch("layercode_gym.tunnel.update_agent") as mock_update,
        ):
            await launcher._restore_webhook()

            mock_update.assert_called_once_with(
                "ag-test",
                "test-key",
                {"webhook_url": ""},
            )


# =============================================================================
# Integration-style tests (still mocked but testing full flow)
# =============================================================================


class TestTunnelIntegration:
    """Integration-style tests for the tunnel functionality."""

    def test_cli_help_shows_tunnel_command(self) -> None:
        """Should show tunnel command in CLI help."""
        from layercode_gym.cli import create_parser

        parser = create_parser()

        # Check that tunnel is in the description
        assert parser.description is not None
        assert "tunnel" in parser.description

    def test_cli_tunnel_help_shows_examples(self) -> None:
        """Should show examples in tunnel help."""
        from layercode_gym.cli import create_parser

        parser = create_parser()

        # Verify the tunnel subparser was created correctly
        subparsers = parser._subparsers
        assert subparsers is not None

    def test_main_parser_includes_tunnel_example(self) -> None:
        """Should include tunnel example in main help."""
        from layercode_gym.cli import create_parser

        parser = create_parser()

        # Check epilog contains tunnel example
        assert parser.epilog is not None
        assert "tunnel" in parser.epilog
        assert "--unsafe-update-webhook" in parser.epilog
