#!/usr/bin/env python3
"""Build the map data: data/geo.js (vectors) and data/dem.js (elevation grid).

geo.js  land, the eight basin polygons (with their measured area) and the
        non-basin water ("context": Atlantic, Black Sea, Red Sea ...).
        Basins are hand-set limit polygons (after the IHO sea-area limits, see
        LIMITS) clipped to the Natural Earth 1:10m coastline.
dem.js  one 8-bit-per-channel PNG (base64) on the Web Mercator grid, used for the
        seabed view and the sea-level toggle. Red = "flood level" of the cell
        (what sea level first covers it, via priority flood from the open sea; for
        sea cells just the depth), green = flags. Elevation and bathymetry come
        from the Mapzen/AWS "terrarium" terrain tiles (SRTM, GMTED, ETOPO1/GEBCO).

    pip install shapely numpy pillow
    python3 scripts/build_data.py [--src DIR]
"""
import argparse
import base64
import heapq
import io
import json
import math
import os
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import shapely
from PIL import Image, ImageDraw
from shapely.geometry import box, shape, Polygon
from shapely.ops import polylabel, unary_union

NE = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/"
TERRARIUM = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"

# Terrain tiles at z6 (about 2 km); the shipped grid is the 2x2 mean of that.
Z = 6
TX = (30, 39)   # inclusive tile range: lon -11.25 .. 45.0
TY = (22, 27)   # lat 49.4 .. 21.9
DOWN = 2
LAND_TOL, BASIN_TOL = 0.008, 0.008
Q_RANGE = 5000.0   # metres at the end of the 8-bit scale (square-root scale, fine near 0)

LIMITS = [
    ("alboran", [(-5.6, 34.8), (-5.6, 37.2), (-2.19, 37.2), (-2.19, 36.72),
                 (-1.27, 35.6), (-1.27, 34.8)]),
    ("ligurian", [(6.5, 43.0), (11.0, 43.0), (11.0, 45.0), (6.5, 45.0)]),
    ("tyrrhenian", [(9.4, 43.0), (12.0, 43.0), (13.4, 42.0), (15.0, 41.0), (16.3, 40.0),
                    (16.3, 38.3), (15.62, 38.2), (15.0, 37.7), (13.5, 37.6), (12.55, 37.75),
                    (12.4, 37.8), (8.85, 38.85), (9.0, 39.5), (9.0, 41.3), (9.2, 42.5)]),
    ("aegean", [(22.0, 42.0), (26.65, 42.0), (26.65, 40.4), (27.4, 39.9), (29.0, 37.5),
                (28.4, 36.8), (28.1, 36.2), (27.5, 35.7), (26.9, 35.4), (26.2, 35.2),
                (23.5, 35.3), (23.1, 36.4), (22.6, 37.0), (22.6, 37.8), (23.0, 37.93),
                (23.0, 38.6), (22.4, 39.0)]),
    ("adriatic", [(18.2, 40.2), (18.36, 39.8), (19.4, 40.45), (21.5, 40.45), (21.5, 46.5),
                  (11.0, 46.5), (11.5, 44.5), (12.9, 43.5), (13.5, 42.0), (16.0, 41.0),
                  (17.0, 40.8)]),
    ("balearic", [(-1.27, 22.0), (-1.27, 35.6), (-2.19, 36.72), (-2.19, 41.5), (2.0, 43.6),
                  (6.5, 43.6), (6.5, 43.0), (9.4, 43.0), (9.2, 42.5), (9.0, 41.3),
                  (9.0, 39.5), (8.85, 38.85), (12.4, 37.8), (11.05, 37.07), (11.15, 35.25),
                  (10.2, 35.25), (10.2, 22.0)]),
    # The lobe at 22.6-23.05E takes in the Gulf of Corinth, which lies west of the canal.
    ("ionian", [(9.0, 22.0), (9.0, 40.5), (22.6, 40.5), (22.6, 38.6), (23.05, 38.6),
                (23.05, 37.85), (22.6, 37.85), (22.6, 22.0)]),
    ("levantine", [(22.6, 30.5), (46.0, 30.5), (46.0, 37.3), (22.6, 37.3)]),
]
NAMES = {"alboran": "Alboran Sea", "balearic": "Balearic Sea", "ligurian": "Ligurian Sea",
         "tyrrhenian": "Tyrrhenian Sea", "adriatic": "Adriatic Sea", "ionian": "Ionian Sea",
         "aegean": "Aegean Sea", "levantine": "Levantine Sea"}
