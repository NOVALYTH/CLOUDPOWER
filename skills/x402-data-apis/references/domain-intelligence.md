# domain-intelligence — DNS / RDAP / TLS lookups

**Base URL**: `https://domain-intelligence.nordman-tehau.workers.dev`
**Prices**: Base mainnet (`eip155:8453`) USDC

| Route | Price | Description |
|---|---|---|
| `GET /normalize?domain=...` | free | Normalize/validate a domain string (no payment) |
| `GET /validate?domain=...` | free | Validate a domain string (no payment) |
| `GET /dns?domain=...` | $0.001 | DNS lookup: A/AAAA/MX/NS/TXT/CNAME/CAA records |
| `GET /rdap?domain=...` | $0.001 | Domain registration lookup (RDAP/WHOIS): registrar, dates, status |
| `GET /tls?domain=...` | $0.001 | SSL/TLS certificate inspection: expiration, issuer, chain |
| `GET /intelligence?domain=...` | $0.002 | All three combined in one call |

All paid responses include `cached` (bool) and `data_age_seconds` — results are cached in KV,
so repeat lookups for the same domain within the TTL window are served from cache (still
counted as one billed request, per x402/Cloudflare's per-request model).

**Example** (`GET /dns?domain=example.com`, 200 after payment):
```json
{
  "ok": true,
  "domain": "example.com",
  "cached": false,
  "data_age_seconds": 0,
  "dns": { "a": ["93.184.216.34"], "ns": ["a.iana-servers.net"], "mx": [], "txt": [], "cname": [], "caa": [], "errors": {}, "minTtlSeconds": 300 }
}
```

## MCP server

A stateless Streamable HTTP MCP server is available at `POST /mcp`, exposing
`normalize_domain`/`validate_domain` (free) and `dns_lookup`/`rdap_lookup`/`tls_lookup`/
`domain_intelligence` (paid, per-call x402) as MCP tools — usable directly by any MCP-compatible
agent client without hand-rolling HTTP calls.

## Discovery

- `GET /llms.txt`, `GET /.well-known/x402` — same conventions as the other two services.

## Notes

- Domain strings are validated before the payment gate — a malformed domain returns `400`
  without ever charging.
