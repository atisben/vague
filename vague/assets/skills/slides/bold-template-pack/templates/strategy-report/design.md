---
version: alpha
name: Strategy Report
description: "A top-tier strategy-consultancy research report, laid out as a 16:9 reading deck. Heavy bold serif headlines over a light neo-grotesque text face, white pages with two or three text columns, a large 'Contents' page, full-bleed cobalt or illustrated section openers, numbered chapter openers with a category tag, survey-highlight bullets with blue left bars, cobalt pull quotes, and 'Exhibit N' charts with note and source lines. Derived from the layout of McKinsey's 'The State of Organizations 2026' report; it borrows the grammar, never the brand."

colors:
  paper: "#FFFFFF"
  ink: "#000000"
  navy: "#051C2C"
  cobalt: "#1537BA"
  electric: "#2972FF"
  sky: "#34B4F4"
  cyan: "#0291DC"
  powder: "#99C4FF"
  teal: "#0BDACB"
  magenta: "#DB57DB"
  orchid: "#E479E4"
  dotted: "#9D9D9C"
  rule: "#E6E6E6"
  note: "#656565"

color-aliases:
  brand: cobalt
  accent: electric
  bg: paper
  text: ink
  muted: note

categories:
  description: "Up to three content families, each owning one colour across tags, TOC rules, overview bands, and left bars."
  cat-1: "{colors.electric}"
  cat-2: "{colors.teal}"
  cat-3: "{colors.magenta}"

typography:
  cover-title:
    fontFamily: "'Source Serif 4', 'Source Serif Pro', Georgia, serif"
    fontSize: "112px"
    fontWeight: 700
    lineHeight: 1.0
    letterSpacing: -0.01em
  cover-year:
    fontFamily: "'Source Serif 4', Georgia, serif"
    fontSize: "72px"
    fontWeight: 700
    lineHeight: 1.0
  contents-word:
    fontFamily: "'Source Serif 4', Georgia, serif"
    fontSize: "164px"
    fontWeight: 700
    lineHeight: 0.9
    letterSpacing: -0.02em
  statement:
    fontFamily: "'Source Serif 4', Georgia, serif"
    fontSize: "92px"
    fontWeight: 700
    lineHeight: 1.05
    letterSpacing: -0.01em
  quote-statement:
    fontFamily: "'Source Serif 4', Georgia, serif"
    fontSize: "84px"
    fontWeight: 700
    lineHeight: 1.08
  chapter-title:
    fontFamily: "'Source Serif 4', Georgia, serif"
    fontSize: "80px"
    fontWeight: 700
    lineHeight: 1.05
    letterSpacing: -0.01em
  panel-quote:
    fontFamily: "'Source Serif 4', Georgia, serif"
    fontSize: "68px"
    fontWeight: 700
    lineHeight: 1.12
  headline:
    fontFamily: "'Source Serif 4', Georgia, serif"
    fontSize: "60px"
    fontWeight: 700
    lineHeight: 1.1
  pull-quote:
    fontFamily: "'Source Serif 4', Georgia, serif"
    fontSize: "56px"
    fontWeight: 700
    lineHeight: 1.15
  kpi-numeral:
    fontFamily: "'Source Serif 4', Georgia, serif"
    fontSize: "158px"
    fontWeight: 700
    lineHeight: 0.95
    letterSpacing: -0.02em
  toc-number:
    fontFamily: "'Source Serif 4', Georgia, serif"
    fontSize: "64px"
    fontWeight: 600
    lineHeight: 1.0
  subhead:
    fontFamily: "'Source Serif 4', Georgia, serif"
    fontSize: "28px"
    fontWeight: 700
    lineHeight: 1.25
  lead:
    fontFamily: "'Public Sans', 'Helvetica Neue', Arial, sans-serif"
    fontSize: "30px"
    fontWeight: 300
    lineHeight: 1.45
  body:
    fontFamily: "'Public Sans', 'Helvetica Neue', Arial, sans-serif"
    fontSize: "23px"
    fontWeight: 300
    lineHeight: 1.55
  body-strong:
    fontFamily: "'Public Sans', 'Helvetica Neue', Arial, sans-serif"
    fontSize: "23px"
    fontWeight: 500
    lineHeight: 1.5
  exhibit-title:
    fontFamily: "'Public Sans', 'Helvetica Neue', Arial, sans-serif"
    fontSize: "28px"
    fontWeight: 500
    lineHeight: 1.3
  exhibit-label:
    fontFamily: "'Public Sans', 'Helvetica Neue', Arial, sans-serif"
    fontSize: "20px"
    fontWeight: 300
    lineHeight: 1.3
  chart-label:
    fontFamily: "'Public Sans', 'Helvetica Neue', Arial, sans-serif"
    fontSize: "19px"
    fontWeight: 300
    lineHeight: 1.3
  tag:
    fontFamily: "'Public Sans', 'Helvetica Neue', Arial, sans-serif"
    fontSize: "16px"
    fontWeight: 500
    lineHeight: 1
    letterSpacing: 0.14em
    textTransform: uppercase
  name-caption:
    fontFamily: "'Public Sans', 'Helvetica Neue', Arial, sans-serif"
    fontSize: "17px"
    fontWeight: 600
    lineHeight: 1.35
    letterSpacing: 0.04em
    textTransform: uppercase
  footnote:
    fontFamily: "'Public Sans', 'Helvetica Neue', Arial, sans-serif"
    fontSize: "15px"
    fontWeight: 300
    lineHeight: 1.4
  footer:
    fontFamily: "'Public Sans', 'Helvetica Neue', Arial, sans-serif"
    fontSize: "15px"
    fontWeight: 600
    lineHeight: 1

