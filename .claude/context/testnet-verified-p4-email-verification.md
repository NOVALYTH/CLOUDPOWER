# Vérification testnet — email-verification

**Date** : 2026-09-12
**Produit** : `products/p4-email-verification`
**Réseau** : Base Sepolia (`eip155:84532`)
**Protocole** : x402 v2 (`@x402/hono` + `@x402/evm` + `@x402/core`, v2.25.0)
**Facilitator** : `https://x402.org/facilitator` (public, testnet, défaut de `getFacilitatorUrl()`)

## Preuve

Paiement de bout en bout exécuté via `products/p4-email-verification/test-payment.mjs`
(`@x402/fetch` + `wrapFetchWithPayment`, wallet testnet jetable détenu et signé par
l'utilisateur — jamais par un agent ou un Worker). Wallet payeur dédié à ce round-trip,
distinct de celui utilisé pour p2/p3, dérivé du même MetaMask que `PAY_TO` mais sans lien
cryptographique avec lui (comptes HD indépendants).

- **Wallet payeur (testnet)** : `0x70D67f27b88Ef4b37AE861a36C3D8B7132eB6436`
- **PAY_TO (bénéficiaire)** : `0x762cf9834691286218D873eA04B898E26F0963c5` (même wallet que
  p1/p2/p3)
- **Endpoint** : `POST https://email-verification.nordman-tehau.workers.dev/verify`
  (body `{"email":"user@example.com"}`)
- **Statut HTTP** : `200` (paiement accepté, ressource livrée — `valid_syntax: true`,
  `domain: "example.com"`, `mx_found: true`, `disposable: false`, `risk: "low"`)
- **Montant réglé** : 0,002 USDC (prix de `/verify`, `products/p4-email-verification/src/pricing.ts`)
- **Transaction on-chain** : `0xf5ad7f7819f2b8ffc0b67e6579cf594464a8fcdc2b01922257aac3db375f6b4d`
  (bloc `46710501` / `0x2c8bee5`, 2026-09-12T05:01:30Z) —
  https://sepolia.basescan.org/tx/0xf5ad7f7819f2b8ffc0b67e6579cf594464a8fcdc2b01922257aac3db375f6b4d
- **Event `Transfer` on-chain** (contrat USDC Base Sepolia
  `0x036CbD53842c5426634e7929541eC2318f3dCF7e`, via `eth_getLogs` sur le RPC public
  `https://sepolia.base.org`, filtré `from=payeur`/`to=PAY_TO`) :
  `data = 0x7d0` = 2000 unités atomiques = 0,002 USDC.
- **Vérification indépendante des soldes** (lecture directe du contrat via `eth_call`,
  bloc avant `0x2c8bee4` / bloc après `0x2c8bee5`) :
  - Payeur : 20,000000 → 19,998000 USDC (−0,002)
  - Bénéficiaire : 0,006000 → 0,008000 USDC (+0,002)

Les deux méthodes (`eth_getLogs` + diff de solde bloc-à-bloc) recoupent exactement le
montant attendu (`PRICE_USD` de `/verify`, `products/p4-email-verification/src/pricing.ts`).

## Note — vérification BaseScan UI non utilisée

Une tentative de vérification via l'interface web `sepolia.basescan.org` a été bloquée par
son écran de vérification anti-bot ; contourner un tel écran est explicitement hors des
actions permises. La vérification ci-dessus repose donc entièrement sur des appels RPC
directs et indépendants (`eth_getLogs`, `eth_call`) plutôt que sur une lecture de l'UI —
même rigueur, source différente. Le lien BaseScan est fourni ci-dessus pour une relecture
humaine ultérieure.

## Conclusion

Le flow complet (402 → paiement signé par le client → vérification/settlement via le
facilitator → 200 + ressource) fonctionne de bout en bout sur testnet, avec règlement
on-chain vérifié indépendamment (event `Transfer` + diff de solde), pas seulement un 200
HTTP. Condition remplie pour la bascule `eip155:84532` → `eip155:8453` (Base mainnet) sur
`products/p4-email-verification` (Task 7 du plan
`docs/superpowers/plans/2026-09-10-p4-email-verification.md`).
