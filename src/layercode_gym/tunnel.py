"""Cloudflare tunnel launcher with optional webhook auto-update.

This module provides a CloudflareTunnelLauncher class that:
1. Starts a Cloudflare quick tunnel on a specified port
2. Optionally updates a LayerCode agent's webhook URL to the tunnel URL
3. Restores the original webhook on shutdown

Usage:
    layercode-gym tunnel --port 8000
    layercode-gym tunnel --port 8000 --unsafe-update-webhook
    layercode-gym tunnel --port 8000 --agent-id ag-123 --unsafe-update-webhook

Requires cloudflared to be installed:
    https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/
"""

from __future__ import annotations

import asyncio
import contextlib
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from layercode_gym.api_agents_utils import get_agent, update_agent
from layercode_gym.logging_utils import sanitize_error

# Pattern to match Cloudflare quick tunnel URLs
TUNNEL_URL_PATTERN = re.compile(
    r"https://[a-z0-9-]+\.trycloudflare\.com", re.IGNORECASE
)


class CloudflareTunnelLauncher:
    """Launches a Cloudflare quick tunnel and optionally updates agent webhook.

    This class manages the lifecycle of a cloudflared tunnel process:
    - Starts the tunnel and extracts the public URL
    - Optionally updates a LayerCode agent's webhook to the tunnel URL
    - On shutdown, restores the previous webhook URL

    Attributes:
        target_url: The local URL to expose via tunnel
        agent_id: LayerCode agent ID for webhook updates
        api_key: LayerCode API key for webhook updates
        update_webhook: Whether to auto-update agent webhook
    """

    def __init__(
        self,
        *,
        url: str | None = None,
        port: int | None = None,
        host: str = "localhost",
        agent_id: str | None = None,
        api_key: str | None = None,
        update_webhook: bool = False,
    ) -> None:
        """Initialize the tunnel launcher.

        Args:
            url: Full URL to expose (e.g., http://localhost:8000)
            port: Local port to expose (alternative to url)
            host: Local host to tunnel to (used with port)
            agent_id: LayerCode agent ID for webhook updates
            api_key: LayerCode API key for webhook updates
            update_webhook: Whether to auto-update agent webhook
        """
        if url:
            self.target_url = url
        elif port:
            self.target_url = f"http://{host}:{port}"
        else:
            raise ValueError("Either 'url' or 'port' must be provided")

        self.agent_id = agent_id
        self.api_key = api_key
        self.update_webhook = update_webhook

        self._process: asyncio.subprocess.Process | None = None
        self._tunnel_url: str | None = None
        self._previous_webhook_url: str | None = None
        self._log_file_handle: Any | None = None
        self._drain_tasks: list[asyncio.Task[None]] = []

        # Create log file path with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file_path = Path(f"cloudflare_tunnel_{timestamp}.log")

    @property
    def tunnel_url(self) -> str | None:
        """The tunnel URL once established, or None if not started."""
        return self._tunnel_url

    async def start(self, timeout_seconds: float = 30.0) -> str:
        """Start the tunnel and return the tunnel URL.

        Args:
            timeout_seconds: Maximum time to wait for tunnel URL

        Returns:
            The tunnel URL (e.g., https://random-words.trycloudflare.com)

        Raises:
            RuntimeError: If cloudflared is not installed or tunnel fails to start
        """
        # Check if cloudflared is installed
        if shutil.which("cloudflared") is None:
            raise RuntimeError(
                "cloudflared binary not found.\n"
                "Install from: https://developers.cloudflare.com/cloudflare-one/"
                "connections/connect-apps/install-and-setup/installation/"
            )

        # Open log file
        self._log_file_handle = open(  # noqa: ASYNC230, SIM115
            self.log_file_path, "w", encoding="utf-8", buffering=1
        )
        self._log_file_handle.write(
            f"=== Cloudflare Tunnel Log - {datetime.now().isoformat()} ===\n"
        )
        self._log_file_handle.write(f"Target: {self.target_url}\n")
        self._log_file_handle.write("=" * 60 + "\n\n")
        self._log_file_handle.flush()

        print(f"Starting Cloudflare tunnel to {self.target_url}...", file=sys.stderr)
        print(f"Tunnel logs: {self.log_file_path.absolute()}", file=sys.stderr)

        # Start cloudflared process
        self._process = await asyncio.create_subprocess_exec(
            "cloudflared",
            "tunnel",
            "--url",
            self.target_url,
            "--loglevel",
            "debug",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        assert self._process.stdout is not None
        assert self._process.stderr is not None

        # Wait for tunnel URL from output
        url_future: asyncio.Future[str] = asyncio.Future()

        async def scan_stream(stream: asyncio.StreamReader, name: str) -> None:
            """Scan stream for tunnel URL and log output."""
            try:
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    decoded = line.decode("utf-8", errors="ignore")

                    # Write to log file
                    if self._log_file_handle:
                        self._log_file_handle.write(f"[{name}] {decoded}")
                        self._log_file_handle.flush()

                    # Check for tunnel URL
                    match = TUNNEL_URL_PATTERN.search(decoded)
                    if match and not url_future.done():
                        url_future.set_result(match.group(0))
            except asyncio.CancelledError:
                pass

        # Start scanning both streams
        stdout_task = asyncio.create_task(scan_stream(self._process.stdout, "stdout"))
        stderr_task = asyncio.create_task(scan_stream(self._process.stderr, "stderr"))

        try:
            # Wait for URL with timeout
            self._tunnel_url = await asyncio.wait_for(
                url_future, timeout=timeout_seconds
            )
        except TimeoutError as exc:
            stdout_task.cancel()
            stderr_task.cancel()
            await self.stop()
            raise RuntimeError(
                f"Timed out waiting for tunnel URL after {timeout_seconds}s. "
                f"Check logs at: {self.log_file_path}"
            ) from exc

        # Cancel scanning tasks and start drain tasks
        stdout_task.cancel()
        stderr_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await stdout_task
        with contextlib.suppress(asyncio.CancelledError):
            await stderr_task

        # Start background drain tasks for remaining output
        self._drain_tasks = [
            asyncio.create_task(self._drain_stream(self._process.stdout, "stdout")),
            asyncio.create_task(self._drain_stream(self._process.stderr, "stderr")),
        ]

        tunnel_url = self._tunnel_url
        assert tunnel_url is not None

        print(f"Tunnel URL: {tunnel_url}", file=sys.stderr)

        # Update webhook if requested
        if self.update_webhook:
            await self._update_webhook(tunnel_url)

        # Print banner
        self._print_banner()

        return tunnel_url

    async def _drain_stream(self, stream: asyncio.StreamReader, name: str) -> None:
        """Drain stream output to log file."""
        while True:
            line = await stream.readline()
            if not line:
                break
            decoded = line.decode("utf-8", errors="ignore")
            if self._log_file_handle:
                self._log_file_handle.write(f"[{name}] {decoded}")
                self._log_file_handle.flush()

    async def _update_webhook(self, webhook_url: str) -> None:
        """Update agent webhook and save previous value."""
        if not self.agent_id or not self.api_key:
            print(
                "Warning: --unsafe-update-webhook requires --agent-id and --api-key",
                file=sys.stderr,
            )
            return

        try:
            # Get current webhook
            print(
                f"Fetching current webhook for agent {self.agent_id}...",
                file=sys.stderr,
            )
            agent = get_agent(self.agent_id, self.api_key)
            self._previous_webhook_url = agent.webhook_url

            if self._previous_webhook_url:
                print(
                    f"Saving previous webhook: {self._previous_webhook_url}",
                    file=sys.stderr,
                )
            else:
                print("Agent has no previous webhook URL", file=sys.stderr)

            # Update to tunnel URL
            print(f"Updating webhook to: {webhook_url}", file=sys.stderr)
            update_agent(self.agent_id, self.api_key, {"webhook_url": webhook_url})
            print("Webhook updated successfully", file=sys.stderr)

        except Exception as e:
            print(
                f"Warning: Failed to update webhook: {sanitize_error(e)}",
                file=sys.stderr,
            )
            print("Continuing with tunnel anyway...", file=sys.stderr)

    async def stop(self) -> None:
        """Stop the tunnel and restore webhook if needed."""
        # Restore webhook if it was updated
        if self.update_webhook and self.agent_id and self.api_key and self._tunnel_url:
            await self._restore_webhook()

        # Terminate process
        if self._process and self._process.returncode is None:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5)
            except TimeoutError:
                self._process.kill()
                await self._process.wait()

        # Cancel drain tasks
        for task in self._drain_tasks:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        self._drain_tasks = []

        # Close log file
        if self._log_file_handle:
            self._log_file_handle.write(
                f"\n=== Tunnel stopped at {datetime.now().isoformat()} ===\n"
            )
            self._log_file_handle.close()
            self._log_file_handle = None
            print(
                f"Tunnel logs saved to: {self.log_file_path.absolute()}",
                file=sys.stderr,
            )

    async def _restore_webhook(self) -> None:
        """Restore the previous webhook URL if unchanged."""
        assert self.agent_id is not None
        assert self.api_key is not None

        try:
            # Check current webhook
            print("Checking if webhook should be restored...", file=sys.stderr)
            agent = get_agent(self.agent_id, self.api_key)
            current_webhook = agent.webhook_url

            # Only restore if webhook is still our tunnel URL
            if current_webhook == self._tunnel_url:
                if self._previous_webhook_url:
                    print(
                        f"Restoring webhook to: {self._previous_webhook_url}",
                        file=sys.stderr,
                    )
                    update_agent(
                        self.agent_id,
                        self.api_key,
                        {"webhook_url": self._previous_webhook_url},
                    )
                    print("Webhook restored successfully", file=sys.stderr)
                else:
                    # Clear webhook if there was none before
                    print("Clearing webhook (no previous value)", file=sys.stderr)
                    update_agent(self.agent_id, self.api_key, {"webhook_url": ""})
                    print("Webhook cleared", file=sys.stderr)
            else:
                print(
                    f"Webhook has been changed externally to: {current_webhook}",
                    file=sys.stderr,
                )
                print("Leaving webhook as-is", file=sys.stderr)

        except Exception as e:
            print(
                f"Warning: Failed to restore webhook: {sanitize_error(e)}",
                file=sys.stderr,
            )

    def _print_banner(self) -> None:
        """Print a prominent banner with tunnel information."""
        border = "=" * 70
        tunnel_url = self._tunnel_url

        if self.update_webhook and self.agent_id:
            message = (
                f"\n{border}\n"
                f"{border}\n"
                "  CLOUDFLARE TUNNEL ESTABLISHED\n"
                f"{border}\n\n"
                f"  Tunnel URL: {tunnel_url}\n"
                f"  Agent ID: {self.agent_id}\n"
                "  Status: Webhook automatically updated\n\n"
                f"{border}\n"
                "  Press Ctrl+C to stop (webhook will be restored)\n"
                f"{border}\n"
                f"{border}\n"
            )
        else:
            message = (
                f"\n{border}\n"
                f"{border}\n"
                "  CLOUDFLARE TUNNEL ESTABLISHED\n"
                f"{border}\n\n"
                f"  Tunnel URL: {tunnel_url}\n\n"
                f"{border}\n"
                "  IMPORTANT: Add this URL to your LayerCode agent webhook:\n"
                "  https://dash.layercode.com/\n\n"
                "  TIP: Use --unsafe-update-webhook to automatically update\n"
                "       the webhook for your agent (requires --agent-id)\n"
                f"{border}\n"
                "  Press Ctrl+C to stop\n"
                f"{border}\n"
                f"{border}\n"
            )
        print(message, flush=True)
