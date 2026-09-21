# domain-parser — TLD/SLD/subdomain split

**Base URL**: `https://domain-parser.nordman-tehau.workers.dev`
**Price**: $0.001 USDC per call, Base mainnet (`eip155:8453`)

## POST /v1/domain/parse

Split a domain name into TLD, SLD, and subdomain using the official Public Suffix List (handles
multi-part TLDs like `.co.uk` correctly, unlike a naive split on the last dot).

**Input** — JSON body: `{ "domain": "sub.example.co.uk" }`

**Output** (200, after payment):
```json
{
  "domain": "sub.example.co.uk",
  "tld": "co.uk",
  "sld": "example",
  "subdomain": "sub",
  "registrable_domain": "example.co.uk",
  "is_public_suffix": false
}
```

## Discovery

- `GET /agent.json`, `GET /llms.txt`, `GET /.well-known/x402` — same conventions as `markdown-x402`.

## Composing with domain-intelligence

`registrable_domain` from this endpoint's output is the correct input to pass to
`domain-intelligence`'s `/dns`, `/rdap`, `/tls`, or `/intelligence` routes (see
[domain-intelligence.md](domain-intelligence.md)) when the original string might include a
subdomain or an unusual multi-part TLD.
