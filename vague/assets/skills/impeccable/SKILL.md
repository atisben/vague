---
name: impeccable
version: 1.0.0
description: |
  Design, redesign, critique, audit, polish or animate a web frontend: landing pages,
  dashboards, app UI, components. Works from a design brief kept in vague memory,
  drafts three static HTML mockups for new work, edits the real UI files, and hands
  the result to two read-only reviewers (finish and motion). Critiques and audits are
  saved to the Obsidian vault. Adapted from pbakaus/impeccable.
  Trigger: "impeccable", "critique this UI", "polish the design", "audit the UI", "design a new page", "make it look better", "/impeccable".
sdk_commands:
  - vague context
  - vague memory-log
  - vague memory-search
  - vague design-check
runtimes:
  - claude
hooks:
  PostToolUse:
    - matcher: "Edit|Write"
      hooks:
        - type: command
          command: vague design-check --hook
allowed-tools: [Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion, Agent]
---
<!-- Adapted from pbakaus/impeccable@2b86d9c (Apache-2.0). See NOTICE.md. -->

## Preamble

```bash
eval "$(vague context --shell --skill impeccable)"
vague memory-search design- --kind learning --skill impeccable
vague memory-search design-direction --scratch
```

The first search prints the brief: one `design-*` learning per fact (audience, purpose, tone, palette, type, layout, motion, imagery, anti-references). The second prints the current task direction note, if one was logged in the last 7 days. The note is short and names the direction file that holds the full direction: read that file next.

This skill gives you the tools and permission to make design that earns the name out-of-distribution craft. Work as an award-winning design director would: production-grade code, a clear POV, a deep grasp of what the client and its users need, and exceptional craft.

Core principles:
- Finish the job. No hedging, no shortcuts: the deliverable is complete, except assets the user must provide.
- Scale ambition to the surface's mode (see Modes). Persuade and Experience get full commitment: bold, distinct work with a point of view. On Operate and Read, ambition shows as precision and restraint, and patterns the visitor already knows earn their place.
- Verify by looking at the rendered result at the sizes it ships at, when this session has a browser tool. Batch the checks: fix what one look shows before looking again, rather than screenshotting after every tweak. Without a browser tool, say which checks were reasoned from code only.

---

## Runtime Flow

Every request runs this flow:

```
 ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
 │ 1. Preamble  │──▶│ 2. Brief     │──▶│ 3. Direction │──▶│ 4. Build     │──▶│ 5. Review    │
 │ load brief + │   │ empty? load  │   │ log it as a  │   │ main session │   │ read-only    │
 │ direction    │   │ brief.md     │   │ scratch note │   │ edits the UI │   │ reviewers    │
 └──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘
```

