# Design — Remise à niveau du workspace `cloudflare-monetization`

**Date** : 2026-09-06
**Statut** : approuvé par l'utilisateur (chat), en attente de revue de cette fiche avant plan d'exécution.

## Contexte

Audit du workspace (`workspace-optimizer`, même session) a trouvé : CLAUDE.md et 4 agents/1 commande pointant vers des chemins `docs/` inexistants (les vrais fichiers sont à la racine) et des sections `CLAUDE.md §X` qui n'existent plus depuis le remplacement complet du CLAUDE.md le 06/09 ; l'agent `x402-payments.md` écrit pour le module `mpp-proxy` alors que le plan actuel (`EXECUTIVE_SUMMARY.md`) retient `x402-hono` inline pour le premier produit ; aucun dépôt git initialisé ; aucun garde-fou mécanique sur la bascule testnet→mainnet du paiement — ce dernier point déjà signalé comme "action prioritaire avant toute mise en production réelle" dans la mission d'onboarding `_metahub` du 05/09 (`missions/2026-09-05_cloudflare-monetization-audit-onboarding.md`), jamais traité depuis.

L'utilisateur veut par ailleurs formaliser son rôle de "Fondateur" et le mien de "Responsable BU" pour ce projet, dans le modèle de gouvernance déjà tranché par `_metahub` (`CLAUDE.md` §Gouvernance interne, 2026-08-30 ; `decisions_registry/2026-08-30_gouvernance-agents-correspondance.md`) — confirmé sans réserve par la session `Pulse` (metahub) en direct pendant le brainstorming, avec deux points annexes intégrés ci-dessous (§1, §6).

## Périmètre

**Dans le périmètre (fondations, avant tout skill/agent produit)** :
1. Section gouvernance dans CLAUDE.md
2. Correction des chemins cassés (agents + commande)
3. Réécriture de `x402-payments.md` pour `x402-hono` inline
4. Hook mécanique `PreToolUse` — garde-fou secrets + bascule testnet→mainnet
5. Allègement de CLAUDE.md (extraction catalogue modèles + références vers un fichier à charge)
6. `.claude/context/errors.md` (journal de pièges techniques)
7. `git init` local + `.gitignore`
8. Clôture du flag "agents à réévaluer" dans `EXECUTIVE_SUMMARY.md`

**Explicitement hors périmètre (déferré)** :
- Tout skill/agent spécifique à un produit — Phase 0 (choix du produit vertical) n'a pas commencé, cohérent avec "un produit à la fois" (CLAUDE.md)
- Déplacement de `PLAN-PROJET.md`/`ROADMAP.md` vers un dossier `docs/` — décision utilisateur : on corrige les références, on ne déplace pas les fichiers
- Remote GitHub — décision utilisateur : dépôt local uniquement (recommandation donnée en chat : ajouter un filet de sauvegarde hors-git, hors périmètre technique de cette fiche)
- `.claude/skills/meta/start.md`/`end.md` génériques — écarté : `EXECUTIVE_SUMMARY.md` + `/update-summary` jouent déjà ce rôle dans la convention `_metahub`, doublon éviterait une désynchronisation (anti-pattern documenté dans `_metahub` `workspace-architecture` §5.1)
- `context/progress.md` générique — même raison

## 1. Section gouvernance (CLAUDE.md)

Contenu sourcé de `_metahub/CLAUDE.md` §Gouvernance interne + `decisions_registry/2026-08-30_gouvernance-agents-correspondance.md`, confirmé par la session `Pulse` en direct (aucune correction reçue sur le modèle lui-même). Intègre les 2 points annexes remontés par `Pulse` : (a) mention courte des 2 pièges connus du mécanisme `/dispatch` ; (b) le roster d'agents n'est plus présenté comme "à réévaluer" mais comme confirmé (cf. §7 de cette fiche).

