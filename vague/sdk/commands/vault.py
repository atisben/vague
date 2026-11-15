"""vague vault-scan command: inventory the Obsidian vault for /vault-clean and the /vault dedup check."""

from __future__ import annotations

import json
import os
import sys
from collections import Counter
from dataclasses import asdict
from datetime import date
from pathlib import Path

import typer


def default_vault() -> Path:
    return Path(os.environ.get("VAGUE_VAULT") or Path.home() / "Obsidian")


def _agent_paths() -> list[str]:
    """Every file a skill logged as a doc memory: the notes an agent wrote."""
    from vague.sdk.core.memory import fold, load_ledger

    return [f for m in fold(load_ledger()) if m.kind == "doc" for f in m.files]


def cmd_vault_scan(vault: Path, as_json: bool, similar_to: str | None, grace_days: int) -> None:
    if not vault.is_dir():
        print(f"vague vault-scan: no such vault directory: {vault}", file=sys.stderr)
        raise typer.Exit(code=2)

    from vague.sdk.core.vault_scan import scan, similar

    if similar_to is not None:
        found = similar(vault=vault, title=similar_to)
        print("SIMILAR: " + (" | ".join(found) if found else "none"))
        return

    report = scan(vault=vault, today=date.today(), agent_paths=_agent_paths(), grace_days=grace_days)
    if as_json:
        print(json.dumps(asdict(report), ensure_ascii=False, indent=1))
        return

    by_path = {n.path: n for n in report.notes}
    kinds = Counter(n.kind for n in report.notes)
    out = [
        f"VAULT: {vault}",
        f"NOTES: {len(report.notes)} (record {kinds['record']}, knowledge {kinds['knowledge']}, plan {kinds['plan']})"
        f"  ORPHANS: {sum(n.inbound == 0 for n in report.notes)}"
        f"  AGENT-WRITTEN: {sum(n.agent_written for n in report.notes)}",
        "",
        "== HYGIENE",
        *[f"{n.path}: {', '.join(n.issues)}" for n in report.notes if n.issues],
        "",
        "== CLUSTERS (likely duplicates)",
    ]
    for number, cluster in enumerate(report.clusters, start=1):
        out.append(f"{number}.")
        out += [f"   [{by_path[p].kind}] {p}  age={by_path[p].age_days}d in={by_path[p].inbound}" for p in cluster]
    out += ["", "== PLANS"]
    out += [f"{n.path}  status={n.status or 'unset'} age={n.age_days}d agent={'yes' if n.agent_written else 'no'}"
            for n in report.notes if n.kind == "plan"]
    out += ["", "== GUESSED KINDS (no `kind:` in frontmatter)"]
    for kind in ("record", "plan", "knowledge"):
        titles = [n.title for n in report.notes if n.kind == kind and n.kind_source == "guess"]
        out.append(f"{kind} ({len(titles)}): " + (" | ".join(titles) if titles else "none"))
    out += ["", f"== EXPIRED (archived over {grace_days} days ago)", *(report.expired or ["none"])]
    print("\n".join(out))
