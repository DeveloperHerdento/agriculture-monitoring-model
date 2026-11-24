# ============================================================
# OUTPUT 4 / 40B04B2
# ERA5-LAND DAILY METEOROLOGICAL FORCING — SIAK_AOI01
# OFFICIAL ECMWF ARCO / LOCAL PYTHON
#
# INPUT
#   40B04A_UNIQUE_ERA5L_CELLS_SIAK_AOI01_V1.csv
#
# PERIOD
#   2001-01-01 through 2025-12-31
#
# OUTPUT DAILY FORCING
#   TMEAN_C, TMIN_C, TMAX_C
#   TD_MEAN_C
#   RH_MEAN_PCT
#   VPD_MEAN_KPA, VPD_MAX_KPA
#   WIND_MEAN_MS
#   RAD_MJ_M2_DAY
#   PRESSURE_HPA
#   ERA5L_RAIN_MM_DAY (diagnostic/cross-check only; CHIRPS remains primary)
#
# SCIENTIFIC POLICY
# - ERA5-Land ARCO accumulated parameters are already de-accumulated hourly.
# - Daily aggregation uses 00:00–23:00 UTC.
# - Rainfall primary for Output 4 remains CHIRPS v2 Final.
# - ERA5-Land rainfall is retained only for cross-check/sensitivity.
# ============================================================

from pathlib import Path
import os
import sys
import json
import gc
import math
import warnings

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

# ------------------------------------------------------------
# 0. CONFIG
# ------------------------------------------------------------

WORKDIR = Path(
    r"C:\Users\user\Documents\KERJA\SPATIAL DATA ANALYST INTERN\04_YIELD"
)
os.chdir(WORKDIR)

INPUT_CELLS = WORKDIR / "40B04A_UNIQUE_ERA5L_CELLS_SIAK_AOI01_V1.csv"

RAW_DIR = WORKDIR / "climate_raw" / "era5land_arco"
RAW_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_DAILY = WORKDIR / "40B04B2_ERA5LAND_DAILY_NATIVE_CELLS_2001_2025_SIAK_AOI01_V1.csv"
OUTPUT_CELL_QC = WORKDIR / "40B04B2_ERA5LAND_CELL_QC_SIAK_AOI01_V1.csv"
OUTPUT_MONTHLY = WORKDIR / "40B04B2_ERA5LAND_MONTHLY_NATIVE_CELLS_2001_2025_SIAK_AOI01_V1.csv"
OUTPUT_ANNUAL = WORKDIR / "40B04B2_ERA5LAND_ANNUAL_NATIVE_CELLS_2001_2025_SIAK_AOI01_V1.csv"
OUTPUT_QC_JSON = WORKDIR / "40B04B2_ERA5LAND_QC_SUMMARY_SIAK_AOI01_V1.json"

START = "2001-01-01T00:00:00"
END = "2025-12-31T23:00:00"

EXPECTED_DAYS = len(pd.date_range("2001-01-01", "2025-12-31", freq="D"))
EXPECTED_HOURS = EXPECTED_DAYS * 24

# Current official ECMWF ERA5-Land ARCO group endpoints.
ARCO_GROUPS = {
    "temperature": {
        "url": "https://arco.datastores.ecmwf.int/cadl-arco-geo-007/arco/reanalysis_era5_land/sfc-2m-temperature/geoChunked.zarr",
        "wanted": {
            "T2M_K": ["2m_temperature", "t2m"],
            "TD2M_K": ["2m_dewpoint_temperature", "d2m"],
        },
    },
    "pressure_precipitation": {
        "url": "https://arco.datastores.ecmwf.int/cadl-arco-geo-009/arco/reanalysis_era5_land/sfc-pressure-precipitation/geoChunked.zarr",
        "wanted": {
            "SP_PA": ["surface_pressure", "sp"],
            "TP_M_HOURLY": ["total_precipitation", "tp"],
        },
    },
    "wind": {
        "url": "https://arco.datastores.ecmwf.int/cadl-arco-geo-008/arco/reanalysis_era5_land/sfc-wind/geoChunked.zarr",
        "wanted": {
            "U10_MS": ["10m_u_component_of_wind", "u10"],
            "V10_MS": ["10m_v_component_of_wind", "v10"],
        },
    },
    # ECMWF current documentation exposes this endpoint for radiation/heat.
    "radiation": {
        "url": "https://arco.datastores.ecmwf.int/cadl-arco-time-010/arco/reanalysis_era5_land/sfc-radiation-heat/timeChunked.zarr",
        "wanted": {
            "SSRD_J_M2_HOURLY": ["surface_solar_radiation_downwards", "ssrd"],
        },
    },
}

