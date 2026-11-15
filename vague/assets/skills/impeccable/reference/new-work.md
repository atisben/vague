<!-- Adapted from pbakaus/impeccable@2b86d9c (Apache-2.0). See ../NOTICE.md. -->

# New visual work

Use this flow for a new surface or a replacement visual identity. Three records hold what the build needs:

| Record | What it owns | Where it lives |
|---|---|---|
| The brief | Product truth and durable visual decisions | The `design-*` learnings: `vague memory-search design- --kind learning --skill impeccable` |
| The direction | This surface's strategy, its build path, and, on the mockup-led path, the mockup path and section checklist | The direction file `/tmp/vague-comps/<project-slug>/<page-slug>/direction.md`, pointed at by the `design-direction` note: `vague memory-search design-direction --scratch` |
| The approved mockup | The composition the user picked by sight | A vault note, pointed at by the `design-comp-<page-slug>` doc |

Complete [brief.md](brief.md) first when the preamble printed no `design-*` learnings. A brief with no `design-palette` or `design-type` fact does not route back to brief.md: the visual world is decided below.

## The two build paths

Every new surface is built along one of two paths. Step 3 says which one this surface takes.

| Path | What happens | When it fits |
|---|---|---|
| Code-led | Write the page directly from the direction contract | A precise request, an extension of an existing surface, or a working screen whose composition is clear |
| Mockup-led | Load [visualize.md](visualize.md) for three HTML mockups, the user picks one, [region-map.md](region-map.md) turns it into a checklist, and the build follows the chosen mockup | A new surface, or a direction whose composition is still uncertain |

The mockup-led path is always available: its mockups are static HTML files, so it needs no image tool. Offer it whenever the surface is new or the direction is uncertain.

## 1. Decide what is already true

Read the brief, then representative code, tokens, components, and assets.

- **Redesign:** preserve product truth, content, function, constraints, and explicit brand commitments. Replace the old visual world rather than polishing it. The old look is evidence of what the subject is, not authority over what it becomes.
- **Established world:** inherit it. A brief with no visual facts does not erase a coherent identity already in code: record that identity as brief learnings at finish (step 7) instead of inventing a replacement.
- **Incomplete brand:** preserve confirmed assets and recognisable traits, then expand the system with the user for this surface.
- **No visual authority:** create a new world with the user.

A section, component, feature, or state inside an established surface inherits that surface. Never turn a local addition into a new identity exercise.

## 2. Ask what will change the work

Before implementation, ask with `AskUserQuestion`. Ask two or three related questions. A precise request needs only a compact confirmation. Skip settled facts, not the confirmation: the brief settles the visual world, not this surface's purpose or concept.

The questions depend on the surface's mode:

- **Persuade:** who must act, what they should believe, and which real proof, content, or assets earn that belief.
- **Operate:** the task, the information, the important states, the frequency, and the constraints.
- **Read:** the reader's question, the source material, the structure, and the wayfinding.
- **Experience:** what leads, how exploration unfolds, and which interaction or transition matters.

Across modes, ask what success looks like, what must remain untouched, and what would make a polished result feel wrong. Never ask for CSS values or canned aesthetic lanes. On a new or replacement world these are product questions only. Propose no look of your own before [new-work-world.md](new-work-world.md) has run its roll, because a direction named in a question is the one the answer confirms.

The mode's own rules live in its file: [mode-persuade.md](mode-persuade.md) for Persuade and Experience, [mode-operate.md](mode-operate.md), and [mode-read.md](mode-read.md). Read the one for this surface now. Its Directions section governs every direction below, and its Comps section governs the mockups.

## 3. Choose the right amount of invention

### Extend an existing surface

Inherit its world and composition. Resolve only the new purpose, content, hierarchy, states, interaction, and how the addition joins the surrounding experience. There is no concept round, and no brief change unless the user approves a durable system change. Build code-led.

### Create a whole surface inside an established world

Keep the visual system fixed. Derive five to seven materially different structures from the content, the task, and user behaviour, ordered by resonance. For a genuinely open whole page, screen, or flow, deal three of them to the user:

1. Roll for the lead with `echo $(( RANDOM % <count> + 1 ))`, where `<count>` is the number of structures. The command prints one number, for example `3`. The dice break the ranking rut while the user keeps a real choice.
2. Take two more structures for spread, never simply the next two in rank.
3. Present the three as full descriptions of equal weight: what leads, the first viewport, the reading order, and the honest risk. The world is settled, so every option shows composition, not identity.

