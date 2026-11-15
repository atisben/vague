<!-- Adapted from pbakaus/impeccable@2b86d9c (Apache-2.0). See ../NOTICE.md. -->
### Purpose

Resolve one stable target, run two independent assessments, synthesize a design critique, save it to the vault, and ask the user what to improve next. The chat response is the primary deliverable. The vault note is an archive of that run.

vague has no screenshot tool and no live overlay. Its detector, `vague design-check`, reads source files only. Every other check in this file runs with Claude's own tools: Read, Glob, Grep, and the optional read-only reviewer subagents. A check that needs a rendered page is reasoned from the code and labelled **unverified (no render)**.

### Hard Invariants

- Assessment A (design review) and Assessment B (code evidence against the craft floor) are both required.
- Assessment A must finish and be written down before Assessment B starts. Mechanical findings anchor judgment, so the design-specificity verdict comes first.
- A render-dependent finding (contrast, tiny text, overflow, spacing as rendered, motion as played) is never stated as measured. Label it `unverified (no render)` unless the user supplied a screenshot that shows it.
- When the reviewer subagents are wanted but no Agent tool is exposed, run their fallback files inline and put the banner `⚠️ DEGRADED: single-context (<reason>)` on the report's first line. A silent degraded critique is a failed critique.
- The question is the LAST thing in the response. Write the entire report first, then ask. Nothing follows the question. Prose emitted after a structured question is withheld until the user answers it, so a report written after the question reads as if the critique never ran.
- A run that ends with neither the targeted questions nor a literal `Questions skipped: <reason>` line is an incomplete run. The report is not the finish. The close is.

### Setup

1. **Resolve the target** to a concrete file path. Prefer a source path over a dev-server URL when both identify the same surface. Ports drift, paths do not.
   - "the homepage" -> `site/pages/index.astro` or `index.html`
   - "the settings modal" -> the primary component file
   - "this page" -> the source file behind the current URL
2. **Derive the target slug** from the resolved path: lowercase, drop the extension, turn every character outside `[a-z0-9]` into `-`, collapse repeats. `site/pages/index.astro` becomes `site-pages-index`. The slug names the vault note's memory key, `design-critique-<target-slug>`.
3. **Read the brief.** The preamble already printed the `design-*` learnings. If it did not, run:
   ```bash
   vague memory-search design- --kind learning --skill impeccable
   ```
   An empty result means there is no brief. Load [brief.md](brief.md) first, then come back.
4. **Read the direction.** Run `vague memory-search design-direction --scratch`, then read the direction file the note names after `FILE:`, when it still exists. When the direction file names a chosen mockup path (under `/tmp/vague-comps/`) and that mockup still exists, read it. The critique compares the built page to that mockup. When the file holds a section checklist, keep it for Assessment A's coverage check.
5. **Read the previous run.** Run `vague memory-search design-critique-<target-slug> --kind doc --skill impeccable`. The line ends with `(files: <path>)`. Read that vault note for the previous score, used later in the trend line. Its findings do not enter Assessment A: read only the score line until A is written down.
6. **Read the target files.** Read the resolved file, the stylesheets and tokens it imports, and the components it renders. Batch the reads. For a tree of more than about 50 markup files, narrow the scope or ask.

### Assessment Orchestration

The main session runs Assessment A, then Assessment B, then synthesis. The two reviewer subagents are optional depth on top of them.

**Reviewers.** Spawn them when the target has a finished visual surface (finish reviewer) or authored motion (motion reviewer), or when the user asks for a thorough critique. Skip them for a quick look at a component. When you spawn them:

- Use the Agent tool with `impeccable-finish-reviewer` and `impeccable-motion-reviewer`, in parallel. They are read-only and never edit files.
- Pass each one the target file paths, the chosen mockup path when the direction file names one, and the user's original request. They load the brief and the direction themselves with `vague memory-search design-direction --scratch` and `vague memory-search design- --kind learning --skill impeccable`, then read the direction file the note names.
- Do not pass them your Assessment A or B findings. They must judge unanchored.
- Spawn them after Assessment A is written down, so their output cannot anchor your verdict.