# ------------------------------------------------------------
# 1. PACKAGE CHECK
# ------------------------------------------------------------

required_modules = ["xarray", "zarr", "fsspec", "aiohttp"]
missing_modules = []

for mod in required_modules:
    try:
        __import__(mod)
    except Exception:
        missing_modules.append(mod)

if missing_modules:
    print("\nERROR: package untuk akses ERA5-Land ARCO belum lengkap.")
    print("Missing:", ", ".join(missing_modules))
    print("\nDi Anaconda Prompt dengan copernicus_env aktif jalankan:")
    print("conda install -c conda-forge xarray zarr fsspec aiohttp")
    print("\nSetelah selesai: restart Jupyter kernel lalu run script ini lagi.")
    raise SystemExit(1)

import xarray as xr

print("====================================================")
print("40B04B2 — ERA5-LAND DAILY METEOROLOGICAL FORCING")
print("====================================================")
print("Python:", sys.executable)
print("xarray:", xr.__version__)
print("Period:", START, "→", END)

# ------------------------------------------------------------
# 2. READ CDS TOKEN
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
    raise RuntimeError("No 'key:' value found in ~/.cdsapirc")

storage_options = {
    "headers": {
        "Authorization": f"Bearer {token}"
    }
}

print("CDS credential: FOUND")
print("Credential path:", cdsrc)

# ------------------------------------------------------------
# 3. LOAD 6 ERA5-LAND NATIVE CELLS
# ------------------------------------------------------------

if not INPUT_CELLS.exists():
    raise FileNotFoundError(f"Missing input: {INPUT_CELLS}")

cells = pd.read_csv(INPUT_CELLS)

required = ["ERA5L_CELL_ID", "ERA5L_LON", "ERA5L_LAT"]
missing = [c for c in required if c not in cells.columns]

if missing:
    raise ValueError(f"Missing columns in {INPUT_CELLS.name}: {missing}")

cells = (
    cells
    .drop_duplicates(subset=["ERA5L_CELL_ID"])
    .sort_values("ERA5L_CELL_ID")
    .reset_index(drop=True)
)

print("Unique ERA5-Land cells:", len(cells))

if len(cells) != 6:
    print(
        "WARNING: 40B04A previously returned 6 unique ERA5-Land cells; "
        f"current file contains {len(cells)}."
    )

point_ids = cells["ERA5L_CELL_ID"].astype(str).tolist()
point_lons = cells["ERA5L_LON"].astype(float).to_numpy()
point_lats = cells["ERA5L_LAT"].astype(float).to_numpy()

# ------------------------------------------------------------
# 4. HELPERS
# ------------------------------------------------------------

def detect_variable(ds, aliases):
    """
    Resolve current Zarr variable names robustly.
    """
    data_vars = list(ds.data_vars)
    lower = {str(v).lower(): v for v in data_vars}

    for alias in aliases:
        if alias.lower() in lower:
            return lower[alias.lower()]

    # Fallback through long_name / standard_name metadata.
    for var in data_vars:
        attrs_text = " ".join(
            str(ds[var].attrs.get(k, ""))
            for k in ["long_name", "standard_name", "description"]
        ).lower()

        for alias in aliases:
            normalized = alias.lower().replace("_", " ")
            if normalized in attrs_text:
                return var

    raise KeyError(
        f"Could not resolve aliases {aliases}. "
        f"Available data variables: {data_vars}"
    )