1. **Preamble.** Run the block in [Preamble](#preamble).
2. **Brief.** An empty learning result means there is no brief yet. Load [reference/brief.md](reference/brief.md) first, then continue. A narrow refinement of existing code (one `polish`, `clarify` or `typeset` pass) may proceed on the incumbent implementation and offer the brief afterward, instead of blocking on it.
3. **Direction.** Load the request's playbook (see [Routing](#routing)). Inspect the target and the incumbent visual truth before editing. When the playbook settles a direction, log it before building:
   ```bash
   vague memory-log design-direction "<page-slug>: <thesis in one line> | PATH: <code-led|mockup-led> | FILE: /tmp/vague-comps/<project-slug>/<page-slug>/direction.md" --scratch --skill impeccable
   ```
   The full direction (the contract, the mockup path, and the section checklist) lives in that `direction.md` file, because a note holds at most 600 characters. `design-direction` is always a scratch note. Never log it as another kind.
4. **Build.** Read [reference/craft-floor.md](reference/craft-floor.md) immediately before any UI edit, including small refinements. It carries the quality floor, the absolute bans, and the reflexes a mechanical scan misses. Do not load it for planning-only work. Then edit the UI files.
5. **Review.** Hand the result to the reviewers (see [Reviewers](#reviewers)) when the playbook calls for them.

Some playbooks come in parts. Read the part a request needs in the same step, not when the playbook later mentions it:
- [reference/new-work-world.md](reference/new-work-world.md) when a visual world is created or replaced (a redesign, a new look, or no established world).
- [reference/visualize.md](reference/visualize.md) and [reference/region-map.md](reference/region-map.md) when new-work drafts mockups. vague drafts three static HTML mockups (`a-safe.html`, `b-bold.html`, `c-wildcard.html` under `/tmp/vague-comps/<project-slug>/<page-slug>/`), the user picks one, and its sections become a checklist.
- [reference/critique-rubric.md](reference/critique-rubric.md) for a critique.

---

## How to Design

- **The brief wins.** Honor pinned aesthetics, eras, materials, fonts, and palettes even when they conflict with a saturated-pattern warning. Redirecting a clear brief toward your taste is failure.
- **Refinement preserves; redesign replaces.** Refinement keeps the incumbent identity, behavior, copy, and everything outside scope. Ask before replacing factual copy or adding claims. Redesign keeps product truth, content, function, native affordances, and constraints, but treats the old look as evidence and anti-reference. Choose a replacement world in new-work and update the brief's `design-*` learnings to match. Never split the difference into polish on the discarded look.
- **Loaded symbols stay out of the decoration.** A subject's world does not license emblems tied to militarism, supremacy, or hate movements as motifs, badges, or ornament, such as the Rising Sun flag's rays, the Confederate battle flag, or Nazi-era insignia and their stylised variants; reach for that world's neutral forms instead. Content that documents such a symbol as fact stays as it is.
- **Visual authority is evidence, not a memory entry.** A missing brief alone does not make a project greenfield. new-work decides whether to preserve, expand, or replace the incumbent world.

---

## Modes

The mode names what the visitor's success looks like on this surface.

- **Persuade:** the visitor decides and acts; design is the product. Landing pages, marketing, campaigns, pricing. Earn attention and action. Ship real imagery when the brief needs it; follow the committed world, not category habit.
- **Operate:** the visitor completes a task. App UI, dashboards, editors, admin, settings, tools. Scanability, consistency, native expectations, and the real usage scene outrank expression. Brand lives in precise details.
- **Read:** the visitor understands something. Docs, articles, guides, help, changelogs. Structure for comprehension, then make the reading experience worth staying in.
- **Experience:** the visitor is inside the work itself. Portfolios, galleries, showcases. Let the artifact lead from the first viewport; the interface recedes.

Choose the mode from the requested surface, not the product. Record it in the direction file, not in the brief. A tool's landing page is still Persuade; a fashion house's documentation is still Read; a docs index is Read, not Persuade. See [reference/new-work.md](reference/new-work.md) for new surfaces and [reference/operate.md](reference/operate.md) for deeper Operate/Read guidance.

vague ships web guidance only. For a native iOS or Android project, say so before starting, and keep to the platform-neutral commands.

---

## Commands

Each command loads one playbook:

| Command | Category | Description | Reference |
|---|---|---|---|
| (new surface) | Build | A new page, a replacement visual world, or a build from an approved mockup | [reference/new-work.md](reference/new-work.md) |
| `brief` | Build | Capture or update the design brief in vague memory | [reference/brief.md](reference/brief.md) |
| `shape [feature]` | Build | Plan UX/UI before writing code | [reference/shape.md](reference/shape.md) |
| `extract [target]` | Build | Pull reusable tokens and components into the design system | [reference/extract.md](reference/extract.md) |
| `critique [target]` | Evaluate | UX design review with heuristic scoring | [reference/critique.md](reference/critique.md) |
| `audit [target]` | Evaluate | Technical quality checks (a11y, perf, responsive) | [reference/audit.md](reference/audit.md) |
| `polish [target]` | Refine | Final quality pass before shipping | [reference/polish.md](reference/polish.md) |
| `bolder [target]` | Refine | Amplify safe or bland designs | [reference/bolder.md](reference/bolder.md) |
| `quieter [target]` | Refine | Tone down aggressive or overstimulating designs | [reference/quieter.md](reference/quieter.md) |
| `distill [target]` | Refine | Strip to essence, remove complexity | [reference/distill.md](reference/distill.md) |
| `harden [target]` | Refine | Production-ready: errors, i18n, edge cases | [reference/harden.md](reference/harden.md) |
| `onboard [target]` | Refine | Design first-run flows, empty states, activation | [reference/onboard.md](reference/onboard.md) |
| `animate [target]` | Enhance | Add purposeful animations and motion | [reference/animate.md](reference/animate.md) |
| `colorize [target]` | Enhance | Add strategic color to monochromatic UIs | [reference/colorize.md](reference/colorize.md) |
| `typeset [target]` | Enhance | Improve typography hierarchy and fonts | [reference/typeset.md](reference/typeset.md) |
| `layout [target]` | Enhance | Fix spacing, rhythm, and visual hierarchy | [reference/layout.md](reference/layout.md) |
| `delight [target]` | Enhance | Add personality and memorable touches | [reference/delight.md](reference/delight.md) |
| `overdrive [target]` | Enhance | Push past conventional limits | [reference/overdrive.md](reference/overdrive.md) |
| `clarify [target]` | Fix | Improve UX copy, labels, and error messages | [reference/clarify.md](reference/clarify.md) |
| `adapt [target]` | Fix | Adapt for different devices and screen sizes | [reference/adapt.md](reference/adapt.md) |
| `optimize [target]` | Fix | Diagnose and fix UI performance | [reference/optimize.md](reference/optimize.md) |

The mode files [reference/mode-persuade.md](reference/mode-persuade.md), [reference/mode-operate.md](reference/mode-operate.md) and [reference/mode-read.md](reference/mode-read.md) are loaded by new-work, not invoked directly.

### Routing

Route each request this way:

- **No argument:** read [reference/routing.md](reference/routing.md) and present its context-aware menu; never auto-run a command.
- **Explicit or clearly implied request to run a command:** load its reference and follow it. Ask once if two commands fit.
- **Workflow or command-selection question:** read the Workflow questions section of [reference/routing.md](reference/routing.md).
- **Otherwise:** treat the request as general design work. A new surface or a replacement world with no brief goes through `brief`, then new-work. A narrow refinement of existing code proceeds on the incumbent implementation, offering `brief` afterward rather than blocking on it.
- `teach` and `init` alias `brief`. `craft` is an alias for ordinary new-work and adds nothing. `shape` owns task discovery, then enters new-work only for visual-world and surface-concept decisions.

After `brief` logs its learnings, resume the original request without rerunning the Preamble.

---

## Reviewers

Two read-only reviewer agents check built work. They never edit files.

| Agent | Checks | Spawned by | Fallback without an Agent tool |
|---|---|---|---|
| `impeccable-finish-reviewer` | The finished surface against the brief, the chosen mockup and the craft floor | new-work, critique | Run [reference/degraded/finish-reviewer.md](reference/degraded/finish-reviewer.md) inline |
| `impeccable-motion-reviewer` | Authored motion and its reduced-motion path | animate, critique | Run [reference/degraded/motion-reviewer.md](reference/degraded/motion-reviewer.md) inline |

Spawn them with the Agent tool and a fresh context. Pass the target files, the chosen mockup path when the direction file names one, and the evidence the playbook names. They load the brief and the direction note themselves with `vague memory-search`, then read the direction file the note names. When no Agent tool is exposed, read the fallback file, step out of your own findings, run the review inline, and disclose the substitution in the result.

---

## Detector

`vague design-check` is a regex scan of UI source files (`.css`, `.html`, `.jsx`, `.tsx`, `.vue`, `.svelte` and similar) for eight AI-design tells. It reads one file at a time, so it cannot see rendered contrast, sizes or overflow.

It runs in two ways:

- **As a hook.** The `hooks` block in this file's frontmatter runs `vague design-check --hook` after every Edit and Write, from the moment `/impeccable` is invoked until the session ends. Findings come back to you as a hook error (exit 2). Fix them in the same turn.
- **By hand.** `audit`, `critique`, `layout`, `typeset` and `polish` run `vague design-check <target paths>` first, then scan by hand for what the rules do not cover. It prints `<path>:<line>: <rule>: <message>` per finding and exits 1 when there is any.

The eight rule ids are `side-tab`, `border-accent-on-rounded`, `overused-font`, `gradient-text`, `gray-on-color`, `ai-color-palette`, `bounce-easing` and `broken-image`. A font named in the brief's `design-type` learning (`Brand fonts: ...`) is never flagged as `overused-font`.

To keep a deliberate match, add a comment with the rule id and a reason after `:` or `--`. The comment uses the file's own syntax (`/* */` in CSS and scripts, `<!-- -->` in markup):

| Comment | Waives the rules for |
|---|---|
| `/* impeccable-disable-next-line side-tab: brand callout */` | The next line |
| `/* impeccable-disable-line bounce-easing: playful toggle */` | Its own line |
| `<!-- impeccable-disable broken-image -- exported doc -->` | The whole file |

Separate several rule ids with commas or spaces. A comment with no rule id waives every rule. Waive only what the brief asks for, never to silence a real finding.

---

## Saving

Each saved artifact gets a vault note and a memory pointer:

| Artifact | Vault call | Memory pointer |
|---|---|---|
| Approved mockup | `/vault export "<mockup path>" title "Design Comp - <Page>" folder "6. Atomic Notes/" tags "design,impeccable"` | `vague memory-log design-comp-<page-slug> "<one line>" --doc --files "<VAULT_NOTE path>" --skill impeccable` |
| Critique or audit report | `/vault save "Design Critique - <Target>" folder "6. Atomic Notes/" tags "design,review,impeccable"` | `vague memory-log design-critique-<target-slug> "<verdict in one line>" --doc --files "<VAULT_NOTE path>" --skill impeccable` |

The vault skill prints `VAULT_NOTE: <path>`. Use that path in `--files`. Slugs are lowercase `[a-z0-9-]`.
