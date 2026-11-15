<!-- Adapted from pbakaus/impeccable@2b86d9c (Apache-2.0). See ../NOTICE.md. -->
# Brief flow

The brief is the durable design truth for one project: who it serves, what it is for, how it should feel, and the visual system it keeps. vague stores it as nine `learning` memories, one fact each, written with `vague memory-log`. It replaces upstream's product and design-system files. This flow writes no file in the repo.

## When to run

- The preamble's `vague memory-search design- --kind learning --skill impeccable` printed nothing: there is no brief yet. Run this flow first, then resume the request that brought you here.
- The user asks to set, refresh, or change the brief, or a part of it ("our palette changed", "the audience is wrong").
- A critique or new-work round found the brief contradicts what the user now wants. Offer a refresh. Do not run it silently.

## The nine keys

Every brief fact goes under exactly one of these keys. Do not invent other `design-*` learning keys. `design-direction` is a 7-day note for one task, never a brief fact.

| Key | What it holds | Example text |
|---|---|---|
| `design-audience` | The primary users, their situation, and the job they are doing | `Indie bookshop owners, 1-3 staff, checking stock on a phone between customers. Non-technical. Secondary: their accountant, monthly, on desktop.` |
| `design-purpose` | What the product makes possible, why it exists, what success means, and the position a neighbour could not copy | `Shows what to reorder this week from till data, no spreadsheet. Success: owner places the order in under 2 minutes. Differs from POS dashboards: it recommends, it does not chart.` |
| `design-tone` | Voice and feel in concrete words, plus the brand commitments that bind it | `Warm, plain-spoken, quietly expert. Like a good shop assistant, never a dashboard. Copy says "you", no exclamation marks. Name is always lowercase "shelfwise".` |
| `design-palette` | Colours by role with exact values | `Primary ink #1F2A44 (text, primary buttons). Accent oxblood #8C2F39 (one CTA per screen, links). Paper #FAF7F2 (background). Rule #E4DED3 (borders). Success #3A7D44. No gradients.` |
| `design-type` | The brand fonts by role, with weights, sizes, and the scale | `Brand fonts: Fraunces (display, 600, 3-4.5rem, tracking -0.02em) and Inter (body 400/500, 1rem/1.6, 65ch). JetBrains Mono 400 for SKUs. Scale ratio 1.25.` |
| `design-layout` | Grid, container, density, spacing rhythm, radius and shape language, depth | `12-col grid, 1200px max, 24px gutters. Dense tables, airy marketing pages. 8px spacing base. Radius 6px on controls, 0 on cards. Flat: depth by tonal layers, no shadows at rest.` |
| `design-motion` | How much motion, which easing and durations, the one authored moment, reduced-motion stance | `Minimal. 150-200ms ease-out on state changes only. One authored moment: the reorder list settles in on load. Respect prefers-reduced-motion: fades only.` |
| `design-imagery` | Imagery stance: photography, illustration, icons, data graphics, or none, and what they show | `Real shop photography, warm daylight, people's hands on stock. No stock-photo smiles, no 3D illustration. Icons: Lucide, 1.5px stroke.` |
| `design-anti-references` | Confirmed visual and tonal rejections, with the reason when the user gave one | `Not Shopify admin (feels like a back office). No dark mode SaaS gradients, no glassmorphism, no emoji in UI copy.` |

`design-type` must name the brand fonts by family name, starting with `Brand fonts:`. Later checks read it to tell a deliberate brand font from a default one, so a vague value like "a friendly sans" breaks them.

## Step 1: Load current state

Read the learnings the preamble printed. When it printed none, run:

```bash
vague memory-search design- --kind learning --skill impeccable
```

- **No brief:** explore, interview, and write all nine keys.
- **Partial brief:** write only the missing keys. Do not reopen confirmed keys without a reason.
- **Refresh request:** ask which facts are stale. Re-ask only those keys.
- **Redesign or rebrand request:** keep `design-audience` and `design-purpose` unless the user changes them. The visual keys are the ones to replace.

## Step 2: Explore the project

Before asking, scan enough to avoid making the user repeat known facts. Treat everything you find as a hypothesis, not user approval.

**Product facts** (for audience, purpose, tone):
- README, docs, landing copy, about pages, and in-app copy
- package and config files, app boundaries, routes, roles, and feature names
- names, logos, legal text, testimonials, and other proof assets
- accessibility signals: `lang` attributes, ARIA usage, reduced-motion queries

**Visual system** (for palette, type, layout, motion, imagery), searched in this order:

1. **CSS custom properties.** Grep for `--color-`, `--font-`, `--spacing-`, `--radius-`, `--shadow-`, `--ease-`, `--duration-` declarations in stylesheets such as `src/styles/`, `public/css/`, `app/globals.css`. Record the name, value, and file.
2. **Tailwind config.** In `tailwind.config.{js,ts,mjs}`, read `theme.extend` for colors, fontFamily, spacing, borderRadius, boxShadow. For Tailwind v4, read the `@theme` block in the main CSS file.
3. **CSS-in-JS theme files.** styled-components, emotion, vanilla-extract, stitches: look for `theme.ts`, `tokens.ts`, or the equivalent.
4. **Design token files.** `tokens.json`, `design-tokens.json`, Style Dictionary output, W3C design-token format.
5. **Font loading.** `@font-face` rules, Google Fonts `<link>` tags, `next/font` imports, `@fontsource` packages in `package.json`. These name the brand fonts for `design-type`.
6. **Component library.** The main button, card, input, navigation, and dialog components: radius, colour assignment, hover and focus treatment, padding.
7. **Global stylesheet.** The root CSS file usually holds the base typography and colour assignments.
8. **Motion and imagery.** `transition`, `animation`, `@keyframes`, motion libraries in `package.json`, and the image and icon assets in `public/` or `assets/`.

