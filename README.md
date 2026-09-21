# cloudflare-monetization

Plateforme agent-first de micro-services de données monétisés en USDC/x402 sur Cloudflare
Workers Free Tier — revenu avant infrastructure. Repo privé, usage interne.

## Produits déployés (Base mainnet)

| Produit | Endpoint principal | Prix | Live |
|---|---|---|---|
| [p1 markdown-x402](products/p1-markdown-x402) | `POST /convert` | $0.005/appel | https://markdown-x402.nordman-tehau.workers.dev |
| [p2 domain-parser](products/p2-domain-parser) | `POST /v1/domain/parse` | $0.001/appel | https://domain-parser.nordman-tehau.workers.dev |
| [p3 domain-intelligence](products/p3-domain-intelligence) | `GET /dns`, `/rdap`, `/tls`, `/intelligence` + MCP | $0.001-$0.002/appel | https://domain-intelligence.nordman-tehau.workers.dev |

Chaque produit expose son propre paywall x402 inline (`@x402/hono`), son manifeste
`/.well-known/x402`, `agent.json` et `llms.txt` — aucune couche partagée avant que 2+ produits
ne génèrent du revenu (voir `CLAUDE.md`).

## Points d'entrée

- [`CLAUDE.md`](CLAUDE.md) — règles, limites Free Tier, philosophie produit (à lire en premier)
- [`ROADMAP.md`](ROADMAP.md) — plan d'exécution phase par phase
- [`PLAN-PROJET.md`](PLAN-PROJET.md) — catalogue technique des briques réutilisables
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — journal des décisions structurelles
- [`EXECUTIVE_SUMMARY.md`](EXECUTIVE_SUMMARY.md) — statut courant, à jour en continu

## Commandes

```bash
cd products/<nom-du-produit>
npx wrangler dev       # développement local
npx wrangler deploy    # déploiement
npx wrangler tail <worker-name>   # logs live
```

Voir `skills/x402-data-apis` (aussi publié séparément :
[NOVALYTH/x402-data-apis](https://github.com/NOVALYTH/x402-data-apis)) pour le skill agent
installable documentant les 3 APIs.
