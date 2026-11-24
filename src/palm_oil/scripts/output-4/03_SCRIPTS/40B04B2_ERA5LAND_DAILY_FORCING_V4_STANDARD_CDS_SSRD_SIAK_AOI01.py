# ============================================================
# OUTPUT 4 / 40B04B2 V4
# ERA5-LAND DAILY METEOROLOGICAL FORCING — SIAK_AOI01
# ROBUST FALLBACK: STANDARD CDS ERA5-LAND + DAILY SSRD AT 00 UTC
#
# KEY FIX
# - Stop using the ERA5-Land time-series / ARCO radiation path.
# - Retrieve ONLY surface_solar_radiation_downwards (SSRD)
#   from the standard ERA5-Land archive.
# - For ERA5-Land accumulated variables, the value time-stamped
#   at 00:00 UTC is the 24-hour accumulation for the PREVIOUS day.
# - Therefore we request only ONE timestep per day (00:00 UTC),
#   shift the date back by one day, and convert J/m² -> MJ/m²/day.
#
# BENEFIT
# - ~24x less temporal data than hourly SSRD.
# - No direct Zarr / Dask / aiohttp radiation access.
# - Existing temperature, pressure/precipitation, and wind
#   checkpoints are reused; they are NOT downloaded again.
#
# PRIMARY RAINFALL POLICY
# - CHIRPS v2 Final remains the primary rainfall forcing.
# - ERA5-Land precipitation remains diagnostic / sensitivity only.
# ============================================================

from pathlib import Path
import os
import sys
import json
import gc
import zipfile
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

RAD_DIR = WORKDIR / "climate_raw" / "era5land_ssrd_daily_cds"
RAD_DIR.mkdir(parents=True, exist_ok=True)

INPUT_CELLS = WORKDIR / "40B04A_UNIQUE_ERA5L_CELLS_SIAK_AOI01_V1.csv"

CHECKPOINTS = {
    "temperature": RAW_DIR / "40B04B2_temperature_6cells_2001_2025.nc",
    "pressure_precipitation": RAW_DIR / "40B04B2_pressure_precipitation_6cells_2001_2025.nc",
    "wind": RAW_DIR / "40B04B2_wind_6cells_2001_2025.nc",
}

OUTPUT_DAILY = WORKDIR / "40B04B2_ERA5LAND_DAILY_NATIVE_CELLS_2001_2025_SIAK_AOI01_V4.csv"
OUTPUT_CELL_QC = WORKDIR / "40B04B2_ERA5LAND_CELL_QC_SIAK_AOI01_V4.csv"
OUTPUT_MONTHLY = WORKDIR / "40B04B2_ERA5LAND_MONTHLY_NATIVE_CELLS_2001_2025_SIAK_AOI01_V4.csv"
OUTPUT_ANNUAL = WORKDIR / "40B04B2_ERA5LAND_ANNUAL_NATIVE_CELLS_2001_2025_SIAK_AOI01_V4.csv"
OUTPUT_QC_JSON = WORKDIR / "40B04B2_ERA5LAND_QC_SUMMARY_SIAK_AOI01_V4.json"

START_DATE = "2001-01-01"
END_DATE = "2025-12-31"

EXPECTED_DAYS = len(pd.date_range(START_DATE, END_DATE, freq="D"))
EXPECTED_DAILY_ROWS = EXPECTED_DAYS * 6

DATASET = "reanalysis-era5-land"

# Five-year chunks are a deliberate reliability compromise.
# Jan 1 of the next chunk supplies Dec 31 of the previous year
# after the ERA5-Land -1 day accumulation timestamp shift.
YEAR_CHUNKS = [
    (2001, 2005),
    (2006, 2010),
    (2011, 2015),
    (2016, 2020),
    (2021, 2025),
]

MONTHS = [f"{m:02d}" for m in range(1, 13)]
DAYS = [f"{d:02d}" for d in range(1, 32)]

# ------------------------------------------------------------
# 1. LOAD THE SIX LOCKED ERA5-LAND CELLS
# ------------------------------------------------------------

if not INPUT_CELLS.exists():
    raise FileNotFoundError(f"Missing input: {INPUT_CELLS}")

cells = pd.read_csv(INPUT_CELLS)

required = ["ERA5L_CELL_ID", "ERA5L_LON", "ERA5L_LAT"]
missing = [c for c in required if c not in cells.columns]
if missing:
    raise ValueError(f"Missing required columns: {missing}")

