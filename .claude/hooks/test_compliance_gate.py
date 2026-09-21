#!/usr/bin/env python3
"""Test manuel du hook compliance-gate.py — pas de framework, cas concrets exécutés en séquence."""
import json
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).parent / "compliance-gate.py"
VERIFICATION_LOG = Path(".claude/context/testnet-verified.md")


def run(tool_name: str, file_path: str, content: str) -> str:
    payload = json.dumps(
        {
            "tool_name": tool_name,
            "tool_input": {"file_path": file_path, "content": content, "new_string": content},
        }
    )
    result = subprocess.run(
        [sys.executable, str(HOOK)], input=payload, capture_output=True, text=True
    )
    return result.stdout.strip()


def check(desc: str, out: str, expect_block: bool) -> None:
    blocked = '"decision": "block"' in out
    if blocked == expect_block:
        print(f"PASS: {desc}")
    else:
        print(f"FAIL: {desc} (sortie: {out!r})")
        sys.exit(1)


def main() -> None:
    VERIFICATION_LOG.unlink(missing_ok=True)

    fake_key = "0x" + "1" * 64

    check(
        "clé privée en dur dans wrangler.jsonc -> bloqué",
        run("Write", "wrangler.jsonc", f'{{"key":"{fake_key}"}}'),
        True,
    )

    check(
        "écriture normale dans wrangler.jsonc -> non bloquée",
        run("Write", "wrangler.jsonc", '{"name":"p1-demo"}'),
        False,
    )

    check(
        "secret en dur dans wrangler.jsonc (fichier versionné) -> bloqué",
        run("Write", "wrangler.jsonc", '{"JWT_SECRET":"abcdef1234567890"}'),
        True,
    )

    check(
        "secret dans .dev.vars (fichier local gitignored) -> non bloqué",
        run("Write", ".dev.vars", 'JWT_SECRET="abcdef1234567890"'),
        False,
    )

    check(
        "bascule testnet->mainnet sans vérification -> bloquée",
        run("Edit", "wrangler.jsonc", '"TEMPO_TESTNET": false'),
        True,
    )

    VERIFICATION_LOG.parent.mkdir(parents=True, exist_ok=True)
    VERIFICATION_LOG.write_text("p1-demo vérifié le 2026-09-06\n", encoding="utf-8")
    check(
        "bascule testnet->mainnet avec vérification -> non bloquée",
        run("Edit", "wrangler.jsonc", '"TEMPO_TESTNET": false'),
        False,
    )
    VERIFICATION_LOG.unlink(missing_ok=True)

    check(
        "clé privée dans un fichier hors config wrangler -> non bloqué (hors périmètre du hook)",
        run("Write", "src/index.ts", f'const k = "{fake_key}";'),
        False,
    )

    check(
        "NETWORK: base sans vérification -> bloqué",
        run("Edit", "wrangler.jsonc", '"NETWORK": "base"'),
        True,
    )

    VERIFICATION_LOG.parent.mkdir(parents=True, exist_ok=True)
    VERIFICATION_LOG.write_text("p1-demo vérifié le 2026-09-06\n", encoding="utf-8")
    check(
        "NETWORK: base avec vérification -> non bloqué",
        run("Edit", "wrangler.jsonc", '"NETWORK": "base"'),
        False,
    )
    VERIFICATION_LOG.unlink(missing_ok=True)

    check(
        "MAINNET: true sans vérification -> bloqué",
        run("Edit", "wrangler.jsonc", '"MAINNET": true'),
        True,
    )

    check(
        "CF_API_TOKEN en dur dans wrangler.jsonc -> bloqué",
        run("Write", "wrangler.jsonc", '{"CF_API_TOKEN":"aaaaaaaaaaaaaaaa"}'),
        True,
    )

    check(
        "TESTNET: true (rester en testnet, état sûr) -> non bloqué",
        run("Edit", "wrangler.jsonc", '"TESTNET": true'),
        False,
    )

    check(
        "MAINNET: false (mainnet désactivé, état sûr) -> non bloqué",
        run("Edit", "wrangler.jsonc", '"MAINNET": false'),
        False,
    )

    print("Tous les cas passent.")


if __name__ == "__main__":
    main()
