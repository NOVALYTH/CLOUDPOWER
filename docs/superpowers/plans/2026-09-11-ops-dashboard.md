# Ops Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix a real blind spot in p1/p2/p3's payment telemetry (a "success" log written before settlement is confirmed), then build a new lean `ops-dashboard` Worker that consolidates all 3 products' payment funnels and cross-checks them against real on-chain USDC transfers to the shared `payTo` wallet.

**Architecture:** No new write-side infrastructure on p1/p2/p3 beyond extending an existing helper's field list and moving one log call to fire from the correct hook. `ops-dashboard` is a new, independent, unpaywalled Worker: it reads p1/p2/p3's existing Analytics Engine datasets over the account-scoped SQL HTTP API (no duplication), maintains a small D1 table of real on-chain settlements found by a Cron Trigger, and serves one consolidated dashboard. Cache API absorbs repeated dashboard refreshes so the Analytics Engine SQL daily quota isn't burned by a human clicking refresh.

**Tech Stack:** Hono (matches the rest of the portfolio), Workers Analytics Engine (read via SQL HTTP API, already in use), D1 (new, `ops-dashboard` only), Workers KV (new, `ops-dashboard` only, one low-frequency key), Cache API (new use), Cron Triggers (new use, 1 of 5 free account slots — 1 already used by p2, 3 remain free after this).

**Spec:** `docs/superpowers/specs/2026-09-11-ops-dashboard-design.md`

## Global Constraints

