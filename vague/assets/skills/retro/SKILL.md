---
name: retro
version: 1.0.0
description: |
  Engineering retrospective. Analyzes commit history, work patterns, and code quality
  metrics. Saves history for trend tracking.
  Trigger: "weekly retro", "what did we ship", "engineering retrospective".
sdk_commands:
  - vague context
  - vague memory-log
  - vague status
  - vague memory-search
requires_slug: true
allowed-tools:
  - Bash
  - Read
  - Write
  - AskUserQuestion
---

## Preamble

```bash
eval "$(vague context --shell --skill retro)"
VAGUE_HOME="${VAGUE_HOME:-$HOME/.vague}"
```

**Proactive invocation:** Suggest at the end of a work week or sprint.

---

## Step 1: Define the Time Window

Default: last 7 days. The user can pass an argument: `/retro 14d`, `/retro 30d`.

```bash
# Compute time window (macOS date)
DAYS=${1:-7}
if date -v-1d +%Y-%m-%d >/dev/null 2>&1; then
  SINCE=$(date -v-${DAYS}d +%Y-%m-%d)
else
  SINCE=$(date -u -d "$DAYS days ago" +%Y-%m-%d 2>/dev/null || date +%Y-%m-%d)
fi
echo "Retro window: $SINCE → today"
```

---

## Step 2: Commit Analysis

```bash
# Total commits in window
git log --oneline --since="$SINCE" 2>/dev/null | wc -l | tr -d ' '

# Commits by type (conventional commits)
git log --oneline --since="$SINCE" 2>/dev/null | grep -oE '^[a-f0-9]+ (feat|fix|chore|docs|test|refactor|perf|style|ci)' | awk '{print $2}' | sort | uniq -c | sort -rn

# Files most changed
git log --since="$SINCE" --name-only --format="" 2>/dev/null | grep -v '^ | sort | uniq -c | sort -rn | head -10

# Insertions and deletions
git log --since="$SINCE" --stat 2>/dev/null | tail -1

# Commits per day
git log --since="$SINCE" --format="%ad" --date=short 2>/dev/null | sort | uniq -c
```

---

## Step 3: Work Pattern Analysis

```bash
# Peak coding hours
git log --since="$SINCE" --format="%ad" --date=format:"%H" 2>/dev/null | sort | uniq -c | sort -rn | head -5

# Commit message quality (length distribution)
git log --since="$SINCE" --format="%s" 2>/dev/null | awk '{print length}' | sort -n | awk 'BEGIN{min=9999;max=0;sum=0;count=0} {if($1<min)min=$1; if($1>max)max=$1; sum+=$1; count++} END{print "msg length: min="min" max="max" avg="int(sum/count)}'
```

---

## Step 4: Test Health

```bash
# Count test files
find . -name '*.test.*' -o -name '*.spec.*' -o -name '*_test.*' -o -name '*_spec.*' 2>/dev/null | grep -v node_modules | grep -v .git | wc -l | tr -d ' '

# Test commits this period
git log --since="$SINCE" --oneline 2>/dev/null | grep -iE '^[a-f0-9]+ test' | wc -l | tr -d ' '
```

---

## Step 5: Load Prior Retro (for trend comparison)

```bash
eval "$(vague context --shell --skill retro)" >/dev/null
VAGUE_HOME="${VAGUE_HOME:-$HOME/.vague}"
ls -t "$VAGUE_HOME/projects/$SLUG/retros/"*.md 2>/dev/null | head -1 || echo "NO_PRIOR_RETRO"
```

If a prior retro exists, read its summary table for trend comparison.

---

## Step 6: Load Skill Activity and Memories

The events log records each skill start and each memory written. Count both for this repo in the window:

```bash
python3 - "$VAGUE_HOME" "$SLUG" "$SINCE" <<'PY'
import collections, glob, json, sys
home, slug, since = sys.argv[1:]
runs, written = collections.Counter(), set()
for path in glob.glob(f"{home}/events/*.jsonl"):
    for line in open(path):
        try: e = json.loads(line)
        except ValueError: continue
        if e.get("repo") != slug or e.get("ts", "")[:10] < since: continue
        if e.get("event") == "skill_start": runs[e.get("skill")] += 1
        if e.get("command") == "memory-log": written.update(e.get("ids", []))
print("skill runs:", dict(runs.most_common()))
print("memories written:", sorted(written))
PY
```

Read a written memory with `vague memory-search <words from its key>`. The preamble's MEMORY block already lists the project's top memories. `vague status` shows the last activity per project.

---

## Step 7: Write the Retro

**Tweetable summary** (first line):
```
Week of [date]: [N] commits, [LOC] LOC, [N] PRs, peak: [hour]
```

Then:

```markdown
## Engineering Retro: [date range]

### Summary
| Metric | Value | vs Last Week |
|--------|-------|--------------|
| Commits | N | ↑/↓/= |
| LOC changed | +N / -N | ↑/↓/= |
| Test files | N | ↑/↓/= |
| Peak hour | Npm | ↑/↓/= |

### Commit Mix
[pie-style breakdown: feat/fix/chore/test/other]

### Hotspot Files
[Top 5 most-changed files and what that suggests]

### Test Health
- Total test files: N
- Tests added this period: N
- [flag if test ratio < 20%]

### Patterns from This Week
[1-3 observations based on the commit data]

### What Went Well
[2-3 specific things anchored in actual commits]

### Where to Level Up
[1-2 specific, actionable suggestions]

### 3 Habits for Next Week
[Small, < 5-minute habits. At least one engineering quality habit.]

### Skills Run and Memories Logged This Period
[From Step 6: skill run counts, and each memory key with its one-line text]
```

---

## Step 8: Save the Retro

```bash
eval "$(vague context --shell --skill retro)" >/dev/null
VAGUE_HOME="${VAGUE_HOME:-$HOME/.vague}"
mkdir -p "$VAGUE_HOME/projects/$SLUG/retros"
RETRO_FILE="$VAGUE_HOME/projects/$SLUG/retros/retro-$(date +%Y-%m-%d).md"
# Write the retro content to $RETRO_FILE
```

Tell the user: "Retro saved to `$RETRO_FILE`."

---

## Observation Protocol

Log feedback about this skill with `vague memory-log <key> "<issue → suggestion>" --about retro` (see the Memory guideline).
