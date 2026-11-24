# ============================================================
# OUTPUT 4 / 40B03C1
# SoilGrids Core Texture Enrichment — SIAK_AOI01
# LOCAL PYTHON / JUPYTER VERSION
#
# PURPOSE
# - Read final exact 500 m ASU GeoJSON
# - Pull SoilGrids mean layers directly from official ISRIC WebDAV
# - Use only PALMSIM-core texture variables first:
#     sand, silt, clay
# - Depth-weight 0–100 cm:
#     0–5, 5–15, 15–30, 30–60, 60–100 cm
# - Calculate per-ASU mean, std, count
# - Export enriched GeoJSON + CSV + QC JSON
#
# NOTE
# - This avoids Google Earth Engine entirely.
# - Internet is required on the machine running this script.
# - SoilGrids native resolution is 250 m.
# ============================================================

from pathlib import Path
import json
import math
import sys
import subprocess
import warnings

warnings.filterwarnings("ignore")

# ------------------------------------------------------------
# 0. USER CONFIG
# ------------------------------------------------------------

# Put this script in the same folder as the GeoJSON,
# OR edit WORKDIR below.
WORKDIR = Path.cwd()

ASU_FILE = WORKDIR / "40B03A_FINAL_ASU_500M_EXACT_SIAK_AOI01_V1.geojson"

OUTPUT_GEOJSON = WORKDIR / "40B03C1_FINAL_ASU_500M_SOIL_TEXTURE_SIAK_AOI01_V1.geojson"
OUTPUT_CSV = WORKDIR / "40B03C1_FINAL_ASU_500M_SOIL_TEXTURE_SIAK_AOI01_V1.csv"
OUTPUT_QC = WORKDIR / "40B03C1_SOIL_TEXTURE_QC_SUMMARY_SIAK_AOI01_V1.json"

CACHE_DIR = WORKDIR / "soilgrids_cache_siak"
CACHE_DIR.mkdir(exist_ok=True)

TARGET_CRS = "EPSG:32647"
TARGET_RES_M = 250

# A small buffer ensures edge ASUs are fully covered.
BBOX_BUFFER_M = 500

DEPTHS = [
    ("0-5cm", 5),
    ("5-15cm", 10),
    ("15-30cm", 15),
    ("30-60cm", 30),
    ("60-100cm", 40),
]

PROPERTIES = {
    "sand": {"factor": 10.0, "unit": "%"},
    "silt": {"factor": 10.0, "unit": "%"},
    "clay": {"factor": 10.0, "unit": "%"},
}

# ------------------------------------------------------------
# 1. IMPORTS WITH FRIENDLY ERROR
# ------------------------------------------------------------

try:
    import numpy as np
    import pandas as pd
    import geopandas as gpd
    import rasterio
    from rasterio.mask import mask
    from osgeo import gdal
except Exception as e:
    print("\nERROR: Required geospatial packages are missing.")
    print("Recommended installation in Anaconda/Miniconda:")
    print("  conda install -c conda-forge geopandas rasterio gdal pandas numpy")
    print("\nThen restart Jupyter and run this script again.")
    raise

gdal.UseExceptions()

# ------------------------------------------------------------
# 2. LOAD FINAL ASU
# ------------------------------------------------------------

if not ASU_FILE.exists():
    raise FileNotFoundError(
        f"ASU file not found:\n{ASU_FILE}\n"
        "Place 40B03A_FINAL_ASU_500M_EXACT_SIAK_AOI01_V1.geojson "
        "in the same folder as this script or edit WORKDIR."
    )

asu = gpd.read_file(ASU_FILE)

if asu.crs is None:
    asu = asu.set_crs("EPSG:4326")

asu_utm = asu.to_crs(TARGET_CRS)

print("====================================================")
print("40B03C1 — SOILGRIDS CORE TEXTURE")
print("====================================================")
print("ASU count:", len(asu_utm))
print("ASU CRS:", asu_utm.crs)

xmin, ymin, xmax, ymax = asu_utm.total_bounds
xmin -= BBOX_BUFFER_M
ymin -= BBOX_BUFFER_M
xmax += BBOX_BUFFER_M
ymax += BBOX_BUFFER_M

print("Buffered UTM bbox:", (xmin, ymin, xmax, ymax))

# ------------------------------------------------------------
# 3. DOWNLOAD/CROP A SOILGRIDS LAYER USING OFFICIAL WEBDAV VRT
# ------------------------------------------------------------

