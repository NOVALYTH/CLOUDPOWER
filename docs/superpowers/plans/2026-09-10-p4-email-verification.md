# p4-email-verification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy `products/p4-email-verification`, a Free Tier Cloudflare Worker that validates an
email address (syntax + MX resolution + disposable-domain detection) behind an x402 paywall, priced
at $0.002/call.

**Architecture:** Single monolithic Worker (`src/index.ts`, Hono + `@x402/hono`), matching the
p1/p2 file-structure convention that `ARCHITECTURE.md` (2026-09-10 entry) sets as the portfolio's
default. Pure logic (syntax parsing, risk classification, MX lookup, disposable-domain lookup) lives
in small, independently-testable modules; `src/index.ts` wires them behind the paywall. No KV, no
Analytics Engine, no shared code with other products — same duplication-over-sharing stance as p2.

**Tech Stack:** Hono ^4.13.7, `@x402/core` / `@x402/evm` / `@x402/extensions` / `@x402/hono`
^2.25.0, TypeScript ^5.7.0, Vitest ^4.1.0 + `@cloudflare/vitest-plugin` ^1.1.5, `node:dns` (Workers
`nodejs_compat`) for MX resolution.

**Spec:** `docs/superpowers/specs/2026-09-10-p4-email-verification-design.md`

## Global Constraints

- DNS-only verification — no SMTP/RCPT TO check (spec §Périmètre, explicitly out of scope)
- Price: $0.002 per `POST /verify` call (spec, confirmed by user)
- Disposable-domain list is a static, build-time-embedded snapshot — no runtime network fetch
  (spec §Composants)
- Testnet round-trip required before any mainnet switch — `.claude/hooks/compliance-gate.py`
  mechanically blocks a `wrangler.jsonc` mainnet value without
  `.claude/context/testnet-verified-p4-email-verification.md` present (CLAUDE.md §Sécurité)
- Never commit a private key, seed phrase, or secret literal to `wrangler.jsonc`/source — `PAY_TO`
  is a public wallet address (not a secret in the security sense) but is still configured via
  `wrangler secret put` per the established p1/p2/p3 convention, not committed as a `vars` literal
- No `shared/` — this product does not import from `p1`/`p2`/`p3` or vice versa (CLAUDE.md
  §Philosophie produit: no shared layer until 2+ products generate revenue)

---

### Task 1: Scaffold the product + pricing constant

**Files:**
- Create: `products/p4-email-verification/wrangler.jsonc`
- Create: `products/p4-email-verification/package.json`
- Create: `products/p4-email-verification/tsconfig.json`
- Create: `products/p4-email-verification/vitest.config.ts`
- Create: `products/p4-email-verification/src/pricing.ts`

