from __future__ import annotations

"""Helpers for orchestrating one or more conversations."""

import asyncio
from dataclasses import dataclass
from typing import Iterable

from .client import LayercodeClient


@dataclass(slots=True)
class ConversationRunner:
    client: LayercodeClient

    async def run_once(self) -> str:
        return await self.client.run()


@dataclass(slots=True)
class ConversationBatch:
    runners: Iterable[ConversationRunner]

    async def run_all(self) -> list[str]:
        tasks = [runner.run_once() for runner in self.runners]
        return await asyncio.gather(*tasks)