How the three reach the user depends on the build path:

- **Mockup-led:** render the three structures as the three mockups in [visualize.md](visualize.md), the dealt lead as `a-safe.html`. The user's pick there is the approval, so visualize.md's round is already done, with no second approval point.
- **Code-led:** ask with `AskUserQuestion` (header: "Structure"), one option per structure, its first viewport described in one line. The locked structure is the composition the build matches.

Never deal structures for a local extension or a precisely specified narrow request: shape those directly.

### Create or replace the visual world

Read [new-work-world.md](new-work-world.md) now and follow it. This path's steps, the roll, and the choice round live there. Come back for step 4 once a direction is locked.

### Choose the build path

Choose the path once per surface, after the surface's scope is clear and before any concept round:

| Situation | Path |
|---|---|
| Extension of an existing surface, or a precisely specified narrow request | Code-led, stated in one line, not asked |
| A new surface, or a direction whose composition is uncertain | Offer both, with mockup-led first on Persuade and Experience surfaces |
| A working Operate or Read screen whose composition is clear | Offer both, with code-led first: working screens often come out better built than pictured |

Offer the choice with `AskUserQuestion` (header: "Build path"), and state the trade beside each option:

- **Mockup-led:** three static HTML mockups first, a pick by sight, then a build held to the chosen mockup. It costs one extra round and wins the boldest composition on the table.
- **Code-led:** the page is written directly, and the ambition lives in the direction contract's FIRST VIEWPORT block plus a named signature interaction and motion grammar. It is faster, and the finish reviewer audits those promises in behaviour. Code-led is not a discount on commitment.

The answer binds this surface only. Record it in the direction file (step 5). When the user asks in words for a standing default, follow it in later surfaces of this session.

## 4. Commit the world

Pick a colour strategy before picking colours:

| Strategy | What it means |
|---|---|
| Restrained | Neutrals tinted from the world, plus one accent. Common on screens people operate or read, where the mode's rules still ask colour to do real jobs. |
| Committed | One saturated colour carries 30 to 60% of the surface. |
| Full palette | Three or four named colour roles. |
| Drenched | The surface IS the colour. |

Persuade and Experience surfaces have permission for the bolder strategies: take them when the brief allows. Colour commits at page scale: fields that own whole regions, not accents scattered over a neutral ground. Dark or light is never a default. Write one sentence of physical scene (who uses this, where, under what light) and let it force the answer.

Choose faces like objects from the subject's world, in the mode's register. Operate and Read surfaces are well served by system stacks and workhorse UI faces. Persuade and Experience surfaces want faces with a point of view, and these training-data defaults mean you stopped looking: Fraunces, Playfair Display, Cormorant, Lora, Crimson, Newsreader, Syne, Space Grotesk, Space Mono, IBM Plex, Inter-as-display, DM Sans, DM Serif, Outfit, Plus Jakarta Sans, Instrument Sans. Naming one of these faces anyway requires a reason no other face could satisfy. A subject association is never that reason: books wanting a serif, bookshops wanting hand-lettering, and tech wanting a mono are the associations the list exists to break. A face the brief names in `design-type` is a brand commitment, not a default: keep it.

Calibration: AI-generated interfaces cluster around a few looks regardless of subject:

- a warm cream ground, a high-contrast serif display, and a terracotta or signal-red accent;
- near-black with one neon accent and glowing edges;
- broadsheet-editorial hairlines, an italic display serif, and small tracked mono labels;
- flat saturated ink with black boxes, hard offset shadows, and heavy condensed display type.

All are legitimate when the brief calls for them. Where the brief leaves the aesthetic free, landing in one means the self-check failed. If someone could guess your aesthetic from the category alone, or from category-plus-avoidance, rework until neither answer is obvious. Energy is not the enemy of trust: a brief's negative constraints (no gamification, no hype) rule out those devices, not exuberance. Adjectives describing the product's behaviour (quiet support, calm coaching) do not dictate the surface's energy. A bookish, warm, or child-facing subject does not soften the calibration: book cloth, thread, jackets, endpapers, and shelf ephemera span the whole saturated spectrum, and cream paper is the smallest corner of that world. Landing on cream plus serif for a book subject is the default wearing the subject's clothes. A brief-pinned world pins the world, not its softest rendition: its full material range stays in play, and a rendition matching what any model ships for that world fails the self-check at execution rather than selection.

