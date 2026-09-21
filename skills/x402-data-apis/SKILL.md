---
name: x402-data-apis
description: Use when an agent needs to convert a URL/PDF/HTML/image to Markdown, parse a domain into TLD/SLD/subdomain, or look up DNS/RDAP/TLS domain intelligence — three pay-per-call x402 APIs on Base mainnet (USDC), no account or API key required.
---

# x402 Data APIs (Cloudflare Workers, Base mainnet)

Three composable, pay-per-call HTTP APIs for AI agents, gated by the [x402](https://x402.org)
payment protocol. No account, no API key, no subscription — each call costs a fixed amount of
USDC on Base mainnet (`eip155:8453`), paid inline via the standard `402 Payment Required` flow.

Use this skill when a task needs one of:
- **Clean Markdown from a URL, PDF, HTML page, or image** (for an LLM context window or a RAG index)
- **Structural parsing of a domain name** (TLD/SLD/subdomain split)
- **DNS records, domain registration data (RDAP/WHOIS), or SSL/TLS certificate details** for a domain

## How payment works

Every endpoint below returns `402 Payment Required` with a standard x402 `PAYMENT-REQUIRED`
challenge header (network `eip155:8453`, asset = USDC) when called without payment. Use any
x402 v2-compatible client to pay and retry automatically — e.g. Coinbase's `awal` CLI
(`npx awal@2.12.1 x402 pay <url> -X <method> -d <json>`, see
[coinbase/agentic-wallet-skills](https://github.com/coinbase/agentic-wallet-skills)) or the
`@x402/fetch` library (`wrapFetchWithPayment`) if the agent controls its own signer.

Each service also exposes a machine-readable manifest at `/.well-known/x402` and a
human-readable `/llms.txt`, and declares an x402 Bazaar discovery extension on its paid
route(s) so it is findable via `x402 bazaar search`.

## Available services

Pick the reference file matching the task:

- [references/markdown-conversion.md](references/markdown-conversion.md) — `markdown-x402`: URL/PDF/HTML/image → structured Markdown, $0.005/call
- [references/domain-parsing.md](references/domain-parsing.md) — `domain-parser`: domain → TLD/SLD/subdomain, $0.001/call
- [references/domain-intelligence.md](references/domain-intelligence.md) — `domain-intelligence`: DNS/RDAP/TLS lookups (+ 2 free routes, + MCP server), $0.001-$0.002/call

## Composing services

`domain-parser` and `domain-intelligence` are complementary: parse a raw domain string into its
registrable domain first (`domain-parser`), then look up DNS/RDAP/TLS data for it
(`domain-intelligence`). Both are cheap enough ($0.001-0.002) to call back-to-back for a single
agent task without materially affecting cost.
