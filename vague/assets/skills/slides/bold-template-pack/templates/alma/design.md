---
version: alpha
name: Alma
description: "A consulting-grade corporate system on a clean white canvas: DM Serif Display headlines with one italic word picked out in Alma orange, Inter for every subtitle, label, and body line. Title and section pages flip to a full-bleed sky blue or Alma orange with a two-line serif title (roman ink line, italic white line). Content slides explain structure with rounded colour tiles (sky, orange, sun) and pale outlined ghost cards for the 'before' state. Derived from the Cobalt Grid system's flat, rule-based editorial structure, re-skinned for Alma."

colors:
  paper: "#FFFFFF"
  ink: "#120A07"
  orange: "#E75D36"
  sky: "#7AD6E5"
  sun: "#F8D648"
  mint: "#5DC38D"
  stone: "#69625D"
  line: "#D4D4D4"
  mist: "#F4F4F4"
  alert: "#EA3424"

color-aliases:
  brand: orange
  bg: paper
  text: ink
  muted: stone

typography:
  display-title:
    fontFamily: "'DM Serif Display', Georgia, serif"
    fontSize: "132px"
    fontWeight: 400
    lineHeight: 1.0
    letterSpacing: -0.01em
  display-section:
    fontFamily: "'DM Serif Display', Georgia, serif"
    fontSize: "112px"
    fontWeight: 400
    lineHeight: 1.02
    letterSpacing: -0.01em
  headline:
    fontFamily: "'DM Serif Display', Georgia, serif"
    fontSize: "92px"
    fontWeight: 400
    lineHeight: 1.05
    letterSpacing: -0.01em
  statement:
    fontFamily: "'DM Serif Display', Georgia, serif"
    fontSize: "76px"
    fontWeight: 400
    lineHeight: 1.12
  kpi-numeral:
    fontFamily: "'DM Serif Display', Georgia, serif"
    fontSize: "150px"
    fontWeight: 400
    lineHeight: 0.95
    letterSpacing: -0.02em
  subtitle:
    fontFamily: "Inter, 'Helvetica Neue', Arial, sans-serif"
    fontSize: "40px"
    fontWeight: 600
    lineHeight: 1.2
  title-meta:
    fontFamily: "Inter, 'Helvetica Neue', Arial, sans-serif"
    fontSize: "40px"
    fontWeight: 700
    lineHeight: 1.25
  column-heading:
    fontFamily: "Inter, 'Helvetica Neue', Arial, sans-serif"
    fontSize: "36px"
    fontWeight: 600
    lineHeight: 1.2
  tile-label:
    fontFamily: "Inter, 'Helvetica Neue', Arial, sans-serif"
    fontSize: "32px"
    fontWeight: 700
    lineHeight: 1.2
  tile-sub:
    fontFamily: "Inter, 'Helvetica Neue', Arial, sans-serif"
    fontSize: "24px"
    fontWeight: 400
    lineHeight: 1.3
  row-label:
    fontFamily: "Inter, 'Helvetica Neue', Arial, sans-serif"
    fontSize: "30px"
    fontWeight: 700
    lineHeight: 1.2
  body:
    fontFamily: "Inter, 'Helvetica Neue', Arial, sans-serif"
    fontSize: "28px"
    fontWeight: 400
    lineHeight: 1.45
  body-small:
    fontFamily: "Inter, 'Helvetica Neue', Arial, sans-serif"
    fontSize: "24px"
    fontWeight: 400
    lineHeight: 1.4
  caption:
    fontFamily: "Inter, 'Helvetica Neue', Arial, sans-serif"
    fontSize: "22px"
    fontWeight: 400
    lineHeight: 1.35
  chrome:
    fontFamily: "Inter, 'Helvetica Neue', Arial, sans-serif"
    fontSize: "18px"
    fontWeight: 500
    lineHeight: 1
  wordmark:
    fontFamily: "Inter, 'Helvetica Neue', Arial, sans-serif"
    fontSize: "34px"
    fontWeight: 800
    lineHeight: 1
    letterSpacing: -0.035em

