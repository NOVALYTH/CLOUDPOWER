# p1 HTML Fast-Path (turndown+linkedom) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route HTML sources in `p1-markdown-x402`'s `/convert` through a pure-JS `turndown`+`linkedom` conversion instead of `env.AI.toMarkdown()`, while every other format keeps using Workers AI exactly as today.

**Architecture:** Add one new pure function module (`src/html-to-markdown.ts`) that converts an HTML string to Markdown using `linkedom` (parses HTML into a DOM without a browser) piped into `turndown` (walks that DOM into Markdown). Insert one shared helper (`convertBlobToMarkdown`) in `src/index.ts` that both existing `/convert` branches (file upload, URL fetch) call instead of calling `env.AI.toMarkdown()` directly — the helper decides HTML-fast-path vs. Workers-AI-fallback by MIME type, after the existing size/type gates already in place.

**Tech Stack:** `turndown` (HTML DOM → Markdown, pure JS), `linkedom` (pure-JS HTML parser exposing a DOM, no browser/jsdom needed — Workers-compatible), `vitest` + `@cloudflare/vitest-plugin` (new test infra for this product, matching the pattern already used in p3/p4).

**Spec:** Decision recorded in project memory `project_project_evolving_0911.md` ("État Phase A — p1 Workers AI"), itself derived from `ARCHITECTURE.md` 2026-09-10 portfolio doctrine (monolithe p1/p2 = patron de référence — this module stays inside `products/p1-markdown-x402/src/`, never extracted to `shared/`). No separate spec doc: the design is narrow enough to state fully in this plan's Global Constraints.

## Global Constraints

- Runtime: Cloudflare Workers Free Tier. `nodejs_compat` is already enabled in `wrangler.jsonc` — no new compatibility flags needed.
- `ConvertResponse` shape (`source_type`, `source`, `converted_at`, `title`, `word_count`, `neuron_tokens`, `sections`, `markdown`) must not change.
- HTML fast-path sets `neuron_tokens: null` — no Workers AI Neurons are consumed on that path.
- Every non-HTML MIME type must keep routing through `env.AI.toMarkdown()` with unchanged behavior — this is a strictly additive change, not a replacement.
- The existing `MAX_SOURCE_BYTES` (10 MB) and `supportedMimeTypes` 415 gate in `/convert` stay exactly where they are today, unchanged, and still run before any conversion.
- HTML MIME detection is exactly `text/html` and `application/xhtml+xml` — no broader set without evidence of need.
- New code lives only inside `products/p1-markdown-x402/src/` — portfolio doctrine (`ARCHITECTURE.md` 2026-09-10) forbids a `shared/` extraction before 2+ products need it.
- No secrets, no `wrangler secret put`, no `wrangler deploy` in this plan — it stops at a locally typechecked, tested, committed branch. Deploying this change to the live product is a separate step requiring explicit go-ahead outside this plan.

---

### Task 1: HTML→Markdown conversion module + test infra

**Files:**
- Create: `products/p1-markdown-x402/src/html-to-markdown.ts`
- Create: `products/p1-markdown-x402/tests/html-to-markdown.test.ts`
- Create: `products/p1-markdown-x402/vitest.config.ts`
- Modify: `products/p1-markdown-x402/package.json`
- Modify: `products/p1-markdown-x402/tsconfig.json`

**Interfaces:**
- Produces: `htmlToMarkdown(html: string): string` — exported from `src/html-to-markdown.ts`. Pure function: given a full HTML document or fragment as a string, returns trimmed Markdown. No `env`/binding dependency. Task 2 imports this exact name and signature.

- [ ] **Step 1: Add dependencies**

Edit `products/p1-markdown-x402/package.json`. Add to `"dependencies"`:

```json
    "linkedom": "^0.18.4",
    "turndown": "^7.2.0",
```

