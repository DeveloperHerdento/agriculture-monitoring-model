# ============================================================
# OUTPUT 4 / 40B04A
# CLIMATE NATIVE-CELL MAPPING — SIAK_AOI01
# LOCAL PYTHON / JUPYTER VERSION
#
# PURPOSE
# - Read final 820 ASU table after 40B03C1
# - Assign each ASU centroid to:
#     (1) the actual native CHIRPS v2 0.05° pixel
#         by reading metadata from one official UCSB CHIRPS COG
#     (2) the nearest ERA5-Land 0.1° grid point
# - Export a compact ASU-to-climate-cell mapping
#
# IMPORTANT
# - This stage DOES NOT download 25 years of climate data.
# - It prevents redundant 820 x daily climate downloads.
# - After this, daily forcing is downloaded once per unique climate cell.
# ============================================================

from pathlib import Path
import os
import json
import math
import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import xy

# ------------------------------------------------------------
# 0. CONFIG
# ------------------------------------------------------------

WORKDIR = Path(
    r"C:\Users\user\Documents\KERJA\SPATIAL DATA ANALYST INTERN\04_YIELD"
)
os.chdir(WORKDIR)

INPUT_CSV = WORKDIR / "40B03C1_FINAL_ASU_500M_SOIL_TEXTURE_SIAK_AOI01_V1.csv"

OUTPUT_CSV = WORKDIR / "40B04A_ASU_CLIMATE_CELL_MAPPING_SIAK_AOI01_V1.csv"
OUTPUT_UNIQUE_CHIRPS = WORKDIR / "40B04A_UNIQUE_CHIRPS_CELLS_SIAK_AOI01_V1.csv"
OUTPUT_UNIQUE_ERA5L = WORKDIR / "40B04A_UNIQUE_ERA5L_CELLS_SIAK_AOI01_V1.csv"
OUTPUT_QC = WORKDIR / "40B04A_CLIMATE_CELL_MAPPING_QC_SIAK_AOI01_V1.json"

# One official CHIRPS v2 daily COG is used ONLY to read the true grid transform.
CHIRPS_REFERENCE_COG = (
    "https://data.chc.ucsb.edu/products/CHIRPS-2.0/"
    "global_daily/cogs/p05/2025/chirps-v2.0.2025.01.01.cog"
)

ERA5L_RES_DEG = 0.1

# ------------------------------------------------------------
# 1. LOAD ASU TABLE
# ------------------------------------------------------------

if not INPUT_CSV.exists():
    raise FileNotFoundError(f"Input not found: {INPUT_CSV}")

df = pd.read_csv(INPUT_CSV)

required = [
    "UNIT_ID",
    "CENTROID_LON_EXACT",
    "CENTROID_LAT_EXACT",
    "ASU_AREA_HA_EXACT",
]

missing = [c for c in required if c not in df.columns]
if missing:
    raise ValueError(f"Missing required columns: {missing}")

if len(df) != 820:
    raise ValueError(f"Expected 820 ASUs, found {len(df)}")

lon = pd.to_numeric(df["CENTROID_LON_EXACT"], errors="coerce")
lat = pd.to_numeric(df["CENTROID_LAT_EXACT"], errors="coerce")

if lon.isna().any() or lat.isna().any():
    raise ValueError("Missing/invalid ASU centroid coordinates.")

print("====================================================")
print("40B04A — CLIMATE NATIVE-CELL MAPPING")
print("====================================================")
print("ASU count:", len(df))
print(
    "Centroid bbox:",
    float(lon.min()), float(lat.min()),
    float(lon.max()), float(lat.max())
)

# ------------------------------------------------------------
# 2. CHIRPS: READ TRUE GRID METADATA FROM OFFICIAL COG
# ------------------------------------------------------------

print("\nReading CHIRPS native grid metadata...")

# These GDAL options reduce unnecessary directory/network operations.
env_opts = {
    "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
    "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".cog,.tif,.tiff",
}

chirps_rows = []
chirps_cols = []
chirps_lons = []
chirps_lats = []

with rasterio.Env(**env_opts):
    with rasterio.open(CHIRPS_REFERENCE_COG) as src:

        chirps_crs = str(src.crs)
        chirps_transform = src.transform
        chirps_res_x = abs(float(src.res[0]))
        chirps_res_y = abs(float(src.res[1]))

        print("CHIRPS CRS:", chirps_crs)
        print("CHIRPS resolution:", src.res)
        print("CHIRPS raster size:", src.width, "x", src.height)

        # Because CHIRPS is geographic WGS84-like lon/lat,
        # each ASU centroid can be mapped to the containing native pixel.
        for x, y in zip(lon, lat):
            r, c = src.index(float(x), float(y))
            cx, cy = src.xy(r, c, offset="center")

            chirps_rows.append(int(r))
            chirps_cols.append(int(c))
            chirps_lons.append(float(cx))
            chirps_lats.append(float(cy))

