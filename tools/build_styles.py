#!/usr/bin/env python3
"""
Build the Corte family from the Regular master.

    pip install fonttools brotli shapely
    python tools/build_styles.py

Reads  fonts/Corte-Regular.ttf  (the master, outlines are never changed)
Writes fonts/Corte-{Regular,Italic,Bold,BoldItalic}.{ttf,woff2}

- Bold        : outlines grown outward (stems 96 -> 136, bars 96 -> ~118),
                cap height, x-height, baseline and descender stay put.
- Italic      : Regular sheared 10 degrees (a slanted roman, not redrawn).
- Bold Italic : Bold sheared 10 degrees.

Every file gets the full naming, weight/style flags, and the copyright /
Reserved Font Name / SIL OFL 1.1 notice in its `name` table.
"""
import math
import os
import sys

import numpy as np
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont, newTable
from shapely.geometry import Polygon
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "fonts")

# ---------------------------------------------------------------- metadata
FAMILY = "Corte"
VERSION = 1.101
VERSION_STR = "Version 1.101"
COPYRIGHT = (
    'Copyright (c) 2026, Hasan Ovi (https://github.com/iamovi), '
    'with Reserved Font Name "Corte".'
)
LICENSE_DESC = (
    "This Font Software is licensed under the SIL Open Font License, "
    "Version 1.1. This license is available with a FAQ at: "
    "https://openfontlicense.org"
)
LICENSE_URL = "https://openfontlicense.org"
DESCRIPTION = (
    "Corte is an original sans-serif typeface built from straight strokes, "
    "flat ends, and cut corners. It holds its shape at large sizes and stays "
    "clear in short lines of display text."
)
DESIGNER = "Hasan Ovi"
DESIGNER_URL = "https://github.com/iamovi"
VENDOR_URL = "https://iamovi.github.io/corte/"

# (file style, subfamily, weight class, bold?, italic?)
STYLES = [
    ("Regular",    "Regular",     400, False, False),
    ("Italic",     "Italic",      400, False, True),
    ("Bold",       "Bold",        700, True,  False),
    ("BoldItalic", "Bold Italic", 700, True,  True),
]

# ---------------------------------------------------------------- geometry
DX, DY = 20, 14          # horizontal / vertical growth per side for Bold
SLANT = 10               # italic angle in degrees
TAN = math.tan(math.radians(SLANT))
MITRE = 6.0
MIN_EDGE = 12            # collapse slivers shorter than this (font units)

# y-remap keeps baseline, x-height, cap height and descender where they were
_KX = [-1200 - DY, -200 - DY, -DY, 500 + DY, 700 + DY, 1700 + DY]
_KY = [-1200, -200, 0, 500, 700, 1700]


def contours(glyph):
    """Return list of point-lists (all on-curve in Corte)."""
    out, start = [], 0
    for end in glyph.endPtsOfContours:
        out.append([tuple(p) for p in glyph.coordinates[start:end + 1]])
        start = end + 1
    return out


def signed_area(pts):
    return 0.5 * sum(x0 * y1 - x1 * y0
                     for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))


def glyph_to_shape(glyph):
    outers, holes = [], []
    for pts in contours(glyph):
        poly = Polygon(pts)
        (outers if signed_area(pts) < 0 else holes).append(poly.buffer(0))
    shape = unary_union(outers)
    if holes:
        shape = shape.difference(unary_union(holes))
        # an outer contour nested inside a hole is an island, e.g. the c inside the copyright sign
        for outer in outers:
            if any(outer.within(hole) for hole in holes):
                shape = shape.union(outer)
    return shape


def embolden(shape):
    k = DX / DY
    stretched = shape.buffer(0)  # copy
    stretched = Polygon_scale(stretched, 1, k)
    grown = stretched.buffer(DX, join_style=2, mitre_limit=MITRE)
    return Polygon_scale(grown, 1, 1 / k)