- Free Tier, $0/month, non-négociable — every new binding below is Free Tier and its real (researched, not assumed) limits are respected.
- Workers Analytics Engine (Free): 100,000 writes/day, 10,000 SQL queries/day, 90-day retention, max 20 blobs / 20 doubles / 1 index per `writeDataPoint()` call, blobs ≤16KB total per call. Read is via `https://api.cloudflare.com/client/v4/accounts/{account_id}/analytics_engine/sql` with an `Account Analytics: Read`-scoped API token — account-scoped, not tied to a specific Worker.
- D1 (Free): 100,000 rows written/day, 5,000,000 rows read/day, 5GB storage cap, 500MB max single DB size, 10 databases/account — **actively enforced since 2026-09-01**, do not assume unlimited.
- Workers KV (Free): 1,000 writes/day/namespace, same-key writes additionally capped at 1/second, eventual consistency up to 60s cross-colo — fine for one low-frequency cursor key.
- Cache API (`caches.default`, Free): no write-count limit, but edge-local only (not globally consistent), TTL is `Cache-Control`-header-driven only, no separate explicit-TTL parameter, 50 Cache API calls/request on Free.
- Cron Triggers (Free): 5 per account total. `products/p2-domain-parser/wrangler.jsonc` already uses 1 (`"0 3 * * *"`). This plan adds exactly 1 more (3 remain free afterward).
- Cloudflare account ID (already used in p1/p2/p3's `/stats` routes): `6e8035aa4fa06c71c4a168ab4ef365d2`.
- Base mainnet USDC contract (verified via BaseScan, 2026-09-11): `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`.
- Shared `payTo` wallet (all 3 products): `0x762cf9834691286218D873eA04B898E26F0963c5`.
- Known Fondateur test wallet (excluded from "real payment" alerts, not from the ledger): `0x2A9b74160288B4d1515d244dC0F5143069cFF6FB`.
- Base mainnet public RPC, no API key required (verified via docs.base.org, 2026-09-11): `https://mainnet.base.org`.
- ERC-20 `Transfer(address,address,uint256)` event topic0 (standard, not project-specific): `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef`.
- p1's payment dataset: `markdown_x402_payments`. p2's: `domain_parser_payments`. p3's: `domain_intelligence_requests` (shared with non-payment events — always filter `blob1 LIKE 'payment%'`, exactly as p3's own existing `/stats` route already does).
- p4 (email-verification) is explicitly OUT of scope for this plan (Fondateur decision, 2026-09-11) — not deployed yet, will be added to `ops-dashboard` in a later, separate change once it is.
- No push notifications (email/Telegram/Discord) — Fondateur explicitly wants a visual dashboard, not an alert channel.
- No new shared `payments`/`pricing` abstraction — this plan is pure observability, does not touch payment processing on any product.
- `ops-dashboard` is not a paid/discoverable product — no `agent.json`/`llms.txt`, no x402 paywall. It reuses the existing `STATS_SECRET` value (same one already used by p1/p2/p3's dashboards) as its own access gate — do not generate a new one.
- Never hardcode a secret value in `wrangler.jsonc` or source — `STATS_SECRET` and `CF_ANALYTICS_TOKEN` are configured via `wrangler secret put`, by the Fondateur, same as on the other 3 products.

---

### Task 1: Fix the premature "success" log on p1 (markdown-x402)

**Files:**
- Modify: `products/p1-markdown-x402/src/index.ts`

**Interfaces:**
- No new exports. Purely internal event-naming and field changes to the existing `logPaymentEvent` helper and `ensurePaymentHooks`/handler call sites.

- [ ] **Step 1: Extend `logPaymentEvent`'s Analytics Engine blob fields**

In `products/p1-markdown-x402/src/index.ts`, find:

```ts
function logPaymentEvent(env: Env, event: string, fields: Record<string, unknown> = {}) {
  console.log(JSON.stringify({ ts: Date.now(), event, ...fields }));
  env.PAYMENT_ANALYTICS?.writeDataPoint({
    blobs: [event, String(fields.reason ?? ""), String(fields.path ?? fields.endpoint ?? "")],
    doubles: [typeof fields.amount === "number" ? fields.amount : 0],
    indexes: [event],
  });
}
```

Replace with:

```ts
function logPaymentEvent(env: Env, event: string, fields: Record<string, unknown> = {}) {
  console.log(JSON.stringify({ ts: Date.now(), event, ...fields }));
  env.PAYMENT_ANALYTICS?.writeDataPoint({
    blobs: [
      event,
      String(fields.reason ?? ""),
      String(fields.path ?? fields.endpoint ?? ""),
      String(fields.tx ?? ""),
      String(fields.payer ?? ""),
      String(fields.resource ?? ""),
    ],
    doubles: [typeof fields.amount === "number" ? fields.amount : 0],
    indexes: [event],
  });
}
```

- [ ] **Step 2: Enrich the `onAfterSettle` hook with settlement proof fields**

Find:

```ts
    .onAfterSettle(async ({ result }) => {
      logPaymentEvent(env, "payment_settled", { tx: result.transaction, network: result.network });
    })
```

Replace with:

```ts
    .onAfterSettle(async ({ result, paymentPayload, requirements }) => {
      logPaymentEvent(env, "payment_settled", {
        tx: result.transaction,
        network: result.network,
        payer: result.payer,
        resource: paymentPayload.resource?.url,
        amount: Number(requirements.amount),
      });
    })
```

- [ ] **Step 3: Rename the premature success log to reflect what it actually proves**

Find (inside the `POST /convert` handler, after a successful conversion):

```ts
    logPaymentEvent(c.env, "payment_success", {
      endpoint: "/convert",
      source_type: "file",
      status: 200,
      paid: true,
      amount: PRICE_USD_NUMBER,
    });
```

Replace with:

```ts
    logPaymentEvent(c.env, "payment_handler_completed", {
      endpoint: "/convert",
      source_type: "file",
      status: 200,
      paid: true,
      amount: PRICE_USD_NUMBER,
    });
```

There is a second, near-identical call a few lines further down for the URL-fetch branch (`source_type: "url"` instead of `"file"`) — apply the same rename (`"payment_success"` → `"payment_handler_completed"`) there too. Do not change anything else in either call.

- [ ] **Step 4: Update the dashboard's event list to match the new name**

Find:

```ts
const EVENT_ORDER = ["payment_challenge","payment_attempt_rejected","payment_verify_rejected","payment_verify_error","payment_settle_failed","payment_settled","payment_success"];
```

Replace with:

```ts
const EVENT_ORDER = ["payment_challenge","payment_attempt_rejected","payment_verify_rejected","payment_verify_error","payment_settle_failed","payment_settled","payment_handler_completed"];
```

- [ ] **Step 5: Typecheck**

Run: `cd products/p1-markdown-x402 && npx tsc --noEmit`
Expected: no errors. `paymentPayload`/`requirements` are already part of the `SettleResultContext` type `@x402/core` exposes to `onAfterSettle` — no new imports needed.

- [ ] **Step 6: Commit**

```bash
git add products/p1-markdown-x402/src/index.ts
git commit -m "fix(p1): stop logging payment success before settlement is confirmed"
```

---

### Task 2: Fix the premature "success" log on p2 (domain-parser)

**Files:**
- Modify: `products/p2-domain-parser/src/index.ts`

**Interfaces:** Same as Task 1, applied to p2's copy of the same pattern (verified structurally identical).

- [ ] **Step 1: Extend `logPaymentEvent`'s Analytics Engine blob fields**

Find:

```ts
function logPaymentEvent(env: Env, event: string, fields: Record<string, unknown> = {}) {
  console.log(JSON.stringify({ ts: Date.now(), event, ...fields }));
  env.PAYMENT_ANALYTICS?.writeDataPoint({
    blobs: [event, String(fields.reason ?? ""), String(fields.path ?? fields.endpoint ?? "")],
    doubles: [typeof fields.amount === "number" ? fields.amount : 0],
    indexes: [event],
  });
}
```

Replace with:

```ts
function logPaymentEvent(env: Env, event: string, fields: Record<string, unknown> = {}) {
  console.log(JSON.stringify({ ts: Date.now(), event, ...fields }));
  env.PAYMENT_ANALYTICS?.writeDataPoint({
    blobs: [
      event,
      String(fields.reason ?? ""),
      String(fields.path ?? fields.endpoint ?? ""),
      String(fields.tx ?? ""),
      String(fields.payer ?? ""),
      String(fields.resource ?? ""),
    ],
    doubles: [typeof fields.amount === "number" ? fields.amount : 0],
    indexes: [event],
  });
}
```

- [ ] **Step 2: Enrich the `onAfterSettle` hook**

Find:

```ts
    .onAfterSettle(async ({ result }) => {
      logPaymentEvent(env, "payment_settled", { tx: result.transaction, network: result.network });
    })
```

Replace with:

```ts
    .onAfterSettle(async ({ result, paymentPayload, requirements }) => {
      logPaymentEvent(env, "payment_settled", {
        tx: result.transaction,
        network: result.network,
        payer: result.payer,
        resource: paymentPayload.resource?.url,
        amount: Number(requirements.amount),
      });
    })
```

- [ ] **Step 3: Rename the premature success log**

Find:

```ts
    logPaymentEvent(c.env, "payment_success", {
      endpoint: "/v1/domain/parse",
      status: 200,
      paid: true,
      amount: PRICE_USD_NUMBER,
    });
```

Replace with:

```ts
    logPaymentEvent(c.env, "payment_handler_completed", {
      endpoint: "/v1/domain/parse",
      status: 200,
      paid: true,
      amount: PRICE_USD_NUMBER,
    });
```

- [ ] **Step 4: Update the dashboard's event list**

Find:

```ts
const EVENT_ORDER = ["payment_challenge","payment_attempt_rejected","payment_verify_rejected","payment_verify_error","payment_settle_failed","payment_settled","payment_success"];
```

Replace with:

```ts
const EVENT_ORDER = ["payment_challenge","payment_attempt_rejected","payment_verify_rejected","payment_verify_error","payment_settle_failed","payment_settled","payment_handler_completed"];
```

- [ ] **Step 5: Typecheck**

Run: `cd products/p2-domain-parser && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add products/p2-domain-parser/src/index.ts
git commit -m "fix(p2): stop logging payment success before settlement is confirmed"
```

---

### Task 3: Fix the premature "success" log on p3 (domain-intelligence)

**Files:**
- Modify: `products/p3-domain-intelligence/src/http/router.ts`

**Interfaces:** Same fix, adapted to p3's closure-based `logPaymentEvent` (no `env` parameter — captured from the enclosing `createApp(env)` scope) and its shared, prefix-filtered dataset. Note this file uses **tabs** for indentation — match the existing style exactly, do not convert to spaces.

- [ ] **Step 1: Extend `logPaymentEvent`'s Analytics Engine blob fields**

Find (inside `createApp`):

```ts
		function logPaymentEvent(event: string, fields: Record<string, unknown> = {}) {
			console.log(JSON.stringify({ ts: Date.now(), event, ...fields }));
			env.ANALYTICS?.writeDataPoint({
				blobs: [event, String(fields.reason ?? ""), String(fields.path ?? fields.route ?? "")],
				doubles: [typeof fields.price_usd === "number" ? fields.price_usd : 0],
				indexes: [event],
			});
		}
```

Replace with:

```ts
		function logPaymentEvent(event: string, fields: Record<string, unknown> = {}) {
			console.log(JSON.stringify({ ts: Date.now(), event, ...fields }));
			env.ANALYTICS?.writeDataPoint({
				blobs: [
					event,
					String(fields.reason ?? ""),
					String(fields.path ?? fields.route ?? ""),
					String(fields.tx ?? ""),
					String(fields.payer ?? ""),
					String(fields.resource ?? ""),
				],
				doubles: [typeof fields.price_usd === "number" ? fields.price_usd : 0],
				indexes: [event],
			});
		}
```

- [ ] **Step 2: Enrich the `onAfterSettle` hook**

Find:

```ts
			.onAfterSettle(async ({ result }) => {
				logPaymentEvent("payment_settled", { tx: result.transaction, network: result.network });
			})
```

Replace with:

```ts
			.onAfterSettle(async ({ result, paymentPayload, requirements }) => {
				logPaymentEvent("payment_settled", {
					tx: result.transaction,
					network: result.network,
					payer: result.payer,
					resource: paymentPayload.resource?.url,
					price_usd: Number(requirements.amount),
				});
			})
```

(Note: p3's `logPaymentEvent` reads its numeric field from `fields.price_usd`, not `fields.amount` — matches its existing `doubles` mapping, kept as-is.)

- [ ] **Step 3: Rename the premature success log**

Find:

```ts
		const logPaid = (route: keyof typeof PRICE_USD, domain: string) =>
			logPaymentEvent("payment_success", { route: `/${route}`, domain, status: 200, paid: true, price_usd: PRICE_USD[route] });
```

Replace with:

```ts
		const logPaid = (route: keyof typeof PRICE_USD, domain: string) =>
			logPaymentEvent("payment_handler_completed", { route: `/${route}`, domain, status: 200, paid: true, price_usd: PRICE_USD[route] });
```

- [ ] **Step 4: Update the dashboard's event list**

Find:

```ts
const EVENT_ORDER = ["payment_challenge","payment_attempt_rejected","payment_verify_rejected","payment_verify_error","payment_settle_failed","payment_settled","payment_success"];
```

Replace with:

```ts
const EVENT_ORDER = ["payment_challenge","payment_attempt_rejected","payment_verify_rejected","payment_verify_error","payment_settle_failed","payment_settled","payment_handler_completed"];
```

- [ ] **Step 5: Typecheck and test**

Run: `cd products/p3-domain-intelligence && npx tsc --noEmit && npx vitest run`
Expected: no type errors; existing test suite still passes unchanged (this task does not touch any tested pure function, only hook wiring and log strings).

- [ ] **Step 6: Commit**

```bash
git add products/p3-domain-intelligence/src/http/router.ts
git commit -m "fix(p3): stop logging payment success before settlement is confirmed"
```

---

### Task 4: Scaffold `products/ops-dashboard`

**Files:**
- Create: `products/ops-dashboard/package.json`
- Create: `products/ops-dashboard/tsconfig.json`
- Create: `products/ops-dashboard/wrangler.jsonc`
- Create: `products/ops-dashboard/vitest.config.ts`
- Create: `products/ops-dashboard/src/env.ts`

**Interfaces:**
- Produces: `Env` interface (in `src/env.ts`) that every later task imports: `{ CF_ANALYTICS_TOKEN: string; STATS_SECRET: string; PAY_TO: string; ONCHAIN_DB: D1Database; WATCH_STATE: KVNamespace }`.

- [ ] **Step 1: package.json**

Create `products/ops-dashboard/package.json`:

```json
{
  "name": "ops-dashboard",
  "version": "0.0.1",
  "private": true,
  "description": "Internal, unpaywalled dashboard consolidating p1/p2/p3 payment funnels and on-chain settlement proof. Not a sold product.",
  "type": "module",
  "scripts": {
    "dev": "wrangler dev",
    "deploy": "wrangler deploy",
    "tail": "wrangler tail",
    "test": "vitest run",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "hono": "^4.13.7"
  },
  "devDependencies": {
    "@cloudflare/vitest-plugin": "^1.1.5",
    "@cloudflare/workers-types": "^5.20260907.1",
    "typescript": "^5.7.0",
    "vitest": "^4.1.0",
    "wrangler": "^4.129.1"
  }
}
```

- [ ] **Step 2: tsconfig.json**

Create `products/ops-dashboard/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022"],
    "module": "ES2022",
    "moduleResolution": "Bundler",
    "types": ["@cloudflare/workers-types", "@cloudflare/vitest-plugin/types"],
    "strict": true,
    "skipLibCheck": true,
    "noEmit": true,
    "resolveJsonModule": true
  },
  "include": ["src", "tests"]
}
```

- [ ] **Step 3: wrangler.jsonc**

Create `products/ops-dashboard/wrangler.jsonc`:

```jsonc
{
  "name": "ops-dashboard",
  "main": "src/index.ts",
  "compatibility_date": "2026-09-11",
  "compatibility_flags": ["nodejs_compat"],
  // Pas un produit vendu : outil interne, sans paywall x402, gate par
  // STATS_SECRET (meme valeur que p1/p2/p3, reutilisee — pas de nouveau
  // secret). Voir docs/superpowers/specs/2026-09-11-ops-dashboard-design.md.
  "triggers": {
    "crons": ["*/30 * * * *"]
  },
  "d1_databases": [
    {
      "binding": "ONCHAIN_DB",
      "database_name": "ops-dashboard-onchain",
      "database_id": "REPLACE_AFTER_D1_CREATE"
    }
  ],
  "kv_namespaces": [
    {
      "binding": "WATCH_STATE",
      "id": "REPLACE_AFTER_KV_CREATE"
    }
  ],
  "vars": {
    // Adresse wallet publique (pas un secret — deja publiee dans
    // agent.json/llms.txt des 3 produits).
    "PAY_TO": "0x762cf9834691286218D873eA04B898E26F0963c5"
  },
  "observability": {
    "logs": {
      "enabled": true,
      "head_sampling_rate": 1,
      "invocation_logs": true,
      "persist": true
    }
  }
  // STATS_SECRET et CF_ANALYTICS_TOKEN sont des secrets (`wrangler secret
  // put`), jamais en clair ici — memes valeurs que p1/p2/p3.
}
```

The two `REPLACE_AFTER_*_CREATE` placeholders are intentional and get filled in Task 5 (they cannot be known before the D1 database and KV namespace exist) — this is the one place in this plan where a literal placeholder is correct, not a defect.

- [ ] **Step 4: vitest.config.ts**

Create `products/ops-dashboard/vitest.config.ts`:

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

- [ ] **Step 5: Env interface**

Create `products/ops-dashboard/src/env.ts`:

```ts
export interface Env {
  CF_ANALYTICS_TOKEN: string;
  STATS_SECRET: string;
  PAY_TO: string;
  ONCHAIN_DB: D1Database;
  WATCH_STATE: KVNamespace;
}
```

- [ ] **Step 6: npm install**

Run: `cd products/ops-dashboard && npm install`
Expected: installs cleanly, `package-lock.json` created.

- [ ] **Step 7: Commit**

```bash
git add products/ops-dashboard/package.json products/ops-dashboard/package-lock.json products/ops-dashboard/tsconfig.json products/ops-dashboard/wrangler.jsonc products/ops-dashboard/vitest.config.ts products/ops-dashboard/src/env.ts
git commit -m "feat(ops-dashboard): scaffold new internal Worker"
```

---

### Task 5: Create the D1 database, KV namespace, and Analytics Engine aggregation module

**Files:**
- Create: `products/ops-dashboard/migrations/0001_onchain_settlements.sql`
- Create: `products/ops-dashboard/src/analytics.ts`
- Create: `products/ops-dashboard/tests/analytics.test.ts`
- Modify: `products/ops-dashboard/wrangler.jsonc` (fill in the two `database_id`/`id` placeholders from Task 4)

**Interfaces:**
- Consumes: `Env` from `src/env.ts` (Task 4).
- Produces: `export interface FunnelTotals { event: string; count: number; amount_usd: number }`, `export interface FunnelDaily { day: string; event: string; count: number }`, `export interface ProductFunnel { product: string; totals: FunnelTotals[]; daily: FunnelDaily[]; error?: string }`, `export async function fetchAllFunnels(env: Env, days: number): Promise<ProductFunnel[]>` — Task 7 imports and calls this directly.

- [ ] **Step 1: Create the D1 database and KV namespace via the Cloudflare account**

Run: `cd products/ops-dashboard && npx wrangler d1 create ops-dashboard-onchain`
Expected: prints a `database_id` (UUID). Copy it.

Run: `npx wrangler kv namespace create WATCH_STATE`
Expected: prints an `id` (hex string). Copy it.

Edit `products/ops-dashboard/wrangler.jsonc`, replacing `"REPLACE_AFTER_D1_CREATE"` with the printed `database_id`, and `"REPLACE_AFTER_KV_CREATE"` with the printed `id`.

- [ ] **Step 2: D1 schema migration**

Create `products/ops-dashboard/migrations/0001_onchain_settlements.sql`:

```sql
CREATE TABLE onchain_settlements (
  tx_hash TEXT PRIMARY KEY,
  from_address TEXT NOT NULL,
  amount_usdc REAL NOT NULL,
  block_number INTEGER NOT NULL,
  detected_at TEXT NOT NULL,
  is_known_test_wallet INTEGER NOT NULL DEFAULT 0
);
```

Run: `npx wrangler d1 migrations apply ops-dashboard-onchain --remote`
Expected: applies cleanly, reports 1 migration applied.

- [ ] **Step 3: Write the failing test for the aggregation module**

Create `products/ops-dashboard/tests/analytics.test.ts`:

```ts
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { fetchAllFunnels } from "../src/analytics";
import type { Env } from "../src/env";

function makeEnv(): Env {
  return {
    CF_ANALYTICS_TOKEN: "test-token",
    STATS_SECRET: "test-secret",
    PAY_TO: "0x762cf9834691286218D873eA04B898E26F0963c5",
    ONCHAIN_DB: {} as D1Database,
    WATCH_STATE: {} as KVNamespace,
  };
}

describe("fetchAllFunnels", () => {
  const originalFetch = globalThis.fetch;

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("queries all 3 product datasets and returns one ProductFunnel per product", async () => {
    const calls: string[] = [];
    globalThis.fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const body = String(init?.body ?? "");
      calls.push(body);
      const isTotals = body.includes("GROUP BY blob1 ORDER BY count DESC");
      const data = isTotals
        ? [{ event: "payment_settled", count: 3, amount_usd: 0.015 }]
        : [{ day: "2026-09-11", event: "payment_settled", count: 3 }];
      return new Response(JSON.stringify({ data }), { status: 200 });
    }) as typeof fetch;

    const result = await fetchAllFunnels(makeEnv(), 2);

    expect(result).toHaveLength(3);
    expect(result.map((r) => r.product)).toEqual(["markdown-x402", "domain-parser", "domain-intelligence"]);
    expect(result[0].totals[0].event).toBe("payment_settled");
    expect(result[0].daily[0].day).toBe("2026-09-11");
    // p3 uses a shared dataset — its queries must filter to payment_* rows.
    const p3Calls = calls.filter((c) => c.includes("domain_intelligence_requests"));
    expect(p3Calls.length).toBeGreaterThan(0);
    for (const call of p3Calls) {
      expect(call).toContain("blob1 LIKE 'payment%'");
    }
  });

  it("returns a per-product error instead of throwing when one dataset's query fails", async () => {
    globalThis.fetch = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("markdown_x402_payments") === false) {
        return new Response(JSON.stringify({ data: [] }), { status: 200 });
      }
      return new Response("Internal Server Error", { status: 500 });
    }) as typeof fetch;

    const result = await fetchAllFunnels(makeEnv(), 2);

    const markdown = result.find((r) => r.product === "markdown-x402");
    expect(markdown?.error).toBeDefined();
    expect(markdown?.totals).toEqual([]);
    const others = result.filter((r) => r.product !== "markdown-x402");
    for (const other of others) {
      expect(other.error).toBeUndefined();
    }
  });
});
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `cd products/ops-dashboard && npm test`
Expected: FAIL — `src/analytics.ts` does not exist yet.

