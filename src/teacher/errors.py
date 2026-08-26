"""Error types and retry classification shared by every graph node."""

from __future__ import annotations

import traceback
from typing import Any, Final, Self

__all__ = [
    "GenerationCancelled",
    "PipelineError",
    "classify_retryable",
    "describe_error",
]


class PipelineError(Exception):
    """A failure raised by a graph node."""

    def __init__(
        self,
        message: str,
        metadata: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        """Builds a pipeline error carrying structured context."""
        super().__init__(message)
        self.metadata: dict[str, Any] = dict(metadata or {})
        if cause is not None:
            self.__cause__ = cause

    @classmethod
    def retryable(
        cls,
        message: str,
        metadata: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> Self:
        """Builds an error the retry predicate will schedule another attempt for."""
        return cls(message, {**(metadata or {}), "retryable": True}, cause)

    @classmethod
    def terminal(
        cls,
        message: str,
        metadata: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> Self:
        """Builds an error that short-circuits retries and aborts the run."""
        return cls(message, {**(metadata or {}), "retryable": False}, cause)

    @property
    def is_retryable(self) -> bool:
        """Whether this error was explicitly flagged as transient."""
        return bool(self.metadata.get("retryable", False))


# Deliberately not suffixed "Error": a cancellation is an outcome the caller asked
# for, not a fault, and callers distinguish the two by type.
class GenerationCancelled(PipelineError):  # noqa: N818
    """Raised when a caller aborts a run in progress."""

    def __init__(self, message: str = "cancelled by the caller") -> None:
        """Builds a cancellation signal."""
        super().__init__(message, {"retryable": False})


# Transport-level error codes that indicate a transient fault rather than a
# contract violation.
TRANSIENT_ERROR_CODES: Final[frozenset[str]] = frozenset(
    {"ETIMEDOUT", "ECONNRESET", "ECONNREFUSED", "EAI_AGAIN"}
)


def classify_retryable(error: BaseException) -> bool:
    """Decides whether a failed node attempt should be retried."""
    if isinstance(error, GenerationCancelled):
        return False
    if isinstance(error, PipelineError):
        return error.is_retryable

    status_code = _read_status_code(error)
    if status_code is not None:
        if status_code == 429:
            return True
        return 500 <= status_code < 600

    error_code = getattr(error, "code", None)
    if isinstance(error_code, str) and error_code in TRANSIENT_ERROR_CODES:
        return True
    return True


def describe_error(error: BaseException) -> dict[str, Any]:
    """Renders an exception as a structured payload for logging."""
    described: dict[str, Any] = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "traceback_frames": [
            {
                "file_name": frame.filename,
                "line_number": frame.lineno,
                "function_name": frame.name,
            }
            for frame in traceback.extract_tb(error.__traceback__)
        ],
    }
    if isinstance(error, PipelineError) and error.metadata:
        described["error_metadata"] = error.metadata
    cause = error.__cause__
    if cause is not None:
        described["error_cause"] = describe_error(cause)
    return described


def _read_status_code(error: BaseException) -> int | None:
    """Extracts an HTTP status code from an exception, when it carries one."""
    for attribute_name in ("status_code", "status"):
        candidate = getattr(error, attribute_name, None)
        if isinstance(candidate, int) and candidate > 0:
            return candidate
    response = getattr(error, "response", None)
    candidate = getattr(response, "status_code", None)
    if isinstance(candidate, int) and candidate > 0:
        return candidate
    return None
