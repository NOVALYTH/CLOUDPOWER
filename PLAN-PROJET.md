# PLAN-PROJET.md — Catalogue technique des briques Cloudflare

> **Ce document est une RÉFÉRENCE TECHNIQUE, pas un plan d'exécution.**
> Pour le plan d'exécution, voir `ROADMAP.md`.
> Toutes les limites, APIs et configurations sont vérifiées contre la documentation officielle Cloudflare (sept. 2026).

---

## TABLE DES MATIÈRES

1. [Architecture cible](#1-architecture-cible)
2. [Limites Free Tier de référence](#2-limites-free-tier-de-référence)
3. [Brique A — Paywall x402/MPP](#brique-a--paywall-x402mpp)
4. [Brique B — LLM API](#brique-b--llm-api)
5. [Brique C — Génération d'images](#brique-c--génération-dimages)
6. [Brique D — Web scraping / Browser Run](#brique-d--web-scraping--browser-run)
7. [Brique E — R2 presigned URLs](#brique-e--r2-presigned-urls)
8. [Brique F — Stream signed tokens](#brique-f--stream-signed-tokens)
9. [Brique G — TTS / Transcription](#brique-g--tts--transcription)
10. [Brique H — Translation](#brique-h--translation)
11. [Brique I — Markdown conversion](#brique-i--markdown-conversion)
12. [Brique J — AI Search](#brique-j--ai-search)
13. [Brique K — API key gating (KV)](#brique-k--api-key-gating-kv)
14. [Brique L — JWT gating](#brique-l--jwt-gating)
15. [Brique M — Pay Per Crawl](#brique-m--pay-per-crawl)
16. [Couche transversale — Gateway partagé](#couche-transversale--gateway-partagé)
17. [Couche transversale — Pricing engine](#couche-transversale--pricing-engine)
18. [Couche transversale — Agent discovery](#couche-transversale--agent-discovery)
19. [Couche transversale — Metering / D1](#couche-transversale--metering--d1)
20. [Séquence de déploiement recommandée](#séquence-de-déploiement-recommandée)
21. [Checklist de validation universelle](#checklist-de-validation-universelle)
22. [Dépannage universel](#dépannage-universel)
23. [Références officielles](#références-officielles)

---

## 1. ARCHITECTURE CIBLE

```
                    ┌─────────────────────────────────┐
                    │       CLIENTS / AGENTS IA         │
                    │  (paient en USDC sur Base)        │
                    └──────────────┬────────────────────┘
                                   │
                    ┌──────────────▼────────────────────┐
                    │     CLOUDFLARE EDGE (Free Tier)    │
                    │                                    │
                    │  ┌─────────────────────────────┐  │
                    │  │   Gateway (Phase 3+)         │  │
                    │  │   router / auth / payments   │  │
                    │  └──────────┬──────────────────┘  │
                    │             │                      │
                    │  ┌──────────▼──────────────────┐  │
                    │  │     PRODUITS VERTICAUX        │  │
                    │  │                              │  │
                    │  │  P1. Data API niche          │  │
                    │  │  P2. Markdown conversion      │  │
                    │  │  P3. Synthetic datasets       │  │
                    │  │  P4. ...                     │  │
                    │  └──────────┬──────────────────┘  │
                    │             │                      │
                    │  ┌──────────▼──────────────────┐  │
                    │  │     BRIQUES TECHNIQUES        │  │
                    │  │                              │  │
                    │  │  A. x402/MPP paywall          │  │
                    │  │  B. LLM (Workers AI)          │  │
                    │  │  C. Image gen (Workers AI)     │  │
                    │  │  D. Scraping (Browser Run)     │  │
                    │  │  E. R2 presigned URLs          │  │
                    │  │  F. Stream tokens             │  │
                    │  │  G. TTS/ASR (Workers AI)      │  │
                    │  │  H. Translation (Workers AI)   │  │
                    │  │  I. Markdown conv (Workers AI) │  │
                    │  │  J. AI Search (Vectorize)      │  │
                    │  │  K. API keys (KV)             │  │
                    │  │  L. JWT gating                │  │
                    │  └──────────┬──────────────────┘  │
                    │             │                      │
                    │  ┌──────────▼──────────────────┐  │
                    │  │     STOCKAGE / ÉTAT           │  │
                    │  │  KV (keys, anti-replay)       │  │
                    │  │  R2 (fichiers, datasets)      │  │
                    │  │  D1 (metering, logs)         │  │
                    │  │  Durable Objects (replay fort)│  │
                    │  └─────────────────────────────┘  │
                    └─────────────────────────────────┘
                                   │
                    ┌──────────────▼────────────────────┐
                    │  WALLET TRUSTWALLET (Base)         │
                    │  Réception USDC automatique        │
                    └─────────────────────────────────┘
```

### Principes de conception

1. **Un Worker par produit vertical** — pas un Worker par brique technique
2. **x402/MPP en façade** — le paywall est un proxy ou un middleware inline
3. **Pas de clé privée blockchain** — le facilitator gère la vérification
4. **Pas de signature on-chain** — le Worker fait du I/O, pas du compute lourd
5. **Stockage minimal** — JWT stateless par défaut, KV/D1/DO seulement si nécessaire
6. **100% Free Tier** — chaque brique respecte les limites strictes
7. **Produit avant infrastructure** — le premier produit n'a pas besoin de shared layer
8. **Agent-first** — chaque produit expose `agent.json` et `llms.txt`

---

## 2. LIMITES FREE TIER DE RÉFÉRENCE

| Ressource | Limite Free | Notes |
|-----------|-------------|-------|
| Requêtes/jour | 100 000 | Par Worker |
| CPU par requête | 10 ms | Le I/O (`fetch()`) ne compte PAS |
| Mémoire | 128 MB | Par Worker |
| Subrequests/req | 50 | fetch() externes |
| Workers par compte | 100 | |
| KV namespaces | 100 | |
| KV reads/jour | 100 000 | Par namespace |
| KV writes/jour | 1 000 | Par namespace |
| R2 stockage | 10 GB | Total compte |
| R2 opérations A | 1M/mois | List, put, copy |
| R2 opérations B | 10M/mois | Get, head |
| D1 reads | 5M/jour | Par base |
| D1 writes | 100K/jour | Par base |
| Workers AI Neurons | 10 000/jour | **GLOBAL** (pas par Worker) |
| Browser Run | 10 min/jour | **GLOBAL** |
| Browser Run /crawl | 5 jobs/jour, 100 pages/job | |
| Browser Run Quick Actions | 1 req/10s | |
| Durable Objects (SQLite) | 100 000 req/jour, 313 000 GB-s/jour compute, 1,25M row-reads/jour, 100 000 row-writes/jour | Gratuit depuis 2025-04-07, cohérence forte — voir règle 5 |
| Taille Worker | 64 MiB **non compressé** | Relevé depuis 3MB compressé le 2026-09-04, tous plans |

### Règles critiques

1. **Workers AI 10K Neurons/jour est GLOBAL** — partagé entre tous les Workers AI du compte
2. **Browser Run 10 min/jour est GLOBAL** — le scraping est limité
3. **KV 1K writes/jour** — utiliser JWT stateless par défaut, KV seulement pour anti-replay ou API keys
4. **CPU 10 ms** — le I/O ne compte pas, seul le code exécuté compte
5. **Durable Objects SQLite gratuit** — quotas bien supérieurs à KV (100k row-writes/jour vs 1k),
   à préférer à KV pour tout état qui a besoin de cohérence forte (ex. registre anti-replay) —
   candidat p7 dans `ROADMAP.md` Phase 1.5

---

## BRIQUE A — Paywall x402/MPP

### Description
Proxy payant devant une API/backend. Les agents paient en USDC sur Base via x402/MPP. Le Worker ne signe pas de transactions — la vérification est déléguée au facilitator MPP.

### Stack
- Template officiel `cloudflare/mpp-proxy` (pour usage standalone)
- Ou middleware inline `x402-hono` (pour intégration dans un produit)
- 2 secrets : `JWT_SECRET`, `MPP_SECRET_KEY`

### Configuration `wrangler.jsonc` (mpp-proxy standalone)

```jsonc
{
  "name": "paywall-mpp",
  "main": "src/index.ts",
  "compatibility_date": "2026-09-06",
  "compatibility_flags": ["nodejs_compat"],
  "vars": {
    "PAY_TO": "0xVOTRE_ADRESSE_WALLET_BASE",
    "TEMPO_TESTNET": false,
    "PAYMENT_CURRENCY": "0x20c000000000000000000000b9537d11c60e8b50",
    "PROTECTED_PATTERNS": [
      {
        "pattern": "/api/*",
        "amount": "0.01",
        "description": "API access for 1 hour"
      }
    ]
  }
}
```

### Déploiement (mpp-proxy standalone)

```bash
git clone https://github.com/cloudflare/mpp-proxy.git products/p1-paywall
cd products/p1-paywall
npm install
npx wrangler secret put JWT_SECRET
npx wrangler secret put MPP_SECRET_KEY
npx wrangler deploy
```

### Intégration inline (`@x402/hono` v2 dans un produit)

`x402-hono` v1.2.0 est **deprecated** (le package lui-même l'annonce : "security patches only",
migrer vers v2). Le premier produit (`p1-markdown-x402`) a été construit directement en v2 —
API réelle vérifiée sur les types publiés (`@x402/hono`, `@x402/core`, `@x402/evm`, tous en
`2.25.0`). Différences clés vs v1 : réseau au format CAIP-2 (`eip155:84532` = Base Sepolia,
`eip155:8453` = Base mainnet, pas `"base-sepolia"`), le scheme EVM se déclare via
`registerExactEvmScheme(server)` sur un `x402ResourceServer`, et `payTo` fait partie de chaque
`accepts` (peut varier par route). Installer avec `--legacy-peer-deps` (le peer optionnel
`@x402/paywall` réclame React 19, inutile pour un usage agent-only sans paywall UI).

```typescript
import { Hono } from "hono";
import { paymentMiddleware } from "@x402/hono";
import { x402ResourceServer, HTTPFacilitatorClient } from "@x402/core/server";
import { registerExactEvmScheme } from "@x402/evm/exact/server";

const facilitator = new HTTPFacilitatorClient({ url: "https://x402.org/facilitator" });
const resourceServer = registerExactEvmScheme(new x402ResourceServer(facilitator));

const app = new Hono<{ Bindings: Env }>();

// env n'existe qu'au niveau requête sur Workers — le middleware se construit
// dans app.use() pour lire c.env.PAY_TO (le resourceServer, lui, est partagé).
app.use("/api/*", async (c, next) => {
  const routes = {
    "/api/*": {
      accepts: {
        scheme: "exact",
        price: "$0.005",
        network: "eip155:84532" as const, // testnet d'abord — voir x402-payments.md #3
        payTo: c.env.PAY_TO,
        maxTimeoutSeconds: 300,
      },
      description: "Description de la route",
    },
  };
  return paymentMiddleware(routes, resourceServer)(c, next);
});

app.all("/api/*", async (c) => {
  // Logique du produit
});

export default app;
```

Exemple complet fonctionnel : `products/p1-markdown-x402/src/index.ts`.

### Variables
| Variable | Description |
|----------|-------------|
| `PAY_TO` | Adresse wallet Base (TrustWallet) — publique uniquement |
| `TEMPO_TESTNET` | `true` pour testnet, `false` pour mainnet |
| `PAYMENT_CURRENCY` | Adresse contrat USDC sur Base |
| `PROTECTED_PATTERNS` | Routes protégées + montants |

### Grille de prix recommandée (micro-économie x402)

| Type | Prix USDC | Cas d'usage |
|------|----------|-------------|
| Données simples | 0.001 | Lookup, metadata |
| Recherche | 0.003 | AI Search, query |
| Transformation | 0.005 | Markdown, format |
| Requête standard | 0.01 | API call, extraction |
| Opération coûteuse | 0.05 | Génération, analyse complexe |

---

## BRIQUE B — LLM API

### Description
Expose une API LLM qui proxy vers Workers AI (gratuit sur Free Tier). À utiliser comme moteur invisible d'un produit vertical, pas comme API LLM générique.

### Stack
- 1 Worker + Workers AI binding (`env.AI`)
- Modèles gratuits : `@cf/google/gemma-4-26b-a4b-it`, `@cf/openai/gpt-oss-120b`, `@cf/openai/gpt-oss-20b`, `@cf/zai-org/glm-4.7-flash`, `@cf/nvidia/nemotron-3-120b-a12b`, `@cf/mistralai/mistral-small-3.1-24b-instruct`

### `wrangler.jsonc`

```jsonc
{
  "name": "llm-engine",
  "main": "src/index.ts",
  "compatibility_date": "2026-09-06",
  "compatibility_flags": ["nodejs_compat"],
  "ai": {
    "binding": "AI"
  }
}
```

### Code de base

```typescript
export interface Env {
  AI: Ai;
}

const MODELS: Record<string, string> = {
  "gemma-4-26b": "@cf/google/gemma-4-26b-a4b-it",
  "gpt-oss-120b": "@cf/openai/gpt-oss-120b",
  "gpt-oss-20b": "@cf/openai/gpt-oss-20b",
  "glm-4.7-flash": "@cf/zai-org/glm-4.7-flash",
  "nemotron-120b": "@cf/nvidia/nemotron-3-120b-a12b",
  "mistral-small": "@cf/mistralai/mistral-small-3.1-24b-instruct",
};

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === "/models" && request.method === "GET") {
      return Response.json({ models: Object.keys(MODELS) });
    }

    if (url.pathname === "/chat" && request.method === "POST") {
      const body = await request.json() as {
        model?: string;
        messages: Array<{ role: string; content: string }>;
        max_tokens?: number;
      };

      const modelKey = body.model || "gemma-4-26b";
      const modelId = MODELS[modelKey];
      if (!modelId) {
        return Response.json({ error: `Model '${modelKey}' not found` }, { status: 400 });
      }

      const response = await env.AI.run(modelId, {
        messages: body.messages,
        max_tokens: body.max_tokens || 1024,
      });

      return Response.json(response);
    }

    return Response.json({ error: "Not found" }, { status: 404 });
  },
} satisfies ExportedHandler<Env>;
```

### ⚠️ Ne pas vendre comme produit générique
Vendre `POST /chat` à $0.01 te met en concurrence avec OpenAI. Vendre `POST /api/extract-company-data` à $0.005 te met sur un marché sans concurrence. Le LLM est le moteur, pas le produit.

### Limite clé
- **10 000 Neurons/jour (global)** = ~500-1000 requêtes LLM/jour selon le modèle

---

## BRIQUE C — Génération d'images

### Description
API text-to-image utilisant `@cf/blackforestlabs/flux-1-schnell`. À verticaliser (product images, ad creatives, thumbnails) plutôt que de vendre un générateur générique.

### Stack
- 1 Worker + Workers AI binding
- Modèle : `@cf/blackforestlabs/flux-1-schnell`

### `wrangler.jsonc`

```jsonc
{
  "name": "image-engine",
  "main": "src/index.ts",
  "compatibility_date": "2026-09-06",
  "compatibility_flags": ["nodejs_compat"],
  "ai": {
    "binding": "AI"
  }
}
```

### Code de base

```typescript
export interface Env {
  AI: Ai;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === "/generate" && request.method === "POST") {
      const body = await request.json() as { prompt: string; width?: number; height?: number };

      if (!body.prompt) {
        return Response.json({ error: "Missing 'prompt'" }, { status: 400 });
      }

      const response = await env.AI.run("@cf/blackforestlabs/flux-1-schnell", {
        prompt: body.prompt,
        width: body.width || 1024,
        height: body.height || 1024,
      });

      if (response instanceof ReadableStream) {
        return new Response(response, { headers: { "Content-Type": "image/png" } });
      }

      return new Response(response as ReadableStream, { headers: { "Content-Type": "image/png" } });
    }

    return Response.json({ error: "Use POST /generate" }, { status: 404 });
  },
} satisfies ExportedHandler<Env>;
```

### Verticalisation recommandée
- `POST /api/product-image` — reçoit `{ product, audience, format }`, construit le prompt, génère
- `POST /api/ad-creative` — reçoit `{ brand, message, format }`, génère
- `POST /api/thumbnail` — reçoit `{ title, style }`, génère

Combiner avec LLM (prompt engineering) + R2 (stockage) + x402 (paiement).

---

## BRIQUE D — Web scraping / Browser Run

### Description
API qui scrape des sites via Browser Run et retourne des données structurées. À utiliser pour de l'extraction de données verticale, pas comme scraper généraliste.

### Stack
- 1 Worker + Browser Run binding (`env.BROWSER`)
- ⚠️ Limite Free : 10 min/jour browser, 5 crawls/jour, 1 req/10s

### `wrangler.jsonc`

```jsonc
{
  "name": "scraping-engine",
  "main": "src/index.ts",
  "compatibility_date": "2026-09-06",
  "compatibility_flags": ["nodejs_compat"],
  "browser": {
    "binding": "BROWSER"
  }
}
```

### Code de base

```typescript
export interface Env {
  BROWSER: BrowserRun;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === "/scrape" && request.method === "POST") {
      const body = await request.json() as {
        url: string;
        elements: Array<{ selector: string }>;
      };

      if (!body.url || !body.elements) {
        return Response.json({ error: "Missing 'url' or 'elements'" }, { status: 400 });
      }

      const response = await env.BROWSER.quickAction("scrape", {
        url: body.url,
        elements: body.elements,
      });

      const data = await response.json();
      return Response.json(data);
    }

    if (url.pathname === "/content" && request.method === "POST") {
      const body = await request.json() as { url: string };

      if (!body.url) {
        return Response.json({ error: "Missing 'url'" }, { status: 400 });
      }

      const response = await env.BROWSER.quickAction("content", {
        url: body.url,
        gotoOptions: { waitUntil: "networkidle2", timeout: 30000 },
      });

      const data = await response.json();
      return Response.json(data);
    }

    return Response.json({ error: "Use POST /scrape or POST /content" }, { status: 404 });
  },
} satisfies ExportedHandler<Env>;
```

### ⚠️ Limites Browser Run Free
| Ressource | Limite |
|-----------|--------|
| Browser hours | 10 min/jour |
| Quick Actions | 1 req/10s |
| /crawl jobs | 5/jour |
| Pages par crawl | 100 |

### ⚠️ Éthique et légalité
- Respecter `robots.txt` quand applicable
- Respecter les conditions d'utilisation des sites
- Ne pas contourner les mesures anti-bot
- Le `/crawl` endpoint de Cloudflare s'identifie comme bot et ne contourne pas la détection

---

## BRIQUE E — R2 presigned URLs

### Description
Stocke des fichiers dans R2. Après paiement, un Worker génère une URL temporaire pour télécharger le fichier. Le Worker ne fait jamais transiter les gros fichiers — il génère juste l'URL.

### Stack
- 1 Worker + R2 binding (`env.BUCKET`)
- `aws4fetch` pour générer les presigned URLs
- R2 Free : 10 GB + 1M ops A + 10M ops B/mois

### `wrangler.jsonc`

```jsonc
{
  "name": "r2-content",
  "main": "src/index.ts",
  "compatibility_date": "2026-09-06",
  "compatibility_flags": ["nodejs_compat"],
  "r2_buckets": [
    {
      "binding": "BUCKET",
      "bucket_name": "content"
    }
  ],
  "vars": {
    "R2_ACCOUNT_ID": "6e8035aa4fa06c71c4a168ab4ef365d2"
  }
}
```

### Code de base

```typescript
import { AwsClient } from "aws4fetch";

export interface Env {
  BUCKET: R2Bucket;
  R2_ACCOUNT_ID: string;
  R2_ACCESS_KEY_ID: string;
  R2_SECRET_ACCESS_KEY: string;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === "/list" && request.method === "GET") {
      const objects = await env.BUCKET.list();
      return Response.json({
        files: objects.objects.map((o) => ({ key: o.key, size: o.size, uploaded: o.uploaded })),
      });
    }

    if (url.pathname === "/download-url" && request.method === "POST") {
      const body = await request.json() as { key: string; expires?: number };
      if (!body.key) return Response.json({ error: "Missing 'key'" }, { status: 400 });

      const expiresIn = body.expires || 3600;
      const r2 = new AwsClient({
        accessKeyId: env.R2_ACCESS_KEY_ID,
        secretAccessKey: env.R2_SECRET_ACCESS_KEY,
      });

      const r2Url = new URL(`https://${env.R2_ACCOUNT_ID}.r2.cloudflarestorage.com/content/${body.key}`);
      r2Url.searchParams.set("X-Amz-Expires", String(expiresIn));
      const signed = await r2.sign(new Request(r2Url, { method: "GET" }), { aws: { signQuery: true } });

      return Response.json({ url: signed.url, expires_in: expiresIn });
    }

    if (url.pathname === "/upload" && request.method === "POST") {
      const body = await request.json() as { key: string; content: string };
      await env.BUCKET.put(body.key, body.content);
      return Response.json({ success: true, key: body.key });
    }

    return Response.json({ error: "Use GET /list, POST /download-url, POST /upload" }, { status: 404 });
  },
} satisfies ExportedHandler<Env>;
```

### Déploiement

```bash
npm install aws4fetch
npx wrangler r2 bucket create content
npx wrangler secret put R2_ACCESS_KEY_ID
npx wrangler secret put R2_SECRET_ACCESS_KEY
npx wrangler deploy
```

### Principe clé
Le Worker **autorise et génère l'URL**. R2 **sert le fichier directement**. Ne jamais faire transiter de gros fichiers par le Worker.

---

## BRIQUE F — Stream signed tokens

### Description
Vidéos premium. Après paiement, Worker génère un token Stream temporaire.

### Stack
- 1 Worker + Stream binding (`env.STREAM`)

### `wrangler.jsonc`

```jsonc
{
  "name": "stream-tokens",
  "main": "src/index.ts",
  "compatibility_date": "2026-09-06",
  "compatibility_flags": ["nodejs_compat"],
  "stream": {
    "binding": "STREAM"
  }
}
```

### Code de base

```typescript
export interface Env {
  STREAM: StreamBucket;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === "/access" && request.method === "POST") {
      const body = await request.json() as { video_id: string };
      if (!body.video_id) return Response.json({ error: "Missing 'video_id'" }, { status: 400 });

      const token = await env.STREAM.video(body.video_id).generateToken();
      return Response.json({ token, expires: "1 hour (default TTL)" });
    }

    return Response.json({ error: "Use POST /access" }, { status: 404 });
  },
} satisfies ExportedHandler<Env>;
```

### Statut
**DORMANT** — ne pas développer maintenant. Activer uniquement si un cas commercial concret justifie la vidéo premium.

---

## BRIQUE G — TTS / Transcription

### Description
API text-to-speech et speech-to-text via Workers AI. À combiner avec LLM pour des pipelines audio → texte → analyse → JSON.

### Stack
- 1 Worker + Workers AI binding
- Modèles : `@cf/deepgram/aura-1` (TTS), `@cf/deepgram/nova-3` (ASR)

### `wrangler.jsonc`

```jsonc
{
  "name": "tts-asr-engine",
  "main": "src/index.ts",
  "compatibility_date": "2026-09-06",
  "compatibility_flags": ["nodejs_compat"],
  "ai": {
    "binding": "AI"
  }
}
```

### Code de base

```typescript
export interface Env {
  AI: Ai;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === "/tts" && request.method === "POST") {
      const body = await request.json() as { text: string; voice?: string };
      if (!body.text) return Response.json({ error: "Missing 'text'" }, { status: 400 });

      const response = await env.AI.run("@cf/deepgram/aura-1", {
        text: body.text,
        voice: body.voice || "aura-asteria-en",
      });

      return new Response(response as ReadableStream, { headers: { "Content-Type": "audio/wav" } });
    }

    if (url.pathname === "/transcribe" && request.method === "POST") {
      const formData = await request.formData();
      const audioFile = formData.get("audio") as File;
      if (!audioFile) return Response.json({ error: "Missing 'audio' file" }, { status: 400 });

      const audioBuffer = await audioFile.arrayBuffer();
      const response = await env.AI.run("@cf/deepgram/nova-3", { audio: audioBuffer });
      return Response.json(response);
    }

    return Response.json({ error: "Use POST /tts or POST /transcribe" }, { status: 404 });
  },
} satisfies ExportedHandler<Env>;
```

### Verticalisation recommandée
- `POST /api/voice-note` — audio → ASR → LLM → JSON structuré
- `POST /api/meeting-summary` — audio → transcription → résumé → JSON

---

## BRIQUE H — Translation

### Description
API de traduction via `@cf/meta/m2m100-1.2b`. À combiner avec d'autres services (markdown, extraction).

### Stack
- 1 Worker + Workers AI binding
- Modèle : `@cf/meta/m2m100-1.2b`

### `wrangler.jsonc`

```jsonc
{
  "name": "translation-engine",
  "main": "src/index.ts",
  "compatibility_date": "2026-09-06",
  "compatibility_flags": ["nodejs_compat"],
  "ai": {
    "binding": "AI"
  }
}
```

### Code de base

```typescript
export interface Env {
  AI: Ai;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === "/translate" && request.method === "POST") {
      const body = await request.json() as { text: string; source_lang: string; target_lang: string };
      if (!body.text || !body.source_lang || !body.target_lang) {
        return Response.json({ error: "Missing 'text', 'source_lang', or 'target_lang'" }, { status: 400 });
      }

      const response = await env.AI.run("@cf/meta/m2m100-1.2b", {
        text: body.text,
        source_lang: body.source_lang,
        target_lang: body.target_lang,
      });

      return Response.json(response);
    }

    return Response.json({ error: "Use POST /translate" }, { status: 404 });
  },
} satisfies ExportedHandler<Env>;
```

---

## BRIQUE I — Markdown conversion

### Description
Convertit des documents (PDF, HTML, images) en Markdown propre via `env.AI.toMarkdown()`. **Brique stratégique** — alimente les pipelines RAG, AI Search, et extraction de données.

### Stack
- 1 Worker + Workers AI binding
- Méthode : `env.AI.toMarkdown()`

### `wrangler.jsonc`

```jsonc
{
  "name": "markdown-engine",
  "main": "src/index.ts",
  "compatibility_date": "2026-09-06",
  "compatibility_flags": ["nodejs_compat"],
  "ai": {
    "binding": "AI"
  }
}
```

### Code de base

```typescript
export interface Env {
  AI: Ai;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === "/convert" && request.method === "POST") {
      const formData = await request.formData();
      const file = formData.get("document") as File;
      if (!file) return Response.json({ error: "Missing 'document' file" }, { status: 400 });

      const fileBuffer = await file.arrayBuffer();
      const result = await env.AI.toMarkdown([{ name: file.name, blob: fileBuffer }]);
      return Response.json(result);
    }

    return Response.json({ error: "Use POST /convert with 'document' file" }, { status: 404 });
  },
} satisfies ExportedHandler<Env>;
```

### Pourquoi stratégique
```
I Markdown → J AI Search → B LLM → D Data extraction
```
Le Markdown est le format d'entrée universel pour les agents IA. Cette brique alimente tout le reste.

---

## BRIQUE J — AI Search

### Description
Instance AI Search sur un corpus niche. Facture l'accès à l'API de recherche.

### Stack
- 1 Worker + AI Search binding (`env.AI_SEARCH`) + Browser Run (pour l'indexation)
- 1 AI Search instance (créée via dashboard)

### `wrangler.jsonc`

```jsonc
{
  "name": "ai-search-service",
  "main": "src/index.ts",
  "compatibility_date": "2026-09-06",
  "compatibility_flags": ["nodejs_compat"],
  "ai_search": [
    {
      "binding": "AI_SEARCH",
      "instance_id": "VOTRE_INSTANCE_ID"
    }
  ],
  "browser": {
    "binding": "BROWSER"
  }
}
```

### Code de base

```typescript
export interface Env {
  AI_SEARCH: AiSearchNamespace;
  BROWSER: BrowserRun;
}

const INSTANCE_ID = "VOTRE_INSTANCE_ID";

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === "/search" && request.method === "POST") {
      const body = await request.json() as { query: string; max_results?: number };
      if (!body.query) return Response.json({ error: "Missing 'query'" }, { status: 400 });

      const results = await env.AI_SEARCH.get(INSTANCE_ID).search({
        query: body.query,
        max_results: body.max_results || 10,
      });

      return Response.json(results);
    }

    if (url.pathname === "/index" && request.method === "POST") {
      const body = await request.json() as { url: string };
      if (!body.url) return Response.json({ error: "Missing 'url'" }, { status: 400 });

      const response = await env.BROWSER.quickAction("content", {
        url: body.url,
        gotoOptions: { waitUntil: "networkidle2", timeout: 30000 },
      });

      const data = await response.json();
      if (!data.success || typeof data.result !== "string") {
        return Response.json({ error: "Browser Run failed" }, { status: 502 });
      }

      const item = await env.AI_SEARCH.get(INSTANCE_ID).items.uploadAndPoll(
        body.url, data.result, { timeoutMs: 60_000 }
      );

      return Response.json({ key: item.key, status: item.status });
    }

    return Response.json({ error: "Use POST /search or POST /index" }, { status: 404 });
  },
} satisfies ExportedHandler<Env>;
```

### Condition de succès
Nécessite un **corpus de données réellement utile**. Sans corpus valuable, l'AI Search ne génère pas de revenu.

---

## BRIQUE K — API key gating (KV)

### Description
Stocke des clés API dans KV. Le Worker vérifie `Authorization: Bearer <key>` contre KV. Pour les clients récurrents qui veulent prépayer.

### Stack
- 1 Worker + 1 KV namespace
- ⚠️ KV Free : 100K reads/jour, 1K writes/jour

### `wrangler.jsonc`

```jsonc
{
  "name": "api-key-gating",
  "main": "src/index.ts",
  "compatibility_date": "2026-09-06",
  "compatibility_flags": ["nodejs_compat"],
  "kv_namespaces": [
    {
      "binding": "API_KEYS",
      "id": "VOTRE_KV_NAMESPACE_ID"
    }
  ]
}
```

### Code de base

```typescript
export interface Env {
  API_KEYS: KVNamespace;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const auth = request.headers.get("Authorization");
    if (!auth || !auth.startsWith("Bearer ")) {
      return Response.json({ error: "Missing API key" }, { status: 401 });
    }

    const apiKey = auth.slice(7);
    const keyData = await env.API_KEYS.get(apiKey, "json") as {
      email: string;
      expires: number;
      active: boolean;
    } | null;

    if (!keyData) return Response.json({ error: "Invalid API key" }, { status: 401 });
    if (!keyData.active) return Response.json({ error: "API key deactivated" }, { status: 403 });
    if (keyData.expires && Date.now() > keyData.expires) {
      return Response.json({ error: "API key expired" }, { status: 403 });
    }

    return Response.json({ message: "Access granted", email: keyData.email });
  },
} satisfies ExportedHandler<Env>;
```

### Déploiement

```bash
npx wrangler kv namespace create API_KEYS
# Copier l'ID dans wrangler.jsonc
npx wrangler deploy

# Ajouter une clé
npx wrangler kv key put --namespace-id=VOTRE_KV_ID "sk-abc123" '{"email":"client@example.com","expires":1735689600000,"active":true}'
```

### Rôle dans l'architecture
```
x402 = paiement sans compte (agent de passage)
API key = client récurrent (préfinancement)
JWT = admin / interne
```

---

## BRIQUE L — JWT gating

### Description
JWT signés via Web Crypto API. Stateless, aucun stockage. Pour l'administration et l'accès interne.

### Stack
- 1 Worker + Web Crypto API
- 1 secret : `JWT_SECRET`

### `wrangler.jsonc`

```jsonc
{
  "name": "jwt-gating",
  "main": "src/index.ts",
  "compatibility_date": "2026-09-06",
  "compatibility_flags": ["nodejs_compat"]
}
```

### Code de base

```typescript
export interface Env {
  JWT_SECRET: string;
}

function base64url(data: ArrayBuffer | Uint8Array): string {
  const bytes = data instanceof Uint8Array ? data : new Uint8Array(data);
  let binary = "";
  for (const b of bytes) binary += String.fromCharCode(b);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function base64urlDecode(str: string): Uint8Array {
  str = str.replace(/-/g, "+").replace(/_/g, "/");
  const binary = atob(str);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes;
}

async function signJWT(payload: object, secret: string): Promise<string> {
  const header = { alg: "HS256", typ: "JWT" };
  const headerB64 = base64url(new TextEncoder().encode(JSON.stringify(header)));
  const payloadB64 = base64url(new TextEncoder().encode(JSON.stringify(payload)));
  const data = `${headerB64}.${payloadB64}`;
  const key = await crypto.subtle.importKey(
    "raw", new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" }, false, ["sign", "verify"]
  );
  const signature = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(data));
  return `${data}.${base64url(signature)}`;
}

async function verifyJWT(token: string, secret: string): Promise<object | null> {
  const parts = token.split(".");
  if (parts.length !== 3) return null;
  const [headerB64, payloadB64, sigB64] = parts;
  const data = `${headerB64}.${payloadB64}`;
  const key = await crypto.subtle.importKey(
    "raw", new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" }, false, ["verify"]
  );
  const signature = base64urlDecode(sigB64);
  const valid = await crypto.subtle.verify("HMAC", key, signature, new TextEncoder().encode(data));
  if (!valid) return null;
  const payload = JSON.parse(new TextDecoder().decode(base64urlDecode(payloadB64)));
  if (payload.exp && Date.now() > payload.exp) return null;
  return payload;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === "/issue" && request.method === "POST") {
      const body = await request.json() as { email: string; duration_hours?: number };
      if (!body.email) return Response.json({ error: "Missing 'email'" }, { status: 400 });
      const durationMs = (body.duration_hours || 1) * 60 * 60 * 1000;
      const payload = { email: body.email, iat: Date.now(), exp: Date.now() + durationMs };
      const token = await signJWT(payload, env.JWT_SECRET);
      return Response.json({ token, expires_at: payload.exp });
    }

    const auth = request.headers.get("Authorization");
    if (!auth || !auth.startsWith("Bearer ")) {
      return Response.json({ error: "Missing JWT" }, { status: 401 });
    }
    const payload = await verifyJWT(auth.slice(7), env.JWT_SECRET);
    if (!payload) return Response.json({ error: "Invalid or expired JWT" }, { status: 401 });

    return Response.json({ message: "Access granted", user: payload });
  },
} satisfies ExportedHandler<Env>;
```

### Rôle dans l'architecture
**Administration et accès privé uniquement.** Pas comme système principal de monétisation.

---

## BRIQUE M — Pay Per Crawl

### Description
Feature native de AI Crawl Control. Les crawlers IA paient pour accéder à ton contenu.

### Configuration
- **Dashboard uniquement** — zéro code
- ⚠️ Bêta fermée — inscription via cloudflare.com/paypercrawl-signup
- ⚠️ Payouts via Stripe (géré par Cloudflare)
- Nécessite une zone Cloudflare active avec du contenu

### Statut
**WATCH** — ne pas investir de temps maintenant. Surveiller si Cloudflare ouvre le système et si les conditions de payout deviennent compatibles.

---

## COUCHE TRANSVERSALE — Gateway partagé

### Statut
**Phase 3+** — ne pas créer avant d'avoir 2+ produits déployés.

### Structure (quand créé)

```
shared/
├── payments/
│   ├── x402.ts          # Middleware x402 réutilisable
│   └── types.ts
├── pricing/
│   ├── catalog.ts       # Catalogue des prix par service
│   └── calculator.ts    # Calcul du prix par requête
├── discovery/
│   ├── agent.json       # Template agent.json
│   └── llms.txt         # Template llms.txt
├── auth/
│   ├── jwt.ts           # Vérification JWT
│   └── api-key.ts       # Vérification API key (KV)
└── types/
    └── env.ts           # Types d'environnement partagés
```

### Quand créer
Quand tu as 2+ produits qui ont besoin des mêmes :
- Logique de paiement x402
- Vérification d'authentification
- Catalogue de prix
- Agent discovery

---

## COUCHE TRANSVERSALE — Pricing engine

### Statut
**Phase 3+** — le premier produit hardcode ses prix.

### Structure (quand créé)

```typescript
// shared/pricing/catalog.ts
export const PRICING = {
  "data.extract": { price: "0.005", currency: "USDC", network: "base" },
  "data.search": { price: "0.003", currency: "USDC", network: "base" },
  "markdown.convert": { price: "0.005", currency: "USDC", network: "base" },
  "image.generate": { price: "0.05", currency: "USDC", network: "base" },
  "llm.analyze": { price: "0.01", currency: "USDC", network: "base" },
} as const;
```

---

## COUCHE TRANSVERSALE — Agent discovery

### Statut
**Phase 1** — chaque produit expose `agent.json` et `llms.txt` dès le premier déploiement.

### `agent.json` (template)

```json
{
  "name": "product-name",
  "version": "1.0.0",
  "description": "Ce que fait le service",
  "endpoints": [
    {
      "path": "/api/endpoint",
      "method": "POST",
      "description": "Ce que fait l'endpoint",
      "payment": {
        "protocol": "x402",
        "amount": "0.005",
        "currency": "USDC",
        "network": "base",
        "payTo": "0xVOTRE_WALLET"
      },
      "input": {
        "type": "object",
        "properties": {
          "query": { "type": "string", "description": "La requête" }
        },
        "required": ["query"]
      },
      "output": {
        "type": "object",
        "properties": {
          "result": { "type": "string" }
        }
      }
    }
  ]
}
```

### `llms.txt` (template)

```markdown
# Product Name

> Description courte du service

## Payment

Ce service utilise le protocole x402. Chaque requête requiert un paiement de 0.005 USDC sur Base.

## Endpoints

### POST /api/endpoint

Description de l'endpoint.

Input: { "query": "string" }
Output: { "result": "string" }

## Usage

1. Envoyer une requête GET/POST sans paiement → recevoir 402
2. Payer 0.005 USDC sur Base à l'adresse indiquée
3. Renvoyer la requête avec le credential de paiement
4. Recevoir la réponse
```

---

## COUCHE TRANSVERSALE — Metering / D1

### Statut
**Phase 4+** — quand tu as assez de volume pour en avoir besoin.

### Structure (quand créé)

```sql
CREATE TABLE usage_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp INTEGER NOT NULL,
  worker TEXT NOT NULL,
  endpoint TEXT NOT NULL,
  method TEXT NOT NULL,
  status INTEGER NOT NULL,
  response_time_ms INTEGER,
  payment_amount TEXT,
  payment_currency TEXT,
  agent_id TEXT,
  error TEXT
);

CREATE INDEX idx_timestamp ON usage_events(timestamp);
CREATE INDEX idx_endpoint ON usage_events(endpoint);
```

### Avant D1
Utiliser `console.log` + `wrangler tail`. Suffisant pour le premier produit.

---

## SÉQUENCE DE DÉPLOIEMENT RECOMMANDÉE

> **Voir `ROADMAP.md` pour le plan d'exécution détaillé.**
> Le tableau ci-dessous est un résumé de référence.

| Phase | Action | Briques utilisées | Revenu attendu |
|-------|--------|-------------------|----------------|
| 1 | Premier produit vertical | A (x402) + B (LLM) ou I (Markdown) ou D (Scraping) | Premier $ |
| 2 | Valider le revenu | — | Confirmation |
| 3 | Extraire shared layer | Gateway, pricing, discovery | Refactor |
| 4 | Deuxième produit | A + autre brique | Diversification |
| 5 | AI Search | J (si corpus disponible) | Récurrent |
| 6 | Image / TTS / Translation | C, G, H (si cas vertical) | Niche |
| 7 | Stream / Pay Per Crawl | F, M (si opportunité) | Passif |

---

## CHECKLIST DE VALIDATION UNIVERSELLE

À exécuter pour chaque produit après déploiement.

### 1. Health check
```bash
curl -i https://<WORKER_URL>/
```

### 2. Test 402 (sans paiement)
```bash
curl -i https://<WORKER_URL>/api/endpoint
# → 402 + header WWW-Authenticate: Payment
```

### 3. Test avec paiement (si x402)
```bash
# Utiliser un client x402/MPP pour payer et retenter
# → 200 + contenu
```

### 4. Agent discovery
```bash
curl https://<WORKER_URL>/agent.json
# → JSON valide avec endpoints, prix, schémas
curl https://<WORKER_URL>/llms.txt
# → Texte lisible par un LLM
```

### 5. Surveillance des logs
```bash
npx wrangler tail
# → Pas d'erreur CPU, subrequest, ou 1027
```

### 6. Quota
Dashboard → Workers & Pages → Worker → Metrics
- [ ] Requests/day < 100 000
- [ ] CPU time moyen < 10 ms

### 7. Vérification on-chain (si x402)
BaseScan → adresse PAY_TO → transaction USDC visible

### 8. Test d'expiration
Attendre l'expiration du cookie/JWT → refaire la requête → doit retourner 402/401

---

## DÉPANNAGE UNIVERSEL

| Erreur | Cause | Solution |
|--------|-------|----------|
| `exceeded CPU time limit` | Worker > 10ms CPU | Optimiser : le I/O ne compte pas |
| `1027` | Quota 100K req/jour | Attendre minuit UTC ou Paid plan |
| `exceeded subrequest limit` | > 50 fetch()/req | Réduire les appels externes |
| `wrangler secret put` échoue | Non authentifié | `npx wrangler login` |
| `deploy` échoue (size) | Worker > 64 MiB | Vérifier les dépendances |
| AI `403` ou `5035` | Modèle Paid | Utiliser un modèle gratuit |
| AI `429` ou `3040` | Out of capacity | Réessayer ou autre modèle |
| Browser Run timeout | > 60s | Réduire la complexité |
| KV write limit | > 1000 writes/jour | JWT stateless au lieu de KV |
| R2 `ExpiredRequest` | Presigned URL expirée | Régénérer l'URL |

---

## RÉFÉRENCES OFFICIELLES

| Ressource | URL |
|-----------|-----|
| Workers Limits | https://developers.cloudflare.com/workers/platform/limits/ |
| Workers Pricing | https://developers.cloudflare.com/workers/platform/pricing/ |
| Workers AI Models | https://developers.cloudflare.com/workers-ai/models/ |
| Workers AI Pricing | https://developers.cloudflare.com/workers-ai/platform/pricing/ |
| Browser Run Limits | https://developers.cloudflare.com/browser-run/limits/ |
| R2 Presigned URLs | https://developers.cloudflare.com/r2/api/s3/presigned-urls/ |
| Stream Tokens | https://developers.cloudflare.com/stream/ |
| KV Limits | https://developers.cloudflare.com/kv/platform/limits/ |
| D1 Limits | https://developers.cloudflare.com/d1/platform/limits/ |
| Durable Objects Pricing | https://developers.cloudflare.com/durable-objects/platform/pricing/ |
| MPP charge for HTTP | https://developers.cloudflare.com/agents/tools/payments/mpp-charge-for-http-content/ |
| mpp-proxy (GitHub) | https://github.com/cloudflare/mpp-proxy |
| Pay Per Crawl | https://developers.cloudflare.com/ai-crawl-control/features/pay-per-crawl/what-is-pay-per-crawl/ |
| Wrangler config | https://developers.cloudflare.com/workers/wrangler/configuration/ |
| AI Search | https://developers.cloudflare.com/ai-search/ |
| Vectorize | https://developers.cloudflare.com/vectorize/ |