- [ ] **Step 5: Implement the aggregation module**

Create `products/ops-dashboard/src/analytics.ts`:

```ts
import type { Env } from "./env";

const CF_ACCOUNT_ID = "6e8035aa4fa06c71c4a168ab4ef365d2";

export interface FunnelTotals {
  event: string;
  count: number;
  amount_usd: number;
}

export interface FunnelDaily {
  day: string;
  event: string;
  count: number;
}

export interface ProductFunnel {
  product: string;
  totals: FunnelTotals[];
  daily: FunnelDaily[];
  error?: string;
}

interface ProductDataset {
  product: string;
  dataset: string;
  // p3's dataset is shared with non-payment events; only it needs the filter.
  paymentPrefixFilter: boolean;
}

const PRODUCTS: ProductDataset[] = [
  { product: "markdown-x402", dataset: "markdown_x402_payments", paymentPrefixFilter: false },
  { product: "domain-parser", dataset: "domain_parser_payments", paymentPrefixFilter: false },
  { product: "domain-intelligence", dataset: "domain_intelligence_requests", paymentPrefixFilter: true },
];

async function queryAnalyticsEngine(env: Env, sql: string): Promise<unknown[]> {
  const res = await fetch(
    `https://api.cloudflare.com/client/v4/accounts/${CF_ACCOUNT_ID}/analytics_engine/sql`,
    {
      method: "POST",
      headers: { Authorization: `Bearer ${env.CF_ANALYTICS_TOKEN}`, "Content-Type": "text/plain" },
      body: sql,
    }
  );
  if (!res.ok) throw new Error(`Analytics Engine query failed (${res.status}): ${await res.text()}`);
  const json = await res.json<{ data?: unknown[] }>();
  return json.data ?? [];
}