**Interfaces:**
- Produces: `PRICE_USD: "$0.002"` (string, matches the `price` field shape `@x402/hono`'s
  `paymentMiddleware` route config expects — see p2's `src/index.ts:72`) and
  `PRICE_USD_NUMBER: 0.002` (number, for logging), both consumed by Task 5.

- [ ] **Step 1: Create `wrangler.jsonc`**

```jsonc
{
  "$schema": "node_modules/wrangler/config-schema.json",
  "name": "email-verification",
  "main": "src/index.ts",
  "compatibility_date": "2026-09-10",
  // Required for `node:dns` (MX resolution) — see src/dns.ts. Without this
  // flag, node:dns throws at import time on Workers.
  "compatibility_flags": ["nodejs_compat"],
  "observability": {
    "enabled": true
  }
  // PAY_TO configured via `wrangler secret put PAY_TO` (Task 6) — never
  // committed here, same convention as p1/p2.
  //
  // X402_NETWORK is set via `wrangler secret put X402_NETWORK` during the
  // testnet phase (Task 6) then flipped to a committed `vars` entry only
  // once testnet-verified-p4-email-verification.md exists (Task 7) — see
  // that task for the exact block added here.
}
```

- [ ] **Step 2: Create `package.json`**

```json
{
  "name": "email-verification",
  "private": true,
  "version": "0.0.1",
  "description": "Validate an email address's syntax, MX resolution, and disposable-domain status. Pay only when you use it.",
  "type": "module",
  "scripts": {
    "dev": "wrangler dev",
    "deploy": "wrangler deploy",
    "tail": "wrangler tail",
    "test": "vitest run",
    "test-payment": "node test-payment.mjs",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "@x402/core": "^2.25.0",
    "@x402/evm": "^2.25.0",
    "@x402/extensions": "^2.25.0",
    "@x402/hono": "^2.25.0",
    "hono": "^4.13.7"
  },
  "devDependencies": {
    "@types/node": "^26.5.0",
    "@cloudflare/vitest-plugin": "^1.1.5",
    "@cloudflare/workers-types": "^5.20260907.1",
    "@x402/fetch": "^2.25.0",
    "typescript": "^5.7.0",
    "viem": "^2.48.11",
    "vitest": "^4.1.0",
    "wrangler": "^4.129.1"
  }
}
```

- [ ] **Step 3: Create `tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "es2021",
    "lib": ["es2021"],
    "module": "es2022",
    "moduleResolution": "bundler",
    "types": ["@cloudflare/workers-types", "@types/node"],
    "strict": true,
    "skipLibCheck": true,
    "resolveJsonModule": true,
    "noEmit": true
  },
  "include": ["src", "tests"]
}
```

- [ ] **Step 4: Create `vitest.config.ts`**

```ts
import { cloudflareTest } from "@cloudflare/vitest-plugin";
import { defineConfig } from "vitest/config";

export default defineConfig({
	plugins: [
		cloudflareTest({
			wrangler: { configPath: "./wrangler.jsonc" },
		}),
	],
});
```

- [ ] **Step 5: Create `src/pricing.ts`**

```ts
// Single source of truth for the price, consumed by both the payment
// middleware config (string form, required by @x402/hono) and logging
// (number form) — same split as p2's PRICE_USD/PRICE_USD_NUMBER.
export const PRICE_USD = "$0.002";
export const PRICE_USD_NUMBER = 0.002;
```

- [ ] **Step 6: Install dependencies and verify the scaffold compiles**

Run (from `products/p4-email-verification/`):
```bash
npm install
npm run typecheck
```
Expected: both commands succeed with no errors (nothing references `pricing.ts` yet, so
`typecheck` passing here just confirms the TS config itself is valid).

- [ ] **Step 7: Commit**

```bash
git add products/p4-email-verification/wrangler.jsonc products/p4-email-verification/package.json products/p4-email-verification/package-lock.json products/p4-email-verification/tsconfig.json products/p4-email-verification/vitest.config.ts products/p4-email-verification/src/pricing.ts products/p4-email-verification/.gitignore
git commit -m "feat(p4): scaffold email-verification product

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```
(If `products/p4-email-verification/.gitignore` doesn't exist because the repo root `.gitignore`
already excludes `node_modules/`/`.wrangler/`/`.dev.vars` globally, skip it — check with
`git status` first; don't create a redundant one.)

---

### Task 2: Email syntax parsing + risk classification

**Files:**
- Create: `products/p4-email-verification/src/email.ts`
- Test: `products/p4-email-verification/tests/email.test.ts`

**Interfaces:**
- Consumes: nothing (pure logic, no dependency on Tasks 1/3/4 beyond the package scaffold)
- Produces:
  - `parseSyntax(email: string): { valid: boolean; domain: string | null }`
  - `classifyRisk(input: { validSyntax: boolean; mxFound: boolean; disposable: boolean }): "low" | "medium" | "high"`
  - Consumed by Task 5's `POST /verify` handler.

- [ ] **Step 1: Write the failing tests**

Create `tests/email.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { classifyRisk, parseSyntax } from "../src/email";

describe("parseSyntax", () => {
	it("accepts a well-formed address and lowercases the domain", () => {
		const result = parseSyntax("User@Example.COM");
		expect(result).toEqual({ valid: true, domain: "example.com" });
	});

	it("rejects an address with no @", () => {
		expect(parseSyntax("not-an-email")).toEqual({ valid: false, domain: null });
	});

	it("rejects an address with no domain after @", () => {
		expect(parseSyntax("user@")).toEqual({ valid: false, domain: null });
	});

	it("rejects an address with no TLD", () => {
		expect(parseSyntax("user@localhost")).toEqual({ valid: false, domain: null });
	});

	it("rejects an empty string", () => {
		expect(parseSyntax("")).toEqual({ valid: false, domain: null });
	});

	it("rejects an address longer than 254 characters", () => {
		const long = "a".repeat(250) + "@b.co";
		expect(parseSyntax(long)).toEqual({ valid: false, domain: null });
	});

	it("accepts common plus-addressing and dotted local parts", () => {
		expect(parseSyntax("first.last+tag@example.co.uk")).toEqual({
			valid: true,
			domain: "example.co.uk",
		});
	});
});

describe("classifyRisk", () => {
	it("is high when syntax is invalid, regardless of other fields", () => {
		expect(classifyRisk({ validSyntax: false, mxFound: true, disposable: false })).toBe("high");
	});

	it("is high when no MX record was found", () => {
		expect(classifyRisk({ validSyntax: true, mxFound: false, disposable: false })).toBe("high");
	});

	it("is high (not medium) when both syntax is invalid AND the domain is disposable", () => {
		expect(classifyRisk({ validSyntax: false, mxFound: false, disposable: true })).toBe("high");
	});

	it("is medium when syntax is valid, MX exists, but the domain is disposable", () => {
		expect(classifyRisk({ validSyntax: true, mxFound: true, disposable: true })).toBe("medium");
	});

	it("is low when syntax is valid, MX exists, and the domain is not disposable", () => {
		expect(classifyRisk({ validSyntax: true, mxFound: true, disposable: false })).toBe("low");
	});
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run (from `products/p4-email-verification/`): `npm test -- tests/email.test.ts`
Expected: FAIL — `Cannot find module '../src/email'` (file doesn't exist yet).

- [ ] **Step 3: Write the implementation**

Create `src/email.ts`:

```ts
// Syntax validation + risk classification for email addresses. This is a
// pragmatic RFC5322-lite filter for "does this look like a real address
// that could receive mail" (signup-form hygiene), not a full grammar
// validator — see docs/superpowers/specs/2026-09-10-p4-email-verification-design.md.

const EMAIL_PATTERN =
	/^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$/;

export interface SyntaxResult {
	valid: boolean;
	domain: string | null;
}

export function parseSyntax(email: string): SyntaxResult {
	if (typeof email !== "string" || email.length === 0 || email.length > 254) {
		return { valid: false, domain: null };
	}
	if (!EMAIL_PATTERN.test(email)) {
		return { valid: false, domain: null };
	}
	const domain = email.slice(email.lastIndexOf("@") + 1).toLowerCase();
	return { valid: true, domain };
}

export type Risk = "low" | "medium" | "high";

export interface RiskInput {
	validSyntax: boolean;
	mxFound: boolean;
	disposable: boolean;
}

export function classifyRisk(input: RiskInput): Risk {
	if (!input.validSyntax || !input.mxFound) return "high";
	if (input.disposable) return "medium";
	return "low";
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `npm test -- tests/email.test.ts`
Expected: PASS (12 tests).

- [ ] **Step 5: Commit**

```bash
git add products/p4-email-verification/src/email.ts products/p4-email-verification/tests/email.test.ts
git commit -m "feat(p4): email syntax parsing and risk classification

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: Disposable-domain detection

**Files:**
- Create: `products/p4-email-verification/src/data/disposable-domains.ts`
- Test: `products/p4-email-verification/tests/data/disposable-domains.test.ts`

**Interfaces:**
- Consumes: nothing
- Produces: `isDisposable(domain: string): boolean` — consumed by Task 5's `POST /verify` handler.

- [ ] **Step 1: Write the failing tests**

Create `tests/data/disposable-domains.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { isDisposable } from "../../src/data/disposable-domains";

describe("isDisposable", () => {
	it("flags a well-known disposable domain", () => {
		expect(isDisposable("mailinator.com")).toBe(true);
	});

	it("is case-insensitive", () => {
		expect(isDisposable("MAILINATOR.COM")).toBe(true);
	});

	it("does not flag a mainstream provider", () => {
		expect(isDisposable("gmail.com")).toBe(false);
	});

	it("does not flag an unknown domain", () => {
		expect(isDisposable("some-random-company.example")).toBe(false);
	});

	it("returns false for an empty string", () => {
		expect(isDisposable("")).toBe(false);
	});
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `npm test -- tests/data/disposable-domains.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Write the implementation**

Create `src/data/disposable-domains.ts`:

```ts
// Curated snapshot of well-known disposable/throwaway email domains, vendored
// at development time (no runtime fetch — spec §Composants). This is a
// starting set of widely-recognized providers, not an exhaustive list;
// expanding it (e.g. syncing a larger open-source list) is a fast-follow,
// not a blocker for V1 — see docs/superpowers/specs/2026-09-10-p4-email-verification-design.md.
const DOMAINS = [
	// mailinator family
	"mailinator.com", "mailinator.net", "mailinator.org", "mailinator2.com",
	// guerrillamail family
	"guerrillamail.com", "guerrillamail.info", "guerrillamail.biz", "guerrillamail.de",
	"guerrillamail.org", "guerrillamail.net", "guerrillamailblock.com", "sharklasers.com",
	"grr.la", "pokemail.net", "spam4.me",
	// 10 minute / temp mail family
	"10minutemail.com", "10minutemail.net", "20minutemail.com",
	"temp-mail.org", "tempmail.com", "tempmail.net", "tempmailo.com", "tempail.com",
	"tempr.email", "tempinbox.com", "mytemp.email",
	// throwaway family
	"throwawaymail.com", "throwam.com",
	// yopmail family
	"yopmail.com", "yopmail.fr", "yopmail.net",
	// trashmail family
	"trashmail.com", "trashmail.net", "trash-mail.com",
	// dispostable / getnada / maildrop
	"dispostable.com", "getnada.com", "nada.email", "maildrop.cc", "mailnesia.com",
	"mailcatch.com", "mintemail.com", "fakeinbox.com", "moakt.com", "emailondeck.com",
	"spamgourmet.com", "discardmail.com", "discardmail.de", "mohmal.com",
	"correotemporal.org", "mail-temporaire.fr", "jetable.org",
	// spambog family
	"spambog.com", "spambog.de", "spambog.ru", "mailforspam.com", "mailnull.com",
	"sogetthis.com", "spamherelots.com", "tempemail.net", "tempemail.co", "meltmail.com",
	"mt2015.com", "incognitomail.com", "e4ward.com", "instant-mail.de", "luxusmail.org",
	"burnermail.io", "emailtemporario.com.br",
] as const;

export const DISPOSABLE_DOMAINS: ReadonlySet<string> = new Set(DOMAINS);

export function isDisposable(domain: string): boolean {
	if (typeof domain !== "string" || domain.length === 0) return false;
	return DISPOSABLE_DOMAINS.has(domain.toLowerCase());
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `npm test -- tests/data/disposable-domains.test.ts`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add products/p4-email-verification/src/data/disposable-domains.ts products/p4-email-verification/tests/data/disposable-domains.test.ts
git commit -m "feat(p4): disposable-domain detection

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 4: MX resolution

**Files:**
- Create: `products/p4-email-verification/src/dns.ts`
- Test: `products/p4-email-verification/tests/dns.test.ts`

**Interfaces:**
- Consumes: nothing (resolver is injected for testing, defaults to `node:dns.promises`)
- Produces: `resolveMx(domain: string, resolver?: MxResolver): Promise<{ mxFound: boolean; records: string[]; error?: string }>` — consumed by Task 5.

- [ ] **Step 1: Write the failing tests**

Create `tests/dns.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { resolveMx, type MxResolver } from "../src/dns";

function enotfound(): never {
	const err = new Error("not found") as NodeJS.ErrnoException;
	err.code = "ENOTFOUND";
	throw err;
}

function servfail(): never {
	const err = new Error("server failure") as NodeJS.ErrnoException;
	err.code = "ESERVFAIL";
	throw err;
}

describe("resolveMx", () => {
	it("returns mxFound: true and the exchange hostnames when records exist", async () => {
		const resolver: MxResolver = {
			resolveMx: async () => [
				{ exchange: "mail.example.com", priority: 10 },
				{ exchange: "mail2.example.com", priority: 20 },
			],
		};
		const result = await resolveMx("example.com", resolver);
		expect(result).toEqual({ mxFound: true, records: ["mail.example.com", "mail2.example.com"] });
	});

	it("treats ENOTFOUND as 'no MX', not an error", async () => {
		const resolver: MxResolver = { resolveMx: async () => enotfound() };
		const result = await resolveMx("no-mail-domain.example", resolver);
		expect(result).toEqual({ mxFound: false, records: [] });
	});

	it("treats ENODATA as 'no MX', not an error", async () => {
		const err = new Error("no data") as NodeJS.ErrnoException;
		err.code = "ENODATA";
		const resolver: MxResolver = {
			resolveMx: async () => {
				throw err;
			},
		};
		const result = await resolveMx("example.com", resolver);
		expect(result).toEqual({ mxFound: false, records: [] });
	});

	it("surfaces a real query failure in `error` instead of silently returning empty", async () => {
		const resolver: MxResolver = { resolveMx: async () => servfail() };
		const result = await resolveMx("example.com", resolver);
		expect(result.mxFound).toBe(false);
		expect(result.records).toEqual([]);
		expect(result.error).toBe("ESERVFAIL");
	});
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `npm test -- tests/dns.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Write the implementation**

Create `src/dns.ts`:

```ts
// MX-only DNS lookup for email domain verification — trimmed from
// p3-domain-intelligence's src/engine/dns.ts (A/AAAA/NS/TXT/CNAME/CAA are
// not needed for this product). Same caveat applies: node:dns's generic
// resolve()/lookup() are NOT implemented on Workers — only the specific
// typed resolvers (resolveMx) work.
//
// The resolver is injected (defaulting to the real node:dns.promises) so
// this module's error classification is unit-testable without live DNS.

import dns from "node:dns";

export interface MxLookupResult {
	mxFound: boolean;
	records: string[];
	error?: string;
}

export interface MxResolver {
	resolveMx(hostname: string): Promise<{ exchange: string; priority: number }[]>;
}

export const nodeMxResolver: MxResolver = dns.promises as unknown as MxResolver;

// Node DNS error codes that mean "queried successfully, no MX records exist"
// rather than "the query failed" — same distinction as p3's dns.ts.
const NO_DATA_CODES = new Set(["ENOTFOUND", "ENODATA"]);

export async function resolveMx(domain: string, resolver: MxResolver = nodeMxResolver): Promise<MxLookupResult> {
	try {
		const records = await resolver.resolveMx(domain);
		return { mxFound: records.length > 0, records: records.map((r) => r.exchange) };
	} catch (err) {
		const code = (err as NodeJS.ErrnoException)?.code;
		if (code && NO_DATA_CODES.has(code)) {
			return { mxFound: false, records: [] };
		}
		return { mxFound: false, records: [], error: code ?? (err as Error).message ?? "unknown_error" };
	}
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `npm test -- tests/dns.test.ts`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add products/p4-email-verification/src/dns.ts products/p4-email-verification/tests/dns.test.ts
git commit -m "feat(p4): MX resolution

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 5: Wire the Worker (x402 paywall + discovery + local validation)

**Files:**
- Create: `products/p4-email-verification/src/index.ts`

**Interfaces:**
- Consumes: `parseSyntax`/`classifyRisk` (Task 2), `isDisposable` (Task 3), `resolveMx` (Task 4),
  `PRICE_USD`/`PRICE_USD_NUMBER` (Task 1)
- Produces: the deployed HTTP surface (`GET /`, `GET /agent.json`, `GET /llms.txt`,
  `GET /.well-known/x402`, `GET /robots.txt`, `GET /sitemap.xml`, `POST /verify`) — nothing later
  in this plan imports from this file (it's the top-level entrypoint).

- [ ] **Step 1: Write `src/index.ts`**

```ts
import { Hono } from "hono";
import { cors } from "hono/cors";
import { paymentMiddleware } from "@x402/hono";
import { x402ResourceServer, HTTPFacilitatorClient } from "@x402/core/server";
import { registerExactEvmScheme } from "@x402/evm/exact/server";
import { declareDiscoveryExtension } from "@x402/extensions/bazaar";
import { parseSyntax, classifyRisk } from "./email";
import { resolveMx } from "./dns";
import { isDisposable } from "./data/disposable-domains";
import { PRICE_USD, PRICE_USD_NUMBER } from "./pricing";

export interface Env {
	PAY_TO: string;
	// "mainnet" switches to Base mainnet; anything else (including unset)
	// stays on Base Sepolia testnet. Set via `wrangler secret put X402_NETWORK`
	// during the testnet phase (Task 6), then promoted to a committed `vars`
	// entry in wrangler.jsonc once testnet-verified-p4-email-verification.md
	// exists (Task 7) — see compliance-gate.py, which gates exactly this.
	X402_NETWORK?: string;
	// Optional override; defaults to the public testnet facilitator below.
	// Set to https://facilitator.payai.network (the fleet's mainnet
	// facilitator, confirmed working 2026-09-09) before the mainnet switch.
	X402_FACILITATOR_URL?: string;
}

const EIP155_BASE = "eip155:8453" as const;
const BASE_SEPOLIA = "eip155:84532" as const;

// English on purpose — the x402 Bazaar indexes this via semantic/vector
// search (CDP embeddings), and observed agent queries are English. Same
// note as p1/p2/p3's src/index.ts.
const AGENT_JSON_BASE = {
	name: "email-verification",
	version: "1.0.0",
	description:
		"Verify an email address: syntax validation, MX record resolution (can the domain receive mail?), and disposable/throwaway domain detection. Composable primitive for AI agents cleaning signup or lead data. Inline x402 payment, no account or API key needed.",
	endpoints: [
		{
			path: "/verify",
			method: "POST",
			description: "Validate an email address's syntax, MX resolution, and disposable-domain status.",
			payment: {
				protocol: "x402",
				amount: "0.002",
				currency: "USDC",
			},
			input: {
				type: "object",
				description: 'JSON { "email": string }',
			},
			output: {
				type: "object",
				properties: {
					email: { type: "string" },
					valid_syntax: { type: "boolean" },
					domain: { type: "string" },
					mx_found: { type: "boolean" },
					mx_records: { type: "array", items: { type: "string" } },
					disposable: { type: "boolean" },
					risk: { type: "string", enum: ["low", "medium", "high"] },
				},
			},
		},
	],
};

function llmsTxt(payTo: string, networkLabel: string, network: string): string {
	return `# email-verification

> Verifies an email address's syntax, MX resolution, and disposable-domain status.

## Payment

This service uses the x402 protocol (v2). Each POST /verify request requires a payment of
0.002 USDC on ${networkLabel} (network ${network}) to ${payTo}.

## Endpoints

### POST /verify

Body JSON: { "email": "user@example.com" }

Response 200 (after payment):
{
  "email": "user@example.com",
  "valid_syntax": true,
  "domain": "example.com",
  "mx_found": true,
  "mx_records": ["mail.example.com"],
  "disposable": false,
  "risk": "low"
}

## Usage

1. Send the request without payment -> receive 402 + x402 challenge
2. Pay 0.002 USDC on ${networkLabel} to the address shown
3. Resend the request with the payment credential
4. Receive the structured JSON result
`;
}

const VERIFY_DISCOVERY = declareDiscoveryExtension({
	bodyType: "json",
	input: { email: "user@example.com" },
	inputSchema: {
		type: "object",
		properties: {
			email: { type: "string", description: "Email address to verify" },
		},
		required: ["email"],
	},
	output: {
		example: {
			email: "user@example.com",
			valid_syntax: true,
			domain: "example.com",
			mx_found: true,
			mx_records: ["mail.example.com"],
			disposable: false,
			risk: "low",
		},
	},
});

function logPaymentEvent(event: string, fields: Record<string, unknown> = {}) {
	console.log(JSON.stringify({ ts: Date.now(), event, ...fields }));
}

function getNetwork(env: Env): typeof EIP155_BASE | typeof BASE_SEPOLIA {
	return env.X402_NETWORK === "mainnet" ? EIP155_BASE : BASE_SEPOLIA;
}

// Cached per isolate: constructing the resource server and payment
// middleware does real setup work (route/extension validation) that
// doesn't depend on anything request-specific once env is known.
// Rebuilding this on every request cost ~15ms of CPU/request on p2/p3
// before that was fixed (2026-09-09, commit 209d193) — applying the fix
// from day one here instead of retrofitting it later.
let cachedMiddleware: ReturnType<typeof paymentMiddleware> | null = null;
function getPaymentMiddleware(env: Env) {
	if (cachedMiddleware) return cachedMiddleware;
	const network = getNetwork(env);
	const facilitator = new HTTPFacilitatorClient({
		url: env.X402_FACILITATOR_URL ?? "https://x402.org/facilitator",
	});
	const resourceServer = registerExactEvmScheme(new x402ResourceServer(facilitator));
	cachedMiddleware = paymentMiddleware(
		{
			"/verify": {
				accepts: {
					scheme: "exact",
					price: PRICE_USD,
					network,
					payTo: env.PAY_TO,
					maxTimeoutSeconds: 300,
				},
				extensions: { ...VERIFY_DISCOVERY },
				description: "Validate an email address: syntax, MX resolution, disposable-domain check.",
			},
		},
		resourceServer,
	);
	return cachedMiddleware;
}

const app = new Hono<{ Bindings: Env }>();

// CORS: the x402 headers (PAYMENT-SIGNATURE in the request,
// PAYMENT-REQUIRED/PAYMENT-RESPONSE in the response) must be explicitly
// allowed/exposed, or a browser-based x402 client can't send/read them even
// with CORS "on". No cookie/session here (payment is authenticated by
// signature, not cookie), so permissive origin carries no CSRF risk — same
// reasoning as p1/p2/p3.
app.use(
	"*",
	cors({
		origin: "*",
		allowHeaders: ["Content-Type", "PAYMENT-SIGNATURE"],
		exposeHeaders: ["PAYMENT-REQUIRED", "PAYMENT-RESPONSE"],
	}),
);

app.get("/robots.txt", (c) => c.text("User-agent: *\nAllow: /\n"));

app.get("/sitemap.xml", (c) => {
	const origin = new URL(c.req.url).origin;
	const urls = ["/agent.json", "/llms.txt", "/.well-known/x402"];
	return c.text(
		`<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls
			.map((u) => `  <url><loc>${origin}${u}</loc></url>`)
			.join("\n")}\n</urlset>\n`,
		200,
		{ "Content-Type": "application/xml" },
	);
});

app.get("/", (c) => c.json({ name: "email-verification", status: "ok" }));

app.get("/agent.json", (c) => {
	const network = getNetwork(c.env);
	return c.json({
		...AGENT_JSON_BASE,
		endpoints: AGENT_JSON_BASE.endpoints.map((e) => ({
			...e,
			payment: { ...e.payment, payTo: c.env.PAY_TO, network },
		})),
	});
});

app.get("/llms.txt", (c) => {
	const network = getNetwork(c.env);
	const networkLabel = network === EIP155_BASE ? "Base mainnet" : "Base Sepolia (testnet)";
	return c.text(llmsTxt(c.env.PAY_TO, networkLabel, network));
});

app.get("/.well-known/x402", (c) => {
	const origin = new URL(c.req.url).origin;
	const network = getNetwork(c.env);
	return c.json({
		x402Version: 2,
		kind: "resource-server",
		name: "email-verification",
		description: AGENT_JSON_BASE.description,
		updated: "2026-09-10T00:00:00.000Z",
		resources: [
			{
				url: `${origin}/verify`,
				method: "POST",
				description: "Validate an email address's syntax, MX resolution, and disposable-domain status",
				price_usd: "0.002",
				network,
				payTo: c.env.PAY_TO,
				asset: "USDC",
			},
		],
	});
});

// Paywall x402 inline — restricted to POST (a GET/PUT probe on this path
// must never reach this middleware, or the Bazaar extension would announce
// the wrong HTTP method to agents — same reasoning as p1/p2/p3).
app.post("/verify", async (c, next) => {
	const res = await getPaymentMiddleware(c.env)(c, next);
	if (res && res.status === 402) {
		const hasPaymentHeader = !!c.req.header("PAYMENT-SIGNATURE");
		logPaymentEvent(hasPaymentHeader ? "payment_attempt_rejected" : "payment_challenge", { path: "/verify" });
	}
	return res;
});

app.post("/verify", async (c) => {
	const body = await c.req.json<{ email?: string }>().catch(() => null);
	if (!body || typeof body.email !== "string") {
		return c.json({ error: "Missing 'email' in JSON body" }, 400);
	}

	const { valid, domain } = parseSyntax(body.email);
	let mxFound = false;
	let mxRecords: string[] = [];
	if (valid && domain) {
		const mx = await resolveMx(domain);
		mxFound = mx.mxFound;
		mxRecords = mx.records;
	}
	const disposable = domain ? isDisposable(domain) : false;
	const risk = classifyRisk({ validSyntax: valid, mxFound, disposable });

	logPaymentEvent("payment_success", { endpoint: "/verify", status: 200, paid: true, amount: PRICE_USD_NUMBER });

	return c.json({
		email: body.email,
		valid_syntax: valid,
		domain,
		mx_found: mxFound,
		mx_records: mxRecords,
		disposable,
		risk,
	});
});

export default app;
```

- [ ] **Step 2: Typecheck**

Run: `npm run typecheck`
Expected: no errors.

- [ ] **Step 3: Run the full test suite**

Run: `npm test`
Expected: all 21 tests (Tasks 2-4) still pass — this task added no new unit tests (the paywall/HTTP
wiring is verified against a live `wrangler dev` in Step 4, matching how p1/p2/p3 validate their
route layer — none of them have route-level Vitest tests either, only the pure-logic layer).

- [ ] **Step 4: Local validation against `wrangler dev`**

Run (from `products/p4-email-verification/`): `npm run dev`

In a second terminal, with the dev server running on `http://localhost:8787`:

```bash
# Health check
curl -i http://localhost:8787/
# Expect: 200 { "name": "email-verification", "status": "ok" }

# Discovery
curl http://localhost:8787/agent.json
curl http://localhost:8787/llms.txt
curl http://localhost:8787/.well-known/x402
curl http://localhost:8787/robots.txt
curl http://localhost:8787/sitemap.xml
# Expect: all 200, well-formed JSON/text

# 402 challenge (no payment credential)
curl -i -X POST http://localhost:8787/verify -H "Content-Type: application/json" -d '{"email":"user@example.com"}'
# Expect: 402 with a WWW-Authenticate / x402 challenge body

# 400 on malformed body
curl -i -X POST http://localhost:8787/verify -H "Content-Type: application/json" -d '{}'
# Expect: 400 { "error": "Missing 'email' in JSON body" }
```

Note: `wrangler dev` will not have `PAY_TO` set yet (Task 6 configures it) — if the payment
middleware errors instead of returning a 402 challenge because `payTo` is empty, set a placeholder
local var for this manual check only:
`echo "PAY_TO=0x0000000000000000000000000000000000dEaD" > .dev.vars` (gitignored, local-only, not a
real deploy — delete or leave as-is, Task 6 configures the real secret independently for the
deployed Worker).

- [ ] **Step 5: Commit**

```bash
git add products/p4-email-verification/src/index.ts
git commit -m "feat(p4): wire x402 paywall, POST /verify, and discovery routes

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 6: Secrets + testnet deploy + testnet payment proof

**Files:**
- Create: `products/p4-email-verification/test-payment.mjs`
- Create: `.claude/context/testnet-verified-p4-email-verification.md` (after a successful run)

**Interfaces:**
- Consumes: the deployed testnet Worker from this task's own deploy step
- Produces: `.claude/context/testnet-verified-p4-email-verification.md`, required by
  `compliance-gate.py` before Task 7's mainnet switch can be written to `wrangler.jsonc`

- [ ] **Step 1: Create `test-payment.mjs`** (adapted from `products/p2-domain-parser/test-payment.mjs`)

```js
// End-to-end x402 payment test against email-verification (Base Sepolia testnet).
//
// RUN THIS YOURSELF, with YOUR OWN disposable testnet key — never shared, never
// committed, never pasted into a conversation. Never use a key holding real mainnet
// funds. This key belongs to the test PAYER, distinct from PAY_TO (the wallet that
// RECEIVES payments, already configured as a secret on the Worker).
//
// Prerequisites:
//   1. npm install (from products/p4-email-verification)
//   2. A test address funded with ETH + USDC on Base Sepolia:
//        - ETH (gas)  : https://docs.base.org/get-started/get-funds (Base Sepolia faucet)
//        - USDC       : https://faucet.circle.com  (choose "Base Sepolia")
//   3. TESTNET_PRIVATE_KEY=0x... node test-payment.mjs
//      (PowerShell: $env:TESTNET_PRIVATE_KEY="0x..."; node test-payment.mjs)
//
// Optional: TARGET_URL (default https://email-verification.nordman-tehau.workers.dev/verify),
// TEST_EMAIL (default user@example.com).

import { privateKeyToAccount } from "viem/accounts";
import { x402Client } from "@x402/core/client";
import { ExactEvmScheme } from "@x402/evm";
import { wrapFetchWithPayment } from "@x402/fetch";

const PRIVATE_KEY = process.env.TESTNET_PRIVATE_KEY;
const WORKER_BASE = process.env.WORKER_BASE || "https://email-verification.nordman-tehau.workers.dev";
const TEST_EMAIL = process.env.TEST_EMAIL || "user@example.com";
const TARGET_URL = process.env.TARGET_URL || `${WORKER_BASE}/verify`;

if (!PRIVATE_KEY || !PRIVATE_KEY.startsWith("0x")) {
  console.error(
    "Missing TESTNET_PRIVATE_KEY (disposable testnet key, format 0x...). See the header comments."
  );
  process.exit(1);
}

const account = privateKeyToAccount(PRIVATE_KEY);
console.log(`Testnet wallet (payer): ${account.address}`);
console.log(`Target                : ${TARGET_URL}`);

const client = new x402Client().register("eip155:84532", new ExactEvmScheme(account));
const fetchWithPayment = wrapFetchWithPayment(fetch, client);

console.log("\nSending paid request...\n");

const response = await fetchWithPayment(TARGET_URL, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ email: TEST_EMAIL }),
});

console.log(`Status: ${response.status}`);
const body = await response.json();
console.log("Response:", JSON.stringify(body, null, 2));

if (response.status === 200) {
  console.log(
    "\nTestnet payment succeeded. Verify the transaction at https://sepolia.basescan.org/address/" +
      account.address
  );
} else {
  console.error(
    "\nFailed — no payment accepted. Check the wallet's testnet USDC/ETH balance, and that " +
      "PAY_TO is configured on the Worker."
  );
  process.exit(1);
}
```

- [ ] **Step 2: Configure secrets and deploy to testnet**

Run (from `products/p4-email-verification/`):
```bash
npx wrangler secret put PAY_TO
# paste your Base wallet address (public, receives payments)

npx wrangler secret put X402_NETWORK
# type: testnet
# (anything other than the literal string "mainnet" keeps getNetwork() on Base Sepolia)

npx wrangler deploy
```

- [ ] **Step 3: Fund a disposable testnet wallet and run the payment test**

Follow the prerequisites in `test-payment.mjs`'s header comment (Base Sepolia faucets for ETH and
USDC), then run:
```bash
TESTNET_PRIVATE_KEY=0x... node test-payment.mjs
```
Expected: `Status: 200` and a JSON body with `valid_syntax: true`. Note the printed wallet address
and the deployed Worker's URL for the proof file.

- [ ] **Step 4: Verify the on-chain settlement independently**

Using the wallet address printed by `test-payment.mjs`, check
`https://sepolia.basescan.org/address/<wallet>` for the outgoing USDC transfer, and confirm the
transferred amount is 0.002 USDC to the `PAY_TO` address configured in Step 2. Record the
transaction hash.

- [ ] **Step 5: Write the proof file**

Create `.claude/context/testnet-verified-p4-email-verification.md`, following the structure of
`.claude/context/testnet-verified-p2-domain-parser.md`: date, network (`eip155:84532`), facilitator
URL used, payer wallet, `PAY_TO`, endpoint + request body, HTTP status, settled amount, the
`wrangler tail` log line, the transaction hash + BaseScan link, and an independent balance-diff or
`Transfer` event check if you want the same double-verification rigor as p2/p3's proofs (not
strictly required by `compliance-gate.py`, which only checks the file's existence, but consistent
with the fleet's standard of evidence).

- [ ] **Step 6: Commit**

```bash
git add products/p4-email-verification/test-payment.mjs .claude/context/testnet-verified-p4-email-verification.md
git commit -m "test(p4): testnet payment round-trip proof

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 7: Mainnet switch + deploy + post-deployment validation + ROADMAP update

**Files:**
- Modify: `products/p4-email-verification/wrangler.jsonc`
- Modify: `ROADMAP.md` (Phase 1.5 table + Phase 1.7 checklist, following the p1/p2/p3 pattern)

**Interfaces:**
- Consumes: `.claude/context/testnet-verified-p4-email-verification.md` from Task 6 (required by
  `compliance-gate.py` for this task's `wrangler.jsonc` edit to be allowed)

- [ ] **Step 1: Add the mainnet `vars` block to `wrangler.jsonc`**

Add to `products/p4-email-verification/wrangler.jsonc` (after `observability`):
```jsonc
  ,
  // Base mainnet — testnet round-trip validated end-to-end (payment
  // accepted, on-chain settlement confirmed) before this switch. See
  // .claude/context/testnet-verified-p4-email-verification.md.
  "vars": {
    "X402_NETWORK": "mainnet"
  }
```
`compliance-gate.py` will block this write unless
`.claude/context/testnet-verified-p4-email-verification.md` exists (Task 6, Step 5) — if it blocks,
that means Task 6 wasn't completed first; don't bypass the hook, go back and finish Task 6.

- [ ] **Step 2: Remove the testnet secret override and set the mainnet facilitator**

```bash
npx wrangler secret put X402_FACILITATOR_URL
# paste: https://facilitator.payai.network
# (the fleet's confirmed-working mainnet facilitator as of 2026-09-09 —
# see EXECUTIVE_SUMMARY.md "Remédiations closes le 09/09")
```
The `X402_NETWORK` secret set in Task 6 is now shadowed by the committed `vars` entry from Step 1
(Wrangler vars still apply even with a same-named secret present, but to avoid the ambiguity,
delete the secret): `npx wrangler secret delete X402_NETWORK`.

- [ ] **Step 3: Deploy**

```bash
npx wrangler deploy
```

- [ ] **Step 4: Post-deployment validation checklist** (mirrors ROADMAP.md Phase 1.7)

```bash
curl -i https://email-verification.nordman-tehau.workers.dev/
curl -i https://email-verification.nordman-tehau.workers.dev/verify
curl https://email-verification.nordman-tehau.workers.dev/agent.json
curl https://email-verification.nordman-tehau.workers.dev/llms.txt
curl https://email-verification.nordman-tehau.workers.dev/.well-known/x402
```
Confirm: health check 200, `/verify` GET is not matched by the POST-only route (Hono returns 404,
not a payment challenge — probing the wrong verb must never leak paywall behavior), `agent.json`
has `network: "eip155:8453"`, `llms.txt` says "Base mainnet".

Run `npx wrangler tail` in a separate terminal and issue one real POST to `/verify` without a
payment credential — confirm a `payment_challenge` log line appears, no CPU/subrequest/1027 errors.

Do **not** run `test-payment.mjs` against production with a funded mainnet wallet as part of this
checklist — that would spend real USDC. The Fondateur decides separately whether/when to make a
real mainnet test payment (same pattern as p1/p2/p3's initial mainnet verification).

- [ ] **Step 5: Update `ROADMAP.md`**

Add a row to the Phase 1.5 "Statut réel" table (same table p2/p3 are listed in) documenting
`products/p4-email-verification/` — endpoint `POST /verify`, price `$0.002`, status "Déployé, Base
mainnet", and a one-line pointer to
`.claude/context/testnet-verified-p4-email-verification.md`.

- [ ] **Step 6: Commit**

```bash
git add products/p4-email-verification/wrangler.jsonc ROADMAP.md
git commit -m "feat(p4): switch to Base mainnet, deploy, update ROADMAP

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

**Note:** don't push any of this plan's commits without asking first — same pattern as the rest of
this session (each `git push` so far has been a separate, explicit confirmation).