(keep existing `@x402/*`/`hono` entries, alphabetical order not required — match the file's existing style).

Add to `"devDependencies"`:

```json
    "@cloudflare/vitest-plugin": "^1.1.5",
    "@types/turndown": "^5.0.5",
    "vitest": "^4.1.0",
```

Add to `"scripts"`:

```json
    "test": "vitest run",
    "typecheck": "tsc --noEmit",
```

- [ ] **Step 2: Run npm install**

Run: `npm install` (from `products/p1-markdown-x402/`)
Expected: installs cleanly, `package-lock.json` updated. If it fails on a version, use the closest available matching major version instead of pinning to something nonexistent — note the substitution in your report.

- [ ] **Step 3: Add vitest config**

Create `products/p1-markdown-x402/vitest.config.ts`:

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

- [ ] **Step 4: Update tsconfig to include tests**

Edit `products/p1-markdown-x402/tsconfig.json` — replace its full contents with:

```json
{
  "compilerOptions": {
    "target": "es2021",
    "lib": ["es2021"],
    "module": "es2022",
    "moduleResolution": "bundler",
    "types": ["@cloudflare/workers-types", "@cloudflare/vitest-plugin/types"],
    "strict": true,
    "skipLibCheck": true,
    "resolveJsonModule": true,
    "noEmit": true
  },
  "include": ["src", "tests"]
}
```

- [ ] **Step 5: Write the failing tests**

Create `products/p1-markdown-x402/tests/html-to-markdown.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { htmlToMarkdown } from "../src/html-to-markdown";

describe("htmlToMarkdown", () => {
  it("converts a heading and paragraph", () => {
    const html = "<html><body><h1>Hello World</h1><p>This is a paragraph.</p></body></html>";
    const md = htmlToMarkdown(html);
    expect(md).toContain("# Hello World");
    expect(md).toContain("This is a paragraph.");
  });

  it("preserves heading levels", () => {
    const html = "<h1>Title</h1><h2>Subtitle</h2><p>Body text.</p>";
    const md = htmlToMarkdown(html);
    expect(md).toContain("# Title");
    expect(md).toContain("## Subtitle");
  });

  it("converts an unordered list to list items", () => {
    const html = "<ul><li>First item</li><li>Second item</li></ul>";
    const md = htmlToMarkdown(html);
    expect(md).toMatch(/[-*] First item/);
    expect(md).toMatch(/[-*] Second item/);
  });

  it("converts a link to Markdown link syntax", () => {
    const html = '<p>See <a href="https://example.com">the docs</a> for more.</p>';
    const md = htmlToMarkdown(html);
    expect(md).toContain("[the docs](https://example.com)");
  });

  it("converts a code block to a fenced code block", () => {
    const html = "<pre><code>const x = 1;</code></pre>";
    const md = htmlToMarkdown(html);
    expect(md).toContain("```");
    expect(md).toContain("const x = 1;");
  });

  it("strips script and style content instead of leaking it into the output", () => {
    const html =
      "<html><head><style>body { color: red; }</style></head><body>" +
      "<script>alert('hi');</script><p>Visible text.</p></body></html>";
    const md = htmlToMarkdown(html);
    expect(md).toContain("Visible text.");
    expect(md).not.toContain("color: red");
    expect(md).not.toContain("alert(");
  });
});
```

- [ ] **Step 6: Run tests to verify they fail**

Run: `npm test` (from `products/p1-markdown-x402/`)
Expected: FAIL — `src/html-to-markdown.ts` does not exist yet (module not found).

- [ ] **Step 7: Implement the conversion module**

Create `products/p1-markdown-x402/src/html-to-markdown.ts`:

```ts
import TurndownService from "turndown";
import { parseHTML } from "linkedom";

// Cached per isolate — TurndownService construction has no per-request
// state, same caching pattern as the rest of this product's src/index.ts
// (getSupportedMimeTypes, getConvertPaymentMiddleware).
const turndownService = new TurndownService({
  headingStyle: "atx",
  codeBlockStyle: "fenced",
});
turndownService.remove(["script", "style", "noscript"]);

export function htmlToMarkdown(html: string): string {
  const { document } = parseHTML(html);
  const root = document.body ?? document.documentElement ?? document;
  return turndownService.turndown(root as unknown as HTMLElement).trim();
}
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `npm test` (from `products/p1-markdown-x402/`)
Expected: PASS, all 6 tests green.

- [ ] **Step 9: Typecheck**

Run: `npm run typecheck` (from `products/p1-markdown-x402/`)
Expected: no errors. If `turndown`'s bundled/`@types/turndown` types don't line up with the `TurndownService` constructor options used above, adjust the options object to whatever the installed types actually accept — do not use `any`/`@ts-ignore` to silence it; report the discrepancy if the options need to change from what's shown here.

- [ ] **Step 10: Commit**

```bash
git add products/p1-markdown-x402/package.json products/p1-markdown-x402/package-lock.json products/p1-markdown-x402/vitest.config.ts products/p1-markdown-x402/tsconfig.json products/p1-markdown-x402/src/html-to-markdown.ts products/p1-markdown-x402/tests/html-to-markdown.test.ts
git commit -m "feat(p1): add HTML-to-Markdown fast-path module (turndown+linkedom)"
```

---

### Task 2: Wire the fast-path into `/convert` routing

**Files:**
- Modify: `products/p1-markdown-x402/src/index.ts`

**Interfaces:**
- Consumes: `htmlToMarkdown(html: string): string` from `src/html-to-markdown.ts` (Task 1).

- [ ] **Step 1: Import the new module**

In `products/p1-markdown-x402/src/index.ts`, add near the top with the other imports (after the `@x402/extensions/offer-receipt` import block, before `export interface Env`):

```ts
import { htmlToMarkdown } from "./html-to-markdown";
```

