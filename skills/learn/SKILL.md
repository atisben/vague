---
name: learn
version: 1.0.0
description: |
  Manage project learnings: review, search, prune, export.
  Trigger: "what have we learned", "show learnings", "prune stale learnings",
  "export learnings", "didn't we fix this before?".
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - AskUserQuestion
---

## Preamble

```bash
export BS_SKILL_NAME="learn"
source "$(dirname "$0")/../_preamble.sh"
```

**Proactive invocation:** Suggest when the user asks about past patterns or wonders "didn't we fix this before?"

---

## Detect Command

Parse the user's input:
- `/learn` (no args) → **show recent**
- `/learn search <query>` → **search**
- `/learn prune` → **prune**
- `/learn export` → **export**
- `/learn stats` → **stats**
- `/learn add` → **manual add**

---

## Show Recent (default)

```bash
eval "$(~/.bastack/bin/bs-slug 2>/dev/null)"
~/.bastack/bin/bs-learnings-search --limit 20 2>/dev/null || echo "No learnings yet."
```

If no learnings: "No learnings recorded yet. As you use /review, /ship, /investigate, and /retro, bastack will automatically capture patterns, pitfalls, and insights it discovers."

---

## Search

```bash
eval "$(~/.bastack/bin/bs-slug 2>/dev/null)"
~/.bastack/bin/bs-learnings-search --query "USER_QUERY" --limit 20 2>/dev/null || echo "No matches."
```

---

## Prune

Check for stale and contradictory entries.

```bash
eval "$(~/.bastack/bin/bs-slug 2>/dev/null)"
~/.bastack/bin/bs-learnings-search --limit 100 2>/dev/null
```

For each learning:
1. **File existence check**: if it has a `files` field, check those files still exist with `ls [file]`. Flag stale entries.
2. **Contradiction check**: look for same `key` but different/opposite `insight`. Flag conflicts.

For each flagged entry, AskUserQuestion:
```
[STALE/CONFLICT] key: [key]
  Insight: [insight]
  [reason for flag]

  A) Remove this learning
  B) Keep it
  C) Update it — tell me what to change
```

For removals: read the JSONL, filter out the entry, write back.
For updates: append a new entry (latest wins).

---

## Export

```bash
eval "$(~/.bastack/bin/bs-slug 2>/dev/null)"
~/.bastack/bin/bs-learnings-search --limit 50 2>/dev/null
```

Format as markdown:

```markdown
## Project Learnings

### Patterns
- **[key]**: [insight] (confidence: N/10)

### Pitfalls
- **[key]**: [insight] (confidence: N/10)

### Architecture
- **[key]**: [insight] (confidence: N/10)

### Preferences
- **[key]**: [insight]
```

Ask if they want to append it to `CLAUDE.md` or save as a separate file.

---

## Stats

```bash
eval "$(~/.bastack/bin/bs-slug 2>/dev/null)"
BASTACK_HOME="${BASTACK_HOME:-$HOME/.bastack}"
LEARN_FILE="$BASTACK_HOME/projects/$SLUG/learnings.jsonl"
if [ -f "$LEARN_FILE" ]; then
  TOTAL=$(wc -l < "$LEARN_FILE" | tr -d ' ')
  echo "Total raw entries: $TOTAL"
  cat "$LEARN_FILE" | bun -e "
    const lines = (await Bun.stdin.text()).trim().split('\n').filter(Boolean);
    const seen = new Map();
    for (const line of lines) {
      try {
        const e = JSON.parse(line);
        const dk = (e.key||'')+'|'+(e.type||'');
        const ex = seen.get(dk);
        if (!ex || new Date(e.ts) > new Date(ex.ts)) seen.set(dk, e);
      } catch {}
    }
    const byType = {}, bySource = {};
    let tc = 0;
    for (const e of seen.values()) {
      byType[e.type] = (byType[e.type]||0)+1;
      bySource[e.source] = (bySource[e.source]||0)+1;
      tc += e.confidence || 0;
    }
    console.log('Unique (after dedup):', seen.size);
    console.log('By type:', JSON.stringify(byType));
    console.log('By source:', JSON.stringify(bySource));
    console.log('Avg confidence:', (tc/seen.size).toFixed(1)+'/10');
  " 2>/dev/null
else
  echo "No learnings file yet."
fi
```

---

## Manual Add

Gather via AskUserQuestion:
1. Type: `pattern / pitfall / preference / architecture / tool`
2. Key: short kebab-case phrase (2-5 words)
3. Insight: one sentence
4. Confidence: 1-10
5. Related files: (optional)

Then log:
```bash
~/.bastack/bin/bs-learnings-log '{"skill":"learn","type":"TYPE","key":"KEY","insight":"INSIGHT","confidence":N,"source":"user-stated","files":["FILE"]}'
```
