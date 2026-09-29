# Proxy Printing Sheet Generator

Generate a printable HTML sheet of standard-size trading cards (63 × 88 mm,
"poker size") from your own source images, sized precisely for cutting at home.

The script auto-detects and trims the print bleed that many card exports carry,
lays the cards out butted together so adjacent cards share one cut line, and
adds alignment marks that make every cut line — including interior ones — easy
to index with a ruler or paper trimmer.

> This tool only handles layout and printing of images **you** supply. It does
> not include, download, or distribute any card artwork. Do not use it to
> reproduce copyrighted material you don't have the right to print.

## Folders

- **cards/** — Put the card images you want to print here (`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.bmp`, `.tif`).
- **archival/** — Move images here once you've printed them, to keep a record of what's already done.

(Both folders and the generated `print_sheet.html` are git-ignored so your
images and output never get committed.)

## How to use

1. Drop your card images into the **cards** folder.
2. Run the script one of two ways:
   - **Double-click** `Make Print Sheet.command` in Finder (macOS), **or**
   - In a terminal: `python3 make_print_sheet.py`
3. `print_sheet.html` is generated. Open it in your browser and review it.
4. Print with **Cmd/Ctrl+P**. Use these settings for correct sizing:
   - Scale: **100%** (do NOT "fit to page")
   - Margins: **Default** or **None**
   - Paper: **A4** (or change `PAGE_SIZE` in the script to `"Letter"`)
5. Move the printed images from **cards/** to **archival/**.

## Layout & cutting

- Card size (trim / final): **63 × 88 mm** (standard poker/bridge card size).
- Cards are **butted together (no gap)** so adjacent cards share ONE cut line.
- Each card shows a **2 mm rounded corner** (a visual guide; you can hand-round
  to a larger final radius afterward, cutting this rounding away).
- **3 × 3 = 9 cards per page.** Add more than 9 images and extra pages are created automatically.

### How to cut (fast, whole-sheet method)

Because there's no gap, one straight cut separates two rows (or columns) at
once. You make just **4 vertical cuts and 4 horizontal cuts** per page.

Two sets of alignment marks let you index every cut line — including the
interior ones that lose their edge reference after the first cut:

- **Edge ticks** — small marks in the page margins at every grid line,
  reaching the top, bottom, left, and right edges of the paper.
- **Node crosses (+)** — a small cross at every corner intersection, sitting
  in the little nook left by the rounded corners. These are printed *on* the
  sheet at every node (interior included), so even the center card's cut lines
  stay findable after you've separated the outer pieces.

To cut:

1. Pick a grid line. For a vertical cut, sight along its **top edge tick**,
   the **node crosses** down that line, and its **bottom edge tick** — they're
   all colinear. For a horizontal cut, use the left tick, the crosses, and the
   right tick.
2. Lay a ruler / paper trimmer along those marks.
3. Cut straight through the whole sheet.
4. Repeat for every grid line. Order doesn't matter — the node crosses keep
   interior lines findable no matter what you cut first.

When you later hand-round each card, the printed rounding and the node crosses
are trimmed away.

Optional: set `GRID_LINES = True` in the script to also print faint gray lines
running the full length of the sheet along every cut line (the lines print
across the card faces, so the ticks + crosses are usually cleaner).

## Bleed handling

Many card print/export services add extra artwork (**bleed**) around the card
so the cut never leaves a white edge. A common export carries roughly
**3–3.2 mm of bleed per edge** (full image ≈ 69.4 × 94.4 mm; final card
63 × 88 mm).

The script does **not** edit your source images. Instead it displays each image
at full size and clips the visible area down to the true 63 × 88 mm trim box —
so exactly the bleed is trimmed off and the printed card is the correct size.

By default `AUTO_BLEED = True`: the script measures each image's real aspect
ratio and trims to the exact card edge automatically. This adapts to whatever
bleed an export uses. If an image's ratio doesn't look like a bleed card, or it
can't be read, it falls back to the fixed `BLEED_MM` value.

To turn off auto-detection and always trim a fixed amount, set in the script:

```python
AUTO_BLEED = False
BLEED_MM = 3.0   # trim this many mm off each edge
```

## Configuration

Edit the constants at the top of `make_print_sheet.py`:

```python
COLS = 3            # cards per row
ROWS = 3            # rows per page
CARD_W_MM = 63.0    # card trim width
CARD_H_MM = 88.0    # card trim height
GAP_MM = 0.0        # gap between cards (0 = butted together, shared cut lines)
PAGE_SIZE = "A4"    # "A4" or "Letter"
CUT_LINES = False   # thin border on the trim line of each card
CROP_MARKS = False  # per-card corner crop marks (only useful when GAP_MM > 0)
EDGE_TICKS = True   # registration ticks in the margins at every cut line
GRID_LINES = False  # faint full-length lines across the sheet on every cut line
CARD_RADIUS_MM = 2.0      # visual rounded-corner radius on each card
NODE_CROSS = True         # + cross at every corner intersection (incl. interior)
NODE_CROSS_LEN_MM = 2.0   # length of each cross arm
NODE_CROSS_W_MM = 0.2     # cross line thickness
AUTO_BLEED = True   # auto-detect & trim each image's bleed to the card edge
BLEED_MM = 3.0      # fallback bleed per edge when AUTO_BLEED is False
```

## Requirements

- Python 3 (uses only the standard library — no packages to install).

## Notes

- Images are embedded directly into the generated HTML, so the file prints
  reliably and can be moved/shared as a single self-contained file.
- Images are scaled to fill each card box; if a source image isn't a 63:88
  ratio it will be cropped slightly to fit. Use images already sized/cropped
  to the card for best results.
