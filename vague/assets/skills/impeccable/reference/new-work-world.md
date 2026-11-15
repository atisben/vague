<!-- Adapted from pbakaus/impeccable@2b86d9c (Apache-2.0). See ../NOTICE.md. -->

# New visual work: create or replace the visual world

The branch of [new-work.md](new-work.md) step 3 for a new or replacement world. Steps 4 to 7 of new-work.md follow it.

The mode file's **Directions** section governs every direction in this round, and it wins where it conflicts with shared guidance: [mode-persuade.md](mode-persuade.md) for Persuade and Experience, [mode-operate.md](mode-operate.md), or [mode-read.md](mode-read.md). Read it before step 1.

### Create or replace the visual world

1. Name the product's unique mechanism in one sentence, the audience's real scene, its cultural home, and what this first surface must prove. Note the page this category always ships and its predictable opposite. Both are the rut, kept out of the seven-candidate list. A brief that paints its own picture (a product name, a titled artifact, a governing metaphor) adds its literal reading to the rut: spend at most one candidate on it and derive the rest from elsewhere in the audience's world.
2. From that cultural world, list seven concrete visual systems, artifacts, places, or rituals the audience knows by heart, ordered by resonance. Give each one line on why it resonates and can carry the mechanism, and one line on how it looks: its ground and main colours, its type voices, and the one signature that makes it recognisable. The audience's world includes its graphic and screen traditions, not only its physical objects: the notation, publications, identity programs, data graphics, and interfaces it reads daily.
   - On an Operate or Read surface, the seven still come from anywhere in that world (its graphic traditions, places, rituals, and artifacts), never from the tools and instruments the audience operates. A terminal, a scope, or a control panel handed to a working screen comes back as a costume of that tool. A nameable abstract system (a school of poster, a documentation standard) is as concrete a candidate as any artifact.
   - On a Persuade or Experience surface, the tools and instruments the audience operates count toward the rut: spend at most one candidate on them.
   - Also ask what this thing would look like as a physical object, and what its world looked like before the web.
   - Near-duplicates count once. When more than three of the seven share one material family, the derivation stopped at the subject's most obvious artifact: dig until the list spans at least three families.
