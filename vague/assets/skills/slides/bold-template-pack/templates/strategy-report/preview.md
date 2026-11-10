# Strategy Report Preview Card

Use this small file for title-slide previews only. For final deck generation, read the full design doc listed below.

## Files

- Full design doc: `bold-template-pack/templates/strategy-report/design.md`
- Preview card: `bold-template-pack/templates/strategy-report/preview.md`

## Selection Metadata

- Slug: `strategy-report`
- Tagline: A strategy-consultancy research report as a 16:9 reading deck: bold serif over light sans, column text, a big Contents page, cobalt section openers, and "Exhibit N" charts.
- Mood: authoritative, editorial, analytical, calm, premium
- Tone: professional, evidence-led, considered, executive
- Formality: high
- Density: high
- Scheme: light
- Best for: Research reports, survey findings, state-of-the-industry reviews, strategy reviews, whitepapers, and executive briefings that are read or sent more than presented.
- Avoid for: Short talk decks with few words per slide, playful or informal decks, and anything that must look like a pitch.

## Visual Snapshot

A printed consultancy report on a white page. The cover splits in two: a flat illustration panel bleeds off the left (navy outlines, electric/cobalt/sky/teal/magenta fills, a halftone dot area, concentric rings), and the right side holds the title in a heavy bold serif in deep navy, with the year right-aligned beneath it. Inside, light sans body text runs in two or three columns, cobalt pull quotes span columns, and charts are labelled "Exhibit 1".

## Preview Ingredients

- Palette: paper #FFFFFF; ink #000000; navy #051C2C; cobalt #1537BA; electric #2972FF; sky #34B4F4; powder #99C4FF; teal #0BDACB; magenta #DB57DB
- Typography: Source Serif 4 700 (all display text, optical sizing on); Public Sans 300 (body), 500–600 (emphasis, tags, footer).
- Title slide: left 1100px is an inline SVG illustration panel (5–9 shapes: concentric rings with 3px #051C2C strokes, flat palette fills, one halftone `<pattern>` of white dots on #2972FF, small white "node" circles, one large sweeping curve), or a user photo. Right side on white: the organisation name at top (Source Serif 4 600 40px, navy, two lines, left edge 1160px, y 80px); the title in Source Serif 4 700 112px navy, 2–3 lines, vertically centred at left 1160px; the year or edition in Source Serif 4 700 72px, right-aligned to the title's right edge.
- Signature move: heavy navy serif title beside a flat, outlined, halftone illustration.
- Flat: no shadows, no gradients outside the illustration, no rounded cards.

## Preview Rules

- Build exactly one title slide at 1920x1080 inside the fixed-stage model.
- Preserve the palette, type roles, surface rhythm, and decorative vocabulary described above.
- Use the user's real title/subtitle/context; do not copy demo slide content.
- Use the user's organisation name. Never render "McKinsey", "McKinsey & Company", or "The State of Organizations".
- The rendered preview must look like a real first slide, not a template-selection card.
- Never place internal workflow text on the slide: no `preview`, `generated from`, `preview.md`, `template`, `preset`, `style option`, `Option A/B/C`, file names, paths, or source-doc labels.
- Never place the template name or slug on the slide itself; mention it only in the chat message.
- Never place user requirement notes such as desired vibe, audience, or internal-use labels on the slide unless the user explicitly wants those exact words in the deck.
- Use only real deck content for visible chrome: deck title, real section title, date, author, company, page number, or genuine content phrases from the user material.
- Do not read other templates' `design.md` files.
- After the user picks this template for the full deck, read the full design doc before generating final slides.
