# Source the lecture

Obtain a timestamped transcript before planning the lesson. Never overwrite the source while cleaning it.

Keep the source run durable and inspectable. Preserve these as separate artifacts:

- the original recording or user submission;
- the raw transcription response;
- each normalized or corrected transcript;
- the source-run record and validation results;
- raw request/response metadata exposed by the provider;
- the outline and reference mapping;
- model-call records; and
- rendered outputs.

Do not collapse these records into the learner-facing lesson.

## Choose the source path

Prefer Modal for audio transcription. The skill contains two self-contained deployments:

- `modal_parakeet.py` runs NVIDIA Parakeet for timestamped segments;
- `modal_whisperx.py` runs WhisperX with controlled decoding and sentence-oriented segments; and
- WhisperX accepts an optional language hint.

Deploy the selected script with the Modal CLI:

```bash
modal deploy <script>
```

A deployment creates or updates a persistent app and prints the authenticated Web Function URL.

For a one-off smoke test, use the script's local entrypoint:

```bash
modal run <script> --url "https://example.test/lecture.m4a"
```

Keep the endpoint protected by Modal proxy authentication. Use the credentials and HTTP client already configured for the user's Modal workspace. Do not make the endpoint public merely to simplify testing. Record:

- deployment name;
- endpoint URL;
- request payload;
- response; and
- errors.

Submit an `items` list with stable integer indices. When the recording is known to be in one language, WhisperX may receive a BCP 47 hint:

```json
{
  "items": [
    {"url": "https://example.test/lecture-01.m4a", "index": 0},
    {"url": "https://example.test/lecture-02.m4a", "index": 1}
  ],
  "language": "en"
}
```

When combining recordings:

- keep the returned indices;
- normalize each result to ordered segments with `start_seconds`, `end_seconds`, and `content`;
- preserve detected language and the raw response beside the normalized form; and
- reject empty or malformed items rather than silently dropping them.

Use local transcription only when:

- the machine has a compatible GPU;
- model dependencies and FFmpeg are available; or
- the user explicitly chooses local execution.

Do not silently run a long lecture on an inadequate CPU setup. Check that a local fallback produces the same normalized segment shape as the Modal path.

## If the user provides the transcript

If there is no usable recording, ask for a timestamped transcript. Accept:

- JSON;
- Markdown;
- plain text with timestamps; or
- another clearly structured format.

Normalize the accepted transcript without changing the spoken words. Use this internal shape:

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

Preserve the user's wording. Mark uncertain portions instead of guessing. If correction is requested:

- make corrections in a new transcript version; and
- retain a record of what changed.

## Validate the source

Before outlining, validate the source:

- every segment is non-empty;
- timestamps are non-negative and ordered;
- every end follows its start;
- the complete available recording timeline is covered;
- the recording language and output language remain distinct; and
- reference PDFs or notes retain their original filenames, page numbers, and provenance.

Preserve source identity separately from transcript timing:

- record the public recording link in `recording_urls`;
- for Pandoc/Typst, derive `audio-files` with one `{name, duration}` mapping per recording;
- derive `reference-files` with one `{name, pages}` mapping per supplied reference file;
- let the supplied template render those fields through its predefined tables;
- keep transcript-service identity and retrieval details in the intermediate source record unless a selected template explicitly supports them;
- never flatten provenance into a prose string or add a hand-written Sources block; and
- preserve the lesson timestamp in machine-readable `date`, then derive its user-friendly display form from that same field for the template: calendar date plus hour/minute only, without seconds, timezone offsets, or raw ISO punctuation.

This document-level timestamp is separate from transcript timecodes, which stay internal by default.

Treat the transcript as the authority for:

- what was said;
- its order; and
- its qualitative depth.

Treat reference documents as secondary evidence for terminology, clarification, and citations. Do not let a rich reference document expand the lecture beyond its stated scope.
