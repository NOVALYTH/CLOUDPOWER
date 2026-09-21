#!/usr/bin/env python3
"""PreToolUse hook — bloque les secrets en dur et une bascule testnet->mainnet non
vérifiée dans la config Wrangler/env de cloudflare-monetization."""
import json
import re
import sys
from pathlib import Path

WRANGLER_CONFIG_PATTERN = re.compile(r"wrangler\.(jsonc?|toml)$", re.IGNORECASE)
# Code source versionné d'un produit — c'est là que vit NETWORK avec x402 v2
# (@x402/hono déclare le réseau par route, pas via une var wrangler globale).
PRODUCT_SOURCE_PATTERN = re.compile(
    r"products[/\\][^/\\]+[/\\]src[/\\].*\.tsx?$", re.IGNORECASE
)
RELEVANT_FILE_PATTERN = re.compile(
    r"(wrangler\.(jsonc?|toml)$|\.dev\.vars(\.|$)|products[/\\][^/\\]+[/\\]src[/\\].*\.tsx?$)",
    re.IGNORECASE,
)

PRIVATE_KEY_PATTERN = re.compile(r"0x[a-fA-F0-9]{64,}")
# {64,} (pas {64} exact) est deliberе : avec {64}, `finditer` sur une cle collee
# immediatement apres le hash public allowlist (sans separateur, ex.
# "<hash allowlist><64 hex de cle reelle>") ne matchait QUE les 64 premiers
# caracteres (= le hash connu, laisse passer), puis reprenait la recherche
# APRES ce match — donc a l'interieur de la cle, qui ne commence plus par
# "0x" et n'etait donc jamais detectee. {64,} consomme goulument toute la
# suite hexadecimale contigue ; un hash allowliste isole reste matche a
# exactement 64 caracteres (donc toujours reconnu), mais tout ce qui colle
# davantage de hex derriere devient une chaine plus longue qui NE correspond
# plus a aucune entree de KNOWN_PUBLIC_HASHES et bloque comme avant.
# Constantes publiques connues qui matchent la FORME d'une cle privee (0x + 64 hex)
# sans en etre une — chacune ajoutee ici a ete verifiee manuellement avant l'ajout.
# Correspondance EXACTE uniquement (pas de regle generale du type "commente comme
# public") : ajouter une entree est une decision de securite au cas par cas, jamais
# un mecanisme de contournement reutilisable. Ne JAMAIS y ajouter une valeur dont la
# nature publique n'est pas positivement etablie (hash d'evenement standard publie,
# adresse de contrat verifiee sur un explorateur, etc.) — dans le doute, laisser le
# hook bloquer et escalader plutot que d'etendre cette liste.
KNOWN_PUBLIC_HASHES = {
    # keccak256("Transfer(address,address,uint256)") — signature d'evenement ERC-20
    # standard, identique sur tous les contrats/toutes les chaines EVM, publiee
    # partout (EIP-20, Etherscan, etc.). Utilisee comme filtre de log ("topics[0]")
    # dans products/ops-dashboard/src/onchain.ts, jamais comme cle de signature.
    "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",
}
SECRET_LITERAL_PATTERN = re.compile(
    r'["\']?[A-Z0-9_]*(SECRET|PRIVATE_KEY|API_KEY|TOKEN|SEED|MNEMONIC)[A-Z0-9_]*["\']?\s*[:=]\s*'
    r'["\'](?!\$\{)[^"\']{8,}["\']',
    re.IGNORECASE,
)
TESTNET_DISABLE_PATTERN = re.compile(
    r'["\']?[A-Z0-9_]*TESTNET[A-Z0-9_]*["\']?\s*[:=]\s*false',
    re.IGNORECASE,
)
# Formes historiques (mpp-proxy : NETWORK: "base"/true) + formes CAIP-2 réelles
# utilisées par x402 v2 pour les mainnets EVM pertinents pour ce projet (Base).
# Étendre KNOWN_EVM_MAINNET_CAIP2 si un autre mainnet EVM est ajouté au projet.
KNOWN_EVM_MAINNET_CAIP2 = ["eip155:8453"]  # Base mainnet
MAINNET_ENABLE_PATTERN = re.compile(
    r'["\']?[A-Z0-9_]*(NETWORK|MAINNET)[A-Z0-9_]*["\']?\s*[:=]\s*'
    r'(true|"mainnet"|\'mainnet\'|"base"|\'base\''
    + "".join(rf'|"{re.escape(cid)}"|\'{re.escape(cid)}\'' for cid in KNOWN_EVM_MAINNET_CAIP2)
    + r")",
    re.IGNORECASE,
)

PRODUCT_FOLDER_PATTERN = re.compile(r"products[/\\]([^/\\]+)[/\\]")

# Un fichier de preuve par produit — évite qu'une vérification testnet de p1 ne serve
# silencieusement de laissez-passer pour une bascule mainnet de p2/p3/... jamais testée.
# Fallback sur l'ancien chemin partagé si le produit n'a pas pu être extrait du chemin
# (ne devrait pas arriver vu RELEVANT_FILE_PATTERN, mais on ne bloque pas à l'aveugle).
def verification_log_for(file_path: str) -> Path:
    match = PRODUCT_FOLDER_PATTERN.search(file_path)
    if match:
        return Path(f".claude/context/testnet-verified-{match.group(1)}.md")
    return Path(".claude/context/testnet-verified.md")


def block(reason: str) -> None:
    print(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(0)


def main() -> None:
    payload = json.load(sys.stdin)
    if payload.get("tool_name") not in ("Write", "Edit"):
        return

    tool_input = payload.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    content = tool_input.get("content") or tool_input.get("new_string", "")

    if not RELEVANT_FILE_PATTERN.search(file_path):
        return

    if PRIVATE_KEY_PATTERN.search(content):
        unknown_hex64 = [
            m.group(0)
            for m in PRIVATE_KEY_PATTERN.finditer(content)
            if m.group(0).lower() not in KNOWN_PUBLIC_HASHES
        ]
        if unknown_hex64:
            block(
                f"Motif de clé privée blockchain détecté dans '{file_path}'. Jamais de clé "
                "privée dans un fichier de config — voir CLAUDE.md > RÈGLES ABSOLUES > Sécurité."
            )

    # wrangler.jsonc/toml et le code source d'un produit sont tous les deux versionnés
    # (commités) — contrairement à .dev.vars (gitignored, échappatoire dev local).
    is_versioned_config = WRANGLER_CONFIG_PATTERN.search(file_path) or PRODUCT_SOURCE_PATTERN.search(
        file_path
    )

    if is_versioned_config and SECRET_LITERAL_PATTERN.search(content):
        block(
            f"Secret en dur détecté dans '{file_path}' (fichier versionné). Utiliser "
            "`wrangler secret put`, ou déplacer la valeur dans `.dev.vars` (gitignored) "
            "pour le développement local."
        )

    if is_versioned_config and (
        TESTNET_DISABLE_PATTERN.search(content) or MAINNET_ENABLE_PATTERN.search(content)
    ):
        verification_log = verification_log_for(file_path)
        if not verification_log.exists():
            block(
                f"Bascule testnet -> mainnet détectée dans '{file_path}' sans "
                f"vérification enregistrée pour ce produit. Créer '{verification_log}' "
                "avec la preuve d'une transaction testnet vérifiée pour CE produit avant "
                "de basculer (une preuve d'un autre produit ne compte pas)."
            )


if __name__ == "__main__":
    main()
