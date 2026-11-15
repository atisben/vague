"""Deterministic inventory of the Obsidian vault for the /vault-clean skill, and `vague vault-scan`.

The scanner measures, it never decides. It reports each note's kind, age, inbound links
and hygiene issues, groups likely duplicates, and lists archived notes past their grace
period. The skill and the user decide what to merge, refresh or retire.
"""

from __future__ import annotations

import json
import math
import os
import re
import sys
import unicodedata
from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Literal

import frontmatter
import typer

Kind = Literal["record", "knowledge", "plan"]

ARCHIVE_DIR = "9. Archive"
# Obsidian internals, templates, binary attachments and plugin-owned drawings are not notes to clean.
SKIPPED_DIRS = frozenset({"5. Templates", "7. Attachments", "8. Excalidraw", "Excalidraw"})
TEMPLATE_SECTIONS = ("# Next Actions", "# References")

_TAG_PATTERN = re.compile(r"^[a-z0-9_/-]+$")
_WIKILINK_PATTERN = re.compile(r"!?\[\[([^\]|#]+)")
_HEADING_LINE = re.compile(r"^#{1,6} .*$", re.MULTILINE)
_H1_DATE = re.compile(r"^# (\d{4}-\d{2}-\d{2})\b", re.MULTILINE)

# A record is history (a review, an interview, a meeting): fix its hygiene, never rewrite it.
_RECORD_TITLE = re.compile(
    r"perf review|review prep|\binterview|entretien|coaching|conversation|\bmeeting\b|\bretro\b|\b1[:-]1\b",
    re.IGNORECASE,
)
_RECORD_TAGS = frozenset({"job_interview", "decision", "management", "meeting", "perf_review"})
# A plan expires once its work ships: distill the decisions, then archive it.
_PLAN_TITLE = re.compile(r"\bplan\b|critique|proposal|\brfc\b|roadmap", re.IGNORECASE)

_STOPWORDS = frozenset(
    "the a an and or of to in on for with by at from is are be this that it as how what why "
    "le la les de des du un une et en au aux pour sur par dans avec est".split()
)
# Two titles this alike name the same subject; Jane's and Max's reviews share only the template words.
TITLE_THRESHOLD = 0.7
# Bodies this alike repeat the same content even when the titles differ.
BODY_THRESHOLD = 0.6
# Shorter bodies have too few words for a cosine to mean anything.
MIN_BODY_TOKENS = 15


@dataclass(frozen=True)
class Note:
    path: str
    title: str
    kind: Kind
    kind_source: Literal["frontmatter", "guess"]
    status: str
    tags: list[str]
    age_days: int
    words: int
    inbound: int
    agent_written: bool
    issues: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Report:
    notes: list[Note]
    clusters: list[list[str]]
    expired: list[str]


@dataclass(frozen=True)
class _Parsed:
    path: Path
    rel: str
    meta: dict
    body: str
    has_frontmatter: bool
    parse_error: bool


def _fold(text: str) -> str:
    """Lowercase and strip accents, so `Planche à voile` and `planche a voile` compare equal."""
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()


def _tokens(text: str, min_len: int = 2) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", _fold(text)) if len(t) >= min_len and t not in _STOPWORDS]


def _jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def _cosine(a: Counter[str], b: Counter[str]) -> float:
    dot = sum(count * b[word] for word, count in a.items() if word in b)
    norm = math.sqrt(sum(v * v for v in a.values())) * math.sqrt(sum(v * v for v in b.values()))
    return dot / norm if norm else 0.0


def _markdown_files(vault: Path) -> Iterator[Path]:
    for dirpath, dirnames, filenames in os.walk(vault):
        top = Path(dirpath).relative_to(vault).parts
        if top and top[0] in SKIPPED_DIRS:
            dirnames[:] = []
            continue
        dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
        for name in sorted(filenames):
            if name.endswith(".md"):
                yield Path(dirpath) / name


def _parse(path: Path, vault: Path) -> _Parsed:
    text = path.read_text(encoding="utf-8", errors="replace")
    rel = path.relative_to(vault).as_posix()
    if not text.startswith("---"):
        return _Parsed(path=path, rel=rel, meta={}, body=text, has_frontmatter=False, parse_error=False)
    try:
        post = frontmatter.loads(text)
    except Exception:
        return _Parsed(path=path, rel=rel, meta={}, body=text, has_frontmatter=True, parse_error=True)
    return _Parsed(path=path, rel=rel, meta=dict(post.metadata), body=post.content, has_frontmatter=True,
                   parse_error=False)


def _as_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, Iterable):
        return [str(v) for v in value if v is not None and str(v).strip()]
    return [str(value)]


def _declared_kind(value: object) -> Kind | None:
    """The `kind:` a note's frontmatter states, or None when it states none or an unknown one."""
    text = str(value or "").strip()
    if text == "record":
        return "record"
    if text == "knowledge":
        return "knowledge"
    if text == "plan":
        return "plan"
    return None


def _guess_kind(title: str, tags: list[str]) -> Kind:
    # Titles first: /plan-eng tags every plan `decision`, so a tag alone would turn plans into records.
    if _RECORD_TITLE.search(title):
        return "record"
    if _PLAN_TITLE.search(title):
        return "plan"
    if _RECORD_TAGS & set(tags):
        return "record"
    return "knowledge"


