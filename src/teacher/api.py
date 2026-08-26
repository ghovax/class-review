"""Black-box execution with durable SQLite checkpoints."""

from __future__ import annotations

from collections.abc import Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Any

import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from teacher.configuration import GraphConfiguration, GraphRuntime
from teacher.graph import define_graph
from teacher.models import DocumentSource, LanguageModelUsage, Lesson, Transcript
from teacher.serialization import build_serializer


@dataclass(frozen=True, slots=True)
class LessonResult:
    """A completed lesson and its model usage."""

    lesson: Lesson
    usage_by_model: dict[str, LanguageModelUsage]
    run_id: str


class LessonGraph:
    """Generates and resumes lessons through the complete graph."""

    def __init__(self, configuration: GraphConfiguration) -> None:
        self.configuration = configuration
        self._connection: aiosqlite.Connection | None = None
        self._graph: Any = None

    async def __aenter__(self) -> LessonGraph:
        self.configuration.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = await aiosqlite.connect(str(self.configuration.checkpoint_path))
        checkpointer = AsyncSqliteSaver(self._connection, serde=build_serializer())
        self._graph = define_graph(model_attempts=self.configuration.model_attempts).compile(
            checkpointer=checkpointer
        )
        return self

    async def __aexit__(self, *error: object) -> None:
        del error
        if self._connection is not None:
            await self._connection.close()
        self._connection = None
        self._graph = None

    async def generate(
        self,
        *,
        transcript: Transcript,
        output_language: str,
        run_id: str,
        sources: Sequence[DocumentSource] = (),
    ) -> LessonResult:
        """Start a checkpointed lesson generation."""

        self._validate(transcript, output_language, run_id)
        return await self._invoke(
            {
                "transcript": transcript,
                "sources": list(sources),
                "output_language": output_language.strip(),
            },
            run_id.strip(),
        )

    async def resume(self, run_id: str) -> LessonResult:
        """Continue an interrupted generation from its latest checkpoint."""

        return await self._invoke(None, run_id)

    async def _invoke(self, value: dict[str, object] | None, run_id: str) -> LessonResult:
        runtime = self.configuration.runtime()
        with self._provider_scope():
            result = await self._require_graph().ainvoke(
                value,
                context=runtime,
                config=self._run_configuration(run_id, runtime),
            )
        return self._result(result, run_id)

    def _provider_scope(self) -> AbstractContextManager[None]:
        """Activate provider-local state for every model call in this graph run."""
        return self.configuration.model_provider.scope()

    @staticmethod
    def _run_configuration(run_id: str, runtime: GraphRuntime) -> dict[str, object]:
        if not run_id.strip():
            raise ValueError("run_id cannot be empty")
        return {
            "configurable": {"thread_id": run_id.strip()},
            "recursion_limit": runtime.recursion_limit,
        }

    def _require_graph(self) -> Any:
        if self._graph is None:
            raise RuntimeError("use LessonGraph inside 'async with'")
        return self._graph

    @staticmethod
    def _validate(transcript: Transcript, output_language: str, run_id: str) -> None:
        if not transcript.segments:
            raise ValueError("transcript cannot be empty")
        if not transcript.languages:
            raise ValueError("transcript languages cannot be empty")
        if not output_language.strip():
            raise ValueError("output_language cannot be empty")
        if not run_id.strip():
            raise ValueError("run_id cannot be empty")

    @staticmethod
    def _result(result: dict[str, Any], run_id: str) -> LessonResult:
        lesson = result.get("lesson")
        if lesson is None:
            raise RuntimeError("the graph completed without a lesson")
        return LessonResult(
            lesson=lesson,
            usage_by_model=dict(result.get("usage_by_model", {})),
            run_id=run_id,
        )