def Polygon_scale(geom, sx, sy):
    from shapely import affinity
    return affinity.scale(geom, xfact=sx, yfact=sy, origin=(0, 0))


def remap_y(y):
    return float(np.interp(y, _KX, _KY))


def clean(ring_pts):
    """Round to ints, drop repeats and collinear points."""
    pts = []
    for x, y in ring_pts:
        p = (int(round(x)), int(round(y)))
        if not pts or pts[-1] != p:
            pts.append(p)
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts.pop()
    # merge vertices closer than MIN_EDGE (offset leaves 1-10 unit slivers)
    merged = True
    while merged and len(pts) > 3:
        merged = False
        for i in range(len(pts)):
            a, b = pts[i], pts[(i + 1) % len(pts)]
            if math.hypot(b[0] - a[0], b[1] - a[1]) < MIN_EDGE:
                mid = (int(round((a[0] + b[0]) / 2)), int(round((a[1] + b[1]) / 2)))
                pts[i] = mid
                pts.pop((i + 1) % len(pts))
                merged = True
                break
    changed = True
    while changed and len(pts) > 3:
        changed = False
        for i in range(len(pts)):
            a, b, c = pts[i - 1], pts[i], pts[(i + 1) % len(pts)]
            cross = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
            if cross == 0:
                pts.pop(i)
                changed = True
                break
    return pts


def shape_to_glyph(shape, transform):
    pen = TTGlyphPen(None)
    geoms = getattr(shape, "geoms", [shape])
    for poly in geoms:
        if poly.is_empty:
            continue
        poly = orient(poly.simplify(0.01), sign=-1.0)  # outer CW, holes CCW
        for ring in [poly.exterior] + list(poly.interiors):
            pts = clean([transform(x, y) for x, y in list(ring.coords)])
            if len(pts) < 3:
                continue
            pen.moveTo(pts[0])
            for p in pts[1:]:
                pen.lineTo(p)
            pen.closePath()
    return pen.glyph()


def shear_glyph(glyph):
    pen = TTGlyphPen(None)
    for pts in contours(glyph):
        pts = [(int(round(x + y * TAN)), y) for x, y in pts]
        pen.moveTo(pts[0])
        for p in pts[1:]:
            pen.lineTo(p)
        pen.closePath()
    return pen.glyph()


# ---------------------------------------------------------------- font prep
def load_master():
    return TTFont(os.path.join(FONTS, "Corte-Regular.ttf"), lazy=False)


def make_bold(font):
    """Grow the outlines of `font` in place (Regular -> Bold)."""
    glyf, hmtx = font["glyf"], font["hmtx"]
    for name in font.getGlyphOrder():
        g = glyf[name]
        adv, _ = hmtx[name]
        if g.numberOfContours == 0:
            continue
        shape = embolden(glyph_to_shape(g))
        new = shape_to_glyph(shape, lambda x, y: (x + DX, remap_y(y)))
        glyf[name] = new
        hmtx[name] = (adv + 2 * DX, 0)
    return font


def make_italic(font):
    """Shear the outlines of `font` in place."""
    for name in font.getGlyphOrder():
        g = font["glyf"][name]
        if g.numberOfContours > 0:
            font["glyf"][name] = shear_glyph(g)
    return font


def set_names(font, style, subfamily):
    full = f"{FAMILY} {subfamily}" if subfamily != "Regular" else f"{FAMILY} Regular"
    ps = f"{FAMILY}-{style}"
    records = {
        0: COPYRIGHT,
        1: FAMILY,
        2: subfamily,
        3: f"{DESIGNER}: {full}: {VERSION:.3f}",
        4: full,
        5: VERSION_STR,
        6: ps,
        8: DESIGNER,
        9: DESIGNER,
        10: DESCRIPTION,
        11: VENDOR_URL,
        12: DESIGNER_URL,
        13: LICENSE_DESC,
        14: LICENSE_URL,
    }
    name = font["name"]
    name.names = []
    for nid, text in records.items():
        name.setName(text, nid, 3, 1, 0x409)   # Windows, Unicode BMP, en-US
        name.setName(text, nid, 1, 0, 0)       # Macintosh, Roman, English


