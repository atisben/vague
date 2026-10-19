# Alma Preview Card

Use this small file for title-slide previews only. For final deck generation, read the full design doc listed below.

## Files

- Full design doc: `bold-template-pack/templates/alma/design.md`
- Preview card: `bold-template-pack/templates/alma/preview.md`

## Selection Metadata

- Slug: `alma`
- Tagline: Alma's house style: DM Serif Display titles with an orange italic accent, Inter text, full-bleed sky or orange title pages, and rounded colour tiles on white.
- Mood: corporate, consulting, clear, confident, warm, structured
- Tone: professional, direct, explanatory, friendly
- Formality: high
- Density: medium
- Scheme: light
- Best for: Any Alma deck: internal reviews, quarterly reviews and deepdives, architecture and roadmap proposals, working sessions, executive updates, and consulting-style recommendations that need a clear takeaway per slide.
- Avoid for: Decks that must not carry Alma branding (personal talks, other companies), and moody or experimental decks.

## Visual Snapshot

A clean consulting system with two personalities. Content slides are white, with a DM Serif Display headline carrying one orange italic accent word and a bold Inter takeaway sentence beneath. Title and section pages flip to a full-bleed sky blue (#7AD6E5) or Alma orange (#E75D36) with a two-line serif title: a roman ink line, then an italic white line. Structure is shown with flat, rounded colour tiles (sky, orange, sun) and pale outlined ghost cards for the current state.

## Preview Ingredients

- Palette: paper #FFFFFF; ink #120A07; orange #E75D36; sky #7AD6E5; sun #F8D648; mint #5DC38D; stone #69625D; line #D4D4D4
- Typography: DM Serif Display 400 roman + italic (all display text); Inter 400–800 (everything else). Inter is required by the brand; ignore the generic "avoid Inter" guidance for this template.
- Title slide: full-bleed `#7AD6E5` or `#E75D36`. Title block left edge at ≈540px, vertically centred. Line 1 in DM Serif Display 132px roman `#120A07`; line 2 in DM Serif Display 132px italic `#FFFFFF`. 48px below: meta lines in Inter 700 40px `#120A07` (team or duration), then the date in Inter 700 italic.
- Wordmark: "Alma" in white, top-left at 40px on orange pages or bottom-right on sky pages. Use the user's logo file if provided, else Inter 800 34px with -0.035em tracking.
- Chrome: "Confidential" in Inter 20px `#120A07` bottom-left for internal decks.
- Optional hero object: one user-supplied 3D image, or a single emoji at 160–220px, beside the title. Never more than one.
- Signature move: the italic second title line in white (on colour pages) or the one orange italic accent word (on white pages).
- Flat: no shadows, gradients, or patterns.

## Preview Rules

- Build exactly one title slide at 1920x1080 inside the fixed-stage model.
- Preserve the palette, type roles, surface rhythm, and decorative vocabulary described above.
- Use the user's real title/subtitle/context; do not copy demo slide content.
- The rendered preview must look like a real first slide, not a template-selection card.
- Never place internal workflow text on the slide: no `preview`, `generated from`, `preview.md`, `template`, `preset`, `style option`, `Option A/B/C`, file names, paths, or source-doc labels.
- Never place the template name or slug on the slide itself; mention it only in the chat message. The Alma wordmark is brand chrome, not a template label, and belongs on the slide.
- Never place user requirement notes such as desired vibe, audience, or internal-use labels on the slide unless the user explicitly wants those exact words in the deck.
- Use only real deck content for visible chrome: deck title, real section title, date, author, company, page number, or genuine content phrases from the user material.
- Do not read other templates' `design.md` files.
- After the user picks this template for the full deck, read the full design doc before generating final slides.
