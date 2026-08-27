"""The small public execution API for Teacher."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4
from typing import Any

import aiosqlite
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from models_provider import ModelUsage
from teacher.configuration import (
    ExecutionPolicy,
    GraphRuntime,
    LessonPolicy,
    ModelSelection,
    RetryPolicy,
    TranscriptPolicy,
    build_serializer,
)
from teacher.graph import define_graph
from teacher.models import DocumentSource, Lesson, Transcript
from teacher.prompts import Prompts


@dataclass(frozen=True, slots=True)
class LessonResult:
    """A completed lesson and its model usage."""

    lesson: Lesson
    usage_by_model: dict[str, ModelUsage]
    run_id: str


class LessonGraph:
    """Generate lessons from transcript and document material."""

    def __init__(
        self,
        models: ModelSelection,
        *,
        checkpoint_path: Path | None = None,
        prompts: Prompts | None = None,
        retries: RetryPolicy | None = None,
        transcript_policy: TranscriptPolicy | None = None,
        lesson_policy: LessonPolicy | None = None,
        execution: ExecutionPolicy | None = None,
    ) -> None:
        self._runtime = GraphRuntime(
            models=models,
            prompts=prompts or Prompts(),
            retries=retries or RetryPolicy(),
            transcript=transcript_policy or TranscriptPolicy(),
            lesson=lesson_policy or LessonPolicy(),
            execution=execution or ExecutionPolicy(),
        )
        self._checkpoint_path = checkpoint_path
        self._connection: aiosqlite.Connection | None = None
        self._graph: Any = None

    async def __aenter__(self) -> "LessonGraph":
        if self._checkpoint_path is None:
            self._graph = define_graph(retry_policy=self._runtime.retries).compile(
                checkpointer=MemorySaver()
            )
            return self
        self._checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = await aiosqlite.connect(str(self._checkpoint_path))
        checkpointer = AsyncSqliteSaver(self._connection, serde=build_serializer())
        self._graph = define_graph(retry_policy=self._runtime.retries).compile(
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
        documents: Sequence[DocumentSource] = (),
        run_id: str | None = None,
    ) -> LessonResult:
        """Generate a lesson, creating a run identity when one is not supplied."""
        selected_run_id = (run_id or uuid4().hex).strip()
        self._validate(transcript, output_language, selected_run_id)
        return await self._invoke(
            {
                "transcript": transcript,
                "document_sources": list(documents),
                "output_language": output_language.strip(),
            },
            selected_run_id,
        )

    async def resume(self, run_id: str) -> LessonResult:
        """Continue an interrupted generation from its latest checkpoint."""
        selected_run_id = run_id.strip()
        if not selected_run_id:
            raise ValueError("run_id cannot be empty")
        return await self._invoke(None, selected_run_id)

    async def _invoke(self, value: dict[str, object] | None, run_id: str) -> LessonResult:
        result = await self._require_graph().ainvoke(
            value,
            context=self._runtime,
            config=self._run_configuration(run_id),
        )
        return self._result(result, run_id)

    def _run_configuration(self, run_id: str) -> dict[str, object]:
        return {
            "configurable": {"thread_id": run_id},
            "recursion_limit": self._runtime.execution.recursion_limit,
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
        if not run_id:
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


__all__ = ["LessonGraph", "LessonResult"]
