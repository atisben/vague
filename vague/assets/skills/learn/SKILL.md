---
name: learn
version: 1.0.0
description: |
  Manage project learnings: review, search, prune, export.
  Trigger: "what have we learned", "show learnings", "prune stale learnings",
  "export learnings", "didn't we fix this before?".
sdk_commands:
  - vague init
  - vague learnings-search
  - vague learnings-log
  - vague observations-log
requires_slug: true
requires_planning: false
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - AskUserQuestion
---

## Preamble

```bash
CONTEXT=$(vague init)
SLUG=$(echo "$CONTEXT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['slug'])")
BRANCH=$(echo "$CONTEXT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['branch'])")
PROACTIVE=$(echo "$CONTEXT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['proactive'])")
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
vague learnings-search 2>/dev/null || echo "No learnings yet."
```

If no learnings: "No learnings recorded yet. As you use /review, /ship, /investigate, and /retro, vague will automatically capture patterns, pitfalls, and insights it discovers."

---

## Search

```bash
vague learnings-search 2>/dev/null || echo "No matches."
```

Filter by type if requested:
```bash
vague learnings-search --type pitfall 2>/dev/null
```

---

## Prune

Check for stale and contradictory entries.

```bash
vague learnings-search 2>/dev/null
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

For updates: append a new entry (latest wins via dedup).

---

## Export

```bash
vague learnings-search 2>/dev/null
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
vague learnings-search --json 2>/dev/null | python3 -c "
import sys, json
entries = json.load(sys.stdin)
print(f'Total unique entries: {len(entries)}')
by_type = {}
for e in entries:
    t = e.get('type','unknown')
    by_type[t] = by_type.get(t, 0) + 1
for t, c in sorted(by_type.items()):
    print(f'  {t}: {c}')
avg_conf = sum(e.get('confidence',0) for e in entries) / max(len(entries),1)
print(f'Avg confidence: {avg_conf:.1f}/10')
"
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
vague learnings-log '{"skill":"learn","type":"TYPE","key":"KEY","insight":"INSIGHT","confidence":N,"source":"user-stated","files":["FILE"]}'
```

---

## Observation Protocol

Throughout this skill's execution, watch for:
- Steps that produce wrong or suboptimal output
- Missing rules the user has to correct
- Workflow inefficiencies or unnecessary steps
- Gaps where a different skill would help
- **User corrections** — any time the user tells you to do something the skill should have done automatically (e.g. "read the plan", "check the tests first", "use the right branch")

When you notice any of these, log an observation:

```bash
vague observations-log '{"skill":"learn","type":"improvement","issue":"WHAT_HAPPENED","suggestion":"CONCRETE_CHANGE","principle":"GENERALISABLE_TAKEAWAY","source_skill":"learn"}'
```

**User correction detection:** If the user has to explicitly ask you to perform a step that should be part of this skill's workflow, log it immediately as a `type: correction` observation. These are the most valuable signals for skill improvement.

```bash
vague observations-log '{"skill":"learn","type":"correction","issue":"User had to manually ask: WHAT_THEY_SAID","suggestion":"Add this as an explicit step in the skill","principle":"GENERALISABLE_TAKEAWAY","source_skill":"learn"}'
```

Log silently — do not interrupt the user's workflow to announce observations.