def local_soilgrid_layer(prop, depth):
    """
    Use GDAL /vsicurl against official ISRIC SoilGrids WebDAV VRT.
    Only the SIAK subset is materialized locally.
    """
    out_tif = CACHE_DIR / f"{prop}_{depth}_mean_SIAK_UTM47N.tif"

    if out_tif.exists() and out_tif.stat().st_size > 0:
        return out_tif

    remote_vrt = (
        f"/vsicurl?max_retry=5&retry_delay=2&list_dir=no&"
        f"url=https://files.isric.org/soilgrids/latest/data/"
        f"{prop}/{prop}_{depth}_mean.vrt"
    )

    print(f"Fetching {prop} {depth} ...")

    options = gdal.WarpOptions(
        format="GTiff",
        dstSRS=TARGET_CRS,
        outputBounds=(xmin, ymin, xmax, ymax),
        outputBoundsSRS=TARGET_CRS,
        xRes=TARGET_RES_M,
        yRes=TARGET_RES_M,
        resampleAlg="bilinear",
        multithread=True,
        creationOptions=[
            "TILED=YES",
            "COMPRESS=DEFLATE",
            "PREDICTOR=2",
        ],
    )

    ds = gdal.Warp(
        str(out_tif),
        remote_vrt,
        options=options,
    )

    if ds is None:
        raise RuntimeError(f"GDAL failed for {prop} {depth}")

    ds = None

    if not out_tif.exists() or out_tif.stat().st_size == 0:
        raise RuntimeError(f"Output raster missing for {prop} {depth}")

    return out_tif

# ------------------------------------------------------------
# 4. CREATE DEPTH-WEIGHTED 0–100 CM RASTER
# ------------------------------------------------------------

def build_weighted_texture(prop, conversion_factor):
    """
    SoilGrids mapped integer values are converted to conventional units,
    then depth-weighted across 0–100 cm.
    """
    arrays = []
    weights = []
    profile = None

    for depth, thickness_cm in DEPTHS:
        tif = local_soilgrid_layer(prop, depth)

        with rasterio.open(tif) as src:
            arr = src.read(1).astype("float64")
            nodata = src.nodata
            if nodata is not None:
                arr[arr == nodata] = np.nan

            # Convert mapped units to conventional units.
            arr = arr / conversion_factor

            arrays.append(arr)
            weights.append(thickness_cm)

            if profile is None:
                profile = src.profile.copy()

    stack = np.stack(arrays, axis=0)
    weights_arr = np.asarray(weights, dtype="float64")[:, None, None]

    valid = np.isfinite(stack)
    weighted_sum = np.nansum(stack * weights_arr, axis=0)
    weight_sum = np.sum(valid * weights_arr, axis=0)

    out = np.full(stack.shape[1:], np.nan, dtype="float32")
    ok = weight_sum > 0
    out[ok] = (weighted_sum[ok] / weight_sum[ok]).astype("float32")

    out_path = CACHE_DIR / f"{prop}_0_100cm_weighted_SIAK_UTM47N.tif"

    profile.update(
        dtype="float32",
        count=1,
        nodata=-9999.0,
        compress="deflate",
        tiled=True,
    )

    write_arr = np.where(np.isfinite(out), out, -9999.0).astype("float32")

    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(write_arr, 1)

    return out_path

# ------------------------------------------------------------
# 5. ZONAL STATS
# ------------------------------------------------------------

def zonal_stats_for_raster(gdf_utm, raster_path, prefix):
    means = []
    stds = []
    counts = []

    with rasterio.open(raster_path) as src:
        nodata = src.nodata

        for geom in gdf_utm.geometry:
            try:
                data, _ = mask(
                    src,
                    [geom],
                    crop=True,
                    all_touched=True,
                    filled=False,
                )
                vals = data[0]

                if hasattr(vals, "compressed"):
                    vals = vals.compressed()
                else:
                    vals = vals[np.isfinite(vals)]

                vals = np.asarray(vals, dtype="float64")

                if nodata is not None:
                    vals = vals[vals != nodata]

                vals = vals[np.isfinite(vals)]

                if vals.size == 0:
                    means.append(np.nan)
                    stds.append(np.nan)
                    counts.append(0)
                else:
                    means.append(float(np.mean(vals)))
                    stds.append(float(np.std(vals, ddof=0)))
                    counts.append(int(vals.size))

            except Exception:
                means.append(np.nan)
                stds.append(np.nan)
                counts.append(0)

    gdf_utm[f"{prefix}_MEAN"] = means
    gdf_utm[f"{prefix}_STD"] = stds
    gdf_utm[f"{prefix}_COUNT"] = counts

    return gdf_utm