def point_select(ds):
    """
    Vectorised nearest-neighbour point extraction.
    Produces dimensions [time, point] instead of a lat-lon Cartesian product.
    """
    if "latitude" not in ds.coords or "longitude" not in ds.coords:
        raise RuntimeError(
            f"Expected latitude/longitude coordinates. Found: {list(ds.coords)}"
        )

    lat_da = xr.DataArray(point_lats, dims="point", coords={"point": point_ids})
    lon_da = xr.DataArray(point_lons, dims="point", coords={"point": point_ids})

    return ds.sel(
        latitude=lat_da,
        longitude=lon_da,
        method="nearest",
    )


def normalize_time_name(ds):
    if "time" in ds.coords:
        return ds
    if "valid_time" in ds.coords:
        return ds.rename({"valid_time": "time"})
    raise RuntimeError(f"No time coordinate found. Coords: {list(ds.coords)}")


def extract_group(group_name, cfg):
    """
    Open one official ARCO group, extract the six native grid points and
    exact 2001–2025 time window, then return tidy [time, point] DataFrame.
    """
    print("\n----------------------------------------------------")
    print("Opening:", group_name)
    print("----------------------------------------------------")

    ds = xr.open_zarr(
        cfg["url"],
        consolidated=True,
        storage_options=storage_options,
    )

    ds = normalize_time_name(ds)

    resolved = {}
    for out_name, aliases in cfg["wanted"].items():
        actual = detect_variable(ds, aliases)
        resolved[out_name] = actual
        print(f"  {out_name} <- {actual}")

    ds_sub = point_select(ds[list(resolved.values())])

    ds_sub = ds_sub.sel(
        time=slice(
            np.datetime64(START),
            np.datetime64(END),
        )
    )

    # Rename variables before materialising.
    reverse = {actual: out for out, actual in resolved.items()}
    ds_sub = ds_sub.rename(reverse)

    print("  loading selected 6-point time-series...")
    ds_sub = ds_sub.load()

    # Save a compact local checkpoint NetCDF when possible.
    checkpoint = RAW_DIR / f"40B04B2_{group_name}_6cells_2001_2025.nc"
    try:
        ds_sub.to_netcdf(checkpoint)
        print("  checkpoint:", checkpoint.name)
    except Exception as e:
        print("  checkpoint skipped:", e)

    frame = ds_sub.to_dataframe().reset_index()

    # Keep only real coordinates + requested output variables.
    keep = ["time", "point"] + list(resolved.keys())
    keep = [c for c in keep if c in frame.columns]
    frame = frame[keep].copy()

    # Close references.
    try:
        ds.close()
    except Exception:
        pass

    del ds, ds_sub
    gc.collect()

    print("  rows:", len(frame))
    return frame


def saturation_vapor_pressure_kpa(temp_c):
    """
    FAO-style saturation vapour pressure approximation.
    """
    return 0.6108 * np.exp(
        (17.27 * temp_c) / (temp_c + 237.3)
    )


# ------------------------------------------------------------
# 5. RETRIEVE FOUR GROUPS
# ------------------------------------------------------------

frames = []

for group_name, cfg in ARCO_GROUPS.items():
    frames.append(
        extract_group(group_name, cfg)
    )

# ------------------------------------------------------------
# 6. MERGE HOURLY VARIABLES
# ------------------------------------------------------------

hourly = frames[0]

for frame in frames[1:]:
    hourly = hourly.merge(
        frame,
        on=["time", "point"],
        how="outer",
        validate="one_to_one",
    )

hourly["time"] = pd.to_datetime(hourly["time"], utc=True)

hourly = hourly.sort_values(
    ["point", "time"]
).reset_index(drop=True)

print("\nMerged hourly rows:", len(hourly))
print("Expected hourly rows:", EXPECTED_HOURS * len(cells))

# ------------------------------------------------------------
# 7. UNIT CONVERSION + DERIVED HOURLY VARIABLES
# ------------------------------------------------------------

hourly["T2M_C"] = pd.to_numeric(hourly["T2M_K"], errors="coerce") - 273.15
hourly["TD2M_C"] = pd.to_numeric(hourly["TD2M_K"], errors="coerce") - 273.15

hourly["U10_MS"] = pd.to_numeric(hourly["U10_MS"], errors="coerce")
hourly["V10_MS"] = pd.to_numeric(hourly["V10_MS"], errors="coerce")