spacing:
  edge-x: "92px"
  edge-top: "80px"
  footer-baseline: "1042px"
  footnote-rule-y: "932px"
  column-gap: "56px"
  gap-lg: "48px"
  gap-md: "28px"
  gap-sm: "14px"
  half: "960px"

canvas:
  width: 1920px
  height: 1080px

components:
  accent-words:
    description: "One phrase of a serif headline or quote in a brighter blue. Cyan on white headlines, electric inside cobalt quotes, powder inside white-on-cobalt quotes."
    on-white-headline: "{colors.cyan}"
    in-cobalt-quote: "{colors.electric}"
    on-cobalt-panel: "{colors.powder}"
  category-tag:
    background: "category colour"
    text: "{typography.tag}, {colors.paper} on electric or magenta, {colors.ink} on teal"
    padding: "14px 28px"
    radius: "0"
    position: "flush top-left of the image half on chapter openers"
  category-band:
    background: "category colour"
    radius: "18px 18px 0 0"
    height: "40px"
    text: "{typography.tag} at 19px, centred"
    description: "Spans the columns of one category on the overview grid."
  numbered-circle:
    size: "60px"
    border: "2px solid category colour"
    text: "{typography.subhead} at 34px, {colors.ink}, centred"
    description: "Sits on a 1px {colors.rule} horizontal line that runs across the column."
  highlight-bar:
    border-left: "5px solid {colors.electric}"
    padding-left: "22px"
    text: "{typography.body}"
    description: "Survey highlights and key findings. Never a bullet glyph."
  toc-entry:
    number: "Public Sans 600 26px {colors.ink}, 52px column"
    label: "{typography.body} at 26px"
    section-head: "{typography.subhead} at 32px with a 4px category-coloured rule 14px beneath"
  drop-cap:
    font: "'Source Serif 4' 700, 3 lines tall (≈112px), {colors.ink}"
    followed-by: "a {typography.subhead} run-in ('What's changing?') then {typography.body}"
  exhibit:
    label: "'Exhibit N' in {typography.exhibit-label} at 22px"
    title: "{typography.exhibit-title}, a full sentence stating the finding"
    lead: "Public Sans 500 22px metric name, then Public Sans 300 22px unit and base ('% of respondents (n = 3,763)')"
    legend: "16px squares, Public Sans 300 19px labels, inline above the chart"
    note: "{typography.footnote} in {colors.note}: 'Note: …' then 'Source: …'"
    credit: "Organisation name in Public Sans 400 19px {colors.ink}, under the note"
  footer:
    position: "right-aligned at {spacing.edge-x}, baseline {spacing.footer-baseline}"
    content: "report title in {typography.footer} {colors.ink}, 28px gap, page number in Public Sans 300 15px"
  footnotes:
    rule: "1px solid {colors.rule} at {spacing.footnote-rule-y}"
    text: "{typography.footnote}; superscript number column 24px wide; titles of works in italic"
  dotted-divider:
    border: "1px dotted {colors.dotted}"
    description: "Separates a column's prose from its stat sentence on the overview grid."
