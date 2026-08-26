"""Loading the Markdown shapes used only by lecture export."""

from __future__ import annotations

from collections.abc import Mapping

from teacher.errors import PipelineError
from teacher.outputs.models import ExportError
from teacher.prompts import Prompts

__all__ = ["render_export_template"]

_TEMPLATES = Prompts(package="teacher.output_templates")


def render_export_template(name: str, variables: Mapping[str, object]) -> str:
    """Renders one packaged export shape with strict placeholder checking."""
    try:
        return _TEMPLATES.render(name, variables)
    except PipelineError as error:
        raise ExportError(f"export template {name!r} could not be rendered") from error
