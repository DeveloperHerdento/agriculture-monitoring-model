# ============================================================
# OUTPUT 4 / 40B04B2 V2
# ERA5-LAND DAILY METEOROLOGICAL FORCING — MEMORY-SAFE RESUME
# SIAK_AOI01
#
# WHY V2?
# - V1 successfully saved temperature, pressure/precipitation, and wind
#   checkpoints for all 6 ERA5-Land cells, 2001-2025.
# - The radiation group currently resolves through a time-chunked ARCO
#   store. Loading 25 years x 6 points at once created a very large Dask
#   task graph and triggered MemoryError.
#
# V2 STRATEGY
# 1) REUSE the 3 existing NetCDF checkpoints. Do not redownload them.
# 2) Aggregate each checkpoint to DAILY immediately.
# 3) Retrieve radiation only, quarter-by-quarter.
# 4) Open radiation Zarr with chunks=None (no Dask graph).
# 5) Cache each radiation quarter as a small daily CSV.
# 6) Merge only daily tables (~54,786 rows), not >1.3M hourly rows.
#
# FINAL SCIENTIFIC POLICY
# - CHIRPS v2 Final remains PRIMARY rainfall.
# - ERA5-Land rainfall remains diagnostic/sensitivity only.
# - ERA5-Land ARCO accumulated parameters are already de-accumulated
#   to hourly increments, so hourly SSRD is summed to daily radiation.
# ============================================================

from pathlib import Path
import os
import sys
import json
import gc
import ssl
import warnings

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import certifi

# ------------------------------------------------------------
# 0. WORKDIR
# ------------------------------------------------------------

WORKDIR = Path(
    r"C:\Users\user\Documents\KERJA\SPATIAL DATA ANALYST INTERN\04_YIELD"
)
os.chdir(WORKDIR)

RAW_DIR = WORKDIR / "climate_raw" / "era5land_arco"
RAW_DIR.mkdir(parents=True, exist_ok=True)

RAD_CACHE_DIR = RAW_DIR / "radiation_daily_quarters"
RAD_CACHE_DIR.mkdir(parents=True, exist_ok=True)

INPUT_CELLS = WORKDIR / "40B04A_UNIQUE_ERA5L_CELLS_SIAK_AOI01_V1.csv"

OUTPUT_DAILY = WORKDIR / "40B04B2_ERA5LAND_DAILY_NATIVE_CELLS_2001_2025_SIAK_AOI01_V2.csv"
OUTPUT_CELL_QC = WORKDIR / "40B04B2_ERA5LAND_CELL_QC_SIAK_AOI01_V2.csv"
OUTPUT_MONTHLY = WORKDIR / "40B04B2_ERA5LAND_MONTHLY_NATIVE_CELLS_2001_2025_SIAK_AOI01_V2.csv"
OUTPUT_ANNUAL = WORKDIR / "40B04B2_ERA5LAND_ANNUAL_NATIVE_CELLS_2001_2025_SIAK_AOI01_V2.csv"
OUTPUT_QC_JSON = WORKDIR / "40B04B2_ERA5LAND_QC_SUMMARY_SIAK_AOI01_V2.json"

CHECKPOINTS = {
    "temperature": RAW_DIR / "40B04B2_temperature_6cells_2001_2025.nc",
    "pressure_precipitation": RAW_DIR / "40B04B2_pressure_precipitation_6cells_2001_2025.nc",
    "wind": RAW_DIR / "40B04B2_wind_6cells_2001_2025.nc",
}

RADIATION_URL = (
    "https://arco.datastores.ecmwf.int/"
    "cadl-arco-time-010/arco/reanalysis_era5_land/"
    "sfc-radiation-heat/timeChunked.zarr"
)

START_DATE = "2001-01-01"
END_DATE = "2025-12-31"
EXPECTED_DAYS = len(pd.date_range(START_DATE, END_DATE, freq="D"))
EXPECTED_HOURS = EXPECTED_DAYS * 24

# ------------------------------------------------------------
# 1. SSL CERTIFICATE PATCH FOR THIS WINDOWS ENVIRONMENT
# ------------------------------------------------------------

_original_create_default_context = ssl.create_default_context

def _certifi_default_context(
    purpose=ssl.Purpose.SERVER_AUTH,
    cafile=None,
    capath=None,
    cadata=None,
):
    if cafile is None and capath is None and cadata is None:
        cafile = certifi.where()
    return _original_create_default_context(
        purpose=purpose,
        cafile=cafile,
        capath=capath,
        cadata=cadata,
    )

