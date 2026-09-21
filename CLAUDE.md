@../_metahub/PROFILE.md

# CLAUDE.md — Directives pour Claude Code

> **Ce fichier est lu automatiquement par Claude Code au démarrage d'une session.**
> Il définit le contexte, les règles, les limites et la philosophie du projet.

---

## PROJET

**Nom** : cloudflare-monetization
**Objectif** : Plateforme agent-first de micro-services de données monétisés en USDC/x402 sur Cloudflare Free Tier.
**Coût infra** : $0/mois
**Dev** : Solo, urgence financière, besoin de revenu rapide.
**Runtime** : Cloudflare Workers (Free Tier) + Workers AI + R2 + Browser Run + KV + D1

---

## RÈGLES ABSOLUES

### Sécurité
- **JAMAIS** de clé privée blockchain dans un Worker
- **JAMAIS** de signature de transaction on-chain dans un Worker
- **JAMAIS** de seed phrase dans le code, les secrets, ou les variables d'env
- **JAMAIS** hardcoder un secret dans `wrangler.jsonc` — utiliser `wrangler secret put`
- Le Worker ne fait que du I/O (fetch, verify, proxy) — pas de crypto lourde
- Les règles ci-dessus (secrets, clé privée) sont aussi appliquées mécaniquement par le hook `PreToolUse` `.claude/hooks/compliance-gate.py` sur Write/Edit des fichiers de config Wrangler, qui exige en plus `.claude/context/testnet-verified.md` avant toute bascule testnet→mainnet

### Limites Free Tier (non-négociables)
- **10 ms CPU** par requête HTTP — le I/O (`fetch()`) ne compte PAS
- **100 000 requêtes/jour** par Worker
- **50 subrequests** par requête
- **10 000 Neurons/jour** Workers AI (GLOBAL, partagé entre tous les Workers)
- **10 min/jour** Browser Run (GLOBAL)
- **1 000 writes/jour** KV par namespace
- **128 MB** mémoire par Worker
- **64 MiB** taille Worker non compressé (relevé le 2026-09-04, avant : 3MB compressé)

### Philosophie produit (révisée 2026-09-07 — décision Fondateur)
- **"Un produit à la fois" est abrogée et remplacée par une règle plus précise** : la contrainte n'était pas le nombre de produits, c'était la contention sur les quotas Free Tier GLOBAUX (Neurons, Browser Run). Donc :
  - **Produits légers (CPU/`fetch()`/KV uniquement, zéro Workers AI, zéro Browser Rendering)** : autant en parallèle que voulu, pas de gate séquentiel.
  - **Produits IA-intensifs ou Browser-Rendering-intensifs** : un seul à la fois tant que le produit IA en cours (`markdown-x402`) n'a pas de signal d'usage validé (cf. `ROADMAP.md` Phase 2) — ces deux quotas sont partagés par tout le compte, un 2e produit qui les consomme cannibalise directement le premier.
- **Revenu avant infrastructure** — reste vrai : chaque produit garde son paywall inline, pas de shared layer avant 2+ produits qui *génèrent* du revenu (pas juste qui existent).
- **Verticaliser, pas cloner** — vendre un résultat, pas du compute générique
- **x402 est le mécanisme de paiement, pas le business**
- **Agent-first** — les services doivent être découvrables par les agents IA (agent.json, llms.txt)

### Ce que Claude Code ne doit PAS faire
- Ne pas créer de gateway partagé avant d'avoir 2+ produits qui génèrent du revenu (existence seule ne suffit pas)
- Ne pas créer de pricing engine avant d'avoir 1 produit qui génère du revenu
- Ne pas créer de D1 metering avant d'avoir du volume
- Ne pas créer la structure de modules qui ne seront pas déployés
- Ne pas ajouter de logique PoW dans les Workers
- Ne pas utiliser de modèles Workers AI nécessitant le plan Paid
- Ne pas dépasser 50 subrequests par requête
- Ne pas modifier le code d'un module sans comprendre l'impact sur les limites
- **Ne pas déployer un 2e produit Workers AI/Browser Rendering avant signal d'usage sur le 1er** (seule survivance de l'ancienne règle "un produit à la fois", justifiée par le quota global — pas une limite arbitraire)

---

## STRUCTURE DU WORKSPACE

```
cloudflare-monetization/
├── CLAUDE.md                    # Ce fichier
├── PLAN-PROJET.md               # Référence technique (catalogue de briques)
├── ROADMAP.md                   # Plan d'exécution (produit-par-produit)
├── README.md
├── .gitignore
│
├── products/                    # Produits verticaux (un dossier par produit)
│   ├── p1-markdown-x402/        # Produit 1 — IA-intensif (Workers AI), gate sequentiel actif
│   └── p2../p3../...            # Produits legers (sans IA/Browser) — paralleles, pas de gate
│       ├── wrangler.jsonc
│       ├── src/
│       │   └── index.ts
│       ├── agent.json           # Discovery pour agents IA
│       ├── llms.txt             # Documentation lisible par les LLMs
│       └── package.json
│
├── shared/                     # Infrastructure partagée (créée en Phase 3+)
│   ├── payments/
│   ├── pricing/
│   ├── discovery/
│   └── types/
│
├── scripts/
│   ├── deploy.sh
│   ├── validate.sh
│   └── gen-secret.sh
│
├── docs/superpowers/{plans,specs}/  # Plans/specs superpowers (existant, pas un guide mpp-proxy)
│
└── skills/x402-data-apis/       # Skill agent installable (existant, publié aussi séparément
                                  # sur NOVALYTH/x402-data-apis) — distribution, pas un skill
                                  # Claude Code pour cette session (ceux-là sont dans
                                  # .claude/skills/ et le plugin cloudflare@cloudflare)
```

