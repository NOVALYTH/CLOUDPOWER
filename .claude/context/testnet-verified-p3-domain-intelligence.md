# Vérification testnet — domain-intelligence

**Date** : 2026-09-08
**Produit** : `products/p3-domain-intelligence`
**Réseau** : Base Sepolia (`eip155:84532`)
**Protocole** : x402 v2 (`@x402/hono` + `@x402/evm` + `@x402/core`, v2.25.0)
**Facilitator** : `https://x402.org/facilitator` (public, testnet, défaut de `X402_FACILITATOR_URL`)

## Preuve

Paiement de bout en bout exécuté via `products/p3-domain-intelligence/test-payment.mjs`
(`@x402/fetch` + `wrapFetchWithPayment`, wallet testnet jetable détenu et signé par
l'utilisateur — jamais par un agent ou un Worker).

- **Wallet payeur (testnet)** : `0x2A9b74160288B4d1515d244dC0F5143069cFF6FB`
- **X402_RECIPIENT_ADDRESS (bénéficiaire)** : `0x762cf9834691286218D873eA04B898E26F0963c5`
- **Endpoint** : `GET https://domain-intelligence.nordman-tehau.workers.dev/dns?domain=example.com`
- **Statut HTTP** : `200` (paiement accepté, ressource livrée)
- **Montant réglé** : 0,001 USDC (prix de `/dns`, `PRICE_USD.dns`)
- **Transaction on-chain** : `0x85f23acd9ab252642c0c5d21ca901c46ba086bcb93fbfa443b63e60fb83fc0b3`
  (bloc `0x2c62dd3`) — https://sepolia.basescan.org/tx/0x85f23acd9ab252642c0c5d21ca901c46ba086bcb93fbfa443b63e60fb83fc0b3
- **Vérification indépendante des soldes** (lecture directe du contrat USDC Base Sepolia
  `0x036CbD53842c5426634e7929541eC2318f3dCF7e` via `eth_call`, avant/après) :
  - Payeur : 20,000000 → 19,999000 USDC (−0,001)
  - Bénéficiaire : 0,000000 → 0,001000 USDC (+0,001)

## Complément — 2026-09-08, `/rdap`, `/tls`, `/intelligence`

Les 3 routes restantes ont été exercées séparément par l'utilisateur via `test-payment.mjs`
(même wallet payeur testnet `0x2A9b74160288B4d1515d244dC0F5143069cFF6FB`), statuts HTTP 200
rapportés. Vérification indépendante via `eth_getLogs` sur le contrat USDC Base Sepolia
(RPC public `https://sepolia.base.org`, aucune clé requise), filtrée sur les événements
`Transfer` vers `X402_RECIPIENT_ADDRESS` depuis le bloc de la transaction `/dns` :

| Route | Transaction | Montant on-chain | `PRICE_USD` attendu |
|---|---|---|---|
| `/rdap` | [`0x6268f274…0820a27`](https://sepolia.basescan.org/tx/0x6268f2748113b4bbe71a86ff0db47ef2d7747b6bf8419476b6179e9b90820a27) (bloc `0x2c63017`) | 0,001 USDC | 0,001 ✓ |
| `/tls` | [`0xae14bd65…875f522b1`](https://sepolia.basescan.org/tx/0xae14bd65668672ea4ae55fb23d151ba986d43456f8d0542cbf8ec88875f522b1) (bloc `0x2c63029`) | 0,001 USDC | 0,001 ✓ |
| `/intelligence` | [`0x958621e5…f66067d3d`](https://sepolia.basescan.org/tx/0x958621e5923f44fd1d93a1e9bc591ac306b1f7f71d6b3f28e050210f66067d3d) (bloc `0x2c6303d`) | 0,002 USDC | 0,002 ✓ |

Les 4 montants correspondent exactement à `PRICE_USD` (`products/p3-domain-intelligence/src/pricing.ts`).

## Conclusion

Le flow complet (402 → paiement signé par le client → vérification/settlement via le
facilitator → 200 + ressource) fonctionne de bout en bout sur testnet, avec règlement
on-chain vérifié indépendamment pour les **4 routes payantes** (pas seulement un 200 HTTP —
le mouvement de fonds réel a été confirmé par lecture directe de la blockchain pour chacune).
Condition remplie pour envisager une bascule `eip155:84532` → `eip155:8453` (Base mainnet)
sur l'ensemble de `products/p3-domain-intelligence/src/http/router.ts`. Le prix de `/tls`
et `/intelligence` reste toutefois qualifié de "non final" dans le code
(`src/pricing.ts`, commentaire) en attendant une décision explicite de le figer — la
validation ci-dessus porte sur le *mécanisme* de paiement, pas sur le caractère définitif
du *montant* facturé.
