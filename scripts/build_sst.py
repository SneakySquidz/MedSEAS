#!/usr/bin/env python3
"""Build data/sst.png + data/sst.json: monthly Mediterranean sea-surface temperature.

Source: Copernicus Marine, Mediterranean Sea Physics Reanalysis (MEDSEA_MULTIYEAR_PHY_006_004),
monthly mean potential temperature at the surface, 1/24 degree, coarsened here to 0.25 degree.
Needs a free Copernicus Marine login (env COPERNICUSMARINE_SERVICE_USERNAME / _PASSWORD).

    pip install copernicusmarine xarray netcdf4 numpy pillow
    python3 scripts/build_sst.py [--start 1987-01] [--out data]

Output: one 8-bit grey PNG atlas (frames laid out left to right, top to bottom, 0 = land / no data,
temperature = BASE + code / SCALE) and a small JSON file describing it. Run by the
"Update SST grid" workflow, which opens a pull request; nothing is written to main directly.
"""
import argparse
import datetime
import json
import os

import numpy as np
import xarray as xr
from PIL import Image

BASE, SCALE = 8.0, 10.0           # code = round((T - 8) * 10): 8.1 .. 33.4 C, 0.1 C steps
LON, LAT = (-6.0, 36.5), (30.0, 46.0)
PRODUCT = "MEDSEA_MULTIYEAR_PHY_006_004"
VAR = "thetao"
COARSEN = 6


def monthly_temperature_datasets():
    """Dataset ids are renamed from time to time, so look them up: monthly temperature,
    the reanalysis first and any interim extension (which covers the later months) after it."""
    import copernicusmarine
    cat = copernicusmarine.describe(product_id=PRODUCT, disable_progress_bar=True)
    ids = [d.dataset_id for p in cat.products for d in p.datasets]
    print("datasets in", PRODUCT + ":", ids)
    pick = [i for i in ids if "temp" in i.lower() and "p1m" in i.lower()
            or ("tem" in i.lower() and i.lower().endswith("-m"))]
    pick.sort(key=lambda i: ("int" in i.lower(), i))
    if not pick:
        raise SystemExit("no monthly temperature dataset found among: %s" % ids)
    return pick


def fetch(dataset_id, start, end, folder):
    import copernicusmarine
    return copernicusmarine.subset(
        dataset_id=dataset_id, variables=[VAR],
        minimum_longitude=LON[0], maximum_longitude=LON[1],
        minimum_latitude=LAT[0], maximum_latitude=LAT[1],
        minimum_depth=0, maximum_depth=2,
        start_datetime=start, end_datetime=end,
        output_directory=folder, output_filename=dataset_id + ".nc", overwrite=True,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="1987-01")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "data"))
    ap.add_argument("--tmp", default=os.environ.get("TMPDIR", "/tmp") + "/sst-src")
    a = ap.parse_args()
    os.makedirs(a.tmp, exist_ok=True)
    os.makedirs(a.out, exist_ok=True)

    parts = []
    for ds in monthly_temperature_datasets():
        try:
            fetch(ds, a.start + "-01T00:00:00" if len(a.start) == 7 else a.start,
                  datetime.date.today().isoformat() + "T00:00:00", a.tmp)
            parts.append(xr.open_dataset(os.path.join(a.tmp, ds + ".nc")))
        except Exception as e:  # a dataset may have no data in the range
            print("skipping", ds, "->", e)
    if not parts:
        raise SystemExit("no data downloaded")
    ds = xr.concat(parts, dim="time")
    ds = ds.sortby("time")
    ds = ds.isel(time=~ds.get_index("time").duplicated(keep="first"))
    da = ds[VAR]
    if "depth" in da.dims:
        da = da.isel(depth=0)
    # monthly means are stamped mid-month; key them by calendar month
    months = da["time"].dt.strftime("%Y-%m").values
    da = da.coarsen(longitude=COARSEN, latitude=COARSEN, boundary="trim").mean(skipna=True)
    da = da.sortby("latitude", ascending=False)       # north at the top
    arr = da.values.astype(np.float32)                # (time, lat, lon)
    n, h, w = arr.shape
    code = np.where(np.isfinite(arr), np.clip(np.round((arr - BASE) * SCALE), 1, 255), 0).astype(np.uint8)

    cols = 24
    rows = -(-n // cols)
    atlas = np.zeros((rows * h, cols * w), dtype=np.uint8)
    for i in range(n):
        r, c = divmod(i, cols)
        atlas[r * h:(r + 1) * h, c * w:(c + 1) * w] = code[i]
    Image.fromarray(atlas, "L").save(os.path.join(a.out, "sst.png"), optimize=True)

    lon, lat = da["longitude"].values, da["latitude"].values
    dlon, dlat = float(abs(lon[1] - lon[0])), float(abs(lat[1] - lat[0]))
    meta = {
        "start": str(months[0]), "end": str(months[-1]), "n": int(n), "w": int(w), "h": int(h), "cols": cols,
        "bounds": [round(float(lon[0] - dlon / 2), 4), round(float(lat[-1] - dlat / 2), 4),
                   round(float(lon[-1] + dlon / 2), 4), round(float(lat[0] + dlat / 2), 4)],
        "base": BASE, "scale": SCALE, "source": "Copernicus Marine MEDSEA_MULTIYEAR_PHY_006_004",
        "built": datetime.date.today().isoformat(),
    }
    # the months must be consecutive for the slider to be a plain index
    ym = [(int(m[:4]), int(m[5:])) for m in months]
    assert all((b[0] * 12 + b[1]) - (a_[0] * 12 + a_[1]) == 1 for a_, b in zip(ym, ym[1:])), "gap in months"
    with open(os.path.join(a.out, "sst.json"), "w") as fh:
        json.dump(meta, fh, separators=(",", ":"))
    print("wrote", n, "months,", w, "x", h, "cells,", os.path.getsize(os.path.join(a.out, "sst.png")) // 1024, "KB")


if __name__ == "__main__":
    main()