Your measured rendition prior: warm, bookish, family, and child-facing subjects come out as cream grounds, serif display with italic accents, and lamplight, even when the assigned direction never asked for them. Treat that first palette as already spent. Before writing code, reread your OWN-WORLD block. When it says cream, paper, parchment, ivory, or lamplight for a Persuade surface the brief did not pin, the rendition failed: rework it from the world's saturated materials first. The same subject renders as bookcloth, thread, jacket, and endpaper colour on other models. Nothing about the subject requires your default.

## 5. Record the decision

Before code, record the chosen direction as a development-only contract in the direction file. Use six short blocks, roughly 150 words in all. Do not spend tool calls counting words.

| Block | What it says |
|---|---|
| THESIS | The one idea this surface owns, and the category-default arrangement it refuses |
| OWN-WORLD | The palette and component language, specific enough to be recognisable with all content removed |
| STORY | What the visitor understands, believes, and does |
| FIRST VIEWPORT | The exact composition: what is where, at what scale, and where the primary action sits |
| FORM | The chosen form, its position on your ordered list, and the roll that dealt it (`roll: 4 of 7`), or `pinned:` followed by the quoted words that pin it |
| FINISH | Verbatim: "unreviewed is unfinished; this build ends with the finish review, the verdict, and the brief updated from the built world" |

Add one more line for the path: `PATH: mockup-led` or `PATH: code-led`. On the mockup-led path, [region-map.md](region-map.md) later adds the mockup path and the section checklist to the same file.

The contract is too long for a note: `vague memory-log` rejects text over 600 characters. So the contract lives in a file, and a short note points to it. Both paths write the file, in the same folder the mockups use. Create the folder with `mkdir -p /tmp/vague-comps/<project-slug>/<page-slug>`, then write `direction.md` there with this template:

```markdown
# Direction: <page-slug>

THESIS: ...
OWN-WORLD: ...
STORY: ...
FIRST VIEWPORT: ...
FORM: ... (roll: 4 of 7, or pinned: "<quoted words>")
FINISH: unreviewed is unfinished; this build ends with the finish review, the verdict, and the brief updated from the built world
PATH: code-led | mockup-led
MOCKUP: <mockup-led only: added by region-map.md>

## Checklist

<mockup-led only: one item per section, added by region-map.md>
```

Read the file back once, and verify that all six blocks, the path line, and the roll or pin are present before building.

Then log the note that points to the file:

```bash
vague memory-log design-direction "<page-slug>: <thesis in one line> | PATH: <code-led|mockup-led> | FILE: /tmp/vague-comps/<project-slug>/<page-slug>/direction.md" --scratch --skill impeccable
```

The command prints `OK <project>/design-direction`. A note key keeps only its latest line, so keep this note short and re-log it only when the thesis, the path, or the file changes. Every other change, including the ticked checklist, is an edit to the file. A build that resumes reads the note, then the file it names.

The note expires after seven days, and `/tmp` may be cleared on reboot. A build that resumes later re-creates whatever is missing first: the file from the approved mockup and the decisions above, then the note. The approved mockup itself is safe in the vault, behind the `design-comp-<page-slug>` doc.

The note and the file are the reminder later agents reload across edits and sessions. A page that looks complete with the FINISH line undischarged is not done: it is abandoned at the finish line. If a block reads like a mood, the direction is not decided yet. The finish review audits the render against this contract.

Never copy the direction contract into implementation source or any browser-delivered artifact. This includes HTML or framework comments, hidden DOM, `<template>` elements, `data-*` attributes, rendered JSX or TSX output, serialized props or state, React Server Component payloads, client bundles, metadata or JSON-LD, accessibility-only text, and files served beside the artifact. A compiler or optimizer removing development metadata is not a safety boundary. The reviewers read the contract from the direction file. The file sits beside the mockups under `/tmp`, never beside the artifact.

The brief changes at two moments only. A new or replacement world logs its first `design-*` facts when the direction locks ([new-work-world.md](new-work-world.md)), and step 7 re-logs them from the built world at finish. An ordinary extension does not rewrite the brief.

On the mockup-led path, load [visualize.md](visualize.md) now and follow it: three compositional mockups before the user, one approval, then [region-map.md](region-map.md). A structure the user already picked as a mockup in step 3 has discharged visualize.md's round: continue at its After approval section. On the code-led path, the mockup round is skipped by choice, never by drift: the ambition it would have carried lives in the FIRST VIEWPORT block and the named signature interaction.