cells = (
    cells
    .drop_duplicates("ERA5L_CELL_ID")
    .sort_values(["ERA5L_LAT", "ERA5L_LON"])
    .reset_index(drop=True)
)

if len(cells) != 6:
    raise ValueError(f"Expected 6 ERA5-Land cells, found {len(cells)}")

print("====================================================")
print("40B04B2 V4 — STANDARD CDS DAILY SSRD FALLBACK")
print("====================================================")
print("Python:", sys.executable)
print("Unique ERA5-Land cells:", len(cells))
print("Period:", START_DATE, "→", END_DATE)
print("Expected final daily rows:", EXPECTED_DAILY_ROWS)

# A tight box enclosing the six locked 0.1° cells.
north = float(cells["ERA5L_LAT"].max() + 0.01)
south = float(cells["ERA5L_LAT"].min() - 0.01)
west = float(cells["ERA5L_LON"].min() - 0.01)
east = float(cells["ERA5L_LON"].max() + 0.01)
AREA = [north, west, south, east]

print("CDS area [N,W,S,E]:", AREA)

# ------------------------------------------------------------
# 2. AUDIT EXISTING SUCCESSFUL V1 CHECKPOINTS
# ------------------------------------------------------------

print("\nCheckpoint audit:")

for name, path in CHECKPOINTS.items():
    ok = path.exists() and path.stat().st_size > 0
    print(f"  {name:24s}: {'FOUND' if ok else 'MISSING'} | {path.name}")
    if not ok:
        raise FileNotFoundError(
            f"\nRequired successful V1 checkpoint missing:\n{path}"
        )

# ------------------------------------------------------------
# 3. HELPERS
# ------------------------------------------------------------

def normalize_time_name(ds):
    if "time" in ds.coords:
        return ds
    if "valid_time" in ds.coords:
        return ds.rename({"valid_time": "time"})
    raise RuntimeError(f"No time coordinate found. Coords={list(ds.coords)}")


def sat_vapor_pressure_kpa(temp_c):
    return 0.6108 * np.exp(
        (17.27 * temp_c) / (temp_c + 237.3)
    )


def first_existing(columns, candidates):
    low = {str(c).lower(): c for c in columns}
    for candidate in candidates:
        if candidate.lower() in low:
            return low[candidate.lower()]
    raise KeyError(
        f"Could not find any of {candidates}. "
        f"Available={list(columns)}"
    )


def clip_dates(df):
    return df[
        df["DATE"].between(
            pd.Timestamp(START_DATE),
            pd.Timestamp(END_DATE)
        )
    ].copy()


def open_netcdf_robust(path):
    """
    CDS 'unarchived' should return a NetCDF directly.
    This helper also tolerates a ZIP response if CDS packaging changes.
    """
    path = Path(path)

    if zipfile.is_zipfile(path):
        extract_dir = path.parent / (path.stem + "_unzipped")
        extract_dir.mkdir(exist_ok=True)

        with zipfile.ZipFile(path, "r") as zf:
            zf.extractall(extract_dir)

        nc_files = sorted(extract_dir.glob("*.nc"))
        if len(nc_files) == 0:
            raise RuntimeError(f"ZIP contains no .nc file: {path}")

        return xr.open_mfdataset(
            [str(p) for p in nc_files],
            combine="by_coords"
        )

    return xr.open_dataset(path)


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

t2m_col = first_existing(
    frame.columns,
    ["T2M_K", "t2m", "2m_temperature"]
)
d2m_col = first_existing(
    frame.columns,
    ["TD2M_K", "d2m", "2m_dewpoint_temperature"]
)

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
# 5. PRESSURE/PRECIP CHECKPOINT -> DAILY
# ------------------------------------------------------------

print("\n[2/4] Reusing pressure/precipitation checkpoint...")

with xr.open_dataset(CHECKPOINTS["pressure_precipitation"]) as ds:
    ds = normalize_time_name(ds)
    frame = ds.to_dataframe().reset_index()

frame["point"] = frame["point"].astype(str)
frame["time"] = pd.to_datetime(frame["time"], utc=True)
frame["DATE"] = frame["time"].dt.floor("D").dt.tz_localize(None)

sp_col = first_existing(
    frame.columns,
    ["SP_PA", "sp", "surface_pressure"]
)
tp_col = first_existing(
    frame.columns,
    ["TP_M_HOURLY", "tp", "total_precipitation"]
)

