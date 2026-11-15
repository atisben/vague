<!-- Adapted from pbakaus/impeccable@2b86d9c (Apache-2.0). See ../NOTICE.md. -->

# Visualize: Three HTML Mockups

Load this from [new-work.md](new-work.md) on the mockup-led path. A code-led build skips this file by design, not by drift; do not load it then.

The brief is a precondition: the `design-*` learnings the preamble printed. On a new or replacement world, the chosen direction fixes the identity instead: its `design-*` learnings were logged when it locked ([new-work-world.md](new-work-world.md)), and the direction file the `design-direction` note names carries the rest. The mode file's **Comps** section governs these mockups together with this file, and it wins where they conflict: [mode-persuade.md](mode-persuade.md) for Persuade and Experience, [mode-operate.md](mode-operate.md), or [mode-read.md](mode-read.md). New-work has already resolved the visual world. This file must not reopen it.

A surface round inside an established world may already have rendered its three structures as mockups ([new-work.md](new-work.md), step 3). That round is this round: go straight to [One approval point](#one-approval-point) and write nothing new.

A probe tests composition, narrative, hierarchy, density, focal moment, signature use, and image requirements. It is not a second identity workshop. Keep the world's palette, typography direction, material language, component character, imagery stance, and motion grammar fixed. They come from the brief on an established world, and from the chosen direction on a new one.

## The mockup set

The three mockups are three files in one folder per page:

| File | What it is |
|---|---|
| `/tmp/vague-comps/<project-slug>/<page-slug>/a-safe.html` | The lead composition: the direction's own first viewport, at full commitment, in the reading order the mode expects |
| `/tmp/vague-comps/<project-slug>/<page-slug>/b-bold.html` | Goes further than A: the world's material carries more of the page's structure, or the focal move is larger or stranger |
| `/tmp/vague-comps/<project-slug>/<page-slug>/c-wildcard.html` | A composition the category would not attempt, still in the same world and still a working page |

`<project-slug>` is the `SLUG` the preamble's `vague context --shell` set. `<page-slug>` names the surface in lowercase `[a-z0-9-]`, for example `pricing` or `onboarding-step-1`. Create the folder first:

```bash
mkdir -p "/tmp/vague-comps/$SLUG/<page-slug>"
```

The command prints nothing on success.

"Safe" names A's place in the spread, not a lower bar. A is the composition a strong studio would ship first, fully committed in the world. It is never the category template with the world's colours on it. B and C each go further than A, never cleaner: a variant that simplifies A into a tidier version of itself adds no choice to the round.

## What varies, what stays fixed

The three mockups differ on four axes and agree on everything else:

| Varies across A, B, C | Fixed by the brief or the chosen direction |
|---|---|
| Composition: what leads the screen, topology, sequence | Palette |
| Hierarchy: what is biggest, what reads first | Type voices and the named fonts (`design-type`) |
| Density: how much each viewport holds | Tone and copy voice |
| Focal moment: the one dominant move | Imagery stance (`design-imagery`) |

When the user shortlisted several concepts, spread the three across them. When one direction is committed, vary the structural uncertainty a mockup can resolve: what leads the screen, topology, sequence, density, hierarchy, focal composition, or interaction framing. Write each mockup from the direction in words. Never start B or C by copying A's markup: a shared skeleton collapses three compositions into one.

Do not make a palette artifact, ask new atmosphere questions, introduce a different type voice, or invent a new motif. If the committed world cannot support the concept, return to the concept shortlist rather than changing the world.

## Write the mockups

Each mockup is one static, self-contained HTML file:

- **Self-contained.** All CSS sits in one inline `<style>`. No external stylesheet, script, font, or image URL, and no network at all.
- **Static.** No JavaScript is needed. Show the signature interaction as one frozen, legible moment, and say in the approval question what moves.
- **Fonts.** Name the brief's face first in `font-family`, then the closest system fallback. A face that is not installed on this machine renders as the fallback. Say so when you show the mockups, so the user judges composition, not a substitute face.
- **Images.** Every image is a labelled placeholder box: a block at the image's real aspect ratio, a flat tint from the palette, and a visible label that names the picture, for example `photo: team at a whiteboard`. Inline SVG is allowed for icons and for diagrams the page will really draw in code, never as a stand-in for an illustration.
- **Viewport.** Comp at the surface's own viewport. A desktop surface fills a 1440px-wide page. A mobile-first surface, or a native app screen, sits in a fixed 390px-wide frame centred on a neutral ground, so a desktop browser shows the phone composition. A phone screen comped at desktop width misstates the composition before anything is built against it.
- **Reach.** Show the first viewport and the start of the section below it, plus enough beyond the opening moment to prove the concept can govern the whole surface.

Mockups are the build thread's own work, never delegated. The thread that writes them holds the direction's full context, and it has seen every mockup when the build starts.

### Authoring rules

These rules adapt upstream's comp discipline to HTML. Each one names a failure a mockup can hide:

- **A finished screen, never a fragment.** The page shows the product's mark and name, its navigation, its utility controls, and its far edge. A page with no navigation says so instead of inventing one. No browser window, device bezel, or desk around it.
- **The visitor's job is the spine.** Name the product, by name, and fill the page with the real content that answers the visitor's job: names, numbers with units, the offer or the state, any claim at its honest certainty, and the next action by name. Decide what leads this mockup (summary-led, timeline-led, offer-led, reference-led), then lay the parts out in reading order.
- **The subject must be in it.** Before accepting a mockup, point at the subject. A mockup that depicts the world and nothing of the subject fails however faithful its atmosphere. Rewrite it with the subject's content named.
- **Judge it as the shipped screen.** The visitor's job must be readable from the page alone. Name the surface's mode from the page with no caption. A page whose mode cannot be read back is art direction without a surface.
- **Commitment is depth, not performance.** The world enters through one dominant move, plus the material, type, and spacing that support it. The remaining regions hold still in that material and keep their content at real reading size. A second element competing with the lead at the same scale is the mockup shouting: keep the strongest move and quiet the rest. Busy is louder, not bolder.
- **A template is a template whatever world paints it.** A split hero with a badge row, or a centred headline over a row of equal cards, is the category default with a skin. The mode file's Comps section says how far the world may carry the page.
- **Truth binds claims, not demonstrations.** Author demonstration data at full fidelity and label it synthetic wherever a visitor could mistake it for the real thing. Never invent prices, customers, benchmarks, or capabilities.
- **No workflow text on the page.** Never render `Option A`, `safe`, `bold`, `wildcard`, `mockup`, a file name, or a path inside the mockup. The page must look like the real first screen of the product.

A colour, typeface, or brand element the user pinned is content: use it exactly.

### Check before showing

Open each file once and confirm it renders: nothing blank, nothing clipped, the right composition behind the right filename. Then confirm no file reaches the network:

```bash
grep -nE 'https?://|src="//|@import' /tmp/vague-comps/"$SLUG"/<page-slug>/*.html
```

The expected output is empty. A hit is a dependency to inline or delete before the user sees the file.

Each mockup is a direction test, not a screenshot specification. Core UI text, responsive behaviour, accessibility, semantics, and interaction states remain implementation work.

## One approval point

Open the three files for the user:

```bash
open /tmp/vague-comps/"$SLUG"/<page-slug>/{a-safe,b-bold,c-wildcard}.html
```

The command opens three browser tabs and prints nothing.

Then ask with `AskUserQuestion` (header: "Mockup"). Give one option per mockup, each labelled with its letter, a two-to-four-word name, and what leads it:

- A: <name> · <what leads, in one phrase>
- B: <name> · <what leads, in one phrase>
- C: <name> · <what leads, in one phrase>

Under the question, ask what should carry forward, what feels false to the world, and whether the pick is approved as it stands, combined with parts of another, or revised. The user answers "Other" to combine, revise, or reject all three. Then stop and wait.

The answers route like this:

| Answer | What happens next |
|---|---|
| A, B or C as it stands | That file is the approved mockup |
| Combine | Edit the base file to take the named parts of the other, reopen it, and ask again |
| Revise | Edit the chosen file as asked, reopen it, and ask again |
| Reject all three | Return to the concept shortlist in [new-work.md](new-work.md), never to the world |

Do not begin code until the user approves a mockup or explicitly delegates the choice. If they delegate, choose from the brief and the chosen direction, and state the evidence. Approval refines the surface concept. It does not change the brief.

This approval point has no substitute and no skip condition. When `AskUserQuestion` errors, ask the same question in plain text and wait. Only when no answer comes at all may you treat the choice as delegated. Record a delegated pick exactly as an approval, and disclose it in your first reply, not your last. The finish reviewer treats a build from a mockup with no recorded pick as a material finding.

## After approval

Record the pick where later sessions and the reviewers can find it, in this order:

1. **Export to the vault.** Run `/vault export "<path>" title "Design Comp - <Page>" folder "6. Atomic Notes/" tags "design,impeccable" kind "plan"`, where `<path>` is the approved mockup's full path under `/tmp/vague-comps/` and `<Page>` is the surface's name in title case. /vault copies the HTML into the vault and writes a note that embeds it.
2. **Read the note path.** /vault prints `VAULT_NOTE: <path>`. Keep that path.
3. **Log the doc pointer.** Run `vague memory-log design-comp-<page-slug> "<one line>" --doc --files "<vault note path>" --skill impeccable`. The one line names the page, the chosen mockup, and what leads it. A later session finds it with `vague memory-search design-comp-<page-slug> --kind doc`, even after `/tmp` is cleared.
4. **Map the mockup.** Load [region-map.md](region-map.md). It turns the mockup's sections into the build checklist and writes it, with the mockup path, into the direction file (`direction.md` in the same folder as the mockups).

Then summarise the composition and the parts of the mockup that must not be literalized, return to [new-work.md](new-work.md), and build.

### The mockup becomes a spec

The approved mockup is a north star for translation into semantic, responsive, accessible code, never a license to recompose. Keeping the palette and mood while redrawing the topology is a second art direction. Do not substitute a different visual driver after approval without asking.

What the mockup shows is measured, not remembered. Its CSS holds the real values: read sizes, spacing, line lengths, and colours off its source rather than from your memory of the page. The mockup's markup is still reference, not production code: rebuild each section in the project's own components and tokens.

Each placeholder's medium follows from what it names, never from what feels buildable. A figure, a product object, machinery, any illustration with perspective, shading, or drawing skill in it, and any texture by name (woven cloth, paper grain, leather, brushed metal) ships as a raster image. Text, controls, chrome, diagrams with countable elements, flat shape systems, and anything that must move, scale, or respond are drawn in code. Writing CSS for a sculpted panel's finish, or a many-vertex `clip-path` for a torn edge, quietly deletes the approved design. Dropping an image is a scope decision the user makes at the approval point, never a silent flattening after it.

## Images

Every placeholder becomes a real asset before the section that holds it is called done:

- **Real imagery.** Search for the subject's physical object rather than the category. One decisive photo beats five mediocre ones. Verify that every stock URL resolves, and note its source and licence in the handoff.
- **User material.** Use what the user supplied, at the placeholder's aspect ratio.
- **Authored material.** Demonstration imagery is design material: author it at full fidelity and label it synthetic wherever a visitor could mistake it for real.

Generated imagery is a material, not a claim. Evidence rules bind assertions, specs, testimonials, and photographs presented as real, never render fidelity. An asset a fix round abandons is deleted in the same batch. End the build by handing the user the list of placeholders still holding demonstration material, so they know what to replace.

Return to [new-work.md](new-work.md) for the direction contract, the checkpointed build, and the finishing pass.
