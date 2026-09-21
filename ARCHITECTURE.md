# ARCHITECTURE.md — Décisions structurelles

Journal append-only des décisions d'architecture non triviales (contexte, décision, alternative écartée). Tenu par l'agent `architect`. Ne pas dupliquer le statut projet (→ `EXECUTIVE_SUMMARY.md`) ni le catalogue technique/diagramme cible déjà présent dans `PLAN-PROJET.md` — n'y renvoyer que par un lien si une décision le concerne, jamais recopier son contenu.

Rattrapage du 2026-09-08 : ce journal était resté vide malgré plusieurs décisions structurelles déjà actées (p1/p2/p3 livrés, philosophie produit révisée). Les 3 entrées ci-dessous documentent rétroactivement ces décisions à partir de l'état réel du repo (`CLAUDE.md`, `ROADMAP.md`, code source) — elles ne créent aucune nouvelle règle.

Rattrapage du 2026-09-11 (audit workspace-optimizer #3) : les 2 entrées suivantes (Gouvernance,
Grille de compétences) étaient rédigées en toutes lettres dans `CLAUDE.md` — déplacées ici pour
alléger le fichier chargé à chaque session (2912 → ~2280 tokens), `CLAUDE.md` ne garde qu'un
pointeur. Contenu inchangé, pas une nouvelle décision.

---

## 2026-08-30 — Modèle de gouvernance hérité de `_metahub` adopté pour ce projet

**Contexte** : ce projet est un des portefeuilles solo pilotés en parallèle par le Fondateur ;
`_metahub` (`CLAUDE.md` §Gouvernance interne, 2026-08-30 ;
`decisions_registry/2026-08-30_gouvernance-agents-correspondance.md`) définit un modèle de
gouvernance commun à tous ces projets.

**Décision** : ce modèle s'applique tel quel ici — Fondateur = l'utilisateur (arbitrage
business/stratégique, jamais délégué à un agent) ; Responsable BU = cette session Claude Code
locale (`cloudflare-monetization/`), autorité technique complète sur ce projet, hors périmètre
lecture-seule de `_metahub` par construction (exclusion structurelle, pas un seuil à atteindre) ;
Lead/Exécutant = les 8 agents locaux (`.claude/agents/`). Reçoit une directive du Fondateur
directement, ou relayée via `_metahub` (canal synchrone `ListAgents`+`SendMessage`, ou
`/dispatch`). Exécute avec autorité technique complète, rapporte via `EXECUTIVE_SUMMARY.md`
(agrégé dans `_metahub/PROJECTS_OVERVIEW.md` via `refresh.sh`).

**Protocole de rapport** : une directive reçue via le canal synchrone `_metahub` est exécutée ici
puis rapportée par le même canal (en plus de `EXECUTIVE_SUMMARY.md`) — le Fondateur n'a pas besoin
d'ouvrir cette session pour en connaître le résultat. Limite connue : tout travail nécessitant
`Bash`, un `git commit`, ou une écriture fiable dans `.claude/` ne peut pas passer par `/dispatch`
(2 pièges documentés côté `_metahub`, `CLAUDE.md` §Commandes) — reste traité dans une session
ouverte ici.

**Alternative écartée** : un modèle de gouvernance spécifique à ce projet, distinct de
`_metahub` — écartée pour rester cohérent avec les autres projets du portefeuille.

---

## 2026-09-07 — Grille de lecture "Agentic Revenue Architect" retenue pour les agents locaux

**Contexte** : discussion externe (ChatGPT, 2026-09-07) sur le métier d'"Agentic Revenue
Architect", proposant 4 couches (Agentic Economics, Agentic Infrastructure, Machine Payments,
Revenue Engineering) et une structure de dossiers associée (`06-analytics/`, `07-optimization/`).

**Décision (Fondateur)** : retenir uniquement la grille de lecture pour classer les 8 agents
locaux existants, PAS la structure de dossiers proposée (`06-analytics/`, `07-optimization/`
restent interdits par la règle D1 metering/pricing engine de `CLAUDE.md` tant qu'il n'y a pas de
volume) :

