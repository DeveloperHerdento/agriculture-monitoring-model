# ============================================================
# OUTPUT 4 / 40B04B2 V3
# ERA5-LAND DAILY METEOROLOGICAL FORCING
# SERVER-SIDE CDS TIMESERIES RADIATION RETRIEVAL
# SIAK_AOI01
#
# WHY V3?
# - Temperature, pressure/precipitation, and wind checkpoints from V1 are valid.
# - Direct ARCO Zarr access to the radiation-and-heat timeChunked store
#   caused MemoryError even for quarterly subsets because vectorized Zarr
#   point selection still pulled large remote chunks.
# - V3 stops accessing the radiation Zarr directly.
# - Instead, V3 asks the official CDS time-series service to prepare a
#   compact NetCDF server-side for the small 6-cell ERA5-Land area.
#
# SCIENTIFIC POLICY
# - CHIRPS v2 Final remains PRIMARY rainfall.
# - ERA5-Land precipitation remains diagnostic/sensitivity only.
# - ERA5-Land time-series accumulated parameters are already
#   de-accumulated to hourly increments by ECMWF.
# - Hourly SSRD is summed to UTC calendar day and divided by 1e6
#   -> MJ m-2 day-1.
# ============================================================

from pathlib import Path
import os
import sys
import json
import gc
import warnings

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import xarray as xr
import cdsapi

# ------------------------------------------------------------
# 0. CONFIG
# ------------------------------------------------------------

WORKDIR = Path(
    r"C:\Users\user\Documents\KERJA\SPATIAL DATA ANALYST INTERN\04_YIELD"
)
os.chdir(WORKDIR)

RAW_DIR = WORKDIR / "climate_raw" / "era5land_arco"
RAW_DIR.mkdir(parents=True, exist_ok=True)

INPUT_CELLS = WORKDIR / "40B04A_UNIQUE_ERA5L_CELLS_SIAK_AOI01_V1.csv"

CHECKPOINTS = {
    "temperature": RAW_DIR / "40B04B2_temperature_6cells_2001_2025.nc",
    "pressure_precipitation": RAW_DIR / "40B04B2_pressure_precipitation_6cells_2001_2025.nc",
    "wind": RAW_DIR / "40B04B2_wind_6cells_2001_2025.nc",
}

RADIATION_CDS_NC = RAW_DIR / "40B04B2_radiation_timeseries_CDS_6cells.nc"

OUTPUT_DAILY = WORKDIR / "40B04B2_ERA5LAND_DAILY_NATIVE_CELLS_2001_2025_SIAK_AOI01_V3.csv"
OUTPUT_CELL_QC = WORKDIR / "40B04B2_ERA5LAND_CELL_QC_SIAK_AOI01_V3.csv"
OUTPUT_MONTHLY = WORKDIR / "40B04B2_ERA5LAND_MONTHLY_NATIVE_CELLS_2001_2025_SIAK_AOI01_V3.csv"
OUTPUT_ANNUAL = WORKDIR / "40B04B2_ERA5LAND_ANNUAL_NATIVE_CELLS_2001_2025_SIAK_AOI01_V3.csv"
OUTPUT_QC_JSON = WORKDIR / "40B04B2_ERA5LAND_QC_SUMMARY_SIAK_AOI01_V3.json"

START_DATE = "2001-01-01"
END_DATE = "2025-12-31"
EXPECTED_DAYS = len(pd.date_range(START_DATE, END_DATE, freq="D"))

DATASET = "reanalysis-era5-land-timeseries"

# ------------------------------------------------------------
# 1. LOAD NATIVE CELLS
# ------------------------------------------------------------

if not INPUT_CELLS.exists():
    raise FileNotFoundError(f"Missing: {INPUT_CELLS}")

cells = pd.read_csv(INPUT_CELLS)

required = ["ERA5L_CELL_ID", "ERA5L_LON", "ERA5L_LAT"]
missing = [c for c in required if c not in cells.columns]
if missing:
    raise ValueError(f"Missing columns: {missing}")

cells = (
    cells.drop_duplicates("ERA5L_CELL_ID")
    .sort_values(["ERA5L_LAT", "ERA5L_LON"])
    .reset_index(drop=True)
)

if len(cells) != 6:
    raise ValueError(f"Expected 6 ERA5-Land cells, found {len(cells)}")

print("====================================================")
print("40B04B2 V3 — CDS SERVER-SIDE RADIATION RETRIEVAL")
print("====================================================")
print("Python:", sys.executable)
print("Unique ERA5-Land cells:", len(cells))
print("Period:", START_DATE, "→", END_DATE)

