# markdown-x402 — URL/PDF/HTML/image to Markdown

**Base URL**: `https://markdown-x402.nordman-tehau.workers.dev`
**Price**: $0.005 USDC per call, Base mainnet (`eip155:8453`)

## POST /convert

Convert a URL, PDF, HTML, or image file to structured JSON containing the Markdown content,
title, section headings, and word count.

**Input** — either:
- JSON body: `{ "url": "https://example.com/article" }`
- `multipart/form-data` with a `document` field (PDF/HTML/image file, max 10 MB)

**Output** (200, after payment):
```json
{
  "source_type": "url",
  "source": "https://example.com/article",
  "converted_at": "2026-09-09T12:00:00.000Z",
  "title": "Example Title",
  "word_count": 128,
  "neuron_tokens": 340,
  "sections": [{ "heading": "Example Title", "level": 1, "char_offset": 0 }],
  "markdown": "# Example Title\n\nContent..."
}
```

## Discovery

- `GET /agent.json` — machine-readable endpoint description + payment terms
- `GET /llms.txt` — human/LLM-readable documentation
- `GET /.well-known/x402` — x402 resource-server manifest

## Notes

- Fetch timeout: 15s. Max source size: 10 MB. Unsupported MIME types return `415`.
- `neuron_tokens` reflects actual Workers AI usage for the conversion (informational; price is
  currently flat regardless of document size).