spacing:
  edge-x: "64px"
  edge-top: "56px"
  edge-bottom: "48px"
  title-to-sub: "12px"
  header-to-body: "88px"
  gap-lg: "48px"
  gap-md: "24px"
  gap-sm: "16px"
  tile-gap: "18px"

canvas:
  width: 1920px
  height: 1080px

components:
  accent-word:
    font: "{typography.headline}"
    fontStyle: italic
    color: "{colors.orange}"
    description: "Exactly one word or short phrase of a content headline, in DM Serif Display italic orange. 'The stack in *practice*'."
  title-page:
    background: "{colors.sky} or {colors.orange}"
    line-1: "{typography.display-title} roman, {colors.ink}"
    line-2: "{typography.display-title} italic, {colors.paper}"
    meta: "{typography.title-meta}, {colors.ink}; date line in Inter 700 italic"
  tile:
    radius: "16px"
    padding: "28px 32px"
    minHeight: "128px"
    fills: ["{colors.sky}", "{colors.orange}", "{colors.sun}"]
    text: "{typography.tile-label} centered, {colors.ink}; optional {typography.tile-sub} second line"
  ghost-card:
    radius: "16px"
    border: "2px solid {colors.line}"
    background: "{colors.paper}"
    text: "{typography.tile-label} centered, {colors.stone}"
    description: "The 'today' / 'before' / out-of-scope state. Never filled."
  flow-arrow:
    color: "{colors.line}"
    size: "28px wide, 36px tall"
    description: "Short, thick, pale-grey down or right arrow between tiles. Inline SVG."
  status-pill:
    background: "{colors.mint}"
    radius: "999px"
    padding: "14px 28px"
    text: "{typography.column-heading} at 30px, {colors.ink}, preceded by an 14px {colors.stone} dot"
  verdict-mark:
    cross: "✕ in {colors.alert}, Inter 700, same size as the heading it prefixes"
    check: "✔ in {colors.mint}, Inter 700, same size as the heading it prefixes"
  footer:
    position: "bottom-right, {spacing.edge-bottom} from bottom, {spacing.edge-x} from right"
    content: "page number in {typography.chrome} {colors.ink}, ' - ', then the Alma wordmark in {colors.orange}"
  footnote:
    font: "{typography.caption}"
    color: "{colors.ink}"
    prefix: "* "
  confidential-tag:
    font: "{typography.chrome} at 20px weight 400"
    position: "bottom-left on title pages"
  table-rule:
    border: "1px solid {colors.line}"
    header: "Inter 700 24px {colors.ink}, 2px solid {colors.ink} bottom border"
---

## Frontend Slides Fixed-Stage Policy

This design system is native to the `slides` skill's **fixed 1920×1080 stage**. Every size in this file is a stage pixel, not a viewport unit. Render each slide at 1920×1080 and scale the whole stage with one transform, using the inline stage scaler from `html-template.md`. Never add responsive breakpoints. Verify rendered screenshots for both text overflow and panel overlap.

## Overview

Alma is a **clean consulting system with two personalities**: quiet white content slides that explain, and loud full-bleed colour pages that announce. It keeps the bones of Cobalt Grid (flat surfaces, one serif display face over one sans text face, structure carried by alignment and rules rather than shadows) and replaces its risograph identity with Alma's brand palette.

The typeface stack is a **two-face conversation**. **DM Serif Display** carries every title, headline, section name, statement, and KPI numeral. It exists at weight 400 only, in roman and italic. **Inter** carries everything else: subtitles, column headings, tile labels, row labels, body, captions, chrome. Inter is a brand requirement here, so the skill's general "avoid Inter" guidance does not apply to this template.

The signature move is the **italic accent**. Every content headline sets exactly one word or short phrase in DM Serif Display italic, coloured `{colors.orange}`: "The stack in *practice*". On colour pages the same idea becomes a two-line title: a roman ink line, then an italic white line ("90-day / *TPV forecast*", "Q3'26 review / *& deepdive*").

