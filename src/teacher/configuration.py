"""Configuration for one lesson graph."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from langchain_core.language_models import BaseChatModel
from models_provider import ModelConfiguration, ModelProvider

from teacher.inputs import DocumentImporter
from teacher.importers.pdf import WebPdfImporter
from teacher.prompts import Prompts


@dataclass(frozen=True, slots=True)
class GraphConfiguration:
    """Models, provider, storage, and bounded graph settings."""

    language_model: ModelConfiguration
    checkpoint_path: Path
    model_provider: ModelProvider
    page_language_model: ModelConfiguration | None = None
    document_importer: DocumentImporter = field(default_factory=WebPdfImporter)
    prompts: Prompts = field(default_factory=Prompts)
    model_attempts: int = 3
    page_attempts: int = 3
    correction_batch_seconds: float = 1800.0
    chapter_boundary_seconds: float = 45.0
    chapter_group_seconds: float = 600.0
    zero_duration_seconds: float = 1e-6
    maximum_plan_request_characters: int = 400_000
    maximum_model_index: int = 10_000
    maximum_model_seconds: float = 86_400.0
    transcript_timestamp_decimals: int = 1
    glossary_key_length: int = 10
    recursion_limit: int = 200

    def runtime(self) -> GraphRuntime:
        """Resolve provider models and immutable settings for one run."""

        return GraphRuntime(
            text_model=self.model_provider.create(
                self.language_model,
            ),
            page_model=(
                self.model_provider.create(
                    self.page_language_model,
                )
                if self.page_language_model is not None
                else None
            ),
            document_importer=self.document_importer,
            prompts=self.prompts,
            model_attempts=self.model_attempts,
            page_attempts=self.page_attempts,
            correction_batch_seconds=self.correction_batch_seconds,
            chapter_boundary_seconds=self.chapter_boundary_seconds,
            chapter_group_seconds=self.chapter_group_seconds,
            zero_duration_seconds=self.zero_duration_seconds,
            maximum_plan_request_characters=self.maximum_plan_request_characters,
            maximum_model_index=self.maximum_model_index,
            maximum_model_seconds=self.maximum_model_seconds,
            transcript_timestamp_decimals=self.transcript_timestamp_decimals,
            glossary_key_length=self.glossary_key_length,
            recursion_limit=self.recursion_limit,
        )

@dataclass(frozen=True, slots=True)
class GraphRuntime:
    """Resolved models and settings passed between graph nodes."""

    text_model: BaseChatModel
    page_model: BaseChatModel | None
    document_importer: DocumentImporter
    prompts: Prompts
    model_attempts: int
    page_attempts: int
    correction_batch_seconds: float
    chapter_boundary_seconds: float
    chapter_group_seconds: float
    zero_duration_seconds: float
    maximum_plan_request_characters: int
    maximum_model_index: int
    maximum_model_seconds: float
    transcript_timestamp_decimals: int
    glossary_key_length: int
    recursion_limit: int