async function fetchOneFunnel(env: Env, p: ProductDataset, days: number): Promise<ProductFunnel> {
  const filter = p.paymentPrefixFilter ? ` AND blob1 LIKE 'payment%'` : "";
  try {
    const [totals, daily] = await Promise.all([
      queryAnalyticsEngine(
        env,
        `SELECT blob1 AS event, count() AS count, sum(double1) AS amount_usd FROM ${p.dataset} WHERE timestamp > NOW() - INTERVAL '${days}' DAY${filter} GROUP BY blob1 ORDER BY count DESC`
      ),
      queryAnalyticsEngine(
        env,
        `SELECT toDate(timestamp) AS day, blob1 AS event, count() AS count FROM ${p.dataset} WHERE timestamp > NOW() - INTERVAL '${days}' DAY${filter} GROUP BY day, blob1 ORDER BY day ASC`
      ),
    ]);
    return {
      product: p.product,
      totals: totals as FunnelTotals[],
      daily: daily as FunnelDaily[],
    };
  } catch (err) {
    return {
      product: p.product,
      totals: [],
      daily: [],
      error: err instanceof Error ? err.message : String(err),
    };
  }
}

export async function fetchAllFunnels(env: Env, days: number): Promise<ProductFunnel[]> {
  return Promise.all(PRODUCTS.map((p) => fetchOneFunnel(env, p, days)));
}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd products/ops-dashboard && npm test`
Expected: PASS, both tests green.

- [ ] **Step 7: Typecheck**

Run: `cd products/ops-dashboard && npm run typecheck`
Expected: no errors.

- [ ] **Step 8: Commit**

```bash
git add products/ops-dashboard/migrations products/ops-dashboard/src/analytics.ts products/ops-dashboard/tests/analytics.test.ts products/ops-dashboard/wrangler.jsonc
git commit -m "feat(ops-dashboard): D1/KV resources + cross-product Analytics Engine aggregation"
```

---

### Task 6: On-chain settlement scanner

**Files:**
- Create: `products/ops-dashboard/src/onchain.ts`
- Create: `products/ops-dashboard/tests/onchain.test.ts`

**Interfaces:**
- Consumes: `Env` from `src/env.ts` (Task 4).
- Produces: `export interface OnchainTransfer { txHash: string; from: string; amountUsdc: number; blockNumber: number }`, `export async function scanForNewSettlements(env: Env, fetchImpl: typeof fetch = fetch): Promise<OnchainTransfer[]>` (the `fetchImpl` param defaults to the global `fetch` — production callers, including Task 7's cron handler, omit it entirely; tests pass a mock explicitly).

- [ ] **Step 1: Write the failing tests**

Create `products/ops-dashboard/tests/onchain.test.ts`:

```ts
import { describe, expect, it, vi } from "vitest";
import { scanForNewSettlements } from "../src/onchain";
import type { Env } from "../src/env";