frame["SP_PA_X"] = pd.to_numeric(frame[sp_col], errors="coerce")
frame["TP_M_X"] = pd.to_numeric(frame[tp_col], errors="coerce")

frame.loc[
    frame["TP_M_X"].between(-1e-10, 0),
    "TP_M_X"
] = 0.0

frame.loc[
    frame["TP_M_X"] < 0,
    "TP_M_X"
] = np.nan

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

u_col = first_existing(
    frame.columns,
    ["U10_MS", "u10", "10m_u_component_of_wind"]
)
v_col = first_existing(
    frame.columns,
    ["V10_MS", "v10", "10m_v_component_of_wind"]
)

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
# 7. RADIATION FROM STANDARD ERA5-LAND CDS
#    ONE VALUE/DAY: 00 UTC = PREVIOUS DAY'S 24-H ACCUMULATION
# ------------------------------------------------------------

print("\n[4/4] Retrieving daily SSRD from standard ERA5-Land CDS...")
print("  Method: 00 UTC accumulated SSRD -> shift date -1 day")
print("  This avoids all direct ARCO/Zarr radiation access.")

client = cdsapi.Client()

rad_frames = []

# 7A. Five-year chunks for 2001-2025 timestamps
for y0, y1 in YEAR_CHUNKS:

    out_file = RAD_DIR / f"SSRD_00UTC_{y0}_{y1}_SIAK.nc"

    if not out_file.exists() or out_file.stat().st_size == 0:
        print(f"  requesting {y0}-{y1} ...")

        request = {
            "variable": ["surface_solar_radiation_downwards"],
            "year": [str(y) for y in range(y0, y1 + 1)],
            "month": MONTHS,
            "day": DAYS,
            "time": ["00:00"],
            "data_format": "netcdf",
            "download_format": "unarchived",
            "area": AREA,
        }

        client.retrieve(
            DATASET,
            request,
            str(out_file)
        )

        print("    downloaded:", out_file.name)
    else:
        print(f"  cached {y0}-{y1}")

    with open_netcdf_robust(out_file) as rds:

        rds = normalize_time_name(rds)

        ssrd_var = first_existing(
            list(rds.data_vars),
            ["ssrd", "surface_solar_radiation_downwards"]
        )

        # Only one timestamp/day, so conversion to DataFrame is small.
        rf = rds[[ssrd_var]].to_dataframe().reset_index()

    rf["SOURCE_TIME"] = pd.to_datetime(rf["time"])
    rf["DATE"] = rf["SOURCE_TIME"].dt.normalize() - pd.Timedelta(days=1)
    rf["SSRD_J_M2_DAY"] = pd.to_numeric(rf[ssrd_var], errors="coerce")
    rf["RAD_MJ_M2_DAY"] = rf["SSRD_J_M2_DAY"] / 1_000_000.0

    rad_frames.append(rf)

# 7B. One extra timestamp: 2026-01-01 00 UTC -> 2025-12-31
tail_file = RAD_DIR / "SSRD_00UTC_2026_01_01_SIAK.nc"

if not tail_file.exists() or tail_file.stat().st_size == 0:
    print("  requesting 2026-01-01 tail timestamp...")

    tail_request = {
        "variable": ["surface_solar_radiation_downwards"],
        "year": ["2026"],
        "month": ["01"],
        "day": ["01"],
        "time": ["00:00"],
        "data_format": "netcdf",
        "download_format": "unarchived",
        "area": AREA,
    }

    client.retrieve(
        DATASET,
        tail_request,
        str(tail_file)
    )

    print("    downloaded:", tail_file.name)
else:
    print("  cached 2026-01-01 tail timestamp")

with open_netcdf_robust(tail_file) as rds:

    rds = normalize_time_name(rds)

    ssrd_var = first_existing(
        list(rds.data_vars),
        ["ssrd", "surface_solar_radiation_downwards"]
    )

    rf = rds[[ssrd_var]].to_dataframe().reset_index()

rf["SOURCE_TIME"] = pd.to_datetime(rf["time"])
rf["DATE"] = rf["SOURCE_TIME"].dt.normalize() - pd.Timedelta(days=1)
rf["SSRD_J_M2_DAY"] = pd.to_numeric(rf[ssrd_var], errors="coerce")
rf["RAD_MJ_M2_DAY"] = rf["SSRD_J_M2_DAY"] / 1_000_000.0

rad_frames.append(rf)