3. Turn that material into complete directions. Each joins a reusable visual world to a concrete first-surface experience.
4. Assign the lead by chance, then test it against challengers. Follow [The roll](#the-roll) below. No substitute and no skip: on a new or replacement world, writing artifact code before the roll has run and its assignment is acknowledged breaks this playbook, whatever the time pressure. The roll is what keeps every run from converging on the category default.
5. Present one direction, fully committed and already raised by the hands it beat, and let the user choose. Follow [Present the choice](#present-the-choice) below.

### The roll

The upstream engine dealt the lead from a seeded catalog. vague has no engine, so the session rolls the dice itself and authors its own challengers:

1. **Deal the lead.** Number your seven directions in resonance order, then roll:

   ```bash
   echo $(( RANDOM % 7 + 1 ))
   ```

   The command prints one number from 1 to 7, for example `4`. That direction is the assigned direction. The dice break the ranking rut while the user keeps a real choice.
2. **Deal two challengers.** Write two directions from foreign forms: visual systems from a culture, era, or discipline outside the audience's world that could still carry the mechanism. They are the outside hand the catalog used to supply. Fuse each challenger before judging it: the challenger supplies the form and its system grammar, the product supplies every fact, and clarity wins conflicts.
3. **Weigh them.** Weigh each fused challenger against the assigned direction on exactly two axes: audience identification and product clarity. Losing to strong grounded material is a valid outcome. Beating a thin or tool-monoculture list is the point.
4. **Give a verdict per challenger,** decided before any borrowing:
   - **wins:** beats the assigned direction on both axes, and becomes the build candidate.
   - **competitive:** holds one axis, and stays a full alternate.
   - **declined:** loses both.
5. **Raise the lead with what it beat.** A declined challenger is not spent. Name the one discipline of its system the assigned direction lacks, and raise the assigned direction to match before presenting it. A donation transfers ambition and system discipline (a palette's total commitment, a grid's density courage, a form's structural honesty), never the challenger's clothes. A component treatment, such as a button's shadow or a display face, is clothes, not discipline. A lifted motif is a costume note, not a raise, and one world owns the page. Write each raise into the presented direction as its own line, named for its donor. A raise nobody can read did not happen.

**The pinned exception.** A direction the user or the brief pins whole skips the roll. A whole pin names its world and its first-surface experience both, in words you can quote. Steps 1 to 3 then have nothing to derive and the roll has nothing left to bind, so there is no roll and no choice round. Confirm a pin that only the brief carries with the user, so the finish review can corroborate it, and record the pin in the direction contract (new-work.md step 5). Anything less rolls: a pin that leaves a dimension open, a direction you completed from a partial brief, or a brief's picture or metaphor alone, which is step 1's rut material.

### Present the choice

Write the full hand in the chat first, then ask. Every card has the same anatomy: thesis, palette (named colours with hex values), materials, type voices, first viewport, visitor path, signature interaction, cross-surface reach, honest risk, and, for challengers, the case lines. With no images, cards carry their identity in palette chips and facts, and that is a complete presentation, not a lesser one.

The hand holds these cards:

| Card | Shown as | Rule |
|---|---|---|
| Assigned direction | First, full card, raises visible as named lines | Always present |
| Your pick | Full card, kicker IMPECCABLE'S PICK | Only when your top-ranked grounded candidate is not the assigned one |
| Winning and competitive challengers | Full cards, each with its verdict and one-line case | At most three full cards besides the assigned one |
| Declined challengers | One compact line each: verdict and what the assigned direction kept from it | Never full-size, never silently dropped, still adoptable on request |
| The standing exit | Last, one quiet line: the category standard, played straight | Always present |

The pick card names its familiarity in its honest-risk line when that is true. The strongest grounded direction is often where most runs in this category land, and the user deciding that trade is the point of showing it. Familiar and effective is a legitimate destination, not a failure of nerve. One pick card, never two, never a ranked list: a lineup of your candidates hands selection back to a taste function and invites the safest card. The pick never takes the lead position. When the dice assign your top candidate, there is no pick card, and the assigned card notes that it topped your list.

The hand's size follows the verdicts, never a number the user named. When the weighing yields fewer full cards than asked, deliver the honest hand, say in one line why it is smaller, and offer a re-roll. A declined challenger is never promoted to fill a slot: a promoted card looks exactly like a competitive one, so the promotion leaves no trace. When more than three challengers earn full cards, the three strongest join and the rest wait in the re-roll pool, noted in one line. Dropping a challenger from the hand takes a named product-truth failure, disclosed.

Then ask with `AskUserQuestion` (header: "Direction"). The tool holds at most four options, so the options are:

1. the assigned direction, with the declined challengers' kept lines folded into its description, so the raises survive the text channel;
2. the pick, or the strongest full-card challenger when there is no pick;
3. the next full card, when one exists;
4. the standing exit.

Any further full card stays in the chat and is adoptable by name. Under the question, tell the user they can answer "Other" with a steer, or with a re-roll in one of three registers:

| Register | What the next hand deals |
|---|---|
| plain | A fresh hand, same spread |
| safer | Your remaining conventional grounded candidates, plus the category standard set against named competitors |
| bolder | Foreign forms only, at full commitment |

The register is the user's steering on the familiar-to-bold axis, never yours to pre-select. A user saying "bolder" or "safer" while a direction round is open means these registers, never the `bolder` or `harden` commands. A re-roll eliminates every direction already shown, grounded and challenger alike: renumber the remaining candidates (derive more when fewer than three remain), roll again, deal fresh challengers, and present the new hand the same way. After two consecutive re-rolls, ask what quality is missing.

When `AskUserQuestion` errors, ask the same question in plain text and wait. With no answer at all, proceed unattended with the assigned direction and state your assumptions in the first reply.

### The standing exit

Every direction round offers one quiet, permanent alternative: the category standard, played straight. It is the user's door, never yours. Never recommend it, never weigh it against the roll, and never let it soften the dealt directions: the counterweights bind the unchosen default, not the chosen one.

When the user takes it (the exit option, a safer steer, or plain words asking for the familiar or competitor-like path), convention becomes the commitment. Ask once for two or three products this should sit alongside, make their craft level the bar, and execute the standard at full fidelity, without irony or smuggled quirk. When the user states it as a standing preference, record it in the brief: re-log `design-tone` with its existing fact plus the commitment, because a learning key keeps only its latest line.

### Re-rolls, pins and collisions

Re-roll on your own only on named factual grounds, when the assigned direction cannot carry the product's truth or task. Taste is never grounds. The user may re-roll freely, and a user- or brief-pinned direction beats the roll, always.

A pin names the look itself, in the user's words or as a brand commitment the user made binding. A product the brief cites as a reference sets the craft bar, not the world. An answer to an open steer that restates the brief pins nothing.

Resolve collisions field by field, and preserve every pinned constraint. In dimensions the brief leaves open, the assignment still binds through its topology, controls, state vocabulary, and ritual. When only its materials conflict with a pinned visual direction or a brand commitment in the brief, translate that material expression and name the translation in the presented direction. A look mismatch is not grounds to re-roll.

### When the choice lands

The chosen world is a working system, not a mood reference. Carry its palette and material, type and composition, topology, controls and state, and responsive rules into the product, as far as the surface's mode allows. How far a source that is itself an interface language may carry its grammar is the mode file's call.

Set the craft bar before building. Name two or three real examples of the chosen world at its best (a publication, an identity program, a place, a product), and hold the build to their finish, commitment, and art direction, never their composition. Your surface serves this product.

Then record the world in the brief, one fact per learning, so the mockups and the reviewers read a fixed identity:

```bash
vague memory-log design-palette "<colour strategy, then each named colour with its hex and its job>" --skill impeccable
vague memory-log design-type "<the named fonts: display face, text face, and what each sets>" --skill impeccable
vague memory-log design-layout "<grid, density, spacing rhythm, the signature structure>" --skill impeccable
vague memory-log design-motion "<the world's native motion and the signature interaction>" --skill impeccable
vague memory-log design-imagery "<imagery stance: photographic, authored, none; what it depicts>" --skill impeccable
```

Each command prints `OK <project>/<key>`. Log only the facts the direction decides, and leave every other brief key alone.

On a replacement world, these keys already hold the old world's facts. Show the user the old line and the new line for each key before you log, because the new line replaces the old one for every later session. The old look stays in the record as evidence of what the subject was, never as authority over what it becomes.

These first facts describe the direction. The build resolves them into real values, so [new-work.md](new-work.md) step 7 re-logs the same keys from the built world at finish. A rulebook written before the build gets defended against reality instead of describing it.

### Every direction must be viable

Every direction the roll can land on must already be viable: every relationship and claim it visualizes true, a real palette and component family, a distinctive composition with one product-specific experience, and workable at full-surface scale within the available assets, tools, and performance budget. A candidate that fails on truth is replaced before the roll, never rescued by it.

Truth binds claims, not demonstrations. In greenfield work, author whatever illustrative material the concept needs at full fidelity, label it synthetic wherever a visitor could mistake it for the real thing, and hand the user the list of what to replace with real material. What stays uninventable are commercial and factual claims: prices, customers, benchmarks, endpoints, capabilities the product does not have. Refusing a bold direction because its demonstration data does not exist yet is the timidity reflex wearing honesty's clothes.

What the opening must do, and how far the world may reach into the page, depends on the surface's mode. The mode file's Directions section governs every direction and card in this round, and its Comps section governs the mockups later. Where they conflict with shared guidance, they win.

Return to [new-work.md](new-work.md) step 4 once a direction is locked.
