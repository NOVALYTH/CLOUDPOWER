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
- Durable Objects pricing/quotas : https://developers.cloudflare.com/durable-objects/platform/pricing/
- Claude Code + Cloudflare (setup officiel) : https://developers.cloudflare.com/agent-setup/claude-code/

## Outillage Claude Code pour ce projet (installé 2026-09-11)

- MCP `bindings.mcp.cloudflare.com` (déjà connecté, préconnecté par l'environnement) — introspection
  directe du vrai compte : Workers/D1/KV/R2 (list/get) + recherche doc (`search_cloudflare_documentation`).
  À préférer à `wrangler` CLI ou à une supposition quand la tâche le permet.
- Plugin `cloudflare@cloudflare` (scope projet, `.claude/settings.json`) — 14 skills officielles
  (`wrangler`, `durable-objects`, `workers-best-practices`, `agents-sdk`, etc.) + déclaration d'un
  MCP `mcp.cloudflare.com` plus large (Code Mode API ~2500 endpoints, Radar, Browser Rendering,
  Observability, DNS Analytics, AI Gateway, AutoRAG) — **pas encore autorisé**, nécessite `/mcp`
  en session interactive.
- Détail complet de l'installation et de l'audit compte associé → mémoire Claude
  `reference_cloudflare_tooling_workspace_setup_0911` (hors repo, système de mémoire de session).