# Label anchors where the pole of inaccessibility lands somewhere awkward.
LABEL_OVERRIDE = {"balearic": (3.2, 39.3), "ionian": (18.6, 35.4), "levantine": (30.0, 33.8)}


# ---- Web Mercator helpers -------------------------------------------------
def tile_lon(x, z):
    return x / 2 ** z * 360.0 - 180.0


def tile_lat(y, z):
    return math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / 2 ** z))))


def lonlat_to_px(lon, lat, z):
    n = 256 * 2 ** z
    x = (np.asarray(lon) + 180.0) / 360.0 * n
    y = (1 - np.arcsinh(np.tan(np.radians(lat))) / math.pi) / 2 * n
    return x, y


def fetch_json(src, name):
    path = os.path.join(src, name + ".geojson")
    if not os.path.exists(path):
        os.makedirs(src, exist_ok=True)
        print("downloading", name)
        urllib.request.urlretrieve(NE + name + ".geojson", path)
    with open(path) as fh:
        return json.load(fh)


def fetch_tile(src, z, x, y):
    path = os.path.join(src, "terrarium-%d-%d-%d.png" % (z, x, y))
    if not os.path.exists(path):
        urllib.request.urlretrieve(TERRARIUM.format(z=z, x=x, y=y), path)
    return path


def union_of(fc, bb):
    parts = []
    for f in fc["features"]:
        g = shape(f["geometry"])
        if not g.is_valid:
            g = g.buffer(0)
        if g.intersects(bb):
            parts.append(g.intersection(bb))
    return unary_union(parts)


def pieces(g):
    return list(g.geoms) if hasattr(g, "geoms") else [g]


def clean(g, min_area):
    """Snap to a 100 m grid (keeps validity) and drop specks."""
    g = shapely.set_precision(g, 0.001)
    assert g.is_valid, "invalid geometry after snapping"
    out = []
    for p in pieces(g):
        if p.geom_type != "Polygon" or p.area < min_area:
            continue
        rings = [[(round(x, 3), round(y, 3)) for x, y in p.exterior.coords]]
        for r in p.interiors:
            if Polygon(r).area >= min_area:
                rings.append([(round(x, 3), round(y, 3)) for x, y in r.coords])
        out.append(rings)
    return {"type": "MultiPolygon", "coordinates": out}


def rasterise(geom, z, x0, y0, w, h, ss=1):
    """Coverage (0..1) of a lon/lat geometry on the Mercator pixel grid."""
    img = Image.new("L", (w * ss, h * ss), 0)
    dr = ImageDraw.Draw(img)
    for p in pieces(geom):
        if p.geom_type != "Polygon":
            continue
        for ring, fill in [(p.exterior, 255)] + [(r, 0) for r in p.interiors]:
            c = np.asarray(ring.coords)
            px, py = lonlat_to_px(c[:, 0], c[:, 1], z)
            pts = list(zip(((px - x0) * ss).tolist(), ((py - y0) * ss).tolist()))
            if len(pts) >= 3:
                dr.polygon(pts, fill=fill)
    a = np.asarray(img, dtype=np.float32) / 255.0
    if ss > 1:
        a = a.reshape(h, ss, w, ss).mean(axis=(1, 3))
    return a


def quant(v):
    """Metres -> 8-bit code on a signed square-root scale (finest near 0)."""
    v = np.asarray(v, dtype=np.float64)
    t = np.sign(v) * np.sqrt(np.minimum(np.abs(v), Q_RANGE) / Q_RANGE)
    return np.clip(np.round(128 + 127.5 * t), 0, 255).astype(np.uint8)


