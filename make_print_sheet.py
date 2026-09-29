#!/usr/bin/env python3
"""
make_print_sheet.py
-------------------
Builds a printable HTML sheet of standard-size trading cards (63 x 88 mm,
"poker size") from source images that include a print bleed.

Many card print services export images with extra artwork (bleed) around the
card so the cut never leaves a white edge. A common export carries roughly
3 mm of bleed on every side:
  - Final card (trim) size ......... 63 x 88 mm
  - Bleed added each edge .......... ~3 mm
  - Full source image size ......... ~69 x 94 mm

This script does NOT modify your source files. Instead it displays each
image at full bleed size and clips the visible area down to the true
63 x 88 mm trim box (removing the bleed from every edge). The printed card is
therefore the correct size, with alignment marks so you can cut precisely.

Usage:
    python3 make_print_sheet.py

Then open print_sheet.html in your browser and print (Cmd+P).
Set scale to 100% and margins to "None"/"Default".
"""

import base64
import mimetypes
import struct
from pathlib import Path

# ---------------------------------------------------------------------------
# CONFIGURATION  -- change these if you want a different layout
# ---------------------------------------------------------------------------
COLS = 3            # cards per row  (3 x 3 = 9 cards fit on A4/Letter)
ROWS = 3            # rows per page
CARD_W_MM = 63.0    # standard card TRIM width  in mm (final size, poker size)
CARD_H_MM = 88.0    # standard card TRIM height in mm (final size, poker size)
GAP_MM = 0.0        # space between finished cards in mm.
                    # 0 = cards butted together so adjacent cards share ONE
                    # cut line (fastest to cut the whole sheet at once).
PAGE_SIZE = "A4"    # "A4" or "Letter"
CUT_LINES = False   # draw a thin border on the trim line of each card
                    # (off by default; use the guides below instead)
CROP_MARKS = False  # per-card corner crop marks (only useful when GAP_MM > 0)
EDGE_TICKS = True   # draw registration ticks in the page margins at every
                    # grid line, extending to all four paper edges. Line up a
                    # ruler/trimmer between a top tick and its matching bottom
                    # tick (or left/right) and cut straight through the whole
                    # sheet. These survive each cut because they sit in the
                    # margin, so interior cut lines are always findable.
GRID_LINES = False  # optionally also draw faint full-length lines across the
                    # sheet on every cut line (belt-and-suspenders; prints
                    # thin gray lines between cards).
CARD_RADIUS_MM = 2.0  # rounded-corner radius shown on each card. With no gap,
                    # rounding leaves a small nook where four card corners meet
                    # -- a natural spot for the alignment crosses below. You'll
                    # round to your final ~2.5 mm radius by hand, cutting this
                    # 2 mm rounding away.
NODE_CROSS = True   # draw a small + cross at every grid node (where card
                    # corners meet), including interior ones, so you can index
                    # a ruler on interior cut lines. Visible in the rounded
                    # corner nooks and survives cutting.
NODE_CROSS_LEN_MM = 2.0   # length of each arm of the cross
NODE_CROSS_W_MM = 0.2     # thickness of the cross lines

# Bleed handling:
#   AUTO_BLEED = True  -> measure each image and trim EXACTLY to the 63x88
#                         trim box based on its real aspect ratio (recommended
#                         for bleed-included exports, which often carry
#                         ~3.19 mm bleed).
#   AUTO_BLEED = False -> use the fixed BLEED_MM value below for every image.
AUTO_BLEED = True
BLEED_MM = 3.0      # fallback bleed per edge (mm) when AUTO_BLEED is False
                    # or when an image's size cannot be read.

# ---------------------------------------------------------------------------
# DEBUG / PRINTER-SETUP MODE
# ---------------------------------------------------------------------------
# Turn this on to print fewer than a full grid of cards and place them in
# specific slots, for calibrating a printer (checking size, margins, and
# exactly where ink lands on the page).
DEBUG_MODE = False