ssl.create_default_context = _certifi_default_context

# Import aiohttp while the safe CA bundle is active.
import aiohttp  # noqa: F401

# aiohttp creates default SSL contexts at import time; restore stdlib function.
ssl.create_default_context = _original_create_default_context

import xarray as xr

print("====================================================")
print("40B04B2 V2 — MEMORY-SAFE RESUME")
print("====================================================")
print("Python:", sys.executable)
print("xarray:", xr.__version__)
print("CA bundle:", certifi.where())
print("Expected daily rows:", EXPECTED_DAYS * 6)

# ------------------------------------------------------------
# 2. CDS TOKEN FOR ARCO AUTH
# ------------------------------------------------------------

cdsrc = Path.home() / ".cdsapirc"
if not cdsrc.exists():
    raise FileNotFoundError(f"CDS credential not found: {cdsrc}")

cfg = {}
for line in cdsrc.read_text(encoding="utf-8").splitlines():
    if ":" in line:
        k, v = line.split(":", 1)
        cfg[k.strip()] = v.strip()

token = cfg.get("key")
if not token:
    raise RuntimeError("No key found in ~/.cdsapirc")

storage_options = {
    "headers": {
        "Authorization": f"Bearer {token}"
    }
}

# ------------------------------------------------------------
# 3. LOAD NATIVE CELL TABLE
# ------------------------------------------------------------

if not INPUT_CELLS.exists():
    raise FileNotFoundError(f"Missing: {INPUT_CELLS}")

cells = pd.read_csv(INPUT_CELLS)

required = ["ERA5L_CELL_ID", "ERA5L_LON", "ERA5L_LAT"]
missing = [c for c in required if c not in cells.columns]
if missing:
    raise ValueError(f"Missing columns: {missing}")

cells = (
    cells
    .drop_duplicates("ERA5L_CELL_ID")
    .sort_values("ERA5L_CELL_ID")
    .reset_index(drop=True)
)

if len(cells) != 6:
    raise ValueError(f"Expected 6 ERA5-Land cells, found {len(cells)}")

point_ids = cells["ERA5L_CELL_ID"].astype(str).tolist()
point_lons = cells["ERA5L_LON"].astype(float).to_numpy()
point_lats = cells["ERA5L_LAT"].astype(float).to_numpy()

print("Unique ERA5-Land cells:", len(cells))

# ------------------------------------------------------------
# 4. CHECK V1 CHECKPOINTS
# ------------------------------------------------------------

print("\nCheckpoint audit:")

for name, path in CHECKPOINTS.items():
    ok = path.exists() and path.stat().st_size > 0
    print(f"  {name:24s}: {'FOUND' if ok else 'MISSING'} | {path.name}")
    if not ok:
        raise FileNotFoundError(
            f"\nRequired V1 checkpoint missing:\n{path}\n"
            "Do not continue. The successful V1 checkpoint should be reused."
        )

# ------------------------------------------------------------
# 5. HELPERS
# ------------------------------------------------------------

def sat_vapor_pressure_kpa(temp_c):
    return 0.6108 * np.exp(
        (17.27 * temp_c) / (temp_c + 237.3)
    )

def normalize_time_name(ds):
    if "time" in ds.coords:
        return ds
    if "valid_time" in ds.coords:
        return ds.rename({"valid_time": "time"})
    raise RuntimeError(f"No time coordinate. Found: {list(ds.coords)}")

def resolve_var(ds, aliases):
    low = {str(v).lower(): v for v in ds.data_vars}
    for a in aliases:
        if a.lower() in low:
            return low[a.lower()]
    raise KeyError(f"Could not resolve {aliases}; variables={list(ds.data_vars)}")

def ensure_point_col(frame):
    if "point" not in frame.columns:
        raise RuntimeError(
            f"Checkpoint does not contain 'point'. Columns: {frame.columns.tolist()}"
        )
    frame["point"] = frame["point"].astype(str)
    return frame

def valid_date_filter(df):
    return df[
        df["DATE"].between(
            pd.Timestamp(START_DATE),
            pd.Timestamp(END_DATE)
        )
    ].copy()

# ------------------------------------------------------------
# 6. TEMPERATURE CHECKPOINT -> DAILY
# ------------------------------------------------------------