For `shape`, return the selected direction to [shape.md](shape.md) and stop before the direction file, the note, or any implementation.

## 6. Build with full commitment

Build the assigned direction, not a safer interpretation of it. The form supplies structure, reading order, component conventions, and native motion. The product supplies every fact. Commit every atom: nav, buttons, inputs, and links are rebuilt in the form's vocabulary, and a stock component inside a committed form is a lapse. Land the first build fully committed. The passes that follow exist to make the committed thing clear and effective, never to dilute it. In unattended work, the safe rendition is the known risk.

### Mockup-led: the mockup is a measured contract

The approved mockup is a spatial contract, not a mood board. Only the user can downgrade its authority, in explicit words. Models systematically believe their recreation of a reference succeeded when it did not, so the build runs as five checkpoints. Each checkpoint has an exit condition you check against the mockup, never against memory. After each one, edit the direction file to tick the finished items `[x]`, so a later session resumes at the first open item. Write nothing for a later checkpoint while an earlier one is open.

The checkpoints run in this order:

1. **Map.** [region-map.md](region-map.md) has written the section checklist and the mockup path into the direction file. Exit: every visible element of the mockup belongs to a checklist item, and every image placeholder is its own item.
2. **First viewport.** Build only the first viewport, at the mockup's own width. Read sizes, spacing, colours, and type off the mockup's CSS rather than estimating them. Copy the mockup's words verbatim: the user approved that mockup with those words, so rewording is a stated decision after this checkpoint, never a silent one inside it. Produce or source each image the viewport holds before laying text over it ([visualize.md](visualize.md), Images). Exit: open the mockup and the build side by side at the same width, and walk the viewport's checklist items. Each one is a match or a cited adaptation, none is missing or contradicted, and nothing appears that the mockup does not show.
3. **Sections.** Build the rest of the surface inside the same system: the same corner language, line weights, and palette, and nothing the mockup never shows. Where the mockup does not cover a region, it inherits the recorded system. Exit: every checklist item is ticked, after the same side-by-side check.
4. **Motion.** Build the signature interaction, reveals, and motion, orchestrated once rather than scattered. Exit: every moving part the checklist names moves, and content stays visible with motion off.
5. **Responsive.** Build the other viewports, and check the first viewport at common desktop widths (1280 to 1600), not only at the mockup's width. Use fluid columns, no fixed-pixel grid that wraps a hundred pixels narrower, and sizes in proportion to the viewport rather than px floors. Exit: nothing the mockup's first viewport shows is pushed below the fold at desktop width. A displaced section is restored by resizing what sits above it, not by moving it alone. A mobile-first surface was mocked in a 390px frame: hold the phone build to that frame.

Anything not in the mockup does not exist on the page: no borders, rules, containers, or chrome the mockup does not show. Four concessions exist, and only four:

- **Fonts:** the closest obtainable face, when the brief's face cannot be served.
- **Icon glyphs:** close enough, exact if the user chose an icon library. This covers the pictogram only, never a control's chrome: a chevron, an arrow, a dropdown's border and fill, and a button's shape are the mockup's.
- **Placeholders:** each labelled box becomes the real image it names, at its box.
- **Defects:** genuine defects in the mockup, such as spelling errors.

When the first viewport still fails its exit after three attempts, stop iterating. Show the user the mockup and the build side by side, name the items that still miss, and ask with `AskUserQuestion` whether to accept the viewport as it stands, rebuild it, or revise the mockup. Once the user accepts a first viewport, hold it: later edits that drift from what they accepted are restored, and that question is never asked again. This checkpoint is where the run's ambition is won or lost. A retry here costs minutes, where a rebuild verdict at the finish costs the run.

### Code-led

There is no mockup and no apology for it. The ambition lives in the direction contract's FIRST VIEWPORT block and the named signature interaction, and the finish reviewer audits those promises in behaviour. When step 3 locked a structure, that structure is the composition the build matches.

### Both paths