# DEBUG_SLOTS maps a grid position to a card. A position is (row, col) with
# row 0 = top, col 0 = left. The value picks which image goes there:
#   - an int   -> index into the cards folder (0 = first image, sorted by name)
#   - a str    -> a filename (or partial name) to match in the cards folder
# Any slot you don't list is left blank. Only ONE page is produced in debug
# mode, using exactly these placements. Guides/marks still draw normally.
#
# Examples:
#   {(0, 0): 0}                      -> one card in the top-left corner
#   {(0, 0): 0, (2, 2): 0}           -> same card in top-left and bottom-right
#   {(1, 1): "lotus"}                -> match a file whose name contains "lotus"
#   {(r, c): 0 for r in range(ROWS) for c in range(COLS)}  -> fill every slot
DEBUG_SLOTS = {
    (0, 0): 0,   # top-left
    (0, 2): 0,   # top-right
    (2, 0): 0,   # bottom-left
    (2, 2): 0,   # bottom-right
    (1, 1): 0,   # center
}
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
CARDS_DIR = SCRIPT_DIR / "cards"
OUTPUT_FILE = SCRIPT_DIR / "print_sheet.html"

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff"}


def find_images(folder: Path):
    """Return a sorted list of image file paths in the given folder."""
    if not folder.exists():
        return []
    files = [
        p for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS
    ]
    return sorted(files, key=lambda p: p.name.lower())


def image_size(path: Path):
    """Return (width, height) in pixels using only the standard library.
    Supports PNG, JPEG, GIF, BMP. Returns None if it can't be determined."""
    try:
        with open(path, "rb") as f:
            head = f.read(26)
            if len(head) < 24:
                return None
            # PNG
            if head[:8] == b"\x89PNG\r\n\x1a\n":
                w, h = struct.unpack(">II", head[16:24])
                return (w, h)
            # GIF
            if head[:6] in (b"GIF87a", b"GIF89a"):
                w, h = struct.unpack("<HH", head[6:10])
                return (w, h)
            # BMP
            if head[:2] == b"BM":
                w, h = struct.unpack("<ii", head[18:26])
                return (abs(w), abs(h))
            # JPEG
            if head[:2] == b"\xff\xd8":
                f.seek(2)
                b = f.read(1)
                while b and b != b"":
                    while b != b"\xff":
                        b = f.read(1)
                        if not b:
                            return None
                    marker = f.read(1)
                    while marker == b"\xff":
                        marker = f.read(1)
                    if marker in (b"\xc0", b"\xc1", b"\xc2", b"\xc3",
                                  b"\xc5", b"\xc6", b"\xc7", b"\xc9",
                                  b"\xca", b"\xcb", b"\xcd", b"\xce", b"\xcf"):
                        f.read(3)  # length(2) + precision(1)
                        h, w = struct.unpack(">HH", f.read(4))
                        return (w, h)
                    seg_len = struct.unpack(">H", f.read(2))[0]
                    f.seek(seg_len - 2, 1)
                    b = f.read(1)
    except Exception:
        return None
    return None


def compute_full_size(path: Path):
    """Return (full_w_mm, full_h_mm, bleed_mm) for how the image should be
    displayed so that clipping to the CARD_W_MM x CARD_H_MM trim box removes
    exactly the bleed. Uses the image's real aspect ratio when AUTO_BLEED is
    on; otherwise (or on failure) uses the fixed BLEED_MM."""
    def fixed():
        return (CARD_W_MM + 2 * BLEED_MM, CARD_H_MM + 2 * BLEED_MM, BLEED_MM)

    if not AUTO_BLEED:
        return fixed()

    size = image_size(path)
    if not size:
        return fixed()
    w, h = size
    if w <= 0 or h <= 0:
        return fixed()

    r = w / h  # width/height of the full (bleed-inclusive) image
    # Solve for uniform per-edge bleed b so (63+2b)/(88+2b) == r
    #   b = (88r - 63) / (2 - 2r)
    denom = (2 - 2 * r)
    if abs(denom) < 1e-9:
        return fixed()
    b = (CARD_H_MM * r - CARD_W_MM) / denom

    # Sanity: bleed should be a small positive value (0.5 .. 6 mm typical).
    if b < 0.5 or b > 6.0:
        # Ratio doesn't look like a bleed card; fall back to cover at fixed bleed.
        return fixed()

    return (CARD_W_MM + 2 * b, CARD_H_MM + 2 * b, b)