**Fallback.** When no Agent tool is exposed, read [finish-reviewer](degraded/finish-reviewer.md) and [motion-reviewer](degraded/motion-reviewer.md), step out of your own findings, and run each review inline in that order. Emit the degraded banner.

Declare the path you took in the report header (see Report header provenance).

### Assessment A: Design Review

Read the relevant source files and think like a design director. Read [critique-rubric.md](critique-rubric.md) before scoring.

Evaluate:
- **Design specificity**: Is the composition, interaction, and visual language grounded in this product, or could an unrelated product use it unchanged? Judge it against the brief (`design-purpose`, `design-tone`, `design-anti-references`). Make this judgment before Assessment B.
- **Brief fit**: Does the code honour `design-palette`, `design-type`, `design-layout`, `design-motion` and `design-imagery`? Name every drift with the brief's value and the code's value, e.g. "brief: Fraunces 600 for display; code: Inter 700".
- **Mockup fit** (only when the direction file names a chosen mockup): Does the built page keep the mockup's composition, hierarchy, density and focal moment? Walk the section checklist from the direction file and mark each section present, drifted, or missing.
- **Holistic design**: hierarchy, IA, emotional fit, discoverability, composition, typography, color, accessibility, states, copy, and edge cases.
- **Cognitive load**: consult the Cognitive Load Assessment in [critique-rubric.md](critique-rubric.md). Report checklist failures and decision points with >4 visible options.
- **Emotional journey**: peak-end rule, emotional valleys, reassurance at high-stakes moments.
- **Nielsen heuristics**: consult the Heuristics Scoring Guide in [critique-rubric.md](critique-rubric.md). Score all 10 heuristics 0-4, marking any heuristic the mode-applicability rule allows as `n/a` instead of forcing a number.
- **Persona red flags**: select personas with the Selecting Personas table in [critique-rubric.md](critique-rubric.md), plus 1-2 project-specific ones from the brief's `design-audience` when it has one, and walk each through the primary action.

Write down: design-specificity verdict, brief fit, mockup fit, heuristic scores, cognitive load, emotional journey, 2-3 strengths, 3-5 priority issues, persona red flags, minor observations, and provocative questions.

### Assessment B: Code Evidence Against the Craft Floor

Run the detector on the target's UI files first. It exits 1 when it finds anything:

```bash
vague design-check <target paths>
```

It covers eight source tells (see Detector in SKILL.md), all in the "Verifiable from code" group. Then read [craft-floor.md](craft-floor.md) and run its Verify and Refuse lists against the code for the rest. This replaces upstream's browser overlay. It is mechanical: grep, read, and compare values.

Each check falls into one of two groups:

| Group | Checks | How |
|---|---|---|
| Verifiable from code | Refuse-list scaffolds (identical icon-heading-text cards, nested cards, hero-metric template, eyebrow above a heading, decorative section numbers, needless modals), missing states (hover, focus-visible, disabled, loading, error, empty), un-themed browser surfaces (`::selection`, `caret-color`, scrollbars, focus rings, `text-underline-offset`, `font-variant-numeric` in tables), zero-offset shadow halos, display size above 6rem, tracking below -0.04em, motion that animates layout properties or lacks a `prefers-reduced-motion` branch, placeholder or lorem copy, brief requirements absent from the markup | Grep the stylesheets and markup, then read the matches |
| Needs a render | Contrast ratios, tiny rendered text, overflow at each breakpoint, spacing as rendered, line measure with the real copy, motion as played | Compute what the code allows: resolve the colour pair to hex and estimate the ratio, resolve `clamp()` at 375px and 1440px, look for fixed widths and `white-space: nowrap` on long copy. Label every result `unverified (no render)` |

When the user supplied screenshots, use them as evidence for the second group and drop the label for what they show.

Write down: each finding with file and line, its group, and any false positives you rejected with the reason.

### Generate Combined Critique Report

Synthesize both assessments, plus the reviewers' output when they ran, into a single report. Do not simply concatenate. Weave the findings together, noting where the design review and the code evidence agree, where the code evidence caught issues the review missed, and where a mechanical match is a false positive.

The chat response is the primary user-facing deliverable. Present the full structured critique below in chat. Do not replace it with a summary and a link. The vault note is an archive of that run.

Structure your feedback as a design director would:

#### Report header provenance