# ------------------------------------------------------------
# 2. CHECK EXISTING V1 CHECKPOINTS
# ------------------------------------------------------------

print("\nCheckpoint audit:")

for name, path in CHECKPOINTS.items():
    ok = path.exists() and path.stat().st_size > 0
    print(f"  {name:24s}: {'FOUND' if ok else 'MISSING'} | {path.name}")
    if not ok:
        raise FileNotFoundError(
            f"Required successful V1 checkpoint missing:\n{path}"
        )

# ------------------------------------------------------------
# 3. HELPERS
# ------------------------------------------------------------

def normalize_time_name(ds):
    if "time" in ds.coords:
        return ds
    if "valid_time" in ds.coords:
        return ds.rename({"valid_time": "time"})
    raise RuntimeError(f"No time coordinate. Found: {list(ds.coords)}")

def sat_vapor_pressure_kpa(temp_c):
    return 0.6108 * np.exp(
        (17.27 * temp_c) / (temp_c + 237.3)
    )

def first_existing(columns, candidates):
    low = {str(c).lower(): c for c in columns}
    for c in candidates:
        if c.lower() in low:
            return low[c.lower()]
    raise KeyError(f"Could not find any of {candidates}. Available={list(columns)}")

def clip_dates(df):
    return df[
        df["DATE"].between(
            pd.Timestamp(START_DATE),
            pd.Timestamp(END_DATE)
        )
    ].copy()

# ------------------------------------------------------------
# 4. TEMPERATURE CHECKPOINT -> DAILY
# ------------------------------------------------------------

print("\n[1/4] Reusing temperature checkpoint...")

with xr.open_dataset(CHECKPOINTS["temperature"]) as ds:
    ds = normalize_time_name(ds)
    frame = ds.to_dataframe().reset_index()

frame["point"] = frame["point"].astype(str)
frame["time"] = pd.to_datetime(frame["time"], utc=True)
frame["DATE"] = frame["time"].dt.floor("D").dt.tz_localize(None)

t2m_col = first_existing(frame.columns, ["T2M_K", "t2m", "2m_temperature"])
d2m_col = first_existing(frame.columns, ["TD2M_K", "d2m", "2m_dewpoint_temperature"])

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

temp_daily = clip_dates(temp_daily)

del frame, es, ea
gc.collect()

print("  daily rows:", len(temp_daily))

# ------------------------------------------------------------
# 5. PRESSURE + PRECIP CHECKPOINT -> DAILY
# ------------------------------------------------------------

print("\n[2/4] Reusing pressure/precipitation checkpoint...")

with xr.open_dataset(CHECKPOINTS["pressure_precipitation"]) as ds:
    ds = normalize_time_name(ds)
    frame = ds.to_dataframe().reset_index()

frame["point"] = frame["point"].astype(str)
frame["time"] = pd.to_datetime(frame["time"], utc=True)
frame["DATE"] = frame["time"].dt.floor("D").dt.tz_localize(None)

sp_col = first_existing(frame.columns, ["SP_PA", "sp", "surface_pressure"])
tp_col = first_existing(frame.columns, ["TP_M_HOURLY", "tp", "total_precipitation"])

frame["SP_PA_X"] = pd.to_numeric(frame[sp_col], errors="coerce")
frame["TP_M_X"] = pd.to_numeric(frame[tp_col], errors="coerce")

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
press_daily = clip_dates(press_daily)

del frame
gc.collect()

print("  daily rows:", len(press_daily))

# ------------------------------------------------------------
# 6. WIND CHECKPOINT -> DAILY
# ------------------------------------------------------------

print("\n[3/4] Reusing wind checkpoint...")

with xr.open_dataset(CHECKPOINTS["wind"]) as ds:
    ds = normalize_time_name(ds)
    frame = ds.to_dataframe().reset_index()

frame["point"] = frame["point"].astype(str)
frame["time"] = pd.to_datetime(frame["time"], utc=True)
frame["DATE"] = frame["time"].dt.floor("D").dt.tz_localize(None)

u_col = first_existing(frame.columns, ["U10_MS", "u10", "10m_u_component_of_wind"])
v_col = first_existing(frame.columns, ["V10_MS", "v10", "10m_v_component_of_wind"])

u = pd.to_numeric(frame[u_col], errors="coerce")
v = pd.to_numeric(frame[v_col], errors="coerce")

frame["WIND_MS"] = np.sqrt(u**2 + v**2)

wind_daily = (
    frame.groupby(["point", "DATE"], as_index=False)
    .agg(
        HOURS_WIND=("time", "count"),
        WIND_MEAN_MS=("WIND_MS", "mean"),
        WIND_VALID_HOURS=("WIND_MS", "count"),
    )
    .rename(columns={"point": "ERA5L_CELL_ID"})
)