hourly["WIND_MS"] = np.sqrt(
    hourly["U10_MS"] ** 2
    + hourly["V10_MS"] ** 2
)

# Hourly ARCO accumulated quantities have already been de-accumulated.
hourly["SSRD_J_M2_HOURLY"] = pd.to_numeric(
    hourly["SSRD_J_M2_HOURLY"],
    errors="coerce"
)
hourly["TP_M_HOURLY"] = pd.to_numeric(
    hourly["TP_M_HOURLY"],
    errors="coerce"
)

# Precision noise should not create negative physical flux.
# Substantial negatives remain NaN and will be caught by completeness QC.
hourly.loc[
    hourly["SSRD_J_M2_HOURLY"].between(-1e-6, 0),
    "SSRD_J_M2_HOURLY"
] = 0.0

hourly.loc[
    hourly["TP_M_HOURLY"].between(-1e-10, 0),
    "TP_M_HOURLY"
] = 0.0

hourly.loc[
    hourly["SSRD_J_M2_HOURLY"] < 0,
    "SSRD_J_M2_HOURLY"
] = np.nan

hourly.loc[
    hourly["TP_M_HOURLY"] < 0,
    "TP_M_HOURLY"
] = np.nan

hourly["SP_PA"] = pd.to_numeric(hourly["SP_PA"], errors="coerce")

es = saturation_vapor_pressure_kpa(hourly["T2M_C"])
ea = saturation_vapor_pressure_kpa(hourly["TD2M_C"])

hourly["VPD_KPA"] = np.maximum(es - ea, 0.0)
hourly["RH_PCT"] = np.clip(
    100.0 * ea / es,
    0.0,
    100.0
)

# Daily key = UTC calendar day.
hourly["DATE"] = hourly["time"].dt.floor("D").dt.tz_localize(None)

# ------------------------------------------------------------
# 8. DAILY AGGREGATION
# ------------------------------------------------------------

daily = (
    hourly
    .groupby(["point", "DATE"], as_index=False)
    .agg(
        HOURS_PRESENT=("time", "count"),

        TMEAN_C=("T2M_C", "mean"),
        TMIN_C=("T2M_C", "min"),
        TMAX_C=("T2M_C", "max"),

        TD_MEAN_C=("TD2M_C", "mean"),

        RH_MEAN_PCT=("RH_PCT", "mean"),
        VPD_MEAN_KPA=("VPD_KPA", "mean"),
        VPD_MAX_KPA=("VPD_KPA", "max"),

        WIND_MEAN_MS=("WIND_MS", "mean"),

        SSRD_J_M2_DAY=("SSRD_J_M2_HOURLY", "sum"),
        TP_M_DAY=("TP_M_HOURLY", "sum"),

        PRESSURE_PA=("SP_PA", "mean"),

        T_VALID_HOURS=("T2M_C", "count"),
        TD_VALID_HOURS=("TD2M_C", "count"),
        WIND_VALID_HOURS=("WIND_MS", "count"),
        RAD_VALID_HOURS=("SSRD_J_M2_HOURLY", "count"),
        TP_VALID_HOURS=("TP_M_HOURLY", "count"),
        PRESSURE_VALID_HOURS=("SP_PA", "count"),
    )
)

daily["RAD_MJ_M2_DAY"] = daily["SSRD_J_M2_DAY"] / 1_000_000.0
daily["ERA5L_RAIN_MM_DAY"] = daily["TP_M_DAY"] * 1000.0
daily["PRESSURE_HPA"] = daily["PRESSURE_PA"] / 100.0

daily = daily.rename(columns={"point": "ERA5L_CELL_ID"})

daily = daily.merge(
    cells[["ERA5L_CELL_ID", "ERA5L_LON", "ERA5L_LAT"]],
    on="ERA5L_CELL_ID",
    how="left",
    validate="many_to_one",
)

# Final date window safeguard.
daily = daily[
    daily["DATE"].between(
        pd.Timestamp("2001-01-01"),
        pd.Timestamp("2025-12-31"),
    )
].copy()

