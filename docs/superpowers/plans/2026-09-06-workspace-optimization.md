# Remise à niveau du workspace `cloudflare-monetization` — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Corriger les fondations du workspace `cloudflare-monetization` (chemins cassés, agent paiement obsolète, CLAUDE.md surchargé, gouvernance non formalisée) et installer le garde-fou mécanique testnet→mainnet signalé comme prioritaire depuis l'onboarding `_metahub` du 05/09 — avant tout skill/agent spécifique à un produit.

**Architecture:** Aucun code produit touché (Phase 0 pas commencée). Uniquement : fichiers `.claude/` (agents, commande, hooks, settings, context), `CLAUDE.md`, `EXECUTIVE_SUMMARY.md`, un nouveau `ARCHITECTURE.md` racine, `.gitignore`, et l'initialisation du dépôt git local. Le seul composant "code" est le hook Python `compliance-gate.py`, testé par un script Python autonome (pas de framework de test — aucun n'existe encore dans ce repo).

**Tech Stack:** Markdown, JSON (`.claude/settings.json`), Python 3 (hook + test), Git, Wrangler (référencé, pas installé/exécuté ici).

**Spec:** [docs/superpowers/specs/2026-09-06-workspace-optimization-design.md](../specs/2026-09-06-workspace-optimization-design.md)

## Global Constraints

- Aucune clé privée blockchain, aucune signature on-chain, jamais dans un Worker ni dans un fichier versionné (spec §4, CLAUDE.md > RÈGLES ABSOLUES > Sécurité).
- Un secret ne va jamais en dur dans `wrangler.jsonc` — `wrangler secret put` en production, `.dev.vars` (gitignored) en local (spec §4).
- Pas de remote git — dépôt local uniquement (décision utilisateur, spec §8).
- `PLAN-PROJET.md` et `ROADMAP.md` restent à la racine — on corrige les références, on ne déplace pas les fichiers (spec, Périmètre).
- La sous-section "Modèles Paid (NE PAS UTILISER sur Free)" reste dans CLAUDE.md (fichier auto-chargé) — seule la liste des modèles gratuits migre vers `references.md` (spec §5).
- La correction des chemins cassés (§2 de la spec) et la clôture du flag "agents à réévaluer" (§7) doivent atterrir dans le **même commit** — jamais un état intermédiaire où l'un est fait sans l'autre (spec §7, ordonnancement).
- `ARCHITECTURE.md` ne contient jamais le diagramme/catalogue déjà présent dans `PLAN-PROJET.md` — seulement le journal des décisions (spec §2bis).

---

### Task 1: Git local — baseline avant toute modification

**Files:**
- Create: `.gitignore` (racine)
- Create: dépôt git local (`.git/`)

**Interfaces:**
- Consumes: rien (premier commit)
- Produces: un dépôt git initialisé avec un commit baseline — toutes les tâches suivantes committent dessus.

- [ ] **Step 1: Créer `.gitignore`**

Contenu exact :
```
node_modules/
.wrangler/
.dev.vars
.dev.vars.*
*.log
.DS_Store
```

- [ ] **Step 2: Initialiser le dépôt et vérifier qu'aucun secret n'est déjà présent**

```bash
cd "C:\Users\Asus\Documents\GitHub\cloudflare-monetization"
git init
git status
```
Lire la sortie de `git status` avant de continuer — si un fichier inattendu apparaît (`.dev.vars`, clé quelconque), s'arrêter et signaler avant de committer.

- [ ] **Step 3: Premier commit — baseline**

```bash
git add -A
git commit -m "chore: baseline avant remise à niveau workspace (docs, agents, gouvernance)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
git log --oneline -1
```

Expected: un seul commit, `git log --oneline -1` affiche son message.

---

### Task 2: Allègement CLAUDE.md — extraction du catalogue de modèles et des références

**Files:**
- Create: `.claude/context/references.md`
- Modify: `CLAUDE.md:100-127` (section "MODÈLES WORKERS AI GRATUITS") et `CLAUDE.md:170-178` (section "RÉFÉRENCES")

**Interfaces:**
- Consumes: contenu actuel de `CLAUDE.md` (lu directement avant édition, pas de mémoire supposée)
- Produces: `CLAUDE.md` ne contient plus que la sous-section "Modèles Paid" (interdiction, reste auto-chargée) ; le reste du catalogue vit dans `.claude/context/references.md`.

- [ ] **Step 1: Lire l'état actuel de CLAUDE.md**

```bash
cat -A CLAUDE.md > /dev/null  # sanity check fichier lisible ; puis lecture normale via l'outil Read
```
Relire tout `CLAUDE.md` avec l'outil Read pour confirmer que les lignes 100-127 et 170-178 correspondent toujours exactement à ce qui suit (le fichier peut avoir bougé depuis la spec) :
- Lignes 100-127 : section `## MODÈLES WORKERS AI GRATUITS` en entier (Text/Image/Translation/TTS-ASR/Markdown/Paid).
- Lignes 170-178 : section `## RÉFÉRENCES` en entier.