def dequant(c):
    t = (np.asarray(c, dtype=np.float64) - 128) / 127.5
    return np.sign(t) * Q_RANGE * t * t


def priority_flood(e, water0):
    """Lowest sea level at which each cell is reached by the open sea.

    Sea cells keep their own depth; land cells get max(own height, the lowest
    rim that connects them to the sea), never below ~0 m, so inland hollows
    (Dead Sea, Qattara) only flood once the sea can actually spill in.
    """
    h, w = e.shape
    fl = np.full(e.shape, np.inf)
    done = np.zeros(e.shape, dtype=bool)
    heap = []
    sea = np.minimum(e, 0.0)
    ys, xs = np.nonzero(water0)
    for y, x in zip(ys.tolist(), xs.tolist()):
        fl[y, x] = sea[y, x]
        heap.append((sea[y, x], y * w + x))
    heapq.heapify(heap)
    fl_flat, e_flat, done_flat = fl.ravel(), e.ravel(), done.ravel()
    while heap:
        f, i = heapq.heappop(heap)
        if done_flat[i]:
            continue
        done_flat[i] = True
        y, x = divmod(i, w)
        for dy in (-1, 0, 1):
            ny = y + dy
            if ny < 0 or ny >= h:
                continue
            for dx in (-1, 0, 1):
                nx = x + dx
                if (dy == 0 and dx == 0) or nx < 0 or nx >= w:
                    continue
                j = ny * w + nx
                if done_flat[j]:
                    continue
                nf = max(f, e_flat[j], 0.25)
                if nf < fl_flat[j]:
                    fl_flat[j] = nf
                    heapq.heappush(heap, (nf, j))
    return fl