The report's first line MUST declare how the assessments ran, so a degraded or render-less run is never silent:
- With reviewers: `Method: design review + code evidence + reviewers (finish: <agent-id> · motion: <agent-id>) · render: none`
- Without reviewers: `Method: design review + code evidence · render: none`
- Degraded: `⚠️ DEGRADED: single-context (<reason, e.g. no Agent tool exposed>)`

Replace `render: none` with `render: user screenshots` when the user supplied them.

#### Design Health Score
> *Use Assessment A's scores. The bands are under [Scoring the report](#scoring-the-report).*

Present the Nielsen's 10 heuristics scores as a table:

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | ? | [specific finding or "n/a" if solid] |
| 2 | Match System / Real World | ? | |
| 3 | User Control and Freedom | ? | |
| 4 | Consistency and Standards | ? | |
| 5 | Error Prevention | ? | |
| 6 | Recognition Rather Than Recall | ? | |
| 7 | Flexibility and Efficiency | ? | |
| 8 | Aesthetic and Minimalist Design | ? | |
| 9 | Error Recovery | ? | |
| 10 | Help and Documentation | ? | |
| **Total** | | **??/[applicable max]** | **[Rating band]** |

The applicable maximum is 4 times the number of heuristics you actually scored: **/40** when all ten apply, **/32** when two are `n/a`. Never print `/40` over a partial set.

Be honest with scores. A 4 means genuinely excellent. Most real interfaces score 20-32 out of 40.

**Mode applicability**: heuristics 7 (Flexibility and Efficiency) and 10 (Help and Documentation) may be scored `n/a` on Persuade and Experience surfaces (landing pages, campaigns, portfolios, bodies of work), as may any other heuristic that genuinely cannot apply to the surface under review. Write `n/a` in the Score cell with a one-line reason, and renormalize the total to the applicable maximum (e.g. **24/32** when two heuristics are n/a) so the rating band stays proportional. The vault note must record the applicable maximum and which heuristics were scored n/a.

#### Design Specificity Verdict

**Start here.** Does the result feel authored for this product, or category-interchangeable?

**Design assessment**: Your unanchored evaluation of design specificity. Cover overall coherence, structural sameness, category-interchangeable choices, and missed opportunities for product character.

**Brief and mockup fit**: Every drift from the brief, with both values. When a chosen mockup exists, the section checklist with present, drifted, or missing per section.

**Code evidence**: Summarize Assessment B with counts and file locations. Separate the verifiable findings from the `unverified (no render)` ones. Note issues the code evidence caught that the design review missed, and flag false positives.

#### Overall Impression
A brief gut reaction: what works, what doesn't, and the single biggest opportunity.

#### What's Working
Highlight 2-3 things done well. Be specific about why they work.

#### Priority Issues
The 3-5 most impactful design problems, ordered by importance.

