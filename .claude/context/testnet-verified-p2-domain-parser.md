# Vérification testnet — domain-parser

**Date** : 2026-09-09
**Produit** : `products/p2-domain-parser`
**Réseau** : Base Sepolia (`eip155:84532`)
**Protocole** : x402 v2 (`@x402/hono` + `@x402/evm` + `@x402/core`, v2.25.0)
**Facilitator** : `https://x402.org/facilitator` (public, testnet, défaut de `FACILITATOR_URL`)

## Contexte

Ce produit avait été déployé directement en Base mainnet le 07/09 (commit `f208ec1`) sans
round-trip testnet préalable ni fichier de preuve — gap identifié par l'audit
architecture/sécurité du 08-09/09 (voir `EXECUTIVE_SUMMARY.md`). Remédiation : bascule
temporaire de `products/p2-domain-parser/src/index.ts` sur `eip155:84532` /
`x402.org/facilitator`, round-trip exécuté, puis re-bascule mainnet ci-dessous.

## Preuve

Paiement de bout en bout exécuté via `products/p2-domain-parser/test-payment.mjs`
(`@x402/fetch` + `wrapFetchWithPayment`, wallet testnet jetable détenu et signé par
l'utilisateur — jamais par un agent ou un Worker). Même wallet payeur que la vérification
p3 (`.claude/context/testnet-verified-p3-domain-intelligence.md`).

- **Wallet payeur (testnet)** : `0x2A9b74160288B4d1515d244dC0F5143069cFF6FB`
- **PAY_TO (bénéficiaire)** : `0x762cf9834691286218D873eA04B898E26F0963c5`
- **Endpoint** : `POST https://domain-parser.nordman-tehau.workers.dev/v1/domain/parse`
  (body `{"domain":"sub.example.co.uk"}`)
- **Statut HTTP** : `200` (paiement accepté, ressource livrée — `tld: "co.uk"`, `sld: "example"`)
- **Montant réglé** : 0,001 USDC (prix de `/v1/domain/parse`, `PRICE_USD`)
- **Log Worker** (`wrangler tail`) : `{"ts":1788933059354,"endpoint":"/v1/domain/parse","status":200,"paid":true,"amount":"$0.001"}`
- **Transaction on-chain** : `0xa43a2c9a73e968344be3a56278b3c57cb08da55cede80084d1aaa7339467697f`
  (bloc `0x2c6ca73`, ≈ 2026-09-09T05:51:02Z) —
  https://sepolia.basescan.org/tx/0xa43a2c9a73e968344be3a56278b3c57cb08da55cede80084d1aaa7339467697f
- **Event `Transfer` on-chain** (contrat USDC Base Sepolia
  `0x036CbD53842c5426634e7929541eC2318f3dCF7e`, via `eth_getLogs`, filtré
  `from=payeur`/`to=PAY_TO`) : `value = 0x3e8` = 1000 unités atomiques = 0,001 USDC.
- **Vérification indépendante des soldes** (lecture directe du contrat via `eth_call`,
  bloc avant `0x2c6ca72` / bloc après `0x2c6ca73`) :
  - Payeur : 39,995000 → 39,994000 USDC (−0,001)
  - Bénéficiaire : 0,005000 → 0,006000 USDC (+0,001)

Les deux méthodes (`eth_getLogs` + diff de solde bloc-à-bloc) recoupent exactement le
montant attendu (`PRICE_USD = "$0.001"`, `products/p2-domain-parser/src/index.ts`).

## Note — premier essai raté

Un premier essai (19:50:57 UTC) a été exécuté par erreur contre `domain-intelligence`
(p3, mauvais Worker — variable d'environnement `TARGET_URL`/`WORKER_BASE` restée d'un test
précédent), reçu en `404`. Corrigé en nettoyant les variables d'environnement avant de
relancer contre `domain-parser`. Le run correct est celui documenté ci-dessus.

Un warning `x402: Route "/v1/domain/parse" has an invalid bazaar extension: ... Code
generation from strings disallowed` apparaît dans les logs — même incompatibilité
ajv/Workers déjà classée non bloquante le 09/09 pour p3 (voir `EXECUTIVE_SUMMARY.md`),
pré-existante sur ce produit depuis son déploiement initial, sans effet sur le règlement
du paiement (confirmé par la preuve on-chain ci-dessus).

## Conclusion

Le flow complet (402 → paiement signé par le client → vérification/settlement via le
facilitator → 200 + ressource) fonctionne de bout en bout sur testnet, avec règlement
on-chain vérifié indépendamment (event `Transfer` + diff de solde), pas seulement un 200
HTTP. Condition remplie pour la bascule `eip155:84532` → `eip155:8453` (Base mainnet) sur
`products/p2-domain-parser/src/index.ts` — gap comblé, produit déjà en mainnet depuis le
07/09 (commit `f208ec1`), cette preuve est une remédiation a posteriori et non une nouvelle
bascule.