function makeEnv(overrides: Partial<{ get: (key: string) => Promise<string | null>; put: (key: string, value: string) => Promise<void>; batch: (stmts: unknown[]) => Promise<unknown>; }> = {}): Env {
  const kvStore = new Map<string, string>();
  const d1Rows: unknown[] = [];
  return {
    CF_ANALYTICS_TOKEN: "test-token",
    STATS_SECRET: "test-secret",
    PAY_TO: "0x762cf9834691286218D873eA04B898E26F0963c5",
    WATCH_STATE: {
      get: overrides.get ?? (async (key: string) => kvStore.get(key) ?? null),
      put: overrides.put ?? (async (key: string, value: string) => { kvStore.set(key, value); }),
    } as unknown as KVNamespace,
    ONCHAIN_DB: {
      prepare: (sql: string) => ({
        bind: (...args: unknown[]) => ({
          run: async () => { d1Rows.push({ sql, args }); return { success: true }; },
        }),
      }),
    } as unknown as D1Database,
  };
}

// keccak256("Transfer(address,address,uint256)")
const TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef";
const PAY_TO_TOPIC = "0x000000000000000000000000762cf9834691286218d873ea04b898e26f0963c5";
const SENDER = "0x2a9b74160288b4d1515d244dc0f5143069cff6fb";
const SENDER_TOPIC = `0x000000000000000000000000${SENDER.slice(2)}`;