- **The first viewport is a thesis, not a header.** Demonstrate the mechanism immediately, at the scale the form has in life. Do not trap the concept inside a standard hero or card shell. The memory test: if someone left after one viewport, what would they describe an hour later? If the honest answer is a mood, the concept has not committed yet.
- **Prove, don't claim.** Show the subject doing its job: the interface at work, the mechanism dramatized, specifics a competitor could not copy-paste. Demonstration data is design material: author it at full fidelity and label it synthetic. Claims stay uninventable.
- **Author the assets, never substitute chrome.** Great surfaces live on carefully made content: names, entries, copy, covers, thumbnails, textures. In greenfield work, every blank the question round left open is yours to author at production fidelity. Content is authorable, claims are labelable, and no section is omittable. Gradients, glass, generic icon tiles, and many-vertex `clip-path` polygons where an authored asset belongs are the gap wearing chrome.
- **Build the form's web leverage.** When the chosen world names a technique (canvas, WebGL, view transitions, generative motion), build the technique itself, not a static imitation of it.
- **Pace the scroll like a studio.** Vary density, scale, image, motion, and quiet inside one grammar. A dense passage earns a quiet one, and the page ends anchored by a real close. Keep one spacing rhythm throughout, with more space above a heading than below it.
- **Use real, verified imagery when the brief implies it.** Search for the subject's physical object rather than the category. One decisive photo beats five mediocre ones. Verify that stock URLs resolve.
- **Author motion as material.** Give the page the form's native motion once, orchestrated, rather than scattered hover effects. Bound expensive effects and keep content visible by default. [animate.md](animate.md) holds the deeper motion playbook.

Preserve semantics, accessibility, performance, responsiveness, project conventions, and working behaviour.

## 7. Inspect and finish

### Inspect