For each issue, tag with **P0-P3 severity** (see [Issue Severity](#issue-severity-p0p3) for definitions):
- **[P?] What**: Name the problem clearly
- **Why it matters**: How this hurts users or undermines goals
- **Fix**: What to do about it (be concrete)
- **Suggested command**: Which command could address this (from: /impeccable adapt, /impeccable animate, /impeccable audit, /impeccable bolder, /impeccable clarify, /impeccable colorize, /impeccable critique, /impeccable delight, /impeccable distill, /impeccable harden, /impeccable layout, /impeccable onboard, /impeccable optimize, /impeccable overdrive, /impeccable polish, /impeccable quieter, /impeccable shape, /impeccable typeset). When the issue is the brief itself (wrong audience, stale palette), suggest refreshing the brief with [brief.md](brief.md).

Mark an issue that rests only on render-dependent evidence `unverified (no render)` next to its severity.

#### Persona Red Flags
> *Use Assessment A's persona red flags. It selected the personas from [critique-rubric.md](critique-rubric.md).*

Assessment A selected 2-3 personas most relevant to this interface type (the selection table in critique-rubric.md). When the brief has a `design-audience` learning, also generate 1-2 project-specific personas from it and from `design-anti-references`.

For each selected persona, walk through the primary user action and list specific red flags found:

**Alex (Power User)**: No keyboard shortcuts detected. Form requires 8 clicks for primary action. Forced modal onboarding. High abandonment risk.

**Jordan (First-Timer)**: Icon-only nav in sidebar. Technical jargon in error messages ("404 Not Found"). No visible help. Will abandon at step 2.

Be specific. Name the exact elements and interactions that fail each persona. Don't write generic persona descriptions. Write what broke for them.

#### Minor Observations
Quick notes on smaller issues worth addressing.

#### Questions to Consider
Provocative questions that might unlock better solutions:
- "What if the primary action were more prominent?"
- "Does this need to feel this complex?"
- "What would a confident version of this look like?"

**Remember**:
- Be direct. Vague feedback wastes everyone's time.
- Be specific. "The submit button," not "some elements."
- Say what's wrong AND why it matters to users.
- Give concrete suggestions. Cut "consider exploring..." entirely.
- Prioritize ruthlessly. If everything is important, nothing is.
- Don't soften criticism. Developers need honest feedback to ship great design.

### Deliver the Report

Write the full report into the chat response now, before any saving. This is the deliverable. Everything below it is bookkeeping.

Do this first because the alternative is the most common way this command fails: the report gets composed once, straight into the vault note, and the run ends with a perfect archive nobody has read. Composing it into a note is not delivering it.

Saving is not the end of the run. After it, the response continues with the trend line and the close.

### Save the Report

Once the report above is final, save it to the vault so the user can refer back, and so `/impeccable polish` can pick up the priority issues without a copy-paste.

1. **Save the note** through the `/vault` skill (see its "Saving for Another Skill" section). The body is the full critique report: header, heuristic table, design-specificity verdict, priority issues, persona red flags, minor observations, and questions to consider. Stop before Ask the User and Recommended Actions. Put this line under the header so a later run can read the trend: `Score: <total>/<applicable max> · n/a: <heuristic numbers, or none> · P0: <n> · P1: <n>`.

   ```
   /vault save "Design Critique - <Target>" folder "6. Atomic Notes/" tags "design,review,impeccable" kind "plan"
   ```

   `<Target>` is the user's name for the surface, e.g. "Homepage". /vault prints `VAULT_NOTE: <path>`. A note with the same title is updated in place, so the vault keeps one critique per target.

2. **Point the ledger at the note.** The key carries the target slug, so a newer critique of the same target replaces the older pointer:

   ```bash
   vague memory-log design-critique-<target-slug> "<verdict in one line, with the score>" --doc --files "<VAULT_NOTE path>" --skill impeccable
   ```

   Tell the user you logged it.

3. **Append a single trend line to the user-visible output**, after the report and before the questions. Use the previous score from Setup step 5:

   > **Trend for `<target-slug>`: 24/40 → 31/40**
   > Saved `<VAULT_NOTE path>`.

   When the two runs scored different heuristic sets, print each score with its own denominator (`24/32 → 30/40`) and say the line is not a like-for-like comparison. When there was no previous critique, say: "First run for this target, no trend yet."

4. **Close the run.** Go to Ask the User and emit the questions, or the `Questions skipped: <reason>` line when the count allows it. The run is not complete until you do. Stopping after the save leaves the user with a report and no way forward.

Failures here do not block the rest of the flow. When /vault cannot save (for example, the folder is missing and the user declines), print the reason in one line, skip the memory-log, and move on.

### Ask the User

**After presenting findings**, use targeted questions based on what was actually found. Ask with the AskUserQuestion tool and wait for the answer before continuing. These answers will shape the action plan.

Ask in the same message that carries the report, with the report written out first and the question last. Do not split the two across turns: a turn that ends on the report is a turn that ends, and the questions never arrive. Order within the message is what matters, because prose emitted after a structured question is withheld until the user answers.

Ask questions along these lines (adapt to the specific findings, never generic):

1. **Priority direction**: Based on the issues found, ask which category matters most to the user right now. For example: "I found problems with visual hierarchy, color usage, and information overload. Which area should we tackle first?" Offer the top 2-3 issue categories as options.

2. **Design intent**: If the critique found a tonal mismatch, ask whether it was intentional. For example: "The interface feels clinical and corporate. Is that the intended tone, or should it feel warmer/bolder/more playful?" Offer 2-3 tonal directions as options based on what would fix the issues found. When the answer contradicts `design-tone`, offer to refresh the brief.

3. **Scope**: Ask how much the user wants to take on. For example: "I found N issues. Want to address everything, or focus on the top 3?" Offer scope options like "Top 3 only", "All issues", "Critical issues only".

4. **Constraints** (optional, only when relevant): If the findings touch many areas, ask if anything is off-limits. For example: "Should any sections stay as-is?" This prevents the plan from touching things the user considers done.

**Rules for questions**:
- Every question must reference specific findings from the report. Never ask generic "who is your audience?" questions.
- Keep it to 2-4 questions maximum. Respect the user's time.
- Offer concrete options, not open-ended prompts.
- Skipping is allowed only when the report listed **fewer than 3 Priority Issues**. Count them. Do not judge the findings "straightforward" by feel. At 3 or more, the questions are required.

**Final-question gate.** The user-visible response must either include the targeted questions or carry the literal line `Questions skipped: <reason>` naming the count that permitted the skip. Each question must include 2-3 concrete answer options tied to the actual critique findings. Do not end with only open-ended questions, and do not end with neither: stopping after the report, having asked nothing and printed no skip line, is the most common way this command fails.

### Recommended Actions

**After receiving the user's answers**, present a prioritized action summary reflecting the user's priorities and scope from Ask the User.

#### Action Summary

List recommended commands in priority order, based on the user's answers:

1. **`/command-name`**: Brief description of what to fix (specific context from critique findings)
2. **`/command-name`**: Brief description (specific context)
...

**Rules for recommendations**:
- Only recommend commands from: /impeccable adapt, /impeccable animate, /impeccable audit, /impeccable bolder, /impeccable clarify, /impeccable colorize, /impeccable critique, /impeccable delight, /impeccable distill, /impeccable harden, /impeccable layout, /impeccable onboard, /impeccable optimize, /impeccable overdrive, /impeccable polish, /impeccable quieter, /impeccable shape, /impeccable typeset. A brief refresh ([brief.md](brief.md)) may also appear when the issue is the brief itself.
- Order by the user's stated priorities first, then by impact
- Each item's description should carry enough context that the command knows what to focus on
- Map each Priority Issue to the appropriate command
- Skip commands that would address zero issues
- If the user chose a limited scope, only include items within that scope
- If the user marked areas as off-limits, exclude commands that would touch those areas
- End with `/impeccable polish` as the final step if any fixes were recommended

After presenting the summary, tell the user:

> You can ask me to run these one at a time, all at once, or in any order you prefer.
>
> Re-run `/impeccable critique` after fixes to see your score improve.

---

## Reference Material

Assessment A scores against [critique-rubric.md](critique-rubric.md): the cognitive load checklist, the heuristic scoring guide, and the personas. Assessment B checks against [craft-floor.md](craft-floor.md). The report uses the bands and severities below.

### Scoring the report

#### Score Summary

**Total possible**: 40 points (10 heuristics × 4 max)

| Score Range | Rating | What It Means |
|-------------|--------|---------------|
| 36–40 | Excellent | Minor polish only; ship it |
| 28–35 | Good | Address weak areas, solid foundation |
| 20–27 | Acceptable | Significant improvements needed before users are happy |
| 12–19 | Poor | Major UX overhaul required; core experience broken |
| 0–11 | Critical | Redesign needed; unusable in current state |

When heuristics were scored `n/a`, the maximum is lower than 40. Read the band off the percentage instead of the raw number (90%+ Excellent, 70%+ Good, 50%+ Acceptable, 30%+ Poor, below that Critical). 24/32 is 75%, so Good.

---

#### Issue Severity (P0–P3)

Tag each individual issue found during scoring with a priority level:

| Priority | Name | Description | Action |
|----------|------|-------------|--------|
| **P0** | Blocking | Prevents task completion entirely | Fix immediately; this is a showstopper |
| **P1** | Major | Causes significant difficulty or confusion | Fix before release |
| **P2** | Minor | Annoyance, but workaround exists | Fix in next pass |
| **P3** | Polish | Nice-to-fix, no real user impact | Fix if time permits |

**Tip**: If you're unsure between two levels, ask: "Would a user contact support about this?" If yes, it's at least P1.