function mockRpcFetch(logs: unknown[], latestBlockHex: string) {
  return vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
    const body = JSON.parse(String(init?.body ?? "{}"));
    if (body.method === "eth_blockNumber") {
      return new Response(JSON.stringify({ jsonrpc: "2.0", id: body.id, result: latestBlockHex }));
    }
    if (body.method === "eth_getLogs") {
      return new Response(JSON.stringify({ jsonrpc: "2.0", id: body.id, result: logs }));
    }
    throw new Error(`Unexpected RPC method: ${body.method}`);
  }) as unknown as typeof fetch;
}

describe("scanForNewSettlements", () => {
  it("decodes a real transfer log and returns it", async () => {
    const logs = [
      {
        transactionHash: "0xabc123",
        blockNumber: "0x030c9c46",
        topics: [TRANSFER_TOPIC, SENDER_TOPIC, PAY_TO_TOPIC],
        // 1000 (0.001 USDC at 6 decimals) as 32-byte hex
        data: "0x00000000000000000000000000000000000000000000000000000000000003e8",
      },
    ];
    const env = makeEnv();
    const result = await scanForNewSettlements(env, mockRpcFetch(logs, "0x030c9c50"));

    expect(result).toHaveLength(1);
    expect(result[0].txHash).toBe("0xabc123");
    expect(result[0].from.toLowerCase()).toBe(SENDER);
    expect(result[0].amountUsdc).toBeCloseTo(0.001, 6);
    expect(result[0].blockNumber).toBe(0x030c9c46);
  });

  it("advances the KV cursor past the latest scanned block", async () => {
    let stored: string | undefined;
    const env = makeEnv({
      get: async () => "50000000",
      put: async (_key, value) => { stored = value; },
    });
    await scanForNewSettlements(env, mockRpcFetch([], "0x030c9c50"));

    expect(stored).toBeDefined();
    expect(Number(stored)).toBeGreaterThan(50000000);
  });

  it("returns an empty array and does not throw when the RPC call fails", async () => {
    const env = makeEnv();
    const failingFetch = vi.fn(async () => new Response("Service Unavailable", { status: 503 })) as unknown as typeof fetch;

    await expect(scanForNewSettlements(env, failingFetch)).resolves.toEqual([]);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd products/ops-dashboard && npm test`
Expected: FAIL — `src/onchain.ts` does not exist yet.

- [ ] **Step 3: Implement the on-chain scanner**

Create `products/ops-dashboard/src/onchain.ts`:

```ts
import type { Env } from "./env";

const BASE_RPC_URL = "https://mainnet.base.org";
const USDC_CONTRACT = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
const TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef";
const KNOWN_TEST_WALLET = "0x2a9b74160288b4d1515d244dc0f5143069cff6fb";
const WATCH_CURSOR_KEY = "last_checked_block";
// Base mainnet genesis-adjacent block is far below this; used only as a
// floor the very first time the cursor is empty, to avoid scanning from
// block 0 on first run.
const FIRST_SCAN_FLOOR_BLOCK = 51000000;

export interface OnchainTransfer {
  txHash: string;
  from: string;
  amountUsdc: number;
  blockNumber: number;
}

interface RpcLog {
  transactionHash: string;
  blockNumber: string;
  topics: string[];
  data: string;
}

function addressFromTopic(topic: string): string {
  return `0x${topic.slice(-40)}`;
}

function payToTopic(payTo: string): string {
  return `0x${"0".repeat(24)}${payTo.slice(2).toLowerCase()}`;
}

async function rpcCall<T>(fetchImpl: typeof fetch, method: string, params: unknown[]): Promise<T> {
  const res = await fetchImpl(BASE_RPC_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ jsonrpc: "2.0", id: 1, method, params }),
  });
  if (!res.ok) throw new Error(`RPC call ${method} failed (${res.status})`);
  const json = await res.json<{ result?: T; error?: { message: string } }>();
  if (json.error) throw new Error(`RPC error on ${method}: ${json.error.message}`);
  if (json.result === undefined) throw new Error(`RPC call ${method} returned no result`);
  return json.result;
}

export async function scanForNewSettlements(
  env: Env,
  fetchImpl: typeof fetch = fetch
): Promise<OnchainTransfer[]> {
  try {
    const cursorRaw = await env.WATCH_STATE.get(WATCH_CURSOR_KEY);
    const fromBlock = cursorRaw ? Number(cursorRaw) + 1 : FIRST_SCAN_FLOOR_BLOCK;

    const latestHex = await rpcCall<string>(fetchImpl, "eth_blockNumber", []);
    const latestBlock = parseInt(latestHex, 16);
    if (latestBlock < fromBlock) return [];

    const logs = await rpcCall<RpcLog[]>(fetchImpl, "eth_getLogs", [
      {
        fromBlock: `0x${fromBlock.toString(16)}`,
        toBlock: `0x${latestBlock.toString(16)}`,
        address: USDC_CONTRACT,
        topics: [TRANSFER_TOPIC, null, payToTopic(env.PAY_TO)],
      },
    ]);

    const transfers: OnchainTransfer[] = logs.map((log) => ({
      txHash: log.transactionHash,
      from: addressFromTopic(log.topics[1]),
      amountUsdc: Number(BigInt(log.data)) / 1_000_000,
      blockNumber: parseInt(log.blockNumber, 16),
    }));

    for (const t of transfers) {
      const isTest = t.from.toLowerCase() === KNOWN_TEST_WALLET ? 1 : 0;
      await env.ONCHAIN_DB.prepare(
        `INSERT OR IGNORE INTO onchain_settlements (tx_hash, from_address, amount_usdc, block_number, detected_at, is_known_test_wallet) VALUES (?, ?, ?, ?, ?, ?)`
      )
        .bind(t.txHash, t.from, t.amountUsdc, t.blockNumber, new Date().toISOString(), isTest)
        .run();
    }

    await env.WATCH_STATE.put(WATCH_CURSOR_KEY, String(latestBlock));
    return transfers;
  } catch (err) {
    console.log(JSON.stringify({ ts: Date.now(), event: "onchain_scan_failed", error: err instanceof Error ? err.message : String(err) }));
    return [];
  }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd products/ops-dashboard && npm test`
Expected: PASS, all tests green (analytics.test.ts + onchain.test.ts).

- [ ] **Step 5: Typecheck**

Run: `cd products/ops-dashboard && npm run typecheck`
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add products/ops-dashboard/src/onchain.ts products/ops-dashboard/tests/onchain.test.ts
git commit -m "feat(ops-dashboard): on-chain USDC settlement scanner (Base RPC, D1 ledger)"
```

---

### Task 7: Dashboard route, `/stats` API, Cache API, and Cron wiring

**Files:**
- Create: `products/ops-dashboard/src/index.ts`

**Interfaces:**
- Consumes: `fetchAllFunnels` (Task 5), `scanForNewSettlements`/`OnchainTransfer` (Task 6), `Env` (Task 4).

- [ ] **Step 1: Implement the Worker entry point**

Create `products/ops-dashboard/src/index.ts`:

```ts
import { Hono } from "hono";
import type { Env } from "./env";
import { fetchAllFunnels, type ProductFunnel } from "./analytics";
import { scanForNewSettlements } from "./onchain";

const CACHE_TTL_SECONDS = 60;

function checkStatsKey(c: { req: { query: (k: string) => string | undefined }; env: Env }) {
  const key = c.req.query("key");
  return !!key && key === c.env.STATS_SECRET;
}

interface RecentSettlement {
  tx_hash: string;
  from_address: string;
  amount_usdc: number;
  block_number: number;
  detected_at: string;
  is_known_test_wallet: number;
}

async function loadRecentOnchainSettlements(env: Env, limit = 20): Promise<RecentSettlement[]> {
  const { results } = await env.ONCHAIN_DB.prepare(
    `SELECT tx_hash, from_address, amount_usdc, block_number, detected_at, is_known_test_wallet FROM onchain_settlements ORDER BY block_number DESC LIMIT ?`
  )
    .bind(limit)
    .all<RecentSettlement>();
  return results ?? [];
}

function integrityGaps(funnels: ProductFunnel[]) {
  return funnels.map((f) => {
    const byEvent = Object.fromEntries(f.totals.map((t) => [t.event, t.count]));
    const completed = byEvent["payment_handler_completed"] ?? 0;
    const settled = byEvent["payment_settled"] ?? 0;
    return { product: f.product, handlerCompleted: completed, settled, gap: completed - settled };
  });
}

const app = new Hono<{ Bindings: Env }>();

app.get("/robots.txt", (c) => c.text("User-agent: *\nDisallow: /\n"));

app.get("/", (c) => c.json({ name: "ops-dashboard", status: "ok" }));

app.get("/stats", async (c) => {
  if (!checkStatsKey(c)) return c.json({ ok: false, error: "Unauthorized" }, 401);

  const cache = caches.default;
  const cacheKey = new Request(c.req.url.replace(/[?&]key=[^&]*/, ""), c.req.raw);
  const cached = await cache.match(cacheKey);
  if (cached) return cached;

  const days = Number(c.req.query("days") ?? "14") || 14;
  try {
    const [funnels, recentSettlements] = await Promise.all([
      fetchAllFunnels(c.env, days),
      loadRecentOnchainSettlements(c.env),
    ]);
    const body = {
      ok: true,
      days,
      funnels,
      integrity: integrityGaps(funnels),
      recent_onchain_settlements: recentSettlements,
    };
    const response = new Response(JSON.stringify(body), {
      headers: { "Content-Type": "application/json", "Cache-Control": `private, max-age=${CACHE_TTL_SECONDS}` },
    });
    c.executionCtx.waitUntil(cache.put(cacheKey, response.clone()));
    return response;
  } catch (err) {
    return c.json({ ok: false, error: String(err) }, 502);
  }
});

function dashboardHtml(key: string): string {
  return `<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><title>ops-dashboard — funnel consolidé</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.4/chart.umd.min.js"></script>
<style>
  body { font-family: system-ui, sans-serif; margin: 2rem; background:#0b0e14; color:#e6e6e6; }
  h1 { font-size: 1.25rem; font-weight: 600; }
  h2 { font-size: 1rem; font-weight: 600; margin-top: 2rem; }
  .cards { display:flex; gap:1rem; flex-wrap:wrap; margin: 1rem 0 2rem; }
  .card { background:#151a24; border-radius:8px; padding:1rem 1.5rem; min-width:160px; }
  .card .n { font-size:1.4rem; font-weight:600; }
  .card .l { font-size:0.7rem; color:#9aa4b2; text-transform:uppercase; letter-spacing:.03em; }
  .card.warn { border: 1px solid #e05263; }
  table { border-collapse: collapse; width: 100%; margin-top: 0.5rem; }
  td, th { text-align: left; padding: 0.4rem 0.6rem; border-bottom: 1px solid #2a3242; font-size: 0.85rem; }
  select { background:#151a24; color:#e6e6e6; border:1px solid #2a3242; border-radius:6px; padding:.3rem .5rem; }
  #err { color:#f88; }
</style></head>
<body>
<h1>ops-dashboard — funnel consolidé p1/p2/p3</h1>
<label>Periode : <select id="days">
  <option value="7">7 jours</option>
  <option value="14" selected>14 jours</option>
  <option value="30">30 jours</option>
</select></label>
<div id="err"></div>

<h2>Intégrité paiement (livré sans règlement confirmé)</h2>
<div class="cards" id="integrity"></div>

<h2>Règlements on-chain réels détectés</h2>
<table id="onchain"><thead><tr><th>tx</th><th>de</th><th>montant</th><th>bloc</th><th>type</th></tr></thead><tbody></tbody></table>

<h2>Funnel par produit</h2>
<div id="funnels"></div>

<script>
const KEY = ${JSON.stringify(key)};
async function load() {
  document.getElementById('err').textContent = '';
  const days = document.getElementById('days').value;
  const res = await fetch('/stats?key=' + encodeURIComponent(KEY) + '&days=' + days);
  const data = await res.json();
  if (!data.ok) { document.getElementById('err').textContent = 'Erreur: ' + (data.error || '?'); return; }
  renderIntegrity(data.integrity);
  renderOnchain(data.recent_onchain_settlements);
  renderFunnels(data.funnels);
}
function renderIntegrity(integrity) {
  document.getElementById('integrity').innerHTML = integrity.map(i =>
    '<div class="card' + (i.gap > 0 ? ' warn' : '') + '"><div class="n">' + i.gap + '</div><div class="l">' + i.product + ' — livré non réglé</div></div>'
  ).join('');
}
function renderOnchain(rows) {
  document.querySelector('#onchain tbody').innerHTML = rows.map(r =>
    '<tr><td>' + r.tx_hash.slice(0, 10) + '…</td><td>' + r.from_address.slice(0, 10) + '…</td><td>' + r.amount_usdc + ' USDC</td><td>' + r.block_number + '</td><td>' + (r.is_known_test_wallet ? 'test fondateur' : '<strong>externe</strong>') + '</td></tr>'
  ).join('');
}
function renderFunnels(funnels) {
  document.getElementById('funnels').innerHTML = funnels.map(f => {
    if (f.error) return '<p>' + f.product + ' : erreur — ' + f.error + '</p>';
    const cards = f.totals.map(t => '<div class="card"><div class="n">' + t.count + '</div><div class="l">' + t.event.replace('payment_', '') + '</div></div>').join('');
    return '<h3>' + f.product + '</h3><div class="cards">' + cards + '</div>';
  }).join('');
}
document.getElementById('days').addEventListener('change', load);
load();
</script>
</body></html>`;
}

app.get("/dashboard", async (c) => {
  if (!checkStatsKey(c)) return c.text("Unauthorized", 401);
  return c.html(dashboardHtml(c.req.query("key")!));
});

export default {
  fetch: app.fetch,
  async scheduled(_event: ScheduledEvent, env: Env, ctx: ExecutionContext) {
    ctx.waitUntil(
      scanForNewSettlements(env).then((found) => {
        if (found.length > 0) {
          console.log(JSON.stringify({ ts: Date.now(), event: "onchain_settlements_found", count: found.length }));
        }
      })
    );
  },
};
```

- [ ] **Step 2: Typecheck**

Run: `cd products/ops-dashboard && npm run typecheck`
Expected: no errors.

- [ ] **Step 3: Run the full test suite**

Run: `cd products/ops-dashboard && npm test`
Expected: PASS — Tasks 5-6's tests unaffected by this task (this task doesn't modify `analytics.ts`/`onchain.ts`).

- [ ] **Step 4: Local boot smoke test**

Run: `cd products/ops-dashboard && npx wrangler dev` in the background, then:

`curl -i http://localhost:8787/`

Expected: 200 JSON `{"name":"ops-dashboard","status":"ok"}` — proves the Worker bundles and boots (Hono app + `scheduled` export together) without a runtime error. `/stats` and `/dashboard` cannot be fully exercised locally without real `CF_ANALYTICS_TOKEN`/`STATS_SECRET` secrets and a populated remote D1 — that is Task 8. Stop `wrangler dev` afterward.

- [ ] **Step 5: Commit**

```bash
git add products/ops-dashboard/src/index.ts
git commit -m "feat(ops-dashboard): consolidated dashboard, /stats API, Cache API, cron wiring"
```

---

### Task 8: Secrets, deploy, and documentation (Fondateur-assisted)

**Files:**
- Modify: `ARCHITECTURE.md`
- Modify: `EXECUTIVE_SUMMARY.md`

This task's secret-configuration and deploy steps require the Fondateur directly — consistent with every other product in this portfolio (`wrangler secret put` is always run by a human, never piped through an assistant). Do not attempt to obtain or transmit the actual secret values.

- [ ] **Step 1: Configure secrets (Fondateur runs these)**

```bash
cd products/ops-dashboard
npx wrangler secret put STATS_SECRET
# same value already used by p1/p2/p3's dashboards
npx wrangler secret put CF_ANALYTICS_TOKEN
# same "Account Analytics: Read" token already used by p1/p2/p3
```

- [ ] **Step 2: Deploy**

```bash
npx wrangler deploy
```

No financial/payment risk in this deploy — `ops-dashboard` has no x402 paywall and does not process payments, only reads existing telemetry and public on-chain data.

- [ ] **Step 3: Validate live**

```bash
curl -i https://ops-dashboard.<account-subdomain>.workers.dev/
curl -i "https://ops-dashboard.<account-subdomain>.workers.dev/stats?key=<STATS_SECRET>&days=7"
```

Expected: `/` returns 200; `/stats` returns `ok: true` with 3 entries in `funnels` and (initially) 4 rows in `recent_onchain_settlements`, all `is_known_test_wallet: 1` — matching the known Fondateur test payments. Open `/dashboard?key=<STATS_SECRET>` in a browser and confirm it renders.

- [ ] **Step 4: Update ARCHITECTURE.md**

Append a dated entry to `ARCHITECTURE.md` documenting: the `payment_success`→`payment_handler_completed` rename and why (settlement-timing blind spot found by tracing `@x402/hono`), the new `ops-dashboard` product and its Free Tier resource usage (1 D1 database, 1 KV namespace, 1 Cron Trigger — 3 of 5 account cron slots remain free), and that p4 is excluded until deployed.

- [ ] **Step 5: Update EXECUTIVE_SUMMARY.md**

Update the "Prochaine action prévue" and relevant sections to reflect: `ops-dashboard` live, on-chain settlement cross-check now automatic (30-min cron), and the corrected telemetry semantics on p1/p2/p3.

- [ ] **Step 6: Commit**

```bash
git add ARCHITECTURE.md EXECUTIVE_SUMMARY.md
git commit -m "docs: document ops-dashboard launch and payment telemetry fix"
```
