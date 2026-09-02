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

### Persist Modal credentials locally for future chats

When the user explicitly requests local persistence, save the Proxy Token ID and Secret after the first-time setup so a later chat can reuse Modal without asking the beginner to repeat the setup. Do not save credentials silently when the user has not authorized local persistence.

Resolve this fixed logical filename relative to the directory that contains SKILL.md:

```text
secrets/modal-proxy-token.json
```

Create the parent directory if needed. Store only the minimum information required to identify and authenticate the workspace:

```json
{
  "workspace": "<username>",
  "environment": "main",
  "token_id": "wk-...",
  "token_secret": "ws-..."
}
```

Use a JSON file because it is easy for the agent to locate and parse in a new chat. Resolve it from the active skill folder, not from the current project or working directory. On macOS and Linux, create the directory with mode 0700 and the file with mode 0600. On Windows, restrict the file ACL to the current user. If secure permissions cannot be applied, do not write the Secret to disk and explain the limitation. In the repository copy, keep this path ignored by Git so the local credential file can never be committed.

Never place this file in the repository, a project directory, a synchronized folder, a transcript, or a generated artifact. Do not print the Secret, include it in a status message, or commit it. Read it only in memory when constructing the authenticated request. If the file is missing, malformed, unreadable, or the endpoint returns 401, guide the user through token creation again without exposing any stored value.

At the beginning of every new Modal transcription task, resolve this path and look for a valid file before asking the user for credentials. If both token fields are present, use them automatically for the matching Workspace and Environment. If valid saved credentials exist and a usable recording URL is available, prefer the Modal transcription path by default; use local transcription only when the user explicitly chooses it or the Modal path is unavailable.

During first-time setup, instruct the user to open the Modal dashboard, select the correct Workspace and Environment, go to Workspace settings, open Proxy Tokens, create a token, and copy the Token ID and Token Secret. After the user supplies the values and has authorized local persistence, write the JSON file immediately without echoing the values. Keep the workspace value as the user's actual Workspace slug; placeholders such as <username> in this document are not literal credentials.

### Find and call the deployed Web Function

The URL in the Modal dashboard is a browser page for inspecting the deployment; it is not the HTTP URL to send transcription requests to. For a deployed app, Modal's default Web Function URL is:

```text
https://<username>--<app>-<function>.modal.run
```

Here, the username placeholder is the Modal Workspace slug, not a literal value. For example, if the workspace is example-workspace, the deployed app is parakeet-pipeline, and the Web Function is transcribe, the URL is:

```text
https://<workspace-slug>--parakeet-pipeline-transcribe.modal.run
```

Use the URL printed by modal deploy or shown in the deployed app's Web Functions section as the authority if the function has a custom label or the app uses a non-default environment suffix. A URL created with modal serve is temporary and normally includes a -dev suffix. See the Modal Web Function URL documentation (https://modal.com/docs/guide/webhook-urls) for the URL components and custom labels.

The Parakeet and WhisperX scripts in this skill expose a transcribe Web Function with method="POST" and requires_proxy_auth=True. Send a JSON request body; do not use the Modal dashboard URL, a GET request, or a local filesystem path for the media.

If no valid saved credentials are found, follow the first-time Proxy Token setup above before making an authenticated request. Keep the values outside the repository and out of transcripts, logs, prompts, and chat messages. Load them at request time through the saved credential file, environment variables, or an equivalent secret store.

For example:

```bash
export MODAL_TOKEN_ID="wk-..."
export MODAL_TOKEN_SECRET="ws-..."
```

Authenticate either with the Modal-Key and Modal-Secret headers or with the equivalent Authorization: Bearer TOKEN_ID.TOKEN_SECRET header. The separate headers are used in the example below. See the Modal Proxy Token documentation (https://modal.com/docs/guide/webhook-proxy-auth) for the supported authentication forms.

Submit an items list with stable integer indices. The media URLs must be anonymously downloadable by the Modal container:

```bash
curl -L --fail-with-body -H "Modal-Key: $MODAL_TOKEN_ID" -H "Modal-Secret: $MODAL_TOKEN_SECRET" -H "Content-Type: application/json" --data '{"items":[{"url":"https://example.test/lecture-01.m4a","index":0}]}' "https://<username>--<app>-transcribe.modal.run"
```

The Parakeet response contains one result per item, preserving url and index, with the detected duration and timestamped segments containing start, end, and text. For multiple recordings, keep each index unique and stable so results can be matched to the source order. The endpoint returns 400 for missing or malformed items, 422 when the downloaded file is not valid media or has no audio stream, and 502 when the remote download fails.

The Web Function may return a redirect for a request that exceeds the short HTTP request window while the underlying Modal Function continues processing. Keep -L in curl or enable redirect following in the HTTP client. The Modal timeout documentation (https://modal.com/docs/guide/webhook-timeouts) describes this behavior.

### Use Google Drive audio files

A Google Drive share link works only if the file is shared for anonymous viewing. In Google Drive, open Share, set General access to Anyone with the link, keep the role Viewer, and copy the link. Do not provide a link that requires the Modal container to sign in.

The usual shareable link has one of these forms:

```text
https://drive.google.com/file/d/<FILE_ID>/view?usp=sharing
https://drive.google.com/open?id=<FILE_ID>
```

Extract the exact file ID and convert it to the direct download URL:

```text
https://drive.google.com/uc?export=download&id=<FILE_ID>
```

Use that uc?export=download URL as the items[].url value. Before sending it to Modal, test that it downloads the media without authentication and does not return an HTML sign-in or confirmation page:

```bash
curl -L -o /dev/null -w "status=%{http_code} type=%{content_type}\n" "https://drive.google.com/uc?export=download&id=<FILE_ID>"
```

If the test returns an HTML page instead of the audio bytes, use a different publicly downloadable host or a signed download URL. The Modal code downloads the URL with a plain HTTP client and then runs ffprobe; it cannot use a user's browser cookies or complete a Google account login.

Keep the deployment name, endpoint URL, request payload, response, and errors in the current run context, using system temporary storage only if a tool requires a file:

- deployment name;
- endpoint URL;
- request payload;
- response; and
- errors.

For WhisperX only, when the recording is known to be in one language, you may include the language hint shown below:

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