print("\n[1/4] Reusing temperature checkpoint...")

with xr.open_dataset(CHECKPOINTS["temperature"]) as ds:
    ds = normalize_time_name(ds)
    frame = ensure_point_col(ds.to_dataframe().reset_index())

t2m_col = "T2M_K" if "T2M_K" in frame.columns else resolve_var(
    xr.Dataset.from_dataframe(frame.set_index(["time", "point"])),
    ["t2m", "2m_temperature"]
)
d2m_col = "TD2M_K" if "TD2M_K" in frame.columns else resolve_var(
    xr.Dataset.from_dataframe(frame.set_index(["time", "point"])),
    ["d2m", "2m_dewpoint_temperature"]
)

frame["time"] = pd.to_datetime(frame["time"], utc=True)
frame["DATE"] = frame["time"].dt.floor("D").dt.tz_localize(None)

frame["T2M_C"] = pd.to_numeric(frame[t2m_col], errors="coerce") - 273.15
frame["TD2M_C"] = pd.to_numeric(frame[d2m_col], errors="coerce") - 273.15

es = sat_vapor_pressure_kpa(frame["T2M_C"])
ea = sat_vapor_pressure_kpa(frame["TD2M_C"])

frame["RH_PCT"] = np.clip(100.0 * ea / es, 0.0, 100.0)
frame["VPD_KPA"] = np.maximum(es - ea, 0.0)

temp_daily = (
    frame.groupby(["point", "DATE"], as_index=False)
    .agg(
        HOURS_TEMP=("time", "count"),
        TMEAN_C=("T2M_C", "mean"),
        TMIN_C=("T2M_C", "min"),
        TMAX_C=("T2M_C", "max"),
        TD_MEAN_C=("TD2M_C", "mean"),
        RH_MEAN_PCT=("RH_PCT", "mean"),
        VPD_MEAN_KPA=("VPD_KPA", "mean"),
        VPD_MAX_KPA=("VPD_KPA", "max"),
        T_VALID_HOURS=("T2M_C", "count"),
        TD_VALID_HOURS=("TD2M_C", "count"),
    )
    .rename(columns={"point": "ERA5L_CELL_ID"})
)

temp_daily = valid_date_filter(temp_daily)
del frame, es, ea
gc.collect()

print("  daily rows:", len(temp_daily))

# ------------------------------------------------------------
# 7. PRESSURE + PRECIP CHECKPOINT -> DAILY
# ------------------------------------------------------------

print("\n[2/4] Reusing pressure/precipitation checkpoint...")

with xr.open_dataset(CHECKPOINTS["pressure_precipitation"]) as ds:
    ds = normalize_time_name(ds)
    frame = ensure_point_col(ds.to_dataframe().reset_index())

sp_col = "SP_PA" if "SP_PA" in frame.columns else next(
    c for c in frame.columns if c.lower() in ["sp", "surface_pressure"]
)
tp_col = "TP_M_HOURLY" if "TP_M_HOURLY" in frame.columns else next(
    c for c in frame.columns if c.lower() in ["tp", "total_precipitation"]
)

frame["time"] = pd.to_datetime(frame["time"], utc=True)
frame["DATE"] = frame["time"].dt.floor("D").dt.tz_localize(None)

frame["SP_PA_X"] = pd.to_numeric(frame[sp_col], errors="coerce")
frame["TP_M_X"] = pd.to_numeric(frame[tp_col], errors="coerce")

# Remove only tiny floating-point negatives; any substantial negative becomes missing.
frame.loc[frame["TP_M_X"].between(-1e-10, 0), "TP_M_X"] = 0.0
frame.loc[frame["TP_M_X"] < 0, "TP_M_X"] = np.nan

press_daily = (
    frame.groupby(["point", "DATE"], as_index=False)
    .agg(
        HOURS_PRESS=("time", "count"),
        PRESSURE_PA=("SP_PA_X", "mean"),
        TP_M_DAY=("TP_M_X", "sum"),
        PRESSURE_VALID_HOURS=("SP_PA_X", "count"),
        TP_VALID_HOURS=("TP_M_X", "count"),
    )
    .rename(columns={"point": "ERA5L_CELL_ID"})
)

press_daily["PRESSURE_HPA"] = press_daily["PRESSURE_PA"] / 100.0
press_daily["ERA5L_RAIN_MM_DAY"] = press_daily["TP_M_DAY"] * 1000.0

