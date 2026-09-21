# x402-mainnet-test

Client x402 minimal pour valider par un **vrai paiement mainnet** le paywall de p1-p4, en
remplacement des tests curl/testnet manuels. Outil de test interne, pas un produit — ne pas
déployer sur Cloudflare, ne pas ajouter à `products/`.

Contexte : deux incidents récents (facilitator qui hang/plante silencieusement sur p3) n'ont été
détectés que par hasard. `wrangler tail` propre ne prouve pas qu'un paiement réel aboutit — ce
script le prouve directement.

## Sécurité — à lire avant usage

- Ce script **dépense de vrais USDC sur Base mainnet**. Ce n'est pas un test testnet (voir
  `products/p4-email-verification/test-payment.mjs` pour l'équivalent testnet).
- N'utilise **jamais** une clé qui détient des fonds importants. Génère un wallet dédié
  (`npm run generate-wallet`) et ne le finance que de quelques dollars.
- Ne colle **jamais** la clé privée dans une conversation avec un assistant IA ou qui que ce soit
  d'autre, ne la commit jamais, et ne la mets pas dans un fichier `.env` local — passe-la en
  variable d'environnement à chaque exécution pour limiter le risque qu'elle finisse committée par
  accident.

## Usage

```bash
npm install

# 1. Générer un wallet de test dédié (une seule fois)
npm run generate-wallet

# 2. Financer l'adresse affichée avec quelques dollars d'USDC sur Base mainnet
#    (depuis un exchange ou un wallet existant — pas besoin d'ETH, le paiement "exact"
#    est gasless côté payeur, le facilitator paie le gas du règlement)

# 3. Lancer un paiement réel contre l'un des 4 produits
X402_PRIVATE_KEY=0x... TARGET=p2 node test-payment.mjs
```

PowerShell :
```powershell
$env:X402_PRIVATE_KEY="0x..."; $env:TARGET="p2"; node test-payment.mjs
```

`TARGET` : `p1` (markdown, $0.005) | `p2` (domain-parser, $0.001, défaut — le moins cher) |
`p3` (domain-intelligence `/dns`, $0.001) | `p4` (email-verification, $0.002).

Variables optionnelles pour personnaliser l'input envoyé : `TEST_URL` (p1), `TEST_DOMAIN` (p2/p3),
`TEST_EMAIL` (p4).

### Tester les 4 produits d'un coup

```powershell
$env:X402_PRIVATE_KEY="0x..."; .\test-all.ps1
# ou un sous-ensemble :
$env:X402_PRIVATE_KEY="0x..."; .\test-all.ps1 -Targets p1,p3,p4
```

Coût total pour les 4 : $0.008 USDC ($0.005 + $0.001 + $0.001 + $0.002... a ajuster si les prix
changent, voir la table ci-dessus).

## Ce que ça valide

Un round-trip complet : 402 → signature EIP-3009 hors-chaîne (`ExactEvmScheme`) → soumission au
facilitator configuré côté Worker (PayAI) → règlement on-chain → 200 avec la réponse du produit. Un
statut différent de 200 (ou un hang) signale un vrai problème de paywall en prod — vérifier le
solde USDC du wallet de test avant de conclure à un bug côté Worker.