---

## Frontend Slides Fixed-Stage Policy

This design system is native to the `slides` skill's **fixed 1920×1080 stage**. Every size in this file is a stage pixel. The source report is a 960×540 pt landscape PDF, so its point sizes were doubled, then nudged up a few pixels for screen reading. Render each slide at 1920×1080 and scale the stage with one transform, using the inline stage scaler from `html-template.md`. Never add responsive breakpoints. Verify rendered output for text overflow and panel overlap.

## Overview

Strategy Report is a **research report that happens to be a deck**. It reads like a printed consultancy publication: dense, calm, authoritative. It suits decks that are read, sent, or printed more than presented. Slides carry real paragraphs set in columns. Hierarchy comes from a heavy serif against a light sans, not from colour or boxes.

The system has **three page families**:
1. **Navigation pages**: cover, contents, section openers. They tell the reader where they are.
2. **Reading pages**: chapter openers, column text, pull quotes, interviews. They carry the argument.
3. **Evidence pages**: exhibits, KPI stacks, overview grids. They prove it.

The typeface stack is a **two-face contrast**. **Source Serif 4** at weight 700 stands in for the report's proprietary bold serif. It carries every title, headline, quote, subhead, KPI numeral, and TOC number. **Public Sans** at weight 300 stands in for the report's light grotesque. It carries body text, exhibits, tags, footnotes, and chrome. Light body weight is the point: it makes the bold serif feel heavier.

The signature moves are:
- **The giant "Contents" word** set bottom-left, with the numbered table of contents in two columns to its right.
- **Cobalt pull quotes** that span two text columns, with one phrase picked out in electric blue.
- **Category colours** (electric, teal, magenta) that thread through tags, TOC rules, overview bands, and left bars, so the reader always knows which family a page belongs to.
- **"Exhibit N" charts** with a sentence title, a metric lead, an inline legend, and a grey note and source line.

**Density philosophy: report-dense, never cramped.** A reading page holds up to three columns of 23px text. That is far denser than a talk deck, and it is intentional. Keep 56px between columns, keep the footnote zone clear, and split a page before a column passes its bottom edge.

**Key Characteristics:**
- White pages; full-bleed cobalt `{colors.cobalt}` or illustrated panels for section openers and statement pages.
- Source Serif 4 700 for all display text; Public Sans 300 for body, 500–600 for emphasis.
- Pure black body text. Navy `{colors.navy}` only on the cover title.
- Two- and three-column body layouts with real paragraphs.
- Blue left bars for highlights; numbered circles and rounded category bands on overview grids.
- Footnote rule and numbered footnotes above a right-aligned "Report title  N" footer.
- Flat surfaces. No shadows, no gradients on UI, no rounded cards except the category band.

## Colors