```markdown
## Gouvernance — rôle de cette session

Modèle hérité de `_metahub` (`CLAUDE.md` §Gouvernance interne, 2026-08-30 ; `decisions_registry/2026-08-30_gouvernance-agents-correspondance.md`) :

- **Fondateur** = l'utilisateur. Arbitrage business/stratégique, jamais délégué à un agent.
- **Responsable BU** = cette session Claude Code locale (`cloudflare-monetization/`) — autorité technique complète sur ce projet, hors périmètre lecture-seule de `_metahub` par construction (exclusion structurelle, pas un seuil à atteindre). Reçoit une directive du Fondateur directement, ou relayée via `_metahub` (canal synchrone `ListAgents`+`SendMessage`, ou `/dispatch`). Exécute avec autorité technique complète, rapporte via `EXECUTIVE_SUMMARY.md` (agrégé dans `_metahub/PROJECTS_OVERVIEW.md` via `refresh.sh`).
- **Lead/Exécutant** = les agents locaux (`.claude/agents/`, cf. § Sous-agents disponibles).
- **Protocole de rapport** : une directive reçue via le canal synchrone `_metahub` est exécutée ici puis rapportée par le même canal (en plus de `EXECUTIVE_SUMMARY.md`) — le Fondateur n'a pas besoin d'ouvrir cette session pour en connaître le résultat. Limite connue : tout travail nécessitant `Bash`, un `git commit`, ou une écriture fiable dans `.claude/` ne peut pas passer par `/dispatch` (2 pièges documentés côté `_metahub`, `CLAUDE.md` §Commandes) — reste traité dans une session ouverte ici.
```