press_daily = valid_date_filter(press_daily)

del frame
gc.collect()

print("  daily rows:", len(press_daily))

# ------------------------------------------------------------
# 8. WIND CHECKPOINT -> DAILY
# ------------------------------------------------------------

print("\n[3/4] Reusing wind checkpoint...")

with xr.open_dataset(CHECKPOINTS["wind"]) as ds:
    ds = normalize_time_name(ds)
    frame = ensure_point_col(ds.to_dataframe().reset_index())

u_col = "U10_MS" if "U10_MS" in frame.columns else next(
    c for c in frame.columns if c.lower() in ["u10", "10m_u_component_of_wind"]
)
v_col = "V10_MS" if "V10_MS" in frame.columns else next(
    c for c in frame.columns if c.lower() in ["v10", "10m_v_component_of_wind"]
)

frame["time"] = pd.to_datetime(frame["time"], utc=True)
frame["DATE"] = frame["time"].dt.floor("D").dt.tz_localize(None)

u = pd.to_numeric(frame[u_col], errors="coerce")
v = pd.to_numeric(frame[v_col], errors="coerce")
frame["WIND_MS"] = np.sqrt(u ** 2 + v ** 2)

wind_daily = (
    frame.groupby(["point", "DATE"], as_index=False)
    .agg(
        HOURS_WIND=("time", "count"),
        WIND_MEAN_MS=("WIND_MS", "mean"),
        WIND_VALID_HOURS=("WIND_MS", "count"),
    )
    .rename(columns={"point": "ERA5L_CELL_ID"})
)

wind_daily = valid_date_filter(wind_daily)

del frame, u, v
gc.collect()

print("  daily rows:", len(wind_daily))

# ------------------------------------------------------------
# 9. RADIATION ONLY — NO DASK, QUARTER-BY-QUARTER
# ------------------------------------------------------------

print("\n[4/4] Retrieving radiation only — memory-safe mode...")
print("  Strategy: chunks=None + quarterly cache")

# chunks=None prevents creation of the giant Dask HighLevelGraph
# that caused V1's MemoryError.
rad_ds = xr.open_zarr(
    RADIATION_URL,
    consolidated=True,
    storage_options=storage_options,
    chunks=None,
)

rad_ds = normalize_time_name(rad_ds)
ssrd_var = resolve_var(
    rad_ds,
    ["ssrd", "surface_solar_radiation_downwards"]
)

print("  SSRD variable:", ssrd_var)

lat_da = xr.DataArray(
    point_lats,
    dims="point",
    coords={"point": point_ids}
)
lon_da = xr.DataArray(
    point_lons,
    dims="point",
    coords={"point": point_ids}
)

rad_point_ds = rad_ds[[ssrd_var]].sel(
    latitude=lat_da,
    longitude=lon_da,
    method="nearest",
)

quarter_frames = []

for year in range(2001, 2026):
    for q in range(1, 5):

        start_month = (q - 1) * 3 + 1
        end_month = q * 3

        start = pd.Timestamp(year=year, month=start_month, day=1)
        end = (
            pd.Timestamp(year=year, month=end_month, day=1)
            + pd.offsets.MonthEnd(1)
            + pd.Timedelta(hours=23)
        )

        cache = RAD_CACHE_DIR / f"SSRD_DAILY_{year}_Q{q}.csv"

        if cache.exists() and cache.stat().st_size > 20:
            qdf = pd.read_csv(cache, parse_dates=["DATE"])
            quarter_frames.append(qdf)
            print(f"  cached {year} Q{q}")
            continue

        print(f"  fetching {year} Q{q} ...", end=" ")

        sub = rad_point_ds.sel(
            time=slice(
                np.datetime64(start),
                np.datetime64(end)
            )
        )

        # No Dask graph because chunks=None.
        qframe = sub.to_dataframe().reset_index()

        if "point" not in qframe.columns:
            raise RuntimeError(
                f"Radiation extraction missing point coordinate. "
                f"Columns={qframe.columns.tolist()}"
            )

        qframe["time"] = pd.to_datetime(qframe["time"], utc=True)
        qframe["DATE"] = qframe["time"].dt.floor("D").dt.tz_localize(None)

        qframe["SSRD_J_M2_HOURLY"] = pd.to_numeric(
            qframe[ssrd_var],
            errors="coerce"
        )

        qframe.loc[
            qframe["SSRD_J_M2_HOURLY"].between(-1e-6, 0),
            "SSRD_J_M2_HOURLY"
        ] = 0.0

        qframe.loc[
            qframe["SSRD_J_M2_HOURLY"] < 0,
            "SSRD_J_M2_HOURLY"
        ] = np.nan

        qdf = (
            qframe.groupby(["point", "DATE"], as_index=False)
            .agg(
                HOURS_RAD=("time", "count"),
                SSRD_J_M2_DAY=("SSRD_J_M2_HOURLY", "sum"),
                RAD_VALID_HOURS=("SSRD_J_M2_HOURLY", "count"),
            )
            .rename(columns={"point": "ERA5L_CELL_ID"})
        )

        qdf["RAD_MJ_M2_DAY"] = qdf["SSRD_J_M2_DAY"] / 1_000_000.0

        qdf.to_csv(cache, index=False, encoding="utf-8-sig")
        quarter_frames.append(qdf)

        del sub, qframe, qdf
        gc.collect()

        print("done")

