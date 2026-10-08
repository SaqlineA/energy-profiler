---
name: Current — Energy Profiler
description: A household energy lab with Apple-product-page calm, where the evidence — including its failures — is the product.
colors:
  current-green: "#0b7a4b"
  current-green-deep: "#06552f"
  current-green-bright: "#13a86a"
  current-green-night: "#30d158"
  signal-teal: "#0a8f8a"
  mint-wash: "#e3f4ea"
  synthetic-violet: "#6e3fa3"
  ink: "#1d1d1f"
  quiet-ink: "#6e6e73"
  paper: "#f5f5f7"
  surface: "#ffffff"
  hairline: "#e5e5ea"
  control-fill: "#e8e8ed"
  night-canvas: "#000000"
  night-surface: "#1c1c1e"
  night-fill: "#2c2c2e"
  night-hairline: "#38383a"
  night-quiet-ink: "#a1a1a6"
  measured-olive: "#426635"
  estimate-rust: "#995127"
  over-amber: "#b0561f"
  under-slate: "#2f5f8a"
typography:
  display:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Helvetica Neue', 'Segoe UI', system-ui, sans-serif"
    fontSize: "clamp(2.6rem, 6vw, 5rem)"
    fontWeight: 700
    lineHeight: 1.02
    letterSpacing: "-0.045em"
  headline:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', system-ui, sans-serif"
    fontSize: "clamp(1.4rem, 2.2vw, 1.9rem)"
    fontWeight: 700
    letterSpacing: "-0.03em"
  metric:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', system-ui, sans-serif"
    fontSize: "clamp(2.2rem, 3.4vw, 3rem)"
    fontWeight: 700
    letterSpacing: "-0.05em"
  title:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', system-ui, sans-serif"
    fontSize: "1.0625rem"
    fontWeight: 650
    letterSpacing: "-0.015em"
  lead:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', system-ui, sans-serif"
    fontSize: "clamp(1.05rem, 1.6vw, 1.3rem)"
    fontWeight: 400
    lineHeight: 1.45
  body:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', system-ui, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 400
    lineHeight: 1.6
    letterSpacing: "-0.011em"
  label:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', system-ui, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 600
    letterSpacing: "0.02em"
rounded:
  pill: "980px"
  hero: "36px"
  card: "28px"
  card-compact: "22px"
  tile: "20px"
  chart: "18px"
  control: "12px"
spacing:
  gutter: "16px"
  card-inset: "24px"
  section: "28px"
  page-inline: "clamp(16px, 3vw, 40px)"
  hero-inset: "clamp(28px, 5vw, 64px)"
components:
  button-primary:
    backgroundColor: "{colors.current-green}"
    textColor: "{colors.surface}"
    rounded: "{rounded.pill}"
    padding: "12px 24px"
    height: "48px"
  button-primary-hover:
    backgroundColor: "{colors.current-green-deep}"
  button-secondary:
    backgroundColor: "{colors.control-fill}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "11px 22px"
    height: "44px"
  card:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.card}"
    padding: "{spacing.card-inset}"
  stat-live:
    backgroundColor: "{colors.current-green}"
    textColor: "{colors.surface}"
    rounded: "{rounded.card}"
    padding: "24px 26px"
  segmented-control:
    backgroundColor: "{colors.control-fill}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "3px"
  input-select:
    backgroundColor: "{colors.control-fill}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
  badge-real:
    backgroundColor: "{colors.current-green}"
    textColor: "{colors.surface}"
    rounded: "{rounded.pill}"
    padding: "5px 12px"
  badge-synthetic:
    backgroundColor: "{colors.synthetic-violet}"
    textColor: "{colors.surface}"
    rounded: "{rounded.pill}"
    padding: "5px 12px"
  appliance-tile:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.card}"
    padding: "22px"
---

# Design System: Current — Energy Profiler

## Overview

**Creative North Star: "The Honest Showroom"**

Current borrows the calm of an Apple product page: generous air, one enormous
headline, product shots floating on soft grey, and controls that feel like
pebbles under the thumb. The showroom polish is a means, not the message. What
is on display is evidence: a live home's power, and a candid record of what the
appliance-detection models got right and wrong. The polish earns attention, and
the honesty keeps it.

The mood is **calm, precise and candid**. Surfaces are quiet: grey paper,
borderless white cards and a single green voice. Precision lives in the numbers,
set large, bold and tightly tracked. Candour lives in labelling: real versus
synthetic is always a coloured badge, and every chart sits on its own white
surface with plain-language text beside it. Density is moderate. The dashboard
shows a lot, but every section breathes, and nothing is decoration.