# ------------------------------------------------------------
# 8. STANDARDIZE RADIATION GRID AND MAP TO 6 LOCKED CELLS
# ------------------------------------------------------------

rad_raw = pd.concat(rad_frames, ignore_index=True)

lat_col = first_existing(
    rad_raw.columns,
    ["latitude", "lat"]
)
lon_col = first_existing(
    rad_raw.columns,
    ["longitude", "lon"]
)

rad_raw["ERA5L_LAT_GRID"] = pd.to_numeric(
    rad_raw[lat_col], errors="coerce"
).round(1)

rad_raw["ERA5L_LON_GRID"] = pd.to_numeric(
    rad_raw[lon_col], errors="coerce"
).round(1)

# Keep exact target dates only.
rad_raw = clip_dates(rad_raw)

cell_lookup = cells.copy()
cell_lookup["ERA5L_LAT_GRID"] = cell_lookup["ERA5L_LAT"].round(1)
cell_lookup["ERA5L_LON_GRID"] = cell_lookup["ERA5L_LON"].round(1)

rad_daily = rad_raw.merge(
    cell_lookup[
        [
            "ERA5L_CELL_ID",
            "ERA5L_LAT_GRID",
            "ERA5L_LON_GRID",
        ]
    ],
    on=["ERA5L_LAT_GRID", "ERA5L_LON_GRID"],
    how="inner",
    validate="many_to_one",
)

rad_daily["RAD_VALID_HOURS"] = np.where(
    rad_daily["RAD_MJ_M2_DAY"].notna(),
    24,
    0
)
rad_daily["HOURS_RAD"] = rad_daily["RAD_VALID_HOURS"]

rad_daily = (
    rad_daily[
        [
            "ERA5L_CELL_ID",
            "DATE",
            "RAD_MJ_M2_DAY",
            "HOURS_RAD",
            "RAD_VALID_HOURS",
        ]
    ]
    .drop_duplicates(["ERA5L_CELL_ID", "DATE"])
    .sort_values(["ERA5L_CELL_ID", "DATE"])
    .reset_index(drop=True)
)

print("  radiation daily rows:", len(rad_daily), "/", EXPECTED_DAILY_ROWS)

if len(rad_daily) != EXPECTED_DAILY_ROWS:
    print(
        "  WARNING: radiation row count differs from expected. "
        "QC below will identify missing cells/dates."
    )

del rad_raw, rad_frames
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
    cells[
        ["ERA5L_CELL_ID", "ERA5L_LON", "ERA5L_LAT"]
    ],
    on="ERA5L_CELL_ID",
    how="left",
    validate="many_to_one",
)

daily = (
    daily
    .sort_values(["ERA5L_CELL_ID", "DATE"])
    .reset_index(drop=True)
)

print("  merged daily rows:", len(daily), "/", EXPECTED_DAILY_ROWS)

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

    full_temporal_support = (
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
        "DAYS_FULL_TEMPORAL_SUPPORT": int(full_temporal_support.sum()),

        "TMEAN_C_MEAN": float(sub["TMEAN_C"].mean()),
        "TMIN_C_MIN": float(sub["TMIN_C"].min()),
        "TMAX_C_MAX": float(sub["TMAX_C"].max()),

        "RH_MEAN_PCT_MEAN": float(sub["RH_MEAN_PCT"].mean()),
        "VPD_MEAN_KPA_MEAN": float(sub["VPD_MEAN_KPA"].mean()),
        "WIND_MEAN_MS_MEAN": float(sub["WIND_MEAN_MS"].mean()),

        "RAD_MJ_M2_DAY_MEAN": float(sub["RAD_MJ_M2_DAY"].mean()),
        "RAD_MJ_M2_DAY_MIN": float(sub["RAD_MJ_M2_DAY"].min()),
        "RAD_MJ_M2_DAY_MAX": float(sub["RAD_MJ_M2_DAY"].max()),

        "PRESSURE_HPA_MEAN": float(sub["PRESSURE_HPA"].mean()),

        "COMPLETE": bool(
            forcing_valid.sum() == EXPECTED_DAYS
            and full_temporal_support.sum() == EXPECTED_DAYS
        ),
    })

cell_qc = pd.DataFrame(qc_rows)

