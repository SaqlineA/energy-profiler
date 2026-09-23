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
