#!/usr/bin/env python3
"""Build data/geo.js: land, eight basin polygons and seabed depth bands.

Inputs are Natural Earth 1:10m vectors (public domain), downloaded on first run.
Basin outlines are hand-set limit polygons (after the IHO sea-area limits, see
LIMITS below) intersected with the Natural Earth coastline, so they follow the
real shore instead of a drawn approximation.

    pip install shapely
    python3 scripts/build_geo.py [--src DIR]
"""
import argparse
import json
import math
import os
import urllib.request

import shapely
from shapely.geometry import box, shape, Polygon
from shapely.ops import polylabel, unary_union

NE = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/"
BBOX = (-10.0, 25.0, 39.0, 51.0)  # lon0, lat0, lon1, lat1
# Natural Earth bands are cumulative ("deeper than N m"); the 5,000 m band is empty here.
BATHY = [("K_200", 200), ("J_1000", 1000), ("I_2000", 2000),
         ("H_3000", 3000), ("G_4000", 4000)]
LAND_TOL, BATHY_TOL, BASIN_TOL = 0.008, 0.02, 0.008

# Limit polygons, in processing order: earlier basins win where they overlap.
# Vertices run across land wherever possible, so only the sea is clipped.
LIMITS = [
    ("alboran", [(-5.6, 34.8), (-5.6, 37.2), (-2.19, 37.2), (-2.19, 36.72),
                 (-1.27, 35.6), (-1.27, 34.8)]),
    ("ligurian", [(6.5, 43.0), (11.0, 43.0), (11.0, 45.0), (6.5, 45.0)]),
    ("tyrrhenian", [(9.4, 43.0), (12.0, 43.0), (13.4, 42.0), (15.0, 41.0), (16.3, 40.0),
                    (16.3, 38.3), (15.62, 38.2), (15.0, 37.7), (13.5, 37.6), (12.55, 37.75),
                    (12.4, 37.8), (8.85, 38.85), (9.0, 39.5), (9.0, 41.3), (9.2, 42.5)]),
    ("aegean", [(22.0, 42.0), (26.65, 42.0), (26.65, 40.4), (27.4, 39.9), (29.0, 37.5),
                (28.4, 36.8), (28.1, 36.2), (27.5, 35.7), (26.9, 35.4), (26.2, 35.2),
                (23.5, 35.3), (23.1, 36.4), (22.6, 37.0), (22.6, 37.8), (22.97, 37.93),
                (22.4, 39.0)]),
    ("adriatic", [(18.2, 40.2), (18.36, 39.8), (19.4, 40.45), (21.5, 40.45), (21.5, 46.5),
                  (11.0, 46.5), (11.5, 44.5), (12.9, 43.5), (13.5, 42.0), (16.0, 41.0),
                  (17.0, 40.8)]),
    ("balearic", [(-1.27, 29.0), (-1.27, 35.6), (-2.19, 36.72), (-2.19, 41.5), (2.0, 43.6),
                  (6.5, 43.6), (6.5, 43.0), (9.4, 43.0), (9.2, 42.5), (9.0, 41.3),
                  (9.0, 39.5), (8.85, 38.85), (12.4, 37.8), (11.1, 37.07), (11.1, 29.0)]),
    ("ionian", [(11.1, 29.0), (11.1, 40.5), (22.6, 40.5), (22.6, 29.0)]),
    ("levantine", [(22.6, 30.5), (39.0, 30.5), (39.0, 37.3), (22.6, 37.3)]),
]
NAMES = {"alboran": "Alboran Sea", "balearic": "Balearic Sea", "ligurian": "Ligurian Sea",
         "tyrrhenian": "Tyrrhenian Sea", "adriatic": "Adriatic Sea", "ionian": "Ionian Sea",
         "aegean": "Aegean Sea", "levantine": "Levantine Sea"}
# Label anchors where the pole of inaccessibility lands somewhere awkward.
LABEL_OVERRIDE = {"balearic": (3.2, 39.3), "ionian": (18.6, 35.4), "levantine": (30.0, 33.8)}


def fetch(src, name):
    path = os.path.join(src, name + ".geojson")
    if not os.path.exists(path):
        os.makedirs(src, exist_ok=True)
        print("downloading", name)
        urllib.request.urlretrieve(NE + name + ".geojson", path)
    with open(path) as fh:
        return json.load(fh)


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
    """Drop specks and round vertices to ~100 m."""
    g = shapely.set_precision(g, 0.001)  # snap to the output grid, keeping the geometry valid
    assert g.is_valid, "invalid geometry after snapping"
    keep = [p for p in pieces(g) if p.geom_type == "Polygon" and p.area >= min_area]
    out = []
    for p in keep:
        rings = [[(round(x, 3), round(y, 3)) for x, y in p.exterior.coords]]
        for r in p.interiors:
            if Polygon(r).area >= min_area:
                rings.append([(round(x, 3), round(y, 3)) for x, y in r.coords])
        out.append(rings)
    return {"type": "MultiPolygon", "coordinates": out}


def km2(g):
    """Area in km2 using a cos(lat) equal-area approximation per piece."""
    total = 0.0
    for p in pieces(g):
        lat = math.radians(p.centroid.y)
        total += p.area * 111.32 * 111.32 * math.cos(lat)
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=os.path.join(os.environ.get("TMPDIR", "/tmp"), "ne-src"))
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "data", "geo.js"))
    a = ap.parse_args()
    bb = box(*BBOX)

    land = union_of(fetch(a.src, "ne_10m_land"), bb).simplify(LAND_TOL)
    water = bb.difference(land)

    basins = []
    taken = Polygon()
    for bid, pts in LIMITS:
        g = Polygon(pts).intersection(water).difference(taken)
        taken = taken.union(g)
        g = g.simplify(BASIN_TOL)
        main_piece = max(pieces(g), key=lambda p: p.area)
        lab = LABEL_OVERRIDE.get(bid) or tuple(polylabel(main_piece, tolerance=0.02).coords[0])
        b = g.bounds
        basins.append({
            "type": "Feature",
            "properties": {"id": bid, "name": NAMES[bid], "label": [round(lab[0], 3), round(lab[1], 3)],
                           "bounds": [round(v, 2) for v in b], "area_km2": round(km2(g))},
            "geometry": clean(g, 0.002),
        })
        print("%-10s %8d km2  label %s" % (bid, km2(g), tuple(round(v, 2) for v in lab)))

    bands = []
    for name, depth in BATHY:
        g = union_of(fetch(a.src, "ne_10m_bathymetry_" + name), bb).simplify(BATHY_TOL)
        bands.append({"type": "Feature", "properties": {"depth": depth},
                      "geometry": clean(g, 0.02)})

    geo = {
        "land": {"type": "Feature", "properties": {}, "geometry": clean(land, 0.004)},
        "basins": {"type": "FeatureCollection", "features": basins},
        "bathy": {"type": "FeatureCollection", "features": bands},
    }
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w") as fh:
        fh.write("/* generated by scripts/build_geo.py from Natural Earth 1:10m; do not edit */\n")
        fh.write("window.MEDGEO=" + json.dumps(geo, separators=(",", ":")) + ";\n")
    print("wrote", os.path.abspath(a.out), os.path.getsize(a.out) // 1024, "KB")


if __name__ == "__main__":
    main()