wind_daily = clip_dates(wind_daily)

del frame, u, v
gc.collect()

print("  daily rows:", len(wind_daily))

# ------------------------------------------------------------
# 7. RADIATION — OFFICIAL CDS TIMESERIES SERVER-SIDE RETRIEVAL
# ------------------------------------------------------------

print("\n[4/4] Radiation via official CDS time-series service...")

# Small padding ensures all six native 0.1° points are included.
north = float(cells["ERA5L_LAT"].max() + 0.01)
south = float(cells["ERA5L_LAT"].min() - 0.01)
west = float(cells["ERA5L_LON"].min() - 0.01)
east = float(cells["ERA5L_LON"].max() + 0.01)

area = [north, west, south, east]

print("  CDS area [N,W,S,E]:", area)

if not RADIATION_CDS_NC.exists() or RADIATION_CDS_NC.stat().st_size == 0:
    print("  requesting server-side NetCDF...")
    print("  NOTE: CDS time-series service may return the full available time range;")
    print("        V3 filters locally to 2001-2025 after download.")

    client = cdsapi.Client()

    request = {
        "variable": ["surface_solar_radiation_downwards"],
        "data_format": "netcdf",
        "area": area,
    }

    client.retrieve(
        DATASET,
        request,
        str(RADIATION_CDS_NC)
    )

    print("  downloaded:", RADIATION_CDS_NC)
else:
    print("  using cached CDS radiation NetCDF:", RADIATION_CDS_NC.name)

# ------------------------------------------------------------
# 8. RADIATION NETCDF -> DAILY USING XARRAY FIRST
# ------------------------------------------------------------

with xr.open_dataset(RADIATION_CDS_NC) as rds:

    rds = normalize_time_name(rds)

    ssrd_var = first_existing(
        list(rds.data_vars),
        ["ssrd", "surface_solar_radiation_downwards"]
    )

    print("  SSRD variable:", ssrd_var)
    print("  source dims:", dict(rds.sizes))

    rds = rds.sel(
        time=slice(
            np.datetime64(START_DATE + "T00:00:00"),
            np.datetime64(END_DATE + "T23:00:00")
        )
    )

    ssrd = rds[ssrd_var]

    # Remove tiny numerical negatives only; substantial negatives -> NaN.
    ssrd = xr.where(
        (ssrd < 0) & (ssrd >= -1e-6),
        0.0,
        ssrd
    )
    ssrd = xr.where(ssrd < 0, np.nan, ssrd)

    # Aggregate remotely downloaded hourly values to daily BEFORE pandas conversion.
    rad_sum = ssrd.resample(time="1D").sum(skipna=True)
    rad_count = ssrd.resample(time="1D").count()

    rad_ds_daily = xr.Dataset({
        "SSRD_J_M2_DAY": rad_sum,
        "RAD_VALID_HOURS": rad_count,
    })

    rad_frame = rad_ds_daily.to_dataframe().reset_index()

# Coordinate names may be latitude/longitude or lat/lon.
lat_col = first_existing(rad_frame.columns, ["latitude", "lat"])
lon_col = first_existing(rad_frame.columns, ["longitude", "lon"])

rad_frame["DATE"] = pd.to_datetime(rad_frame["time"]).dt.normalize()

rad_frame["ERA5L_LAT_GRID"] = pd.to_numeric(
    rad_frame[lat_col], errors="coerce"
).round(1)

rad_frame["ERA5L_LON_GRID"] = pd.to_numeric(
    rad_frame[lon_col], errors="coerce"
).round(1)

rad_frame["RAD_MJ_M2_DAY"] = (
    pd.to_numeric(rad_frame["SSRD_J_M2_DAY"], errors="coerce")
    / 1_000_000.0
)

# Join returned CDS grid points to our six locked native-cell IDs.
cell_lookup = cells.copy()
cell_lookup["ERA5L_LAT_GRID"] = cell_lookup["ERA5L_LAT"].round(1)
cell_lookup["ERA5L_LON_GRID"] = cell_lookup["ERA5L_LON"].round(1)

rad_daily = rad_frame.merge(
    cell_lookup[
        ["ERA5L_CELL_ID", "ERA5L_LAT_GRID", "ERA5L_LON_GRID"]
    ],
    on=["ERA5L_LAT_GRID", "ERA5L_LON_GRID"],
    how="inner",
    validate="many_to_one",
)

rad_daily["HOURS_RAD"] = pd.to_numeric(
    rad_daily["RAD_VALID_HOURS"],
    errors="coerce"
)

