# ROADMAP.md — Plan d'exécution produit-par-produit

> **Ce document pilote l'exécution.** Pour les détails techniques des briques, voir `PLAN-PROJET.md`.
> Philosophie : **revenu avant infrastructure.** ("un produit à la fois" révisé le 2026-09-07 —
> voir Phase 1.5 : ne s'applique plus qu'aux produits IA-intensifs/Browser-Rendering-intensifs,
> à cause des quotas Free Tier globaux partagés.)

---

## PRINCIPE DIRECTEUR

```
1 produit vertical → valide le revenu → extrais l'infrastructure partagée → 2e produit → 3e produit
```

**PAS :**
```
infrastructure partagée → 1er produit → 2e produit
```

### Règles
- Un produit IA-intensif/Browser-Rendering-intensif à la fois (quotas globaux partagés) — voir
  Phase 1.5 pour la règle complète. Les produits légers (CPU/`fetch()`/KV) n'ont pas cette
  contrainte.
- Le premier produit n'a pas besoin de shared layer. Le paywall est inline.
- Le pricing est hardcodé dans le code du premier produit.
- Le metering est un `console.log` + `wrangler tail`.
- L'agent discovery est un fichier `agent.json` + `llms.txt` à la racine.
- `shared/` n'est créé qu'en Phase 3 (quand 2+ produits existent).
- Ne crée un dossier que quand tu déploies le module correspondant.

---

## VUE D'ENSEMBLE

| Phase | Objectif | Durée estimée | Revenu attendu |
|-------|----------|---------------|----------------|
| **Phase 0** | Choix du produit vertical | 1 jour | — |
| **Phase 1** | Premier produit déployé | 2-3 jours | Premier $ |
| **Phase 1.5** | Produits légers en parallèle (2026-09-07) | Continu | Diversification $0-quota |
| **Phase 2** | Validation du revenu | 2-3 jours | Confirmation |
| **Phase 3** | Extraction shared layer | 1-2 jours | Refactor |
| **Phase 4** | Deuxième produit | 2-3 jours | Diversification |
| **Phase 5** | AI Search (si corpus) | 1-2 jours | Récurrent |
| **Phase 6** | Briques niche (image, TTS, translation) | 1 jour/chacune | Niche |
| **Phase 7** | Stream / Pay Per Crawl | — | Passif (si opportunité) |

---

## PHASE 0 — Choix du produit vertical

### Objectif
Choisir **UN** produit vertical à lancer. Pas 13. Pas 3. **Un.**

### Critères de choix
1. **Tu sais le construire** — tu as les compétences techniques
2. **Il y a de la demande** — des agents IA ou des développeurs veulent payer pour ça
3. **Le coût de production est $0** — Workers AI / Browser Run / R2 Free Tier
4. **Le prix de vente est justifié** — le résultat vaut plus que le coût de production

### Candidats recommandés

| Option | Produit | Briques utilisées | Temps | Pourquoi |
|--------|---------|-------------------|-------|----------|
| **A** | Data API niche | D (scraping) + B (LLM) + A (x402) | 2-3j | Meilleur ratio valeur/effort. Les agents paient pour des données structurées qu'ils ne peuvent pas obtenir eux-mêmes. |
| **B** | Markdown conversion API | I (markdown) + A (x402) | 1j | Le plus rapide à déployer. Les agents IA ont besoin de Markdown propre pour ingérer du contenu. |
| **C** | Synthetic dataset | E (R2) + A (x402) | 1-2j | Tu produis une fois, tu vends plusieurs fois. Le plus scalable. |

### Comment choisir
Pose-toi ces 3 questions :
1. **Quelle donnée ou transformation un agent IA pourrait-il payer pour obtenir sans effort ?**
2. **Quelle source de données ou quel type de document connais-tu bien ?**
3. **Quel format de sortie serait le plus utile pour un pipeline RAG ou un agent ?**

### Livrable de Phase 0
- Une description du produit en 1 phrase
- L'endpoint principal (ex: `POST /api/extract-company-data`)
- Le prix par requête (ex: 0.005 USDC)
- L'input et l'output attendus

