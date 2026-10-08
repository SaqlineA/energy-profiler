# Current — Energy Profiler: notes for Claude

Read this first in every session. **Product truth** is in `PRODUCT.md`, the
**visual system** in `DESIGN.md`, and **results** in `docs/`.

## Working with the builder

- **The builder is a student learning ML and hardware.** Explain decisions in
  plain language.
- **Keep changes simple and tested.** No frameworks or rewrites (FastAPI,
  SQLite and plain HTML/CSS/JS, with no build step).
- **Be honest about accuracy.** Never overstate it. Label real vs synthetic data
  everywhere.
- **Ask before** spending money (paid services, Higgsfield credits), making
  anything public, or doing irreversible git operations. Hardware, wiring and
  mains safety belong to the builder.
- **The builder pastes plans from another advisor.** Follow the steps the
  builder confirms.

## Research rules (do not break)

- **Preregister:** commit each experiment's protocol and decision rule before
  running it. Run it once; record failures as they are; never tune toward a score.
- **One change at a time.** Simulator changes are opt-in versions (`fridge=`,
  `washer=`, `microwave=`, `background='v2'`). v1 output stays byte-identical
  (golden hashes in `test_realistic.py`).
- **REFIT House 5 is spent** (scored once, `docs/final-test.md`). Any new final
  test needs a fresh sealed house.
- **Data handling:**
  - Preserve timestamps and gaps.
  - Blank means unknown, not zero.
  - Appliance truth is used for evaluation only, never as a model input.
- **Live model:** `data/models/current.json` = `3132ae99ccd11d4c` (synthetic,
  seed 43). Research models never get promoted automatically.

## Key results (details in docs/)

- Fridge, trained on Houses 1, 3 and 4 with background-relative features:
  - **Development, House 2:** Decision Tree F1 0.781.
  - **Sealed House 5:** F1 0.297.
  - **Simulator-trained model on House 5:** F1 0.686.
- Washer (synthetic): Random Forest with 5-reading windows, F1 0.70. An
  8-minute window hurt.

## Commands

```powershell
.\.venv\Scripts\python.exe app.py                      # dashboard at http://127.0.0.1:8000
.\.venv\Scripts\python.exe -m unittest -q              # 78 tests
.\.venv\Scripts\python.exe -m unittest discover -s research -q
node --check static/app.js; node --check static/experiments.js; node --check docs/site.js
.\.venv\Scripts\python.exe sensor_client.py --start    # ESP32 stand-in
```

**Showcase site:** `docs/index.html` and `docs/paper.html`, for GitHub Pages
from `/docs`. To preview, serve `docs/` over HTTP (for example
`python -m http.server` inside `docs/`); `paper.html` fetches `report.md`.

## Environment quirks (Windows)

- **Inline shell scripts:** long heredoc Python sometimes breaks on quotes.
  Write the script to the scratchpad and run it instead. Keep paths under 260
  characters.
- **Headless Chrome screenshots:**
  - Use a tall window rather than scrolling (smooth scroll leaves blank frames).
  - Windows won't size a window narrower than about 500 px, so capture phone
    widths inside a 390 px iframe.
  - Use `--force-prefers-reduced-motion` to settle entrance animations.
- **Tool locations:**
  - `gh` is not installed. Use plain `git` for pushes; repo settings are done in
    the GitHub web UI.
  - The Higgsfield CLI is at `~/.local/bin/higgsfield.exe`, on the free plan:
    GPT Image 2 works, GPT Image 2.5 needs a paid plan.
- **Personal files:** the resume files in this folder are gitignored and must
  never be committed.

## Status and next steps

The roadmap is the builder's 21 steps. Done: Steps 1–16, plus Phase 1
visibility work (README, report, showcase, MIT license). Open:

1. **Author name:** ask the builder whether to replace "SaqlineA" with their
   real name on the paper and site.
2. **Going public:** the builder makes the repo public, then enables Pages
   (branch `codex/online-workspace`, folder `/docs`). Then tag `v1.0`.
3. **Resume:** update the resume project section (`resume.html`, local only)
   after the builder confirms.
4. **Step 17 (ESP32):** the builder is buying an AITRIP ESP32-WROOM-32 (USB-C,
   CP2102). Write a starter Arduino sketch (Wi-Fi, NTP, batched POSTs to
   `/api/sensor/readings` with the token).
5. **Later research:**
   - leave-one-house-out across more REFIT houses;
   - a seq2point baseline via NILMTK;
   - smart-plug real data with no mains work;
   - testing whether simulator v2 improves ML, on fresh houses.
