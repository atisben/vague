---
name: retro
version: 1.0.0
description: |
  Engineering retrospective. Analyzes commit history, work patterns, and code quality
  metrics. Saves history for trend tracking.
  Trigger: "weekly retro", "what did we ship", "engineering retrospective".
sdk_commands:
  - vague init
  - vague timeline-log
  - vague learnings-search
  - vague observations-log
requires_slug: true
requires_planning: false
allowed-tools:
  - Bash
  - Read
  - Write
  - AskUserQuestion
---

## Preamble

```bash
CONTEXT=$(vague init)
SLUG=$(echo "$CONTEXT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['slug'])")
BRANCH=$(echo "$CONTEXT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['branch'])")
PROACTIVE=$(echo "$CONTEXT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['proactive'])")
SESSION_ID="$$-$(date +%s)"
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
ls -t "$VAGUE_HOME/projects/$SLUG/retros/"*.md 2>/dev/null | head -1 || echo "NO_PRIOR_RETRO"
```

If a prior retro exists, read its summary table for trend comparison.

---

## Step 6: Load Learnings

```bash
vague learnings-search 2>/dev/null || true
```

Summarize learnings logged since the last retro (if any).

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

### Learnings Logged This Period
[From vague learnings-search]
```

---

## Step 8: Save the Retro

```bash
mkdir -p "$VAGUE_HOME/projects/$SLUG/retros"
RETRO_FILE="$VAGUE_HOME/projects/$SLUG/retros/retro-$(date +%Y-%m-%d).md"
# Write the retro content to $RETRO_FILE
```

Tell the user: "Retro saved to `$RETRO_FILE`."

Log telemetry:
```bash
vague timeline-log "{\"skill\":\"retro\",\"event\":\"completed\",\"branch\":\"$(git branch --show-current 2>/dev/null)\",\"session\":\"$SESSION_ID\"}"
```

---

## Observation Protocol

Throughout this skill's execution, watch for:
- Steps that produce wrong or suboptimal output
- Missing rules the user has to correct
- Workflow inefficiencies or unnecessary steps
- Gaps where a different skill would help

When you notice any of these, log an observation:

```bash
vague observations-log '{{"skill":"retro","type":"improvement","issue":"WHAT_HAPPENED","suggestion":"CONCRETE_CHANGE","principle":"GENERALISABLE_TAKEAWAY","source_skill":"retro"}}'
```

Log silently — do not interrupt the user's workflow to announce observations.