**Addendum 2026-09-06 (après validation initiale)** : l'utilisateur a exprimé le souhait de ne plus interagir qu'avec `_metahub` (modèle PDG→DGD→BU). Le canal synchrone existant permet déjà ce flux pour les directives/rapports ; la limite `/dispatch` (Bash/git/`.claude/` non exécutables à distance) reste réelle et documentée ci-dessus plutôt que découverte plus tard. Décision utilisateur : partir sur ce protocole tel quel (pas de changement côté `_metahub` demandé pour l'instant).

Insérée après la section "## Sous-agents disponibles" existante (voir §7).

## 2. Corrections de chemins

| Fichier | Ligne(s) | Avant | Après |
|---|---|---|---|
| `.claude/agents/architect.md` | 3, 15 | `docs/architecture.md` | `ARCHITECTURE.md` (nouveau fichier racine, cf. §2bis) |
| `.claude/agents/architect.md` | 16 | `docs/PLAN-PROJET.md` | `PLAN-PROJET.md` |
| `.claude/agents/cloudflare-ops.md` | 16 | `docs/ROADMAP.md` | `ROADMAP.md` |
| `.claude/agents/monetization-strategist.md` | 3, 9, 16 | `docs/ROADMAP.md` | `ROADMAP.md` |
| `.claude/agents/testing.md` | 3 | `Definition of Done (CLAUDE.md §9)` | `checklist de validation (ROADMAP.md)` |
| `.claude/agents/testing.md` | 16 | `docs/ROADMAP.md` | `ROADMAP.md` |
| `.claude/commands/update-summary.md` | 5, 7 | `docs/ROADMAP.md`, `docs/architecture.md` | `ROADMAP.md`, `ARCHITECTURE.md` |

### 2bis. `ARCHITECTURE.md` (nouveau, racine)

`architect.md` a pour mission de logger les décisions structurelles dans un fichier qui n'existe nulle part (ni `docs/architecture.md`, ni équivalent racine). Créer `ARCHITECTURE.md` à la racine (pas dans `docs/`, cohérent avec la décision §Périmètre) — squelette minimal :

```markdown
# ARCHITECTURE.md — Décisions structurelles

Journal append-only des décisions d'architecture non triviales (contexte, décision, alternative écartée). Tenu par l'agent `architect`. Ne pas dupliquer le statut projet (→ `EXECUTIVE_SUMMARY.md`) ni le catalogue technique/diagramme cible déjà présent dans `PLAN-PROJET.md` (→ n'y ajouter qu'un lien si une décision y touche, jamais recopier le diagramme).

(vide pour l'instant — première entrée au premier changement structurel réel)
```

**Garde-fou anti-doublon** : ajouter dans `architect.md` une ligne explicite — "Ne jamais recopier ou paraphraser le diagramme/catalogue déjà présent dans `PLAN-PROJET.md` ; `ARCHITECTURE.md` ne contient que le journal des décisions (contexte/choix/alternative écartée), jamais l'état cible lui-même."

## 3. Réécriture `x402-payments.md`

Remplace l'agent actuel (écrit pour `mpp-proxy` standalone) par une version pour `x402-hono` inline, cohérente avec `EXECUTIVE_SUMMARY.md` ("x402 inline via `x402-hono` dans le premier produit — pas de module paywall séparé avant Phase 3+"). Contenu :

- Règles absolues inchangées (aucune clé privée/signature on-chain dans le Worker — renvoie à CLAUDE.md § RÈGLES ABSOLUES > Sécurité par son titre, pas par un numéro de section)
- Config : `PAY_TO` (adresse Base publique) en clair, tout secret via `wrangler secret put` — noms de variables exacts non figés ici (l'implémentation `x402-hono` n'existe pas encore, Phase 0 pas commencée) ; l'agent doit consulter la doc/repo réel de `x402-hono` au moment de l'implémentation plutôt que de supposer des noms
- Discipline testnet avant mainnet : identique en esprit à l'ancienne version (vérifier une transaction testnet de bout en bout avant toute bascule), et **câblée mécaniquement** par le hook du §4 dès qu'un flag de bascule apparaît dans `wrangler.jsonc`
- `mpp-proxy` redevient une alternative documentée (Phase 3+ seulement, si un module paywall séparé devient nécessaire), pas l'approche principale
- Vérification post-déploiement : BaseScan → adresse `PAY_TO` → transaction visible (inchangé)

## 4. Garde-fou mécanique — `compliance-gate.py`

**Le point signalé comme prioritaire par la mission d'onboarding `_metahub` du 05/09, jamais traité.** Calqué sur le squelette `_metahub/PATTERN_compliance-gate.md` (variante "garde-fou financier"), adapté à ce projet.

Fichier : `.claude/hooks/compliance-gate.py` — hook `PreToolUse`, déclenché sur `Write`/`Edit` uniquement quand le fichier cible ressemble à une config Wrangler ou un fichier d'env (`wrangler.jsonc`, `.dev.vars`, `.dev.vars.*`, `*.toml` wrangler).

Deux contrôles :
1. **Secret en dur** — regex sur clé privée blockchain (`0x[a-fA-F0-9]{64}`) ou variable `*SECRET*`/`*KEY*`/`*PRIVATE*` assignée à une valeur littérale (pas une référence `wrangler secret`) → bloque, message renvoyant vers `wrangler secret put`.
2. **Bascule testnet→mainnet non vérifiée** — regex générique sur un flag ressemblant à une bascule réseau (`TESTNET`, `NETWORK`, `MAINNET` assigné à `false`/`"mainnet"`/`"base"`) → bloque sauf si `.claude/context/testnet-verified.md` existe et référence le module concerné.

**Limite assumée et documentée dans le fichier lui-même** : le nom exact des variables (`TEMPO_TESTNET` ou autre) n'est pas figé tant que `x402-hono` n'est pas implémenté (Phase 0 pas commencée) — le hook part sur un pattern générique à resserrer au moment de l'implémentation réelle, pas inventé maintenant. Même limite déjà documentée dans `PATTERN_compliance-gate.md` lui-même ("Points ouverts à vérifier avant install").

Câblage `.claude/settings.json` :
```json
{
  "hooks": {
    "PreToolUse": [
      { "matcher": "Write|Edit", "hooks": [{ "type": "command", "command": "python .claude/hooks/compliance-gate.py" }] }
    ]
  }
}
```

## 5. Allègement CLAUDE.md

- Créer `.claude/context/references.md` : y déplacer la **liste complète des modèles gratuits** (sous-sections Text/Image/Translation/TTS-ASR, lignes 102-121) et la section "RÉFÉRENCES" (lignes 170-178).
- **Garder dans CLAUDE.md** la sous-section "Modèles Paid (NE PAS UTILISER sur Free)" (lignes 123-126) — c'est une règle de sécurité (liste d'interdiction), pas un catalogue de référence ; elle doit rester dans le fichier auto-chargé au démarrage, pas dans un fichier consulté à la demande. Seule la liste des modèles autorisés migre vers `references.md`, l'interdiction reste sur place.
- Dans CLAUDE.md, remplacer la liste des modèles gratuits + la section RÉFÉRENCES par une ligne pointant vers `references.md`, en gardant la sous-section Paid juste au-dessus intacte.
- Effet : CLAUDE.md passe d'environ 1638 à ~1150 tokens (fichier seul, avant l'import `PROFILE.md`) malgré l'ajout de la section gouvernance (§1) — cible réaliste, pas le seuil générique de 300 tokens (ne correspond pas au contenu réellement utile ici).

