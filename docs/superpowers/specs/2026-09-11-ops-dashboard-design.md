# Ops Dashboard — Design Spec

**Date**: 2026-09-11
**Décision Fondateur**: construire un système de suivi des transactions/événements agents, consolidé sur p1/p2/p3 (p4 ajouté après son déploiement), en s'appuyant rigoureusement sur les primitives Cloudflare Free Tier réellement disponibles.

## Contexte

Le Fondateur veut comprendre le parcours complet d'un agent sur nos 3 produits — de l'arrivée à l'achat ou non — avec assez de détail pour diagnostiquer : un agent a-t-il tenté de payer et échoué (et pourquoi), ou pire, a-t-il reçu le service sans que le wallet reçoive l'argent ?

**Découverte technique faite pendant le brainstorming** (en traçant `@x402/hono`'s `paymentMiddlewareFromHTTPServer`, `node_modules/@x402/hono/dist/esm/index.mjs`) :
- Le handler métier (notre code) s'exécute **avant** le règlement on-chain (`processSettlement` est appelé après `next()`).
- Si le règlement échoue, le middleware **remplace** la réponse HTTP par un échec — un agent ne peut donc pas recevoir le résultat payant sans règlement confirmé. C'est structurellement sûr côté client.
- MAIS notre propre log applicatif `payment_success` (p1/p2/p3, `src/index.ts`) est écrit **dans le handler**, donc avant que le règlement soit confirmé. Il peut donc affirmer un succès qui, quelques instants plus tard, se révèle être un échec de règlement — sans qu'on le voie nulle part aujourd'hui. C'est un vrai angle mort de notre télémétrie actuelle, pas une fuite de paiement réelle.

Ce spec corrige cet angle mort et construit la vue consolidée demandée, sur les primitives Free Tier vérifiées (recherche documentaire du 2026-09-11, pas les anciennes notes du projet — voir tableau ci-dessous).

## Primitives Cloudflare Free Tier retenues (vérifiées, pas supposées)

| Primitive | Limite réelle (Free, vérifiée 09/2026) | Rôle dans ce design |
|---|---|---|
| Workers Analytics Engine | 100k writes/jour, 10k requêtes SQL/jour, historique 90 jours, lecture via token de compte (pas lié à un Worker précis) | Reste la source d'écriture (p1/p2/p3, déjà en place) ; l'ops Worker la lit via l'API SQL, aucune duplication |
| D1 | 100k lignes écrites/jour, 5M lues/jour, 5GB stockage — **réellement appliqué depuis le 01/09/2026** | Petit registre des règlements on-chain réels détectés (`onchain_settlements`), faible volume |
| Cache API (`caches.default`) | Pas de limite d'écriture, mais local par edge, piloté uniquement par `Cache-Control` | Cache la réponse agrégée `/stats` (évite de re-consommer le quota SQL Analytics Engine à chaque rafraîchissement du dashboard) |
| Workers KV | 1000 writes/jour/namespace | Stocke uniquement le curseur on-chain (dernier bloc vérifié) — écriture peu fréquente |
| Cron Triggers | 5 max/compte en Free — **1 déjà utilisé** (p2, cache PSL, `0 3 * * *`) | 1 nouveau cron pour le scan on-chain (4 slots restent libres après) |

Point non confirmé dans la doc Cloudflare (à traiter comme tel, pas comme acquis) : impossible de confirmer si une requête SQL Analytics Engine peut joindre plusieurs datasets. Design en conséquence : chaque dataset est requêté séparément, la fusion se fait côté code du Worker ops, pas en SQL.

## Portée

**Inclus** : p1 (markdown-x402), p2 (domain-parser), p3 (domain-intelligence).
**Exclu pour l'instant** : p4 (email-verification) — sera ajouté après son déploiement (décision Fondateur explicite), même schéma d'événements à réutiliser tel quel à ce moment-là.
**Hors périmètre (YAGNI explicite)** :
- Pas de notification push (email/Telegram/Discord) — le Fondateur veut un visuel/dashboard, pas une alerte.
- Pas de tracking d'identité par agent au-delà de ce qui est déjà loggé (pas de nouvelle collecte de PII).
- Pas de jointure SQL cross-dataset (non confirmée côté Cloudflare).
- Pas de nouvelle abstraction de paiement/pricing partagée — ce chantier est de l'observabilité pure, ne touche pas au traitement des paiements, donc ne relève pas de la règle "pas de gateway partagé avant 2 produits qui génèrent du revenu".

## Composants

### 1. Correction de l'angle mort `payment_success` (p1, p2, p3 — changement additif)

Sur chacun des 3 produits :
- Ajout d'un identifiant de corrélation court par requête payante (généré au moment du challenge de paiement, ex. `crypto.randomUUID()` côté Worker si `@x402/core` n'expose pas déjà un identifiant utilisable dans le contexte des hooks — à vérifier précisément au moment du plan d'implémentation).
- Cet identifiant est attaché à **tous** les événements du cycle de vie d'une requête donnée (`payment_challenge`, `payment_attempt_rejected`, `payment_verify_rejected`, `payment_verify_error`, `payment_settle_failed`, `payment_settled`).
- Le log `payment_success` actuel (écrit dans le handler, donc avant règlement) est retiré de sa position actuelle. Le signal de succès définitif est désormais émis depuis `onAfterSettle` (hook déjà câblé), renommé `payment_delivered_and_settled` pour éviter toute ambiguïté avec l'ancien nom — c'est le seul événement qui signifie réellement "l'agent a reçu le service ET le wallet a été payé".
- Le handler garde un log neutre (`service_delivered` ou équivalent) sans prétendre que le paiement est acquis — utile pour distinguer "le calcul a été fait" de "on a été payé pour ce calcul", exactement la distinction que le Fondateur veut pouvoir tracer.

### 2. `products/ops-dashboard/` — nouveau Worker, léger, sans paywall

Pas un produit vendu — outil interne, protégé par le même `STATS_SECRET` que les 3 dashboards existants (réutilisé, pas régénéré).

**Routes** :
- `GET /dashboard?key=...` — page HTML consolidée (même pattern Chart.js + fetch same-origin que les dashboards existants) : funnel par produit (challenge → tentative → vérification → règlement → livré-et-payé), et une section dédiée "intégrité" qui affiche explicitement le compte d'événements `service_delivered` sans `payment_delivered_and_settled` correspondant (devrait rester à zéro — le mesurer prouve que le paywall tient, plutôt que de le supposer).
- `GET /stats?key=...&days=N` — JSON d'agrégation, résultat mis en cache via Cache API (TTL court, ~60s) pour ne pas taper le quota SQL Analytics Engine à chaque rafraîchissement.
- Export `scheduled` (cron) — scan on-chain périodique du wallet `payTo` partagé (voir composant 3).

**Bindings** (`wrangler.jsonc`) : `CF_ANALYTICS_TOKEN` (secret, même token "Account Analytics: Read" que les 3 produits — un seul suffit, il est scope-compte), `STATS_SECRET` (secret, valeur réutilisée), `PAY_TO` (var, adresse publique — pas un secret, déjà publiée partout), binding D1 (`ONCHAIN_DB`), binding KV (`WATCH_STATE`), `triggers.crons`.

### 3. Registre on-chain réel — D1 + KV + Cron

**Pourquoi D1 et pas juste re-vérifier BaseScan à la demande** : un registre persistant permet de comparer nos propres événements `payment_delivered_and_settled` à la réalité on-chain de façon fiable et historisée, pas seulement "combien de tx existent là maintenant".

Table D1 (`ONCHAIN_DB`), une seule :
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

Cron (fréquence proposée : toutes les 30 minutes — `*/30 * * * *`) :
1. Lit le curseur (`last_checked_block`) depuis KV.
2. Interroge la chaîne Base pour les transferts USDC entrants vers `payTo` depuis ce bloc (RPC public Base, ex. `mainnet.base.org` — sans clé — à confirmer au moment du plan ; alternative : API BaseScan avec clé gratuite si le RPC direct s'avère peu pratique en filtrage de logs).
3. Insère les nouvelles transactions (`INSERT OR IGNORE`, la clé primaire `tx_hash` déduplique naturellement), marque `is_known_test_wallet = 1` si l'expéditeur correspond au wallet de test Fondateur connu (`0x2A9b7416...069cFF6FB`).
4. Met à jour le curseur en KV.

### 4. Croisement d'intégrité (le cœur de la demande Fondateur)

Le dashboard affiche, par produit et en agrégé :
- Funnel complet : challenge → tentative rejetée → vérification échouée → règlement échoué → **livré-et-payé**.
- **Alerte visuelle** si `service_delivered` > `payment_delivered_and_settled` sur une période — répond exactement à "pourquoi il a reçu le service et mon wallet ne reçoit rien".
- **Comparaison avec la réalité on-chain** : nombre de `payment_delivered_and_settled` vs nombre de transactions on-chain non-test dans la table `onchain_settlements` sur la même période — si ces deux nombres divergent, c'est un signal de bug à investiguer, pas une supposition.

## Gestion des erreurs

- Une requête SQL Analytics Engine qui échoue pour un produit ne doit pas faire échouer toute la page — affichage partiel avec indicateur d'erreur par produit.
- Un échec du scan on-chain (RPC indisponible) est loggé et retenté au cycle suivant (pas d'alerte push, cohérent avec le choix du Fondateur) — le dashboard affiche "dernière vérification on-chain : il y a X min" pour rendre la fraîcheur visible.
- Écritures D1 idempotentes (`INSERT OR IGNORE` sur `tx_hash`) — un re-scan partiel ne duplique rien.

## Tests

- Tests unitaires (Vitest) sur la logique pure : fusion des résultats de plusieurs requêtes Analytics Engine en une forme unique pour le dashboard ; avancement du curseur on-chain et déduplication, avec des réponses RPC mockées.
- Validation manuelle : dashboard testé en local (`wrangler dev`) avec bindings mockés ; le scan on-chain doit retrouver exactement les 4 transactions de test Fondateur connues sur la plage historique réelle.

## Auto-revue

- **Placeholders** : aucun "TBD" — le seul point réellement ouvert (mécanisme RPC exact pour le scan Base, et la source exacte de l'identifiant de corrélation dans les hooks `@x402/core`) est explicitement nommé comme tel, à trancher pendant l'écriture du plan, pas pendant l'implémentation à l'aveugle.
- **Cohérence interne** : le composant 1 (correction `payment_success`) est un prérequis du composant 4 (croisement d'intégrité) — l'ordre des tâches du plan devra respecter cette dépendance.
- **Portée** : un seul sous-projet cohérent (observabilité), pas de découpage supplémentaire nécessaire.
- **Ambiguïté** : "toutes les 30 minutes" pour le cron est une proposition, pas une contrainte dure — ajustable sans risque si le Fondateur préfère une autre fréquence.
