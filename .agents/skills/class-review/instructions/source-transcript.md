# Source the lecture

Obtain the available lecture source before planning the lesson. Use the source in the form it arrives; timestamps are valuable when present but are not required. Never rewrite the source merely to fit a canonical transcript format.

Keep working material in the current context by default. Do not serialize intermediate source, transcript, extraction, validation, outline, reference-map, model-call, or draft artifacts into the repository. Leave user-provided files where they are; do not copy or overwrite them.

Use the system temporary directory only for disposable processing files, such as:

- downloaded or transcoded media;
- OCR output, extracted reference text, or page/slide mappings when a tool requires files;
- provider responses or source snapshots needed only by the current run; and
- temporary inputs and outputs required by a renderer.

Remove disposable files when the task is complete. Write only the final requested learner-facing export to the user's requested destination. Preserve an intermediate audit or resume package only when the user explicitly requests it or the runtime requires it, and keep it outside the repository.

## Inputs to collect

Identify the inputs before choosing a source path:

- a lecture recording URL or file, or a user-provided transcript/source document;
- optional reference documents or links, preserving their filenames, page identity, and provenance;
- the requested learner-facing language;
- the requested export format and destination, when known; and
- the lesson duration or length, derived from reliable metadata when available or requested from the user only when no reliable metadata exists.

Optional inputs include a source-language hint, title, lecturer identity, and lesson date. Do not require timestamps, a transcript schema, or any other particular representation. Do not estimate lesson duration from transcript length, word count, chapter count, segment count, or speaking rate.

Reliable duration metadata includes:

- media or container metadata;
- platform metadata, such as the duration reported for a hosted recording;
- an explicit user-provided duration; and
- the final reliable end timestamp when a timestamped source is known to cover the complete recording.

Use the final end timestamp as the duration when it is a genuine end marker, not merely the start of the last segment. Ask the user only when none of these sources provides a reliable duration.

## Reference materials

Reference materials are optional supporting inputs, separate from the lecture source. They may include PDFs, handouts, slide decks, presentations, notes, web documents, or other supplied files and links.

For each reference, preserve:

- its original filename or title;
- its URL, when applicable;
- the locator system it provides, such as page, slide, section, or heading; and
- its provenance and relationship to the lecture.

Keep the identity and locator information intact when the material is extracted, OCR'd, or converted for analysis. Hold extraction output and page/slide mappings in the current context, or in the system temporary directory when a tool requires files. Keep reference material separate from the transcript and do not require it to be rewritten into a common format.

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

Keep the endpoint protected by Modal proxy authentication. Use the credentials and HTTP client already configured for the user's Modal workspace. Do not make the endpoint public merely to simplify testing. Keep the following in the current run context, using system temporary storage only if a tool requires a file:

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

Preserve the user's wording and mark uncertain portions instead of guessing. Determine lesson duration from the reliable metadata listed above, even when exact transcript timestamps are unavailable. Do not estimate it from word count, transcript length, chapter count, segment count, or speaking rate. Ask the user only when no reliable duration metadata exists.

## Transcription cost

Use the following as rough planning information for the transcription step: experimental measurements put the average cost at approximately $0.02–$0.05 per lesson. In those measurements, the cost changed little between lessons of roughly one hour and roughly two hours. Treat this as an empirical estimate rather than a guarantee, and retain actual provider usage or billing information when it is available.

As of 2026-09-02, Modal's sign-up and pricing pages advertise approximately $30 in free monthly compute credits. Treat this offer as time-sensitive and verify it at sign-up; do not confuse the monthly account allowance with the measured per-lesson transcription cost.

## Validate the source

Before outlining, validate the source:

- the source content is non-empty;
- the source order and recording associations are preserved;
- when timestamps are present, they are non-negative and ordered, and each end follows its start;
- when timestamps are absent, do not reject the source or fabricate them; use media/platform metadata or explicit user input for duration, and ask only when no reliable duration metadata exists;
- the recording language and output language remain distinct; and
- reference PDFs or notes retain their original filenames, page numbers, and provenance.

Preserve source identity separately from transcript timing:

- record the public recording link in `recording_urls`;
- for Pandoc/Typst, derive `audio-files` with one `{name, duration}` mapping per recording when reliable media/platform metadata, a complete source's final end timestamp, or user-provided duration exists;
- derive `reference-files` with one `{name, pages}` mapping per supplied reference file;
- let the supplied template render those fields through its predefined tables;
- keep transcript-service identity and retrieval details in the current run context or system temporary storage only when needed; expose them in the final artifact only when a selected template explicitly supports them;
- never flatten provenance into a prose string or add a hand-written Sources block; and
- preserve the lesson timestamp in machine-readable `date`, then derive its user-friendly display form from that same field for the template: calendar date plus hour/minute only, without seconds, timezone offsets, or raw ISO punctuation.

This document-level timestamp is separate from transcript timecodes, which stay internal by default.

Treat the recording, transcript, or other supplied source content as the authority for:

- what was said;
- its order; and
- its qualitative depth.

Treat reference materials as secondary evidence for confirmation, terminology, clarification, focused enrichment, correction, and citations. Do not let a rich reference document expand the lecture beyond its stated scope or turn the produced lesson into a reproduction of the reference material.
