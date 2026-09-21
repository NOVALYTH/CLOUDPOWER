# Design — p4-email-verification

**Date** : 2026-09-10
**Statut** : approuvé par l'utilisateur (chat), en attente de revue de cette fiche avant plan d'exécution.

## Contexte

Candidat "vérification email" (léger, réutilise le module DNS de `p3-domain-intelligence`) — verdict
ACTIVER du `monetization-strategist` depuis le 2026-09-09, jamais commencé (l'audit opérationnel puis
le funnel/dashboard de paiement ont pris la priorité, voir `EXECUTIVE_SUMMARY.md`). C'est un produit
Free Tier CPU-only (aucun Workers AI, aucun Browser Rendering) — pas de gate séquentiel selon la
philosophie produit révisée (`CLAUDE.md` §Philosophie produit).

Ce candidat est aussi le 4e produit du portfolio. `ARCHITECTURE.md` (entrée du 2026-09-08) avait
explicitement signalé un point ouvert : aucune convention commune n'a jamais été tranchée entre le
patron monolithique de p1/p2 (un seul `src/index.ts`) et le patron modulaire de p3 (`http/`,
`engine/`, `adapters/`, tests Vitest, MCP) — "à trancher avant un 4e produit". Ce design tranche ce
point en même temps que le design de p4 lui-même (décision Fondateur, voir §Portfolio ci-dessous).

## Périmètre

**Dans le périmètre** :
1. Nouveau produit `products/p4-email-verification/` (Worker isolé, monolithique)
2. Endpoint payant unique `POST /verify` — syntaxe + MX + détection domaine jetable
3. Discovery : `agent.json`, `llms.txt`, `/.well-known/x402`
4. x402 v2 inline (`@x402/hono`), facilitator PayAI, réseau Base — **testnet d'abord**
   (`base-sepolia`), bascule mainnet seulement après round-trip vérifié
5. Tests Vitest sur la logique pure (syntaxe, classification risk, lookup jetable)
6. Décision portfolio : monolithe = patron de référence par défaut (tranchée dans `ARCHITECTURE.md`,
   pas seulement dans ce fichier — voir §Portfolio)

**Explicitement hors périmètre (déferré)** :
- Vérification SMTP (RCPT TO) — écartée : nécessite le TCP Sockets API, risque de greylistage/
  blocage des IP Cloudflare par les serveurs mail tiers, complexité de fiabilisation disproportionnée
  par rapport à la valeur ajoutée sur un candidat non encore validé par le marché
- `shared/` — pas de 2e produit *générant du revenu* à ce jour (`CLAUDE.md` §Philosophie produit)
- Endpoints gratuits type `/normalize` (présents sur p3) — pas nécessaires pour ce produit, un seul
  endpoint payant suffit pour V1
- Mise à jour rétroactive de la structure de p1/p2/p3 pour "confirmer" le monolithe — aucun des trois
  n'est retouché par ce chantier, la décision ne s'applique qu'aux produits futurs

## Portfolio — le monolithe devient le patron de référence

**Décision (Fondateur, 2026-09-10)** : le patron monolithique (p1/p2) devient la convention par
défaut pour les futurs produits légers CPU-only, sauf besoin explicite justifiant l'écart (ex. un
futur produit qui a réellement besoin de plusieurs adaptateurs, d'un serveur MCP, ou d'une suite de
tests significative — comme p3, qui reste un cas particulier justifié rétroactivement, pas remis en
cause). Raison : proportionnalité — la majorité des candidats identifiés à ce jour (cf. `ROADMAP.md`
Phase 1.5, produits légers) sont des transformations simples à un seul endpoint, pour lesquelles la
séparation `http/engine/adapters` de p3 ajoute de la charge cognitive sans bénéfice mesuré. Ceci
referme le point ouvert de l'entrée `ARCHITECTURE.md` du 2026-09-08 ("à trancher avant un 4e
produit").

Cette décision doit être tracée comme entrée **portfolio** dans `ARCHITECTURE.md` (pas seulement
comme un choix local de ce fichier) — voir tâche dédiée dans le plan d'implémentation.

## Composants

