# Vérification testnet — markdown-x402

**Date** : 2026-09-07
**Produit** : `products/p1-markdown-x402`
**Réseau** : Base Sepolia (`eip155:84532`)
**Protocole** : x402 v2 (`@x402/hono` + `@x402/evm` + `@x402/core`, v2.25.0)
**Facilitator** : `https://x402.org/facilitator` (public, testnet)

## Preuve

Paiement de bout en bout exécuté via `products/p1-markdown-x402/test-payment.mjs`
(`@x402/fetch` + `wrapFetchWithPayment`, wallet testnet jetable détenu et signé par
l'utilisateur — jamais par un agent ou un Worker).

- **Wallet payeur (testnet)** : `0x9a78e7922C5E08340a566E517aDE6b0c49108AF6`
- **PAY_TO (bénéficiaire)** : `0xE24269769477f9d7604c88fb3A0800A06Fe9ba01`
- **Endpoint** : `POST https://markdown-x402.nordman-tehau.workers.dev/convert`
- **Statut HTTP** : `200` (paiement accepté, ressource livrée)
- **Réponse** : conversion réussie de `https://example.com` (20 mots, 42 Neurons Workers AI)
- **Horodatage réponse** : `2026-09-07T06:03:21.846Z`
- **Vérification on-chain** : https://sepolia.basescan.org/address/0x9a78e7922C5E08340a566E517aDE6b0c49108AF6

## Conclusion

Le flow complet (402 → paiement signé par le client → vérification/settlement via le
facilitator → 200 + ressource) fonctionne de bout en bout sur testnet. Condition remplie
pour envisager une bascule `eip155:84532` → `eip155:8453` (Base mainnet) dans
`products/p1-markdown-x402/src/index.ts`, selon x402-payments.md §3.
