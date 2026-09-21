// Genere un nouveau wallet EVM jetable, a usage UNIQUEMENT pour test-payment.mjs.
//
// Ne finance JAMAIS ce wallet avec plus que quelques dollars d'USDC -- c'est un outil
// de validation technique du paywall, pas un wallet de tresorerie. Garde la cle privee
// affichee ci-dessous en local uniquement : jamais dans Git, jamais collee dans une
// conversation avec un assistant IA ou qui que ce soit d'autre.

import { generatePrivateKey, privateKeyToAccount } from "viem/accounts";

const privateKey = generatePrivateKey();
const account = privateKeyToAccount(privateKey);

console.log("Nouveau wallet de test genere.\n");
console.log(`Adresse    : ${account.address}`);
console.log(`Cle privee : ${privateKey}`);
console.log("\nGarde la cle privee en lieu sur (gestionnaire de mots de passe, pas un fichier du repo).");
console.log("Finance cette adresse avec quelques dollars d'USDC sur Base MAINNET, puis lance par exemple :");
console.log(`  X402_PRIVATE_KEY=${privateKey} TARGET=p2 node test-payment.mjs`);