# Broad physical plausibility gates.
plausibility = {
    "TMEAN_C": bool(daily["TMEAN_C"].between(-10, 45).all()),
    "TMIN_C": bool(daily["TMIN_C"].between(-20, 45).all()),
    "TMAX_C": bool(daily["TMAX_C"].between(-5, 55).all()),
    "RH_MEAN_PCT": bool(daily["RH_MEAN_PCT"].between(0, 100).all()),
    "VPD_MEAN_KPA": bool((daily["VPD_MEAN_KPA"] >= 0).all()),
    "WIND_MEAN_MS": bool((daily["WIND_MEAN_MS"] >= 0).all()),
    "RAD_MJ_M2_DAY": bool(
        daily["RAD_MJ_M2_DAY"].between(0, 45).all()
    ),
    "PRESSURE_HPA": bool(
        daily["PRESSURE_HPA"].between(800, 1100).all()
    ),
    "ERA5L_RAIN_MM_DAY": bool(
        (daily["ERA5L_RAIN_MM_DAY"] >= 0).all()
    ),
}

all_complete = bool(cell_qc["COMPLETE"].all())
all_plausible = bool(all(plausibility.values()))

status = "PASS" if all_complete and all_plausible else "CHECK"

# ------------------------------------------------------------
# 11. MONTHLY + ANNUAL SUMMARIES
# ------------------------------------------------------------

daily["YEAR"] = daily["DATE"].dt.year
daily["MONTH"] = daily["DATE"].dt.month

monthly = (
    daily.groupby(
        [
            "ERA5L_CELL_ID",
            "ERA5L_LON",
            "ERA5L_LAT",
            "YEAR",
            "MONTH",
        ],
        as_index=False,
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
        [
            "ERA5L_CELL_ID",
            "ERA5L_LON",
            "ERA5L_LAT",
            "YEAR",
        ],
        as_index=False,
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
    "version": "V4_STANDARD_CDS_DAILY_SSRD",
    "status": status,

    "dataset_temperature_pressure_wind": (
        "ERA5-Land hourly ARCO time-series checkpoints"
    ),
    "dataset_radiation": "ERA5-Land standard hourly CDS archive",

    "provider": "ECMWF / Copernicus Climate Data Store",
    "period": [START_DATE, END_DATE],

    "unique_era5land_cells": int(len(cells)),
    "expected_days_per_cell": int(EXPECTED_DAYS),
    "expected_daily_rows": int(EXPECTED_DAILY_ROWS),
    "actual_daily_rows": int(len(daily)),

    "complete_cells": int(cell_qc["COMPLETE"].sum()),
    "incomplete_cells": int((~cell_qc["COMPLETE"]).sum()),
    "missing_forcing_days_total": int(
        cell_qc["MISSING_FORCING_DAYS"].sum()
    ),

    "v1_checkpoints_reused": [
        p.name for p in CHECKPOINTS.values()
    ],

    "radiation_method": (
        "Standard ERA5-Land accumulated SSRD sampled at 00 UTC. "
        "Each 00 UTC timestamp represents the 24-hour accumulation "
        "for the previous UTC day; timestamp shifted by -1 day."
    ),

    "radiation_conversion": (
        "SSRD J m-2 per previous 24 h / 1e6 -> MJ m-2 day-1"
    ),

    "primary_rainfall_policy": "CHIRPS v2 Final",
    "era5land_rainfall_role": (
        "diagnostic_crosscheck_and_sensitivity_only"
    ),

    "plausibility_checks": plausibility,

    "next_step_if_pass": (
        "40B04C merge CHIRPS primary rainfall + ERA5-Land "
        "meteorological forcing into model-ready climate store"
    ),
}

OUTPUT_QC_JSON.write_text(
    json.dumps(qc_summary, indent=2),
    encoding="utf-8"
)

print("\n====================================================")
print("40B04B2 V4 FINISHED")
print("====================================================")
print("Status:", status)
print("Daily rows:", len(daily), "/", EXPECTED_DAILY_ROWS)
print("Complete cells:", int(cell_qc["COMPLETE"].sum()), "/", len(cells))
print(
    "Missing forcing days:",
    int(cell_qc["MISSING_FORCING_DAYS"].sum())
)
print("Plausibility:", "PASS" if all_plausible else "CHECK")
print("Daily output:", OUTPUT_DAILY)
print("Cell QC:", OUTPUT_CELL_QC)
print("Monthly:", OUTPUT_MONTHLY)
print("Annual:", OUTPUT_ANNUAL)
print("QC JSON:", OUTPUT_QC_JSON)
print("====================================================")
