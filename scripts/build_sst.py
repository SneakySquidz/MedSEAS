#!/usr/bin/env python3
"""Build data/sst.png, data/sst.json and data/sst_clim.png: a light SST tracker, not a dataset.

Source: Copernicus Marine, Mediterranean Sea Physics Reanalysis (MEDSEA_MULTIYEAR_PHY_006_004),
monthly mean potential temperature at the surface, coarsened to 0.25 degree.
Needs a free Copernicus Marine login (env COPERNICUSMARINE_SERVICE_USERNAME / _PASSWORD).

Incremental on purpose:
  * the first run builds the last --years years (default 12);
  * every later run reads the existing data/sst.png, keeps every month already there
    unchanged, and only fetches months after the last one, appending them;
  * the data is fetched one year at a time, reduced straight away and the file deleted,
    so memory stays small and nothing large is ever held;
  * the 1991-2020 monthly climatology (12 frames, data/sst_clim.png) is built once and
    reused until you pass --rebuild-climatology.

    pip install copernicusmarine xarray netcdf4 numpy pillow
    python3 scripts/build_sst.py [--years 12] [--rebuild-climatology]

Run by the "Update SST grid" workflow, which opens a pull request.
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
COLS = 24
CLIM_YEARS = (1991, 2020)


def monthly_temperature_datasets():
    """Dataset ids are renamed from time to time, so look them up: monthly temperature only,
    the reanalysis first and any interim extension (later months) after it."""
    import copernicusmarine
    cat = copernicusmarine.describe(product_id=PRODUCT, disable_progress_bar=True)
    ids = [d.dataset_id for p in cat.products for d in p.datasets]
    print("datasets in", PRODUCT + ":", ids)
    low = {i: i.lower() for i in ids}
    pick = [i for i in ids if ("temp" in low[i] or "-tem-" in low[i]) and
            ("p1m" in low[i] or low[i].endswith("-m") and "p1d" not in low[i])]
    pick.sort(key=lambda i: ("int" in i.lower(), i))
    if not pick:
        raise SystemExit("no monthly temperature dataset found among: %s" % ids)
    return pick


def one_year(datasets, year, folder):
    """Monthly surface temperature for one calendar year, coarsened to 0.25 degree, or None."""
    import copernicusmarine
    for ds in datasets:
        path = os.path.join(folder, "%s-%d.nc" % (ds, year))
        try:
            copernicusmarine.subset(
                dataset_id=ds, variables=[VAR],
                minimum_longitude=LON[0], maximum_longitude=LON[1],
                minimum_latitude=LAT[0], maximum_latitude=LAT[1],
                minimum_depth=0, maximum_depth=2,
                start_datetime="%d-01-01T00:00:00" % year, end_datetime="%d-12-31T23:59:59" % year,
                output_directory=folder, output_filename=os.path.basename(path), overwrite=True,
                disable_progress_bar=True)
        except Exception as e:
            print("  %s %d: %s" % (ds, year, str(e)[:120]))
            continue
        try:
            with xr.open_dataset(path) as raw:
                da = raw[VAR]
                if "depth" in da.dims:
                    da = da.isel(depth=0)
                if da.sizes["time"] > 13:
                    raise SystemExit("%s returned %d time steps for one year; not monthly data" % (ds, da.sizes["time"]))
                da = da.coarsen(longitude=COARSEN, latitude=COARSEN, boundary="trim").mean()
                da = da.sortby("latitude", ascending=False).load()
        finally:
            if os.path.exists(path):
                os.remove(path)
        if da.sizes["time"]:
            return da
    return None


def encode(arr):
    return np.where(np.isfinite(arr), np.clip(np.round((arr - BASE) * SCALE), 1, 255), 0).astype(np.uint8)


def write_atlas(frames, path, cols):
    n, h, w = frames.shape
    rows = -(-n // cols)
    atlas = np.zeros((rows * h, cols * w), dtype=np.uint8)
    for i in range(n):
        r, c = divmod(i, cols)
        atlas[r * h:(r + 1) * h, c * w:(c + 1) * w] = frames[i]
    Image.fromarray(atlas, "L").save(path, optimize=True)


def load_existing(out):
    """Read the published atlas back into codes, so old months are kept byte for byte."""
    meta_path, png_path = os.path.join(out, "sst.json"), os.path.join(out, "sst.png")
    if not (os.path.exists(meta_path) and os.path.exists(png_path)):
        return None
    with open(meta_path) as fh:
        meta = json.load(fh)
    n, w, h, cols = meta["n"], meta["w"], meta["h"], meta["cols"]
    atlas = np.asarray(Image.open(png_path).convert("L"))
    frames = []
    for i in range(n):
        r, c = divmod(i, cols)
        frames.append(atlas[r * h:(r + 1) * h, c * w:(c + 1) * w].copy())
    months = [str(m) for m in np.array(
        [("%04d-%02d" % (int(meta["start"][:4]) + (int(meta["start"][5:]) - 1 + i) // 12,
                         (int(meta["start"][5:]) - 1 + i) % 12 + 1)) for i in range(n)])]
    print("existing:", n, "months,", meta["start"], "to", meta["end"])
    return {"meta": meta, "frames": frames, "months": months}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=int, default=12)
    ap.add_argument("--rebuild-climatology", action="store_true")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "data"))
    ap.add_argument("--tmp", default=os.environ.get("TMPDIR", "/tmp") + "/sst-src")
    a = ap.parse_args()
    os.makedirs(a.tmp, exist_ok=True)
    os.makedirs(a.out, exist_ok=True)
    datasets = monthly_temperature_datasets()
    clim_path = os.path.join(a.out, "sst_clim.png")

    # ---- months to add: the whole window on the first run, only newer months after that ----
    this_year = datetime.date.today().year
    prev = load_existing(a.out)
    if prev:
        frames, months = list(prev["frames"]), list(prev["months"])
        last = months[-1]
        years = range(int(last[:4]), this_year + 1)
    else:
        frames, months, last = [], [], None
        years = range(this_year - a.years + 1, this_year + 1)
    grid = {}
    for year in years:
        da = one_year(datasets, year, a.tmp)
        if da is None:
            print(year, "no data")
            continue
        if prev and (da.sizes["latitude"], da.sizes["longitude"]) != (prev["meta"]["h"], prev["meta"]["w"]):
            raise SystemExit("grid changed: %s vs %s" % ((da.sizes["latitude"], da.sizes["longitude"]),
                                                       (prev["meta"]["h"], prev["meta"]["w"])))
        grid = grid or {"lon": da["longitude"].values, "lat": da["latitude"].values}
        t = da["time"].dt.strftime("%Y-%m").values
        added = 0
        for i in range(da.sizes["time"]):
            if last and str(t[i]) <= last:
                continue
            frames.append(encode(da.values[i].astype(np.float32)))
            months.append(str(t[i]))
            added += 1
        print(year, added, "new months")
    if not frames:
        raise SystemExit("no data downloaded")

    # ---- 1991-2020 monthly climatology, built once ----
    if a.rebuild_climatology or not os.path.exists(clim_path):
        h, w = frames[0].shape
        tot, cnt = np.zeros((12, h, w), np.float64), np.zeros((12, h, w), np.int32)
        for year in range(CLIM_YEARS[0], CLIM_YEARS[1] + 1):
            da = one_year(datasets, year, a.tmp)
            if da is None:
                continue
            for i in range(da.sizes["time"]):
                m = int(str(da["time"].dt.strftime("%m").values[i])) - 1
                v = da.values[i].astype(np.float64)
                ok = np.isfinite(v)
                tot[m][ok] += v[ok]
                cnt[m][ok] += 1
            print("climatology", year)
        clim = np.where(cnt > 0, tot / np.maximum(cnt, 1), np.nan)
        write_atlas(np.stack([encode(c) for c in clim]), clim_path, 12)

    ym = [(int(m[:4]), int(m[5:])) for m in months]
    assert all((b[0] * 12 + b[1]) - (x[0] * 12 + x[1]) == 1 for x, b in zip(ym, ym[1:])), "gap in months"
    n, (h, w) = len(frames), frames[0].shape
    write_atlas(np.stack(frames), os.path.join(a.out, "sst.png"), COLS)
    if prev:
        bounds = prev["meta"]["bounds"]
    else:
        lon, lat = grid["lon"], grid["lat"]
        dlon, dlat = float(abs(lon[1] - lon[0])), float(abs(lat[1] - lat[0]))
        bounds = [round(float(lon[0] - dlon / 2), 4), round(float(lat[-1] - dlat / 2), 4),
                  round(float(lon[-1] + dlon / 2), 4), round(float(lat[0] + dlat / 2), 4)]
    meta = {
        "start": months[0], "end": months[-1], "n": n, "w": int(w), "h": int(h), "cols": COLS,
        "bounds": bounds,
        "base": BASE, "scale": SCALE, "clim": "sst_clim.png", "climYears": list(CLIM_YEARS),
        "source": "Copernicus Marine " + PRODUCT, "built": datetime.date.today().isoformat(),
    }
    with open(os.path.join(a.out, "sst.json"), "w") as fh:
        json.dump(meta, fh, separators=(",", ":"))
    print("wrote %d months, %dx%d cells, sst.png %d KB, sst_clim.png %d KB" % (
        n, w, h, os.path.getsize(os.path.join(a.out, "sst.png")) // 1024, os.path.getsize(clim_path) // 1024))


if __name__ == "__main__":
    main()