| Couche (ChatGPT) | Couvert par | Statut |
|---|---|---|
| Agentic Economics (pricing, demande) | `monetization-strategist` | Couvert |
| Agentic Infrastructure (Workers, KV/D1/R2) | `cloudflare-ops`, `architect` | Couvert |
| Machine Payments (x402, MPP, facilitators) | `x402-payments` | Couvert |
| Revenue Engineering (analytics, auto-optimisation) | `query-analyst` (diagnostic manuel) | **Partiellement couvert** le 09/09 — diagnostic sur trafic réel couvert ; auto-optimisation (D1 metering, pricing engine) différée volontairement (pas de volume), toujours interdite par `CLAUDE.md` |

**Alternative écartée** : créer les dossiers `06-analytics/`/`07-optimization/` proposés par la
grille externe — écartée, prématuré tant que les règles de volume de `CLAUDE.md` ne sont pas
remplies.

---

## 2026-09-07 — Gate séquentiel remplacé par un gate par type de quota

**Contexte** : `p1-markdown-x402` (Workers AI) était en prod ; la règle initiale `ROADMAP.md` ("un produit à la fois") interdisait tout `p2` tant que `p1` n'avait pas de signal de revenu validé.

**Décision (Fondateur)** : la contrainte réelle n'est pas le nombre de produits mais la contention sur les quotas Free Tier **globaux** (Neurons Workers AI, minutes Browser Run — `.claude/context/errors.md` le confirme : "quota GLOBAL au compte, partagé entre tous les Workers"). Un produit CPU-only (`fetch()`/KV, zéro IA/Browser) ne retire rien à `markdown-x402`. Donc : produits légers = parallèles sans gate ; produits IA/Browser-intensifs = un seul à la fois tant que `markdown-x402` n'a pas de signal d'usage validé. Actée dans `CLAUDE.md` §Philosophie produit et `ROADMAP.md` §Phase 1.5.

**Alternative écartée** : garder le gate séquentiel strict pour tout produit sans distinction de type de quota — aurait bloqué `p2`/`p3` (tous deux CPU-only/`fetch()`) sans bénéfice réel, puisqu'ils ne partagent aucun quota avec `p1`.

---

## 2026-09-07/08 — p2-domain-parser : réplique du patron monolithique p1, pas d'extraction anticipée

**Contexte** : `p2-domain-parser` est le 2e produit livré (`products/p2-domain-parser/src/index.ts`). Le boilerplate x402 de `p1` (facilitator `HTTPFacilitatorClient`/`registerExactEvmScheme`, `agent.json`/`llms.txt` dynamiques, manifeste `/.well-known/x402`, gate `POST` séparé du handler) était déjà connu et fonctionnel.

**Décision** : `p2` réplique ce patron quasi à l'identique (mêmes imports `@x402/*`, même structure de route, même style de commentaires) plutôt que d'introduire une couche partagée. Duplication assumée pour rester conforme à la règle "`shared/` seulement en Phase 3, quand 2+ produits *génèrent du revenu*" (`CLAUDE.md` §Philosophie produit, révisé 07/09) — ni `p1` ni `p2` n'avait de revenu confirmé à ce moment (`EXECUTIVE_SUMMARY.md` : $0 de revenu externe réel au 07/09).

**Alternative écartée** : extraire dès `p2` un `shared/payments/x402.ts` commun à `p1`+`p2` — écartée comme prématurée au regard de la règle de revenu ci-dessus, pas seulement du nombre de produits.

---

## 2026-09-08 — p3-domain-intelligence : architecture modulaire divergente, sans arbitrage de convention commune

**Contexte** : `p3-domain-intelligence` est arrivé "par un canal hors roadmap (session mobile)" (`ROADMAP.md` §Phase 1.5 "Statut réel"), réalisant l'idée "Domain Intelligence" initialement prévue pour le slot `p2`. Contrairement à `p1`/`p2` (un seul fichier `src/index.ts` monolithique), `p3` est structuré en modules (`src/http/router.ts`, `src/pricing.ts`, `src/env.ts`, `src/engine/*`, `src/adapters/*`, `src/mcp/server.ts`) et ajoute un serveur MCP, des tests `vitest`, un dataset Analytics Engine.

**Décision (implicite, jamais arbitrée explicitement)** : cette structure a été conservée telle quelle, sans rétro-alignement sur `p1`/`p2` ni remontée dans une couche partagée — chaque produit reste isolé dans son dossier `products/<slug>/`, conforme à la règle "un produit = un Worker isolé".