def embed_image(path: Path) -> str:
    """Return a data: URI so the HTML is fully self-contained (prints reliably)."""
    mime, _ = mimetypes.guess_type(str(path))
    if mime is None:
        mime = "image/png"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


def chunk(seq, size):
    """Yield successive lists of length <= size from seq."""
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def card_cell(img_path):
    """Build one grid cell: a trim box with the full-bleed image clipped,
    plus four corner crop-mark ticks positioned just outside the trim box.
    Each image is sized individually so exactly its bleed is trimmed."""
    src = embed_image(img_path)
    full_w, full_h, bleed = compute_full_size(img_path)
    img_style = (
        f"width:{full_w:.3f}mm;height:{full_h:.3f}mm;"
    )
    marks = ""
    if CROP_MARKS:
        marks = (
            '<span class="m tl-h"></span><span class="m tl-v"></span>'
            '<span class="m tr-h"></span><span class="m tr-v"></span>'
            '<span class="m bl-h"></span><span class="m bl-v"></span>'
            '<span class="m br-h"></span><span class="m br-v"></span>'
        )
    return (
        f'<div class="cell">'
        f'<div class="card">'
        f'<img style="{img_style}" src="{src}" alt="{img_path.name}">'
        f'</div>'
        f'{marks}'
        f'</div>'
    )


def guides_html():
    """Edge registration ticks (in the margins) and optional full-length grid
    lines, drawn at every card boundary. Positioned relative to the .block,
    which is exactly COLS*card_w by ROWS*card_h."""
    parts = []

    # Vertical cut lines are at x = i * card_w  (i = 0..COLS)
    # Horizontal cut lines are at y = j * card_h (j = 0..ROWS)
    if EDGE_TICKS:
        for i in range(COLS + 1):
            left = f"calc({i} * var(--card-w))"
            # tick above the block (points up into top margin)
            parts.append(f'<span class="tick v top" style="left:{left};"></span>')
            # tick below the block (points down into bottom margin)
            parts.append(f'<span class="tick v bot" style="left:{left};"></span>')
        for j in range(ROWS + 1):
            top = f"calc({j} * var(--card-h))"
            # tick left of the block
            parts.append(f'<span class="tick h lft" style="top:{top};"></span>')
            # tick right of the block
            parts.append(f'<span class="tick h rgt" style="top:{top};"></span>')

    if GRID_LINES:
        for i in range(COLS + 1):
            left = f"calc({i} * var(--card-w))"
            parts.append(f'<span class="gline v" style="left:{left};"></span>')
        for j in range(ROWS + 1):
            top = f"calc({j} * var(--card-h))"
            parts.append(f'<span class="gline h" style="top:{top};"></span>')

    if NODE_CROSS:
        # A small + at every grid node (i*card_w, j*card_h). Interior nodes
        # sit in the nook left by the rounded corners; edge/corner nodes sit
        # on the block boundary. Each node = one horizontal + one vertical bar,
        # both centered on the node.
        for i in range(COLS + 1):
            for j in range(ROWS + 1):
                x = f"calc({i} * var(--card-w))"
                y = f"calc({j} * var(--card-h))"
                parts.append(
                    f'<span class="cross ch" style="left:{x};top:{y};"></span>'
                    f'<span class="cross cv" style="left:{x};top:{y};"></span>'
                )

    return "".join(parts)


