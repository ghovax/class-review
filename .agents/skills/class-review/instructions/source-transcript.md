# Source the lecture

Obtain a timestamped transcript before planning the lesson. Keep the original recording or user submission, the raw transcription response, and each normalized or corrected transcript as separate artifacts. Never overwrite the source while cleaning it.

## Choose the source path

Prefer Modal for audio transcription. The skill contains two self-contained deployments:

- `modal_parakeet.py` runs NVIDIA Parakeet for timestamped segments.
- `modal_whisperx.py` runs WhisperX with controlled decoding and sentence-oriented segments; it accepts an optional language hint.

Deploy the selected script with the Modal CLI. A deployment creates or updates a persistent app and prints the authenticated Web Function URL:

```bash
modal deploy <script>
```

For a one-off smoke test, use the script's local entrypoint:

```bash
modal run <script> --url "https://example.test/lecture.m4a"
```

The endpoint is protected by Modal proxy authentication. Use the credentials and HTTP client already configured for the user's Modal workspace; do not make the endpoint public merely to simplify testing. Keep the deployment name, URL, request payload, response, and any errors in the run record.

Submit an `items` list with stable integer indices. WhisperX may receive a BCP 47 language hint when the recording is known to be one language:

```json
{
  "items": [
    {"url": "https://example.test/lecture-01.m4a", "index": 0},
    {"url": "https://example.test/lecture-02.m4a", "index": 1}
  ],
  "language": "en"
}
```

Keep the returned indices when combining multiple recordings. Normalize each result to ordered segments with `start_seconds`, `end_seconds`, and `content`; preserve detected language and the raw response beside the normalized form. Reject empty or malformed items rather than silently dropping them.

Use local transcription only when the machine has the required compatible GPU, model dependencies, and FFmpeg, or when the user explicitly chooses it. Do not silently run a long lecture on an inadequate CPU setup. Check that a local fallback produces the same normalized segment shape as the Modal path.

## If the user provides the transcript

If there is no usable recording, ask for a timestamped transcript. Accept JSON, Markdown, plain text with timestamps, or another clearly structured format, then normalize it without changing the spoken words. A useful internal shape is:

```json
{
  "languages": ["en"],
  "segments": [
    {
      "start_seconds": 0.0,
      "end_seconds": 8.4,
      "content": "Today we introduce the derivative."
    }
  ]
}
```

Preserve the user's wording and mark uncertain portions instead of guessing. If correction is requested, make corrections in a new transcript version and retain a record of what changed.

## Validate the source

Before outlining, confirm that segments are non-empty, timestamps are non-negative and ordered, each end follows its start, and the complete recording timeline is covered. Keep the recording language and output language distinct. Preserve reference PDFs or notes with their original filenames, page numbers, and provenance.

Preserve source identity separately from transcript timing. Record the public recording link in `recording_urls`. For Pandoc/Typst export, derive the template-supported `audio-files` list with one `{name, duration}` mapping per recording, and derive `reference-files` with one `{name, pages}` mapping per supplied reference file. The supplied export template renders those fields as its predefined `Recordings | Duration` and `Reference documents | Pages` tables. Keep transcript-service identity and retrieval details in the intermediate source record unless a selected template explicitly supports them; never flatten them into a prose string or add a hand-written Sources block at the end of the lesson. Preserve the lesson timestamp in machine-readable `date` and pass a localized `lesson-date` display value to the template; this is separate from transcript timecodes, which stay internal by default.

Treat the transcript as the authority for what was said, its order, and its qualitative depth. Treat reference documents as secondary evidence for terminology, clarification, and citations. Do not let a rich reference document expand a lecture beyond its stated scope.
