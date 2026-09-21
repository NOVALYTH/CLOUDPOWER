// Test de paiement x402 MAINNET reel contre nos 4 produits en prod (Base mainnet, eip155:8453).
//
// ATTENTION : ceci depense de VRAIS USDC, ce n'est pas un test testnet (voir
// products/p4-email-verification/test-payment.mjs pour l'equivalent testnet).
//
// A LANCER TOI-MEME, avec TA propre cle mainnet financee de quelques dollars d'USDC sur
// Base UNIQUEMENT. Ne jamais utiliser une cle qui detient des fonds importants. Ne jamais
// coller cette cle dans une conversation avec un assistant IA ou qui que ce soit d'autre,
// ne jamais la committer, ne jamais la mettre dans un fichier .env local (passe-la en
// variable d'environnement a chaque execution pour eviter qu'elle finisse committee par
// accident). Genere un wallet dedie avec `npm run generate-wallet` si tu n'en as pas deja un.
//
// Prerequis :
//   1. npm install (depuis scripts/x402-mainnet-test)
//   2. Un wallet finance de quelques dollars d'USDC sur Base mainnet (le paiement x402
//      "exact" est gasless pour le payeur -- pas besoin d'ETH pour le gas, le facilitator
//      s'en charge)
//   3. X402_PRIVATE_KEY=0x... TARGET=p2 node test-payment.mjs
//      (PowerShell : $env:X402_PRIVATE_KEY="0x..."; $env:TARGET="p2"; node test-payment.mjs)
//
// TARGET : p1 | p2 | p3 | p4 (defaut p2, le moins cher : $0.001)
// Optionnel : TEST_DOMAIN, TEST_EMAIL, TEST_URL pour personnaliser l'input envoye.

import { privateKeyToAccount } from "viem/accounts";
import { x402Client } from "@x402/core/client";
import { ExactEvmScheme } from "@x402/evm";
import { wrapFetchWithPayment } from "@x402/fetch";

const PRODUCTS = {
	p1: {
		url: "https://markdown-x402.nordman-tehau.workers.dev/convert",
		method: "POST",
		price: "0.005",
		body: () => ({ url: process.env.TEST_URL || "https://example.com" }),
	},
	p2: {
		url: "https://domain-parser.nordman-tehau.workers.dev/v1/domain/parse",
		method: "POST",
		price: "0.001",
		body: () => ({ domain: process.env.TEST_DOMAIN || "example.com" }),
	},
	p3: {
		url: () =>
			`https://domain-intelligence.nordman-tehau.workers.dev/dns?domain=${encodeURIComponent(process.env.TEST_DOMAIN || "example.com")}`,
		method: "GET",
		price: "0.001",
		body: null,
	},
	p4: {
		url: "https://email-verification.nordman-tehau.workers.dev/verify",
		method: "POST",
		price: "0.002",
		body: () => ({ email: process.env.TEST_EMAIL || "user@example.com" }),
	},
};

const PRIVATE_KEY = process.env.X402_PRIVATE_KEY;
const TARGET = process.env.TARGET || "p2";

if (!PRIVATE_KEY || !PRIVATE_KEY.startsWith("0x")) {
	console.error("Manque X402_PRIVATE_KEY (cle mainnet, format 0x...). Voir les commentaires en tete de ce fichier.");
	process.exit(1);
}

const product = PRODUCTS[TARGET];
if (!product) {
	console.error(`TARGET invalide : "${TARGET}". Choix possibles : ${Object.keys(PRODUCTS).join(", ")}`);
	process.exit(1);
}

const account = privateKeyToAccount(PRIVATE_KEY);
const url = typeof product.url === "function" ? product.url() : product.url;

console.log(`Produit                 : ${TARGET} (prix attendu : $${product.price} USDC)`);
console.log(`Wallet mainnet (payeur) : ${account.address}`);
console.log(`Cible                   : ${url}`);
console.log("\nCECI VA DEPENSER DE VRAIS USDC SUR BASE MAINNET.\n");

const client = new x402Client().register("eip155:8453", new ExactEvmScheme(account));
const fetchWithPayment = wrapFetchWithPayment(fetch, client);

const init = { method: product.method };
if (product.body) {
	init.headers = { "Content-Type": "application/json" };
	init.body = JSON.stringify(product.body());
}

console.log("Envoi de la requete payante...\n");
const response = await fetchWithPayment(url, init);

console.log(`Statut : ${response.status}`);
const bodyText = await response.text();
try {
	console.log("Reponse :", JSON.stringify(JSON.parse(bodyText), null, 2));
} catch {
	console.log("Reponse (non-JSON) :", bodyText);
}

if (response.status === 200) {
	console.log(
		`\nPaiement mainnet reussi. Verifier la transaction sur https://basescan.org/address/${account.address}`,
	);
} else {
	console.error("\nEchec -- pas de paiement accepte. Verifier le solde USDC du wallet sur Base et la config du Worker.");
	process.exit(1);
}
