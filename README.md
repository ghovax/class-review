# class-review

This repository contains the `class-review` agent skill. It guides an agent from lecture-source acquisition through flexible lesson planning, chapter writing, and Markdown, HTML, DOCX, or PDF export.

The `class-review` skill is the repository entry point. Its instructions are intentionally progressive: obtain the available source content first, devise the outline second, write the lesson third, and export last. Transcripts may arrive in any readable format; timestamps are used when available, and missing lesson duration is requested from the user rather than inferred.

Modal transcription is preferred. The skill includes deployable Parakeet and WhisperX scripts, plus a Pandoc/Typst template for rendered output.
