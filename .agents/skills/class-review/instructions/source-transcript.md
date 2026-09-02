# Source the lecture

Obtain the available lecture source before planning the lesson. Use the source in the form it arrives; timestamps are valuable when present but are not required. Never rewrite the source merely to fit a canonical transcript format.

Keep the source run durable and inspectable. Preserve these as separate artifacts:

- the original recording or user submission;
- the raw transcription response, when transcription is performed;
- the source transcript or other source content as received;
- any user-requested edits, together with a record of what changed;
- the source-run record and validation results;
- raw request/response metadata exposed by the provider;
- the outline and reference mapping;
- model-call records; and
- rendered outputs.

Do not collapse these records into the learner-facing lesson.

## Inputs to collect

Identify the inputs before choosing a source path:

- a lecture recording URL or file, or a user-provided transcript/source document;
- optional reference documents or links, preserving their filenames, page identity, and provenance;
- the requested learner-facing language;
- the requested export format and destination, when known; and
- the lesson duration or length, using reliable recording metadata when available or asking the user when it is not.

Optional inputs include a source-language hint, title, lecturer identity, and lesson date. Do not require timestamps, a transcript schema, or any other particular representation. Do not infer lesson duration from transcript length, word count, chapter count, or missing timecodes.

## Choose the source path

Prefer Modal for audio transcription. The skill contains two self-contained deployments:

- `modal_parakeet.py` runs NVIDIA Parakeet for timestamped segments;
- `modal_whisperx.py` runs WhisperX with controlled decoding and returns the provider's segments; and
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
- preserve the provider's response for each recording, including timestamps when available;
- keep the recordings in source order without converting them into a common segment schema; and
- reject empty or malformed items rather than silently dropping them.

Use local transcription only when:

- the machine has a compatible GPU;
- model dependencies and FFmpeg are available; or
- the user explicitly chooses local execution.

Do not silently run a long lecture on an inadequate CPU setup. Check that a local fallback produces usable source content and relevant metadata; it does not need to mimic the Modal response shape.

## If the user provides the transcript

If there is no usable recording, ask for whatever transcript, source file, or source content the user has. Accept any format that the agent/runtime can read or extract; do not impose an allowlist or require reformatting merely for convenience. If a format cannot be read, ask for the same content in any more accessible form.

Timestamps are preferred because they support precise source mapping, but they are optional. Preserve the supplied content and structure as-is. Do not add synthetic timecodes or convert the transcript to a fixed internal shape.

Preserve the user's wording and mark uncertain portions instead of guessing. If the source has no reliable lesson duration, ask the user for the lesson duration or length. Do not infer it from word count, transcript length, chapter count, or the absence of timestamps.

## Transcription cost

Use the following as rough planning information for the transcription step: experimental measurements put the average cost at approximately $0.02–$0.05 per lesson. In those measurements, the cost changed little between lessons of roughly one hour and roughly two hours. Treat this as an empirical estimate rather than a guarantee, and retain actual provider usage or billing information when it is available.

As of 2026-09-02, Modal's sign-up and pricing pages advertise approximately $30 in free monthly compute credits. Treat this offer as time-sensitive and verify it at sign-up; do not confuse the monthly account allowance with the measured per-lesson transcription cost.

## Validate the source

Before outlining, validate the source:

- the source content is non-empty;
- the source order and recording associations are preserved;
- when timestamps are present, they are non-negative and ordered, and each end follows its start;
- when timestamps are absent, do not reject the source or fabricate them; ask for lesson duration when it is not available from reliable recording metadata;
- the recording language and output language remain distinct; and
- reference PDFs or notes retain their original filenames, page numbers, and provenance.

Preserve source identity separately from transcript timing:

- record the public recording link in `recording_urls`;
- for Pandoc/Typst, derive `audio-files` with one `{name, duration}` mapping per recording when reliable metadata or user-provided duration exists;
- derive `reference-files` with one `{name, pages}` mapping per supplied reference file;
- let the supplied template render those fields through its predefined tables;
- keep transcript-service identity and retrieval details in the intermediate source record unless a selected template explicitly supports them;
- never flatten provenance into a prose string or add a hand-written Sources block; and
- preserve the lesson timestamp in machine-readable `date`, then derive its user-friendly display form from that same field for the template: calendar date plus hour/minute only, without seconds, timezone offsets, or raw ISO punctuation.

This document-level timestamp is separate from transcript timecodes, which stay internal by default.

Treat the recording, transcript, or other supplied source content as the authority for:

- what was said;
- its order; and
- its qualitative depth.

Treat reference documents as secondary evidence for terminology, clarification, and citations. Do not let a rich reference document expand the lecture beyond its stated scope.