It must never read as a **generic admin template**: no bordered grey boxes, no
cramped utility sidebar full of tiny links, and no stock SaaS card grid. If a
screen could be dropped into any Bootstrap dashboard unchanged, it has drifted.

**Key Characteristics:**
- A grey paper canvas with borderless white cards, softly lifted.
- One display headline per page, very large and very tight.
- Big bold metrics, with small calm labels above them.
- Current Green is the only accent; violet appears only to mean "synthetic".
- Fully rounded pill controls with grey fills instead of outlines.
- Product-shot illustrations on transparent backgrounds, floating on soft plates.
- Evidence charts on white, never animated.
- Light and true-black dark themes are equal citizens.

## Colors

A near-monochrome Apple neutral scale carrying one green voice, plus a fixed,
separate set of chart colours for the data itself.

### Primary
- **Current Green** (#0b7a4b): primary buttons, the live-power tile, the
  REAL DATA badge, eyebrows and the brand mark. It is the colour of "live" and
  "real".
- **Current Green Deep** (#06552f): hover and pressed state for the primary
  button, and the darker end of the live-power gradient.
- **Current Green Bright** (#13a86a): the lighter start of the live-power tile
  and brand-mark gradients. It is only used inside gradients.
- **Current Green Night** (#30d158): Current Green's dark-theme counterpart,
  for text and accents on #1c1c1e surfaces.
- **Signal Teal** (#0a8f8a): only the final stop of the hero headline gradient
  ("in watts."). It is never used as a flat fill.
- **Mint Wash** (#e3f4ea): tinted chips, pills and the icon plates on appliance
  tiles.

### Secondary
- **Synthetic Violet** (#6e3fa3): it means only "synthetic data", on the
  TRAINED ON / TESTED ON badges. It is lifted to #7d52a3 in dark mode.

### Neutral
- **Ink** (#1d1d1f): headlines, metrics and primary text.
- **Quiet Ink** (#6e6e73): secondary text, captions, stat labels and chart notes.
- **Paper** (#f5f5f7): the page canvas and the inner plates (summary panels,
  image plates, table headers).
- **Surface** (#ffffff): every card, and the chart background in both themes.
- **Hairline** (#e5e5ea): table rules and the inset outline around charts.
  It is never a card border.
- **Control Fill** (#e8e8ed): secondary buttons, segmented-control tracks,
  selects and inputs.
- **Night set:** canvas (#000000), surface (#1c1c1e), fill (#2c2c2e),
  hairline (#38383a) and quiet ink (#a1a1a6). In dark mode, ink becomes #f5f5f7.

### Chart colours (evidence only)
- **Measured Olive** (#426635): the solid "actual" line and the actual ON bars.
- **Estimate Rust** (#995127): the dashed model-estimate line and the predicted
  ON bars.
- **Over Amber** (#b0561f) and **Under Slate** (#2f5f8a): overestimates and
  underestimates in the prediction-error chart.

### Named Rules
**The Provenance Rule.** Green means real or live; violet means synthetic. A
badge colour is a factual claim about where data came from. Never use either as
decoration, and never swap them.

**The One Green Voice Rule.** Current Green is the only UI accent. It marks the
single primary action on a screen, the live-power tile, real-data badges and the
brand. If two green buttons compete in one view, one of them should be
secondary grey.

**The Evidence Palette Rule.** Chart colours are reserved for data and never
leak into UI chrome. UI colours never enter charts.

## Typography

**Display Font:** the system San Francisco stack (-apple-system, "SF Pro
Display", with "Helvetica Neue", "Segoe UI", system-ui, sans-serif).
**Body Font:** the same stack, resolving to SF Pro Text / Segoe UI.

**Character:** a single native sans in weights 400–700, doing all the work
through size and tracking. Headlines and metrics are heavy and pulled tight;
running text stays light and slightly tightened (−0.011em) for the Apple feel.
No web fonts are downloaded.

### Hierarchy
- **Display** (700, clamp(2.6rem, 6vw, 5rem), 1.02, −0.045em): the hero headline
  only. There is one per page, and its key phrase uses the green gradient.
- **Headline** (700, clamp(1.4rem, 2.2vw, 1.9rem), −0.03em): section and panel
  titles ("The power picture", "Meet your appliances").
- **Metric** (700, clamp(2.2rem, 3.4vw, 3rem), −0.05em): live numbers in stat
  tiles, and the washer's state word.
- **Title** (650, 1.0625rem, −0.015em): chart titles inside the experiment
  workbench.
- **Lead** (400, clamp(1.05rem, 1.6vw, 1.3rem), 1.45): the hero sentence, in
  Quiet Ink, capped at about 30rem.
- **Body** (400, 0.8125rem, 1.6): explanations, research notes and summaries.
  Keep lines readable and let them wrap.
- **Label** (600, 0.8125rem, +0.02em): eyebrows and stat labels, in sentence
  case. The hero eyebrow is Current Green.

### Named Rules
**The One Loud Headline Rule.** Only the display headline is enormous. Section
headlines stay at Headline size, so the hero keeps its authority.

**The Big Number Rule.** Numbers the viewer came for are set in Metric weight
with tight tracking. Their units sit smaller beside them.

### Showcase site (docs/)
The public pages (`docs/index.html`, `docs/paper.html`, styled by
`docs/site.css`) tell a story, so they are scaled up from the dashboard:
- **Showcase Display** (700, clamp(3rem, 7.2vw, 5.75rem), 0.98, −0.04em): the
  landing hero only, with "in watts." in solid Current Green.
- **Story Headline** (700, clamp(2.1rem, 4.6vw, 3.6rem), 1.04, −0.035em): each
  landing section. This is the one deliberate exception to the One Loud
  Headline Rule: an Apple-style product page gives every chapter a headline.
- **Paper Title** (700, clamp(2.2rem, 4.8vw, 3.9rem)) and **Paper Section**
  (700, 1.6rem) on the paper page.
- **Score** (700, 1.9rem, −0.04em, tabular figures): the F1 numbers.
- **Text steps:** 1.25rem (verdict and closing lead), 1.0625rem (row titles,
  facts, quotes), 0.8125rem (captions, nav, footer, tables), 0.75rem (tags,
  badges, pipeline notes). Do not add sizes in between.

## Layout

A fixed 242 px translucent sidebar sits on the left, with the content column
beside it (maximum width 1,320 px, inline padding clamp(16px, 3vw, 40px)). The
page opens with a full-width hero card: text in the left half, the transparent
house illustration fitted into the right half. Below it come:
- a pill section switcher;
- a collapsible data-source panel;
- a four-up stat row (16 px gaps);
- a main grid with the chart and the simulation lab;
- appliance tiles;
- full-width research, sessions and model panels.

The spacing rhythm is 16 px between tiles, about 22–28 px between major blocks,
and 22–26 px inside cards.

Responsive behaviour:
- **At 900 px and below,** the hero stacks: the image moves below the text into
  a 220 px band.
- **At 700 px and below,** card corners tighten from 28 to 22 px.
- **Earlier breakpoints from the base layer** (1180, 950, 720, 600, 400 px)
  collapse the sidebar, grids and stat row.
- **Dense charts** keep a 560 px minimum width and scroll sideways inside their
  own region. The page never scrolls horizontally.

## Elevation & Depth

**Softly lifted.** Depth comes from two things. First, tonal separation: white
cards on grey paper. Second, a broad, low-contrast ambient shadow that suggests
the card floats a few millimetres above the page. Depth is atmosphere, not
structure: nothing relies on a shadow to be understood.

### Shadow Vocabulary
- **Ambient** (`box-shadow: 0 1px 2px rgba(0,0,0,.04), 0 12px 32px rgba(0,0,0,.06)`):
  every card at rest.
- **Lift** (`box-shadow: 0 2px 4px rgba(0,0,0,.05), 0 20px 44px rgba(0,0,0,.09)`):
  stat and appliance tiles on hover, with a 2 px rise. Only on hover-capable
  pointers, and only when motion is allowed.
- **Live glow** (`box-shadow: 0 16px 40px rgba(11,122,75,.28)`): only the green
  live-power tile.
- **Dark theme:** the same geometry at 0.35–0.5 black opacity.

### Named Rules
**The Borderless Card Rule.** Cards never carry borders. Separation comes from
paper versus surface plus the ambient shadow. Hairlines belong inside tables
and around charts only. When transparency is reduced or contrast increased,
shadows give way to a 1 px hairline outline.

**The Glass-Is-For-Navigation Rule.** Translucent blur (the 22 px sidebar and top
bar) is only for navigation chrome. Evidence surfaces stay solid.

## Shapes

Soft, generous, consistent. Radii step down with nesting:
- the hero is the softest (36px);
- cards (28px, or 22px on phones);
- image plates and tiles (20px);
- chart surfaces (18px);
- inputs and navigation items (12px);
- anything you press (the pill radius, 980px).

There are no sharp corners and no angled or clipped silhouettes. The house
illustration and product shots bring the only irregular outlines, always on
transparent backgrounds.

## Components

### Buttons
Soft, tactile pills.
- **Shape:** fully rounded (980px).
- **Primary:** Current Green fill, white text, 600 weight at 0.9375rem, 12×24 px
  padding (48 px tall in the hero). Only one per view.
- **Hover / Focus:** hover deepens to Current Green Deep. A press scales to 0.98
  over 180 ms when motion is allowed. Focus shows a 3 px outline offset from the
  pill.
- **Secondary:** Control Fill grey with Ink text, no border, and #dcdce1 on
  hover. It is used for export, refresh, load and similar actions.

### Segmented Controls
- **Style:** a Control Fill track with 3 px inset. The selected segment is a
  white thumb with a small two-layer shadow; unselected segments are plain Ink
  text. Used for Auto / Manual and the section switcher.

### Cards / Containers
- **Corner Style:** 28 px (36 px for the hero, 22 px on phones).
- **Background:** Surface white on Paper. Nested summary plates use Paper with
  no shadow.
- **Shadow Strategy:** Ambient, with Lift on hover for tiles (see Elevation).
- **Border:** none.
- **Internal Padding:** 22–26 px, and clamp(28px, 5vw, 64px) for the hero.

### Live Power Tile (signature)
The first stat tile is the product's heartbeat: a 150° gradient from Current
Green Bright to Current Green to Current Green Deep, white text, a Metric-size
number and the Live glow shadow. No other tile is coloured.

### Appliance Tiles
Each tile shows a transparent product shot centred on a Paper plate (16:10,
20 px radius), then a Mint Wash icon chip, a switch, the name, and a live
watts Metric. The washing-machine tile puts the image on the left and its phase
details on the right, stacking on phones. It is labelled "simulated, not
ML-detected".

### Inputs / Fields
- **Style:** Control Fill background, no border, 12 px radius, Ink text.
- **Focus:** a 3 px outline.
- **Known drift:** the chart range select still renders with the base layer's
  7 px radius, 1 px border and 10 px text. The appliance switches keep the base
  layer's olive (#688954). Bring both in line with this section when next edited.

### Data Provenance Badges (signature)
Pills with 5×12 px padding, 0.6875rem type, 700 weight, +0.08em tracking and
uppercase words: TESTED ON REAL DATA / TRAINED ON SYNTHETIC DATA /
BASELINE · NO TRAINING. Real uses Current Green, synthetic uses Synthetic
Violet, and the baseline is a white pill with a hairline.

### Evidence Charts
Inline SVG on a white 18 px surface with an inset hairline. Each chart has a
text summary above it and a swatch legend below. Measured values are solid;
estimates are dashed. The power and error charts scale to the 99th percentile
and say how many readings were clipped. They are never animated.

### Navigation
The sidebar holds the wordmark, workspace chip and 13 px nav items (500 weight,
12 px radius, 13×12 px padding). Hover gives a 5% ink wash. The top bar holds
breadcrumb text and a live-status dot. Both sit on translucent paper with a
22 px blur. The in-page section switcher is a segmented pill.

## Do's and Don'ts

### Do:
- **Do** keep the canvas Paper (#f5f5f7) and every card white, borderless and
  softly lifted.
- **Do** keep one display headline per page, and give its key phrase the green
  gradient (#0b7a4b → #17b26a → #0a8f8a; brighter greens in dark mode).
- **Do** label every result's provenance with the badge pair: green for real,
  violet for synthetic.
- **Do** set numbers in Metric weight with tight tracking, and keep labels small
  and quiet above them.
- **Do** make every button a pill: one Current Green primary, and grey-fill
  secondaries.
- **Do** put new illustrations on transparent backgrounds so they float on
  Paper plates in both themes.
- **Do** honour reduced motion (no hover lift, no press scale) and reduced
  transparency or increased contrast (opaque navigation, hairline outlines
  instead of shadows).

### Don't:
- **Don't** make it look like a generic admin template: no bordered grey boxes,
  no dense link-farm sidebars, no stock SaaS card grids.
- **Don't** put borders on cards, or add a second UI accent colour beyond
  Current Green.
- **Don't** use Synthetic Violet or the chart colours for anything except what
  they mean.
- **Don't** animate charts or count numbers up. Evidence appears at rest.
- **Don't** apply glass blur to evidence surfaces. It is for navigation only.
- **Don't** set new text below 11 px. The existing 10 px captions (stat footers,
  panel subtitles) are drift to fix, not precedent.