## 6. `.claude/context/errors.md`

Nouveau fichier, journal court des pièges Wrangler/Cloudflare rencontrés (contenu différent d'`EXECUTIVE_SUMMARY.md`, pas un doublon). Seedé avec 3 pièges déjà connus (issus des limites Free Tier déjà documentées dans CLAUDE.md, reformulés en piège+fix) plutôt que laissé vide jusqu'au premier bug réel :

```markdown
# Erreurs & pièges connus — cloudflare-monetization

Journal court des bugs/pièges Wrangler/Cloudflare rencontrés et leur fix, un par ligne, le plus récent en haut. Ne duplique pas le statut projet (→ `EXECUTIVE_SUMMARY.md`).

- **CPU 10ms/requête** : le compteur n'inclut pas le temps passé en attente d'un `fetch()` (I/O exempté) — ne pas s'alarmer d'une latence perçue élevée si elle vient d'un appel externe, seul le temps CPU actif compte.
- **KV limité à 1000 writes/jour par namespace** : éviter d'écrire dans KV à chaque requête pour de l'auth/session — préférer un JWT stateless vérifié sans écriture KV, ça économise tout le quota pour l'usage métier réel.
- **Workers AI, 10 000 Neurons/jour** : quota GLOBAL au compte, partagé entre tous les Workers — pas 10 000 par Worker. Un 2e produit actif consomme le même quota que le premier, à surveiller dès qu'il y a plus d'un produit.
```

## 7. Clôture du flag "agents à réévaluer"

Dans CLAUDE.md, section "## Sous-agents disponibles" : remplacer la formulation "utilité à réévaluer... pas encore fait" par une confirmation — les 6 agents sont des agents de process/gouvernance (architecture, ops, tests, sécurité, stratégie monétisation, paiement), pas du scaffolding produit prématuré, donc pertinents dès Phase 0. Répercuté dans `EXECUTIVE_SUMMARY.md` (remplacer la ligne "6 sous-agents... utilité à réévaluer" par une ligne confirmant le roster + mentionnant la remise à niveau du 06/09), en respectant la limite de 30 lignes déjà en vigueur pour ce fichier.

**Ordonnancement d'exécution** : §2 (correction des chemins, dont `monetization-strategist.md`) et cette clôture de flag doivent être faits dans la même passe/commit — jamais l'un sans l'autre, pour éviter un état intermédiaire où le roster est déclaré "confirmé" alors qu'un agent pointe encore vers un chemin cassé.

## 8. Git

- `.gitignore` (racine) : `node_modules/`, `.wrangler/`, `.dev.vars`, `.dev.vars.*`, `*.log`, `.DS_Store`
- `git init`, `git add -A`, premier commit
- Pas de remote — décision utilisateur explicite. Recommandation donnée en chat (hors périmètre d'exécution de cette fiche) : filet de sauvegarde hors-git (copie horodatée périodique) vu l'absence de remote.

## Vérification

- Chaque chemin corrigé (§2) relu directement après édition — pas de confiance déclarative
- Hook testé manuellement : une tentative d'écriture avec un pattern de clé privée factice dans un `wrangler.jsonc` de test doit être bloquée ; une écriture normale ne doit pas l'être (faux positif = hook inutilisable au quotidien)
- `git log --oneline -1` après le premier commit
- Relecture complète du CLAUDE.md final (taille + cohérence, aucune section adjacente non visée perdue)