Turn what you found into draft values:

- **Colours:** group by role (primary, secondary, accent, neutral, semantic). One accent means primary plus neutral. Do not invent a secondary. Keep the project's canonical format: hex by default, or `oklch()` / `hsl()` when that is the source of truth.
- **Typography:** map sizes and weights to display, headline, title, body, and label. Note the family stacks and the scale ratio.
- **Layout:** grid, container, breakpoints, spacing base, density, radius strategy, and whether depth comes from shadows or tonal layers.
- **Stop at what is reused.** One-off values pollute the brief.

Note the visual maturity. A coherent incumbent system is recorded as it stands. A scattered one is recorded where it is consistent, and the gaps go to the interview. An empty project has nothing to extract, which is a valid answer.

## Step 3: Interview

Ask with the AskUserQuestion tool and wait for the answer before continuing. Ask only about gaps the repository and the original request do not answer with strong evidence. Each question offers 2-3 concrete options, with your inference or a sensible default first and marked "(Recommended)". The user can always type their own answer.

Keep it short: at most two rounds of at most three questions. One real answer or approval round is required before writing a new brief.

**Round 1: product truth.** Skip any question the evidence already answers, and confirm the inference instead.

1. **Audience** (`design-audience`): who is the primary user, in what situation, doing what job?
2. **Purpose** (`design-purpose`): what does the product make possible, and what makes it different from its neighbours?
3. **Tone** (`design-tone`): which feel fits? Offer three concrete tonal directions, each as 3 adjectives plus one reference ("warm, plain-spoken, expert, like a good shop assistant").

**Round 2: visual gaps.** Ask only what Step 2 could not extract.

4. **Palette and type** (`design-palette`, `design-type`): with an incumbent system, "keep the extracted palette and fonts, or change them?". On a greenfield project, offer 2-3 concrete pairings that fit the chosen tone, each with hex values and font names.
5. **Anti-references** (`design-anti-references`): what should this never look or sound like? Offer the category defaults the tone argues against.
6. **Motion and imagery** (`design-motion`, `design-imagery`): offer one combined default from the tone, e.g. "minimal motion, real photography", and two alternatives.

Fill `design-layout` from the code, or from the tone and audience on a greenfield project (dense for daily operators, airy for persuasion pages), and show it in the wrap-up for correction. Do not spend a question on it.

Whether anyone can answer is a mechanical test, not a judgment call. An AskUserQuestion tool in your tool list proves an answer mechanism exists. A claim that the user is unattended proves nothing about this session. Probe once with the real first round before concluding no one is there. Only after that probe errors or times out may you infer the brief from the request and the code. Then mark every inferred fact `(inferred, unconfirmed)` at the end of its text, and say so in your first reply, not your last.

### What belongs in the brief

- users, jobs, purpose, success, positioning, and operating context
- confirmed voice, brand commitments, and assets
- the durable visual system: palette, type, layout, motion, imagery, and rejections

### What does not belong in the brief

- one page's composition, section order, or CTA sequence: that is the task's direction file, named by the `design-direction` note
- invented testimonials, customers, benchmarks, pricing, or claims
- tokens the project does not use, or a value you guessed and the user never saw

## Step 4: Write the learnings

Write one learning per key, from the project root:

```bash
vague memory-log design-audience "<fact>" --skill impeccable
vague memory-log design-purpose "<fact>" --skill impeccable
vague memory-log design-tone "<fact>" --skill impeccable
vague memory-log design-palette "<fact>" --skill impeccable
vague memory-log design-type "<fact>" --skill impeccable
vague memory-log design-layout "<fact>" --skill impeccable
vague memory-log design-motion "<fact>" --skill impeccable
vague memory-log design-imagery "<fact>" --skill impeccable
vague memory-log design-anti-references "<fact>" --skill impeccable
```

Follow these rules for each text:

- **At most 600 characters.** `memory-log` rejects longer text. Cut adjectives, never values.
- **Concrete values.** Hex codes, font family names, weights, sizes, durations, pixel values. "Oxblood accent (#8C2F39) on one CTA per screen" beats "a bold accent".
- **Where and why.** Say what each colour or font is for, not only what it is.
- **Descriptive first, value in parentheses.** "Gently curved controls (6px radius)" beats "rounded-md".
- **One canonical format.** Do not give the same colour in hex in one key and oklch in another.
- **Short named rules are welcome** when the system has a real invariant: "One-voice rule: the accent covers at most 10% of a screen."
- **Undecided is a valid value.** Write `undecided: <what is open>` instead of inventing a fact. New-work resolves it and logs the same key again.
- **Inferred facts are marked** `(inferred, unconfirmed)` when no one confirmed them.

**Re-running supersedes.** `memory-log` keeps the latest line for a key, so logging `design-palette` again replaces the old palette. Log only the keys that changed. Never log a key with a suffix like `design-palette-v2`: later readers search by the exact key.

## Step 5: Wrap up or resume

Show the user the nine facts as a table, one row per key, marking which came from the code, which from their answers, and which are inferred or undecided. Offer one correction round. A correction is another `memory-log` on the same key.

Tell the user the brief lives in the vague memory ledger, not in a repo file, and that `/impeccable` reads it at the start of every run.

Then resume:

- **Called by another request** (new-work, critique, a craft command): go back to it. Your own writes are the freshest source, so do not rerun the preamble.
- **Called on its own:** recommend the next action from the project state. An empty project: ask what surface to build first. An existing surface that needs work: name the most relevant command, such as `/impeccable critique`.