try:
    rad_ds.close()
except Exception:
    pass

del rad_ds, rad_point_ds
gc.collect()

rad_daily = pd.concat(quarter_frames, ignore_index=True)
rad_daily["DATE"] = pd.to_datetime(rad_daily["DATE"])
rad_daily = valid_date_filter(rad_daily)

rad_daily = (
    rad_daily
    .sort_values(["ERA5L_CELL_ID", "DATE"])
    .drop_duplicates(["ERA5L_CELL_ID", "DATE"])
    .reset_index(drop=True)
)

print("  radiation daily rows:", len(rad_daily))

# ------------------------------------------------------------
# 10. MERGE DAILY TABLES ONLY
# ------------------------------------------------------------

print("\nMerging daily forcing tables...")

daily = temp_daily.merge(
    press_daily,
    on=["ERA5L_CELL_ID", "DATE"],
    how="outer",
    validate="one_to_one",
)

daily = daily.merge(
    wind_daily,
    on=["ERA5L_CELL_ID", "DATE"],
    how="outer",
    validate="one_to_one",
)

daily = daily.merge(
    rad_daily,
    on=["ERA5L_CELL_ID", "DATE"],
    how="outer",
    validate="one_to_one",
)

daily = daily.merge(
    cells[["ERA5L_CELL_ID", "ERA5L_LON", "ERA5L_LAT"]],
    on="ERA5L_CELL_ID",
    how="left",
    validate="many_to_one",
)

daily = (
    daily
    .sort_values(["ERA5L_CELL_ID", "DATE"])
    .reset_index(drop=True)
)

print("  merged daily rows:", len(daily))

# ------------------------------------------------------------
# 11. QC
# ------------------------------------------------------------

forcing_cols = [
    "TMEAN_C",
    "TMIN_C",
    "TMAX_C",
    "TD_MEAN_C",
    "RH_MEAN_PCT",
    "VPD_MEAN_KPA",
    "VPD_MAX_KPA",
    "WIND_MEAN_MS",
    "RAD_MJ_M2_DAY",
    "PRESSURE_HPA",
]

all_dates = pd.date_range(START_DATE, END_DATE, freq="D")
qc_rows = []

for _, c in cells.iterrows():

    cid = c["ERA5L_CELL_ID"]

    sub = (
        daily[daily["ERA5L_CELL_ID"] == cid]
        .set_index("DATE")
        .reindex(all_dates)
    )

    forcing_valid = sub[forcing_cols].notna().all(axis=1)

    full_24h = (
        (sub["HOURS_TEMP"] == 24)
        & (sub["HOURS_PRESS"] == 24)
        & (sub["HOURS_WIND"] == 24)
        & (sub["HOURS_RAD"] == 24)
    )

    qc_rows.append({
        "ERA5L_CELL_ID": cid,
        "EXPECTED_DAYS": EXPECTED_DAYS,
        "ROWS_PRESENT": int(sub["TMEAN_C"].notna().sum()),
        "DAYS_ALL_GROUPS_24H": int(full_24h.sum()),
        "VALID_FORCING_DAYS": int(forcing_valid.sum()),
        "MISSING_FORCING_DAYS": int((~forcing_valid).sum()),
        "TMEAN_C_MEAN": float(sub["TMEAN_C"].mean()),
        "TMIN_C_MIN": float(sub["TMIN_C"].min()),
        "TMAX_C_MAX": float(sub["TMAX_C"].max()),
        "RH_MEAN_PCT_MEAN": float(sub["RH_MEAN_PCT"].mean()),
        "VPD_MEAN_KPA_MEAN": float(sub["VPD_MEAN_KPA"].mean()),
        "WIND_MEAN_MS_MEAN": float(sub["WIND_MEAN_MS"].mean()),
        "RAD_MJ_M2_DAY_MEAN": float(sub["RAD_MJ_M2_DAY"].mean()),
        "PRESSURE_HPA_MEAN": float(sub["PRESSURE_HPA"].mean()),
        "ERA5L_RAIN_ANNUALIZED_MM": float(
            sub["ERA5L_RAIN_MM_DAY"].mean() * 365.25
        ),
        "COMPLETE": bool(
            forcing_valid.sum() == EXPECTED_DAYS
            and full_24h.sum() == EXPECTED_DAYS
        ),
    })