Colour is **functional, not decorative**. On content slides the palette maps to meaning:
- `{colors.sky}` tiles = what people use, entry points, options.
- `{colors.orange}` tiles = the central or decisive layer, the recommendation, the thing to remember.
- `{colors.sun}` tiles = foundations, infrastructure, supporting layers.
- `{colors.mint}` = status that is positive or in progress (pills, check marks).
- Ghost cards with `{colors.line}` borders and `{colors.stone}` text = the current state, the old way, or what is out of scope.

**Density philosophy: clear first, then dense.** A content slide has one headline, one subtitle that states the takeaway as a full sentence, and one diagram, table, or set of columns. The subtitle carries the message; the body proves it. Consulting rule: a reader who reads only the headline and subtitle of every slide must get the whole story.

**Key Characteristics:**
- White canvas `{colors.paper}` for content; full-bleed `{colors.sky}` or `{colors.orange}` for title, section, and closing pages.
- DM Serif Display 400 for all display text; Inter 400–800 for all other text.
- Exactly one orange italic accent word per content headline.
- Bold Inter subtitle directly under the headline, written as the slide's takeaway sentence.
- Rounded 16px tiles in sky / orange / sun with bold centred Inter labels; ghost cards for the "before" state.
- Pale grey flow arrows between tiles.
- Footer bottom-right: page number, dash, orange Alma wordmark.
- No shadows, no gradients, no textures, no background patterns.

## Colors

