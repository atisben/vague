<!-- Adapted from pbakaus/impeccable@2b86d9c (Apache-2.0). See ../NOTICE.md. -->

# Region map

A region map names what is actually visible in the approved mockup before anything is built. It is not a page build or an asset approval. In vague it is a checklist: one item per section, written into the direction file together with the mockup path. The build in [new-work.md](new-work.md) step 6 works through it, and the reviewers compare the built page against it.

## Build the checklist

1. **Open the mockup twice.** Open the approved file in the browser and read its source. Never edit the approved file: it is the fixed reference the build and the review measure against.
2. **List the sections in reading order.** Walk the page top to bottom. Give each section a stable id in lowercase `[a-z0-9-]`, for example `nav`, `hero`, `proof-strip`, `pricing-table`, `close`.
3. **Fill in three fields per item.** Each item gives its id, what it holds, and what varies independently. See [What varies independently](#what-varies-independently).
4. **Split what is too big.** A section larger than a quarter of the page that holds several separate elements is a column, not an element. Name each element inside it as its own item, with the section as its parent. See [Containment](#containment).
5. **Check coverage.** Walk the mockup once more and point at every visible element: each one belongs to an item. What is never named can never be missing, so the review cannot catch it.
6. **Write it into the direction file.** See [Record the checklist](#record-the-checklist).

If the request ends at mapping, stop with the checklist and any unresolved questions. Otherwise return to [new-work.md](new-work.md) and build.

### One item, filled in

This item is an example. It maps a hero that shows a product photo behind a framed window, with a booking form on top:

```
[ ] hero: headline "Rooms above the harbour", subline, booking form (dates, guests, Search); photo placeholder "photo: room with open shutters at dusk"
    varies: swapped = room photo; moving = shutters (open on load), form focus states; frame = window surround
```

## What varies independently

Split items by what varies independently. Each item names which of the three kinds it contains:

| Kind | What it is | Example |
|---|---|---|
| Swapped content | What the site changes without a redesign | Room photos, products, people, prices, entries |
| Moving parts | Anything a hover, a state change, or the signature interaction moves | Shutters, an expanding card, a tab indicator |
| Structure (frame) | Frames, surrounds, ornament, and layout that stay put | A window surround, a ruled grid, a spine |

A window with open shutters onto a room holds all three. The surround is the frame. The room is swapped content beneath it. Each shutter is a moving part. Build them as separate layers composited in the page, never as one picture of a framed view: a single baked image cannot swap its room or open its shutters.

## Containment

An item may name a parent: `parent: <id>`. Parent and children keep separate ids and separate checklist lines. Containment never transfers completion: ticking the parent does not tick its children, and each child is checked on its own.

## Painted material

Classify each item's medium while mapping, not during the build. A section the mockup draws as a labelled placeholder is an image to produce. A section the mockup drew in CSS, but which is painted material in life (a figure, a photograph, a metal or paper surface), is an image too: mark it `image` now. Leaving the catch to the build is how a painted surface ships as a gradient.

The mockup is reference evidence only. Its markup and placeholder boxes are never production assets.

## Record the checklist

The checklist goes into the direction file, `/tmp/vague-comps/<project-slug>/<page-slug>/direction.md`, which [new-work.md](new-work.md) step 5 created. A checklist is far longer than the 600 characters a note can hold, so it never goes into the `design-direction` note. Edit the file: fill the `MOCKUP:` line and replace the placeholder under `## Checklist` with one item per section, each in the form of [One item, filled in](#one-item-filled-in):

```markdown
MOCKUP: /tmp/vague-comps/<project-slug>/<page-slug>/<chosen file>

## Checklist

[ ] nav: ...
    varies: ...
[ ] hero: ...
    varies: ...
```

Leave the six contract blocks and the `PATH:` line as they are. Read the file back once to confirm the contract, the mockup path, and every item are there.

The `design-direction` note already points to this file, so it needs no new log. During the build, each checkpoint in [new-work.md](new-work.md) step 6 edits the file to tick its finished items `[x]`. The file is the build's state: a later session reads the note, opens the file it names, and resumes at the first unticked item.
