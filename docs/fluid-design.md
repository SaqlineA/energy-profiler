# Fluid dashboard design

## Design contract

Keep the dependency-free web stack and green identity. System fonts, rounded
solid cards and a prominent live-power card establish hierarchy. Desktop keeps
the sidebar; narrow screens stack overview, appliances, research and sessions.
Tables scroll inside panels. Pill links replace arbitrary numbered sections.

Semantic ink, muted text, paper, surface, accent and border tokens in
`static/fluid.css` support light and dark palettes. Primary numbers remain
dominant. No external font download is needed.

## Apple-inspired, still a website

The supplied Apple design references influenced typography, materials, layout
and motion. Translucency is restricted to navigation; evidence surfaces remain
solid. Native web controls and keyboard focus stay intact. This is neither an
Apple product nor a native macOS interface.

Interaction feedback lasts 180 ms. Numbers do not count up and charts gain no
decorative animation. Reduced-motion disables motion; reduced-transparency and
high-contrast preferences request opaque navigation. Browsers without blur
support retain near-opaque backgrounds.

## Review

- Summary: restrained navigation materials and solid evidence surfaces, no new dependencies.
- Critical: uncertainty and timing limitations remain visible; polish must not imply model certainty.
- Improvements: system typography, semantic secondary text, larger controls and responsive links.
- Craft: brief pressed feedback, gentle disclosure reveal and shared color tokens.
- What works: the green power card anchors the monitoring workflow.
- Platform notes: preserve web semantics instead of copying macOS window chrome.

Preference media queries alone do not constitute an accessibility certification.
Runtime checks passed at 320, 768, 1024 and 1440 CSS pixels with no page-level
horizontal overflow. Keyboard Enter opens and closes source settings. The
House 2 report renders its chart, uncertainty note and metrics; no browser
console errors were observed. These visual checks used the browser's dark theme.
Light theme and reduced-motion/transparency preferences were code-reviewed,
not separately emulated. All 48 application and four research tests passed;
both JavaScript files passed Node syntax checks.

## Apple.com-style layer (2026-09-27)

`static/apple.css` loads last and changes styling only. Deleting it restores the
fluid design above. It adds:

- **Palette and surfaces:** a #f5f5f7 page, #1d1d1f ink, borderless white cards
  with layered soft shadows (a slight lift on hover when motion is allowed), and
  a true-black dark mode with #1c1c1e cards.
- **Hero:** a large "Your home, *in watts.*" headline with a green gradient
  (brighter in dark mode), pill buttons, and a transparent house illustration.
  On screens up to 900 px the illustration moves below the text.
- **Bento stats:** larger numbers, and a green-gradient live-power tile.
- **Controls:** Apple-style pills. Primary is solid green; secondary is a grey
  fill with no border. Segmented controls have a grey track and a white thumb.
- **Appliance cards:** a product photo on a soft plate. The washer card shows
  the photo and details side by side, stacking on phones. Missing images hide
  themselves (`onerror`), so the page never shows a broken icon.

Reduced motion removes the hover lift. Reduced transparency or increased
contrast swaps shadows for hairline outlines.

**Checked on 2026-09-27** at 375, 768 and 1,280 px (plus the pane's own
desktop width) in light and dark mode:
- no page-level horizontal overflow;
- hero buttons both 48 px tall;
- the hero image never overlaps the buttons;
- every static asset loads.

Screenshots were reviewed for the hero (desktop light and dark, and phone) and
for the appliance cards.

### Images (Higgsfield)

The five images in `static/img/` were generated with **Higgsfield GPT Image 2**
(medium quality, transparent background) from the account owner's free-plan
workspace, using 6 credits. GPT Image 2.5 needs a paid plan. The images were
then trimmed and saved as WebP (about 215 KB total).

| File | Prompt summary |
|---|---|
| `hero.webp` (2K) | Apple product-page 3D render of a white cutaway two-storey house model, with glowing emerald energy lines running to a fridge, lamp and washing machine; soft studio light; no text, logos or people |
| `lamp.webp`, `refrigerator.webp`, `microwave.webp`, `washing_machine.webp` (1K) | Apple product-page studio photo of the appliance, three-quarter view, soft light, a tiny emerald power light; no text, logos or people |

These are illustrations, not photos of the simulated or REFIT appliances. The
hero's solar panels were added by the model and are not part of the simulation.