daily = daily.sort_values(
    ["ERA5L_CELL_ID", "DATE"]
).reset_index(drop=True)

# ------------------------------------------------------------
# 9. QC PER CELL
# ------------------------------------------------------------

all_dates = pd.date_range(
    "2001-01-01",
    "2025-12-31",
    freq="D"
)

qc_rows = []

forcing_columns = [
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

for _, c in cells.iterrows():

    cid = c["ERA5L_CELL_ID"]

    sub = (
        daily[daily["ERA5L_CELL_ID"] == cid]
        .set_index("DATE")
        .reindex(all_dates)
    )

    forcing_valid = sub[forcing_columns].notna().all(axis=1)

    qc_rows.append({
        "ERA5L_CELL_ID": cid,
        "EXPECTED_DAYS": EXPECTED_DAYS,
        "ROWS_PRESENT": int(sub["ERA5L_CELL_ID"].notna().sum()),
        "DAYS_WITH_24_HOURS": int((sub["HOURS_PRESENT"] == 24).sum()),
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
            and (sub["HOURS_PRESENT"] == 24).sum() == EXPECTED_DAYS
        )
    })

cell_qc = pd.DataFrame(qc_rows)

# Plausibility checks — deliberately broad; these are QA flags, not climatological claims.
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

# ------------------------------------------------------------
# 10. MONTHLY + ANNUAL SUMMARIES
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
# 11. FINAL STATUS + EXPORT
# ------------------------------------------------------------

all_complete = bool(cell_qc["COMPLETE"].all())
all_plausible = bool(all(plausibility.values()))

status = "PASS" if all_complete and all_plausible else "CHECK"

qc_summary = {
    "gate": "40B04B2",
    "status": status,

    "dataset": "ERA5-Land hourly ARCO time-series",
    "provider": "ECMWF / Copernicus Climate Data Store",
    "period": ["2001-01-01", "2025-12-31"],

    "unique_era5land_cells": int(len(cells)),
    "expected_days_per_cell": int(EXPECTED_DAYS),
    "expected_hours_per_cell": int(EXPECTED_HOURS),

    "actual_daily_rows": int(len(daily)),
    "expected_daily_rows": int(EXPECTED_DAYS * len(cells)),

    "complete_cells": int(cell_qc["COMPLETE"].sum()),
    "incomplete_cells": int((~cell_qc["COMPLETE"]).sum()),
    "missing_forcing_days_total": int(cell_qc["MISSING_FORCING_DAYS"].sum()),

    "daily_boundary": "00:00-23:00 UTC",

    "primary_rainfall_policy": "CHIRPS v2 Final",
    "era5land_rainfall_role": "diagnostic_crosscheck_and_sensitivity_only",

    "radiation_conversion": "hourly de-accumulated J m-2 summed daily and divided by 1e6 -> MJ m-2 day-1",
    "precipitation_conversion": "hourly de-accumulated m summed daily and multiplied by 1000 -> mm day-1",
    "temperature_conversion": "K - 273.15 -> degC",
    "pressure_conversion": "Pa / 100 -> hPa",

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

# Keep scientific output columns clean.
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

    "HOURS_PRESENT",
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

OUTPUT_QC_JSON.write_text(
    json.dumps(qc_summary, indent=2),
    encoding="utf-8"
)

print("\n====================================================")
print("40B04B2 FINISHED")
print("====================================================")
print("Status:", status)
print("Unique ERA5-Land cells:", len(cells))
print("Daily rows:", len(daily), "/", EXPECTED_DAYS * len(cells))
print("Complete cells:", int(cell_qc["COMPLETE"].sum()), "/", len(cells))
print("Missing forcing days:", int(cell_qc["MISSING_FORCING_DAYS"].sum()))
print("Plausibility checks:", "PASS" if all_plausible else "CHECK")
print("Daily output:", OUTPUT_DAILY)
print("Cell QC:", OUTPUT_CELL_QC)
print("Monthly:", OUTPUT_MONTHLY)
print("Annual:", OUTPUT_ANNUAL)
print("QC JSON:", OUTPUT_QC_JSON)
print("====================================================")