**Alternative écartée** : aucune — c'est précisément le point ouvert. Aucun choix explicite n'a tranché si le patron modulaire de `p3` doit devenir la convention par défaut des futurs produits, ou si `p1`/`p2` doivent y être alignés a posteriori. À trancher avant un 4e produit pour éviter que chaque nouveau produit invente sa propre convention (cf. revue de cohérence du 2026-09-08).

**Point ouvert relevé par cette revue (pas encore une décision)** : divergence de config sur le couple wallet destinataire/facilitator — `p1`/`p2` committent `PAY_TO` en clair dans `vars` de `wrangler.jsonc` (adresse publique, pas un secret au sens des RÈGLES ABSOLUES) et un `FACILITATOR_URL` codé en dur dans `src/index.ts` ; `p3` exige `X402_RECIPIENT_ADDRESS`/`X402_FACILITATOR_URL` via `wrangler secret put`, jamais committés, avec un défaut de code différent (`x402.org/facilitator`, testnet-only) explicitement neutralisé par le secret en prod (`ROADMAP.md` ligne "Facilitator par défaut... remplacé par facilitator.0xarchive.io... via secret X402_FACILITATOR_URL"). Aucune règle `CLAUDE.md` n'impose l'un ou l'autre mécanisme, mais le nommage et le mode de configuration diffèrent d'un produit à l'autre sans convention commune tranchée.

---

## 2026-09-09 — Pas de support Agent2Agent (A2A) sur p1/p2/p3 : décision délibérée, pas un oubli

**Contexte** : un audit opérationnel du 09/09 (checklist "tout est bien déployé/paramétré, zéro intervention humaine") a relevé qu'aucun des 3 produits n'expose de Agent Card A2A (`/.well-known/agent-card.json`), alors qu'agent-tools.cloud indexe une catégorie "A2A Agents" séparée (2994 entrées au 09/09) où on est donc invisibles.

**Décision (Fondateur, via arbitrage en session)** : ne pas construire ce support, après vérification du spec officiel (https://a2a-protocol.org/latest/specification/) plutôt que sur supposition. L'Agent Card n'est qu'un descripteur : un client A2A qui la lit envoie ensuite de vraies requêtes JSON-RPC (`SendMessage`, `GetTask`, `ListTasks`) au endpoint déclaré — même une implémentation "minimale" (réponses directes sans cycle de vie de tâche complet) exige d'implémenter ces opérations pour de vrai. Ce n'est donc pas un fichier de config manquant comme l'était `products/p2-domain-parser/agent.json` (fixé le même jour, commit `407b423`), mais un vrai serveur protocolaire à construire.

**Alternative écartée** : publier la carte seule sans le serveur RPC derrière. Écartée car pire que l'absence de fiche — un client A2A réel (ou le probe de santé A2A d'agent-tools.cloud, qui compte un handshake `initialize` réussi comme `healthy`) obtiendrait des erreurs et nous classerait probablement `down`/`degraded`, un signal négatif là où il n'y a aujourd'hui simplement aucun signal. Aucun signal de demande A2A observé par ailleurs (recherche `opportunity-scout` du même jour). Le protocole x402 n'a en outre pas de pattern établi pour se composer avec le modèle de tâches A2A — terrain non balisé.

**À revisiter si** : un signal de demande A2A concret apparaît (pas une hypothèse de "on manque peut-être un canal") — voir mémoire de session `project_paused_0909_operational_audit` pour le détail de l'analyse.

---

## 2026-09-06/09 — Historique de fiabilisation des sous-agents (`.claude/agents/`)

**Contexte** : les 6 agents initiaux référençaient des chemins et une structure du plan ChatGPT
initial, remplacé le 06/09 (`docs/ROADMAP.md`, `docs/PLAN-PROJET.md` inexistants, sections
`CLAUDE.md §1/§2/§6/§9` disparues) — un agent invoqué serait allé chercher des fichiers inexistants.