cell_qc = pd.DataFrame(qc_rows)

plausibility = {
    "TMEAN_C": bool(daily["TMEAN_C"].between(-10, 45).all()),
    "TMIN_C": bool(daily["TMIN_C"].between(-20, 45).all()),
    "TMAX_C": bool(daily["TMAX_C"].between(-5, 55).all()),
    "RH_MEAN_PCT": bool(daily["RH_MEAN_PCT"].between(0, 100).all()),
    "VPD_MEAN_KPA": bool((daily["VPD_MEAN_KPA"] >= 0).all()),
    "WIND_MEAN_MS": bool((daily["WIND_MEAN_MS"] >= 0).all()),
    "RAD_MJ_M2_DAY": bool((daily["RAD_MJ_M2_DAY"] >= 0).all()),
    "PRESSURE_HPA": bool(daily["PRESSURE_HPA"].between(800, 1100).all()),
    "ERA5L_RAIN_MM_DAY": bool((daily["ERA5L_RAIN_MM_DAY"] >= 0).all()),
}

all_complete = bool(cell_qc["COMPLETE"].all())
all_plausible = bool(all(plausibility.values()))
status = "PASS" if all_complete and all_plausible else "CHECK"

# ------------------------------------------------------------
# 12. MONTHLY / ANNUAL
# ------------------------------------------------------------

daily["YEAR"] = daily["DATE"].dt.year
daily["MONTH"] = daily["DATE"].dt.month

monthly = (
    daily.groupby(
        ["ERA5L_CELL_ID", "ERA5L_LON", "ERA5L_LAT", "YEAR", "MONTH"],
        as_index=False
    )
    .agg(
        TMEAN_C=("TMEAN_C", "mean"),
        TMIN_C=("TMIN_C", "min"),
        TMAX_C=("TMAX_C", "max"),
        RH_MEAN_PCT=("RH_MEAN_PCT", "mean"),
        VPD_MEAN_KPA=("VPD_MEAN_KPA", "mean"),
        VPD_MAX_KPA=("VPD_MAX_KPA", "max"),
        WIND_MEAN_MS=("WIND_MEAN_MS", "mean"),
        RAD_MJ_M2_MONTH=("RAD_MJ_M2_DAY", "sum"),
        PRESSURE_HPA=("PRESSURE_HPA", "mean"),
        ERA5L_RAIN_MM_MONTH=("ERA5L_RAIN_MM_DAY", "sum"),
        VALID_DAYS=("TMEAN_C", "count"),
    )
)

annual = (
    daily.groupby(
        ["ERA5L_CELL_ID", "ERA5L_LON", "ERA5L_LAT", "YEAR"],
        as_index=False
    )
    .agg(
        TMEAN_C=("TMEAN_C", "mean"),
        TMIN_C=("TMIN_C", "min"),
        TMAX_C=("TMAX_C", "max"),
        RH_MEAN_PCT=("RH_MEAN_PCT", "mean"),
        VPD_MEAN_KPA=("VPD_MEAN_KPA", "mean"),
        VPD_MAX_KPA=("VPD_MAX_KPA", "max"),
        WIND_MEAN_MS=("WIND_MEAN_MS", "mean"),
        RAD_MJ_M2_YEAR=("RAD_MJ_M2_DAY", "sum"),
        PRESSURE_HPA=("PRESSURE_HPA", "mean"),
        ERA5L_RAIN_MM_YEAR=("ERA5L_RAIN_MM_DAY", "sum"),
        VALID_DAYS=("TMEAN_C", "count"),
    )
)