### Palette
- **Paper** (`{colors.paper}` — #FFFFFF): Every reading and evidence page.
- **Ink** (`{colors.ink}` — #000000): Body, headlines, TOC, footer. Pure black, as in the source.
- **Navy** (`{colors.navy}` — #051C2C): Cover title and illustration outlines only.
- **Cobalt** (`{colors.cobalt}` — #1537BA): Statement panels, section-opener backgrounds, pull quotes on white, KPI numerals, interview question text, darkest chart series.
- **Electric** (`{colors.electric}` — #2972FF): Category 1, highlight bars, primary chart series, accent phrase inside cobalt quotes.
- **Sky** (`{colors.sky}` — #34B4F4): Secondary chart series and a TOC rule colour.
- **Cyan** (`{colors.cyan}` — #0291DC): The accent phrase in black serif headlines on white ("Three tectonic forces that are *reshaping* organizations").
- **Powder** (`{colors.powder}` — #99C4FF): Accent phrase inside white-on-cobalt quotes; light chart fill.
- **Teal** (`{colors.teal}` — #0BDACB): Category 2.
- **Magenta** (`{colors.magenta}` — #DB57DB) and **Orchid** (`{colors.orchid}` — #E479E4): Category 3, and the warm notes in illustrations.
- **Dotted** (`{colors.dotted}` — #9D9D9C): Dotted dividers and column rules.
- **Rule** (`{colors.rule}` — #E6E6E6): Footnote rule, circle baselines, table rules.
- **Note** (`{colors.note}` — #656565): Exhibit notes and sources only.

### Category System
A deck may group its chapters into up to three families. Each family owns one colour for the whole deck: `cat-1` electric, `cat-2` teal, `cat-3` magenta. Use that colour for the family's category tag, its TOC rule, its overview band, its left bars on the section opener, and its numbered-circle outline. A deck with no families uses electric everywhere.

### Contrast Rules
- On cobalt, all text is white; the accent phrase is powder.
- Category tags: white text on electric and magenta, ink text on teal.
- Never set body text in a colour. Colour is for display text, rules, bars, and charts.

## Typography

### Font Family
`Source Serif 4` (Google Fonts, variable, 600–700 used, with optical sizing) and `Public Sans` (Google Fonts, 300 / 400 / 500 / 600, plus 300 italic). There is no third face.

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,600;8..60,700&family=Public+Sans:ital,wght@0,300;0,400;0,500;0,600;1,300&display=swap" rel="stylesheet">
```

```css
:root {
  --font-display: 'Source Serif 4', 'Source Serif Pro', Georgia, serif;
  --font-body: 'Public Sans', 'Helvetica Neue', Arial, sans-serif;
}
.display { font-family: var(--font-display); font-weight: 700; font-optical-sizing: auto; }
```

### Type Scale

| Token | Size | Family | Weight | Use |
|---|---|---|---|---|
| `{typography.contents-word}` | 164px | Serif | 700 | The word "Contents" |
| `{typography.kpi-numeral}` | 158px | Serif | 700 | Stacked KPI figures, cobalt |
| `{typography.cover-title}` | 112px | Serif | 700 | Cover title, navy |
| `{typography.statement}` | 92px | Serif | 700 | Introduction statement headline |
| `{typography.quote-statement}` | 84px | Serif | 700 | Full-page quote, cobalt |
| `{typography.chapter-title}` | 80px | Serif | 700 | Chapter opener and section opener titles |
| `{typography.cover-year}` | 72px | Serif | 700 | Year or edition on the cover, right-aligned |
| `{typography.panel-quote}` | 68px | Serif | 700 | White quote on a cobalt half-panel |
| `{typography.toc-number}` | 64px | Serif | 600 | Page numbers on the section-opener TOC |
| `{typography.headline}` | 60px | Serif | 700 | One-line headline on overview and exhibit pages |
| `{typography.pull-quote}` | 56px | Serif | 700 | Cobalt pull quote across two columns |
| `{typography.lead}` | 30px | Sans | 300 | Standfirst under a chapter title |
| `{typography.subhead}` | 28px | Serif | 700 | "Issues to address", column titles, "Survey highlights" |
| `{typography.exhibit-title}` | 28px | Sans | 500 | Exhibit finding sentence |
| `{typography.body}` | 23px | Sans | 300 | Column text |
| `{typography.body-strong}` | 23px | Sans | 500 | Run-in sans subheads, stat sentences, Q&A questions |
| `{typography.exhibit-label}` | 20px | Sans | 300 | "Exhibit 1", chart category labels |
| `{typography.chart-label}` | 19px | Sans | 300 | Legend, values |
| `{typography.name-caption}` | 17px | Sans | 600 | Interviewee name and role, uppercase |
| `{typography.tag}` | 16px | Sans | 500 | Category tag, uppercase, tracked |
| `{typography.footnote}` | 15px | Sans | 300 | Footnotes, notes, sources |
| `{typography.footer}` | 15px | Sans | 600 | Footer report title |

### Signature Treatments
- **Heavy serif, light sans.** Never set body text heavier than 300 except for run-in heads and stat sentences (500).
- **One accent phrase** per headline or quote, in the accent colour for its surface. Pick the phrase that carries the claim ("drive productivity", "long-term impact"), never a filler word.
- **Sentence case everywhere** except category tags and interviewee captions, which are uppercase and tracked.
- **Two subhead registers.** A serif subhead ("Issues to address") opens a new part of the argument. A sans 500 run-in subhead ("Build a strategy that recalibrates the business…") opens a numbered step or recommendation, and the paragraph follows on the next line with no gap.
- **Drop cap** only on the first paragraph of a chapter's "What's changing?" section.
- **Footnote superscripts** in body text at 0.6em, raised, with numbered footnotes above the footer.
- **Tabular figures** in exhibits and KPI numerals (`font-variant-numeric: tabular-nums lining-nums`).

## Layout

### Canvas and Grid
- Stage 1920×1080. Side margins `{spacing.edge-x}` (92px). Content top `{spacing.edge-top}` (80px).
- **Half-split**: many pages split at x = 960. The left half is an image, a cobalt panel, or a quote; the right half starts at 1000px and holds text.
- **Column grid** for reading pages: three columns, 56px gutters, between 92px and 1828px (≈541px each). Two-column variants use the right two-thirds or the full width.
- **Footnote zone**: a 1px `{colors.rule}` line at y = 932, footnotes below it, then the footer at baseline 1042. Text columns end above y = 900.

### Page Chrome
- **Footer** on every page except the cover and full-bleed openers: report title in Public Sans 600 15px, then the page number in 300, right-aligned at 92px from the right edge.
- **Organisation credit** under each exhibit note, not in the footer.
- **No logo on content pages.** The organisation name appears on the cover and under exhibits only.

### Layout Catalogue

**1. Cover** — Left half (0–1100px): an illustration panel bleeding off three edges (see Illustration below) or a user photo. Right half on paper: the organisation name top-left of the half at y = 80, in Source Serif 4 600 40px, two lines, `{colors.navy}`. The `{typography.cover-title}` title in `{colors.navy}`, two or three lines, vertically centred, left edge at 1160px. The year or edition below in `{typography.cover-year}`, right-aligned to the title's right edge. Nothing else.

**2. Contents** — White. "Contents" in `{typography.contents-word}` anchored bottom-left (left 92px, baseline 1000px). The table of contents in two columns starting at x = 1000 and x = 1440, top at y = 140. A top-level section is a serif `{typography.subhead}` at 32px with its page number in Public Sans 600 26px to its left, then a 4px rule in that section's category colour, 14px below. Child entries are Public Sans 300 26px with a 600 page number, listed under their parent with 20px between entries. Up to 18 entries; beyond that, split into "Contents (continued)".

**3. Section opener, illustrated** — Full-bleed illustration or photo. The section title in `{typography.chapter-title}` `{colors.paper}`, bottom-left (left 92px, baseline 960px). Nothing else; no footer.

**4. Section opener with contents** — Full-bleed `{colors.cobalt}`. An illustration fragment bleeds in from the top-right edge, cut by one large sweeping curve. The section title in `{typography.chapter-title}` white at y ≈ 580. Under it, up to three groups side by side, each with a 5px left bar in its category colour. Each row: a `{typography.toc-number}` page number in white, then the chapter name in Public Sans 600 26px white, two lines max.

**5. Introduction statement** — Left two-thirds: a `{typography.statement}` headline, four lines max, black with one cyan accent phrase. Under it, starting at y ≈ 560, two columns of body text, the first opening with a serif drop cap. Right third: a third column of body text running the full height.

**6. Overview grid** ("The nine shifts…") — A `{typography.headline}` across the top, one accent word in cyan. Below it, rounded category bands span the columns of each family. Up to five columns per slide, each with: a numbered circle on a rule, a serif column title (28px, two lines), body text (21px, 9 lines max), a dotted divider, a body-strong stat sentence, then a serif stat ("86%", "1 of 4", 34px) above a small geometric figure that shows the stat (dot ring, square grid, overlapping circles; see Data Figures). Thin 1px `{colors.dotted}` vertical rules between columns. Split more than five items across consecutive slides that repeat the headline.

**7. Chapter opener** — Left half: a full-height image or illustration, with the category tag flush at its top-left corner. Right half: `{typography.chapter-title}` (two or three lines), 40px gap, a `{typography.lead}` standfirst (8 lines max), 48px gap, "Survey highlights" (or "Key findings") as a serif subhead, then two columns of highlight-bar items (two or three items per column). Footnote zone and footer on the right half only.

**8. Reading page with pull quote** — Three columns. The first column opens with the drop-cap "What's changing?" run-in. The right two-thirds carry a cobalt `{typography.pull-quote}` at the top (6–7 lines, one electric accent phrase), then two text columns beneath it. Serif subheads ("The benefits of getting it right") break the columns.

**9. Exhibit page** — Left half: two text columns. Right half from x = 1000: "Exhibit N", the exhibit title, 32px gap, the metric lead, the inline legend, then the chart, then note, source, and organisation credit. See Exhibits.

**10. Cobalt statement panel** — Left half full-bleed `{colors.cobalt}` with a `{typography.panel-quote}` in white, left 92px, vertically centred, 10 lines max, one powder accent phrase. Right half: two text columns with sans 500 run-in subheads.

**11. KPI stack** — Two text columns on the left two-thirds. In the right third, three or four stacked KPIs: a `{typography.kpi-numeral}` in cobalt, then a 3-line body caption at 19px directly beneath, 36px between KPIs.

**12. Full-page quote** — Left third: a narrow column of body text or a highlight list. Right two-thirds: a `{typography.quote-statement}` in cobalt with one electric accent phrase, wrapped in curly single quotes, then the speaker in `{typography.name-caption}` 40px below.

**13. Interview** — First column: a 300px circular portrait (user-supplied photo), the speaker's name and role in `{typography.name-caption}`, then a cobalt `{typography.panel-quote}` at 40px with one electric phrase. Remaining columns: Q&A, with questions in `{typography.body-strong}` `{colors.cobalt}` and answers in body.

**14. Closing / about** — White. "About this research" or "Authors" as a `{typography.chapter-title}`, then body columns. For authors: a grid of 160px circular portraits with Public Sans 600 22px names and 300 19px roles.

## Exhibits

Exhibits are the evidence pages, and they follow the source's grammar exactly.

1. **Label**: "Exhibit 1" in Public Sans 300 22px. Number exhibits through the whole deck.
2. **Title**: the finding as one sentence in `{typography.exhibit-title}`, two lines max. "Survey respondents cited concerns about AI as the top barrier to adoption."
3. **Lead**: the metric in Public Sans 500 22px, then a comma and the unit and base in 300. "Top barriers to adopting AI at scale, % of respondents (n = 3,763)".
4. **Legend**: inline above the chart. 16px squares, labels in `{typography.chart-label}`.
5. **Chart**: inline SVG, following the "SVG Charts" rules in `html-template.md`.
6. **Note and source**: `{typography.footnote}` in `{colors.note}`. "Note: …" on its own line, then "Source: …".
7. **Credit**: the organisation name in Public Sans 400 19px, ink, 24px under the source.

### Chart Styles
- **Horizontal bars** (the default): category labels left in `{typography.exhibit-label}`, 260px column. Bars 22px tall, square ends, values right of the bar end in `{typography.chart-label}`. Series order and colours: electric, sky, cobalt. Group gap 28px. No axis line, no gridlines.
- **Single-series bars**: electric, with the bar that matters in cobalt.
- **Stacked 100% bars**: segments in powder, electric, cobalt (light to dark = low to high), values centred in white inside dark segments and ink inside powder.
- **Dot plot / lollipop**: 1px `{colors.dotted}` rails, 14px electric dots, an "Other" series as cobalt dots.
- **Proportional circles**: one row of circles sized by value, electric, with the highlighted one in cobalt; the value centred in white Public Sans 500 22px; the label below in 19px.
- **Waffle**: a 10×10 grid of 14px squares, filled squares in electric, empty in `{colors.rule}`; one waffle per segment, value right of the grid.

### Data Figures (overview grid)
Small, decorative, but true to the number. Each sits in a 140px square under a serif stat:
- Percent: a ring of 7px dots, the share in electric, the rest in powder (86% → 86 of 100 dots).
- "1 of N": N squares rotated 45°, one in electric, the rest in cobalt.
- Part of a whole: a 10×10 square grid, share in cobalt, rest in powder.
- Overlap: two circles, cobalt behind, teal in front, sized by value.

## Illustration

The source report uses commissioned flat illustrations: bold navy outlines, flat electric, cobalt, sky, teal, and magenta fills, halftone dot textures, concentric rings, eyes, globes, and grids. Photos (servers, glass, light trails) alternate with them.

In HTML, use one of these, in this order:
1. A user-supplied image or photo, `object-fit: cover`, filling its panel.
2. A generated **inline SVG panel** in the same vocabulary: concentric rings and circles with 3px `{colors.navy}` strokes, flat fills from the palette, one halftone area made from a `<pattern>` of 3px white dots on electric at 10px spacing, a few small white circles with navy outlines as "nodes", and one large sweeping curve that crops the composition. Use 5–9 shapes. No people, no faces, no text inside the illustration.
3. A plain `{colors.cobalt}` panel, when the deck should stay sober.

Never use stock clip art, emoji, or icon sets. Illustrations live on cover, section openers, and chapter-opener image halves only.

## Depth and Elevation

Flat. No shadows, no blur, no glass, no card borders. Separation comes from whitespace, 1px rules, dotted dividers, and the half-split.

## Shapes and Treatment

| Shape | Use |
|---|---|
| 0 radius | Panels, tags, bars, images |
| 18px top radius | Category bands on the overview grid only |
| Circle | Numbered markers, portraits, data figures |
| 5px left bar | Highlights, section-opener TOC groups |
| 4px underline | Contents section rules |

## Motion
- Reading pages: the headline or quote fades in over 500ms, then columns fade up 12px, staggered 90ms left to right.
- Exhibits: bars grow from zero width over 700ms, staggered 40ms per bar; values fade in after.
- KPI numerals count up from 0 over 900ms.
- Section openers: the illustration fades in, then the title rises 20px.
- Respect `prefers-reduced-motion`: show the final state, no transforms, no counting.

## Do's and Don'ts

### Do
- Write exhibit titles and headlines as findings, not topics.
- Keep a consistent category colour per family across the whole deck.
- Put a source line under every exhibit and every survey number.
- Number footnotes in body text and resolve them above the footer on the same page.
- Use the half-split for openers and quote panels; use three columns for reading pages.
- Number the TOC with real slide numbers from the generated deck.

### Don't
- Don't reproduce the McKinsey name, logo, or report title. Use the user's organisation and report name.
- Don't bold the body text or set it in colour.
- Don't use more than one accent phrase per headline or quote.
- Don't let a text column pass y = 900 or overlap the footnote zone. Split the page.
- Don't put more than seven bar groups in one exhibit, or more than five columns on an overview slide.
- Don't use rounded cards, drop shadows, or gradients in content areas.

## Iteration Guide

1. Build the deck skeleton first: cover, contents, section openers, chapter openers. Fill the contents page last, with real slide numbers.
2. Every chapter follows the same sequence: chapter opener → reading page with pull quote → exhibit page(s) → cobalt statement panel or quote → recommendations page with sans run-in heads.
3. Render the footer and footnote zone from one component; pass footnotes per slide.
4. When a talk deck needs fewer words, keep the grammar but cut to two columns and the `{typography.lead}` size for body.
5. If a column overflows, move text to the next page. Never shrink body text below 21px.

## Known Gaps

- The source's proprietary serif and sans are replaced by Source Serif 4 and Public Sans. Source Serif 4 is a touch narrower and less dark than the original serif at large sizes.
- Commissioned illustrations cannot be reproduced; the inline SVG panel is a stylistic approximation.
- No CJK pairing is defined. For Chinese or Japanese content, fall back to Noto Serif SC 700 for display and Noto Sans SC 300 for text.