- [ ] **Step 2: Add the HTML MIME-type set**

Add this constant right after the existing `MAX_SOURCE_BYTES` line (currently `const MAX_SOURCE_BYTES = 10 * 1024 * 1024; // 10 MB`):

```ts
// Fast-path: these MIME types skip env.AI.toMarkdown() (Workers AI, global
// Neurons quota) entirely and convert locally via turndown+linkedom — see
// html-to-markdown.ts and ARCHITECTURE.md 2026-09-10 Phase A decision.
const HTML_MIME_TYPES = new Set(["text/html", "application/xhtml+xml"]);
```

- [ ] **Step 3: Add the shared conversion helper**

Add this function right after `structureMarkdown` (which ends with the closing `}` before the `// Discovery —` comment block):

```ts
async function convertBlobToMarkdown(
  env: Env,
  name: string,
  blob: Blob,
  mimeType: string
): Promise<{ markdown: string; tokens: number | null } | { error: string }> {
  if (HTML_MIME_TYPES.has(mimeType)) {
    const html = await blob.text();
    return { markdown: htmlToMarkdown(html), tokens: null };
  }
  const [converted] = await env.AI.toMarkdown([{ name, blob }]);
  if (converted.format === "error") {
    return { error: converted.error };
  }
  return { markdown: converted.data, tokens: converted.tokens };
}
```

- [ ] **Step 4: Route the file-upload branch through the helper**

In the `app.post("/convert", ...)` handler (the second one, with the try/catch), find:

```ts
      const [converted] = await c.env.AI.toMarkdown([{ name: file.name, blob: file }]);
      if (converted.format === "error") {
        return c.json({ error: `Conversion failed: ${converted.error}` }, 502);
      }

      logPaymentEvent(c.env, "payment_success", {
        endpoint: "/convert",
        source_type: "file",
        status: 200,
        paid: true,
        amount: PRICE_USD_NUMBER,
      });

      return c.json(structureMarkdown(converted.data, file.name, "file", converted.tokens));
```

Replace with:

```ts
      const converted = await convertBlobToMarkdown(c.env, file.name, file, file.type);
      if ("error" in converted) {
        return c.json({ error: `Conversion failed: ${converted.error}` }, 502);
      }

      logPaymentEvent(c.env, "payment_success", {
        endpoint: "/convert",
        source_type: "file",
        status: 200,
        paid: true,
        amount: PRICE_USD_NUMBER,
      });

      return c.json(structureMarkdown(converted.markdown, file.name, "file", converted.tokens));
```

- [ ] **Step 5: Route the URL-fetch branch through the helper**

In the same handler, find:

```ts
    const [converted] = await c.env.AI.toMarkdown([{ name, blob }]);
    if (converted.format === "error") {
      return c.json({ error: `Conversion failed: ${converted.error}` }, 502);
    }

    logPaymentEvent(c.env, "payment_success", {
      endpoint: "/convert",
      source_type: "url",
      status: 200,
      paid: true,
      amount: PRICE_USD_NUMBER,
    });

    return c.json(structureMarkdown(converted.data, body.url, "url", converted.tokens));
```

Replace with:

```ts
    const converted = await convertBlobToMarkdown(c.env, name, blob, sourceMimeType);
    if ("error" in converted) {
      return c.json({ error: `Conversion failed: ${converted.error}` }, 502);
    }

    logPaymentEvent(c.env, "payment_success", {
      endpoint: "/convert",
      source_type: "url",
      status: 200,
      paid: true,
      amount: PRICE_USD_NUMBER,
    });

    return c.json(structureMarkdown(converted.markdown, body.url, "url", converted.tokens));
```

- [ ] **Step 6: Typecheck**

Run: `npm run typecheck` (from `products/p1-markdown-x402/`)
Expected: no errors.

- [ ] **Step 7: Run the full test suite**

Run: `npm test` (from `products/p1-markdown-x402/`)
Expected: PASS — Task 1's 6 tests still green (this task doesn't touch `html-to-markdown.ts`).

- [ ] **Step 8: Local boot smoke test (no deploy, no secrets, no payment)**

Run: `npx wrangler dev` (from `products/p1-markdown-x402/`) in the background, then:

`curl -i http://localhost:8787/agent.json`

Expected: 200 JSON response (this route has no payment gate — it only proves the Worker bundles and boots cleanly with the new `turndown`/`linkedom` imports, catching any Workers-runtime incompatibility that `vitest`'s Miniflare environment might not). Stop the `wrangler dev` process afterward.

Do NOT run `npx wrangler deploy`. Do NOT configure any secrets. This task stops at a locally verified, committed branch.

- [ ] **Step 9: Commit**

```bash
git add products/p1-markdown-x402/src/index.ts
git commit -m "feat(p1): route HTML sources in /convert through the turndown+linkedom fast-path"
```