- [ ] **Step 2: Créer `.claude/context/references.md`**

```markdown
# References — cloudflare-monetization

Contenu consulté à la demande (pas chargé automatiquement au démarrage de session). Les interdictions de sécurité (modèles Paid à ne pas utiliser) restent dans `CLAUDE.md`.

## Modèles Workers AI gratuits (Free Tier)

### Text generation
- `@cf/google/gemma-4-26b-a4b-it`
- `@cf/openai/gpt-oss-120b`
- `@cf/openai/gpt-oss-20b`
- `@cf/zai-org/glm-4.7-flash`
- `@cf/nvidia/nemotron-3-120b-a12b`
- `@cf/mistralai/mistral-small-3.1-24b-instruct`

### Image generation
- `@cf/blackforestlabs/flux-1-schnell`

### Translation
- `@cf/meta/m2m100-1.2b`

### TTS / ASR
- `@cf/deepgram/aura-1`
- `@cf/deepgram/nova-3`

### Markdown conversion
- `env.AI.toMarkdown()` (méthode du binding AI)

## Références externes

- Workers Limits : https://developers.cloudflare.com/workers/platform/limits/
- Workers AI Models : https://developers.cloudflare.com/workers-ai/models/
- MPP : https://developers.cloudflare.com/agents/tools/payments/mpp-charge-for-http-content/
- mpp-proxy : https://github.com/cloudflare/mpp-proxy
- Browser Run : https://developers.cloudflare.com/browser-run/limits/
- R2 Presigned : https://developers.cloudflare.com/r2/api/s3/presigned-urls/
- Wrangler config : https://developers.cloudflare.com/workers/wrangler/configuration/
```

- [ ] **Step 3: Éditer CLAUDE.md — remplacer les deux sections**

Remplacer (édition exacte, `old_string`→`new_string`) :

`old_string` (section RÉFÉRENCES, lignes ~170-178) :
```
## RÉFÉRENCES

- Workers Limits : https://developers.cloudflare.com/workers/platform/limits/
- Workers AI Models : https://developers.cloudflare.com/workers-ai/models/
- MPP : https://developers.cloudflare.com/agents/tools/payments/mpp-charge-for-http-content/
- mpp-proxy : https://github.com/cloudflare/mpp-proxy
- Browser Run : https://developers.cloudflare.com/browser-run/limits/
- R2 Presigned : https://developers.cloudflare.com/r2/api/s3/presigned-urls/
- Wrangler config : https://developers.cloudflare.com/workers/wrangler/configuration/
```

`new_string` :
```
## RÉFÉRENCES

Catalogue complet des modèles Workers AI gratuits + liens de référence Cloudflare → `.claude/context/references.md` (à consulter à la demande, pas chargé au démarrage).
```

Puis remplacer :

`old_string` (section MODÈLES, lignes ~100-121, tout SAUF la sous-section Paid) :
```
## MODÈLES WORKERS AI GRATUITS (Free Tier)

### Text generation
- `@cf/google/gemma-4-26b-a4b-it`
- `@cf/openai/gpt-oss-120b`
- `@cf/openai/gpt-oss-20b`
- `@cf/zai-org/glm-4.7-flash`
- `@cf/nvidia/nemotron-3-120b-a12b`
- `@cf/mistralai/mistral-small-3.1-24b-instruct`

### Image generation
- `@cf/blackforestlabs/flux-1-schnell`

### Translation
- `@cf/meta/m2m100-1.2b`

### TTS / ASR
- `@cf/deepgram/aura-1`
- `@cf/deepgram/nova-3`

### Markdown conversion
- `env.AI.toMarkdown()` (méthode du binding AI)

### Modèles Paid (NE PAS UTILISER sur Free)
```

`new_string` :
```
## MODÈLES WORKERS AI

Catalogue complet des modèles gratuits → `.claude/context/references.md` (à consulter à la demande).

### Modèles Paid (NE PAS UTILISER sur Free)
```

(La liste des modèles Paid elle-même, lignes 124-126, ne change pas — elle reste juste sous ce nouveau titre de sous-section.)

- [ ] **Step 4: Vérifier**

Relire `CLAUDE.md` en entier avec l'outil Read : confirmer que la sous-section "Modèles Paid" est toujours présente et intacte, que les deux nouvelles lignes de pointeur sont bien là, qu'aucune section adjacente (RÈGLES ABSOLUES, STRUCTURE, COMMANDES, WORKFLOW) n'a bougé. Compter la taille approximative (`wc -c CLAUDE.md`, diviser par 4) — doit être en baisse par rapport à l'état de départ.

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md .claude/context/references.md
git commit -m "docs: extraire le catalogue de modèles gratuits et les références vers .claude/context/references.md

