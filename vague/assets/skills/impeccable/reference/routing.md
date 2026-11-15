<!-- Adapted from pbakaus/impeccable@2b86d9c (Apache-2.0). See ../NOTICE.md. -->

# Command guidance

## Workflow questions

Give advice without executing commands; the menu below is only for bare invocations. Consult relevant command references as needed for prerequisites and scope. Link to the [docs](https://impeccable.style/docs/) for the broader workflow guide. If the user also requests execution, follow that request.

## No-argument routing: the context-aware menu

Read this when the user invokes `/impeccable` with no argument. They are asking "what should I do?" Make the menu context-aware instead of static.

The Preamble has already loaded the brief. If it came back empty, the project has no captured context yet: lead the menu with the brief ([brief.md](brief.md)) as the top recommendation (one line on why) and still show the rest below; don't silently jump into it. Otherwise gather the signals below with your own tools, then lead with the **2-3 highest-value next commands**, each with a one-line reason pulled from the signals, followed by the full menu (the Commands table in SKILL.md, grouped by category). **Never auto-run a command; the recommendation is a suggestion the user confirms.**

Gather the signals once:

- **Critique history:** `vague memory-search design-critique- --kind doc --skill impeccable` lists past critique and audit reports, each pointing to a vault note.
- **Changed files:** `git status --short` and `git diff --stat` show which markup and style files are dirty.
- **Platform:** the project's manifest files (`package.json`, `Package.swift`, `build.gradle`) show whether it is web or native.

Reason over the signals; there is no score to obey:

- No critique hit → the project has never been critiqued; for a project with a brief and a real surface, offering `/impeccable critique <surface>` is a strong default.
- A critique hit whose verdict reports a low score or open P0 / P1 issues, and no later "cleared by polish" line → `polish` (it reads that note as its backlog).
- Changed files pointing at one surface → scope `audit` or `polish` to those files specifically, naming them.
- A native project (`ios`, `android`, or `adaptive`) → say that vague ships no native-platform guidance, and recommend only the commands that are platform-neutral (`critique`, `clarify`, `distill`, `onboard`, `shape`).
- Otherwise group by intent (build new / improve what's there), tailored to the current surface.

**If there are changed markup or style files and the project is web, skim them once** with Read and Grep for obvious slop families. Fold the hits into your picks: many contrast or quality problems → `audit` or `polish`; a specific slop family → the matching command (gradient text or eyebrows → `quieter` / `typeset`, flat or gray palette → `colorize`, and so on). If the tree is large and slow, skip it and recommend the user run `audit` themselves; never block the suggestion on it.

Keep it to 2-3 pointed picks with the exact command to type. The menu stays the fallback; the recommendation is the lede.
