# Source the lecture

Obtain a timestamped transcript before lesson planning. Keep the original transcript and every revision as separate intermediate artifacts; never replace the source irreversibly.

## Preferred decision

Use Modal first for audio transcription. The bundled scripts are:

- [modal_parakeet.py](../scripts/modal_parakeet.py) for NVIDIA Parakeet.
- [modal_whisperx.py](../scripts/modal_whisperx.py) for WhisperX with word-aware segmenting and same-language input.

Deploy the selected script from the repository root:

```bash
modal deploy .agents/skills/review-class/scripts/modal_parakeet.py
modal deploy .agents/skills/review-class/scripts/modal_whisperx.py
```

The deploy command creates or updates a persistent Modal App and prints the Web Function URL; the URL is also available in the Modal dashboard. For a deliberate one-off smoke test, use the registered local entrypoint with `modal run` instead of creating a persistent deployment. The endpoints require the authentication configured by the script (`requires_proxy_auth=True`); use the credentials and HTTP client convention from the user's Modal environment rather than making the endpoint public.

The scripts expose an authenticated POST endpoint. Send a JSON body with an `items` list containing stable integer indices and audio URLs. WhisperX also accepts an optional BCP 47 `language` value. Keep the returned item indices so multiple recordings can be reassembled deterministically.

```json
{
  "items": [
    {"url": "https://example.test/lecture-01.m4a", "index": 0}
  ],
  "language": "en"
}
```

The local entrypoint is useful for a deliberate local run or a smoke test, but it is not the preferred production path. Local execution requires the model's dependencies, FFmpeg, and a compatible GPU; do not silently fall back to a slow or incomplete CPU transcription for a long lecture.

Normalize the endpoint response before planning: map each returned `start`, `end`, and `text` field to `start_seconds`, `end_seconds`, and `content`, retain `detected_language` when WhisperX supplies it, and preserve the raw response alongside the normalized transcript.

## If audio is not available

Ask the user for a timestamped transcript. Accept JSON, Markdown, plain text with timestamps, or another clearly structured format, then normalize it into ordered segments without changing the words. A useful normalized shape is:

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

If the user provides reference PDFs or notes, preserve their filenames and page boundaries. Use them to clarify or verify the lecture, not to expand the lesson beyond what the lecture supports.

Before moving to planning, verify that timestamps are ordered, non-negative, and non-empty; that the recording language is known or clearly marked as detected; and that the transcript can be traced back to its source recording or user submission.