# ------------------------------------------------------------
# 6. RUN
# ------------------------------------------------------------

weighted_files = {}

for prop, cfg in PROPERTIES.items():
    weighted_files[prop] = build_weighted_texture(
        prop,
        cfg["factor"]
    )

for prop in ["sand", "silt", "clay"]:
    prefix = prop.upper() + "_PCT_0_100"
    asu_utm = zonal_stats_for_raster(
        asu_utm,
        weighted_files[prop],
        prefix,
    )

# ------------------------------------------------------------
# 7. BASIC TEXTURE QC
# ------------------------------------------------------------

asu_utm["TEXTURE_SUM_PCT"] = (
    asu_utm["SAND_PCT_0_100_MEAN"]
    + asu_utm["SILT_PCT_0_100_MEAN"]
    + asu_utm["CLAY_PCT_0_100_MEAN"]
)

asu_utm["SOIL_TEXTURE_DATA_VALID"] = (
    asu_utm[
        [
            "SAND_PCT_0_100_MEAN",
            "SILT_PCT_0_100_MEAN",
            "CLAY_PCT_0_100_MEAN",
        ]
    ]
    .notna()
    .all(axis=1)
    .astype(int)
)

# SoilGrids values should approximately sum to 100%.
asu_utm["TEXTURE_SUM_QC"] = np.where(
    asu_utm["SOIL_TEXTURE_DATA_VALID"].eq(0),
    "NO_DATA",
    np.where(
        asu_utm["TEXTURE_SUM_PCT"].between(95, 105),
        "PASS",
        "CHECK",
    ),
)

asu_utm["SOIL_SOURCE"] = "SoilGrids_2.0_mean_250m_ISRIC_WebDAV"
asu_utm["SOIL_OBSERVED_LOCAL"] = 0
asu_utm["SOIL_DEPTH_PROFILE_USED"] = "0-100cm_depth_weighted"
asu_utm["SOIL_ENRICHMENT_VERSION"] = "40B03C1_V1"

# ------------------------------------------------------------
# 8. EXPORT
# ------------------------------------------------------------

asu_out = asu_utm.to_crs("EPSG:4326")
asu_out.to_file(OUTPUT_GEOJSON, driver="GeoJSON")

csv_df = pd.DataFrame(asu_out.drop(columns="geometry"))
csv_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

valid = asu_utm["SOIL_TEXTURE_DATA_VALID"].eq(1)

qc = {
    "status": "PASS" if valid.all() else "PASS_WITH_MISSING",
    "asu_count": int(len(asu_utm)),
    "soil_texture_valid_asu_count": int(valid.sum()),
    "soil_texture_missing_asu_count": int((~valid).sum()),
    "soil_texture_valid_fraction": float(valid.mean()),
    "texture_sum_pass_count": int((asu_utm["TEXTURE_SUM_QC"] == "PASS").sum()),
    "texture_sum_check_count": int((asu_utm["TEXTURE_SUM_QC"] == "CHECK").sum()),
    "sand_mean_pct_global_asu_mean": float(asu_utm.loc[valid, "SAND_PCT_0_100_MEAN"].mean()),
    "silt_mean_pct_global_asu_mean": float(asu_utm.loc[valid, "SILT_PCT_0_100_MEAN"].mean()),
    "clay_mean_pct_global_asu_mean": float(asu_utm.loc[valid, "CLAY_PCT_0_100_MEAN"].mean()),
    "source": "ISRIC SoilGrids 2.0 mean predictions via official WebDAV VRT",
    "resolution_m": 250,
    "depths_used_cm": ["0-5", "5-15", "15-30", "30-60", "60-100"],
    "output_geojson": OUTPUT_GEOJSON.name,
    "output_csv": OUTPUT_CSV.name,
}

with open(OUTPUT_QC, "w", encoding="utf-8") as f:
    json.dump(qc, f, indent=2)

print("====================================================")
print("40B03C1 FINISHED")
print("====================================================")
print("ASU count:", qc["asu_count"])
print("Valid soil-texture ASUs:", qc["soil_texture_valid_asu_count"])
print("Missing soil-texture ASUs:", qc["soil_texture_missing_asu_count"])
print("Texture-sum PASS:", qc["texture_sum_pass_count"])
print("Texture-sum CHECK:", qc["texture_sum_check_count"])
print("Output GeoJSON:", OUTPUT_GEOJSON)
print("Output CSV:", OUTPUT_CSV)
print("QC JSON:", OUTPUT_QC)
print("====================================================")
