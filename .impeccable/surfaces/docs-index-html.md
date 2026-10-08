---
version: 1
slug: "docs-index-html"
primary_target: "docs/index.html"
related_targets: ["docs/paper.html"]
---

# Surface brief: project showcase (docs/index.html + docs/paper.html)

**Scope and mode.** Two linked static pages served by GitHub Pages from `docs/`:
- `index.html` is the landing page, in **Persuade** mode.
- `paper.html` is the scroll-told report, in **Read** mode.

Both inherit the Honest Showroom world from DESIGN.md.

**Audience and job.**
- BMCC professors, recruiters and curious visitors, most with no ML background.
- They should understand within a minute what Current does, what it found, and
  that the work is careful and honest.
- Actions: read the paper, open the repo, download the PDF.

**Proof and content.** Only real project material:
- the Higgsfield house and appliance renders;
- dashboard screenshots;
- the House 5 figure;
- documented numbers: 8 → 4,368 windows; F1 0.781 → 0.297 vs simulator 0.686;
  washer 0.701; 78 tests.

No invented claims, users or accuracy.

**Constraints.**
- Static HTML/CSS/JS with no build step.
- Must work on GitHub Pages at any sub-path, so links are relative.
- Charts and figures stay at rest; only staging moves.
- Respect `prefers-reduced-motion`.
- Light and dark themes.

## Direction contract

THESIS: The house is the star. Energy visibly flows to each appliance, and the
page then dramatizes the NILM problem by merging those lines into the single
total wire a model actually sees. It refuses the category default of a
case-study template (hero banner, then Problem / Approach / Results cards).

OWN-WORLD:
- Grey paper (#f5f5f7), borderless white cards with soft lift, and a single
  Current Green voice (#0b7a4b).
- Synthetic Violet appears only to mean "simulated".
- Huge tight San Francisco display type and pill controls.
- Transparent product renders floating on Paper plates.

STORY:
1. Here is a home and its appliances.
2. The meter only sees one combined wire.
3. Can a model untangle it?
4. I tested that honestly: the development score of 0.781 fell to 0.297 on a
   sealed house, and the simulator-trained model did better.
5. Then: read the paper or explore the code.

FIRST VIEWPORT:
- **Left, about 45%:** the eyebrow "Current · Energy research lab", the display
  headline "Your home, in watts." at about 5.5rem with "in watts." in the green
  gradient, a one-line lead, a primary pill "See the findings" and a secondary
  pill "Read the paper".
- **Right, about 55%:** the house render at full height, with three animated SVG
  energy paths pulsing from the meter to the fridge, lamp and washer.

FORM: Living House (dealt candidate 4 of 6), combined with the Staged Paper
(candidate 6) at the user's steer; seed key d414dc49.

Signature interaction: as the visitor scrolls past the hero, the three coloured
appliance lines converge and merge into one total line, which is what the model
must untangle. Motion grammar: calm reveals with ease-out, staged once per
section; the paper pins each figure while its text scrolls.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