rad_daily = rad_daily[
    [
        "ERA5L_CELL_ID",
        "DATE",
        "RAD_MJ_M2_DAY",
        "HOURS_RAD",
        "RAD_VALID_HOURS",
    ]
].copy()

rad_daily = (
    rad_daily.sort_values(["ERA5L_CELL_ID", "DATE"])
    .drop_duplicates(["ERA5L_CELL_ID", "DATE"])
    .reset_index(drop=True)
)

print("  radiation daily rows:", len(rad_daily))

if len(rad_daily) != EXPECTED_DAYS * len(cells):
    print(
        "  WARNING: radiation row count differs from expected:",
        len(rad_daily),
        "vs",
        EXPECTED_DAYS * len(cells)
    )

del rad_frame
gc.collect()

# ------------------------------------------------------------
# 9. MERGE DAILY TABLES
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
    daily.sort_values(["ERA5L_CELL_ID", "DATE"])
    .reset_index(drop=True)
)

print("  merged daily rows:", len(daily))

# ------------------------------------------------------------
# 10. QC
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
        "VALID_FORCING_DAYS": int(forcing_valid.sum()),
        "MISSING_FORCING_DAYS": int((~forcing_valid).sum()),
        "DAYS_ALL_GROUPS_24H": int(full_24h.sum()),

        "TMEAN_C_MEAN": float(sub["TMEAN_C"].mean()),
        "TMIN_C_MIN": float(sub["TMIN_C"].min()),
        "TMAX_C_MAX": float(sub["TMAX_C"].max()),
        "RH_MEAN_PCT_MEAN": float(sub["RH_MEAN_PCT"].mean()),
        "VPD_MEAN_KPA_MEAN": float(sub["VPD_MEAN_KPA"].mean()),
        "WIND_MEAN_MS_MEAN": float(sub["WIND_MEAN_MS"].mean()),
        "RAD_MJ_M2_DAY_MEAN": float(sub["RAD_MJ_M2_DAY"].mean()),
        "PRESSURE_HPA_MEAN": float(sub["PRESSURE_HPA"].mean()),

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

status = (
    "PASS"
    if bool(cell_qc["COMPLETE"].all()) and bool(all(plausibility.values()))
    else "CHECK"
)

# ------------------------------------------------------------
# 11. MONTHLY + ANNUAL
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
# 12. EXPORT
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
    "version": "V3_CDS_SERVER_SIDE_RADIATION",
    "status": status,
    "dataset": "ERA5-Land hourly time-series",
    "provider": "ECMWF / Copernicus Climate Data Store",
    "period": [START_DATE, END_DATE],
    "unique_era5land_cells": int(len(cells)),
    "expected_days_per_cell": int(EXPECTED_DAYS),
    "expected_daily_rows": int(EXPECTED_DAYS * len(cells)),
    "actual_daily_rows": int(len(daily)),
    "complete_cells": int(cell_qc["COMPLETE"].sum()),
    "incomplete_cells": int((~cell_qc["COMPLETE"]).sum()),
    "missing_forcing_days_total": int(cell_qc["MISSING_FORCING_DAYS"].sum()),
    "v1_checkpoints_reused": [p.name for p in CHECKPOINTS.values()],
    "radiation_retrieval": (
        "Official CDS reanalysis-era5-land-timeseries server-side NetCDF; "
        "no direct radiation Zarr access."
    ),
    "radiation_conversion": (
        "ECMWF time-series de-accumulated hourly SSRD J m-2; "
        "sum daily / 1e6 -> MJ m-2 day-1."
    ),
    "daily_boundary": "00:00-23:00 UTC",
    "primary_rainfall_policy": "CHIRPS v2 Final",
    "era5land_rainfall_role": "diagnostic_crosscheck_and_sensitivity_only",
    "plausibility_checks": plausibility,
}

OUTPUT_QC_JSON.write_text(
    json.dumps(qc_summary, indent=2),
    encoding="utf-8"
)

print("\n====================================================")
print("40B04B2 V3 FINISHED")
print("====================================================")
print("Status:", status)
print("Daily rows:", len(daily), "/", EXPECTED_DAYS * len(cells))
print("Complete cells:", int(cell_qc["COMPLETE"].sum()), "/", len(cells))
print("Missing forcing days:", int(cell_qc["MISSING_FORCING_DAYS"].sum()))
print("Plausibility:", "PASS" if all(plausibility.values()) else "CHECK")
print("Daily output:", OUTPUT_DAILY)
print("Cell QC:", OUTPUT_CELL_QC)
print("Monthly:", OUTPUT_MONTHLY)
print("Annual:", OUTPUT_ANNUAL)
print("QC JSON:", OUTPUT_QC_JSON)
print("====================================================")