def set_flags(font, weight, bold, italic):
    os2, head, hhea, post = font["OS/2"], font["head"], font["hhea"], font["post"]

    os2.version = 4
    os2.usWeightClass = weight
    os2.usWidthClass = 5
    os2.fsType = 0                      # installable embedding (OFL)
    sel = 0x80                          # USE_TYPO_METRICS
    if italic:
        sel |= 0x01
    if bold:
        sel |= 0x20
    if not bold and not italic:
        sel |= 0x40                     # REGULAR
    os2.fsSelection = sel
    os2.achVendID = "NONE"
    # Windows/Word read these to decide which text the font can display;
    # all zeros made Word fall back to another font for plain Latin text.
    os2.ulCodePageRange1 = 0x00000001   # Latin 1 (Windows 1252)
    os2.ulCodePageRange2 = 0x00000000
    os2.sxHeight, os2.sCapHeight = 500, 700
    os2.panose.bFamilyType = 2
    os2.panose.bSerifStyle = 11
    os2.panose.bWeight = 8 if bold else 5

    head.macStyle = (1 if bold else 0) | (2 if italic else 0)
    head.fontRevision = VERSION

    post.italicAngle = float(-SLANT) if italic else 0.0
    post.isFixedPitch = 0
    if italic:
        hhea.caretSlopeRise, hhea.caretSlopeRun = 1000, int(round(1000 * TAN))
    else:
        hhea.caretSlopeRise, hhea.caretSlopeRun = 1, 0

    if "gasp" not in font:
        gasp = newTable("gasp")
        gasp.version = 1
        gasp.gaspRange = {0xFFFF: 0x000F}   # gridfit + grayscale + symmetric
        font["gasp"] = gasp


def finish(font, style):
    glyf, hmtx = font["glyf"], font["hmtx"]
    for name in font.getGlyphOrder():
        g = glyf[name]
        g.recalcBounds(glyf)
        adv, _ = hmtx[name]
        hmtx[name] = (adv, getattr(g, "xMin", 0) if g.numberOfContours else 0)
    font["OS/2"].recalcAvgCharWidth(font)

    # ascent/descent must cover every glyph in every style
    ymax = max(glyf[n].yMax for n in font.getGlyphOrder() if glyf[n].numberOfContours)
    ymin = min(glyf[n].yMin for n in font.getGlyphOrder() if glyf[n].numberOfContours)
    font["OS/2"].usWinAscent = max(950, ymax)
    font["OS/2"].usWinDescent = max(300, -ymin)

    ttf = os.path.join(FONTS, f"{FAMILY}-{style}.ttf")
    font.save(ttf)
    woff2 = TTFont(ttf)
    woff2.flavor = "woff2"
    woff2.save(os.path.join(FONTS, f"{FAMILY}-{style}.woff2"))
    return ttf


def main():
    master_bytes = os.path.getsize(os.path.join(FONTS, "Corte-Regular.ttf"))
    # every style starts from a fresh copy of the Regular master
    sources = {
        "Regular": load_master(),
        "Italic": make_italic(load_master()),
        "Bold": make_bold(load_master()),
        "BoldItalic": make_italic(make_bold(load_master())),
    }
    for style, sub, weight, is_bold, is_italic in STYLES:
        font = sources[style]
        set_names(font, style, sub)
        set_flags(font, weight, is_bold, is_italic)
        path = finish(font, style)
        print(f"wrote {os.path.relpath(path, ROOT)}  ({os.path.getsize(path)} bytes)")
    print(f"(Regular master was {master_bytes} bytes)")


if __name__ == "__main__":
    sys.exit(main())