### `src/index.ts` (monolithique, patron p1/p2)
- Setup Hono + `x402-hono`/`@x402/hono` (mêmes imports que p2 : `HTTPFacilitatorClient`,
  `registerExactEvmScheme`)
- Route `POST /verify` derrière le paywall x402
- Routes discovery : `GET /agent.json`, `GET /llms.txt`, `GET /.well-known/x402`
- Health check `GET /`

### `src/email.ts` (logique pure, testable sans réseau)
- `parseSyntax(email): { valid: boolean; domain: string | null }` — regex RFC5322-lite
- `classifyRisk(input: { validSyntax, mxFound, disposable }): "low" | "medium" | "high"`
  - `high` si `!validSyntax || !mxFound`
  - `medium` si `disposable`
  - `low` sinon

### `src/dns.ts` (adapté de `p3/src/engine/dns.ts`, réduit au MX)
- `resolveMx(domain, resolver = node:dns.promises): Promise<{ mxFound: boolean; records: string[]; error?: string }>`
- Resolver injectable (même pattern que p3 — `DnsResolver` interface minimale à un seul
  membre `resolveMx`), pour tests déterministes sans réseau réel
- Réutilise le classement d'erreurs `ENOTFOUND`/`ENODATA` = "pas de MX" (pas une erreur) de p3

### `src/data/disposable-domains.ts`
- `export const DISPOSABLE_DOMAINS: ReadonlySet<string>` — snapshot vendorisé d'une liste
  open-source connue (type `disposable-email-domains`, licence permissive), quelques milliers
  d'entrées, générée une fois au moment du développement (pas d'appel réseau à l'exécution)
- `isDisposable(domain: string): boolean`

### `src/pricing.ts`
```ts
export const PRICE_USD = { verify: 0.002 } as const;
```

## Flux de données

```
POST /verify { "email": "..." }
  → [paywall x402 — 402 si pas de paiement valide]
  → parseSyntax(email) → { valid, domain }
  → si domain: resolveMx(domain) → { mxFound, records }
  → isDisposable(domain)
  → classifyRisk(...)
  → 200 { email, valid_syntax, domain, mx_found, mx_records, disposable, risk }
```

## Gestion des erreurs

- Body JSON manquant ou champ `email` absent/non-string → `400` **avant** le paiement (validation
  de requête malformée, pas un résultat métier — même convention que les routes existantes)
- Email syntaxiquement invalide → payé normalement, retourné comme résultat
  (`valid_syntax: false, domain: null, mx_found: false, disposable: false, risk: "high"`), **pas**
  une erreur HTTP
- Échec de résolution DNS réel (timeout, SERVFAIL) → `mx_found: false`, pas d'exception non gérée ;
  le détail de l'erreur n'est pas exposé au client (évite de fuir des détails d'infra), seulement
  loggé côté serveur comme p3 le fait déjà pour `/dns`

## Tests

Vitest, aucun réseau réel :
- `parseSyntax` : cas valides/invalides classiques (manque de `@`, domaine vide, TLD absent, etc.)
- `classifyRisk` : les 3 branches (high/medium/low) + priorité `high` sur `medium` si les deux
  conditions sont vraies
- `resolveMx` : resolver mocké — cas MX trouvés, cas `ENOTFOUND`/`ENODATA` (pas d'erreur), cas
  timeout réel (erreur remontée sans crasher)
- `isDisposable` : domaine connu de la liste, domaine inconnu, casse/normalisation (majuscules)

## Sécurité / conformité `CLAUDE.md`

- Pas de clé privée, pas de signature on-chain, pas de secret en dur — mêmes garde-fous que p1/p2/p3
- Bascule mainnet bloquée par `compliance-gate.py` tant que
  `.claude/context/testnet-verified-p4-email-verification.md` n'existe pas
- Aucun Workers AI, aucun Browser Rendering → pas de gate séquentiel, déployable en parallèle du
  reste

## Hors périmètre de cette fiche (rappel)

- Le choix du nom exact de domaine à vendre/annoncer, la distribution (agent-tools.cloud,
  agent402.tools) suivent le canal automatique déjà en place pour p1/p2/p3, pas re-décrits ici
- Pas de decision sur un prix "final" — $0.002 est un prix de lancement, ajustable après signal
  d'usage comme pour les autres produits