**Corrections apportées** :
- 06/09 (audit workspace-optimizer #1) : chemins corrigés dans les 6 agents.
- 06/09 (2e passe) : `cloudflare-ops`, `monetization-strategist`, `security-auditor` réécrits —
  référençaient encore des slugs de modules du plan ChatGPT (`d-scraping`, `f-stream-tokens`,
  `m-pay-per-crawl`, `a-paywall-mpp`, `k-api-keys`, `l-jwt-gating`), absents de `ROADMAP.md`/
  `PLAN-PROJET.md` actuels. `architect`/`testing` non ré-audités ligne à ligne (pas de slug
  fantôme détecté).
- 09/09 (audit #2) : `x402-payments` et `security-auditor` référençaient encore un unique
  `testnet-verified.md` (obsolète, remplacé par un fichier par produit) et `x402-payments`
  affirmait à tort "Phase 0 pas commencée" alors que p1/p2/p3 étaient déjà en mainnet — corrigé.
  Deux agents ajoutés ce jour : `query-analyst` (diagnostic trafic réel) et `opportunity-scout`
  (veille marché, propose sans jamais activer).

**Alternative écartée** : aucune — correctifs factuels, pas des choix de conception.

---

## 2026-09-10 — Le monolithe (p1/p2) devient le patron de référence du portfolio

**Contexte** : l'entrée du 2026-09-08 ci-dessus ("p3-domain-intelligence : architecture modulaire
divergente") avait relevé un point ouvert jamais arbitré : aucune convention commune n'a tranché si
le patron modulaire de `p3` (`http/`, `engine/`, `adapters/`, tests Vitest, MCP) devait devenir la
référence des futurs produits, ou si `p1`/`p2` (un seul `src/index.ts`) le restaient — "à trancher
avant un 4e produit". `p4-email-verification` (design :
`docs/superpowers/specs/2026-09-10-p4-email-verification-design.md`) est ce 4e produit.

**Décision (Fondateur)** : le patron **monolithique** (p1/p2) devient la convention par défaut du
portfolio pour les futurs produits légers CPU-only, appliquée dès `p4`. Raison : proportionnalité —
la majorité des candidats identifiés à ce jour (`ROADMAP.md` Phase 1.5, produits légers) sont des
transformations à un seul endpoint, pour lesquelles la séparation `http/engine/adapters` de `p3`
ajoute de la charge cognitive sans bénéfice mesuré. Ce n'est pas un choix local à `p4` seul — c'est
la levée explicite du point ouvert ci-dessus, applicable à tout produit futur qui ne justifie pas
explicitement un écart.

**Alternative écartée** : généraliser le patron modulaire de `p3` à tous les futurs produits —
écartée par défaut de proportionnalité, pas par rejet de principe.

**`p1`/`p2`/`p3` ne sont pas retouchés par cette décision** — elle ne s'applique qu'aux produits
futurs. `p3` reste un cas particulier justifié rétroactivement (MCP + tests + complexité réelle du
module DNS/RDAP/TLS), pas remis en cause.

**À revisiter si** : un futur produit a un besoin réel (plusieurs adaptateurs, serveur MCP, suite de
tests significative) qui justifie explicitement un écart au patron par défaut — l'écart doit alors
être documenté ici au moment où il est fait, pas décidé par défaut faute de convention.

---

## 2026-09-11 — Angle mort de télémétrie corrigé (`payment_success` prématuré) + nouveau Worker interne `ops-dashboard`

**Contexte** : le Fondateur a signalé ne recevoir aucun paiement externe. En traçant le code source de `paymentMiddlewareFromHTTPServer` (`@x402/hono`), découverte que le handler métier s'exécute **avant** confirmation du règlement on-chain (`processSettlement` après `next()`) — le client ne peut structurellement pas recevoir de contenu payant sans règlement confirmé (pas une fuite de paiement), mais le log applicatif `payment_success` de `p1`/`p2`/`p3` était écrit **dans le handler**, donc avant cette confirmation : angle mort de télémétrie réel.

**Décision (Fondateur)** : (1) renommer l'événement en `payment_handler_completed` et enrichir les hooks officiels `onAfterSettle` (payer/resource/tx) sur les 3 produits ; (2) construire un nouveau Worker interne `products/ops-dashboard/` qui consolide les 3 funnels de paiement (lecture croisée des datasets Analytics Engine existants, sans duplication), un scanner de règlements USDC réels on-chain (RPC public Base mainnet `mainnet.base.org`, D1 dédié `ops-dashboard-onchain`), et un calcul d'écart d'intégrité (`payment_handler_completed` moins `payment_settled`) par produit — le signal explicitement demandé pour détecter à la fois "l'agent allait payer et n'a pas réglé" et "le service a été livré sans règlement confirmé". Ressources Free Tier ajoutées : 1 base D1, 1 namespace KV (`WATCH_STATE`), 1 Cron Trigger toutes les 30 min (3 des 5 emplacements/compte restent libres, `p2` en utilisait déjà 1). `ops-dashboard` n'a ni paywall x402 ni fiche `agent.json`/`llms.txt` — c'est un outil interne, pas un produit.

**Alternative écartée** : un canal de notification push (email/Telegram/Discord) plutôt qu'un dashboard visuel — écartée, le Fondateur voulait explicitement "un visu, graphique, des données", pas un canal d'alerte.

**Point de sécurité traité en cours de route (corrigé une 2e fois lors de la revue finale)** : un faux-positif de `.claude/hooks/compliance-gate.py` (regex de détection de clé privée, motif `0x[a-fA-F0-9]{64}`) sur le hash public standard `keccak256("Transfer(address,address,uint256)")` (identique sur tout contrat ERC-20/toute chaîne EVM) a été résolu par une allowlist étroite, exact-match uniquement (`KNOWN_PUBLIC_HASHES` dans le hook) — jamais par un contournement du code produit lui-même (une première tentative avait scindé la chaîne en deux littéraux pour échapper à la regex ; rejetée et corrigée, car un gate de sécurité contournable par découpage de chaîne ne protège plus rien pour la prochaine correspondance, potentiellement réelle celle-là). **Correction** : la revue finale de branche a trouvé, et vérifié en direct, que ce premier correctif affaiblissait réellement le hook — `finditer` avec un motif à longueur exacte (`{64}`) ne capture que les 64 premiers caractères hex d'une chaîne plus longue, donc une vraie clé collée immédiatement après le hash allowlisté (sans séparateur) matchait comme "hash connu" et ne déclenchait plus de 2e correspondance pour la clé elle-même — un contournement bien réel, pas seulement théorique, découvert par vérification empirique (pas par relecture). Corrigé en changeant le motif en `0x[a-fA-F0-9]{64,}` (capture goulue de toute la suite hexadécimale contiguë) : un hash isolé reste reconnu à l'identique, mais toute suite plus longue ne correspond plus à aucune entrée de l'allowlist et bloque. Revérifié en direct : hash seul → autorisé, fausse clé seule → bloqué, hash+clé collés → bloqué (corrigé), quasi-collision 1 caractère → bloqué.

**`p4-email-verification` reste explicitement hors périmètre** de `ops-dashboard` tant qu'il n'est pas déployé — sera intégré dans un changement séparé une fois ce produit en production.

**2e correction faite à la revue finale (scanner on-chain, également corrigé, pas seulement le hook ci-dessus)** : le scanner on-chain (`products/ops-dashboard/src/onchain.ts`) échouait de façon permanente et silencieuse en production — l'appel `eth_getLogs` sur ~188 000 blocs dépassait la limite de 2 000 blocs du RPC public Base (vérifié en direct : `eth_getLogs is limited to a 2,000 range`), et le curseur KV n'avançait jamais après un échec (D1 `onchain_settlements` confirmé à 0 ligne en production malgré des heures de cron). Corrigé par découpage en tranches de ≤2000 blocs (plafonné à 40 tranches/exécution pour rester sous la limite Free Tier de 50 sous-requêtes `fetch`/requête), curseur persisté après chaque tranche réussie même si une tranche suivante échoue, statut de dernier scan exposé sur `/stats` et sur le dashboard.

**Lacunes connues, documentées à la revue finale de branche, réellement pas corrigées dans ce chantier** :
- Le calcul de comparaison spec §4 ("nombre de `payment_settled` vs transactions on-chain non-test sur la même période") n'a jamais été implémenté — `ops-dashboard` calcule seulement l'écart `payment_handler_completed` moins `payment_settled` par produit (le signal réellement demandé par le Fondateur), pas la corrélation avec la table on-chain. À faire dans un changement séparé si ce recoupement s'avère nécessaire.
- Le renommage `payment_success`→`payment_handler_completed` (p1/p2/p3) vit sur cette branche mais **n'a pas encore été redéployé en production** au moment de la fusion — tant que p1/p2/p3 ne sont pas redéployés, `ops-dashboard` compte 0 `payment_handler_completed` (l'ancien nom `payment_success` continue d'être émis), donc l'écart d'intégrité affiché est temporairement dénué de sens. **Redéployer p1/p2/p3 fait partie intégrante de l'atterrissage de cette branche, pas une étape optionnelle.**
- Les dashboards propres à p1/p2/p3 pointent vers la même version cdnjs de Chart.js (`4.4.4`) qui n'existe plus (404 vérifié en direct) — casse leur graphique en prod depuis un moment, pas introduit par ce chantier mais découvert pendant. Suivi séparé proposé (hors périmètre de cette branche, touche 3 Workers de production distincts).

---

## 2026-09-11 — Adoption du plugin officiel `cloudflare@cloudflare` (14 skills + MCP)

**Contexte** : jusqu'ici, aucune skill Claude Code dédiée à Cloudflare/Wrangler n'était installée — seuls les 8 agents locaux du projet (process/gouvernance) et la mémoire du modèle couvraient la syntaxe wrangler/bindings, avec un risque de dérive sur une plateforme qui évolue vite (ex. Durable Objects SQLite passé gratuit en 2025, changements de `wrangler.jsonc`).

**Décision (Fondateur)** : installer le plugin marketplace officiel `cloudflare@cloudflare` (14 skills : `wrangler`, `durable-objects`, `workers-best-practices`, `agents-sdk`, etc.) + le MCP `mcp.cloudflare.com` (nécessite une auth Fondateur séparée via `/mcp`, pas encore faite), versionné dans `.claude/settings.json` — scope machine locale uniquement, pas synchronisé mobile/cloud. Articulation actée avec les 8 agents locaux : **agents = process du projet** (quand invoquer quoi, quelles règles business respecter), **skills = état de l'art technique Cloudflare** (syntaxe/API à jour) — pas un remplacement l'un de l'autre, les deux se complètent. En cas de doute sur une syntaxe wrangler/binding récente, la skill correspondante fait autorité avant la mémoire du modèle.

**Alternative écartée** : écrire des skills custom maison pour ce projet — écartée, le plugin officiel Cloudflare est maintenu en amont et couvre déjà le besoin, dupliquer aurait été de la maintenance inutile.

**Détail complet** : mémoire cross-session `reference_cloudflare_tooling_workspace_setup_0911` (2 Workers de test orphelins supprimés au passage, non liés à cette décision).

---

## 2026-09-11 — Deux branches orphelines terminées mergées dans master ; p1 déployé avec l'hybride turndown+linkedom

**Contexte** : un audit demandé par le Fondateur ("check p1/p2/p3/p4, quelles optimisations sont pertinentes") a révélé deux branches locales (`worktree-p1-html-fastpath`, `worktree-p4-email-verification`) contenant du travail terminé et déjà review-passé, jamais fusionné dans `master`. La branche p1 implémentait précisément la piste identifiée dans le chantier "Project Evolving" (`project_project_evolving_0911` en mémoire) : router le HTML pur de `/convert` vers `turndown`+`linkedom` (JS pur, zéro Neuron) au lieu de `env.AI.toMarkdown()` pour tout, avec repli automatique vers `env.AI` en cas d'échec ou de taille > 15 Ko (budget CPU 10 ms Free Tier).

**Décision (Fondateur)** : merger les deux branches (`git merge --ff-only`, rebase préalable sur `master` dans des worktrees jetables pour vérifier propreté — 0 conflit sur les deux, typecheck + tests unitaires 100% verts avant et après rebase), puis déployer `p1-markdown-x402` immédiatement. Checklist de validation post-déploiement passée (health 200, 402 correct avec le bon payload x402 mainnet, `agent.json`/`llms.txt` OK) — le paywall lui-même est inchangé, seul le chemin de conversion post-paiement évolue. Le chemin turndown+linkedom réel n'est pas vérifiable en production sans un vrai paiement (hors du périmètre d'exécution automatique) ; couvert par les 9 tests unitaires de `html-to-markdown.ts`.

**`p4-email-verification` est mergé dans `master` mais reste non déployé** — bloqué sur le même point que documenté précédemment : les Tasks 6-7 du plan (`docs/superpowers/plans/2026-09-10-p4-email-verification.md`) exigent explicitement que le test de paiement testnet soit exécuté par le Fondateur lui-même, avec sa propre clé testnet jetable ("never shared, never committed, never pasted into a conversation") — ce n'est pas une étape déléguée à cette session.

**Alternative écartée** : redévelopper ces deux fonctionnalités à partir de zéro sans vérifier l'historique git complet — aurait dupliqué du travail déjà fait et review-passé, pour un gain nul.