# Strong QC: expected ~0.05 degree native grid.
if not (0.049 <= chirps_res_x <= 0.051 and 0.049 <= chirps_res_y <= 0.051):
    raise RuntimeError(
        f"Unexpected CHIRPS resolution: {chirps_res_x}, {chirps_res_y}"
    )

df["CHIRPS_ROW"] = chirps_rows
df["CHIRPS_COL"] = chirps_cols
df["CHIRPS_LON"] = chirps_lons
df["CHIRPS_LAT"] = chirps_lats

df["CHIRPS_CELL_ID"] = [
    f"CHIRPS_R{r}_C{c}"
    for r, c in zip(chirps_rows, chirps_cols)
]

# ------------------------------------------------------------
# 3. ERA5-LAND: NEAREST 0.1° GRID POINT
# ------------------------------------------------------------

# ECMWF CDS location selection is resolved to the nearest
# ERA5-Land 0.1-degree grid point.
#
# np.rint avoids Python string rounding tricks and keeps
# numeric grid coordinates explicit.
era_lon = np.rint(lon.to_numpy(dtype=float) / ERA5L_RES_DEG) * ERA5L_RES_DEG
era_lat = np.rint(lat.to_numpy(dtype=float) / ERA5L_RES_DEG) * ERA5L_RES_DEG

# Remove floating artefacts.
era_lon = np.round(era_lon, 1)
era_lat = np.round(era_lat, 1)

df["ERA5L_LON"] = era_lon
df["ERA5L_LAT"] = era_lat
df["ERA5L_CELL_ID"] = [
    f"ERA5L_{la:+05.1f}_{lo:+06.1f}"
    for la, lo in zip(era_lat, era_lon)
]

# ------------------------------------------------------------
# 4. UNIQUE CELL TABLES
# ------------------------------------------------------------

chirps_unique = (
    df.groupby(
        ["CHIRPS_CELL_ID", "CHIRPS_ROW", "CHIRPS_COL", "CHIRPS_LON", "CHIRPS_LAT"],
        as_index=False
    )
    .agg(
        ASU_COUNT=("UNIT_ID", "count"),
        PLANTATION_AREA_HA=("ASU_AREA_HA_EXACT", "sum"),
    )
    .sort_values(["CHIRPS_LAT", "CHIRPS_LON"])
    .reset_index(drop=True)
)

era_unique = (
    df.groupby(
        ["ERA5L_CELL_ID", "ERA5L_LON", "ERA5L_LAT"],
        as_index=False
    )
    .agg(
        ASU_COUNT=("UNIT_ID", "count"),
        PLANTATION_AREA_HA=("ASU_AREA_HA_EXACT", "sum"),
    )
    .sort_values(["ERA5L_LAT", "ERA5L_LON"])
    .reset_index(drop=True)
)

# ------------------------------------------------------------
# 5. QC
# ------------------------------------------------------------

qc = {
    "status": "PASS",
    "asu_count": int(len(df)),
    "asu_with_chirps_mapping": int(df["CHIRPS_CELL_ID"].notna().sum()),
    "asu_with_era5land_mapping": int(df["ERA5L_CELL_ID"].notna().sum()),
    "unique_chirps_cells": int(len(chirps_unique)),
    "unique_era5land_cells": int(len(era_unique)),
    "chirps_reference_cog": CHIRPS_REFERENCE_COG,
    "chirps_crs": chirps_crs,
    "chirps_resolution_x_deg": chirps_res_x,
    "chirps_resolution_y_deg": chirps_res_y,
    "era5land_resolution_deg": ERA5L_RES_DEG,
    "strategy": (
        "Download/extract daily climate forcing once per unique native climate cell, "
        "then join the time-series back to 820 ASUs by climate cell ID."
    ),
    "temporal_target": {
        "forcing_resolution": "daily",
        "analysis_period": "2001-2025",
        "palmsim_internal_reference_timestep": "10-day model integration",
        "reporting_outputs": ["monthly", "annual"],
    },
}

# ------------------------------------------------------------
# 6. EXPORT
# ------------------------------------------------------------

df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
chirps_unique.to_csv(OUTPUT_UNIQUE_CHIRPS, index=False, encoding="utf-8-sig")
era_unique.to_csv(OUTPUT_UNIQUE_ERA5L, index=False, encoding="utf-8-sig")

with OUTPUT_QC.open("w", encoding="utf-8") as f:
    json.dump(qc, f, indent=2)

print("\n====================================================")
print("40B04A FINISHED")
print("====================================================")
print("ASU mapped to CHIRPS:", qc["asu_with_chirps_mapping"], "/", qc["asu_count"])
print("ASU mapped to ERA5-Land:", qc["asu_with_era5land_mapping"], "/", qc["asu_count"])
print("Unique CHIRPS cells:", qc["unique_chirps_cells"])
print("Unique ERA5-Land cells:", qc["unique_era5land_cells"])
print("Output mapping:", OUTPUT_CSV)
print("Unique CHIRPS:", OUTPUT_UNIQUE_CHIRPS)
print("Unique ERA5-Land:", OUTPUT_UNIQUE_ERA5L)
print("QC:", OUTPUT_QC)
print("====================================================")