def _issues(parsed: _Parsed, tags: list[str]) -> list[str]:
    if not parsed.has_frontmatter:
        found = ["no-frontmatter"]
    elif parsed.parse_error:
        found = ["bad-frontmatter"]
    else:
        found = [] if tags else ["no-tags"]
        found += [f"bad-tag: {t}" for t in tags if not _TAG_PATTERN.match(t)]
    lines = {line.strip() for line in parsed.body.splitlines()}
    if not all(section in lines for section in TEMPLATE_SECTIONS):
        found.append("missing-sections")
    return found


def _content_vector(body: str) -> Counter[str]:
    """Word counts of the body without headings, so the shared template does not look like shared content."""
    return Counter(_tokens(_HEADING_LINE.sub("", body), min_len=3))


def _clusters(parsed: list[_Parsed]) -> list[list[str]]:
    titles = [set(_tokens(p.path.stem)) for p in parsed]
    vectors = [_content_vector(p.body) for p in parsed]
    parent = list(range(len(parsed)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(len(parsed)):
        for j in range(i + 1, len(parsed)):
            alike_titles = _jaccard(titles[i], titles[j]) >= TITLE_THRESHOLD
            long_enough = min(sum(vectors[i].values()), sum(vectors[j].values())) >= MIN_BODY_TOKENS
            alike_bodies = long_enough and _cosine(vectors[i], vectors[j]) >= BODY_THRESHOLD
            if alike_titles or alike_bodies:
                parent[find(i)] = find(j)

    groups: dict[int, list[str]] = {}
    for i, p in enumerate(parsed):
        groups.setdefault(find(i), []).append(p.rel)
    return sorted(sorted(g) for g in groups.values() if len(g) > 1)


def _written_on(parsed: _Parsed) -> date:
    """The date in the template's H1 heading. File times move whenever a sync tool touches the vault."""
    if match := _H1_DATE.search(parsed.body):
        try:
            return date.fromisoformat(match.group(1))
        except ValueError:
            pass
    return date.fromtimestamp(parsed.path.stat().st_mtime)


def _archived_on(parsed: _Parsed) -> date:
    value = parsed.meta.get("archived")
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value.strip())
        except ValueError:
            pass
    return date.fromtimestamp(parsed.path.stat().st_mtime)


def scan(vault: Path, today: date, agent_paths: Iterable[str] = (), grace_days: int = 90) -> Report:
    """Inventory every note under `vault`. Notes in the archive only feed `expired`."""
    agent = {os.path.realpath(p) for p in agent_paths}
    parsed = [_parse(path=p, vault=vault) for p in _markdown_files(vault=vault)]
    live = [p for p in parsed if not p.rel.startswith(f"{ARCHIVE_DIR}/")]
    archived = [p for p in parsed if p.rel.startswith(f"{ARCHIVE_DIR}/")]

    inbound: Counter[str] = Counter()
    for p in live:
        targets = {Path(t.strip()).stem.lower() for t in _WIKILINK_PATTERN.findall(p.body)}
        targets.discard(p.path.stem.lower())
        inbound.update(targets)

    notes: list[Note] = []
    for p in live:
        tags = _as_list(p.meta.get("tags"))
        declared = _declared_kind(value=p.meta.get("kind"))
        names = [p.path.stem, *_as_list(p.meta.get("aliases"))]
        notes.append(Note(
            path=p.rel,
            title=p.path.stem,
            kind=declared or _guess_kind(title=p.path.stem, tags=tags),
            kind_source="frontmatter" if declared else "guess",
            status=str(p.meta.get("status") or ""),
            tags=tags,
            age_days=(today - _written_on(parsed=p)).days,
            words=len(p.body.split()),
            inbound=max(inbound[n.lower()] for n in names),
            agent_written=os.path.realpath(p.path) in agent,
            issues=_issues(parsed=p, tags=tags),
        ))

    expired = sorted(p.rel for p in archived if (today - _archived_on(parsed=p)).days > grace_days)
    return Report(notes=notes, clusters=_clusters(parsed=live), expired=expired)


def similar(vault: Path, title: str) -> list[str]:
    """Live notes whose title covers the words of `title`, for the /vault dedup check before a save."""
    query = set(_tokens(title))
    if not query:
        return []
    found = []
    for path in _markdown_files(vault=vault):
        rel = path.relative_to(vault).as_posix()
        if rel.startswith(f"{ARCHIVE_DIR}/"):
            continue
        words = set(_tokens(path.stem))
        if query <= words or _jaccard(query, words) >= 0.5:
            found.append(rel)
    return found


def default_vault() -> Path:
    return Path(os.environ.get("VAGUE_VAULT") or Path.home() / "Obsidian")


def _agent_paths() -> list[str]:
    """Every file a skill logged as a doc memory: the notes an agent wrote."""
    from vague.memory import fold, load_ledger

    return [f for m in fold(load_ledger()) if m.kind == "doc" for f in m.files]


def cmd_vault_scan(vault: Path, as_json: bool, similar_to: str | None, grace_days: int) -> None:
    if not vault.is_dir():
        print(f"vague vault-scan: no such vault directory: {vault}", file=sys.stderr)
        raise typer.Exit(code=2)

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
