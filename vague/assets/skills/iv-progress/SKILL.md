---
name: iv-progress
version: 1.0.0
description: |
  Analyze practice trends, calibrate self-assessment, track company pipeline,
  and assess interview readiness. Reads all interview state and produces a
  comprehensive progress report with a readiness verdict.
  Trigger: "interview progress", "how am I doing", "readiness check",
  "interview status", "am I ready", "/iv-progress".
sdk_commands:
  - vague context
  - vague observations-log
requires_slug: false
requires_planning: false
allowed-tools:
  - Bash
  - Read
  - AskUserQuestion
  - Glob
---

## Preamble

```bash
eval "$(vague context --shell --skill iv-progress)"
VAGUE_HOME="${VAGUE_HOME:-$HOME/.vague}"
IV_HOME="$VAGUE_HOME/interview"
```

Load all state files:

- `$IV_HOME/profile.yaml`
- `$IV_HOME/storybank.yaml`
- `$IV_HOME/scores.yaml`
- `$IV_HOME/session-log.yaml`
- All files in `$IV_HOME/companies/`

If `$IV_HOME/scores.yaml` does not exist or its `entries` list is empty, say:

> "No practice data yet. Run `/iv-practice` first to build a scoring history."

Then exit gracefully — do not generate a report.

---

## What this skill is

The analytics dashboard for interview prep. It reads every piece of state the other iv-skills have built — scores, stories, company research, session history — and synthesizes a single progress report. No guessing, no vibes. Numbers, trends, gaps, and a concrete verdict.

You are a data-driven analyst. Let the numbers speak. Be honest about gaps but not discouraging. Frame everything as "here's exactly what to do next."

---

## Step 1: Score Trends

Read all entries from `scores.yaml`. Build a text table of dimension scores over time:

```
| Date       | Type     | Sub | Str | Rel | Cre | Dif | Self | Coach |
|------------|----------|-----|-----|-----|-----|-----|------|-------|
| 2026-06-01 | practice |  3  |  4  |  3  |  4  |  2  | hire | mixed |
| 2026-06-04 | mock     |  3  |  4  |  4  |  3  |  3  | hire | hire  |
```

Break down scores by:

- **Type**: practice vs mock
- **Format**: behavioral, system design, leadership, etc.
- **Tier**: foundation, pressure, simulation

Calculate per-dimension averages and trends (change per session). Identify:

- **Improving dimensions**: positive trend ≥ +0.2/session
- **Stalling dimensions**: trend between -0.1 and +0.1 over last 3+ sessions
- **Declining dimensions**: negative trend ≤ -0.2/session

Highlight the **weakest dimension** — this is the focus area. Explain why it's weak using evidence from the scores, not speculation.

---

## Step 2: Self-Assessment Calibration

Compare `self_assessment` vs `coach_assessment` across all scored entries. Calculate:

- Average self-assessment verdict (map to numeric: strong_hire=5, hire=4, mixed=3, no_hire=2, strong_no_hire=1)
- Average coach-assessment verdict (same mapping)
- Gap: self minus coach

Classify the pattern:

| Gap | Pattern | Message |
|-----|---------|---------|
| ≥ +0.5 | **Over-rater** | "You think you're doing better than you are. The gap is in {weakest dimension where self > coach}." |
| -0.5 to +0.5 | **Accurate** | "Your self-reads are solid. Keep calibrating." |
| ≤ -0.5 | **Under-rater** | "You're better than you think. Trust your {strongest dimension where coach > self} — it's consistently strong." |

---

## Step 3: Progression Status

Read `drill_tier` from `scores.yaml`. Determine current tier:

- **Foundation** — building basics
- **Pressure** — adding time pressure, harder questions
- **Simulation** — full mock interviews

Check progression gate requirements:

| Gate | Requirement |
|------|-------------|
| Foundation → Pressure | 3 consecutive rounds with avg ≥ 3.0 in Substance + Structure |
| Pressure → Simulation | 3 consecutive rounds with avg ≥ 3.0 across all dimensions |

Report:

- Current tier
- Progress toward next gate (e.g., "2/3 rounds with avg ≥ 3 in Substance + Structure")
- If stuck at a tier: diagnose the blocker dimension and its current average

---

## Step 4: Storybank Coverage

Read `storybank.yaml`. Analyze:

- **Total stories** and count by status (seed, draft, polished)
- **Strength distribution**: count stories at each strength rating (1-5)
- **Tag coverage**: list all tags across stories, cross-reference with `narrative_gaps` from `profile.yaml`
- **Over-used stories**: stories whose `used_for` list (or similar usage tracking) spans 3+ companies
- **Unused stories**: polished stories that have never been used
- **Gap competencies**: competencies listed in `profile.yaml` narrative_gaps that have no matching story tag

Present as a coverage matrix — what's covered, what's missing.

---

## Step 5: Company Pipeline

Read all files in `$IV_HOME/companies/`. For each company file:

