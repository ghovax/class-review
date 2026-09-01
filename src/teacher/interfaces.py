"""Interfaces accepted by Teacher operations."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol

from langchain_core.messages import BaseMessage


class ChatModel(Protocol):
    """Minimal asynchronous chat-model interface required by Teacher."""

    async def ainvoke(self, messages: Sequence[BaseMessage]) -> Any: ...
