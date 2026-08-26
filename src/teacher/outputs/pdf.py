"""Converting canonical lecture Markdown into PDF bytes with Pandoc and Typst."""

from __future__ import annotations

import json
import re
import subprocess
from importlib import resources
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Final

import segno

from teacher.outputs.localization import (
    export_labels,
    format_lesson_date,
    primary_language,
)
from teacher.outputs.models import ExportError, ExportMetadata

__all__ = ["render_pdf"]

_PANDOC_TIMEOUT_SECONDS: Final[int] = 40
_PANDOC_INPUT_FORMAT: Final[str] = "markdown+smart+footnotes+raw_html+header_attributes"
_ANCHOR_BEFORE_HEADING: Final[re.Pattern[bytes]] = re.compile(
    rb'^<a id="([^"]+)"></a>\n\n(#{1,6} .+)$', re.MULTILINE
)


def render_pdf(markdown: bytes, metadata: ExportMetadata) -> bytes:
    """Converts canonical Markdown into PDF bytes."""
    template_resource = resources.files("teacher.outputs.assets").joinpath("pandoc-typst.template")
    with resources.as_file(template_resource) as template_path:
        return _run_pandoc(markdown, metadata, template_path)


def _run_pandoc(
    markdown: bytes,
    metadata: ExportMetadata,
    template_path: Path,
) -> bytes:
    """Runs one bounded Pandoc-to-Typst conversion in an isolated directory."""
    with TemporaryDirectory(prefix="teacher-export-") as temporary_directory:
        working_directory = Path(temporary_directory)
        output_path = working_directory / "lesson.pdf"
        metadata_path = working_directory / "metadata.json"
        pandoc_metadata = _pandoc_metadata(metadata)

        if metadata.share_url:
            qr_code_path = working_directory / "share-qr.svg"
            segno.make_qr(metadata.share_url, error="m").save(
                str(qr_code_path),
                scale=4,
                border=1,
                dark="#000000",
                light="#ffffff",
            )
            pandoc_metadata["qr-image-path"] = qr_code_path.name

        metadata_path.write_text(json.dumps(pandoc_metadata, ensure_ascii=False), encoding="utf-8")
        command = [
            "pandoc",
            "--sandbox",
            "--from",
            _PANDOC_INPUT_FORMAT,
            "--shift-heading-level-by=-1",
            "--toc",
            "--toc-depth=2",
            "--pdf-engine=typst",
            f"--template={template_path}",
            f"--metadata-file={metadata_path}",
            "--output",
            str(output_path),
        ]
        try:
            completed = subprocess.run(
                command,
                input=_prepare_markdown_for_typst(markdown),
                cwd=working_directory,
                capture_output=True,
                check=False,
                timeout=_PANDOC_TIMEOUT_SECONDS,
            )
        except FileNotFoundError as error:
            raise ExportError("PDF export requires pandoc and typst on PATH") from error
        except OSError as error:
            raise ExportError("PDF export could not start pandoc") from error
        except subprocess.TimeoutExpired as error:
            raise ExportError(f"PDF export exceeded {_PANDOC_TIMEOUT_SECONDS} seconds") from error

        if completed.returncode != 0:
            details = completed.stderr.decode("utf-8", errors="replace").strip()
            reason = details or "pandoc exited unsuccessfully"
            raise ExportError(f"PDF export failed: {reason}")
        try:
            rendered = output_path.read_bytes()
        except OSError as error:
            raise ExportError("PDF export completed without an output file") from error
        if not rendered.startswith(b"%PDF-"):
            raise ExportError("PDF export produced bytes that are not a PDF")
        return rendered


def _prepare_markdown_for_typst(markdown: bytes) -> bytes:
    """Turns portable HTML anchors into labels understood by Typst."""
    return _ANCHOR_BEFORE_HEADING.sub(rb"\2 {#\1}", markdown)


def _pandoc_metadata(metadata: ExportMetadata) -> dict[str, str]:
    """Builds the scalar metadata consumed by the packaged Typst template."""
    labels = export_labels(metadata.language)
    values = {"lang": primary_language(metadata.language)}
    if metadata.author and metadata.author.strip():
        values["author"] = metadata.author.strip()
    if metadata.lesson_date:
        values["date"] = format_lesson_date(metadata.lesson_date, metadata.language)
    if metadata.include_generated_notice:
        values["generated-notice"] = (
            metadata.generated_notice.strip()
            if metadata.generated_notice and metadata.generated_notice.strip()
            else labels.generated_notice
        )
    return values