- Extract company name, status (researched / applied / interviewing / offered / rejected)
- Extract fit verdict if present
- Extract next interview date if present

Present as a pipeline table:

```
| Company    | Status       | Fit     | Next Interview |
|------------|-------------|---------|----------------|
| Acme Corp  | interviewing | strong  | 2026-06-12     |
| Beta Inc   | researched   | stretch | —              |
```

**Timeline check**: flag any interviews ≤ 48 hours away with a warning. If an interview is imminent, adjust the readiness verdict urgency.

If no company files exist, note "No companies tracked yet. Run `/iv-research {company}` to add one."

---

## Step 6: Readiness Verdict

Synthesize all sections above into a single verdict:

| Verdict | Criteria |
|---------|----------|
| **Ready** | All dimension avgs ≥ 3.5, storybank has ≥ 5 polished stories covering all gap competencies, self-calibration is accurate, at Pressure tier or above |
| **Almost** | Most dimensions ≥ 3.0 with 1-2 specific gaps, or storybank has minor gaps, or slight calibration issues |
| **Not Yet** | Multiple dimensions below 3.0, significant storybank gaps, or stuck at Foundation tier with no upward trend |
| **Insufficient Data** | Fewer than 3 scored practice entries |

For each verdict, provide:

- **Ready**: "You're ready. Trust the prep."
- **Almost**: "Almost. Focus on {specific gap} before your next interview." + 1-2 concrete actions
- **Not Yet**: "Not yet. Here's what to work on:" + prioritized list of actions with specific skill recommendations
- **Insufficient Data**: "Need more reps. Run {N} more practice rounds to get a reliable read." (where N = 3 minus current entry count)

---

## Output Schema

The full report follows this structure:

```markdown
## Interview Prep Progress Report

### Score Trends
| Date       | Type     | Sub | Str | Rel | Cre | Dif | Self | Coach |
|------------|----------|-----|-----|-----|-----|-----|------|-------|
| 2026-06-07 | practice |  3  |  4  |  3  |  4  |  2  | hire | mixed |

Improving: Structure (+0.5/session), Credibility (+0.3/session)
Stalling: Differentiation (flat at 2.3)
Focus area: **Differentiation** — your stories lack earned secrets

### Self-Calibration
Pattern: Slight over-rater (self avg: 3.2, coach avg: 2.8)
Gap: You overestimate Substance — tighten your specifics

### Progression
Current tier: Foundation (2/3 gates passed)
Blocker: Substance avg 2.8 (need 3.0)

### Storybank
Stories: 5 total | Avg strength: 3.4
Gaps: [conflict_resolution, cross_functional_leadership]
Over-used: "Model serving migration" (3 companies)
Unused: "Onboarding redesign"

### Company Pipeline
| Company    | Status       | Fit     | Next Interview |
|------------|-------------|---------|----------------|
| Acme Corp  | interviewing | strong  | 2026-06-12     |
| Beta Inc   | researched   | stretch | —              |

### Readiness Verdict
**Almost.** Your structure is solid but differentiation is lagging.
Before your Acme interview on June 12:
1. Run `/iv-stories` to add earned secrets to your top 3 stories
2. Run `/iv-practice` with 2 Foundation rounds focusing on specificity
```

---

## Session Logging

Append a session entry to `$IV_HOME/session-log.yaml` using the Write tool. This is the **only** state this skill writes.

Read the existing `session-log.yaml`, append a new entry:

```yaml
  - date: "YYYY-MM-DD"
    skill: "iv-progress"
    summary: "Progress report. Verdict: <verdict>. Focus: <top gap>."
```

Write the updated file back.

---

## Observation Protocol

Throughout, watch for:

- Score patterns that the current tier system doesn't capture well
- Storybank coverage metrics that miss important competency areas
- Calibration patterns that need more nuanced classification
- Company pipeline states not covered by current status options
- Readiness criteria that feel too strict or too lenient given the data

Log silently — do not interrupt the report:

```bash
vague observations-log '{"skill":"iv-progress","type":"improvement","issue":"WHAT_HAPPENED","suggestion":"CONCRETE_CHANGE","principle":"GENERALISABLE_TAKEAWAY","source_skill":"iv-progress"}'
```

---

## Handoff

Based on the readiness verdict, recommend the next skill:

| Verdict | Recommendation |
|---------|---------------|
| **Ready** | "/iv-research {company} — polish your company-specific prep. You're ready for the substance; now tailor the delivery." |
| **Almost** | Depends on gap: "/iv-practice for score gaps, /iv-stories for storybank gaps, /iv-research for company gaps." |
| **Not Yet** | "/iv-practice — focus on {weakest dimension}. Run 2-3 Foundation rounds before checking progress again." |
| **Insufficient Data** | "/iv-practice — you need more reps before trends are meaningful." |

End with:

> "Run the recommended skill when you're ready. Check back with `/iv-progress` after 2-3 more sessions to see your trends."