### Brand Palette
- **Paper** (`{colors.paper}` — #FFFFFF): The content canvas. Pure white.
- **Ink** (`{colors.ink}` — #120A07): A warm near-black. Every headline, subtitle, label, and body line on white and on colour pages.
- **Orange** (`{colors.orange}` — #E75D36): Alma's brand colour. Accent words, the wordmark, decisive tiles, full-bleed title and closing pages.
- **Sky** (`{colors.sky}` — #7AD6E5): Full-bleed title and section pages; entry-layer tiles.
- **Sun** (`{colors.sun}` — #F8D648): Foundation-layer tiles and highlight cells. Never a full-page background.
- **Mint** (`{colors.mint}` — #5DC38D): Status pills and check marks only.
- **Stone** (`{colors.stone}` — #69625D): Text inside ghost cards, secondary labels, muted captions.
- **Line** (`{colors.line}` — #D4D4D4): Ghost-card borders, table rules, flow arrows, dividers.
- **Mist** (`{colors.mist}` — #F4F4F4): Optional zebra fill for dense tables. Use sparingly.
- **Alert** (`{colors.alert}` — #EA3424): The ✕ verdict mark and genuinely negative values. Never a fill.

### Defaults
- **Default content surface**: `{colors.paper}`.
- **Default headline colour**: `{colors.ink}`, with the accent word in `{colors.orange}` italic.
- **Default body colour**: `{colors.ink}`. Use `{colors.stone}` only for ghost cards and secondary captions.
- **Default tile text colour**: `{colors.ink}` on every fill, including orange.
- **Default title-page surface**: `{colors.sky}` for topic or working-session decks, `{colors.orange}` for reviews, milestones, and executive decks. Alternate the two for section pages.

### Contrast Rules
- White text on sky (~1.6:1) and on orange (~3.3:1) is legible only at display size. Use white **only** for the italic second line of a title, at 100px or more.
- All Inter text on sky, orange, and sun pages is `{colors.ink}`.
- Never put `{colors.stone}` text on a coloured fill.

## Typography

### Font Family
`DM Serif Display` (Google Fonts, 400 roman + 400 italic) and `Inter` (Google Fonts, 400 / 500 / 600 / 700 / 800, plus 700 italic). There is no third face. DM Serif Display has no bold: hierarchy comes from size, never weight.

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=Inter:ital,wght@0,400;0,500;0,600;0,700;0,800;1,700&display=swap" rel="stylesheet">
```

```css
:root {
  --font-display: 'DM Serif Display', Georgia, serif;
  --font-body: Inter, 'Helvetica Neue', Arial, sans-serif;
}
```

### Type Scale

| Token | Size | Family | Weight | Use |
|---|---|---|---|---|
| `{typography.kpi-numeral}` | 150px | DM Serif Display | 400 | Headline figure on a KPI slide |
| `{typography.display-title}` | 132px | DM Serif Display | 400 | Two-line title on title and closing pages |
| `{typography.display-section}` | 112px | DM Serif Display | 400 | Section page title |
| `{typography.headline}` | 92px | DM Serif Display | 400 | Content slide headline |
| `{typography.statement}` | 76px | DM Serif Display | 400 | Statement or quote slide |
| `{typography.subtitle}` | 40px | Inter | 600 | Takeaway sentence under every content headline |
| `{typography.title-meta}` | 40px | Inter | 700 | Team, date, or duration under a title |
| `{typography.column-heading}` | 36px | Inter | 600 | "Today: …" / "Target: …" column heads |
| `{typography.tile-label}` | 32px | Inter | 700 | Text inside tiles and ghost cards |
| `{typography.row-label}` | 30px | Inter | 700 | Left-hand row names ("Harness", "Control") |
| `{typography.body}` | 28px | Inter | 400 | Paragraphs and bullets |
| `{typography.body-small}` | 24px | Inter | 400 | Row descriptions, tile sub-lines, table cells |
| `{typography.caption}` | 22px | Inter | 400 | Footnotes and source lines |
| `{typography.chrome}` | 18px | Inter | 500 | Page number, confidential tag |

### Signature Treatments
- **One accent per headline.** Exactly one word or short phrase in DM Serif Display italic `{colors.orange}`. Pick the word that carries the meaning ("practice", "risk", "next"), never a filler word.
- **Two-line titles on colour pages.** Line 1 roman `{colors.ink}`, line 2 italic `{colors.paper}`. Left-aligned, sharing one left edge with the meta lines beneath.
- **Subtitle as a sentence.** The Inter 600 subtitle sits 12px under the headline and states the slide's conclusion. Example: "Today the vendor locks all three layers. With the target stack, we choose each one."
- **Negative tracking on serif display** (-0.01em; -0.02em on KPI numerals). Inter stays at 0 except the wordmark.
- **No uppercase.** Labels, headings, and chrome are sentence case. Uppercase reads as a different brand.
- **Body bullets** use a 10px `{colors.orange}` square marker, 20px left of the text.

## Layout

### Canvas and Margins
- Stage: 1920×1080, `{colors.paper}` unless the slide is a colour page.
- Side margins `{spacing.edge-x}` (64px); headline top at `{spacing.edge-top}` (56px).
- The body region starts `{spacing.header-to-body}` (88px) below the subtitle and ends 120px above the bottom edge, leaving room for the footer and footnote.

### Content Slide Anatomy
1. **Headline** top-left, `{typography.headline}`, with one accent word.
2. **Subtitle** directly under it, `{typography.subtitle}`.
3. **Body region**: a diagram, a two- or three-column comparison, a table, or a KPI row.
4. **Footnote** (optional) centred under the body region or aligned with it, `{typography.caption}`, prefixed `* `.
5. **Footer** bottom-right: page number in `{typography.chrome}`, " - ", Alma wordmark in orange.

### Title Page Anatomy (sky or orange)
- Title block left edge at 28% of the width (≈540px); vertically centred, slightly above centre.
- Two-line `{typography.display-title}` title, then 48px gap, then `{typography.title-meta}` lines (team or duration in Inter 700, date in Inter 700 italic).
- Wordmark: white, top-left at 40px/40px on orange pages; white, bottom-right at 48px/64px on sky pages. Use one position per deck.
- "Confidential" in `{typography.chrome}` 20px `{colors.ink}` bottom-left when the deck is internal.
- **Hero object (optional):** one large object illustration (a 3D render the user supplies, or a single large emoji at 160–220px) placed beside the title, overlapping the title block's right edge or sitting to its left. Never more than one. Never clip art or icon sets.

### Layout Catalogue
Pick from these per slide. All share the content anatomy above unless they are colour pages.

**Title** — Colour page, two-line title, meta lines, optional hero object.

**Section** — Colour page (alternate sky and orange through the deck). A small Inter 700 32px section number ("02") above a `{typography.display-section}` two-line title. No meta lines.

**Comparison: today vs target** — Two column groups. Left group: ✕ `{colors.alert}` + `{typography.column-heading}` "Today: …" over ghost cards. Right group: ✔ `{colors.mint}` + "Target: …" over coloured tiles, with an optional status pill to the right of the heading. Shared row labels down the left edge (`{typography.row-label}` + `{typography.body-small}` description in two lines), in a column at least 200px wide with 24px clear before the first card. Keep each column heading on one line. If the heading and the status pill don't both fit, move the pill above the heading, right-aligned.

**Layer stack** — Three rows of tiles (sky entry layer, one full-width orange central tile, sun foundation layer), joined by pale flow arrows. Small Inter 700 24px column headings ("Example: chat") above the top row.

**KPI row** — Three or four KPIs side by side. Each: `{typography.kpi-numeral}` in `{colors.orange}`, then a 28px Inter 700 label, then a `{typography.body-small}` `{colors.stone}` one-line context ("vs 1.4% in Q2"). Thin 1px `{colors.line}` vertical dividers between KPIs.

**Table** — Inter throughout. Header row Inter 700 24px with a 2px `{colors.ink}` bottom border; body rows 24px with 1px `{colors.line}` dividers; numbers right-aligned with tabular figures (`font-variant-numeric: tabular-nums`). Highlight the one row or cell that matters with a `{colors.sun}` fill and 8px radius.

**Columns** — Two or three text columns, each topped by a 6px-tall, 64px-wide rounded bar in sky / orange / sun, then a `{typography.column-heading}` heading and `{typography.body}` text or 2–4 bullets.

**Timeline / roadmap** — A horizontal 2px `{colors.line}` rail with 20px circular nodes (filled orange for done, white with 3px orange ring for next, white with `{colors.line}` ring for later). Inter 700 24px date above each node, `{typography.body-small}` description below.

**Statement** — White page. A `{typography.statement}` sentence, max three lines, left-aligned at 28% like a title page, with its accent phrase in orange italic. Optional attribution in Inter 600 26px `{colors.stone}`.

**Chart** — Content anatomy, with the chart filling the body region (up to 1792×640px). Inline SVG, following the "SVG Charts" rules in `html-template.md`. Axis lines and gridlines are 1px `{colors.line}`. Tick labels are Inter 22px `{colors.stone}`, and direct labels are Inter 700 24px `{colors.ink}` at the end of each series, instead of a legend. One annotation callout at most: a `{typography.body-small}` note joined to its point by a 1px `{colors.ink}` leader line.
- **Bar:** bars in `{colors.sky}`, 8px top radius, with the one bar that matters in `{colors.orange}`. Value labels above the bars in Inter 700 22px.
- **Line:** actuals as a 4px solid `{colors.ink}` line. Plan or target as a 3px dashed `{colors.orange}` line (`stroke-dasharray="12 10"`). Mark the latest actual with a 14px orange dot.
- **Range / forecast band:** the band between low and high scenarios in `{colors.sky}` at `fill-opacity="0.35"`, the central forecast as a 4px `{colors.orange}` line, and actuals as a 4px `{colors.ink}` line that stops at today. A 1px dashed `{colors.stone}` vertical rule marks today, labelled "Today" in Inter 600 20px. Label the band's two edges directly ("High", "Low") in Inter 22px `{colors.stone}`.

**Closing / next steps** — Orange colour page. Two-line title ("Next / *steps*"), then up to four numbered Inter 700 32px actions with owner and date in Inter 400. When the deck asks for a decision, budget, or support, add an **ask block** to the right of the actions: a 16px-radius `{colors.paper}` card, 640px wide, 40px padding, with an Inter 600 24px `{colors.stone}` label ("Our ask") above the ask in DM Serif Display 52px `{colors.ink}`, with its key word in italic `{colors.orange}`. Keep the actions to three when the ask block is present.

## Depth and Elevation

Flat. No drop shadows, no gradients, no blur, no glass. Depth comes from fill versus outline: filled tiles are "real" or "target", outlined ghost cards are "today" or "not chosen". A rendered 3D hero object on a title page is the only dimensional element, and it is content, not chrome.

## Shapes and Treatment

### Border Radius
| Value | Use |
|---|---|
| 16px | Tiles, ghost cards, image frames |
| 8px | Highlighted table cells, small chips |
| 999px | Status pills, timeline nodes |
| 0 | Full-bleed colour pages, table rules |

### Border Weights
- **2px solid `{colors.line}`** — ghost cards.
- **2px solid `{colors.ink}`** — table header bottom border.
- **1px solid `{colors.line}`** — table row dividers, KPI dividers, internal divisions inside a ghost-card column.

### Decorative Vocabulary
The system has almost none, on purpose. Allowed: the italic accent, the colour tiles, pale flow arrows, the status pill, ✕ / ✔ verdict marks, the hero object on colour pages. Anything else (blobs, patterns, gradients, grids, icons in every tile) breaks the consulting register.

## Motion
- Content slides: headline and subtitle fade up 16px over 500ms, then body elements stagger in at 80ms intervals.
- Tiles: fade + scale from 0.96 to 1. Flow arrows fade in after the tiles they connect.
- Colour pages: the title's italic line slides in 24px from the left, 150ms after the roman line.
- Respect `prefers-reduced-motion`: show everything at once with no transform.

## Do's and Don'ts

### Do
- Write every subtitle as the slide's conclusion in one sentence.
- Use exactly one orange italic accent per content headline.
- Map colours to meaning consistently across the deck (sky = entry, orange = decisive, sun = foundation).
- Use ghost cards to show the current state next to the coloured target state.
- Mark provisional items with `*` and explain them in one footnote.
- Keep every text element in Inter except display text, which is DM Serif Display.
- Alternate sky and orange for section pages.

### Don't
- Don't bold or uppercase DM Serif Display. It has one weight.
- Don't put white Inter text on sky, orange, or sun.
- Don't use sun or mint as a full-page background.
- Don't add shadows, gradients, or background patterns.
- Don't put more than two accent colours of tiles in one row.
- Don't use more than one hero object on a page, or any on content slides.
- Don't let a tile label wrap to more than two lines. Shorten it or widen the tile.

## Logo and Wordmark

The real Alma logo is a custom wordmark. If the user provides it (SVG or PNG), embed it as a base64 `<img>` and use it in every logo position, in `{colors.orange}` on white and in white on colour pages. Otherwise render the fallback: the word "Alma" in `{typography.wordmark}` (Inter 800, -0.035em). Tell the user the fallback is an approximation.

## Iteration Guide

1. Every content slide inherits: headline + accent word, subtitle, footer. Don't author the footer per slide; render it from one component.
2. Every new diagram uses tiles and ghost cards before anything else. Reach for a chart only for real numeric series.
3. Charts: bars in `{colors.sky}` with the highlighted bar in `{colors.orange}`; axis and gridlines in `{colors.line}`; labels in Inter 22px. No chart junk.
4. New colour pages follow the title anatomy and alternate sky / orange.
5. If a slide needs more than six tiles or eight table rows, split it into two slides.

## Known Gaps

- The real Alma wordmark is not bundled. The Inter fallback is close in weight but not identical in letterforms.
- The 3D hero objects in Alma's reference decks are rendered images. They cannot be reproduced in CSS; use a user-supplied image or a single large emoji.
- No CJK pairing is defined. For Chinese or Japanese content, fall back to Noto Serif SC for display and Noto Sans SC for text.