Inspect the surface's target sizes in one batched screenshot round, with whatever browser tool the session has. Capture desktop and mobile. When the session knows the user's actual viewport (an in-app browser's size, a named resolution), add that width: the width that breaks is the one the user sees first. On anything interactive, the round drives every interaction and reachable state (open, closed, hover, focus, error, empty, overlong content) and checks each for overlap and clipping, not only the resting screen.

Critique the render against the user's request and the direction contract, fix material gaps, and confirm with one final round. Two rounds is the ceiling, and fixes batch between them rather than earning per-tweak screenshots. The ceiling bounds inspection. It never closes an open checkpoint: a checkpoint stays open until its exit holds or the user decides it.

On the mockup-led path, the critique is a side-by-side comparison. Open the mockup and the build at the mockup's width, walk the checklist, and give each item one word: match, adaptation, missing, contradicted, or added. A section scored missing or contradicted is a fix, whatever the page looks like from memory. Never judge fidelity from one full-page thumbnail: it hides exactly the failures that matter. On a Persuade surface, verify that the mode did its job: a first-time visitor should know what this is, why it matters, and what to do within seconds, in the form's own vocabulary.

A capture is evidence only when it is valid, and you validate it before you send it. Settle or disable entrance motion first: an element hidden by animation timing reads as a missing element and gets "fixed" into a regression. Capture full-page shots from the document top. Then open every file once and confirm it shows what its name claims: no black or blank regions, no wrong section behind a right filename, no half-loaded state. A malformed capture sent onward costs the whole round, because the reviewer answers it with `disposition: recapture` and nothing it reviewed binds.

Save the captures in one folder, one file per viewport:

| Capture | Path |
|---|---|
| Desktop, 1440 wide, full page | `/tmp/vague-comps/<project-slug>/<page-slug>/review/desktop.png` |
| Mobile, 390 wide, full page | `/tmp/vague-comps/<project-slug>/<page-slug>/review/mobile.png` |
| The user's viewport, when known | `/tmp/vague-comps/<project-slug>/<page-slug>/review/user-<width>.png` |

Create the folder with `mkdir -p` first. Every viewport you inspected is named as required in the reviewer's packet. When the session has no browser tool at all, say so in one line, and pass the reviewer the source files only.

After the second inspection round, the build thread's polishing is over: no further defect hunts, micro-edit scripts, or rebuilds here. An open checkpoint is not a defect hunt: it closes as described in step 6. Whatever remains ships through the review, where a fresh context does the finding better and cheaper.

### Review

Spawn the finish reviewer, `impeccable-finish-reviewer`, with the `Agent` tool. Pass this packet:

- the original request and the confirmed user answers;
- the artifact path(s);
- the screenshot paths from the Inspect table, each named as required;
- the chosen mockup path on the mockup-led path, or the line "code-led: no mockup";
- the path to [craft-floor.md](craft-floor.md).

The reviewer reads the brief and the direction note itself, through `vague memory-search`, then the direction file the note names. It has no browser: screenshots you fail to pass are checks it cannot run. When the build carries a signature interaction or orchestrated motion, also spawn `impeccable-motion-reviewer`, as [animate.md](animate.md) describes.

Spawn each reviewer fresh, with no forked conversation history. A reviewer that inherits your transcript inherits your framing, your optimism, and your abstractions, and everything it needs travels in the packet. Never read the agents' definition files before spawning: the harness loads them, and you owe only the packet. Wait on each agent with one long timeout rather than a loop of short polls, and spend the wait on the next independent step. Verify that the return opens with a disposition line and carries the reviewer's contracted sections. On an empty or thrashed return, respawn once with the same packet.

Only a session with no subagent tool at all substitutes an inline pass: step fully out of the build context, then run the review from [degraded/finish-reviewer.md](degraded/finish-reviewer.md) (and [degraded/motion-reviewer.md](degraded/motion-reviewer.md) for motion). Disclose a substituted or failed-and-replaced review in one line at finish, never silently.

### Act on the disposition

The reviewer's first line is one of exactly four words:

| Disposition | What it means | What you do |
|---|---|---|
| recapture | The evidence failed, not the build | Recapture what the return names under the capture-validity rules, then run a full review over the new evidence |
| rebuild | Fidelity failed wholesale, not in patches | Skip the fix batch and rebuild at once: re-derive the named sections, produce the named assets, and send the result for a fresh full review |
| fix | Material fixes are owed | Apply them in one batch, rebuild once, recapture the same viewports over the same files, then send them for a verdict pass |
| ship | Nothing is owed | Report the verdict at its scope, then update the brief |

A review conducted on invalid evidence binds nothing, and a verdict pass may never follow it. A rebuild replaces sections wholesale, so the whole review runs again over the recaptures, never a verdict pass. Tell the user what is happening rather than asking permission to fix a failure. Consult the user only on a second rebuild directive, when both verdicts are on the table, or when rebuilding would discard content the user approved.

A recapture measures positions, loading, and overflow. It cannot measure whether a fix reached the quality the finding named. So send the recaptured screenshots back to the same reviewer for a verdict that scores every material fix resolved, partial, or unresolved. Continue the same agent with `SendMessage`. Without one, run the scoring fresh from the Verdict Pass section of [degraded/finish-reviewer.md](degraded/finish-reviewer.md). Fixes scored partial or unresolved get another batch, recapture, and verdict.

Two rounds is the budget an unattended run ends at. An attended session's ceiling belongs to the user: when the second verdict still lists open items, put the table in front of them, and let them choose between shipping as it stands and funding another round. Whoever decides, stop the moment a round resolves nothing. The reviewer's findings are the only list you work from, never your own re-opened hunt.

A rebuild and a fix round share one asset rule. An image either round creates or replaces follows [visualize.md](visualize.md)'s Images section, with its source noted. An image the round abandons is deleted in the same batch.

### Report the verdict

Report the final verdict under the reviewer's own disposition word, at its actual scope. A verdict pass scores the listed fixes and nothing else: "the reviewer scored all three fixes resolved" is a claim it supports, "no material issues remain" is not. A table with open material findings is never announced as a pass, never softened, and never dressed as whole-surface approval when only a fix list was scored.

When the user answers a ship with evidence against it (their own screenshot, a named mismatch with the mockup), that evidence outranks every capture you made. Put their material in the packet and spawn a fresh reviewer for a new full review. Patching inline and self-certifying is how a rejected page ships twice.

### Update the brief

After the last correction, the brief catches up with what was built:

- **New world, replacement world, or approved system change:** draft one fact per affected key from the built world, not from the direction: `design-palette`, `design-type`, `design-layout`, `design-motion`, `design-imagery`. Show the user each current line beside its new line, and ask with `AskUserQuestion` which to replace. Then log each approved fact with `vague memory-log <key> "<fact>" --skill impeccable`. Each command prints `OK <project>/<key>`.
- **An established world first recorded in this run:** log the identity the code already carries, the same way.
- **Ordinary extension:** compare the finished build against the brief, leave the brief unchanged, and report the evidence you checked. Report drift that predates this run without repairing it unasked.

Recheck after later edits. Then add the final line `FINISHED: <disposition word>` to the direction file.

Finish only when the review and the brief update are complete. A refused ship is an unfinished build: report the open items with the verdict. Any edit after the last capture, a fix after `ship` included, voids that capture: recapture and confirm the edited viewport before you stop. Never end a run over an open checkpoint by calling it fixed. Take the route the checkpoint names, and when the user leaves it open, report that checkpoint as open.