def resolve_slot_image(value, images):
    """Resolve a DEBUG_SLOTS value (int index or filename substring) to an
    image Path, or None if it can't be matched."""
    if not images:
        return None
    if isinstance(value, int):
        if 0 <= value < len(images):
            return images[value]
        return None
    if isinstance(value, str):
        needle = value.lower()
        # exact name first, then substring match
        for p in images:
            if p.name.lower() == needle:
                return p
        for p in images:
            if needle in p.name.lower():
                return p
        return None
    return None


def build_debug_page(images):
    """Build a single page using DEBUG_SLOTS placements. Slots not listed are
    blank. Returns (page_html, placements) where placements is a list of
    (row, col, Path|None) for logging."""
    per_page = COLS * ROWS
    guides = guides_html()

    placements = []
    cells = []
    for idx in range(per_page):
        r, c = divmod(idx, COLS)
        val = DEBUG_SLOTS.get((r, c))
        img = resolve_slot_image(val, images) if val is not None else None
        placements.append((r, c, img))
        if img is not None:
            cells.append(card_cell(img))
        else:
            cells.append('<div class="cell"><div class="card empty-cell"></div></div>')

    page_html = (
        f'<div class="page">'
        f'<div class="block">'
        f'<div class="grid">{"".join(cells)}</div>'
        f'{guides}'
        f'</div>'
        f'</div>'
    )
    return page_html, placements


def build_html(images):
    per_page = COLS * ROWS
    trim_border = "0.2mm solid rgba(0,0,0,0.55)" if CUT_LINES else "none"

    debug_placements = None
    pages_html = []
    if not images:
        pages_html.append(
            '<div class="empty">No images found in the '
            '<code>cards</code> folder.<br>'
            'Drop your card images in there and run the script again.</div>'
        )
    elif DEBUG_MODE:
        page_html, debug_placements = build_debug_page(images)
        pages_html.append(page_html)
    else:
        guides = guides_html()
        for page_imgs in chunk(images, per_page):
            cells = [card_cell(img) for img in page_imgs]
            while len(cells) < per_page:
                cells.append('<div class="cell"><div class="card empty-cell"></div></div>')
            pages_html.append(
                f'<div class="page">'
                f'<div class="block">'
                f'<div class="grid">{"".join(cells)}</div>'
                f'{guides}'
                f'</div>'
                f'</div>'
            )

    if DEBUG_MODE and debug_placements is not None:
        total = sum(1 for _, _, img in debug_placements if img is not None)
        num_pages = 1
        debug_banner = (
            '<div class="info" style="background:#fff3cd;border-bottom-color:#e0c96b;">'
            f'<b>DEBUG / printer-setup mode</b> &mdash; single page, {total} card(s) '
            'placed in fixed slots. Turn off <code>DEBUG_MODE</code> for a normal run.'
            '</div>'
        )
    else:
        total = len(images)
        num_pages = (total + per_page - 1) // per_page if total else 0
        debug_banner = ""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Card Print Sheet</title>