---

## PHASE 1 — Premier produit déployé

### Objectif
Déployer un seul produit vertical fonctionnel, avec paywall x402 inline, agent discovery, et validation complète.

### Sous-roadmap Phase 1

#### 1.1 — Setup du workspace (30 min)

```bash
mkdir cloudflare-monetization && cd cloudflare-monetization
npm init -y
git init
```

Créer `.gitignore` :
```gitignore
node_modules/
.wrangler/
.dev.vars
dist/
.env
*.log
.DS_Store
```

Créer la structure minimale :
```
cloudflare-monetization/
├── CLAUDE.md
├── PLAN-PROJET.md
├── ROADMAP.md
├── .gitignore
├── package.json
└── products/
    └── p1-<nom-produit>/
        ├── wrangler.jsonc
        ├── src/
        │   └── index.ts
        ├── agent.json
        ├── llms.txt
        └── package.json
```

> **Ne crée PAS** `shared/`, `scripts/`, `docs/` — ils viendront quand nécessaires.

#### 1.2 — Développer le produit (1-2 jours)

Suivre le code de la brique correspondante dans `PLAN-PROJET.md` :
- Si produit = Data API → Briques D + B + A
- Si produit = Markdown conversion → Briques I + A
- Si produit = Synthetic dataset → Briques E + A

**Le paywall x402 est inline** dans le Worker (pas de gateway séparé) :

```typescript
// Pattern : x402 inline via x402-hono
import { Hono } from "hono";
import { x402Middleware } from "x402-hono";

const app = new Hono<{ Bindings: Env }>();

app.use("/api/*", x402Middleware({
  payTo: (c) => c.env.PAY_TO,
  amount: (c) => "0.005",
  network: "base",
}));

app.post("/api/endpoint", async (c) => {
  // Logique du produit
});

export default app;
```

**Le pricing est hardcodé** — pas de pricing engine.

#### 1.3 — Agent discovery (30 min)

Créer `agent.json` à la racine du produit :

```json
{
  "name": "nom-du-produit",
  "version": "1.0.0",
  "description": "Description en une phrase",
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

Créer `llms.txt` à la racine du produit :

```markdown
# Nom du produit

> Description courte

## Payment

Ce service utilise le protocole x402. Chaque requête requiert un paiement de 0.005 USDC sur Base.

## Endpoints

### POST /api/endpoint

Description.

Input: { "query": "string" }
Output: { "result": "string" }

## Usage

1. Envoyer une requête sans paiement → recevoir 402
2. Payer 0.005 USDC sur Base à l'adresse indiquée
3. Renvoyer la requête avec le credential de paiement
4. Recevoir la réponse
```

#### 1.4 — Test local (30 min)

```bash
cd products/p1-<nom-produit>
npm install
npx wrangler dev
```

Tester :
```bash
# Health check
curl -i http://localhost:8787/

# Test 402
curl -i http://localhost:8787/api/endpoint

# Agent discovery
curl http://localhost:8787/agent.json
curl http://localhost:8787/llms.txt
```

#### 1.5 — Configurer les secrets (10 min)

```bash
npx wrangler secret put JWT_SECRET
# → openssl rand -base64 32

npx wrangler secret put MPP_SECRET_KEY
# → Clé du facilitator MPP

# Si R2 :
npx wrangler secret put R2_ACCESS_KEY_ID
npx wrangler secret put R2_SECRET_ACCESS_KEY
```

#### 1.6 — Déployer (5 min)

```bash
npx wrangler deploy
```

#### 1.7 — Validation post-déploiement (30 min)

Exécuter la checklist :

- [ ] `curl -i https://<WORKER_URL>/` → réponse valide
- [ ] `curl -i https://<WORKER_URL>/api/endpoint` → 402 + `WWW-Authenticate: Payment`
- [ ] `curl https://<WORKER_URL>/agent.json` → JSON valide
- [ ] `curl https://<WORKER_URL>/llms.txt` → texte lisible
- [ ] `npx wrangler tail` → pas d'erreur CPU/subrequest/1027
- [ ] Dashboard → Metrics → Requests/day < 100 000
- [ ] Test avec un vrai paiement (client x402/MPP) → 200 + contenu
- [ ] BaseScan → adresse PAY_TO → transaction visible (après paiement réel)

