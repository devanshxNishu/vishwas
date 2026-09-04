# Deck figures

Every graphic on `deck/VISHWAS_SIH.pptx` (slides 2 to 5) is produced by a script
in this folder. Rendered PNGs live in `deck/assets/`.

    cd src/deck_figures
    python3 deck_figC_what_it_is.py     # slide 2 left   - what VISHWAS is
    python3 deck_figF_collapse.py       # slide 2 right  - 43.9% vs 0.90%
    python3 deck_figD_features.py       # slide 3 left   - the 23 features
    python3 deck_figE_slide4.py         # slide 4 right  - inversion + the tie
    python3 deck_figAB_leadtime.py      # slide 5 right  - IMD lead-time decay

Each script asserts on save that no ink touches the canvas edge (`noink`), which
is what stops a figure from looking clipped once it is scaled into a slide.

`fig6_confidence_map.png` (slide 3 right) comes from `src/08_demo_map.py`, not
from this folder.

## Rules

* **Numbers live in the scripts.** `scripts/check_docs.py` walks `.md` files
  only; a wrong number baked into a PNG is invisible to it and always will be.
  Figure captions are checked by reading the figure.
* **If you add a figure, commit its script in the same commit.** An uncommitted
  generator is how fig4 ended up with two different captions and no way to tell
  which one shipped.
* **"variance" is load-bearing in `deck_figF_collapse.py`.** The claim is the
  share of the *variance* in forecast error, not of forecast error.
* **Five wet-point definitions is right on figF and on slide 6, and wrong on the
  +0.13 to +0.16 margin range, which spans two variants.** See CLAUDE.md P18.

## Retired

* `fig4_inversion` and `figB_tie` were two separate graphics on slide 4. They
  are folded into `deck_figE_slide4.py`. `src/11_inversion.py` still prints a
  pooled 0.909 vs 0.885 onto its figure; that figure is no longer on the deck,
  and those numbers are the artefact the slide exists to discredit. Do not put
  it back without fixing that caption first.