# ------------------------------------------------------------
# 13. EXPORT
# ------------------------------------------------------------

final_cols = [
    "DATE",
    "ERA5L_CELL_ID",
    "ERA5L_LON",
    "ERA5L_LAT",
    "TMEAN_C",
    "TMIN_C",
    "TMAX_C",
    "TD_MEAN_C",
    "RH_MEAN_PCT",
    "VPD_MEAN_KPA",
    "VPD_MAX_KPA",
    "WIND_MEAN_MS",
    "RAD_MJ_M2_DAY",
    "PRESSURE_HPA",
    "ERA5L_RAIN_MM_DAY",
    "HOURS_TEMP",
    "HOURS_PRESS",
    "HOURS_WIND",
    "HOURS_RAD",
    "T_VALID_HOURS",
    "TD_VALID_HOURS",
    "WIND_VALID_HOURS",
    "RAD_VALID_HOURS",
    "TP_VALID_HOURS",
    "PRESSURE_VALID_HOURS",
]

daily[final_cols].to_csv(
    OUTPUT_DAILY,
    index=False,
    encoding="utf-8-sig"
)

cell_qc.to_csv(
    OUTPUT_CELL_QC,
    index=False,
    encoding="utf-8-sig"
)

monthly.to_csv(
    OUTPUT_MONTHLY,
    index=False,
    encoding="utf-8-sig"
)

annual.to_csv(
    OUTPUT_ANNUAL,
    index=False,
    encoding="utf-8-sig"
)

qc_summary = {
    "gate": "40B04B2",
    "version": "V2_MEMORY_SAFE_RESUME",
    "status": status,
    "dataset": "ERA5-Land hourly ARCO time-series",
    "provider": "ECMWF / Copernicus Climate Data Store",
    "period": [START_DATE, END_DATE],
    "unique_era5land_cells": int(len(cells)),
    "expected_days_per_cell": int(EXPECTED_DAYS),
    "expected_daily_rows": int(EXPECTED_DAYS * len(cells)),
    "actual_daily_rows": int(len(daily)),
    "complete_cells": int(cell_qc["COMPLETE"].sum()),
    "incomplete_cells": int((~cell_qc["COMPLETE"]).sum()),
    "missing_forcing_days_total": int(cell_qc["MISSING_FORCING_DAYS"].sum()),
    "v1_checkpoints_reused": [
        p.name for p in CHECKPOINTS.values()
    ],
    "radiation_strategy": (
        "Official ARCO radiation time-chunked store; opened without Dask "
        "(chunks=None) and retrieved quarter-by-quarter with local daily cache."
    ),
    "daily_boundary": "00:00-23:00 UTC",
    "primary_rainfall_policy": "CHIRPS v2 Final",
    "era5land_rainfall_role": "diagnostic_crosscheck_and_sensitivity_only",
    "radiation_conversion": (
        "ARCO de-accumulated hourly J m-2 summed by UTC day / 1e6 "
        "to MJ m-2 day-1"
    ),
    "plausibility_checks": plausibility,
    "palmsim_core_ready_variables": [
        "TMEAN_C",
        "RH_MEAN_PCT",
        "WIND_MEAN_MS",
        "RAD_MJ_M2_DAY",
    ],
    "apsim_core_ready_variables": [
        "TMIN_C",
        "TMAX_C",
        "RAD_MJ_M2_DAY",
    ],
    "rainfall_to_join_from_40B04B1": "CHIRPS RAIN_MM_DAY",
}

OUTPUT_QC_JSON.write_text(
    json.dumps(qc_summary, indent=2),
    encoding="utf-8"
)

print("\n====================================================")
print("40B04B2 V2 FINISHED")
print("====================================================")
print("Status:", status)
print("Daily rows:", len(daily), "/", EXPECTED_DAYS * len(cells))
print("Complete cells:", int(cell_qc["COMPLETE"].sum()), "/", len(cells))
print("Missing forcing days:", int(cell_qc["MISSING_FORCING_DAYS"].sum()))
print("Plausibility:", "PASS" if all_plausible else "CHECK")
print("Daily output:", OUTPUT_DAILY)
print("Cell QC:", OUTPUT_CELL_QC)
print("Monthly:", OUTPUT_MONTHLY)
print("Annual:", OUTPUT_ANNUAL)
print("QC JSON:", OUTPUT_QC_JSON)
print("====================================================")