### Règle de création de dossiers
- **Ne crée un dossier que quand tu déploies le module correspondant**
- Un dossier vide = distraction mentale
- `shared/` n'est créé qu'en Phase 3 (quand 2+ produits existent)

---

## MODÈLES WORKERS AI

Catalogue complet des modèles gratuits → `.claude/context/references.md` (à consulter à la demande).

### Modèles Paid (NE PAS UTILISER sur Free)
- `@cf/moonshotai/kimi-k2.6`, `kimi-k2.7-code`
- `@cf/zai-org/glm-5.2`, `glm-5.3`, `glm-5.3-flash`
- `@cf/deepseek-ai/deepseek-v4-flash-0731`, `deepseek-v4-pro-0813`

---

## COMMANDES UNIVERSELLES

```bash
# Développer un produit
cd products/p1-*
npx wrangler dev

# Déployer un produit
cd products/p1-*
npx wrangler deploy

# Configurer un secret
npx wrangler secret put SECRET_NAME

# Surveiller les logs
npx wrangler tail

# Health check
curl -i https://<WORKER_URL>/

# Test 402
curl -i https://<WORKER_URL>/api/endpoint
```

---

## WORKFLOW DE DÉVELOPPEMENT

> Avant de commencer : consulter `.claude/context/errors.md` (pièges Cloudflare/Wrangler déjà rencontrés).

1. Lire `ROADMAP.md` pour connaître la phase actuelle
2. Lire `PLAN-PROJET.md` pour les détails techniques de la brique à utiliser
3. Créer le dossier du produit sous `products/`
4. Écrire `wrangler.jsonc`, `src/index.ts`, `agent.json`, `llms.txt`
5. `npm install` → `npx wrangler dev` (test local)
6. Configurer les secrets
7. `npx wrangler deploy`
8. Exécuter la checklist de validation du `ROADMAP.md`
9. Mettre à jour le statut dans `ROADMAP.md`

---

## RÉFÉRENCES

Catalogue complet des modèles Workers AI gratuits + liens de référence Cloudflare → `.claude/context/references.md` (à consulter à la demande, pas chargé au démarrage).

## Gouvernance

Modèle hérité de `_metahub` : Fondateur = utilisateur (arbitrage business/stratégique, jamais
délégué à un agent) ; cette session = responsable BU, autorité technique complète sur ce projet.
Détail du modèle et du protocole de rapport `_metahub` → `ARCHITECTURE.md` (entrée 2026-08-30).

## Sous-agents disponibles (`.claude/agents/`)
8 agents de process/gouvernance — invoque-les quand leur périmètre correspond à la tâche en cours :
- `architect` — cohérence structure workspace
- `cloudflare-ops` — Wrangler, bindings, quotas, déploiement
- `x402-payments` — paywall x402, secrets, bascule testnet→mainnet
- `security-auditor` — secrets, permissions tokens, surfaces API
- `testing` — Vitest/Miniflare, checklist de validation
- `monetization-strategist` — décision d'activation de module selon signal de revenu
- `query-analyst` — analyse trafic réel (KV/wrangler tail/annuaires tiers), intégrité paywall
- `opportunity-scout` — veille marché/écosystème, propose des candidats produit (jamais d'activation)

Grille de lecture "Agentic Revenue Architect" (classement de ces agents par compétence) et
historique des corrections apportées → `ARCHITECTURE.md` (entrées 2026-09-07 et 2026-09-06/09).

## Skills Cloudflare officielles

Plugin `cloudflare@cloudflare` installé en scope **projet** (2026-09-11, versionné dans
`.claude/settings.json`) : 14 skills (`wrangler`, `durable-objects`, `workers-best-practices`,
`agents-sdk`, etc.) — complémentaires aux agents locaux ci-dessus (agents = process du projet,
skills = état de l'art technique Cloudflare), pas un remplacement. En cas de doute sur une syntaxe
wrangler/binding récente, invoquer la skill correspondante avant de se fier à la mémoire du
modèle. Détail complet → mémoire `reference_cloudflare_tooling_workspace_setup_0911`.

## Persistance de session

Pas de `context/progress.md` — ce rôle est rempli par `EXECUTIVE_SUMMARY.md` (statut projet) plus
la mémoire cross-session Claude. Ne pas créer `progress.md` en plus (doublon).

## Fin de session
Si le statut, le blocage ou la prochaine action du projet a changé pendant
cette session, propose à l'utilisateur de lancer /update-summary avant de clore.
