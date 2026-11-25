"""Build data/live.json: recent Argo floats and a per-basin sea-surface heat watch.

Runs in the Pages deploy job (on every push and once a day), so the live file is
never committed. Each half is independent: if one source fails, the other is still
written, and the page hides whatever is missing.

  python scripts/build_live.py            # both parts (heat needs Copernicus secrets)
  python scripts/build_live.py --no-heat  # Argo only, no account needed

Argo: Ifremer ERDDAP (Argo GDAC), surface reading (top 10 dbar) of each profile in
the last 21 days. Heat: Copernicus Marine Mediterranean SST anomaly (L4, NRT, daily),
averaged over each basin outline. The alert levels approximate the marine-heatwave
idea (warm for 5 days or more); they are not the formal percentile-based definition.
"""
import csv, io, json, math, os, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "live.json")
ARGO_DAYS = 21
HEAT_DAYS = 35
HEAT_PRODUCT = "SST_MED_SST_L4_NRT_OBSERVATIONS_010_004"
HEAT_DATASET = "SST_MED_SSTA_L4_NRT_OBSERVATIONS_010_004_b"  # 1/16 degree daily anomaly
LEVELS = [(3.0, 3, "Severe"), (2.0, 2, "Strong"), (1.0, 1, "Warm")]  # degC above normal
MIN_DAYS = 5


def load_basins():
    s = open(os.path.join(ROOT, "data", "geo.js")).read()
    g = json.loads(s[s.index("{"):s.rindex("}") + 1])
    return [(f["properties"]["id"], f["geometry"]["coordinates"]) for f in g["basins"]["features"]]


def in_ring(x, y, ring):
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def basin_of(x, y, basins):
    for bid, polys in basins:
        for poly in polys:
            if in_ring(x, y, poly[0]) and not any(in_ring(x, y, h) for h in poly[1:]):
                return bid
    return None


def in_med(lon, lat):
    """Drop the Atlantic and Black Sea corners of the query box."""
    if lon < -5.45:
        return False
    if lon < 0 and lat > 40.5:  # Bay of Biscay
        return False
    if lon > 27.5 and lat > 40.95:  # Black Sea
        return False
    return True


def fetch(url, tries=3, timeout=90):
    for k in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                return r.read().decode("utf-8")
        except Exception as e:  # noqa: BLE001
            if k == tries - 1:
                raise
            print("  retry after:", e, file=sys.stderr)
            time.sleep(5 * (k + 1))


def build_argo(basins):
    q = ("platform_number,time,latitude,longitude,pres,temp"
         "&time>=now-%ddays&latitude>=30&latitude<=46&longitude>=-6&longitude<=36.5&pres<=10" % ARGO_DAYS)
    url = "https://erddap.ifremer.fr/erddap/tabledap/ArgoFloats.csv?" + urllib.parse.quote(q, safe="&=,")
    rows = list(csv.reader(io.StringIO(fetch(url))))[2:]
    prof = {}  # (float, time) -> shallowest reading
    for r in rows:
        try:
            fid, t, lat, lon, p = r[0], r[1], float(r[2]), float(r[3]), float(r[4])
            temp = float(r[5]) if r[5] not in ("", "NaN") else None
        except (ValueError, IndexError):
            continue
        if not in_med(lon, lat):
            continue
        k = (fid, t)
        if k not in prof or (temp is not None and (prof[k]["p"] > p or prof[k]["temp"] is None)):
            prof[k] = {"lat": lat, "lon": lon, "p": p, "temp": temp}
    floats = {}
    for (fid, t), v in prof.items():
        floats.setdefault(fid, []).append((t, v))
    out = []
    for fid, pts in floats.items():
        pts.sort()
        t, last = pts[-1]
        out.append({
            "id": fid,
            "time": t,
            "lat": round(last["lat"], 3),
            "lon": round(last["lon"], 3),
            "temp": None if last["temp"] is None else round(last["temp"], 2),
            "basin": basin_of(last["lon"], last["lat"], basins),
            "track": [[round(v["lon"], 3), round(v["lat"], 3)] for _, v in pts],
        })
    out.sort(key=lambda f: f["time"], reverse=True)
    return {
        "source": "Argo GDAC via Ifremer ERDDAP",
        "days": ARGO_DAYS,
        "count": len(out),
        "floats": out,
    }


def build_heat(basins):
    import numpy as np
    import copernicusmarine

    ds = copernicusmarine.open_dataset(dataset_id=HEAT_DATASET, variables=["sst_anomaly"])
    da = ds["sst_anomaly"]
    end = da["time"].values[-1]
    start = end - np.timedelta64(HEAT_DAYS - 1, "D")
    da = da.sel(time=slice(start, end)).isel(latitude=slice(None, None, 2), longitude=slice(None, None, 2)).load()
    lat = da["latitude"].values
    lon = da["longitude"].values
    days = [str(t)[:10] for t in da["time"].values]
    arr = da.values  # time, lat, lon

    lon2, lat2 = np.meshgrid(lon, lat)
    wgt = np.cos(np.radians(lat2))
    res = {}
    for bid, polys in basins:
        xs = [p[0] for poly in polys for p in poly[0]]
        ys = [p[1] for poly in polys for p in poly[0]]
        box = (lon2 >= min(xs)) & (lon2 <= max(xs)) & (lat2 >= min(ys)) & (lat2 <= max(ys))
        mask = np.zeros_like(box)
        for iy, ix in zip(*np.nonzero(box)):
            mask[iy, ix] = basin_of(float(lon2[iy, ix]), float(lat2[iy, ix]), [(bid, polys)]) is not None
        series = []
        for k in range(arr.shape[0]):
            v = arr[k][mask]
            w = wgt[mask]
            ok = np.isfinite(v)
            series.append(round(float((v[ok] * w[ok]).sum() / w[ok].sum()), 2) if ok.any() else None)
        res[bid] = summarise(series)
    return {
        "source": "Copernicus Marine, Mediterranean SST anomaly (L4, near real time)",
        "dataset": HEAT_DATASET,
        "date": days[-1],
        "start": days[0],
        "basins": res,
    }


def summarise(series):
    vals = [v for v in series if v is not None]
    latest = vals[-1] if vals else None
    level, label, streak = 0, None, 0
    for thr, lv, name in LEVELS:
        n = 0
        for v in reversed(series):
            if v is None or v < thr:
                break
            n += 1
        if n >= MIN_DAYS:
            level, label, streak = lv, name, n
            break
    warm_days = 0
    for v in reversed(series):
        if v is None or v < 1.0:
            break
        warm_days += 1
    return {
        "anom": latest,
        "level": level,
        "label": label,
        "streak": streak if level else warm_days,
        "peak": max(vals) if vals else None,
        "series": series,
    }


def main():
    basins = load_basins()
    live = {"built": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")}
    try:
        live["argo"] = build_argo(basins)
        print("Argo:", live["argo"]["count"], "floats")
    except Exception as e:  # noqa: BLE001
        print("Argo failed:", e, file=sys.stderr)
    if "--no-heat" not in sys.argv:
        try:
            live["heat"] = build_heat(basins)
            print("Heat:", live["heat"]["date"],
                  {k: (v["anom"], v["level"]) for k, v in live["heat"]["basins"].items()})
        except Exception as e:  # noqa: BLE001
            print("Heat failed:", e, file=sys.stderr)
    if len(live) == 1:
        print("Nothing built; leaving no live.json", file=sys.stderr)
        return 1
    with open(OUT, "w") as f:
        json.dump(live, f, separators=(",", ":"))
    print("Wrote", OUT, os.path.getsize(OUT), "bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