<style>
  :root {{
    --card-w: {CARD_W_MM}mm;      /* trim size */
    --card-h: {CARD_H_MM}mm;
    --gap: {GAP_MM}mm;
    --radius: {CARD_RADIUS_MM}mm; /* visual rounded corner on each card */
    --tick-len: 4mm;              /* how far edge ticks reach into margin */
    --tick-w: 0.25mm;             /* tick / line thickness */
    --tick-color: #000;
    --gline-color: #999;          /* faint full-length grid line color */
    --cross-len: {NODE_CROSS_LEN_MM}mm;  /* node cross arm length */
    --cross-w: {NODE_CROSS_W_MM}mm;      /* node cross thickness */
    --cross-color: #000;
  }}

  @page {{
    size: {PAGE_SIZE} portrait;
    margin: 6mm;
  }}

  * {{ box-sizing: border-box; }}

  body {{
    margin: 0;
    background: #d9d9d9;
    font-family: -apple-system, Helvetica, Arial, sans-serif;
    color: #222;
  }}

  .info {{
    padding: 10px 16px;
    background: #fff;
    border-bottom: 1px solid #bbb;
    font-size: 14px;
  }}
  .info b {{ color: #000; }}

  .page {{
    background: #fff;
    margin: 16px auto;
    padding: 8mm;
    width: 210mm;               /* A4 width; harmless for Letter */
    box-shadow: 0 2px 8px rgba(0,0,0,.25);
    display: flex;
    justify-content: center;    /* center the block horizontally */
  }}

  /* The block is exactly the card grid size; ticks/lines position off it. */
  .block {{
    position: relative;
    width: calc({COLS} * var(--card-w) + {max(COLS - 1, 0)} * var(--gap));
    height: calc({ROWS} * var(--card-h) + {max(ROWS - 1, 0)} * var(--gap));
  }}

  .grid {{
    display: grid;
    grid-template-columns: repeat({COLS}, var(--card-w));
    grid-auto-rows: var(--card-h);
    gap: var(--gap);
  }}

  /* The cell is exactly the trim size. */
  .cell {{
    position: relative;
    width: var(--card-w);
    height: var(--card-h);
  }}

  /* Trim box = final printed card size. Bleed is clipped away here. */
  .card {{
    position: absolute;
    inset: 0;
    overflow: hidden;
    border: {trim_border};
    border-radius: var(--radius);   /* visual rounded corner (cut away later) */
  }}

  /* Full bleed image (size set inline per-image), centered so equal bleed
     is clipped on all sides by the trim box above. */
  .card img {{
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    display: block;
  }}

  /* --- Edge registration ticks: sit in the margin at every cut line --- */
  .tick {{ position: absolute; background: var(--tick-color); }}
  /* vertical ticks (for vertical cut lines): thin & tall, extend past
     top/bottom edges of the block into the margins. */
  .tick.v {{ width: var(--tick-w); height: var(--tick-len); transform: translateX(-50%); }}
  .tick.v.top {{ top: calc(-1 * var(--tick-len)); }}
  .tick.v.bot {{ bottom: calc(-1 * var(--tick-len)); }}
  /* horizontal ticks (for horizontal cut lines): thin & wide, extend past
     left/right edges of the block into the margins. */
  .tick.h {{ height: var(--tick-w); width: var(--tick-len); transform: translateY(-50%); }}
  .tick.h.lft {{ left: calc(-1 * var(--tick-len)); }}
  .tick.h.rgt {{ right: calc(-1 * var(--tick-len)); }}

  /* --- Optional faint full-length grid lines across the whole sheet --- */
  .gline {{ position: absolute; background: var(--gline-color); }}
  .gline.v {{ top: 0; height: 100%; width: var(--tick-w); transform: translateX(-50%); }}
  .gline.h {{ left: 0; width: 100%; height: var(--tick-w); transform: translateY(-50%); }}

  /* --- Node crosses: a small + centered on every grid node (corner
     intersection). Sit in the rounded-corner nooks so interior cut lines
     can still be indexed. Rendered above the cards. --- */
  .cross {{ position: absolute; background: var(--cross-color); z-index: 5; }}
  .cross.ch {{ width: var(--cross-len); height: var(--cross-w);
               transform: translate(-50%, -50%); }}
  .cross.cv {{ width: var(--cross-w); height: var(--cross-len);
               transform: translate(-50%, -50%); }}

  /* --- Legacy per-card crop marks (only when CROP_MARKS + GAP_MM>0) --- */
  .m {{ position: absolute; background: var(--tick-color); }}
  .tl-h, .tr-h, .bl-h, .br-h {{ width: 3mm; height: var(--tick-w); }}
  .tl-v, .tr-v, .bl-v, .br-v {{ width: var(--tick-w); height: 3mm; }}
  .tl-h {{ top: calc(-1 * var(--tick-w)); left: -3mm; }}
  .tl-v {{ left: calc(-1 * var(--tick-w)); top: -3mm; }}
  .tr-h {{ top: calc(-1 * var(--tick-w)); right: -3mm; }}
  .tr-v {{ right: calc(-1 * var(--tick-w)); top: -3mm; }}
  .bl-h {{ bottom: calc(-1 * var(--tick-w)); left: -3mm; }}
  .bl-v {{ left: calc(-1 * var(--tick-w)); bottom: -3mm; }}
  .br-h {{ bottom: calc(-1 * var(--tick-w)); right: -3mm; }}
  .br-v {{ right: calc(-1 * var(--tick-w)); bottom: -3mm; }}

  .empty-cell {{ border: none; }}

  .empty {{
    max-width: 600px;
    margin: 60px auto;
    padding: 30px;
    background: #fff;
    border-radius: 8px;
    text-align: center;
    font-size: 16px;
    line-height: 1.5;
  }}

  @media print {{
    body {{ background: #fff; }}
    .info {{ display: none; }}
    .page {{
      margin: 0;
      padding: 0;
      width: auto;
      box-shadow: none;
      page-break-after: always;
    }}
    .page:last-child {{ page-break-after: auto; }}
  }}
</style>
</head>
<body>
  <div class="info">
    <b>Card Print Sheet</b> &mdash; {total} card(s) across {num_pages} page(s).
    Trim size <b>{CARD_W_MM:g}&times;{CARD_H_MM:g} mm</b>,
    {"bleed auto-detected &amp; trimmed to the exact card edge" if AUTO_BLEED else f"{BLEED_MM:g} mm bleed trimmed each edge"},
    {"cards butted together" if GAP_MM == 0 else f"{GAP_MM:g} mm gap"}, {COLS}&times;{ROWS} per page.
    {"&nbsp;|&nbsp; <b>To cut:</b> align a straightedge between a top tick and its matching bottom tick (or left/right) and cut straight through the whole sheet on each grid line." if EDGE_TICKS else ""}
    &nbsp;|&nbsp; Print with <b>Cmd+P</b>, scale <b>100%</b>, margins <b>Default/None</b>.
  </div>
  {debug_banner}
  {"".join(pages_html)}
</body>
</html>
"""
    return html


def main():
    images = find_images(CARDS_DIR)
    html = build_html(images)
    OUTPUT_FILE.write_text(html, encoding="utf-8")

    if DEBUG_MODE:
        print("=== DEBUG / printer-setup mode ON ===")
        print(f"Grid: {ROWS} rows x {COLS} cols. Slots use (row, col), "
              "row 0 = top, col 0 = left.")
        _, placements = build_debug_page(images)
        placed = 0
        for r, c, img in placements:
            if img is not None:
                placed += 1
                print(f"  slot (row {r}, col {c}) -> {img.name}")
        # Report any requested slots that couldn't be filled.
        for (r, c), val in DEBUG_SLOTS.items():
            if not (0 <= r < ROWS and 0 <= c < COLS):
                print(f"  !! slot (row {r}, col {c}) is outside the "
                      f"{ROWS}x{COLS} grid -- ignored")
            elif resolve_slot_image(val, images) is None:
                print(f"  !! slot (row {r}, col {c}) value {val!r} matched "
                      "no image -- left blank")
        print(f"Placed {placed} card(s) on 1 page.")
        print(f"\nWrote: {OUTPUT_FILE}")
        print("Open it in your browser and print (Cmd+P).")
        return

    mode = "AUTO (per-image)" if AUTO_BLEED else f"FIXED {BLEED_MM:g} mm"
    print(f"Bleed mode: {mode}. Trim target: "
          f"{CARD_W_MM:g}x{CARD_H_MM:g} mm.")
    print(f"Found {len(images)} image(s) in: {CARDS_DIR}")
    for img in images:
        full_w, full_h, bleed = compute_full_size(img)
        print(f"  - {img.name}  ->  bleed {bleed:.2f} mm/edge "
              f"(display {full_w:.1f}x{full_h:.1f} mm)")
    print(f"\nWrote: {OUTPUT_FILE}")
    print("Open it in your browser and print (Cmd+P).")


if __name__ == "__main__":
    main()
