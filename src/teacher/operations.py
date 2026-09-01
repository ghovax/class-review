"""Public operation classes for building lesson material.

Implementations live beside the material they transform: transcript revision,
reference reading, outline drafting, chapter writing, and glossary writing.
"""

from teacher.documents.reader import ReferenceReader
from teacher.lesson.chapter import ChapterWriter
from teacher.lesson.glossary import GlossaryWriter
from teacher.lesson.outline import OutlineWriter
from teacher.transcript.revision import TranscriptRevision

__all__ = [
    "TranscriptRevision",
    "ReferenceReader",
    "OutlineWriter",
    "ChapterWriter",
    "GlossaryWriter",
]