Garde la liste des modèles Paid interdits dans CLAUDE.md (règle de sécurité, doit rester auto-chargée).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: Gouvernance + correction des chemins cassés + clôture du flag agents

**Files:**
- Create: `ARCHITECTURE.md` (racine)
- Modify: `CLAUDE.md` (ajout section Gouvernance, mise à jour section "Sous-agents disponibles")
- Modify: `.claude/agents/architect.md`
- Modify: `.claude/agents/cloudflare-ops.md`
- Modify: `.claude/agents/monetization-strategist.md`
- Modify: `.claude/agents/testing.md`
- Modify: `.claude/commands/update-summary.md`
- Modify: `EXECUTIVE_SUMMARY.md`

**Interfaces:**
- Consumes: contenu actuel de chaque fichier (relu directement avant édition)
- Produces: plus aucune référence à `docs/ROADMAP.md`, `docs/architecture.md`, `docs/PLAN-PROJET.md`, ou `CLAUDE.md §X` dans tout le workspace ; roster d'agents confirmé de façon cohérente dans `CLAUDE.md` et `EXECUTIVE_SUMMARY.md`.

**Pourquoi un seul task/commit pour tout ça** : la spec (§7, ordonnancement) interdit explicitement de committer la confirmation du roster séparément des corrections de chemins — un commit intermédiaire avec l'un sans l'autre laisserait le workspace dans un état incohérent (roster "confirmé" alors qu'un agent pointe encore vers un fichier inexistant).

- [ ] **Step 1: Créer `ARCHITECTURE.md`**

```markdown
# ARCHITECTURE.md — Décisions structurelles

Journal append-only des décisions d'architecture non triviales (contexte, décision, alternative écartée). Tenu par l'agent `architect`. Ne pas dupliquer le statut projet (→ `EXECUTIVE_SUMMARY.md`) ni le catalogue technique/diagramme cible déjà présent dans `PLAN-PROJET.md` — n'y renvoyer que par un lien si une décision le concerne, jamais recopier son contenu.

(vide pour l'instant — première entrée au premier changement structurel réel)
```

- [ ] **Step 2: Éditer `.claude/agents/architect.md`**

`old_string` :
```
description: Garde la cohérence de l'arborescence du workspace cloudflare-monetization. À invoquer avant d'ajouter un nouveau module, déplacer du code partagé, ou faire évoluer la structure de dossiers. Met à jour docs/architecture.md après chaque décision structurelle.
```
`new_string` :
```
description: Garde la cohérence de l'arborescence du workspace cloudflare-monetization. À invoquer avant d'ajouter un nouveau module, déplacer du code partagé, ou faire évoluer la structure de dossiers. Met à jour ARCHITECTURE.md après chaque décision structurelle.
```

`old_string` :
```
3. Après chaque décision structurelle non triviale, ajouter une entrée datée dans
   `docs/architecture.md` (contexte, décision, alternative écartée).
4. Ne jamais modifier `docs/PLAN-PROJET.md` (document historique figé).
```
`new_string` :
```
3. Après chaque décision structurelle non triviale, ajouter une entrée datée dans
   `ARCHITECTURE.md` (contexte, décision, alternative écartée). Ne jamais y recopier ou
   paraphraser le diagramme/catalogue déjà présent dans `PLAN-PROJET.md` — seulement le
   journal des décisions (contexte/choix/alternative écartée), jamais l'état cible lui-même.
4. Ne jamais modifier `PLAN-PROJET.md` (document historique figé).
```

- [ ] **Step 3: Éditer `.claude/agents/cloudflare-ops.md`**

`old_string` :
```
3. Avant de proposer d'activer `d-scraping` ou `f-stream-tokens`, vérifier explicitement dans
   `docs/ROADMAP.md` qu'un cas d'usage payant a été validé (Phase 4 uniquement).
```
`new_string` :
```
3. Avant de proposer d'activer `d-scraping` ou `f-stream-tokens`, vérifier explicitement dans
   `ROADMAP.md` qu'un cas d'usage payant a été validé (Phase 4 uniquement).
```

- [ ] **Step 4: Éditer `.claude/agents/monetization-strategist.md`**

`old_string` :
```
description: Analyse quel module activer ensuite selon docs/ROADMAP.md et les signaux de revenu réels observés. À invoquer pour décider d'une transition de phase, ou pour trancher si un module doit rester désactivé faute de signal suffisant.
```
`new_string` :
```
description: Analyse quel module activer ensuite selon ROADMAP.md et les signaux de revenu réels observés. À invoquer pour décider d'une transition de phase, ou pour trancher si un module doit rester désactivé faute de signal suffisant.
```

`old_string` :
```
1. Ne jamais recommander l'activation d'un module de Phase 3 ou 4 (docs/ROADMAP.md) sans un
   signal concret : demande explicite d'un utilisateur réel, ou revenu déjà généré par un module
   de phase antérieure qui justifie l'extension.
```
`new_string` :
```
1. Ne jamais recommander l'activation d'un module de Phase 3 ou 4 (ROADMAP.md) sans un
   signal concret : demande explicite d'un utilisateur réel, ou revenu déjà généré par un module
   de phase antérieure qui justifie l'extension.
```

`old_string` :
```
3. Après chaque activation de module, proposer la ligne à ajouter au tableau "Historique
   d'activation" en bas de `docs/ROADMAP.md` (date, module, réseau, coût mesuré).
```
`new_string` :
```
3. Après chaque activation de module, proposer la ligne à ajouter au tableau "Historique
   d'activation" en bas de `ROADMAP.md` (date, module, réseau, coût mesuré).
```

- [ ] **Step 5: Éditer `.claude/agents/testing.md`**

`old_string` :
```
description: Écrit et maintient les tests Vitest/Miniflare pour chaque module. À invoquer pour valider la Definition of Done (CLAUDE.md §9) avant de marquer un module comme activé.
```
`new_string` :
```
description: Écrit et maintient les tests Vitest/Miniflare pour chaque module. À invoquer pour valider la checklist de validation (ROADMAP.md) avant de marquer un module comme activé.
```

`old_string` :
```
Utiliser `@cloudflare/vitest-pool-workers` (Miniflare) pour simuler l'environnement Workers.
Un module ne doit pas être coché "activé" dans `docs/ROADMAP.md` tant que ces trois tests ne
sont pas verts.
```
`new_string` :
```
Utiliser `@cloudflare/vitest-pool-workers` (Miniflare) pour simuler l'environnement Workers.
Un module ne doit pas être coché "activé" dans `ROADMAP.md` tant que ces trois tests ne
sont pas verts.
```

- [ ] **Step 6: Éditer `.claude/commands/update-summary.md`**

`old_string` :
```
Source de vérité : la mémoire auto déjà en contexte (si présente) + `docs/ROADMAP.md` (phase/module courants, tableau "Historique d'activation") et `docs/architecture.md` (décisions structurelles récentes) — pas une re-lecture intégrale de `PLAN-PROJET.md` (figé, 1500+ lignes, ne change jamais).
```
`new_string` :
```
Source de vérité : la mémoire auto déjà en contexte (si présente) + `ROADMAP.md` (phase/module courants, tableau "Historique d'activation") et `ARCHITECTURE.md` (décisions structurelles récentes) — pas une re-lecture intégrale de `PLAN-PROJET.md` (figé, 1500+ lignes, ne change jamais).
```

- [ ] **Step 7: Ajouter la section Gouvernance et mettre à jour "Sous-agents disponibles" dans `CLAUDE.md`**

`old_string` :
```
## Sous-agents disponibles (`.claude/agents/`)
6 agents scaffoldés lors de l'onboarding `_metahub` du 2026-09-05 (`architect`, `cloudflare-ops`,
`x402-payments`, `security-auditor`, `testing`, `monetization-strategist`) — utilité à réévaluer à
la lumière de la philosophie "un produit à la fois" ci-dessus (pas encore fait, invoque-les si
pertinent pour ton produit courant, sinon ignore-les).
```
`new_string` :
```
## Gouvernance — rôle de cette session

Modèle hérité de `_metahub` (`CLAUDE.md` §Gouvernance interne, 2026-08-30 ; `decisions_registry/2026-08-30_gouvernance-agents-correspondance.md`) :

- **Fondateur** = l'utilisateur. Arbitrage business/stratégique, jamais délégué à un agent.
- **Responsable BU** = cette session Claude Code locale (`cloudflare-monetization/`) — autorité technique complète sur ce projet, hors périmètre lecture-seule de `_metahub` par construction (exclusion structurelle, pas un seuil à atteindre). Reçoit une directive du Fondateur directement, ou relayée via `_metahub` (canal synchrone `ListAgents`+`SendMessage`, ou `/dispatch`). Exécute avec autorité technique complète, rapporte via `EXECUTIVE_SUMMARY.md` (agrégé dans `_metahub/PROJECTS_OVERVIEW.md` via `refresh.sh`).
- **Lead/Exécutant** = les agents locaux ci-dessous.
- **Protocole de rapport** : une directive reçue via le canal synchrone `_metahub` est exécutée ici puis rapportée par le même canal (en plus de `EXECUTIVE_SUMMARY.md`) — le Fondateur n'a pas besoin d'ouvrir cette session pour en connaître le résultat. Limite connue : tout travail nécessitant `Bash`, un `git commit`, ou une écriture fiable dans `.claude/` ne peut pas passer par `/dispatch` (2 pièges documentés côté `_metahub`, `CLAUDE.md` §Commandes) — reste traité dans une session ouverte ici, comme pour ce chantier.

## Sous-agents disponibles (`.claude/agents/`)
6 agents de process/gouvernance (`architect`, `cloudflare-ops`, `x402-payments`, `security-auditor`,
`testing`, `monetization-strategist`), confirmés le 06/09 après remise à niveau (chemins corrigés,
`x402-payments` réécrit pour `x402-hono` inline) — pas du scaffolding produit prématuré, pertinents
dès Phase 0. Invoque-les quand leur périmètre correspond à la tâche en cours.
```

- [ ] **Step 8: Éditer `EXECUTIVE_SUMMARY.md`**

`old_string` :
```
- 6 sous-agents dans `.claude/agents/` (hérités de l'onboarding du 05/09, utilité à réévaluer)
```
`new_string` :
```
- 6 sous-agents dans `.claude/agents/`, roster confirmé le 06/09 (chemins corrigés, `x402-payments` réécrit pour x402-hono inline)
```

- [ ] **Step 9: Vérifier — plus aucune référence cassée**

```bash
grep -rn "docs/ROADMAP\|docs/architecture\|docs/PLAN-PROJET\|CLAUDE.md §" .claude/ CLAUDE.md EXECUTIVE_SUMMARY.md
```
Expected: aucune sortie (0 match). Si une occurrence apparaît, la corriger avant de continuer.

- [ ] **Step 10: Commit**

```bash
git add ARCHITECTURE.md CLAUDE.md EXECUTIVE_SUMMARY.md .claude/agents/architect.md .claude/agents/cloudflare-ops.md .claude/agents/monetization-strategist.md .claude/agents/testing.md .claude/commands/update-summary.md
git commit -m "fix: corriger les chemins docs/ cassés, ajouter la gouvernance, confirmer le roster d'agents

Les agents/commande référençaient un dossier docs/ et des sections CLAUDE.md §X qui
n'existent plus depuis le remplacement du CLAUDE.md le 06/09. Ajoute aussi la section
Gouvernance (rôle Responsable BU, sourcé _metahub) et ARCHITECTURE.md.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 4: Réécriture de `x402-payments.md` pour `x402-hono` inline

**Files:**
- Modify: `.claude/agents/x402-payments.md` (réécriture complète du corps, frontmatter inchangé sauf description)

**Interfaces:**
- Consumes: rien de code (pas d'implémentation x402-hono encore) — s'appuie sur `EXECUTIVE_SUMMARY.md` (décision "x402 inline via x402-hono") et les RÈGLES ABSOLUES de `CLAUDE.md`.
- Produces: agent à jour, invocable dès que Phase 1 démarre l'implémentation réelle.

- [ ] **Step 1: Relire l'état actuel du fichier**

Lire `.claude/agents/x402-payments.md` en entier avec l'outil Read pour confirmer le contenu de départ avant de le remplacer intégralement (il a pu changer depuis la spec).

- [ ] **Step 2: Remplacer tout le corps (après le frontmatter)**

`old_string` (frontmatter, description seule) :
```
description: Spécialiste du module de paiement a-paywall-mpp (template cloudflare/mpp-proxy). À invoquer pour tout code touchant à la config de paiement, aux secrets, ou pour préparer la bascule testnet → mainnet.
```
`new_string` :
```
description: Spécialiste du paiement x402 inline (x402-hono) du produit courant. À invoquer pour tout code touchant à la config de paiement, aux secrets, ou pour préparer la bascule testnet → mainnet. mpp-proxy reste une alternative Phase 3+ si un module paywall séparé devient nécessaire, pas l'approche retenue pour le premier produit.
```

`old_string` (tout le corps après le frontmatter) :
```
Tu es le spécialiste paiement du workspace. Règles non négociables (CLAUDE.md §2 et §6) :

1. Le module `a-paywall-mpp` est un clone du template officiel `cloudflare/mpp-proxy` — ne pas
   réimplémenter la vérification de paiement à la main. Aucune clé privée blockchain, aucune
   signature on-chain, aucun appel RPC direct dans un Worker.
2. Configuration via `PAY_TO` (adresse wallet Base publique uniquement) et deux secrets :
   `JWT_SECRET`, `MPP_SECRET_KEY` — jamais en dur dans `wrangler.jsonc`.
3. Tout nouveau réglage de prix est d'abord testé avec `TEMPO_TESTNET: true`. La bascule en
   production (`TEMPO_TESTNET: false`) ne se fait qu'après un paiement testnet vérifié de bout
   en bout et visible dans les logs (`wrangler tail`).
4. Ne jamais dépendre du "Cloudflare Monetization Gateway" (liste d'attente) ni du protocole
   x402/facilitator tiers (Coinbase CDP, x402.org) tant que mpp-proxy suffit au besoin — ce
   n'est utile que si on doit sortir de Base/USDC vers un autre réseau.
5. Vérification post-déploiement : BaseScan → adresse `PAY_TO` → transaction visible.
```
`new_string` :
```
Tu es le spécialiste paiement du workspace. Règles non négociables (CLAUDE.md > RÈGLES ABSOLUES > Sécurité) :

1. Le paiement du premier produit passe par `x402-hono` inline dans le Worker (décision actée,
   voir `EXECUTIVE_SUMMARY.md`) — pas de module paywall séparé avant Phase 3+. Aucune clé privée
   blockchain, aucune signature on-chain, aucun appel RPC direct dans un Worker : `x402-hono`
   vérifie le paiement via un facilitator, le Worker ne signe jamais rien.
2. Les noms exacts des variables/secrets `x402-hono` ne sont pas figés ici — l'implémentation
   n'existe pas encore (Phase 0 pas commencée). Au moment de l'implémenter : consulter la doc/repo
   réel de `x402-hono` plutôt que de supposer des noms. Ce qui ne change pas quel que soit le nom
   exact : `PAY_TO` (adresse wallet Base publique uniquement) en clair, tout secret (clé de
   facilitator, etc.) via `wrangler secret put` — jamais en dur dans `wrangler.jsonc`.
3. Tout nouveau réglage de prix est d'abord testé sur testnet. La bascule en production ne se
   fait qu'après un paiement testnet vérifié de bout en bout et visible dans les logs
   (`wrangler tail`). Cette règle est aussi câblée mécaniquement par le hook
   `.claude/hooks/compliance-gate.py` — toute tentative d'écrire un flag de bascule dans
   `wrangler.jsonc` sans entrée dans `.claude/context/testnet-verified.md` est bloquée.
4. `mpp-proxy` (template `cloudflare/mpp-proxy`) reste une alternative documentée pour un module
   paywall séparé (`a-paywall-mpp`) — pertinent seulement en Phase 3+ si le besoin apparaît
   (ex. sortir de Base/USDC vers un autre réseau), pas l'approche du premier produit.
5. Vérification post-déploiement : BaseScan → adresse `PAY_TO` → transaction visible.
```

- [ ] **Step 3: Vérifier**

Relire le fichier entier — confirmer que le frontmatter (`name`, `tools`) n'a pas bougé, que seule `description` + le corps ont changé.

- [ ] **Step 4: Commit**

```bash
git add .claude/agents/x402-payments.md
git commit -m "docs: réécrire x402-payments.md pour x402-hono inline au lieu de mpp-proxy

Le premier produit utilise x402-hono inline (EXECUTIVE_SUMMARY.md), pas le module
mpp-proxy standalone pour lequel cet agent était écrit. mpp-proxy redevient une
alternative Phase 3+.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 5: `.claude/context/errors.md` — journal de pièges, seedé

**Files:**
- Create: `.claude/context/errors.md`

**Interfaces:**
- Consumes: rien
- Produces: fichier consulté en début de session future pour éviter de re-découvrir des pièges déjà connus.

- [ ] **Step 1: Créer le fichier**

```markdown
# Erreurs & pièges connus — cloudflare-monetization

Journal court des bugs/pièges Wrangler/Cloudflare rencontrés et leur fix, un par ligne, le plus récent en haut. Ne duplique pas le statut projet (→ `EXECUTIVE_SUMMARY.md`).

- **CPU 10ms/requête** : le compteur n'inclut pas le temps passé en attente d'un `fetch()` (I/O exempté) — ne pas s'alarmer d'une latence perçue élevée si elle vient d'un appel externe, seul le temps CPU actif compte.
- **KV limité à 1000 writes/jour par namespace** : éviter d'écrire dans KV à chaque requête pour de l'auth/session — préférer un JWT stateless vérifié sans écriture KV, ça économise tout le quota pour l'usage métier réel.
- **Workers AI, 10 000 Neurons/jour** : quota GLOBAL au compte, partagé entre tous les Workers — pas 10 000 par Worker. Un 2e produit actif consomme le même quota que le premier, à surveiller dès qu'il y a plus d'un produit.
```

- [ ] **Step 2: Vérifier**

Relire le fichier créé, confirmer les 3 entrées sont présentes et lisibles.

- [ ] **Step 3: Commit**

```bash
git add .claude/context/errors.md
git commit -m "docs: seed .claude/context/errors.md avec 3 pièges Free Tier déjà connus

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 6: Garde-fou mécanique — `compliance-gate.py`

**Files:**
- Create: `.claude/hooks/compliance-gate.py`
- Create: `.claude/hooks/test_compliance_gate.py`
- Create: `.claude/settings.json`

**Interfaces:**
- Consumes: JSON sur stdin au format `{"tool_name": str, "tool_input": {"file_path": str, "content"?: str, "new_string"?: str}}` (contrat des hooks `PreToolUse` de Claude Code).
- Produces: sur stdout, soit rien (autorisé), soit `{"decision": "block", "reason": str}` puis exit 0 (bloqué). Fichier de déblocage attendu : `.claude/context/testnet-verified.md` (n'importe quel contenu non vide suffit à débloquer une bascule testnet→mainnet).

- [ ] **Step 1: Écrire le test AVANT le hook (il doit échouer — le script n'existe pas encore)**

Créer `.claude/hooks/test_compliance_gate.py` :

```python
#!/usr/bin/env python3
"""Test manuel du hook compliance-gate.py — pas de framework, cas concrets exécutés en séquence."""
import json
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).parent / "compliance-gate.py"
VERIFICATION_LOG = Path(".claude/context/testnet-verified.md")


def run(tool_name: str, file_path: str, content: str) -> str:
    payload = json.dumps(
        {
            "tool_name": tool_name,
            "tool_input": {"file_path": file_path, "content": content, "new_string": content},
        }
    )
    result = subprocess.run(
        [sys.executable, str(HOOK)], input=payload, capture_output=True, text=True
    )
    return result.stdout.strip()


def check(desc: str, out: str, expect_block: bool) -> None:
    blocked = '"decision": "block"' in out
    if blocked == expect_block:
        print(f"PASS: {desc}")
    else:
        print(f"FAIL: {desc} (sortie: {out!r})")
        sys.exit(1)


def main() -> None:
    VERIFICATION_LOG.unlink(missing_ok=True)

    fake_key = "0x" + "1" * 64

    check(
        "clé privée en dur dans wrangler.jsonc -> bloqué",
        run("Write", "wrangler.jsonc", f'{{"key":"{fake_key}"}}'),
        True,
    )

    check(
        "écriture normale dans wrangler.jsonc -> non bloquée",
        run("Write", "wrangler.jsonc", '{"name":"p1-demo"}'),
        False,
    )

    check(
        "secret en dur dans wrangler.jsonc (fichier versionné) -> bloqué",
        run("Write", "wrangler.jsonc", '{"JWT_SECRET":"abcdef1234567890"}'),
        True,
    )

    check(
        "secret dans .dev.vars (fichier local gitignored) -> non bloqué",
        run("Write", ".dev.vars", 'JWT_SECRET="abcdef1234567890"'),
        False,
    )

    check(
        "bascule testnet->mainnet sans vérification -> bloquée",
        run("Edit", "wrangler.jsonc", '"TEMPO_TESTNET": false'),
        True,
    )

    VERIFICATION_LOG.parent.mkdir(parents=True, exist_ok=True)
    VERIFICATION_LOG.write_text("p1-demo vérifié le 2026-09-06\n", encoding="utf-8")
    check(
        "bascule testnet->mainnet avec vérification -> non bloquée",
        run("Edit", "wrangler.jsonc", '"TEMPO_TESTNET": false'),
        False,
    )
    VERIFICATION_LOG.unlink(missing_ok=True)

    check(
        "clé privée dans un fichier hors config wrangler -> non bloqué (hors périmètre du hook)",
        run("Write", "src/index.ts", f'const k = "{fake_key}";'),
        False,
    )

    print("Tous les cas passent.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Lancer le test, vérifier qu'il échoue (le hook n'existe pas)**

```bash
python .claude/hooks/test_compliance_gate.py
```
Expected: `FileNotFoundError` ou erreur similaire (le fichier `compliance-gate.py` n'existe pas encore).

- [ ] **Step 3: Écrire `.claude/hooks/compliance-gate.py`**

```python
#!/usr/bin/env python3
"""PreToolUse hook — bloque les secrets en dur et une bascule testnet->mainnet non
vérifiée dans la config Wrangler/env de cloudflare-monetization."""
import json
import re
import sys
from pathlib import Path

WRANGLER_CONFIG_PATTERN = re.compile(r"wrangler\.(jsonc?|toml)$", re.IGNORECASE)
RELEVANT_FILE_PATTERN = re.compile(
    r"(wrangler\.(jsonc?|toml)$|\.dev\.vars(\.|$))", re.IGNORECASE
)

PRIVATE_KEY_PATTERN = re.compile(r"0x[a-fA-F0-9]{64}")
SECRET_LITERAL_PATTERN = re.compile(
    r'["\']?[A-Z0-9_]*(SECRET|PRIVATE_KEY|API_KEY)[A-Z0-9_]*["\']?\s*[:=]\s*'
    r'["\'](?!\$\{)[^"\']{8,}["\']',
    re.IGNORECASE,
)
NETWORK_FLIP_PATTERN = re.compile(
    r'["\']?[A-Z0-9_]*(TESTNET)[A-Z0-9_]*["\']?\s*[:=]\s*(false|"mainnet"|\'mainnet\')',
    re.IGNORECASE,
)

VERIFICATION_LOG = Path(".claude/context/testnet-verified.md")


def block(reason: str) -> None:
    print(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(0)


def main() -> None:
    payload = json.load(sys.stdin)
    if payload.get("tool_name") not in ("Write", "Edit"):
        return

    tool_input = payload.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    content = tool_input.get("content") or tool_input.get("new_string", "")

    if not RELEVANT_FILE_PATTERN.search(file_path):
        return

    if PRIVATE_KEY_PATTERN.search(content):
        block(
            f"Motif de clé privée blockchain détecté dans '{file_path}'. Jamais de clé "
            "privée dans un fichier de config — voir CLAUDE.md > RÈGLES ABSOLUES > Sécurité."
        )

    is_versioned_config = WRANGLER_CONFIG_PATTERN.search(file_path)

    if is_versioned_config and SECRET_LITERAL_PATTERN.search(content):
        block(
            f"Secret en dur détecté dans '{file_path}' (fichier versionné). Utiliser "
            "`wrangler secret put`, ou déplacer la valeur dans `.dev.vars` (gitignored) "
            "pour le développement local."
        )

    if is_versioned_config and NETWORK_FLIP_PATTERN.search(content):
        if not VERIFICATION_LOG.exists():
            block(
                f"Bascule testnet -> mainnet détectée dans '{file_path}' sans "
                f"vérification enregistrée. Créer '{VERIFICATION_LOG}' avec la preuve "
                "d'une transaction testnet vérifiée avant de basculer."
            )


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Lancer le test, vérifier qu'il passe**

```bash
python .claude/hooks/test_compliance_gate.py
```
Expected: 7 lignes `PASS: ...` puis `Tous les cas passent.` — aucun `FAIL`.

- [ ] **Step 5: Créer `.claude/settings.json` et câbler le hook**

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [{ "type": "command", "command": "python .claude/hooks/compliance-gate.py" }]
      }
    ]
  }
}
```

- [ ] **Step 6: Test d'intégration réel — le hook bloque bien une vraie tentative d'écriture**

Dans cette session (pas dans le script de test), tenter d'écrire un fichier `wrangler.jsonc` de test avec l'outil Write contenant une fausse clé privée (`0x` + 64 caractères hex), et confirmer que Claude Code refuse l'opération avec le message du hook. Supprimer ensuite ce fichier de test s'il a été créé avant le blocage.

- [ ] **Step 7: Commit**

```bash
git add .claude/hooks/compliance-gate.py .claude/hooks/test_compliance_gate.py .claude/settings.json
git commit -m "feat: garde-fou mécanique PreToolUse — secrets en dur + bascule testnet->mainnet non vérifiée

Comble le gap signalé comme prioritaire dans la mission d'onboarding _metahub du 05/09
(missions/2026-09-05_cloudflare-monetization-audit-onboarding.md) : aucun garde-fou
mécanique n'existait avant une mise en production réelle du paiement. Calqué sur
_metahub/PATTERN_compliance-gate.md (variante garde-fou financier). Testé (7 cas,
.claude/hooks/test_compliance_gate.py).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Self-Review (fait avant remise du plan)

- **Couverture spec** : §1 gouvernance → Task 3 Step 7 ; §2 chemins → Task 3 Steps 2-6 ; §2bis ARCHITECTURE.md → Task 3 Step 1-2 ; §3 x402-payments → Task 4 ; §4 hook → Task 6 ; §5 allègement CLAUDE.md → Task 2 ; §6 errors.md seedé → Task 5 ; §7 clôture flag → Task 3 Steps 7-8 (même commit que §2, conforme à la contrainte d'ordonnancement) ; §8 git → Task 1. Aucun point de la spec sans tâche.
- **Placeholders** : aucun "TBD"/"à compléter" dans les artefacts produits — les deux incertitudes assumées (noms de variables `x402-hono`, pattern exact de bascule réseau) sont documentées comme des limites explicites dans le contenu livré lui-même (Task 4 Step 2, Task 6 docstring/commit), pas laissées vides.
- **Cohérence** : le hook (Task 6) référence `.claude/context/testnet-verified.md`, le même chemin est cité dans `x402-payments.md` (Task 4) — cohérent. `ARCHITECTURE.md` (Task 3) est référencé de façon identique dans `architect.md` et `update-summary.md`.