### Livrable de Phase 1
- Un produit vertical déployé et fonctionnel
- Paywall x402 actif
- Agent discovery (agent.json + llms.txt) accessible
- Premier paiement reçu (ou au moins un test de paiement validé)

---

## PHASE 1.5 — Produits légers en parallèle (décision Fondateur 2026-09-07)

### Objectif
Abroge "un produit à la fois" pour les produits qui ne consomment **ni Workers AI ni Browser
Rendering** — ces deux quotas sont globaux/partagés (`CLAUDE.md` § Limites Free Tier), donc le
seul vrai risque de parallélisation. Un produit CPU-only (`fetch()` + `HTMLRewriter` + KV) ne
retire rien à `markdown-x402`. Origine : brainstorm ChatGPT (10 idées) du 2026-09-07, filtré ici
sur ce seul critère technique — 4 des 10 idées (Website Intelligence, Company Intelligence,
Screenshot/Visual, Research mini-report) nécessitent IA/Browser et sont donc reportées en Phase 6
(après signal d'usage sur `markdown-x402`), pas abandonnées.

### Candidats retenus (aucun ne touche Workers AI ni Browser Run)

| # | Produit | Endpoint | Prix | Implémentation |
|---|---------|----------|------|-----------------|
| p2 | Domain Intelligence | `POST /lookup` | $0.006 | RDAP (bootstrap public) + DNS-over-HTTPS pour age/registrar/DNS/MX — zéro clé API |
| p3 | Trust/Risk Score | `POST /score` | $0.005 | Scoring par règles : age domaine (RDAP), HTTPS, TLD suspect, blocklist statique — pas de modèle |
| p4 | SEO Audit (basique) | `POST /audit` | $0.01 | `HTMLRewriter` natif Workers : title/meta/canonical/robots/schema.org/sitemap — pas de parsing DOM externe |
| p5 | Web Change Detection | `POST /watch` + `POST /check` | $0.005/check | Snapshot hash en KV, diff texte simple au check suivant |
| p6 | Web Actions (bundle) | `/fetch`, `/extract-text`, `/extract-links`, `/check-url` | $0.001–0.002/appel | 4 endpoints atomiques, un seul Worker — composable par un agent |

Bonus optionnel (non prioritaire) : Decision API (`POST /decide`, scoring pondéré sur options
fournies par l'agent, $0.01–0.05) — même famille CPU-only, à ajouter seulement si un des 5
ci-dessus montre un signal.

### Candidats additionnels (source : recherche écosystème Cloudflare, 2026-09-11)

Issus de la veille `opportunity-scout` sur les nouveautés Cloudflare 2026 (Agents Week août 2026,
quotas Durable Objects/Worker) — détail complet en mémoire (`reference_cloudflare_ecosystem_research_0911`).
Même critère que ci-dessus : zéro Workers AI, zéro Browser Rendering, donc pas de gate séquentiel.

| # | Produit | Endpoint | Prix | Implémentation |
|---|---------|----------|------|-----------------|
| p7 | x402 Replay-Guard | `POST /v1/nonce/check-and-consume` | $0.001–0.002 | Registre exactement-une-fois de nonces/receipts de paiement x402 pour un vendeur x402 tiers, sur **Durable Objects SQLite** (gratuit depuis 2025-04-07, cohérence forte non disponible via KV) — évite à ce vendeur de rejouer/double-encaisser une preuve de paiement |
| p8 | Bot/Agent Identity Verification API | `GET /v1/verify?ip=&ua=` | $0.001–0.003 | Proxy `fetch()` + cache KV vers le registre Radar Verified Bots (catégories Direct/Intermediary depuis 2026-07-01), pour des sites tiers non protégés par Cloudflare qui n'ont ni compte ni token Radar |

**Note technique (p7)** : les quotas Durable Objects SQLite (100 000 req/jour, 313 000 GB-s/jour
compute, 1,25M row-reads/jour, 100 000 row-writes/jour — bien au-dessus de la limite KV
1000 writes/jour) sont déjà référencés dans `PLAN-PROJET.md` §2 et Règles critiques #5. Il manque
seulement une section "Brique — Durable Objects" en bonne et due forme (code, `wrangler.jsonc`,
pattern de déploiement, comme les Briques A-M) — différé à l'activation réelle de p7, cohérent
avec la règle "ne pas créer la structure de modules qui ne seront pas déployés".

**Candidat écarté de cette liste** : MCP Traffic Classifier (règles statiques sur en-têtes
`Mcp-*`/JSON-RPC) — même recherche, mais demande jugée spéculative (aucun signal de marché
confirmé) ; à ne développer qu'en prototype rapide si un signal apparaît, pas en tant que produit
Phase 1.5 planifié.

### Candidats additionnels (source : synthèse de recherches externes ChatGPT/Gemini, 2026-09-12)

Détail complet + critique en mémoire (`reference_agent_gate_products_research_0912`). Même critère
que ci-dessus : zéro Workers AI, zéro Browser Rendering. Différence de nature avec p1-p4 : ce sont
des produits de **vérification avant action** (un agent paie pour un verdict avant d'agir), pas des
lookups de données — catégorie de demande potentiellement différente de celle testée jusqu'ici.

| # | Produit | Endpoint | Prix | Implémentation |
|---|---------|----------|------|-----------------|
| p9 | Agent Supply-Chain Gate | `POST /v1/lockfile/verify` | $0.02–0.05 | Analyse déterministe d'un lockfile npm (`package-lock.json`/`pnpm-lock.yaml`) fourni par un agent avant installation : dépendances Git inattendues, registry non autorisée, intégrité SHA absente/incohérente, versions dupliquées — verdict JSON, aucun LLM |
| p10 | MCP Tool Risk Gate | `POST /v1/mcp/tools/lint` | $0.01–0.05 | Analyse déterministe d'un `tools/list`/server card MCP : outils destructifs sans annotation, schémas trop permissifs (`additionalProperties`, pas de `maxItems`/longueur max), absence d'`outputSchema` — verdict JSON, aucun LLM |

**Explicitement non activés maintenant** — recommandation croisée des deux sources externes ET de
`monetization-strategist` : construire un 5e/6e produit ne répond pas à la question ouverte
("pourquoi 0 transaction sur p1-p4"), ça la contourne. À reconsidérer seulement si la mesure
Phase 2 (relancée le 12/09 après-midi) confirme un vrai problème de catégorie de demande plutôt
qu'un problème de distribution/fiabilité opérationnelle.

### Règle d'exécution
- Même checklist que Phase 1.7 pour chacun (402, agent.json, llms.txt, `wrangler tail` propre)
- Pas de `shared/` — chaque produit reste inline, comme `markdown-x402`
- Un dossier `products/pN-*/` n'est créé qu'au moment de développer CE produit précis (règle de
  création de dossiers inchangée)

### Livrable de Phase 1.5
- 0 à 5 produits légers déployés selon le temps disponible — pas de séquence imposée entre eux
- `markdown-x402` (Phase 2) continue en parallèle sans interférence de quota

### Statut réel (mis à jour 2026-09-08)

Le slot "p2" ci-dessus a été implémenté différemment de ce qui était planifié, et un second
produit est arrivé par un canal hors roadmap (session mobile) :

| Dossier | Produit réel | Endpoint | Prix | Statut |
|---|---|---|---|---|
| `products/p2-domain-parser/` | Parsing TLD/SLD/sous-domaine via Public Suffix List (pas le "Domain Intelligence" prévu ci-dessus) | `POST /v1/domain/parse` | $0.001 | **Déployé, Base mainnet** (voir commit `f208ec1`) |
| `products/p3-domain-intelligence/` | DNS/RDAP/TLS lookups + MCP — réalise la vraie idée "p2 Domain Intelligence" ci-dessus, en plus complet (ajoute TLS, MCP, Analytics Engine) | `GET /dns`, `/rdap`, `/tls`, `/intelligence` (+ `/normalize`, `/validate` gratuits) | $0.001–0.002 | **Déployé, Base mainnet** — les 4 routes payantes validées de bout en bout sur testnet (règlement on-chain vérifié indépendamment pour chacune) avant bascule le 08/09 (voir `.claude/context/testnet-verified-p3-domain-intelligence.md`) |
| `products/p4-email-verification/` | Validation d'email : syntaxe, résolution MX, détection domaine disposable | `POST /verify` | $0.002 | **Déployé, Base mainnet** — round-trip testnet validé de bout en bout (règlement on-chain vérifié indépendamment, `eth_getLogs` + diff de solde) avant bascule le 12/09 (voir `.claude/context/testnet-verified-p4-email-verification.md`) |

`products/p3-domain-intelligence/` est passé en `X402_NETWORK: "mainnet"` le 2026-09-08, décision
Fondateur, après validation on-chain indépendante des 4 routes (`dns`/`rdap`/`tls`/`intelligence`).
Facilitator par défaut (`x402.org`, testnet-only) remplacé par `facilitator.0xarchive.io`
(confirmé mainnet, déjà utilisé par p1) via secret `X402_FACILITATOR_URL`. Le prix de `tls`/
`intelligence` reste qualifié de "non final" dans `src/pricing.ts` (mécanisme validé, montant pas
figé formellement).

---

## PHASE 2 — Validation du revenu

### Objectif
Confirmer que le produit génère du revenu réel. Pas du revenu théorique — du revenu réel.

### Sous-roadmap Phase 2

#### 2.1 — Distribuer le service (1-2 jours)

- Publier `agent.json` et `llms.txt` sur des forums/communautés d'agents IA
- Contacter des développeurs d'agents IA qui pourraient avoir besoin du service
- Tester avec un agent IA réel (ex: un agent qui consomme l'API)

#### 2.2 — Mesurer (1 jour)

```bash
npx wrangler tail
# Compter :
# - Nombre de 402 (challenges émis)
# - Nombre de 200 après paiement
# - Revenu total (200 × prix)
```

#### 2.3 — Décision (1 jour)

| Résultat | Action |
|----------|--------|
| 0 paiement en 3 jours | Changer de produit ou de niche. Retour Phase 0. |
| 1-5 paiements | Optimiser : prix, description, distribution. Continuer. |
| 5+ paiements | Validé. Passer Phase 3. |

### Livrable de Phase 2
- Soit : validation que le modèle génère du revenu → Phase 3
- Soit : pivot vers un autre produit → retour Phase 0

---

## PHASE 3 — Extraction shared layer

### Objectif
Maintenant que tu as 1 produit validé et que tu vas en ajouter un 2e, extraire l'infrastructure partagée.

### Prérequis
- Phase 2 validée (5+ paiements ou décision de continuer)
- Intention de créer un 2e produit

### Sous-roadmap Phase 3

#### 3.1 — Créer `shared/` (2-3h)

```
shared/
├── payments/
│   └── x402.ts          # Middleware x402 réutilisable
├── pricing/
│   └── catalog.ts       # Catalogue des prix
├── discovery/
│   ├── agent.json       # Template
│   └── llms.txt         # Template
├── auth/
│   ├── jwt.ts           # Vérification JWT
│   └── api-key.ts       # Vérification API key
└── types/
    └── env.ts           # Types d'environnement
```

#### 3.2 — Refactoriser le produit 1 (2-3h)

- Extraire le paywall x402 → `shared/payments/x402.ts`
- Extraire le pricing → `shared/pricing/catalog.ts`
- Extraire l'agent discovery → `shared/discovery/`
- Le produit 1 importe depuis `shared/`

#### 3.3 — Valider le refactor (1h)

```bash
cd products/p1-*
npx wrangler deploy
# Re-exécuter la checklist de validation
```

### Livrable de Phase 3
- `shared/` créé et fonctionnel
- Produit 1 refactorisé pour utiliser `shared/`
- Aucune régression (mêmes réponses, mêmes paiements)

---

## PHASE 4 — Deuxième produit

### Objectif
Déployer un 2e produit vertical en réutilisant la shared layer.

### Sous-roadmap Phase 4

#### 4.1 — Choisir le 2e produit (1 jour)

Candidats (selon ce qui complète le produit 1) :
- Si produit 1 = Data API → produit 2 = Markdown conversion ou Synthetic dataset
- Si produit 1 = Markdown conversion → produit 2 = Data API ou AI Search
- Si produit 1 = Synthetic dataset → produit 2 = Data API ou Markdown conversion

#### 4.2 — Développer (1-2 jours)

```
products/p2-<nom>/
├── wrangler.jsonc
├── src/
│   └── index.ts         # Importe depuis shared/
├── agent.json
├── llms.txt
└── package.json
```

#### 4.3 — Déployer et valider (30 min)

Même checklist que Phase 1.7.

### Livrable de Phase 4
- 2 produits verticaux déployés
- Shared layer réutilisée
- 2 sources de revenu indépendantes

---

## PHASE 5 — AI Search (si corpus disponible)

### Objectif
Ajouter AI Search si tu as un corpus de données réellement utile.

### Prérequis
- Un corpus de données niche (documents, pages web, datasets)
- Le corpus doit être valuable pour des agents IA

### Sous-roadmap Phase 5

#### 5.1 — Créer l'instance AI Search (30 min)
Dashboard → AI Search → Créer une instance

#### 5.2 — Indexer le corpus (1-2 jours)
Utiliser Brique I (Markdown) + Brique D (Browser Run) pour alimenter l'index

#### 5.3 — Déployer le Worker AI Search (2h)
Voir Brique J dans `PLAN-PROJET.md`

#### 5.4 — Valider (30 min)
Même checklist + vérifier que les résultats de recherche sont pertinents

### Livrable de Phase 5
- Service AI Search déployé
- Corpus indexé et searchable
- Revenu récurrent si le corpus est valuable

---

## PHASE 6 — Briques niche

### Objectif
Activer les briques C (image), G (TTS/ASR), H (translation) **uniquement si un cas d'usage vertical justifie leur activation**.

### Idées IA/Browser-intensives différées de Phase 1.5 (brainstorm ChatGPT 2026-09-07)
Reportées ici car elles consomment Neurons/Browser Run globaux — à activer seulement après signal
d'usage confirmé sur `markdown-x402` (Phase 2), pour ne pas cannibaliser son budget :
- **Website Intelligence** (analyse business/tech d'un site, $0.01–0.05) — nécessite LLM
- **Company/Business Intelligence** (enrichissement entreprise, $0.01–0.05) — nécessite LLM
- **Visual/Screenshot Analysis** (design/UX via vision model, $0.02–0.20) — Browser Run + vision
- **Research mini-report** (recherche multi-source résumée, $0.03–0.50) — LLM + recherche externe

### Règle
Ne pas déployer une brique "au cas où". Chaque brique doit répondre à un besoin d'un produit ou d'un client.

### Sous-roadmap Phase 6

#### 6.1 — Image generation (si besoin)
- Produit vertical : `POST /api/product-image`, `POST /api/ad-creative`
- Brique C + LLM (prompt engineering) + R2 (stockage) + x402
- Temps : 1 jour

#### 6.2 — TTS/ASR (si besoin)
- Produit vertical : `POST /api/voice-note`, `POST /api/meeting-summary`
- Brique G + LLM (analyse) + x402
- Temps : 1 jour

#### 6.3 — Translation (si besoin)
- Produit vertical : `POST /api/multilingual-data`
- Brique H + autres services + x402
- Temps : 1 jour

### Livrable de Phase 6
- Chaque brique activée a un produit vertical et un cas d'usage justifié

---

## PHASE 7 — Stream / Pay Per Crawl

### Objectif
Activer les briques dormantes uniquement si une opportunité concrète se présente.

### Brique F — Stream
- **Statut** : DORMANT
- **Activer si** : tu as du contenu vidéo premium que des agents ou des utilisateurs veulent payer
- **Temps** : 1 jour

### Brique M — Pay Per Crawl
- **Statut** : WATCH
- **Activer si** : Cloudflare ouvre la bêta à ton compte ET les payouts deviennent compatibles (non-Stripe ou Stripe acceptable pour toi)
- **Temps** : 10 min (dashboard uniquement)
- **Inscription** : cloudflare.com/paypercrawl-signup

---

## MATRICE DES STATUTS

| Brique | Statut | Phase | Priorité |
|--------|--------|-------|----------|
| A. x402/MPP | **CORE** | Phase 1 | 10/10 |
| B. LLM | **BUILD NOW** | Phase 1 (si Data API) | 8.5/10 |
| I. Markdown | **BUILD NOW** | Phase 1 (si Markdown API) | 8/10 |
| E. R2 | **BUILD NOW** | Phase 1 (si dataset) | 9/10 |
| D. Scraping | **CONDITIONAL** | Phase 1 (si Data API) | 7/10 |
| J. AI Search | **AFTER DATA** | Phase 5 | 8.5/10 |
| K. API keys | **INFRA** | Phase 3+ | 8/10 |
| L. JWT | **ADMIN** | Phase 3+ | 8/10 |
| C. Image | **CONDITIONAL** | Phase 6 | 6/10 |
| G. TTS/ASR | **CONDITIONAL** | Phase 6 | 5.5/10 |
| H. Translation | **CONDITIONAL** | Phase 6 | 4.5/10 |
| F. Stream | **DORMANT** | Phase 7 | 2/10 |
| M. Pay Per Crawl | **WATCH** | Phase 7 | 1/10 |
| Gateway partagé | **PHASE 3** | Phase 3 | — |
| Pricing engine | **PHASE 3** | Phase 3 | — |
| D1 metering | **PHASE 4+** | Phase 4+ | — |

---

## CHECKLIST DE VALIDATION PAR PHASE

### Phase 0
- [x] Produit choisi en 1 phrase — candidat B : conversion Markdown structurée (URL/PDF/HTML/image), différenciée par x402 comme distribution agent-native (zéro compte, zéro clé API) plutôt que par la qualité de conversion
- [x] Endpoint principal défini — `POST /convert`
- [x] Prix par requête défini — 0,005 USDC (grille "Transformation", `base-sepolia` en test)
- [x] Input/output définis — JSON `{url}` ou `multipart/form-data` (`document`) → JSON structuré (title, sections, word_count, neuron_tokens, markdown)

### Phase 1
- [x] Workspace créé — `products/p1-markdown-x402/`
- [x] Produit développé (code + wrangler.jsonc) — `src/index.ts` (Hono + `x402-hono` réel, `env.AI.toMarkdown()`)
- [x] agent.json créé
- [x] llms.txt créé
- [x] Test local validé (402, agent.json, llms.txt — le 200 nécessite un vrai paiement testnet, pas encore fait)
- [x] Secrets configurés — aucun requis (facilitator public `x402.org`, `PAY_TO` en `vars` seulement)
- [x] Déployé — https://markdown-x402.nordman-tehau.workers.dev (Base **mainnet**, `eip155:8453`, facilitator `facilitator.0xarchive.io`)
- [x] Checklist post-déploiement validée — health check, 402, `agent.json`/`llms.txt`, paiement testnet de bout en bout vérifié (preuve `.claude/context/testnet-verified.md`) puis bascule mainnet. Reste : premier paiement **mainnet** externe réel (Phase 2)

### Phase 2
- [x] Service distribué — canal automatique uniquement (décision Fondateur 08/09 : pas de contact humain pour l'instant) : `/.well-known/x402` sur les 3 produits + listage sur l'annuaire tiers agent-tools.cloud (p1 auto-crawlé, p2/p3 dns-rdap-tls + MCP p3 soumis, `p3/intelligence` en attente de rate limit) + skill agent installable `skills/x402-data-apis` (aussi publié séparément : [NOVALYTH/x402-data-apis](https://github.com/NOVALYTH/x402-data-apis), commit `68a1a93` du 08/09) documentant les 3 APIs. Pas de forums/communautés (hors scope de la décision actuelle).
- [x] Mesure du nombre de 402 et de 200 — mesuré 18/09 sur fenêtre 72h (15-18/09), sources croisées GraphQL Analytics Cloudflare + D1 `onchain_settlements` + KV cache p3 (détail en mémoire `project_2026-09-18_phase2_measurement_conversion`) : ~450-825 req/j/produit (réel, pas un artefact), 402 fonctionnellement émis sur les 4 (vérifié en direct), **zéro conversion externe confirmée sur 72h** malgré ce volume (KV cache p3 vide depuis ≥3-7j, D1 partagé = 6 règlements lifetime dont 5 wallet-test-fondateur + 1 transfert $2 hors-flux x402 déjà classé bruit). Répartition exacte 402-jamais-émis vs 402-jamais-payés indéterminée (pas de champ path/status dans l'API Analytics utilisée, `/stats` p3 bloqué par secret write-only) — mais la conclusion "conversion fantôme" tient quelle que soit cette répartition.
- [x] Décision prise — règle §2.3 déclenchée (0 paiement, largement >3j sur les 4 produits) : **pivot / retour Phase 0**. Pas de 5e produit (explicitement écarté 12/09, esquiverait la question). Diagnostic transversal déjà public côté fondateur (article dev.to 16/09) : signal de demande de marché, pas un problème technique ou de distribution (paywall vérifié fonctionnel, visibilité résolue sur 3 canaux indépendants). Les 4 produits restent en prod ($0 coût de maintien) ; prochaine étape = re-choisir la niche/catégorie de demande, pas re-coder la même catégorie.

### Phase 3
- [ ] `shared/` créé
- [ ] Produit 1 refactorisé
- [ ] Aucune régression

### Phase 4
- [ ] Produit 2 choisi
- [ ] Produit 2 développé (avec shared/)
- [ ] Produit 2 déployé et validé

### Phase 5
- [ ] Instance AI Search créée
- [ ] Corpus indexé
- [ ] Worker AI Search déployé
- [ ] Résultats pertinents

### Phase 6
- [ ] Chaque brique activée a un produit vertical justifié

---

## SUIVI DES MÉTRIQUES

### Métriques à suivre (Phase 1-2)
Avant D1 metering, utiliser `wrangler tail` + `console.log` :

```typescript
// Dans le Worker
console.log(JSON.stringify({
  ts: Date.now(),
  endpoint: url.pathname,
  status: response.status,
  paid: response.status === 200,
  amount: "0.005",
}));
```

### Métriques à suivre (Phase 4+)
Avec D1 metering (voir `PLAN-PROJET.md` → Metering) :
- Requests/day par endpoint
- 402 vs 200 ratio
- Revenue/day
- CPU time moyen
- AI Neurons consommés
- Browser Run minutes consommées

### Tableau de bord (manuel, Phase 1-2)
| Date | 402 émis | 200 après paiement | Revenu USDC | Notes |
|------|----------|-------------------|-------------|-------|
| 2026-09-18 | vérifié fonctionnel sur les 4 (curl direct), volume exact non isolable (~450-825 req/j/produit tous endpoints confondus, API Analytics sans champ path) | 0 externe / 72h (5 fondateur + 1 hors-flux x402 sur lifetime complet, 6 lignes D1) | $0 externe | Mesure croisée GraphQL Analytics + D1 `onchain_settlements` + KV cache p3 — voir Phase 2 checklist ci-dessus |
| | | | | |
| | | | | |