def main():
    ap = argparse.ArgumentParser()
    tmp = os.environ.get("TMPDIR", "/tmp")
    ap.add_argument("--src", default=os.path.join(tmp, "ne-src"))
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "data"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    # ---- region (tile edges) ----
    west, east = tile_lon(TX[0], Z), tile_lon(TX[1] + 1, Z)
    north, south = tile_lat(TY[0], Z), tile_lat(TY[1] + 1, Z)
    bb = box(west, south, east, north)
    print("region lon %.3f..%.3f lat %.3f..%.3f" % (west, east, south, north))

    # ---- vectors ----
    land = union_of(fetch_json(a.src, "ne_10m_land"), bb).simplify(LAND_TOL)
    water = bb.difference(land)
    basins, taken = [], Polygon()
    polys = {}
    for bid, pts in LIMITS:
        g = Polygon(pts).intersection(water).difference(taken)
        taken = taken.union(g)
        polys[bid] = g
    context = water.difference(taken).simplify(BASIN_TOL)

    # ---- elevation grid: z6 tiles stitched, then 2x2 mean ----
    nx, ny = TX[1] - TX[0] + 1, TY[1] - TY[0] + 1
    jobs = [(x, y) for y in range(TY[0], TY[1] + 1) for x in range(TX[0], TX[1] + 1)]
    with ThreadPoolExecutor(8) as ex:
        paths = list(ex.map(lambda t: fetch_tile(a.src, Z, t[0], t[1]), jobs))
    full = np.zeros((ny * 256, nx * 256), dtype=np.float32)
    for (x, y), pth in zip(jobs, paths):
        rgb = np.asarray(Image.open(pth).convert("RGB"), dtype=np.float32)
        full[(y - TY[0]) * 256:(y - TY[0] + 1) * 256, (x - TX[0]) * 256:(x - TX[0] + 1) * 256] = \
            rgb[..., 0] * 256 + rgb[..., 1] + rgb[..., 2] / 256 - 32768
    H, W = full.shape
    x0, y0 = TX[0] * 256, TY[0] * 256            # pixel origin at zoom Z

    # basin stats on the full-resolution grid
    rows = np.arange(H) + y0 + 0.5
    lat_rows = np.degrees(np.arctan(np.sinh(math.pi * (1 - 2 * rows / (256 * 2 ** Z)))))
    m_per_px = 40075016.686 / (256 * 2 ** Z) * np.cos(np.radians(lat_rows))
    cell_km2 = ((m_per_px / 1000.0) ** 2)[:, None]
    feats = []
    for bid, _ in LIMITS:
        g = polys[bid]
        cov = rasterise(g, Z, x0, y0, W, H, ss=2)
        wgt = cov * cell_km2
        area = float(wgt.sum())
        depth = float((wgt * np.maximum(-full, 0)).sum() / max(wgt.sum(), 1e-9))
        gs = g.simplify(BASIN_TOL)
        main_piece = max(pieces(gs), key=lambda p: p.area)
        lab = LABEL_OVERRIDE.get(bid) or tuple(polylabel(main_piece, tolerance=0.02).coords[0])
        print("%-10s area %9d km2   mean depth %5d m   max %5d m" %
              (bid, area, depth, float(np.max(np.where(cov > 0.5, -full, 0)))))
        feats.append({"type": "Feature",
                      "properties": {"id": bid, "name": NAMES[bid], "label": [round(lab[0], 3), round(lab[1], 3)],
                                     "bounds": [round(v, 2) for v in gs.bounds],
                                     "area_km2": int(round(area, -3)), "mean_depth_m": int(round(depth, -1))},
                      "geometry": clean(gs, 0.002)})

    # shipped grid
    h, w = H // DOWN, W // DOWN
    e = full.reshape(h, DOWN, w, DOWN).mean(axis=(1, 3))
    water0 = rasterise(water, Z - 1, x0 // 2, y0 // 2, w, h, ss=4) >= 0.5

    cols = tile_lon(TX[0], Z) + (np.arange(w) + 0.5) / w * (east - west)
    lons = np.broadcast_to(cols[None, :], (h, w))
    rws = (np.arange(h) + 0.5) * DOWN + y0
    lats = np.degrees(np.arctan(np.sinh(math.pi * (1 - 2 * rws / (256 * 2 ** Z)))))[:, None]
    lats = np.broadcast_to(lats, (h, w))
    outside = water0 & ((lons < -5.55) | ((lats < 30.5) & (lons > 31.5)))

    print("priority flood on %dx%d ..." % (w, h))
    fl = priority_flood(e.astype(np.float64), water0)
    fl[~np.isfinite(fl)] = Q_RANGE
    fl[~water0] = np.maximum(fl[~water0], 0.25)

    img = np.zeros((h, w, 3), dtype=np.uint8)
    img[..., 0] = quant(fl)
    img[..., 1] = water0.astype(np.uint8) | (outside.astype(np.uint8) << 1)
    buf = io.BytesIO()
    Image.fromarray(img, "RGB").save(buf, "PNG", optimize=True)
    png = buf.getvalue()
    print("dem png %d KB (%dx%d)" % (len(png) // 1024, w, h))
    dem = {"w": w, "h": h, "bounds": [round(west, 4), round(south, 4), round(east, 4), round(north, 4)],
           "range": Q_RANGE, "png": "data:image/png;base64," + base64.b64encode(png).decode()}
    with open(os.path.join(a.out, "dem.js"), "w") as fh:
        fh.write("/* generated by scripts/build_data.py; do not edit */\nwindow.MEDDEM=" +
                 json.dumps(dem, separators=(",", ":")) + ";\n")

    geo = {
        "bounds": [round(west, 4), round(south, 4), round(east, 4), round(north, 4)],
        "land": {"type": "Feature", "properties": {}, "geometry": clean(land, 0.004)},
        "basins": {"type": "FeatureCollection", "features": feats},
        "context": {"type": "Feature", "properties": {}, "geometry": clean(context, 0.01)},
    }
    with open(os.path.join(a.out, "geo.js"), "w") as fh:
        fh.write("/* generated by scripts/build_data.py from Natural Earth 1:10m; do not edit */\n")
        fh.write("window.MEDGEO=" + json.dumps(geo, separators=(",", ":")) + ";\n")
    for n in ("geo.js", "dem.js"):
        print("wrote", n, os.path.getsize(os.path.join(a.out, n)) // 1024, "KB")


if __name__ == "__main__":
    main()
