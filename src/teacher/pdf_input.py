"""Default PDF input from local paths or URLs."""

from __future__ import annotations

import base64
import asyncio
import io
import re
from email.message import EmailMessage
from pathlib import Path
from typing import Any, cast
from urllib.parse import unquote, urlparse

import httpx

from teacher.errors import PipelineError
from teacher.inputs import ImportedDocument
from teacher.models import DocumentSource, RenderedPage

_PDF_SIGNATURE = b"%PDF-"
_CONFIRMATION_LINK = re.compile(
    r"""(?:href|action)=["'](?P<target>[^"']*confirm=[^"']*)["']""", re.I
)


def _read_local_pdf(location: str) -> tuple[bytes, str, str] | None:
    """Read a local PDF without blocking the event loop."""
    path = Path(location).expanduser()
    if not path.is_file():
        return None
    return path.read_bytes(), str(path.resolve()), path.name


class WebPdfImporter:
    """Downloads or reads a PDF and renders every page as a JPEG data URL."""

    def __init__(
        self,
        *,
        timeout_seconds: float = 60.0,
        render_scale: float = 1.5,
        image_quality: int = 85,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.render_scale = render_scale
        self.image_quality = image_quality
        self.client = client

    async def load(self, source: DocumentSource, *, document_index: int) -> ImportedDocument:
        content, resolved_url, downloaded_name = await self._read(source.url)
        if not content.startswith(_PDF_SIGNATURE):
            raise PipelineError.terminal("the source is not a PDF", {"source": source.url})
        file_name = self._file_name(source, downloaded_name)
        return ImportedDocument(
            document_index=document_index,
            source_url=resolved_url,
            file_name=file_name,
            pages=tuple(self._render(content)),
        )

    async def _read(self, location: str) -> tuple[bytes, str, str | None]:
        local = await asyncio.to_thread(_read_local_pdf, location)
        if local is not None:
            return local

        if self.client is not None:
            response = await self._request(self.client, location)
            response = await self._follow_confirmation(self.client, response)
            return self._response(response)

        async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=True) as client:
            response = await self._request(client, location)
            response = await self._follow_confirmation(client, response)
            return self._response(response)
    async def _request(self, client: httpx.AsyncClient, location: str) -> httpx.Response:
        try:
            response = await client.get(location, follow_redirects=True)
        except httpx.HTTPError as error:
            raise PipelineError.retryable(
                "the document could not be downloaded", {"source": location}, error
            ) from error
        if response.status_code >= 400:
            retryable = response.status_code == 429 or response.status_code >= 500
            raise PipelineError(
                "the document source returned an error",
                {
                    "source": location,
                    "status_code": response.status_code,
                    "retryable": retryable,
                },
            )
        return response

    async def _follow_confirmation(
        self, client: httpx.AsyncClient, response: httpx.Response
    ) -> httpx.Response:
        if "text/html" not in (response.headers.get("content-type") or ""):
            return response
        match = _CONFIRMATION_LINK.search(response.text)
        if match is None:
            return response
        target = str(response.url.join(match.group("target").replace("&amp;", "&")))
        return await self._request(client, target)

    def _response(self, response: httpx.Response) -> tuple[bytes, str, str | None]:
        disposition = response.headers.get("content-disposition")
        name = None
        if disposition:
            message = EmailMessage()
            message["Content-Disposition"] = disposition
            name = message.get_filename()
        return response.content, str(response.url), name.strip() if name else None

    def _render(self, content: bytes) -> list[RenderedPage]:
        try:
            import pypdfium2
        except ImportError as error:
            raise PipelineError.terminal(
                "PDF input requires pypdfium2", {"required_package": "pypdfium2"}
            ) from error
        try:
            document = pypdfium2.PdfDocument(content)
        except Exception as error:
            raise PipelineError.terminal("the PDF could not be opened", cause=error) from error
        try:
            return [
                RenderedPage(
                    page_number=index + 1,
                    image_data_url=self._encode(
                        cast(Any, document[index]).render(scale=self.render_scale).to_pil()
                    ),
                )
                for index in range(len(document))
            ]
        finally:
            document.close()

    def _encode(self, image: object) -> str:
        buffer = io.BytesIO()
        image.convert("RGB").save(  # type: ignore[attr-defined]
            buffer, format="JPEG", quality=self.image_quality
        )
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return f"data:image/jpeg;base64,{encoded}"

    @staticmethod
    def _file_name(source: DocumentSource, downloaded_name: str | None) -> str:
        for candidate in (downloaded_name, source.file_name):
            if candidate and candidate.strip():
                return candidate.strip()
        path_name = Path(unquote(urlparse(source.url).path)).name.strip()
        if path_name:
            return path_name
        raise PipelineError.terminal("the document has no usable name", {"source": source.url})
