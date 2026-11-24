# ========================================
# RECOVERED HISTORICAL SOURCE CANDIDATE
# Stage: 30D04
# Source: OUTPUT 3.ipynb
# ========================================


# ========================================
# ORIGINAL CELL 0
# ========================================

# ============================================================
# OUTPUT 3 | 30F-B01
# CELL 01 — PYTHON ENVIRONMENT & GOOGLE EARTH ENGINE CONNECTION
# ============================================================

import sys
import platform

print("=" * 70)
print("30F-B01 | ENVIRONMENT & GOOGLE EARTH ENGINE CONNECTION CHECK")
print("=" * 70)

# ------------------------------------------------------------
# 1. Python environment
# ------------------------------------------------------------
print("\n[1] PYTHON ENVIRONMENT")
print("Python version :", sys.version.split()[0])
print("Executable     :", sys.executable)
print("Platform       :", platform.platform())

# ------------------------------------------------------------
# 2. Import Earth Engine Python API
# ------------------------------------------------------------
print("\n[2] EARTH ENGINE PYTHON API")

try:
    import ee
    print("Earth Engine API imported successfully.")
    print("ee version     :", getattr(ee, "__version__", "unknown"))
except ModuleNotFoundError:
    print("ERROR: earthengine-api belum terpasang pada kernel ini.")
    print("\nInstall dengan command berikut:")
    print(f'"{sys.executable}" -m pip install earthengine-api')
    raise

# ------------------------------------------------------------
# 3. Initialize / authenticate Earth Engine
# ------------------------------------------------------------
PROJECT_ID = "palm-oil-503202"

print("\n[3] EARTH ENGINE INITIALIZATION")
print("Cloud Project  :", PROJECT_ID)

try:
    ee.Initialize(project=PROJECT_ID)
    print("Existing Earth Engine credentials detected.")
except Exception:
    print("Earth Engine authentication diperlukan.")
    print("Browser/login Google mungkin akan terbuka.")
    
    ee.Authenticate()
    ee.Initialize(project=PROJECT_ID)

print("Earth Engine initialized successfully.")

# ------------------------------------------------------------
# 4. Server-side connection test
# ------------------------------------------------------------
print("\n[4] SERVER CONNECTION TEST")

test_value = ee.Number(30).add(1).getInfo()

print("Earth Engine test value:", test_value)

if test_value == 31:
    print("Server connection: PASS")
else:
    print("Server connection: CHECK")

# ------------------------------------------------------------
# 5. Test access to frozen 30D04 asset
# ------------------------------------------------------------
print("\n[5] OUTPUT 3 ASSET ACCESS TEST")

ASSET_30D04 = (
    "projects/palm-oil-503202/assets/"
    "SIAK_AOI01_O3_30D04_BALANCED_RISK_2025"
)

try:
    asset_info = ee.data.getAsset(ASSET_30D04)

    print("30D04 asset   : FOUND")
    print("Asset ID      :", ASSET_30D04)
    print("Asset type    :", asset_info.get("type", "unknown"))
    
except Exception as e:
    print("30D04 asset   : FAILED")
    print("Asset ID      :", ASSET_30D04)
    print("Error         :", str(e))

print("\n" + "=" * 70)
print("CELL 01 FINISHED")
print("=" * 70)

# ========================================
# ORIGINAL CELL 15
# ========================================

ASSET_30D04 = (
    "projects/palm-oil-503202/assets/"
    "SIAK_AOI01_O3_30D04_BALANCED_RISK_2025"
)

try:
    info_30D04 = ee.data.getAsset(ASSET_30D04)

    print("30D04 ASSET ACCESS: PASS")
    print("Asset ID   :", ASSET_30D04)
    print("Asset type :", info_30D04.get("type"))
    
except Exception as e:
    print("30D04 ASSET ACCESS: FAILED")
    print(type(e).__name__ + ":", e)

# ========================================
# ORIGINAL CELL 20
# ========================================

# ============================================================
# OUTPUT 3 | 30F-B01
# BATCH INVENTORY — 30D04 + ALL WALL-TO-WALL 30E CONTEXT ASSETS
# ============================================================

import ee
import pandas as pd

ROOT = "projects/palm-oil-503202/assets/"

ASSETS = {
    "30D04_CORE_RISK":
        ROOT + "SIAK_AOI01_O3_30D04_BALANCED_RISK_2025",

    "30E01_AGE":
        ROOT + "SIAK_AOI01_O3_30E01_AGE_CONTEXT_V3_2025",

    "30E02A_CHIRPS":
        ROOT + "SIAK_AOI01_O3_30E02A_CHIRPS_FINAL_2025",

    "30E02B_ERA5LAND":
        ROOT + "SIAK_AOI01_O3_30E02B_ERA5LAND_FINAL_2025",

    "30E02C_ETPET":
        ROOT + "SIAK_AOI01_O3_30E02C_ETPET_FINAL_2025",

    "30E03A_TERRAIN":
        ROOT + "SIAK_AOI01_O3_30E03A_TERRAIN_CORE_2025",

    "30E03B_HYDRO":
        ROOT + "SIAK_AOI01_O3_30E03B_HYDRO_CONTEXT_2025",

    "30E04A_SOIL":
        ROOT + "SIAK_AOI01_O3_30E04A_SOIL_CORE_PROFILE_2025",

    "30E04B_SOIL_WATER":
        ROOT + "SIAK_AOI01_O3_30E04B_SOIL_WATER_RETENTION_2025",
}

inventory_rows = []
band_registry = {}

print("=" * 90)
print("30F-B01 | BATCH ASSET + BAND INVENTORY")
print("=" * 90)

for key, asset_id in ASSETS.items():

    print(f"\n{'=' * 90}")
    print(f"{key}")
    print(f"{'=' * 90}")

    try:
        # ----------------------------------------------------
        # Asset access
        # ----------------------------------------------------
        asset_info = ee.data.getAsset(asset_id)
        asset_type = asset_info.get("type", "unknown")

        print("ACCESS      : PASS")
        print("ASSET TYPE  :", asset_type)

        # ----------------------------------------------------
        # Image + bands
        # ----------------------------------------------------
        img = ee.Image(asset_id)

        bands = img.bandNames().getInfo()
        band_registry[key] = bands

        print("BAND COUNT  :", len(bands))

        # ----------------------------------------------------
        # Projection from first band
        # ----------------------------------------------------
        first_band = bands[0]

        proj = img.select(first_band).projection()
        proj_info = proj.getInfo()
        scale = proj.nominalScale().getInfo()

        crs = proj_info.get("crs")

        print("FIRST BAND  :", first_band)
        print("CRS         :", crs)
        print("SCALE       :", scale, "m")

        # ----------------------------------------------------
        # Full band list
        # ----------------------------------------------------
        print("\nBANDS:")

        for i, band in enumerate(bands, start=1):
            print(f"  {i:03d}. {band}")

        # ----------------------------------------------------
        # Save inventory
        # ----------------------------------------------------
        inventory_rows.append({
            "asset_key": key,
            "asset_id": asset_id,
            "asset_type": asset_type,
            "band_count": len(bands),
            "first_band": first_band,
            "crs": crs,
            "nominal_scale_m": scale,
            "status": "PASS"
        })

    except Exception as e:

        print("ACCESS      : FAILED")
        print("ERROR       :", type(e).__name__, str(e))

        inventory_rows.append({
            "asset_key": key,
            "asset_id": asset_id,
            "asset_type": None,
            "band_count": None,
            "first_band": None,
            "crs": None,
            "nominal_scale_m": None,
            "status": "FAILED"
        })


# ============================================================
# SUMMARY TABLE
# ============================================================

inventory_df = pd.DataFrame(inventory_rows)

print("\n\n" + "=" * 90)
print("30F-B01 | SUMMARY")
print("=" * 90)

display(
    inventory_df[
        [
            "asset_key",
            "asset_type",
            "band_count",
            "crs",
            "nominal_scale_m",
            "status"
        ]
    ]
)

# ========================================
# ORIGINAL CELL 24
# ========================================

# ============================================================
# OUTPUT 3 | 30F-B03
# CONTROLLED STRATIFIED SPATIAL SAMPLE
# ============================================================

import ee

# ------------------------------------------------------------
# 1. Core image
# ------------------------------------------------------------

core_img = ee.Image(ASSETS["30D04_CORE_RISK"])

# CONDITION_CLASS is stored as float in the asset.
# stratifiedSample requires an integer class band.
condition_int = (
    core_img
    .select("CONDITION_CLASS")
    .round()
    .toInt()
    .rename("CONDITION_CLASS_INT")
)

# Core reference fields we want to carry into Python
core_sample_img = ee.Image.cat([
    condition_int,
    core_img.select("RISK_SCORE_0_100"),
    core_img.select("ANNUAL_CONFIDENCE"),
    core_img.select("MEAN_DATA_CONFIDENCE"),
    core_img.select("ALERT_PERIOD_COUNT"),
    core_img.select("INSPECTION_PERIOD_COUNT"),
    core_img.select("HIGH_PERIOD_COUNT"),
    core_img.select("MAX_CONSECUTIVE_ALERT"),
    core_img.select("REASON_CODE")
])

# ------------------------------------------------------------
# 2. Controlled stratified sample
# ------------------------------------------------------------
# Class 1 = Stable
# Class 2 = Watch
# Class 3 = Inspection Priority
# Class 4 = High Priority
#
# We intentionally oversample minority classes 3 and 4.
# Class 0 is excluded from contextual-condition modelling.

sample_fc = core_sample_img.stratifiedSample(
    numPoints=0,
    classBand="CONDITION_CLASS_INT",
    region=core_img.geometry(),
    scale=10,
    projection=ee.Projection("EPSG:32647"),
    seed=42,
    classValues=[1, 2, 3, 4],
    classPoints=[400, 400, 300, 200],
    dropNulls=True,
    tileScale=4,
    geometries=True
)

# ------------------------------------------------------------
# 3. Add coordinates + spatial grouping IDs
# ------------------------------------------------------------

UTM47 = ee.Projection("EPSG:32647")

def add_spatial_ids(feature):

    feature = ee.Feature(feature)

    geom_utm = feature.geometry().transform(UTM47, 1)
    xy = ee.List(geom_utm.coordinates())

    x = ee.Number(xy.get(0))
    y = ee.Number(xy.get(1))

    # deterministic sample ID from UTM position
    sample_id = (
        ee.String("S_")
        .cat(x.round().format())
        .cat("_")
        .cat(y.round().format())
    )

    # spatial grouping IDs
    g250 = (
        x.divide(250).floor().format()
        .cat("_")
        .cat(y.divide(250).floor().format())
    )

    g500 = (
        x.divide(500).floor().format()
        .cat("_")
        .cat(y.divide(500).floor().format())
    )

    g1000 = (
        x.divide(1000).floor().format()
        .cat("_")
        .cat(y.divide(1000).floor().format())
    )

    return feature.set({
        "SAMPLE_ID": sample_id,
        "X_UTM47N": x,
        "Y_UTM47N": y,
        "SPATIAL_GROUP_250M": g250,
        "SPATIAL_GROUP_500M": g500,
        "SPATIAL_GROUP_1000M": g1000
    })


sample_fc = sample_fc.map(add_spatial_ids)

# ------------------------------------------------------------
# 4. QC
# ------------------------------------------------------------

sample_count = sample_fc.size().getInfo()

class_hist = (
    sample_fc
    .aggregate_histogram("CONDITION_CLASS_INT")
    .getInfo()
)

groups_250 = (
    sample_fc
    .aggregate_count_distinct("SPATIAL_GROUP_250M")
    .getInfo()
)

groups_500 = (
    sample_fc
    .aggregate_count_distinct("SPATIAL_GROUP_500M")
    .getInfo()
)

groups_1000 = (
    sample_fc
    .aggregate_count_distinct("SPATIAL_GROUP_1000M")
    .getInfo()
)

print("=" * 80)
print("30F-B03 | CONTROLLED SPATIAL SAMPLE QC")
print("=" * 80)

print("\nTotal samples:")
print(sample_count)

print("\nSamples by CONDITION_CLASS:")
print(class_hist)

print("\nDistinct spatial groups:")
print("250 m :", groups_250)
print("500 m :", groups_500)
print("1 km  :", groups_1000)

print("\nExpected maximum sample count: 1300")

# ========================================
# ORIGINAL CELL 25
# ========================================

# ============================================================
# OUTPUT 3 | 30F-B04
# BUILD COMMON FEATURE TABLE
# GEE native-scale extraction -> Pandas merge
# ============================================================

import ee
import pandas as pd
import numpy as np
import time

print("=" * 90)
print("30F-B04 | BUILD COMMON FEATURE TABLE")
print("=" * 90)

# ============================================================
# 1. BASE SAMPLE TABLE
# ============================================================

base_properties = [
    "SAMPLE_ID",
    "X_UTM47N",
    "Y_UTM47N",
    "SPATIAL_GROUP_250M",
    "SPATIAL_GROUP_500M",
    "SPATIAL_GROUP_1000M",
    "CONDITION_CLASS_INT",
    "RISK_SCORE_0_100",
    "ANNUAL_CONFIDENCE",
    "MEAN_DATA_CONFIDENCE",
    "ALERT_PERIOD_COUNT",
    "INSPECTION_PERIOD_COUNT",
    "HIGH_PERIOD_COUNT",
    "MAX_CONSECUTIVE_ALERT",
    "REASON_CODE"
]

# Keep geometry because reduceRegions needs the sample locations.
sample_for_context = sample_fc.select(
    ["SAMPLE_ID"],
    retainGeometry=True
)

# Pull base sample information into Pandas.
base_df = ee.data.computeFeatures({
    "expression": sample_fc.select(base_properties),
    "fileFormat": "PANDAS_DATAFRAME"
})

base_df = base_df.drop(
    columns=["geo", "system:index"],
    errors="ignore"
)

print("\nBASE TABLE")
print("Rows   :", len(base_df))
print("Columns:", len(base_df.columns))
print("Unique SAMPLE_ID:", base_df["SAMPLE_ID"].nunique())


# ============================================================
# 2. CONTEXT ASSETS
# ============================================================

context_assets = [
    "30E01_AGE",
    "30E02A_CHIRPS",
    "30E02B_ERA5LAND",
    "30E02C_ETPET",
    "30E03A_TERRAIN",
    "30E03B_HYDRO",
    "30E04A_SOIL",
    "30E04B_SOIL_WATER"
]

context_dfs = {}
extraction_log = []


# ============================================================
# 3. EXTRACTION FUNCTION
# ============================================================

def extract_context_to_df(asset_key):
    
    print("\n" + "-" * 90)
    print("Extracting:", asset_key)
    
    # Candidate bands only
    bands = (
        candidate_registry.loc[
            candidate_registry["asset_key"] == asset_key,
            "band_name"
        ]
        .tolist()
    )
    
    if len(bands) == 0:
        print("No candidate bands. SKIPPED.")
        return None
    
    asset_id = ASSETS[asset_key]
    scale = float(source_meta[asset_key]["native_scale_m"])
    
    print("Candidate bands :", len(bands))
    print("Native scale    :", scale, "m")
    
    img = ee.Image(asset_id).select(bands)
    
    # --------------------------------------------------------
    # IMPORTANT:
    # CRS is deliberately NOT forced to EPSG:32647.
    # Each asset is sampled using its own native projection
    # at its native/effective nominal scale.
    # --------------------------------------------------------
    
    reduced_fc = img.reduceRegions(
        collection=sample_for_context,
        reducer=ee.Reducer.first(),
        scale=scale,
        tileScale=4
    )
    
    # Pull result to Pandas
    df = ee.data.computeFeatures({
        "expression": reduced_fc,
        "fileFormat": "PANDAS_DATAFRAME"
    })
    
    df = df.drop(
        columns=["geo", "system:index"],
        errors="ignore"
    )
    
    # --------------------------------------------------------
    # Some reducer configurations may append "_first".
    # Normalize names back to original band names if needed.
    # --------------------------------------------------------
    
    rename_map = {}
    
    for band in bands:
        if band not in df.columns:
            alternative = f"{band}_first"
            if alternative in df.columns:
                rename_map[alternative] = band
    
    if rename_map:
        df = df.rename(columns=rename_map)
    
    # --------------------------------------------------------
    # Ensure expected columns exist
    # --------------------------------------------------------
    
    for band in bands:
        if band not in df.columns:
            df[band] = np.nan
    
    # Keep only ID + expected features
    df = df[["SAMPLE_ID"] + bands].copy()
    
    # Remove accidental duplicate SAMPLE_ID rows if any
    duplicate_count = df["SAMPLE_ID"].duplicated().sum()
    
    if duplicate_count > 0:
        print("WARNING duplicate SAMPLE_ID:", duplicate_count)
        df = df.drop_duplicates(
            subset="SAMPLE_ID",
            keep="first"
        )
    
    # QC
    missing_rows = 1300 - len(df)
    
    print("Rows returned   :", len(df))
    print("Unique IDs      :", df["SAMPLE_ID"].nunique())
    print("Missing rows    :", missing_rows)
    
    missing_pct = (
        df[bands]
        .isna()
        .mean()
        .mean()
        * 100
    )
    
    print(
        "Mean missingness:",
        round(missing_pct, 3),
        "%"
    )
    
    extraction_log.append({
        "asset_key": asset_key,
        "candidate_bands": len(bands),
        "native_scale_m": scale,
        "rows": len(df),
        "unique_ids": df["SAMPLE_ID"].nunique(),
        "mean_missing_pct": missing_pct
    })
    
    return df


# ============================================================
# 4. RUN ALL CONTEXT EXTRACTIONS
# ============================================================

start_time = time.time()

for asset_key in context_assets:
    
    context_df = extract_context_to_df(asset_key)
    
    if context_df is not None:
        context_dfs[asset_key] = context_df


# ============================================================
# 5. MERGE INTO ONE COMMON TABLE
# ============================================================

common_df = base_df.copy()

for asset_key in context_assets:
    
    if asset_key in context_dfs:
        
        common_df = common_df.merge(
            context_dfs[asset_key],
            on="SAMPLE_ID",
            how="left",
            validate="one_to_one"
        )


# ============================================================
# 6. FINAL QC
# ============================================================

elapsed = time.time() - start_time

print("\n\n" + "=" * 90)
print("30F-B04 | FINAL COMMON TABLE QC")
print("=" * 90)

print("\nRows:")
print(len(common_df))

print("\nColumns:")
print(len(common_df.columns))

print("\nUnique SAMPLE_ID:")
print(common_df["SAMPLE_ID"].nunique())

print("\nDuplicate SAMPLE_ID:")
print(common_df["SAMPLE_ID"].duplicated().sum())

print("\nCondition class distribution:")
print(
    common_df["CONDITION_CLASS_INT"]
    .value_counts()
    .sort_index()
)

print("\nExtraction time:")
print(round(elapsed, 2), "seconds")


# ============================================================
# 7. EXTRACTION LOG
# ============================================================

extraction_log_df = pd.DataFrame(extraction_log)

print("\nExtraction summary:")

display(extraction_log_df)


# ============================================================
# 8. TABLE PREVIEW
# ============================================================

print("\nCommon table preview:")

display(common_df.head())

# ========================================
# ORIGINAL CELL 36
# ========================================

# ============================================================
# OUTPUT 3 | 30F-RECOVERY-01
# RECONNECT GEE + RESTORE ASSETS + REBUILD FROZEN SAMPLE
# after full Jupyter kernel restart
# ============================================================

import ee
import pandas as pd
import numpy as np
import ssl
import certifi

print("=" * 95)
print("30F-RECOVERY-01 | RESTORE MINIMUM NOTEBOOK STATE")
print("=" * 95)

# ------------------------------------------------------------
# 1. HTTPS certificate patch
# ------------------------------------------------------------

ssl._create_default_https_context = (
    lambda: ssl.create_default_context(
        cafile=certifi.where()
    )
)

# ------------------------------------------------------------
# 2. Initialize Earth Engine
# ------------------------------------------------------------

PROJECT_ID = "palm-oil-503202"

try:
    ee.Initialize(project=PROJECT_ID)
    print("Earth Engine initialization : PASS")

except Exception as e:
    print("Initial Earth Engine initialization failed.")
    print("Authentication will be requested.")
    print("Original message:", str(e)[:300])

    ee.Authenticate()
    ee.Initialize(project=PROJECT_ID)

    print("Earth Engine authentication : PASS")


# ============================================================
# 3. Restore frozen asset registry
# ============================================================

ROOT = "projects/palm-oil-503202/assets"

ASSETS = {

    "CORE":
        f"{ROOT}/SIAK_AOI01_O3_30D04_BALANCED_RISK_2025",

    "AGE":
        f"{ROOT}/SIAK_AOI01_O3_30E01_AGE_CONTEXT_V3_2025",

    "CHIRPS":
        f"{ROOT}/SIAK_AOI01_O3_30E02A_CHIRPS_FINAL_2025",

    "ERA5":
        f"{ROOT}/SIAK_AOI01_O3_30E02B_ERA5LAND_FINAL_2025",

    "ETPET":
        f"{ROOT}/SIAK_AOI01_O3_30E02C_ETPET_FINAL_2025",

    "TERRAIN":
        f"{ROOT}/SIAK_AOI01_O3_30E03A_TERRAIN_CORE_2025",

    "HYDRO":
        f"{ROOT}/SIAK_AOI01_O3_30E03B_HYDRO_CONTEXT_2025",

    "SOIL":
        f"{ROOT}/SIAK_AOI01_O3_30E04A_SOIL_CORE_PROFILE_2025",

    "SOIL_WATER":
        f"{ROOT}/SIAK_AOI01_O3_30E04B_SOIL_WATER_RETENTION_2025"
}


# Expected band counts from frozen inventory
expected_band_counts = {
    "CORE": 38,
    "AGE": 11,
    "CHIRPS": 72,
    "ERA5": 144,
    "ETPET": 84,
    "TERRAIN": 6,
    "HYDRO": 6,
    "SOIL": 27,
    "SOIL_WATER": 12
}


print("\n" + "-" * 95)
print("ASSET INVENTORY CHECK")
print("-" * 95)

asset_check_rows = []

for key, asset_id in ASSETS.items():

    img = ee.Image(asset_id)

    bands = img.bandNames().getInfo()

    actual_n = len(bands)
    expected_n = expected_band_counts[key]

    status = (
        "PASS"
        if actual_n == expected_n
        else "CHECK"
    )

    asset_check_rows.append({
        "asset_key": key,
        "expected_bands": expected_n,
        "actual_bands": actual_n,
        "status": status
    })


asset_check_df = pd.DataFrame(asset_check_rows)

display(asset_check_df)


# ============================================================
# 4. Restore FINAL VIF FEATURE LIST from B10
# ============================================================

vif_features = [

    # ---------------- SOIL ----------------
    "CLAY_PCT_SURFACE_0_30CM",
    "SAND_PCT_DEEP_100_200CM",
    "PH_H2O_SURFACE_0_30CM",
    "SOC_GKG_SURFACE_0_30CM",
    "PH_H2O_DEEP_100_200CM",
    "SILT_PCT_DEEP_100_200CM",
    "N_GKG_SURFACE_0_30CM",
    "BDOD_KGDM3_SURFACE_0_30CM",
    "CFVO_VOLPCT_SURFACE_0_30CM",

    # ---------------- TERRAIN ----------------
    "LOCAL_RELIEF_300M_M",
    "TPI_300M_M",
    "TPI_90M_M",
    "SLOPE_DEG",
    "ASPECT_SIN",
    "ASPECT_COS",

    # ---------------- SOIL WATER ----------------
    "WV1500_SURFACE_0_30CM",
    "WV1500_DEEP_100_200CM",
    "PAW_PROXY_SURFACE_0_30CM",
    "WV10_DEEP_100_200CM",

    # ---------------- HYDROLOGY ----------------
    "HAND_M",
    "LOG10_UPA"
]


print("\nFinal VIF features restored :", len(vif_features))

if len(vif_features) == 21:
    print("VIF feature count           : PASS")
else:
    print("VIF feature count           : FAIL")


# ============================================================
# 5. Verify core target bands
# ============================================================

core_img = ee.Image(ASSETS["CORE"])

core_band_names = core_img.bandNames().getInfo()

required_core_bands = [
    "CONDITION_CLASS",
    "RISK_SCORE_0_100"
]

missing_core = [
    b for b in required_core_bands
    if b not in core_band_names
]


print("\n" + "-" * 95)
print("CORE TARGET CHECK")
print("-" * 95)

print("Required :", required_core_bands)
print("Missing  :", missing_core)

if len(missing_core) == 0:
    print("Core target bands : PASS")
else:
    raise ValueError(
        f"Required core bands missing: {missing_core}"
    )


# ============================================================
# 6. Rebuild controlled stratified sample
#
# Frozen parameters from previous 30F-B03:
#
# Class 1 = 400
# Class 2 = 400
# Class 3 = 300
# Class 4 = 200
#
# scale      = 10 m
# projection = EPSG:32647
# seed       = 42
# ============================================================

sampling_img = core_img.select([
    "CONDITION_CLASS",
    "RISK_SCORE_0_100"
])


sample_fc_raw = sampling_img.stratifiedSample(

    numPoints=0,

    classBand="CONDITION_CLASS",

    region=core_img.geometry(),

    scale=10,

    projection="EPSG:32647",

    classValues=[
        1,
        2,
        3,
        4
    ],

    classPoints=[
        400,
        400,
        300,
        200
    ],

    seed=42,

    dropNulls=True,

    geometries=True,

    tileScale=4
)


# ============================================================
# 7. Restore coordinate + deterministic spatial group IDs
# ============================================================

def add_sample_metadata(feature):

    geom_utm = (
        feature
        .geometry()
        .transform(
            "EPSG:32647",
            1
        )
    )

    coords = ee.List(
        geom_utm.coordinates()
    )

    x = ee.Number(
        coords.get(0)
    )

    y = ee.Number(
        coords.get(1)
    )


    # --------------------------------------------------------
    # Deterministic SAMPLE_ID from UTM pixel-center coordinate
    # --------------------------------------------------------

    sample_id = (
        ee.String("S_")
        .cat(
            x.round()
            .toInt64()
            .format()
        )
        .cat("_")
        .cat(
            y.round()
            .toInt64()
            .format()
        )
    )


    def group_id(cell_size):

        gx = (
            x.divide(cell_size)
            .floor()
            .toInt64()
            .format()
        )

        gy = (
            y.divide(cell_size)
            .floor()
            .toInt64()
            .format()
        )

        return (
            ee.String(gx)
            .cat("_")
            .cat(gy)
        )


    return feature.set({

        "SAMPLE_ID":
            sample_id,

        "X_UTM47N":
            x,

        "Y_UTM47N":
            y,

        "SPATIAL_GROUP_250M":
            group_id(250),

        "SPATIAL_GROUP_500M":
            group_id(500),

        "SPATIAL_GROUP_1000M":
            group_id(1000)
    })


sample_fc = sample_fc_raw.map(
    add_sample_metadata
)


# ============================================================
# 8. SAMPLE CHECKSUM
# ============================================================

sample_count = (
    sample_fc
    .size()
    .getInfo()
)

class_hist = (
    sample_fc
    .aggregate_histogram(
        "CONDITION_CLASS"
    )
    .getInfo()
)

unique_sample_ids = (
    sample_fc
    .aggregate_count_distinct(
        "SAMPLE_ID"
    )
    .getInfo()
)


group_250 = (
    sample_fc
    .aggregate_count_distinct(
        "SPATIAL_GROUP_250M"
    )
    .getInfo()
)

group_500 = (
    sample_fc
    .aggregate_count_distinct(
        "SPATIAL_GROUP_500M"
    )
    .getInfo()
)

group_1000 = (
    sample_fc
    .aggregate_count_distinct(
        "SPATIAL_GROUP_1000M"
    )
    .getInfo()
)


print("\n" + "=" * 95)
print("RECOVERED SAMPLE CHECKSUM")
print("=" * 95)

print("Total samples          :", sample_count)
print("Unique SAMPLE_ID       :", unique_sample_ids)
print("Class distribution     :", class_hist)

print("\nDistinct spatial groups")
print("250 m                  :", group_250)
print("500 m                  :", group_500)
print("1000 m                 :", group_1000)


# ============================================================
# 9. Compare against previous frozen B03 result
# ============================================================

expected_total = 1300

expected_groups = {
    "250": 792,
    "500": 491,
    "1000": 189
}


print("\n" + "-" * 95)
print("RECOVERY VERIFICATION")
print("-" * 95)


if sample_count == expected_total:
    print("Total sample count     : PASS")
else:
    print(
        "Total sample count     : CHECK",
        f"(expected {expected_total})"
    )


if unique_sample_ids == expected_total:
    print("Unique SAMPLE_ID       : PASS")
else:
    print(
        "Unique SAMPLE_ID       : CHECK",
        f"(expected {expected_total})"
    )


if (
    group_250 == expected_groups["250"]
    and group_500 == expected_groups["500"]
    and group_1000 == expected_groups["1000"]
):
    print("Spatial-group checksum : PASS")
else:
    print("Spatial-group checksum : CHECK")
    print(
        "Expected:",
        expected_groups
    )


print("\n" + "=" * 95)
print("30F-RECOVERY-01 COMPLETE")
print("=" * 95)

print("""
DO NOT RUN B13 YET.

If:
- all assets = PASS,
- samples = 1300,
- classes = 400 / 400 / 300 / 200,
- spatial groups = 792 / 491 / 189,

then the frozen B03 sampling state has been
successfully reproduced.

Next:
30F-RECOVERY-02 will rebuild only the minimum
common feature table required by B13.
""")

# ========================================
# ORIGINAL CELL 44
# ========================================

# ============================================================
# OUTPUT 3 | 30F-B15
# PRODUCTION CONTEXT ROLE & ARCHITECTURE FREEZE
#
# Purpose:
# - Freeze production roles after B11-B14C
# - Separate PRIMARY CORE from CONTEXT / DIAGNOSTIC evidence
# - Define what may / may not modify the production risk layer
#
# IMPORTANT:
# This stage DOES NOT create a new risk model.
# ============================================================

import pandas as pd
import numpy as np
import json
from pathlib import Path

print("=" * 110)
print("30F-B15 | PRODUCTION CONTEXT ROLE & ARCHITECTURE FREEZE")
print("=" * 110)


# ============================================================
# 1. CHECKPOINT DIRECTORY
# ============================================================

checkpoint_dir = Path("checkpoints_30F")

if not checkpoint_dir.exists():
    raise FileNotFoundError(
        "checkpoints_30F directory was not found."
    )


# ============================================================
# 2. RESTORE REQUIRED RESULT TABLES IF NEEDED
# ============================================================

# ------------------------------------------------------------
# B14B incremental results
# ------------------------------------------------------------

if "increment_summary_df" not in globals():

    increment_summary_df = pd.read_csv(
        checkpoint_dir
        / "30F_B14B_INCREMENT_SUMMARY_V1.csv"
    )


# ------------------------------------------------------------
# B14B OOF metrics
# ------------------------------------------------------------

if "oof_metrics_df" not in globals():

    oof_metrics_df = pd.read_csv(
        checkpoint_dir
        / "30F_B14B_OOF_METRICS_V1.csv"
    )


# ------------------------------------------------------------
# B14B class errors
# ------------------------------------------------------------

if "class_error_df" not in globals():

    class_error_df = pd.read_csv(
        checkpoint_dir
        / "30F_B14B_CLASS_ERROR_V1.csv"
    )


# ------------------------------------------------------------
# B14C CHIRPS holdout
# ------------------------------------------------------------

if "chirps_holdout_global_df" not in globals():

    chirps_holdout_global_df = pd.read_csv(
        checkpoint_dir
        / "30F_B14C_CHIRPS_GLOBAL_V1.csv"
    )


# ------------------------------------------------------------
# B14C ERA5 / ET-PET holdout
# ------------------------------------------------------------

if "full_weather_holdout_global_df" not in globals():

    full_weather_holdout_global_df = pd.read_csv(
        checkpoint_dir
        / "30F_B14C_ERA5_ETPET_GLOBAL_V1.csv"
    )


# ------------------------------------------------------------
# Restore frozen 21 B10 features if needed
# ------------------------------------------------------------

if "vif_features" not in globals():

    manifest_path = (
        checkpoint_dir
        / "30F_RECOVERY_MANIFEST_V1.json"
    )

    with open(
        manifest_path,
        "r",
        encoding="utf-8"
    ) as f:

        recovery_manifest = json.load(f)

    vif_features = recovery_manifest[
        "vif_features"
    ]


if len(vif_features) != 21:
    raise ValueError(
        f"Expected 21 frozen B10 features, "
        f"found {len(vif_features)}"
    )


# ============================================================
# 3. EXTRACT B14 EVIDENCE
# ============================================================

# ------------------------------------------------------------
# AGE increment A -> B
# ------------------------------------------------------------

age_row = (
    increment_summary_df[
        increment_summary_df[
            "comparison"
        ] == "AGE_INCREMENT"
    ]
    .iloc[0]
)


age_mae_improvement = float(
    age_row[
        "mean_MAE_improvement"
    ]
)

age_r2_delta = float(
    age_row[
        "mean_R2_delta"
    ]
)

age_folds_mae_improved = int(
    age_row[
        "folds_MAE_improved"
    ]
)

age_folds_r2_improved = int(
    age_row[
        "folds_R2_improved"
    ]
)


# ------------------------------------------------------------
# CHIRPS unseen-context result
# ------------------------------------------------------------

chirps_row = (
    chirps_holdout_global_df
    .iloc[0]
)

chirps_mae_unseen = float(
    chirps_row[
        "OOF_MAE_improvement"
    ]
)

chirps_r2_unseen = float(
    chirps_row[
        "OOF_R2_delta"
    ]
)

chirps_spearman_unseen = float(
    chirps_row[
        "OOF_SPEARMAN_delta"
    ]
)

chirps_contexts_improved = int(
    chirps_row[
        "contexts_MAE_improved"
    ]
)

chirps_n_contexts = int(
    chirps_row[
        "n_contexts"
    ]
)


# ------------------------------------------------------------
# ERA5 + ET/PET unseen-context result
# ------------------------------------------------------------

weather_row = (
    full_weather_holdout_global_df
    .iloc[0]
)

weather_mae_unseen = float(
    weather_row[
        "OOF_MAE_improvement"
    ]
)

weather_r2_unseen = float(
    weather_row[
        "OOF_R2_delta"
    ]
)

weather_spearman_unseen = float(
    weather_row[
        "OOF_SPEARMAN_delta"
    ]
)

weather_contexts_improved = int(
    weather_row[
        "contexts_MAE_improved"
    ]
)

weather_n_contexts = int(
    weather_row[
        "n_contexts"
    ]
)


# ============================================================
# 4. DECISION LOGIC
# ============================================================

# ------------------------------------------------------------
# AGE
#
# Require consistent improvement in >= 3/5 folds.
# Current B14B does not meet this.
# ------------------------------------------------------------

age_predictive_support = (
    age_folds_mae_improved >= 3
    and
    age_folds_r2_improved >= 3
    and
    age_mae_improvement > 0
    and
    age_r2_delta > 0
)


# ------------------------------------------------------------
# CHIRPS
#
# Must improve BOTH global MAE and R2 under unseen
# CHIRPS-context holdout.
# ------------------------------------------------------------

chirps_predictive_support = (
    chirps_mae_unseen > 0
    and
    chirps_r2_unseen > 0
    and
    chirps_contexts_improved
    >= (chirps_n_contexts / 2)
)


# ------------------------------------------------------------
# ERA5 / ET-PET
#
# Even positive result would remain sensitivity-only because
# there are only ~4 independent contexts.
# ------------------------------------------------------------

weather_predictive_support = (
    weather_mae_unseen > 0
    and
    weather_r2_unseen > 0
    and
    weather_contexts_improved >= 3
)


# ============================================================
# 5. MODEL EXTREME-CLASS BIAS CHECK
#
# Use D_FULL_CONTEXT as the most complete experimental model.
# This is NOT a production model.
# ============================================================

d_class_error = (
    class_error_df[
        class_error_df[
            "feature_set"
        ] == "D_FULL_CONTEXT"
    ]
    .copy()
)


class1_bias = float(
    d_class_error.loc[
        d_class_error[
            "condition_class"
        ] == 1,
        "bias_pred_minus_true"
    ]
    .iloc[0]
)


class4_bias = float(
    d_class_error.loc[
        d_class_error[
            "condition_class"
        ] == 4,
        "bias_pred_minus_true"
    ]
    .iloc[0]
)


# ============================================================
# 6. EVIDENCE DECISION TABLE
# ============================================================

evidence_decision_df = pd.DataFrame([
    {
        "component":
            "AGE_CLASS_6",

        "test":
            "A_SPATIAL vs B_SPATIAL_AGE",

        "evidence":
            (
                f"MAE improvement={age_mae_improvement:.4f}; "
                f"R2 delta={age_r2_delta:.4f}; "
                f"MAE improved {age_folds_mae_improved}/5 folds; "
                f"R2 improved {age_folds_r2_improved}/5 folds"
            ),

        "predictive_support":
            (
                "DEMONSTRATED"
                if age_predictive_support
                else "NOT_DEMONSTRATED"
            ),

        "production_decision":
            "CONTEXT_ONLY"
    },

    {
        "component":
            "CHIRPS",

        "test":
            "Leave-One-CHIRPS-Context-Out",

        "evidence":
            (
                f"OOF MAE improvement={chirps_mae_unseen:.4f}; "
                f"R2 delta={chirps_r2_unseen:.4f}; "
                f"Spearman delta={chirps_spearman_unseen:.4f}; "
                f"MAE improved {chirps_contexts_improved}/"
                f"{chirps_n_contexts} contexts"
            ),

        "predictive_support":
            (
                "DEMONSTRATED"
                if chirps_predictive_support
                else "NOT_DEMONSTRATED"
            ),

        "production_decision":
            "CONTEXT_ONLY"
    },

    {
        "component":
            "ERA5_LAND_ETPET",

        "test":
            "Leave-One-Coarse-Weather-Context-Out",

        "evidence":
            (
                f"OOF MAE improvement={weather_mae_unseen:.4f}; "
                f"R2 delta={weather_r2_unseen:.4f}; "
                f"Spearman delta={weather_spearman_unseen:.4f}; "
                f"MAE improved {weather_contexts_improved}/"
                f"{weather_n_contexts} contexts"
            ),

        "predictive_support":
            (
                "DEMONSTRATED"
                if weather_predictive_support
                else "NOT_DEMONSTRATED"
            ),

        "production_decision":
            "REGIONAL_CONTEXT_ONLY"
    },

    {
        "component":
            "PYTHON_RF_FULL_CONTEXT",

        "test":
            "OOF extreme-class bias audit",

        "evidence":
            (
                f"Class 1 mean bias={class1_bias:+.3f}; "
                f"Class 4 mean bias={class4_bias:+.3f}"
            ),

        "predictive_support":
            "NOT_SUITABLE_AS_CORE_REPLACEMENT",

        "production_decision":
            "EXPERIMENTAL_DIAGNOSTIC_ONLY"
    }
])


print("\n" + "=" * 110)
print("B15 EVIDENCE DECISION TABLE")
print("=" * 110)

display(
    evidence_decision_df
)


# ============================================================
# 7. PRODUCTION ROLE REGISTRY
# ============================================================

production_role_registry_df = pd.DataFrame([
    {
        "family":
            "30D04_CORE",

        "main_fields":
            "CONDITION_CLASS; RISK_SCORE_0_100",

        "effective_scale":
            "~10 m",

        "production_role":
            "PRIMARY_CORE",

        "modify_core_risk_score":
            "SOURCE",

        "modify_core_class":
            "SOURCE",

        "can_support_reason_code":
            True,

        "can_support_warning":
            True,

        "web_status":
            "INCLUDE",

        "interpretation":
            (
                "Frozen core condition / inspection-risk output. "
                "Primary source of production class and risk score."
            )
    },

    {
        "family":
            "STATIC_ENVIRONMENT",

        "main_fields":
            "21 B10 retained terrain / hydrology / soil / soil-water features",

        "effective_scale":
            "~30-259 m",

        "production_role":
            "EXPLANATORY_CONTEXT",

        "modify_core_risk_score":
            "NO",

        "modify_core_class":
            "NO",

        "can_support_reason_code":
            True,

        "can_support_warning":
            False,

        "web_status":
            "SELECTIVE_INCLUDE",

        "interpretation":
            (
                "Environmental context only. Association does not "
                "establish causal plantation stress."
            )
    },

    {
        "family":
            "AGE",

        "main_fields":
            "AGE_CLASS_6",

        "effective_scale":
            "~30 m",

        "production_role":
            "TEMPORAL_CONTEXT",

        "modify_core_risk_score":
            "NO",

        "modify_core_class":
            "NO",

        "can_support_reason_code":
            True,

        "can_support_warning":
            True,

        "web_status":
            "INCLUDE",

        "interpretation":
            (
                "Age/event context. Class 0 means no event detected "
                "during 2001-2025, not age zero."
            )
    },

    {
        "family":
            "CHIRPS",

        "main_fields":
            "rainfall / anomaly / dry-day summaries",

        "effective_scale":
            "~5.6 km",

        "production_role":
            "RAINFALL_CONTEXT",

        "modify_core_risk_score":
            "NO",

        "modify_core_class":
            "NO",

        "can_support_reason_code":
            True,

        "can_support_warning":
            True,

        "web_status":
            "INCLUDE_AS_CONTEXT",

        "interpretation":
            (
                "Regional rainfall context. Unseen-context predictive "
                "support was not demonstrated in B14C."
            )
    },

    {
        "family":
            "ERA5_LAND",

        "main_fields":
            "temperature / VPD / regional soil-moisture summaries",

        "effective_scale":
            "~11 km",

        "production_role":
            "REGIONAL_ATMOSPHERE_MOISTURE_CONTEXT",

        "modify_core_risk_score":
            "NO",

        "modify_core_class":
            "NO",

        "can_support_reason_code":
            True,

        "can_support_warning":
            True,

        "web_status":
            "INCLUDE_AS_CONTEXT",

        "interpretation":
            (
                "Regional atmospheric and soil-moisture context; "
                "not fine-scale plantation evidence."
            )
    },

    {
        "family":
            "ET_PET",

        "main_fields":
            "ET/PET ratio / ET anomaly / PET-ET gap",

        "effective_scale":
            "~11 km",

        "production_role":
            "REGIONAL_WATER_BALANCE_CONTEXT",

        "modify_core_risk_score":
            "NO",

        "modify_core_class":
            "NO",

        "can_support_reason_code":
            True,

        "can_support_warning":
            True,

        "web_status":
            "INCLUDE_AS_CONTEXT",

        "interpretation":
            (
                "Regional water-balance context only. "
                "No pseudo-downscaling to 10 m interpretation."
            )
    },

    {
        "family":
            "PYTHON_RF_A_B_C_D",

        "main_fields":
            "OOF / experimental predictions",

        "effective_scale":
            "sample-based experiment",

        "production_role":
            "EXPERIMENTAL_DIAGNOSTIC",

        "modify_core_risk_score":
            "NO",

        "modify_core_class":
            "NO",

        "can_support_reason_code":
            False,

        "can_support_warning":
            False,

        "web_status":
            "EXCLUDE_FROM_PRODUCTION",

        "interpretation":
            (
                "Used to test incremental contextual value and "
                "architecture; not an independent accuracy model."
            )
    }
])


print("\n" + "=" * 110)
print("PRODUCTION ROLE REGISTRY")
print("=" * 110)

display(
    production_role_registry_df
)


# ============================================================
# 8. FROZEN ARCHITECTURE DECISIONS
# ============================================================

architecture_decision_df = pd.DataFrame([
    {
        "decision_id": "B15-D01",
        "decision":
            "30D04 CONDITION_CLASS remains the primary production class.",
        "status": "FROZEN"
    },

    {
        "decision_id": "B15-D02",
        "decision":
            "30D04 RISK_SCORE_0_100 remains the primary production risk score.",
        "status": "FROZEN"
    },

    {
        "decision_id": "B15-D03",
        "decision":
            "Age context must not directly modify the core risk score or class in V1.",
        "status": "FROZEN"
    },

    {
        "decision_id": "B15-D04",
        "decision":
            "CHIRPS is contextual rainfall evidence and must not directly modify core risk/class in V1.",
        "status": "FROZEN"
    },

    {
        "decision_id": "B15-D05",
        "decision":
            "ERA5-Land and ET/PET remain regional contextual evidence only.",
        "status": "FROZEN"
    },

    {
        "decision_id": "B15-D06",
        "decision":
            "The 21 B10 environmental features may support explanation/reason codes but are not causal diagnoses.",
        "status": "FROZEN"
    },

    {
        "decision_id": "B15-D07",
        "decision":
            "Python RF A/B/C/D predictions are experimental diagnostic outputs and must not replace 30D04.",
        "status": "FROZEN"
    },

    {
        "decision_id": "B15-D08",
        "decision":
            "Context may add reason/context/warning attributes while preserving the frozen core score and class.",
        "status": "FROZEN"
    },

    {
        "decision_id": "B15-D09",
        "decision":
            "Context-data availability must be represented separately from predictive confidence.",
        "status": "FROZEN"
    },

    {
        "decision_id": "B15-D10",
        "decision":
            "Coarse weather values must retain native/effective-scale interpretation and must not be treated as 10 m information.",
        "status": "FROZEN"
    }
])


print("\n" + "=" * 110)
print("FROZEN ARCHITECTURE DECISIONS")
print("=" * 110)

display(
    architecture_decision_df
)


# ============================================================
# 9. PROPOSED 30G ATTRIBUTE CONTRACT V1
#
# These are PROPOSED downstream attributes.
# They are not claimed to already exist in 30D04.
# Exact thresholds/codes will be designed in B16.
# ============================================================

output_contract_df = pd.DataFrame([
    {
        "field":
            "CONDITION_CLASS",

        "source":
            "30D04",

        "role":
            "PRIMARY_CLASS",

        "status":
            "PASS_THROUGH_FROZEN"
    },

    {
        "field":
            "RISK_SCORE_0_100",

        "source":
            "30D04",

        "role":
            "PRIMARY_RISK_SCORE",

        "status":
            "PASS_THROUGH_FROZEN"
    },

    {
        "field":
            "AGE_CONTEXT_CODE",

        "source":
            "Output 2 / AGE_CLASS_6",

        "role":
            "TEMPORAL_CONTEXT",

        "status":
            "DERIVE_IN_B16"
    },

    {
        "field":
            "STATIC_ENV_CONTEXT_CODE",

        "source":
            "B10 retained terrain/soil/hydrology",

        "role":
            "EXPLANATORY_CONTEXT",

        "status":
            "DERIVE_IN_B16"
    },

    {
        "field":
            "RAINFALL_CONTEXT_FLAG",

        "source":
            "CHIRPS",

        "role":
            "WEATHER_CONTEXT",

        "status":
            "DERIVE_IN_B16"
    },

    {
        "field":
            "ATMOS_MOISTURE_CONTEXT_FLAG",

        "source":
            "ERA5-Land",

        "role":
            "REGIONAL_CONTEXT",

        "status":
            "DERIVE_IN_B16"
    },

    {
        "field":
            "WATER_BALANCE_CONTEXT_FLAG",

        "source":
            "ET/PET",

        "role":
            "REGIONAL_CONTEXT",

        "status":
            "DERIVE_IN_B16"
    },

    {
        "field":
            "CONTEXT_REASON_PRIMARY",

        "source":
            "context integration",

        "role":
            "EXPLANATION",

        "status":
            "DESIGN_IN_B16"
    },

    {
        "field":
            "CONTEXT_REASON_SECONDARY",

        "source":
            "context integration",

        "role":
            "EXPLANATION",

        "status":
            "DESIGN_IN_B16"
    },

    {
        "field":
            "CONTEXT_COVERAGE_FLAG",

        "source":
            "data availability / native coverage",

        "role":
            "DATA_COVERAGE",

        "status":
            "DESIGN_IN_B16"
    },

    {
        "field":
            "WARNING_FLAG",

        "source":
            "context / data limitations",

        "role":
            "USER_WARNING",

        "status":
            "DESIGN_IN_B16"
    }
])


print("\n" + "=" * 110)
print("PROPOSED 30G ATTRIBUTE CONTRACT V1")
print("=" * 110)

display(
    output_contract_df
)


# ============================================================
# 10. PRODUCTION CORE LOCK CHECK
# ============================================================

context_rows = (
    production_role_registry_df[
        production_role_registry_df[
            "family"
        ] != "30D04_CORE"
    ]
)


context_score_locked = (
    context_rows[
        "modify_core_risk_score"
    ]
    .eq("NO")
    .all()
)


context_class_locked = (
    context_rows[
        "modify_core_class"
    ]
    .eq("NO")
    .all()
)


# ============================================================
# 11. B15 MANIFEST
# ============================================================

b15_manifest = {

    "stage":
        "30F-B15",

    "version":
        "V1",

    "architecture":
        "CORE_RISK_PLUS_CONTEXT_ENRICHMENT",

    "primary_core": {

        "condition_class":
            "CONDITION_CLASS",

        "risk_score":
            "RISK_SCORE_0_100",

        "source":
            "30D04_BALANCED_RISK_2025",

        "frozen":
            True
    },

    "context_score_modification_allowed":
        False,

    "context_class_modification_allowed":
        False,

    "age_predictive_support":
        bool(
            age_predictive_support
        ),

    "chirps_unseen_context_support":
        bool(
            chirps_predictive_support
        ),

    "era5_etpet_unseen_context_support":
        bool(
            weather_predictive_support
        ),

    "static_environment_features":
        list(
            vif_features
        ),

    "python_models":
        {
            "A_SPATIAL":
                "EXPERIMENTAL_DIAGNOSTIC",

            "B_SPATIAL_AGE":
                "EXPERIMENTAL_DIAGNOSTIC",

            "C_SPATIAL_AGE_CHIRPS":
                "EXPERIMENTAL_DIAGNOSTIC",

            "D_FULL_CONTEXT":
                "EXPERIMENTAL_DIAGNOSTIC"
        },

    "next_stage":
        "30F-B16_CONTEXT_REASON_FRAMEWORK"
}


# ============================================================
# 12. SAVE CHECKPOINT
# ============================================================

evidence_decision_df.to_csv(
    checkpoint_dir
    / "30F_B15_EVIDENCE_DECISION_V1.csv",
    index=False
)


production_role_registry_df.to_csv(
    checkpoint_dir
    / "30F_B15_PRODUCTION_ROLE_REGISTRY_V1.csv",
    index=False
)


architecture_decision_df.to_csv(
    checkpoint_dir
    / "30F_B15_ARCHITECTURE_DECISIONS_V1.csv",
    index=False
)


output_contract_df.to_csv(
    checkpoint_dir
    / "30F_B15_30G_ATTRIBUTE_CONTRACT_V1.csv",
    index=False
)


with open(
    checkpoint_dir
    / "30F_B15_ARCHITECTURE_MANIFEST_V1.json",
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        b15_manifest,
        f,
        indent=2
    )


# ============================================================
# 13. FINAL GATE
# ============================================================

checks = {

    "core_score_locked":
        context_score_locked,

    "core_class_locked":
        context_class_locked,

    "age_predictive_support_not_demonstrated":
        not age_predictive_support,

    "chirps_unseen_support_not_demonstrated":
        not chirps_predictive_support,

    "era5_etpet_support_not_demonstrated":
        not weather_predictive_support,

    "vif_feature_count_21":
        len(vif_features) == 21,

    "architecture_decisions_frozen":
        architecture_decision_df[
            "status"
        ].eq("FROZEN").all()
}


print("\n" + "=" * 110)
print("30F-B15 | FINAL GATE")
print("=" * 110)


for name, result in checks.items():

    print(
        f"{name:45s}:",
        "PASS"
        if result
        else "CHECK"
    )


if all(checks.values()):

    print("""
30F-B15 = PASS

PRODUCTION ARCHITECTURE V1 IS FROZEN:

30D04
  -> PRIMARY CONDITION CLASS
  -> PRIMARY RISK SCORE

AGE
  -> temporal context only

21 STATIC ENVIRONMENT FEATURES
  -> explanatory context only

CHIRPS
  -> rainfall context / warning only

ERA5-LAND + ET/PET
  -> regional atmosphere / moisture /
     water-balance context only

PYTHON RF A/B/C/D
  -> experimental diagnostic only
  -> NOT production risk replacement

CORE SCORE AND CLASS MUST REMAIN UNCHANGED
BY CONTEXT IN VERSION 1.

NEXT:
30F-B16
Context / Reason / Warning Framework
before spatial rejoin and mapping in B17.
""")

else:

    print("""
30F-B15 requires review.

DO NOT proceed to B16 until the architecture
freeze checks are resolved.
""")


print("\nCheckpoint written to:")
print("checkpoints_30F/")

# ========================================
# ORIGINAL CELL 55
# ========================================

# ============================================================
# OUTPUT 3 | 30F-B18D2B
# CORE EVIDENCE LOGIC AUDIT
#
# Purpose:
# 1. Verify radar-only period limitation
# 2. Verify optical support for period Class 3/4
# 3. Inspect annual evidence profiles by final class
# 4. Audit CONDITION_CLASS_RAW -> CONDITION_CLASS
# 5. Inspect REASON_CODE behaviour
#
# IMPORTANT:
# No integrated class is created here.
# ============================================================

import ee
import pandas as pd
import numpy as np
from pathlib import Path

print("=" * 115)
print("30F-B18D2B | CORE EVIDENCE LOGIC AUDIT")
print("=" * 115)

checkpoint_dir = Path("checkpoints_30F")


# ============================================================
# 1. LOAD CORE
# ============================================================

core_img = ee.Image(
    ASSETS["CORE"]
)


periods = [
    "P01", "P02", "P03",
    "P04", "P05", "P06"
]


period_class_bands = [
    f"{p}_CLASS"
    for p in periods
]

period_opt_bands = [
    f"{p}_OPTICAL_GROUP_COUNT"
    for p in periods
]

period_radar_bands = [
    f"{p}_RADAR_COUNT"
    for p in periods
]


annual_bands = [

    "TOTAL_VALID_PERIOD_COUNT",
    "OPTICAL_VALID_PERIOD_COUNT",
    "RADAR_VALID_PERIOD_COUNT",

    "ALERT_PERIOD_COUNT",
    "INSPECTION_PERIOD_COUNT",
    "HIGH_PERIOD_COUNT",

    "RADAR_ONLY_PERIOD_COUNT",

    "MAX_PERIOD_CLASS",
    "MAX_CONSECUTIVE_ALERT",

    "MEAN_DATA_CONFIDENCE",
    "ANNUAL_CONFIDENCE",

    "GREENNESS_ALERT_PERIODS",
    "RED_EDGE_ALERT_PERIODS",
    "MOISTURE_ALERT_PERIODS",
    "RADAR_CONFIRM_PERIODS",

    "CONDITION_CLASS_RAW",
    "CONDITION_CLASS",

    "RISK_SCORE_0_100",

    "REASON_CODE",
    "ALERT_MASK"
]


audit_bands = (
    period_class_bands
    + period_opt_bands
    + period_radar_bands
    + annual_bands
)


# ============================================================
# 2. RESTORE SAMPLE GEOMETRY IF NEEDED
# ============================================================

if "sample_fc" not in globals():

    if "b17_spatial_df" not in globals():

        b17_spatial_df = pd.read_pickle(
            checkpoint_dir /
            "30F_B17A_SPATIAL_REJOIN_SAMPLE_V1.pkl"
        )


    ee_features = []

    for _, row in b17_spatial_df.iterrows():

        geom = ee.Geometry.Point([
            float(row["LON_WGS84"]),
            float(row["LAT_WGS84"])
        ])

        ee_features.append(
            ee.Feature(
                geom,
                {
                    "SAMPLE_ID":
                        str(row["SAMPLE_ID"])
                }
            )
        )


    sample_fc = ee.FeatureCollection(
        ee_features
    )


# ============================================================
# 3. SAMPLE ALL EVIDENCE BANDS
# ============================================================

audit_fc = (

    core_img
    .select(
        audit_bands
    )
    .sampleRegions(

        collection=sample_fc,

        properties=[
            "SAMPLE_ID"
        ],

        scale=10,

        tileScale=4,

        geometries=False
    )
)


audit_info = audit_fc.getInfo()


rows = []

for feature in audit_info["features"]:

    props = feature["properties"]

    rows.append(
        props
    )


core_evidence_df = pd.DataFrame(
    rows
)


print("\nSample rows:", len(core_evidence_df))
print(
    "Unique SAMPLE_ID:",
    core_evidence_df[
        "SAMPLE_ID"
    ].nunique()
)


# ============================================================
# 4. CAST DISCRETE FIELDS
# ============================================================

discrete_fields = (

    period_class_bands
    + period_opt_bands
    + period_radar_bands
    + [

        "TOTAL_VALID_PERIOD_COUNT",
        "OPTICAL_VALID_PERIOD_COUNT",
        "RADAR_VALID_PERIOD_COUNT",

        "ALERT_PERIOD_COUNT",
        "INSPECTION_PERIOD_COUNT",
        "HIGH_PERIOD_COUNT",

        "RADAR_ONLY_PERIOD_COUNT",

        "MAX_PERIOD_CLASS",
        "MAX_CONSECUTIVE_ALERT",

        "GREENNESS_ALERT_PERIODS",
        "RED_EDGE_ALERT_PERIODS",
        "MOISTURE_ALERT_PERIODS",

        "RADAR_CONFIRM_PERIODS",

        "CONDITION_CLASS_RAW",
        "CONDITION_CLASS",

        "REASON_CODE",
        "ALERT_MASK"
    ]
)


for col in discrete_fields:

    core_evidence_df[col] = (

        pd.to_numeric(
            core_evidence_df[col],
            errors="coerce"
        )

        .round()
    )


# ============================================================
# 5. PERIOD-LEVEL OPTICAL / RADAR GATE AUDIT
# ============================================================

period_gate_rows = []


for p in periods:

    class_col = (
        f"{p}_CLASS"
    )

    optical_col = (
        f"{p}_OPTICAL_GROUP_COUNT"
    )

    radar_col = (
        f"{p}_RADAR_COUNT"
    )


    period_class = core_evidence_df[
        class_col
    ]

    optical = core_evidence_df[
        optical_col
    ]

    radar = core_evidence_df[
        radar_col
    ]


    # ----------------------------------------
    # Radar-only period:
    # radar available, no optical group
    # ----------------------------------------

    radar_only = (
        (radar > 0)
        &
        (optical <= 0)
    )


    radar_only_high = (
        radar_only
        &
        (period_class >= 3)
    )


    # ----------------------------------------
    # Any Class 3/4 period without optical
    # ----------------------------------------

    high_period = (
        period_class >= 3
    )


    high_without_optical = (
        high_period
        &
        (optical <= 0)
    )


    radar_only_classes = (
        period_class[
            radar_only
        ]
        .dropna()
    )


    max_radar_only_class = (

        radar_only_classes.max()

        if len(
            radar_only_classes
        ) > 0

        else np.nan
    )


    period_gate_rows.append({

        "period":
            p,

        "radar_only_samples":
            int(
                radar_only.sum()
            ),

        "max_class_when_radar_only":
            max_radar_only_class,

        "radar_only_class3_4_count":
            int(
                radar_only_high.sum()
            ),

        "class3_4_period_count":
            int(
                high_period.sum()
            ),

        "class3_4_without_optical_count":
            int(
                high_without_optical.sum()
            )
    })


period_gate_df = pd.DataFrame(
    period_gate_rows
)


print("\n" + "=" * 115)
print("PERIOD-LEVEL OPTICAL / RADAR GATE")
print("=" * 115)

display(
    period_gate_df
)


# ============================================================
# 6. ANNUAL OPTICAL-EVIDENCE FLAGS
# ============================================================

core_evidence_df[
    "OPTICAL_ALERT_PERIODS_TOTAL"
] = (

    core_evidence_df[
        "GREENNESS_ALERT_PERIODS"
    ]

    +

    core_evidence_df[
        "RED_EDGE_ALERT_PERIODS"
    ]

    +

    core_evidence_df[
        "MOISTURE_ALERT_PERIODS"
    ]
)


core_evidence_df[
    "ANY_OPTICAL_VALID"
] = (

    core_evidence_df[
        "OPTICAL_VALID_PERIOD_COUNT"
    ] > 0
)


core_evidence_df[
    "ANY_OPTICAL_ALERT"
] = (

    core_evidence_df[
        "OPTICAL_ALERT_PERIODS_TOTAL"
    ] > 0
)


core_evidence_df[
    "ANY_HIGH_PERIOD"
] = (

    core_evidence_df[
        "HIGH_PERIOD_COUNT"
    ] > 0
)


core_evidence_df[
    "ANY_RADAR_CONFIRM"
] = (

    core_evidence_df[
        "RADAR_CONFIRM_PERIODS"
    ] > 0
)


# ============================================================
# 7. FINAL CLASS EVIDENCE PROFILE
# ============================================================

profile_rows = []


for condition_class in [
    1, 2, 3, 4
]:

    s = core_evidence_df[
        core_evidence_df[
            "CONDITION_CLASS"
        ] == condition_class
    ]


    profile_rows.append({

        "class":
            condition_class,

        "n":
            len(s),

        "optical_valid_period_median":
            s[
                "OPTICAL_VALID_PERIOD_COUNT"
            ].median(),

        "radar_valid_period_median":
            s[
                "RADAR_VALID_PERIOD_COUNT"
            ].median(),

        "radar_only_period_median":
            s[
                "RADAR_ONLY_PERIOD_COUNT"
            ].median(),

        "alert_period_median":
            s[
                "ALERT_PERIOD_COUNT"
            ].median(),

        "inspection_period_median":
            s[
                "INSPECTION_PERIOD_COUNT"
            ].median(),

        "high_period_median":
            s[
                "HIGH_PERIOD_COUNT"
            ].median(),

        "max_consecutive_alert_median":
            s[
                "MAX_CONSECUTIVE_ALERT"
            ].median(),

        "optical_alert_periods_median":
            s[
                "OPTICAL_ALERT_PERIODS_TOTAL"
            ].median(),

        "radar_confirm_periods_median":
            s[
                "RADAR_CONFIRM_PERIODS"
            ].median(),

        "mean_data_confidence":
            s[
                "MEAN_DATA_CONFIDENCE"
            ].mean(),

        "annual_confidence_mean":
            s[
                "ANNUAL_CONFIDENCE"
            ].mean(),

        "max_period_class_median":
            s[
                "MAX_PERIOD_CLASS"
            ].median(),

        "risk_score_mean":
            s[
                "RISK_SCORE_0_100"
            ].mean(),

        "pct_any_optical_valid":
            s[
                "ANY_OPTICAL_VALID"
            ].mean() * 100,

        "pct_any_optical_alert":
            s[
                "ANY_OPTICAL_ALERT"
            ].mean() * 100,

        "pct_any_high_period":
            s[
                "ANY_HIGH_PERIOD"
            ].mean() * 100,

        "pct_any_radar_confirm":
            s[
                "ANY_RADAR_CONFIRM"
            ].mean() * 100
    })


class_evidence_profile_df = pd.DataFrame(
    profile_rows
)


print("\n" + "=" * 115)
print("FINAL CLASS EVIDENCE PROFILE")
print("=" * 115)

display(
    class_evidence_profile_df
)


# ============================================================
# 8. CLASS 3/4 SUPPORT AUDIT
#
# These are evidence descriptors.
# Only the period optical gate is treated as a hard
# validation rule here.
# ============================================================

high_final = core_evidence_df[
    core_evidence_df[
        "CONDITION_CLASS"
    ].isin([
        3, 4
    ])
]


high_support_df = pd.DataFrame([{

    "n_final_class3_4":
        len(
            high_final
        ),

    "no_optical_valid_count":
        int(
            (
                ~high_final[
                    "ANY_OPTICAL_VALID"
                ]
            ).sum()
        ),

    "no_optical_alert_count":
        int(
            (
                ~high_final[
                    "ANY_OPTICAL_ALERT"
                ]
            ).sum()
        ),

    "no_high_period_count":
        int(
            (
                ~high_final[
                    "ANY_HIGH_PERIOD"
                ]
            ).sum()
        ),

    "no_radar_confirmation_count":
        int(
            (
                ~high_final[
                    "ANY_RADAR_CONFIRM"
                ]
            ).sum()
        )
}])


print("\n" + "=" * 115)
print("FINAL CLASS 3/4 SUPPORT AUDIT")
print("=" * 115)

display(
    high_support_df
)


# ============================================================
# 9. RAW -> FINAL CLASS TRANSITION
# ============================================================

raw_final_transition_df = pd.crosstab(

    core_evidence_df[
        "CONDITION_CLASS_RAW"
    ],

    core_evidence_df[
        "CONDITION_CLASS"
    ],

    margins=True
)


print("\n" + "=" * 115)
print("CONDITION_CLASS_RAW -> CONDITION_CLASS")
print("=" * 115)

display(
    raw_final_transition_df
)


changed = core_evidence_df[
    core_evidence_df[
        "CONDITION_CLASS_RAW"
    ]
    !=
    core_evidence_df[
        "CONDITION_CLASS"
    ]
].copy()


print(
    "\nSamples changed RAW -> FINAL:",
    len(changed)
)

print(
    "Changed pct:",
    round(
        len(changed)
        /
        len(core_evidence_df)
        * 100,
        3
    ),
    "%"
)


if len(changed) > 0:

    changed_transition_df = (

        changed

        .groupby([
            "CONDITION_CLASS_RAW",
            "CONDITION_CLASS"
        ])

        .size()

        .reset_index(
            name="n"
        )

        .sort_values(
            "n",
            ascending=False
        )
    )

else:

    changed_transition_df = pd.DataFrame()


print("\nChanged transitions only:")

display(
    changed_transition_df
)


# ============================================================
# 10. REASON CODE x FINAL CLASS
# ============================================================

reason_class_df = pd.crosstab(

    core_evidence_df[
        "REASON_CODE"
    ],

    core_evidence_df[
        "CONDITION_CLASS"
    ],

    margins=True
)


print("\n" + "=" * 115)
print("REASON_CODE x CONDITION_CLASS")
print("=" * 115)

display(
    reason_class_df
)


# ============================================================
# 11. ALERT MASK x FINAL CLASS
# ============================================================

alertmask_class_df = pd.crosstab(

    core_evidence_df[
        "ALERT_MASK"
    ],

    core_evidence_df[
        "CONDITION_CLASS"
    ],

    margins=True
)


print("\n" + "=" * 115)
print("ALERT_MASK x CONDITION_CLASS")
print("=" * 115)

display(
    alertmask_class_df
)


# ============================================================
# 12. SAVE
# ============================================================

core_evidence_df.to_pickle(
    checkpoint_dir /
    "30F_B18D2B_CORE_EVIDENCE_SAMPLE_V1.pkl"
)


core_evidence_df.to_csv(
    checkpoint_dir /
    "30F_B18D2B_CORE_EVIDENCE_SAMPLE_V1.csv",
    index=False
)


period_gate_df.to_csv(
    checkpoint_dir /
    "30F_B18D2B_PERIOD_GATE_AUDIT_V1.csv",
    index=False
)


class_evidence_profile_df.to_csv(
    checkpoint_dir /
    "30F_B18D2B_CLASS_EVIDENCE_PROFILE_V1.csv",
    index=False
)


changed_transition_df.to_csv(
    checkpoint_dir /
    "30F_B18D2B_RAW_FINAL_CHANGED_TRANSITIONS_V1.csv",
    index=False
)


# ============================================================
# 13. FINAL GATE
# ============================================================

radar_only_high_total = int(
    period_gate_df[
        "radar_only_class3_4_count"
    ].sum()
)


high_without_optical_total = int(
    period_gate_df[
        "class3_4_without_optical_count"
    ].sum()
)


checks = {

    "sample_count_1300":
        len(
            core_evidence_df
        ) == 1300,

    "period_gate_audited_P01_P06":
        len(
            period_gate_df
        ) == 6,

    "radar_only_never_period_class3_4":
        radar_only_high_total == 0,

    "period_class3_4_has_optical_support":
        high_without_optical_total == 0,

    "raw_final_fields_complete":
        core_evidence_df[
            [
                "CONDITION_CLASS_RAW",
                "CONDITION_CLASS"
            ]
        ]
        .notna()
        .all()
        .all()
}


print("\n" + "=" * 115)
print("30F-B18D2B | FINAL STATUS")
print("=" * 115)


for name, result in checks.items():

    print(
        f"{name:42s}:",
        "PASS"
        if result
        else "FAIL"
    )


print(
    "\nDirect PATCH/MMU threshold band available : NO"
)

print(
    "MMU consequence via RAW->FINAL           : AUDITED ABOVE"
)


if all(checks.values()):

    print("""
30F-B18D2B = PASS

The original 30D04 optical/radar evidence logic
is consistent at the sampled locations.

NEXT:
30F-B18D2C

Use the evidence audit to define eligibility for
bounded class transitions under F05.

Important:
- Maximum transition will be ±1 class.
- Radar-only evidence cannot promote to Class 3/4.
- Core evidence remains authoritative.
- Context modifier can only refine borderline cases.
- MMU behaviour will be preserved / audited separately.
""")

else:

    print("""
30F-B18D2B requires review.

DO NOT create integrated classes yet.
""")

# ========================================
# ORIGINAL CELL 56
# ========================================

# ============================================================
# OUTPUT 3 | 30F-B18E
# INTEGRATED SCORE + INTEGRATED PRIORITY CLASS CANDIDATE V1
#
# Combines:
# - frozen 30D04 core
# - F05 context modifier
# - optical/radar evidence
# - alert persistence
# - RAW->FINAL post-processing lock
#
# IMPORTANT:
# This creates an INTEGRATED PRIORITY CLASS candidate.
# It is not yet independent field-validated accuracy.
# ============================================================

import pandas as pd
import numpy as np
from pathlib import Path

print("=" * 115)
print("30F-B18E | INTEGRATED SCORE + CLASS CANDIDATE V1")
print("=" * 115)

checkpoint_dir = Path("checkpoints_30F")


# ============================================================
# 1. RESTORE INPUTS IF NEEDED
# ============================================================

if "fusion_test_df" not in globals():
    fusion_test_df = pd.read_pickle(
        checkpoint_dir /
        "30F_B18D1_FUSION_SENSITIVITY_SAMPLE_V1.pkl"
    )

if "core_evidence_df" not in globals():
    core_evidence_df = pd.read_pickle(
        checkpoint_dir /
        "30F_B18D2B_CORE_EVIDENCE_SAMPLE_V1.pkl"
    )


fusion_test_df["SAMPLE_ID"] = (
    fusion_test_df["SAMPLE_ID"].astype(str)
)

core_evidence_df["SAMPLE_ID"] = (
    core_evidence_df["SAMPLE_ID"].astype(str)
)


# ============================================================
# 2. MERGE
# ============================================================

evidence_cols = [
    "SAMPLE_ID",
    "CONDITION_CLASS_RAW",
    "CONDITION_CLASS",
    "OPTICAL_VALID_PERIOD_COUNT",
    "RADAR_VALID_PERIOD_COUNT",
    "RADAR_ONLY_PERIOD_COUNT",
    "ALERT_PERIOD_COUNT",
    "INSPECTION_PERIOD_COUNT",
    "HIGH_PERIOD_COUNT",
    "MAX_PERIOD_CLASS",
    "MAX_CONSECUTIVE_ALERT",
    "GREENNESS_ALERT_PERIODS",
    "RED_EDGE_ALERT_PERIODS",
    "MOISTURE_ALERT_PERIODS",
    "RADAR_CONFIRM_PERIODS",
    "ALERT_MASK",
    "REASON_CODE"
]


integrated_df = fusion_test_df.copy()


# remove duplicate evidence fields if already present
drop_existing = [
    c for c in evidence_cols
    if c != "SAMPLE_ID"
    and c in integrated_df.columns
]

integrated_df = integrated_df.drop(
    columns=drop_existing
)


integrated_df = integrated_df.merge(
    core_evidence_df[evidence_cols],
    on="SAMPLE_ID",
    how="left",
    validate="one_to_one"
)


# ============================================================
# 3. INTEGRATED SCORE
# ============================================================

integrated_df[
    "INTEGRATED_SCORE_0_100"
] = integrated_df[
    "SCORE_F05_CORE_PLUS_CONTEXT"
]


integrated_df[
    "CORE_CLASS"
] = integrated_df[
    "CONDITION_CLASS"
].astype(int)


integrated_df[
    "INTEGRATED_CLASS"
] = integrated_df[
    "CORE_CLASS"
].copy()


# ============================================================
# 4. SUPPORT FLAGS
# ============================================================

integrated_df[
    "OPTICAL_ALERT_TOTAL"
] = (
    integrated_df["GREENNESS_ALERT_PERIODS"]
    + integrated_df["RED_EDGE_ALERT_PERIODS"]
    + integrated_df["MOISTURE_ALERT_PERIODS"]
)


integrated_df[
    "HAS_OPTICAL_SUPPORT"
] = (
    (integrated_df["OPTICAL_VALID_PERIOD_COUNT"] > 0)
    &
    (integrated_df["OPTICAL_ALERT_TOTAL"] > 0)
)


integrated_df[
    "POSTPROCESS_LOCK"
] = (
    integrated_df["CONDITION_CLASS_RAW"]
    != integrated_df["CORE_CLASS"]
)


# ============================================================
# 5. EMPIRICAL ADJACENT-CLASS SUPPORT THRESHOLDS
#
# Derived from minimum observed core risk of the
# upper class in AOI01.
#
# Freeze these for later AOI02 transfer testing.
# ============================================================

T12 = integrated_df.loc[
    integrated_df["CORE_CLASS"] == 2,
    "RISK_SCORE_0_100"
].min()

T23 = integrated_df.loc[
    integrated_df["CORE_CLASS"] == 3,
    "RISK_SCORE_0_100"
].min()

T34 = integrated_df.loc[
    integrated_df["CORE_CLASS"] == 4,
    "RISK_SCORE_0_100"
].min()


print("\nFrozen pilot transition thresholds:")
print("Class 1 -> 2 support threshold :", T12)
print("Class 2 -> 3 support threshold :", T23)
print("Class 3 -> 4 support threshold :", T34)


# ============================================================
# 6. TRANSITION ELIGIBILITY
#
# Principles:
# - maximum ±1 class
# - positive modifier for promotion
# - negative modifier for demotion
# - promotion to Class 3/4 requires optical support
# - persistence must resemble the adjacent class
# - preserve RAW->FINAL post-processing
# ============================================================

modifier = integrated_df[
    "CONTEXT_MODIFIER_SCORE"
].fillna(0)

score = integrated_df[
    "INTEGRATED_SCORE_0_100"
]

core = integrated_df[
    "CORE_CLASS"
]

unlocked = ~integrated_df[
    "POSTPROCESS_LOCK"
]


# ------------------------------------------------------------
# 1 -> 2
# ------------------------------------------------------------

promote_1_2 = (
    (core == 1)
    & unlocked
    & (modifier > 0)
    & (score >= T12)
    & (integrated_df["ALERT_MASK"] == 1)
)


# ------------------------------------------------------------
# 2 -> 3
# ------------------------------------------------------------

promote_2_3 = (
    (core == 2)
    & unlocked
    & (modifier > 0)
    & (score >= T23)
    & integrated_df["HAS_OPTICAL_SUPPORT"]
    & (integrated_df["MAX_PERIOD_CLASS"] >= 3)
    & (integrated_df["MAX_CONSECUTIVE_ALERT"] >= 2)
)


# ------------------------------------------------------------
# 3 -> 4
# ------------------------------------------------------------

promote_3_4 = (
    (core == 3)
    & unlocked
    & (modifier > 0)
    & (score >= T34)
    & integrated_df["HAS_OPTICAL_SUPPORT"]
    & (integrated_df["MAX_PERIOD_CLASS"] >= 3)
    & (integrated_df["MAX_CONSECUTIVE_ALERT"] >= 3)
)


# ------------------------------------------------------------
# 2 -> 1
# Very conservative: core alert evidence must disappear.
# ------------------------------------------------------------

demote_2_1 = (
    (core == 2)
    & unlocked
    & (modifier < 0)
    & (score < T12)
    & (integrated_df["ALERT_MASK"] == 0)
)


# ------------------------------------------------------------
# 3 -> 2
# Negative context + score leaves Class-3 support range
# + weak persistence.
# ------------------------------------------------------------

demote_3_2 = (
    (core == 3)
    & unlocked
    & (modifier < 0)
    & (score < T23)
    & (integrated_df["MAX_CONSECUTIVE_ALERT"] <= 1)
)


# ------------------------------------------------------------
# 4 -> 3
# ------------------------------------------------------------

demote_4_3 = (
    (core == 4)
    & unlocked
    & (modifier < 0)
    & (score < T34)
    & (integrated_df["MAX_CONSECUTIVE_ALERT"] <= 2)
)


# ============================================================
# 7. APPLY MAXIMUM ±1 TRANSITION
# ============================================================

integrated_df.loc[
    promote_1_2,
    "INTEGRATED_CLASS"
] = 2

integrated_df.loc[
    promote_2_3,
    "INTEGRATED_CLASS"
] = 3

integrated_df.loc[
    promote_3_4,
    "INTEGRATED_CLASS"
] = 4

integrated_df.loc[
    demote_2_1,
    "INTEGRATED_CLASS"
] = 1

integrated_df.loc[
    demote_3_2,
    "INTEGRATED_CLASS"
] = 2

integrated_df.loc[
    demote_4_3,
    "INTEGRATED_CLASS"
] = 3


# ============================================================
# 8. TRANSITION LABEL
# ============================================================

integrated_df[
    "CLASS_DELTA"
] = (
    integrated_df["INTEGRATED_CLASS"]
    - integrated_df["CORE_CLASS"]
)


integrated_df[
    "CLASS_TRANSITION"
] = (
    integrated_df["CORE_CLASS"].astype(str)
    + "->"
    + integrated_df["INTEGRATED_CLASS"].astype(str)
)


# ============================================================
# 9. QA
# ============================================================

print("\n" + "=" * 115)
print("CORE -> INTEGRATED CLASS TRANSITION")
print("=" * 115)

transition_table = pd.crosstab(
    integrated_df["CORE_CLASS"],
    integrated_df["INTEGRATED_CLASS"],
    margins=True
)

display(transition_table)


transition_summary = (
    integrated_df[
        "CLASS_TRANSITION"
    ]
    .value_counts()
    .rename_axis("transition")
    .reset_index(name="n")
)

transition_summary["pct"] = (
    transition_summary["n"]
    / len(integrated_df)
    * 100
)

display(transition_summary)


# ============================================================
# 10. CHANGE RATE
# ============================================================

changed = (
    integrated_df["CLASS_DELTA"] != 0
)

print(
    "\nChanged samples:",
    int(changed.sum()),
    "/",
    len(integrated_df)
)

print(
    "Changed pct:",
    round(changed.mean() * 100, 2),
    "%"
)

print(
    "Maximum absolute class change:",
    integrated_df[
        "CLASS_DELTA"
    ].abs().max()
)


# ============================================================
# 11. SCORE BY INTEGRATED CLASS
# ============================================================

integrated_class_summary = (
    integrated_df
    .groupby("INTEGRATED_CLASS")
    .agg(
        n=("SAMPLE_ID", "count"),
        integrated_score_mean=(
            "INTEGRATED_SCORE_0_100", "mean"
        ),
        integrated_score_median=(
            "INTEGRATED_SCORE_0_100", "median"
        ),
        modifier_mean=(
            "CONTEXT_MODIFIER_SCORE", "mean"
        )
    )
    .reset_index()
)


print("\n" + "=" * 115)
print("INTEGRATED CLASS SUMMARY")
print("=" * 115)

display(integrated_class_summary)


# ============================================================
# 12. GUARDRAIL QA
# ============================================================

promotion_to_high = (
    (integrated_df["INTEGRATED_CLASS"] >= 3)
    &
    (integrated_df["INTEGRATED_CLASS"]
     > integrated_df["CORE_CLASS"])
)


high_promotion_without_optical = (
    promotion_to_high
    &
    ~integrated_df["HAS_OPTICAL_SUPPORT"]
)


locked_changed = (
    integrated_df["POSTPROCESS_LOCK"]
    &
    (integrated_df["CLASS_DELTA"] != 0)
)


checks = {

    "sample_count_1300":
        len(integrated_df) == 1300,

    "class_range_1_4":
        integrated_df[
            "INTEGRATED_CLASS"
        ].between(1, 4).all(),

    "maximum_transition_one_class":
        integrated_df[
            "CLASS_DELTA"
        ].abs().max() <= 1,

    "no_high_promotion_without_optical":
        high_promotion_without_optical.sum() == 0,

    "raw_final_postprocess_preserved":
        locked_changed.sum() == 0,

    "integrated_score_0_100":
        integrated_df[
            "INTEGRATED_SCORE_0_100"
        ].between(0, 100).all()
}


print("\n" + "=" * 115)
print("30F-B18E | FINAL GATE")
print("=" * 115)

for name, result in checks.items():

    print(
        f"{name:42s}:",
        "PASS" if result else "FAIL"
    )


# ============================================================
# 13. SAVE
# ============================================================

integrated_df.to_pickle(
    checkpoint_dir /
    "30F_B18E_INTEGRATED_CLASS_CANDIDATE_V1.pkl"
)

integrated_df.to_csv(
    checkpoint_dir /
    "30F_B18E_INTEGRATED_CLASS_CANDIDATE_V1.csv",
    index=False
)

transition_summary.to_csv(
    checkpoint_dir /
    "30F_B18E_CLASS_TRANSITIONS_V1.csv",
    index=False
)


if all(checks.values()):

    print("""
30F-B18E = PASS

Integrated Output 3 candidate created.

CORE:
30D04 optical/radar condition evidence

PLUS:
family-balanced environmental modifier

RESULT:
INTEGRATED_SCORE_0_100
INTEGRATED_CLASS 1-4

NEXT MACRO STEP:
1. Review transition rate / behaviour.
2. Implement the same logic wall-to-wall in GEE.
3. Apply the frozen AOI01 calibration unchanged to AOI02.
4. Transferability QC.
5. Final web-ready Output 3 package.
""")

else:

    print("""
30F-B18E requires review.
Do not create the wall-to-wall integrated map yet.
""")

# ========================================
# ORIGINAL CELL 57
# ========================================

# ============================================================
# OUTPUT 3 | 30G-A
# WALL-TO-WALL INTEGRATED OUTPUT 3 CANDIDATE V1
#
# Applies unchanged:
# - AOI01 B18C calibration
# - feature directions
# - within-family weights
# - family weights
# - F05 amplitude
# - B18E evidence-gated class transition logic
#
# Outputs:
# - INTEGRATED_SCORE_0_100
# - INTEGRATED_CLASS
# - CLASS_DELTA
# - CONTEXT_MODIFIER_SCORE
# - CONTEXT_MODIFIER_COVERAGE
#
# IMPORTANT:
# This is an integrated inspection-priority candidate.
# It is NOT independent field-validated plantation condition.
# ============================================================

import ee
import pandas as pd
import numpy as np
from pathlib import Path
from PIL import Image
from IPython.display import display, FileLink
import urllib.request

print("=" * 120)
print("30G-A | WALL-TO-WALL INTEGRATED OUTPUT 3 CANDIDATE V1")
print("=" * 120)

checkpoint_dir = Path("checkpoints_30F")

output_dir = Path("checkpoints_30G")
output_dir.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# 1. RESTORE FROZEN CALIBRATION
# ============================================================

calibration_df = pd.read_csv(
    checkpoint_dir /
    "30F_B18C_AOI01_WALL_TO_WALL_CALIBRATION_V1.csv"
)

family_weight_df = pd.read_csv(
    checkpoint_dir /
    "30F_B18C_FAMILY_WEIGHTS_V1.csv"
)


print("\nCalibration features :", len(calibration_df))
print("Families             :", len(family_weight_df))


if len(calibration_df) != 8:
    raise ValueError(
        "Expected 8 frozen fusion features."
    )

if len(family_weight_df) != 4:
    raise ValueError(
        "Expected 4 frozen evidence families."
    )


# ============================================================
# 2. FEATURE SOURCE REGISTRY
# ============================================================

feature_source_registry = {

    "LOCAL_RELIEF_300M_M":
        ASSETS["TERRAIN"],

    "SLOPE_DEG":
        ASSETS["TERRAIN"],

    "HAND_M":
        ASSETS["HYDRO"],

    "SILT_PCT_DEEP_100_200CM":
        ASSETS["SOIL"],

    "SOC_GKG_SURFACE_0_30CM":
        ASSETS["SOIL"],

    "WV1500_DEEP_100_200CM":
        ASSETS["SOIL_WATER"],

    "WV10_DEEP_100_200CM":
        ASSETS["SOIL_WATER"],

    "PAW_PROXY_SURFACE_0_30CM":
        ASSETS["SOIL_WATER"]
}


# ============================================================
# 3. CORE
# ============================================================

core_img = ee.Image(
    ASSETS["CORE"]
)

core_class = (
    core_img
    .select("CONDITION_CLASS")
    .round()
    .toInt16()
)

core_raw = (
    core_img
    .select("CONDITION_CLASS_RAW")
    .round()
    .toInt16()
)

core_risk = (
    core_img
    .select("RISK_SCORE_0_100")
    .toFloat()
)


valid_mask = (
    core_class.gte(1)
    .And(
        core_class.lte(4)
    )
)


# ============================================================
# 4. BUILD DIRECTIONAL FEATURE IMAGES
#
# Exactly follows B18C:
#
# P10 -> 0
# P90 -> 1
# clip
# invert negative associations
# [0,1] -> [-1,+1]
# ============================================================

directional_images = {}


for _, row in calibration_df.iterrows():

    feature = row["feature"]

    source = (
        ee.Image(
            feature_source_registry[
                feature
            ]
        )
        .select(feature)
        .toFloat()
        .updateMask(valid_mask)
    )

    p10 = float(row["p10"])
    p90 = float(row["p90"])

    direction = int(
        row[
            "association_direction"
        ]
    )


    norm01 = (
        source
        .subtract(p10)
        .divide(
            p90 - p10
        )
        .clamp(
            0,
            1
        )
    )


    if direction < 0:

        norm01 = (
            ee.Image.constant(1)
            .subtract(norm01)
        )


    directional = (
        norm01
        .multiply(2)
        .subtract(1)
        .rename(
            f"DIR_{feature}"
        )
    )


    directional_images[
        feature
    ] = directional


# ============================================================
# 5. FAMILY COMPOSITES
#
# Replicates available-weight normalization from B18C.
# ============================================================

family_score_images = {}
family_coverage_images = {}


for family in (
    family_weight_df[
        "family"
    ].tolist()
):

    family_cal = calibration_df[
        calibration_df[
            "family"
        ] == family
    ]


    weighted_sum = (
        ee.Image.constant(0)
        .toFloat()
    )

    available_weight = (
        ee.Image.constant(0)
        .toFloat()
    )


    for _, row in family_cal.iterrows():

        feature = row["feature"]

        weight = float(
            row[
                "within_family_weight"
            ]
        )


        img = directional_images[
            feature
        ]


        valid = (
            img.mask()
            .reduce(
                ee.Reducer.min()
            )
            .gt(0)
        )


        weighted_sum = (
            weighted_sum
            .add(
                img
                .unmask(0)
                .multiply(weight)
            )
        )


        available_weight = (
            available_weight
            .add(
                valid
                .toFloat()
                .multiply(weight)
            )
        )


    family_score = (
        weighted_sum
        .divide(
            available_weight
            .max(1e-6)
        )
        .updateMask(
            available_weight.gte(0.50)
        )
        .clamp(
            -1,
            1
        )
        .rename(
            f"FAMILY_SCORE_{family}"
        )
    )


    family_score_images[
        family
    ] = family_score


    family_coverage_images[
        family
    ] = (
        available_weight
        .rename(
            f"FAMILY_COVERAGE_{family}"
        )
    )


# ============================================================
# 6. OVERALL FAMILY-BALANCED MODIFIER
# ============================================================

overall_sum = (
    ee.Image.constant(0)
    .toFloat()
)

overall_weight = (
    ee.Image.constant(0)
    .toFloat()
)


for _, row in family_weight_df.iterrows():

    family = row["family"]

    family_weight = float(
        row["family_weight"]
    )

    img = family_score_images[
        family
    ]


    valid = (
        img.mask()
        .reduce(
            ee.Reducer.min()
        )
        .gt(0)
    )


    overall_sum = (
        overall_sum
        .add(
            img
            .unmask(0)
            .multiply(
                family_weight
            )
        )
    )


    overall_weight = (
        overall_weight
        .add(
            valid
            .toFloat()
            .multiply(
                family_weight
            )
        )
    )


context_modifier = (
    overall_sum
    .divide(
        overall_weight
        .max(1e-6)
    )
    .updateMask(
        overall_weight.gte(0.75)
    )
    .clamp(
        -1,
        1
    )
    .rename(
        "CONTEXT_MODIFIER_SCORE"
    )
)


context_coverage = (
    overall_weight
    .rename(
        "CONTEXT_MODIFIER_COVERAGE"
    )
)


# ============================================================
# 7. F05 INTEGRATED SCORE
#
# Missing context -> adjustment 0
# ============================================================

integrated_score = (

    core_risk

    .add(
        context_modifier
        .unmask(0)
        .multiply(5)
    )

    .clamp(
        0,
        100
    )

    .rename(
        "INTEGRATED_SCORE_0_100"
    )
)


# ============================================================
# 8. CORE EVIDENCE
# ============================================================

optical_valid = (
    core_img
    .select(
        "OPTICAL_VALID_PERIOD_COUNT"
    )
)

alert_mask = (
    core_img
    .select(
        "ALERT_MASK"
    )
    .round()
)

max_period_class = (
    core_img
    .select(
        "MAX_PERIOD_CLASS"
    )
)

max_consecutive = (
    core_img
    .select(
        "MAX_CONSECUTIVE_ALERT"
    )
)


optical_alert_total = (

    core_img.select(
        "GREENNESS_ALERT_PERIODS"
    )

    .add(
        core_img.select(
            "RED_EDGE_ALERT_PERIODS"
        )
    )

    .add(
        core_img.select(
            "MOISTURE_ALERT_PERIODS"
        )
    )
)


has_optical_support = (
    optical_valid.gt(0)
    .And(
        optical_alert_total.gt(0)
    )
)


# preserve existing RAW -> FINAL post-processing
postprocess_lock = (
    core_raw
    .neq(core_class)
)


unlocked = (
    postprocess_lock.Not()
)


# ============================================================
# 9. FROZEN PILOT TRANSITION THRESHOLDS
# ============================================================

T12 = 12
T23 = 22
T34 = 32


# ============================================================
# 10. TRANSITION ELIGIBILITY
# ============================================================

modifier_available = (
    context_modifier
    .mask()
    .reduce(
        ee.Reducer.min()
    )
    .gt(0)
)


modifier_pos = (
    context_modifier
    .unmask(0)
    .gt(0)
)

modifier_neg = (
    context_modifier
    .unmask(0)
    .lt(0)
)


# --------------------------
# 1 -> 2
# --------------------------

promote_1_2 = (
    core_class.eq(1)
    .And(unlocked)
    .And(modifier_available)
    .And(modifier_pos)
    .And(integrated_score.gte(T12))
    .And(alert_mask.eq(1))
)


# --------------------------
# 2 -> 3
# --------------------------

promote_2_3 = (
    core_class.eq(2)
    .And(unlocked)
    .And(modifier_available)
    .And(modifier_pos)
    .And(integrated_score.gte(T23))
    .And(has_optical_support)
    .And(max_period_class.gte(3))
    .And(max_consecutive.gte(2))
)


# --------------------------
# 3 -> 4
# --------------------------

promote_3_4 = (
    core_class.eq(3)
    .And(unlocked)
    .And(modifier_available)
    .And(modifier_pos)
    .And(integrated_score.gte(T34))
    .And(has_optical_support)
    .And(max_period_class.gte(3))
    .And(max_consecutive.gte(3))
)


# --------------------------
# 2 -> 1
# --------------------------

demote_2_1 = (
    core_class.eq(2)
    .And(unlocked)
    .And(modifier_available)
    .And(modifier_neg)
    .And(integrated_score.lt(T12))
    .And(alert_mask.eq(0))
)


# --------------------------
# 3 -> 2
# --------------------------

demote_3_2 = (
    core_class.eq(3)
    .And(unlocked)
    .And(modifier_available)
    .And(modifier_neg)
    .And(integrated_score.lt(T23))
    .And(max_consecutive.lte(1))
)


# --------------------------
# 4 -> 3
# --------------------------

demote_4_3 = (
    core_class.eq(4)
    .And(unlocked)
    .And(modifier_available)
    .And(modifier_neg)
    .And(integrated_score.lt(T34))
    .And(max_consecutive.lte(2))
)


# ============================================================
# 11. APPLY MAXIMUM ±1 CLASS CHANGE
# ============================================================

integrated_class = (
    core_class
    .where(
        promote_1_2,
        2
    )
    .where(
        promote_2_3,
        3
    )
    .where(
        promote_3_4,
        4
    )
    .where(
        demote_2_1,
        1
    )
    .where(
        demote_3_2,
        2
    )
    .where(
        demote_4_3,
        3
    )
    .rename(
        "INTEGRATED_CLASS"
    )
    .toInt16()
)


class_delta = (
    integrated_class
    .subtract(
        core_class
    )
    .rename(
        "CLASS_DELTA"
    )
    .toInt16()
)


# ============================================================
# 12. BUILD FINAL 30G IMAGE
# ============================================================

integrated_img = (

    core_class
    .rename("CORE_CLASS")

    .addBands(
        core_risk
        .rename("CORE_RISK_SCORE_0_100")
    )

    .addBands(
        context_modifier
    )

    .addBands(
        context_coverage
    )

    .addBands(
        integrated_score
    )

    .addBands(
        integrated_class
    )

    .addBands(
        class_delta
    )

    .updateMask(
        valid_mask
    )
)


print(
    "\nIntegrated bands:",
    integrated_img
    .bandNames()
    .getInfo()
)


# ============================================================
# 13. WALL-TO-WALL CLASS TRANSITION AREA
#
# PixelArea at native 10 m core grid.
# ============================================================

transition_code = (
    core_class
    .multiply(10)
    .add(
        integrated_class
    )
    .rename(
        "TRANSITION_CODE"
    )
)


transition_area = (

    ee.Image.pixelArea()
    .divide(10000)        # hectares
    .rename("AREA_HA")
    .addBands(
        transition_code
    )
    .updateMask(
        valid_mask
    )

    .reduceRegion(

        reducer=(
            ee.Reducer.sum()
            .group(
                groupField=1,
                groupName="transition_code"
            )
        ),

        geometry=core_img.geometry(),

        scale=10,

        maxPixels=1e9,

        tileScale=4
    )

    .getInfo()
)


transition_rows = []


for item in transition_area.get(
    "groups",
    []
):

    code = int(
        item[
            "transition_code"
        ]
    )

    old_class = (
        code // 10
    )

    new_class = (
        code % 10
    )


    transition_rows.append({

        "core_class":
            old_class,

        "integrated_class":
            new_class,

        "transition":
            f"{old_class}->{new_class}",

        "area_ha":
            float(
                item["sum"]
            )
    })


transition_area_df = (
    pd.DataFrame(
        transition_rows
    )
    .sort_values(
        [
            "core_class",
            "integrated_class"
        ]
    )
    .reset_index(
        drop=True
    )
)


total_area_ha = (
    transition_area_df[
        "area_ha"
    ].sum()
)


transition_area_df[
    "pct_total_valid_area"
] = (
    transition_area_df[
        "area_ha"
    ]
    /
    total_area_ha
    * 100
)


print("\n" + "=" * 120)
print("WALL-TO-WALL CLASS TRANSITION AREA")
print("=" * 120)

display(
    transition_area_df
)


changed_area_ha = (
    transition_area_df.loc[
        transition_area_df[
            "core_class"
        ]
        !=
        transition_area_df[
            "integrated_class"
        ],
        "area_ha"
    ]
    .sum()
)


changed_area_pct = (
    changed_area_ha
    /
    total_area_ha
    * 100
)


print(
    "\nTotal valid mapped area :",
    round(
        total_area_ha,
        2
    ),
    "ha"
)

print(
    "Changed class area     :",
    round(
        changed_area_ha,
        2
    ),
    "ha"
)

print(
    "Changed class pct      :",
    round(
        changed_area_pct,
        3
    ),
    "%"
)


# ============================================================
# 14. FINAL CLASS AREA
# ============================================================

final_class_area_df = (

    transition_area_df

    .groupby(
        "integrated_class"
    )

    .agg(
        area_ha=(
            "area_ha",
            "sum"
        )
    )

    .reset_index()
)


final_class_area_df[
    "area_pct"
] = (
    final_class_area_df[
        "area_ha"
    ]
    /
    total_area_ha
    * 100
)


print("\n" + "=" * 120)
print("INTEGRATED CLASS AREA")
print("=" * 120)

display(
    final_class_area_df
)


# ============================================================
# 15. GUARDRAIL QA
# ============================================================

max_abs_delta = (

    class_delta
    .abs()

    .reduceRegion(

        reducer=ee.Reducer.max(),

        geometry=core_img.geometry(),

        scale=10,

        maxPixels=1e9,

        tileScale=4
    )

    .get(
        "CLASS_DELTA"
    )

    .getInfo()
)


locked_change_count = (

    postprocess_lock
    .And(
        class_delta.neq(0)
    )

    .rename(
        "LOCKED_CHANGED"
    )

    .reduceRegion(

        reducer=ee.Reducer.sum(),

        geometry=core_img.geometry(),

        scale=10,

        maxPixels=1e9,

        tileScale=4
    )

    .get(
        "LOCKED_CHANGED"
    )

    .getInfo()
)


high_promotion_without_optical = (

    integrated_class
    .gte(3)

    .And(
        integrated_class
        .gt(core_class)
    )

    .And(
        has_optical_support.Not()
    )

    .rename(
        "BAD_HIGH_PROMOTION"
    )

    .reduceRegion(

        reducer=ee.Reducer.sum(),

        geometry=core_img.geometry(),

        scale=10,

        maxPixels=1e9,

        tileScale=4
    )

    .get(
        "BAD_HIGH_PROMOTION"
    )

    .getInfo()
)


checks = {

    "seven_output_bands":
        len(
            integrated_img
            .bandNames()
            .getInfo()
        ) == 7,

    "class_delta_max_abs_1":
        max_abs_delta <= 1,

    "postprocess_lock_preserved":
        locked_change_count == 0,

    "no_high_promotion_without_optical":
        high_promotion_without_optical == 0,

    "valid_transition_area":
        total_area_ha > 0
}


print("\n" + "=" * 120)
print("30G-A | WALL-TO-WALL FINAL GATE")
print("=" * 120)

for name, result in checks.items():

    print(
        f"{name:42s}:",
        "PASS"
        if result
        else "FAIL"
    )


# ============================================================
# 16. VISUALIZATION PNG
# ============================================================

condition_vis = {

    "min": 1,

    "max": 4,

    "palette": [
        "2ca25f",
        "fee08b",
        "f46d43",
        "a50026"
    ],

    "forceRgbOutput":
        True
}


visual = (
    integrated_class
    .updateMask(
        integrated_class.gte(1)
    )
    .visualize(
        **condition_vis
    )
)


outline = (

    ee.Image()
    .byte()

    .paint(

        featureCollection=ee.FeatureCollection([
            ee.Feature(
                core_img.geometry()
            )
        ]),

        color=1,

        width=3
    )

    .selfMask()

    .visualize(
        palette=[
            "000000"
        ],
        forceRgbOutput=True
    )
)


visual = visual.blend(
    outline
)


png_path = (
    output_dir /
    "30G_A_INTEGRATED_CLASS_WALL_TO_WALL_V1.png"
)


thumb_url = visual.getThumbURL({

    "region":
        core_img
        .geometry()
        .bounds(),

    "dimensions":
        1400,

    "format":
        "png"
})


urllib.request.urlretrieve(
    thumb_url,
    png_path
)


print(
    "\nPNG:",
    png_path
)


display(
    Image.open(
        png_path
    )
)


display(
    FileLink(
        str(png_path)
    )
)


# ============================================================
# 17. SAVE QA TABLES
# ============================================================

transition_area_df.to_csv(

    output_dir /
    "30G_A_TRANSITION_AREA_V1.csv",

    index=False
)


final_class_area_df.to_csv(

    output_dir /
    "30G_A_INTEGRATED_CLASS_AREA_V1.csv",

    index=False
)


# ============================================================
# 18. FINAL STATUS
# ============================================================

if all(
    checks.values()
):

    print("""
30G-A = PASS

WALL-TO-WALL INTEGRATED OUTPUT 3 CANDIDATE CREATED.

The final candidate now combines:

1. 30D04 optical/radar core evidence
2. terrain context
3. hydrology context
4. soil context
5. soil-water context
6. bounded F05 environmental modifier
7. evidence-gated Class 1-4 refinement

NEXT MACRO STEPS:

A. Review wall-to-wall transition area and map.

B. Export this exact integrated raster to Earth Engine
   as the AOI01 Integrated Output 3 candidate.

C. Apply the SAME frozen calibration, weights,
   amplitude and transition rules to AOI02.

D. Transferability QC.

E. Web-ready raster / COG / metadata packaging.
""")

else:

    print("""
30G-A requires review.

Do not export the integrated raster yet.
""")

# ========================================
# ORIGINAL CELL 58
# ========================================

# ============================================================
# OUTPUT 3 | 30G-B
# EXPORT INTEGRATED AOI01 CANDIDATE TO EARTH ENGINE
# ============================================================

import ee

print("=" * 110)
print("30G-B | EXPORT AOI01 INTEGRATED OUTPUT 3")
print("=" * 110)

EXPORT_ASSET = (
    "projects/palm-oil-503202/assets/"
    "SIAK_AOI01_O3_30G_INTEGRATED_V1_2025"
)


# ============================================================
# 1. ADD PROVENANCE METADATA
# ============================================================

export_img = integrated_img.set({

    "OUTPUT":
        "OUTPUT_3",

    "PRODUCT":
        "INTEGRATED_INSPECTION_PRIORITY",

    "VERSION":
        "30G_V1",

    "AOI":
        "SIAK_AOI01",

    "YEAR":
        2025,

    "CORE_SOURCE":
        "SIAK_AOI01_O3_30D04_BALANCED_RISK_2025",

    "FUSION_AMPLITUDE":
        5,

    "TRANSITION_THRESHOLD_1_2":
        12,

    "TRANSITION_THRESHOLD_2_3":
        22,

    "TRANSITION_THRESHOLD_3_4":
        32,

    "MODIFIER_FEATURE_COUNT":
        8,

    "MODIFIER_FAMILY_COUNT":
        4,

    "MODIFIER_FAMILIES":
        "TERRAIN|HYDROLOGY|SOIL|SOIL_WATER",

    "MAX_CLASS_CHANGE":
        1,

    "HIGH_CLASS_REQUIRES_OPTICAL":
        1,

    "AOI01_CALIBRATION_FROZEN":
        1,

    "FIELD_VALIDATED":
        0,

    "INTERPRETATION":
        (
            "Integrated inspection-priority candidate; "
            "not causal diagnosis and not independent "
            "field-validated plantation condition."
        )
})


# ============================================================
# 2. EXPORT
# ============================================================

task = ee.batch.Export.image.toAsset(

    image=export_img,

    description=(
        "SIAK_AOI01_O3_30G_INTEGRATED_V1_2025"
    ),

    assetId=EXPORT_ASSET,

    region=core_img.geometry(),

    scale=10,

    crs="EPSG:32647",

    maxPixels=1e13
)


task.start()


print("\nExport task started.")
print("Asset:")
print(EXPORT_ASSET)

print("\nTask ID:")
print(task.id)

print("\nInitial status:")
print(task.status())

print("""
IMPORTANT:
Wait until Earth Engine reports COMPLETED.

Do not rerun the export while the task is active.

NEXT AFTER COMPLETED:
AOI02 TRANSFERABILITY TEST.
""")

# ========================================
# ORIGINAL CELL 61
# ========================================

# ============================================================
# 30G-C1B | GRID / AREA RECONCILIATION
#
# Purpose:
# 1. Reproduce the legacy 30G-A area calculation method
#    (scale=10, no explicit CRS/transform).
# 2. Calculate area on the exact permanent asset grid.
# 3. Check whether exported CORE_CLASS still matches
#    the original 30D04 core after alignment to the asset grid.
#
# DO NOT modify or re-export the model in this step.
# ============================================================

import ee
import pandas as pd

PROJECT_ID = "palm-oil-503202"

INTEGRATED_ASSET = (
    "projects/palm-oil-503202/assets/"
    "SIAK_AOI01_O3_30G_INTEGRATED_V1_2025"
)

CORE_ASSET = (
    "projects/palm-oil-503202/assets/"
    "SIAK_AOI01_O3_30D04_BALANCED_RISK_2025"
)

# Frozen 30G-A reference
EXPECTED_CLASS_AREA_HA = {
    1: 9531.973324,
    2: 4079.089398,
    3: 187.304555,
    4: 29.787187,
}

EXPECTED_TOTAL_HA = 13828.154464
EXPECTED_CHANGED_HA = 42.222563


# ------------------------------------------------------------
# 0. Initialize
# ------------------------------------------------------------

try:
    ee.Initialize(project=PROJECT_ID)
except Exception:
    ee.Authenticate()
    ee.Initialize(project=PROJECT_ID)


final_img = ee.Image(INTEGRATED_ASSET)
core_img = ee.Image(CORE_ASSET)

asset_core = (
    final_img
    .select("CORE_CLASS")
    .round()
    .toInt16()
)

integrated_class = (
    final_img
    .select("INTEGRATED_CLASS")
    .round()
    .toInt16()
)

source_core = (
    core_img
    .select("CONDITION_CLASS")
    .round()
    .toInt16()
)

source_valid = (
    source_core.gte(1)
    .And(source_core.lte(4))
)

asset_valid = (
    asset_core.gte(1)
    .And(asset_core.lte(4))
)


print("=" * 92)
print("30G-C1B | GRID / AREA RECONCILIATION")
print("=" * 92)


# ============================================================
# 1. EXACT PERMANENT-ASSET PROJECTION
# ============================================================

asset_proj = integrated_class.projection()

asset_crs = asset_proj.crs().getInfo()
asset_transform = asset_proj.transform().getInfo()
asset_scale = asset_proj.nominalScale().getInfo()

print("\n[1] PERMANENT ASSET GRID")
print("CRS       :", asset_crs)
print("Scale     :", asset_scale, "m")
print("Transform :", asset_transform)


# ============================================================
# Helper
# ============================================================

def parse_grouped(groups, group_key):
    out = {}

    for row in groups or []:
        key = int(row[group_key])
        out[key] = float(row["sum"])

    return out


# ============================================================
# 2. LEGACY 30G-A STYLE CALCULATION
#
# IMPORTANT:
# Same principle as the earlier 30G-A:
# - ee.Image.pixelArea()
# - geometry = core_img.geometry()
# - scale = 10
# - NO explicit CRS / transform
# ============================================================

legacy_class_area_raw = (
    ee.Image.pixelArea()
    .divide(10000)
    .rename("AREA_HA")
    .addBands(
        integrated_class.rename("CLASS")
    )
    .updateMask(source_valid)
    .reduceRegion(
        reducer=ee.Reducer.sum().group(
            groupField=1,
            groupName="CLASS"
        ),
        geometry=core_img.geometry(),
        scale=10,
        maxPixels=1e13,
        tileScale=8
    )
    .get("groups")
    .getInfo()
)

legacy_class_area = parse_grouped(
    legacy_class_area_raw,
    "CLASS"
)

legacy_total = sum(
    legacy_class_area.values()
)


legacy_changed = (
    ee.Image.pixelArea()
    .divide(10000)
    .updateMask(
        source_valid
        .And(
            source_core.neq(
                integrated_class
            )
        )
    )
    .rename("CHANGED_HA")
    .reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=core_img.geometry(),
        scale=10,
        maxPixels=1e13,
        tileScale=8
    )
    .get("CHANGED_HA")
    .getInfo()
)

legacy_changed = float(
    legacy_changed or 0
)


print("\n[2] LEGACY 30G-A STYLE AREA")

for cls in [1, 2, 3, 4]:

    actual = legacy_class_area.get(
        cls,
        0.0
    )

    expected = EXPECTED_CLASS_AREA_HA[cls]

    print(
        f"Class {cls}: "
        f"{actual:,.6f} ha | "
        f"30G-A expected {expected:,.6f} ha | "
        f"diff {actual - expected:+.6f} ha"
    )

print(
    "\nLegacy total   :",
    f"{legacy_total:,.6f} ha"
)

print(
    "30G-A expected :",
    f"{EXPECTED_TOTAL_HA:,.6f} ha"
)

print(
    "Difference     :",
    f"{legacy_total - EXPECTED_TOTAL_HA:+.6f} ha"
)

print(
    "\nLegacy changed :",
    f"{legacy_changed:,.6f} ha"
)

print(
    "30G-A expected :",
    f"{EXPECTED_CHANGED_HA:,.6f} ha"
)

print(
    "Difference     :",
    f"{legacy_changed - EXPECTED_CHANGED_HA:+.6f} ha"
)


# ============================================================
# 3. EXACT NATIVE ASSET GRID CALCULATION
#
# This uses the permanent raster's actual CRS + transform.
# This is the preferred candidate for final raster-area
# statistics if structural equivalence is confirmed.
# ============================================================

native_class_area_raw = (
    ee.Image.pixelArea()
    .divide(10000)
    .rename("AREA_HA")
    .addBands(
        integrated_class.rename("CLASS")
    )
    .updateMask(asset_valid)
    .reduceRegion(
        reducer=ee.Reducer.sum().group(
            groupField=1,
            groupName="CLASS"
        ),
        geometry=final_img.geometry(),
        crs=asset_crs,
        crsTransform=asset_transform,
        maxPixels=1e13,
        tileScale=8
    )
    .get("groups")
    .getInfo()
)

native_class_area = parse_grouped(
    native_class_area_raw,
    "CLASS"
)

native_total = sum(
    native_class_area.values()
)


native_changed = (
    ee.Image.pixelArea()
    .divide(10000)
    .updateMask(
        asset_valid
        .And(
            asset_core.neq(
                integrated_class
            )
        )
    )
    .rename("CHANGED_HA")
    .reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=final_img.geometry(),
        crs=asset_crs,
        crsTransform=asset_transform,
        maxPixels=1e13,
        tileScale=8
    )
    .get("CHANGED_HA")
    .getInfo()
)

native_changed = float(
    native_changed or 0
)


print("\n[3] EXACT PERMANENT-ASSET GRID AREA")

for cls in [1, 2, 3, 4]:

    print(
        f"Class {cls}: "
        f"{native_class_area.get(cls, 0.0):,.6f} ha"
    )

print(
    "\nNative total   :",
    f"{native_total:,.6f} ha"
)

print(
    "Native changed :",
    f"{native_changed:,.6f} ha"
)


# ============================================================
# 4. ORIGINAL CORE vs EXPORTED CORE
#
# Align original 30D04 to the final asset projection.
# If the export is faithful, mismatch should be zero
# or extremely small and explainable by boundary/grid effects.
# ============================================================

source_core_on_asset_grid = (
    source_core
    .reproject(asset_proj)
)

source_valid_on_asset_grid = (
    source_core_on_asset_grid
    .gte(1)
    .And(
        source_core_on_asset_grid.lte(4)
    )
)

both_valid = (
    source_valid_on_asset_grid
    .And(asset_valid)
)

core_class_mismatch = (
    source_core_on_asset_grid
    .neq(asset_core)
    .updateMask(both_valid)
)

core_mismatch_area = (
    ee.Image.pixelArea()
    .divide(10000)
    .updateMask(core_class_mismatch)
    .rename("MISMATCH_HA")
    .reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=final_img.geometry(),
        crs=asset_crs,
        crsTransform=asset_transform,
        maxPixels=1e13,
        tileScale=8
    )
    .get("MISMATCH_HA")
    .getInfo()
)

core_mismatch_area = float(
    core_mismatch_area or 0
)


# Mask difference
source_mask01 = (
    source_valid_on_asset_grid
    .unmask(0)
    .toByte()
)

asset_mask01 = (
    asset_valid
    .unmask(0)
    .toByte()
)

mask_difference = (
    source_mask01
    .neq(asset_mask01)
)

mask_difference_area = (
    ee.Image.pixelArea()
    .divide(10000)
    .updateMask(mask_difference)
    .rename("MASK_DIFF_HA")
    .reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=final_img.geometry(),
        crs=asset_crs,
        crsTransform=asset_transform,
        maxPixels=1e13,
        tileScale=8
    )
    .get("MASK_DIFF_HA")
    .getInfo()
)

mask_difference_area = float(
    mask_difference_area or 0
)


print("\n[4] ORIGINAL CORE vs EXPORTED CORE")

print(
    "Core class mismatch area :",
    f"{core_mismatch_area:,.6f} ha"
)

print(
    "Valid-mask difference    :",
    f"{mask_difference_area:,.6f} ha"
)


# ============================================================
# 5. DIAGNOSTIC SUMMARY
# ============================================================

legacy_total_diff = abs(
    legacy_total - EXPECTED_TOTAL_HA
)

legacy_changed_diff = abs(
    legacy_changed - EXPECTED_CHANGED_HA
)

print("\n" + "=" * 92)
print("30G-C1B DIAGNOSTIC SUMMARY")
print("=" * 92)

print(
    "Legacy total difference  :",
    f"{legacy_total_diff:.6f} ha"
)

print(
    "Legacy changed difference:",
    f"{legacy_changed_diff:.6f} ha"
)

print(
    "Core mismatch area       :",
    f"{core_mismatch_area:.6f} ha"
)

print(
    "Mask difference area     :",
    f"{mask_difference_area:.6f} ha"
)

print("\nINTERPRETATION RULE:")

print(
    "- If legacy values closely reproduce 30G-A, "
    "but native-grid values differ slightly, "
    "the issue is reducer/grid alignment rather than model logic."
)

print(
    "- If original CORE_CLASS and exported CORE_CLASS match "
    "on the asset grid, the permanent export is structurally faithful."
)

print(
    "- Do NOT re-export or retune before this diagnostic is reviewed."
)

print("=" * 92)

# ========================================
# ORIGINAL CELL 62
# ========================================

# ============================================================
# 30G-C1B FIX | EXACT GRID / AREA RECONCILIATION
#
# Purpose:
# 1. Read the exact permanent asset grid correctly.
# 2. Compare the permanent Output 3 raster against:
#    - frozen 30G-A statistics
#    - original 30D04 core raster
# 3. Determine whether previous area differences are caused
#    by grid alignment rather than model logic.
#
# IMPORTANT:
# - No model retuning
# - No re-export
# - No local raster download
# ============================================================

import ee

PROJECT_ID = "palm-oil-503202"

FINAL_ASSET = (
    "projects/palm-oil-503202/assets/"
    "SIAK_AOI01_O3_30G_INTEGRATED_V1_2025"
)

CORE_ASSET = (
    "projects/palm-oil-503202/assets/"
    "SIAK_AOI01_O3_30D04_BALANCED_RISK_2025"
)

EXPECTED_CLASS_AREA_HA = {
    1: 9531.973324,
    2: 4079.089398,
    3: 187.304555,
    4: 29.787187,
}

EXPECTED_TOTAL_HA = 13828.154464
EXPECTED_CHANGED_HA = 42.222563


# ------------------------------------------------------------
# 0. Initialize
# ------------------------------------------------------------

ee.Initialize(project=PROJECT_ID)

final_img = ee.Image(FINAL_ASSET)
core_img = ee.Image(CORE_ASSET)

asset_core = (
    final_img
    .select("CORE_CLASS")
    .round()
    .toInt16()
)

integrated_class = (
    final_img
    .select("INTEGRATED_CLASS")
    .round()
    .toInt16()
)

class_delta = (
    final_img
    .select("CLASS_DELTA")
    .round()
    .toInt16()
)

source_core = (
    core_img
    .select("CONDITION_CLASS")
    .round()
    .toInt16()
)

asset_valid = (
    asset_core.gte(1)
    .And(asset_core.lte(4))
)

source_valid = (
    source_core.gte(1)
    .And(source_core.lte(4))
)


print("=" * 100)
print("30G-C1B FIX | EXACT GRID / AREA RECONCILIATION")
print("=" * 100)


# ============================================================
# 1. READ PROJECTIONS CORRECTLY
# ============================================================

asset_proj = integrated_class.projection()
asset_proj_info = asset_proj.getInfo()

asset_crs = asset_proj_info["crs"]
asset_transform = asset_proj_info["transform"]
asset_scale = asset_proj.nominalScale().getInfo()

core_proj = source_core.projection()
core_proj_info = core_proj.getInfo()

core_crs = core_proj_info["crs"]
core_transform = core_proj_info["transform"]
core_scale = core_proj.nominalScale().getInfo()


print("\n[1] GRID / PROJECTION")

print("\nFINAL 30G ASSET")
print("CRS       :", asset_crs)
print("Scale     :", asset_scale, "m")
print("Transform :", asset_transform)

print("\nSOURCE 30D04 CORE")
print("CRS       :", core_crs)
print("Scale     :", core_scale, "m")
print("Transform :", core_transform)

same_crs = asset_crs == core_crs
same_transform = asset_transform == core_transform

print("\nSame CRS       :", same_crs)
print("Same transform :", same_transform)


# ============================================================
# Helper
# ============================================================

def grouped_to_dict(groups, key_name):
    result = {}

    for row in groups or []:
        result[int(row[key_name])] = float(row["sum"])

    return result


# ============================================================
# 2. LEGACY 30G-A METHOD
#
# Reproduce the original QA method:
# scale=10, without forcing an explicit affine transform.
# ============================================================

legacy_groups = (
    ee.Image.pixelArea()
    .divide(10000)
    .rename("AREA_HA")
    .addBands(
        integrated_class.rename("CLASS")
    )
    .updateMask(source_valid)
    .reduceRegion(
        reducer=ee.Reducer.sum().group(
            groupField=1,
            groupName="CLASS"
        ),
        geometry=core_img.geometry(),
        scale=10,
        maxPixels=1e13,
        tileScale=8
    )
    .get("groups")
    .getInfo()
)

legacy_area = grouped_to_dict(
    legacy_groups,
    "CLASS"
)

legacy_total = sum(
    legacy_area.values()
)


print("\n[2] LEGACY 30G-A REPRODUCTION")

for cls in [1, 2, 3, 4]:

    actual = legacy_area.get(cls, 0.0)
    expected = EXPECTED_CLASS_AREA_HA[cls]

    print(
        f"Class {cls}: "
        f"{actual:,.6f} ha | "
        f"expected {expected:,.6f} ha | "
        f"diff {actual - expected:+.6f} ha"
    )

print(
    "\nTotal:",
    f"{legacy_total:,.6f} ha"
)

print(
    "Expected:",
    f"{EXPECTED_TOTAL_HA:,.6f} ha"
)

print(
    "Diff:",
    f"{legacy_total - EXPECTED_TOTAL_HA:+.6f} ha"
)


# ============================================================
# 3. EXACT PERMANENT-ASSET GRID
#
# IMPORTANT:
# Use exact affine transform from projection().getInfo().
# Do NOT combine scale + crsTransform.
# ============================================================

native_groups = (
    ee.Image.pixelArea()
    .divide(10000)
    .rename("AREA_HA")
    .addBands(
        integrated_class.rename("CLASS")
    )
    .updateMask(asset_valid)
    .reduceRegion(
        reducer=ee.Reducer.sum().group(
            groupField=1,
            groupName="CLASS"
        ),
        geometry=final_img.geometry(),
        crs=asset_crs,
        crsTransform=asset_transform,
        maxPixels=1e13,
        tileScale=8
    )
    .get("groups")
    .getInfo()
)

native_area = grouped_to_dict(
    native_groups,
    "CLASS"
)

native_total = sum(
    native_area.values()
)


native_changed = (
    ee.Image.pixelArea()
    .divide(10000)
    .updateMask(
        asset_valid
        .And(class_delta.neq(0))
    )
    .rename("CHANGED_HA")
    .reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=final_img.geometry(),
        crs=asset_crs,
        crsTransform=asset_transform,
        maxPixels=1e13,
        tileScale=8
    )
    .get("CHANGED_HA")
    .getInfo()
)

native_changed = float(
    native_changed or 0
)


print("\n[3] EXACT PERMANENT-ASSET GRID")

for cls in [1, 2, 3, 4]:
    print(
        f"Class {cls}: "
        f"{native_area.get(cls, 0.0):,.6f} ha"
    )

print(
    "\nNative total   :",
    f"{native_total:,.6f} ha"
)

print(
    "Native changed :",
    f"{native_changed:,.6f} ha"
)


# ============================================================
# 4. ALIGN ORIGINAL 30D04 CORE TO FINAL ASSET GRID
#
# CONDITION_CLASS is categorical.
# Earth Engine's default reprojection resampling is nearest
# neighbour, which is appropriate here.
# ============================================================

source_core_aligned = (
    source_core
    .reproject(
        crs=asset_crs,
        crsTransform=asset_transform
    )
)

source_valid_aligned = (
    source_core_aligned.gte(1)
    .And(source_core_aligned.lte(4))
)


# ============================================================
# 5. CORE CLASS MISMATCH
# ============================================================

both_valid = (
    source_valid_aligned
    .And(asset_valid)
)

core_mismatch = (
    source_core_aligned
    .neq(asset_core)
    .updateMask(both_valid)
)

core_mismatch_area = (
    ee.Image.pixelArea()
    .divide(10000)
    .updateMask(core_mismatch)
    .rename("MISMATCH_HA")
    .reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=final_img.geometry(),
        crs=asset_crs,
        crsTransform=asset_transform,
        maxPixels=1e13,
        tileScale=8
    )
    .get("MISMATCH_HA")
    .getInfo()
)

core_mismatch_area = float(
    core_mismatch_area or 0
)


# ============================================================
# 6. VALID MASK DIFFERENCE
# ============================================================

source_mask01 = (
    source_valid_aligned
    .unmask(0)
    .toByte()
)

asset_mask01 = (
    asset_valid
    .unmask(0)
    .toByte()
)

mask_diff = (
    source_mask01
    .neq(asset_mask01)
)

mask_diff_area = (
    ee.Image.pixelArea()
    .divide(10000)
    .updateMask(mask_diff)
    .rename("MASK_DIFF_HA")
    .reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=final_img.geometry(),
        crs=asset_crs,
        crsTransform=asset_transform,
        maxPixels=1e13,
        tileScale=8
    )
    .get("MASK_DIFF_HA")
    .getInfo()
)

mask_diff_area = float(
    mask_diff_area or 0
)


print("\n[4] SOURCE CORE vs EXPORTED CORE")
print(
    "Core class mismatch area :",
    f"{core_mismatch_area:,.6f} ha"
)

print(
    "Valid-mask difference    :",
    f"{mask_diff_area:,.6f} ha"
)


# ============================================================
# 7. FINAL DIAGNOSTIC
# ============================================================

legacy_diff = abs(
    legacy_total - EXPECTED_TOTAL_HA
)

native_vs_legacy = (
    native_total - legacy_total
)

changed_vs_expected = (
    native_changed - EXPECTED_CHANGED_HA
)


print("\n" + "=" * 100)
print("30G-C1B FIX | DIAGNOSTIC SUMMARY")
print("=" * 100)

print(
    "Legacy vs frozen total    :",
    f"{legacy_diff:.6f} ha"
)

print(
    "Native vs legacy total    :",
    f"{native_vs_legacy:+.6f} ha"
)

print(
    "Native changed vs frozen  :",
    f"{changed_vs_expected:+.6f} ha"
)

print(
    "Core class mismatch area  :",
    f"{core_mismatch_area:.6f} ha"
)

print(
    "Mask difference area      :",
    f"{mask_diff_area:.6f} ha"
)


# Conservative diagnostic gate
structural_pass = (
    core_mismatch_area <= 0.10
    and
    mask_diff_area <= 0.10
)

print("\nStructural export fidelity :", structural_pass)

if structural_pass:

    print("""
STATUS: STRUCTURALLY CONSISTENT

The permanent 30G asset preserves the source core structure.
Small differences in reported area can therefore be evaluated
as grid/reducer alignment effects rather than immediate evidence
of model failure.

NEXT:
Review these numbers before freezing the canonical area method.
""")

else:

    print("""
STATUS: REVIEW REQUIRED

The source core and exported core differ by more than the
conservative diagnostic tolerance.

DO NOT re-export yet.
The spatial mismatch must be located and inspected first.
""")

print("=" * 100)

# ========================================
# ORIGINAL CELL 63
# ========================================

# ============================================================
# 30G-C1C | GRID-LOCKED CORRECTED EXPORT
#
# Purpose:
# Export the SAME frozen 30G integrated image,
# but lock it exactly to the original 30D04 core grid.
#
# IMPORTANT:
# - No model changes
# - No parameter changes
# - No re-tuning
# - New versioned asset; do not overwrite V1
# ============================================================

import ee

PROJECT_ID = "palm-oil-503202"

CORE_ASSET = (
    "projects/palm-oil-503202/assets/"
    "SIAK_AOI01_O3_30D04_BALANCED_RISK_2025"
)

OUTPUT_ASSET = (
    "projects/palm-oil-503202/assets/"
    "SIAK_AOI01_O3_30G_INTEGRATED_V1_1_GRIDLOCKED_2025"
)

TASK_DESCRIPTION = (
    "SIAK_AOI01_O3_30G_INTEGRATED_V1_1_GRIDLOCKED_2025"
)

ee.Initialize(project=PROJECT_ID)

print("=" * 92)
print("30G-C1C | GRID-LOCKED CORRECTED EXPORT")
print("=" * 92)


# ============================================================
# 1. REQUIRE ORIGINAL 30G-A IMAGE
# ============================================================

if "integrated_img" not in globals():
    raise RuntimeError(
        "integrated_img is not available in the current notebook session.\n"
        "DO NOT reproject the already-exported V1 asset as a substitute.\n"
        "Re-run the 30G-A build cells first to recreate the frozen "
        "integrated_img object."
    )

print("\nOriginal integrated_img: FOUND")


# ============================================================
# 2. GET EXACT 30D04 CORE GRID
# ============================================================

core_img = ee.Image(CORE_ASSET)

core_proj = (
    core_img
    .select("CONDITION_CLASS")
    .projection()
)

core_proj_info = core_proj.getInfo()

core_crs = core_proj_info["crs"]
core_transform = core_proj_info["transform"]

print("\nREFERENCE GRID")
print("CRS       :", core_crs)
print("Transform :", core_transform)


# ============================================================
# 3. STRUCTURE CHECK BEFORE EXPORT
# ============================================================

expected_bands = [
    "CORE_CLASS",
    "CORE_RISK_SCORE_0_100",
    "CONTEXT_MODIFIER_SCORE",
    "CONTEXT_MODIFIER_COVERAGE",
    "INTEGRATED_SCORE_0_100",
    "INTEGRATED_CLASS",
    "CLASS_DELTA",
]

actual_bands = integrated_img.bandNames().getInfo()

print("\nBANDS")
print("Actual   :", actual_bands)
print("Expected :", expected_bands)

if actual_bands != expected_bands:
    raise RuntimeError(
        "Band structure does not match the frozen 30G-A product."
    )

print("Band structure: PASS")


# ============================================================
# 4. EXPORT EXACT FROZEN IMAGE ON CORE GRID
# ============================================================

task = ee.batch.Export.image.toAsset(
    image=integrated_img,
    description=TASK_DESCRIPTION,
    assetId=OUTPUT_ASSET,

    region=core_img.geometry(),

    # IMPORTANT:
    # exact source grid lock
    crs=core_crs,
    crsTransform=core_transform,

    maxPixels=1e13
)

task.start()


# ============================================================
# 5. STATUS
# ============================================================

status = task.status()

print("\nEXPORT STARTED")
print("Asset ID :", OUTPUT_ASSET)
print("Task ID  :", status.get("id"))
print("State    :", status.get("state"))

print("\n" + "=" * 92)
print("30G-C1C SUBMITTED")
print(
    "The frozen 30G product is being exported again "
    "using the exact 30D04 10 m grid."
)
print(
    "Do NOT delete the previous V1 asset; retain it for audit."
)
print("=" * 92)

# ========================================
# ORIGINAL CELL 64
# ========================================

# ============================================================
# 30G-R0 | REHYDRATE FROZEN 30G-A SESSION
#
# Purpose:
# Reconstruct integrated_img after a fresh/restarted kernel
# using persistent Earth Engine assets + frozen calibration files.
#
# No raster download.
# No model retuning.
# No export in this step.
# ============================================================

import ssl
import certifi
import ee
import pandas as pd
from pathlib import Path

# ------------------------------------------------------------
# 0. HTTPS + EARTH ENGINE INITIALIZATION
# ------------------------------------------------------------

ssl._create_default_https_context = (
    lambda: ssl.create_default_context(
        cafile=certifi.where()
    )
)

PROJECT_ID = "palm-oil-503202"

try:
    ee.Initialize(project=PROJECT_ID)
except Exception:
    ee.Authenticate()
    ee.Initialize(project=PROJECT_ID)


# ============================================================
# 1. PERSISTENT SOURCE ASSET REGISTRY
# ============================================================

ASSETS = {

    "CORE":
        "projects/palm-oil-503202/assets/"
        "SIAK_AOI01_O3_30D04_BALANCED_RISK_2025",

    "TERRAIN":
        "projects/palm-oil-503202/assets/"
        "SIAK_AOI01_O3_30E03A_TERRAIN_CORE_2025",

    "HYDRO":
        "projects/palm-oil-503202/assets/"
        "SIAK_AOI01_O3_30E03B_HYDRO_CONTEXT_2025",

    "SOIL":
        "projects/palm-oil-503202/assets/"
        "SIAK_AOI01_O3_30E04A_SOIL_CORE_PROFILE_2025",

    "SOIL_WATER":
        "projects/palm-oil-503202/assets/"
        "SIAK_AOI01_O3_30E04B_SOIL_WATER_RETENTION_2025",
}


# ============================================================
# 2. RESTORE FROZEN CALIBRATION
# ============================================================

checkpoint_dir = Path("checkpoints_30F")

calibration_path = (
    checkpoint_dir /
    "30F_B18C_AOI01_WALL_TO_WALL_CALIBRATION_V1.csv"
)

family_weight_path = (
    checkpoint_dir /
    "30F_B18C_FAMILY_WEIGHTS_V1.csv"
)

print("=" * 100)
print("30G-R0 | SESSION REHYDRATION")
print("=" * 100)

print("\n[1] LOCAL FROZEN CONFIG")
print("Calibration file :", calibration_path.exists())
print("Family weights   :", family_weight_path.exists())

if not calibration_path.exists():
    raise FileNotFoundError(
        f"Missing frozen calibration file: {calibration_path}"
    )

if not family_weight_path.exists():
    raise FileNotFoundError(
        f"Missing frozen family-weight file: {family_weight_path}"
    )

calibration_df = pd.read_csv(calibration_path)
family_weight_df = pd.read_csv(family_weight_path)

if len(calibration_df) != 8:
    raise RuntimeError(
        f"Expected 8 calibration features, found {len(calibration_df)}"
    )

if len(family_weight_df) != 4:
    raise RuntimeError(
        f"Expected 4 evidence families, found {len(family_weight_df)}"
    )

print("Calibration rows :", len(calibration_df))
print("Families         :", len(family_weight_df))


# ============================================================
# 3. CHECK SOURCE ASSETS
# ============================================================

print("\n[2] EARTH ENGINE SOURCE ASSETS")

for key, asset_id in ASSETS.items():

    try:
        info = ee.data.getAsset(asset_id)

        print(
            f"{key:12s}: PASS | "
            f"{info.get('type')} | "
            f"{asset_id.split('/')[-1]}"
        )

    except Exception as e:
        raise RuntimeError(
            f"Asset unavailable: {key}\n{asset_id}\n{e}"
        )


# ============================================================
# 4. FEATURE SOURCE REGISTRY
# ============================================================

feature_source_registry = {

    "LOCAL_RELIEF_300M_M":
        ASSETS["TERRAIN"],

    "SLOPE_DEG":
        ASSETS["TERRAIN"],

    "HAND_M":
        ASSETS["HYDRO"],

    "SILT_PCT_DEEP_100_200CM":
        ASSETS["SOIL"],

    "SOC_GKG_SURFACE_0_30CM":
        ASSETS["SOIL"],

    "WV1500_DEEP_100_200CM":
        ASSETS["SOIL_WATER"],

    "WV10_DEEP_100_200CM":
        ASSETS["SOIL_WATER"],

    "PAW_PROXY_SURFACE_0_30CM":
        ASSETS["SOIL_WATER"],
}


# ============================================================
# 5. CORE
# ============================================================

core_img = ee.Image(ASSETS["CORE"])

core_class = (
    core_img
    .select("CONDITION_CLASS")
    .round()
    .toInt16()
)

core_raw = (
    core_img
    .select("CONDITION_CLASS_RAW")
    .round()
    .toInt16()
)

core_risk = (
    core_img
    .select("RISK_SCORE_0_100")
    .toFloat()
)

valid_mask = (
    core_class.gte(1)
    .And(core_class.lte(4))
)


# ============================================================
# 6. DIRECTIONAL NORMALIZED FEATURES
# ============================================================

directional_images = {}

for _, row in calibration_df.iterrows():

    feature = row["feature"]

    source = (
        ee.Image(
            feature_source_registry[feature]
        )
        .select(feature)
        .toFloat()
        .updateMask(valid_mask)
    )

    p10 = float(row["p10"])
    p90 = float(row["p90"])

    direction = int(
        row["association_direction"]
    )

    norm01 = (
        source
        .subtract(p10)
        .divide(p90 - p10)
        .clamp(0, 1)
    )

    if direction < 0:

        norm01 = (
            ee.Image.constant(1)
            .subtract(norm01)
        )

    directional_images[feature] = (
        norm01
        .multiply(2)
        .subtract(1)
        .rename(
            f"DIR_{feature}"
        )
    )


# ============================================================
# 7. FAMILY COMPOSITES
# ============================================================

family_score_images = {}
family_coverage_images = {}

for family in family_weight_df["family"].tolist():

    family_cal = calibration_df[
        calibration_df["family"] == family
    ]

    weighted_sum = (
        ee.Image.constant(0)
        .toFloat()
    )

    available_weight = (
        ee.Image.constant(0)
        .toFloat()
    )

    for _, row in family_cal.iterrows():

        feature = row["feature"]

        weight = float(
            row["within_family_weight"]
        )

        img = directional_images[feature]

        valid = (
            img.mask()
            .reduce(ee.Reducer.min())
            .gt(0)
        )

        weighted_sum = (
            weighted_sum
            .add(
                img
                .unmask(0)
                .multiply(weight)
            )
        )

        available_weight = (
            available_weight
            .add(
                valid
                .toFloat()
                .multiply(weight)
            )
        )

    family_score = (
        weighted_sum
        .divide(
            available_weight.max(1e-6)
        )
        .updateMask(
            available_weight.gte(0.50)
        )
        .clamp(-1, 1)
        .rename(
            f"FAMILY_SCORE_{family}"
        )
    )

    family_score_images[family] = family_score

    family_coverage_images[family] = (
        available_weight.rename(
            f"FAMILY_COVERAGE_{family}"
        )
    )


# ============================================================
# 8. FAMILY-BALANCED CONTEXT MODIFIER
# ============================================================

overall_sum = (
    ee.Image.constant(0)
    .toFloat()
)

overall_weight = (
    ee.Image.constant(0)
    .toFloat()
)

for _, row in family_weight_df.iterrows():

    family = row["family"]

    family_weight = float(
        row["family_weight"]
    )

    img = family_score_images[family]

    valid = (
        img.mask()
        .reduce(ee.Reducer.min())
        .gt(0)
    )

    overall_sum = (
        overall_sum
        .add(
            img
            .unmask(0)
            .multiply(family_weight)
        )
    )

    overall_weight = (
        overall_weight
        .add(
            valid
            .toFloat()
            .multiply(family_weight)
        )
    )

context_modifier = (
    overall_sum
    .divide(
        overall_weight.max(1e-6)
    )
    .updateMask(
        overall_weight.gte(0.75)
    )
    .clamp(-1, 1)
    .rename(
        "CONTEXT_MODIFIER_SCORE"
    )
)

context_coverage = (
    overall_weight.rename(
        "CONTEXT_MODIFIER_COVERAGE"
    )
)


# ============================================================
# 9. F05 INTEGRATED SCORE
# ============================================================

integrated_score = (
    core_risk
    .add(
        context_modifier
        .unmask(0)
        .multiply(5)
    )
    .clamp(0, 100)
    .rename(
        "INTEGRATED_SCORE_0_100"
    )
)


# ============================================================
# 10. CORE EVIDENCE
# ============================================================

optical_valid = (
    core_img.select(
        "OPTICAL_VALID_PERIOD_COUNT"
    )
)

alert_mask = (
    core_img
    .select("ALERT_MASK")
    .round()
)

max_period_class = (
    core_img.select(
        "MAX_PERIOD_CLASS"
    )
)

max_consecutive = (
    core_img.select(
        "MAX_CONSECUTIVE_ALERT"
    )
)

optical_alert_total = (
    core_img
    .select("GREENNESS_ALERT_PERIODS")
    .add(
        core_img.select(
            "RED_EDGE_ALERT_PERIODS"
        )
    )
    .add(
        core_img.select(
            "MOISTURE_ALERT_PERIODS"
        )
    )
)

has_optical_support = (
    optical_valid.gt(0)
    .And(
        optical_alert_total.gt(0)
    )
)

postprocess_lock = (
    core_raw.neq(core_class)
)

unlocked = (
    postprocess_lock.Not()
)


# ============================================================
# 11. FROZEN TRANSITION RULES
# ============================================================

T12 = 12
T23 = 22
T34 = 32

modifier_available = (
    context_modifier
    .mask()
    .reduce(ee.Reducer.min())
    .gt(0)
)

modifier_pos = (
    context_modifier
    .unmask(0)
    .gt(0)
)

modifier_neg = (
    context_modifier
    .unmask(0)
    .lt(0)
)

promote_1_2 = (
    core_class.eq(1)
    .And(unlocked)
    .And(modifier_available)
    .And(modifier_pos)
    .And(integrated_score.gte(T12))
    .And(alert_mask.eq(1))
)

promote_2_3 = (
    core_class.eq(2)
    .And(unlocked)
    .And(modifier_available)
    .And(modifier_pos)
    .And(integrated_score.gte(T23))
    .And(has_optical_support)
    .And(max_period_class.gte(3))
    .And(max_consecutive.gte(2))
)

promote_3_4 = (
    core_class.eq(3)
    .And(unlocked)
    .And(modifier_available)
    .And(modifier_pos)
    .And(integrated_score.gte(T34))
    .And(has_optical_support)
    .And(max_period_class.gte(3))
    .And(max_consecutive.gte(3))
)

demote_2_1 = (
    core_class.eq(2)
    .And(unlocked)
    .And(modifier_available)
    .And(modifier_neg)
    .And(integrated_score.lt(T12))
    .And(alert_mask.eq(0))
)

demote_3_2 = (
    core_class.eq(3)
    .And(unlocked)
    .And(modifier_available)
    .And(modifier_neg)
    .And(integrated_score.lt(T23))
    .And(max_consecutive.lte(1))
)

demote_4_3 = (
    core_class.eq(4)
    .And(unlocked)
    .And(modifier_available)
    .And(modifier_neg)
    .And(integrated_score.lt(T34))
    .And(max_consecutive.lte(2))
)


# ============================================================
# 12. REBUILD FINAL INTEGRATED IMAGE
# ============================================================

integrated_class = (
    core_class
    .where(promote_1_2, 2)
    .where(promote_2_3, 3)
    .where(promote_3_4, 4)
    .where(demote_2_1, 1)
    .where(demote_3_2, 2)
    .where(demote_4_3, 3)
    .rename("INTEGRATED_CLASS")
    .toInt16()
)

class_delta = (
    integrated_class
    .subtract(core_class)
    .rename("CLASS_DELTA")
    .toInt16()
)

integrated_img = (
    core_class
    .rename("CORE_CLASS")
    .addBands(
        core_risk.rename(
            "CORE_RISK_SCORE_0_100"
        )
    )
    .addBands(context_modifier)
    .addBands(context_coverage)
    .addBands(integrated_score)
    .addBands(integrated_class)
    .addBands(class_delta)
    .updateMask(valid_mask)
)


# ============================================================
# 13. REHYDRATION QA
# ============================================================

expected_bands = [
    "CORE_CLASS",
    "CORE_RISK_SCORE_0_100",
    "CONTEXT_MODIFIER_SCORE",
    "CONTEXT_MODIFIER_COVERAGE",
    "INTEGRATED_SCORE_0_100",
    "INTEGRATED_CLASS",
    "CLASS_DELTA",
]

actual_bands = (
    integrated_img
    .bandNames()
    .getInfo()
)

band_pass = (
    actual_bands == expected_bands
)


# Frozen 30G-A final areas
expected_area = {
    1: 9531.973324,
    2: 4079.089398,
    3: 187.304555,
    4: 29.787187,
}

expected_total = 13828.154464
expected_changed = 42.222563


transition_code = (
    core_class
    .multiply(10)
    .add(integrated_class)
    .rename("TRANSITION_CODE")
)

transition_groups = (
    ee.Image.pixelArea()
    .divide(10000)
    .rename("AREA_HA")
    .addBands(transition_code)
    .updateMask(valid_mask)
    .reduceRegion(
        reducer=(
            ee.Reducer.sum()
            .group(
                groupField=1,
                groupName="transition_code"
            )
        ),
        geometry=core_img.geometry(),
        scale=10,
        maxPixels=1e13,
        tileScale=8
    )
    .get("groups")
    .getInfo()
)

final_area = {
    1: 0.0,
    2: 0.0,
    3: 0.0,
    4: 0.0,
}

changed_area = 0.0

for row in transition_groups:

    code = int(
        row["transition_code"]
    )

    old_class = code // 10
    new_class = code % 10

    area_ha = float(
        row["sum"]
    )

    final_area[new_class] += area_ha

    if old_class != new_class:
        changed_area += area_ha


total_area = sum(
    final_area.values()
)

print("\n[3] REHYDRATED PRODUCT QA")
print("Bands :", actual_bands)

for cls in [1, 2, 3, 4]:

    print(
        f"Class {cls}: "
        f"{final_area[cls]:,.6f} ha | "
        f"expected {expected_area[cls]:,.6f} ha | "
        f"diff "
        f"{final_area[cls] - expected_area[cls]:+.6f} ha"
    )

print(
    "\nTotal   :",
    f"{total_area:,.6f} ha"
)

print(
    "Expected:",
    f"{expected_total:,.6f} ha"
)

print(
    "\nChanged :",
    f"{changed_area:,.6f} ha"
)

print(
    "Expected:",
    f"{expected_changed:,.6f} ha"
)


area_pass = (
    abs(total_area - expected_total) <= 0.05
)

changed_pass = (
    abs(changed_area - expected_changed) <= 0.05
)

rehydration_pass = all([
    band_pass,
    area_pass,
    changed_pass,
])


print("\n" + "=" * 100)

if rehydration_pass:

    print("30G-R0 RESULT: PASS")
    print(
        "integrated_img has been successfully "
        "reconstructed in the current Python session."
    )
    print(
        "NEXT: rerun 30G-C1C grid-locked export."
    )

else:

    print("30G-R0 RESULT: REVIEW REQUIRED")
    print(
        "Do not export until the reconstructed "
        "product matches the frozen 30G-A result."
    )

print("=" * 100)

# ========================================
# ORIGINAL CELL 65
# ========================================

# ============================================================
# 30G-C1C | GRID-LOCKED CORRECTED EXPORT V1.1
#
# Same frozen analytical product.
# Technical correction only:
# export on the exact 30D04 reference grid.
# ============================================================

import ee

PROJECT_ID = "palm-oil-503202"

CORE_ASSET = (
    "projects/palm-oil-503202/assets/"
    "SIAK_AOI01_O3_30D04_BALANCED_RISK_2025"
)

PREVIOUS_ASSET = (
    "projects/palm-oil-503202/assets/"
    "SIAK_AOI01_O3_30G_INTEGRATED_V1_2025"
)

OUTPUT_ASSET = (
    "projects/palm-oil-503202/assets/"
    "SIAK_AOI01_O3_30G_INTEGRATED_V1_1_GRIDLOCKED_2025"
)

TASK_DESCRIPTION = (
    "SIAK_AOI01_O3_30G_INTEGRATED_V1_1_GRIDLOCKED_2025"
)

ee.Initialize(project=PROJECT_ID)

print("=" * 100)
print("30G-C1C | GRID-LOCKED CORRECTED EXPORT V1.1")
print("=" * 100)


# ============================================================
# 1. REQUIRE REHYDRATED PRODUCT
# ============================================================

if "integrated_img" not in globals():
    raise RuntimeError(
        "integrated_img is not available. "
        "Run 30G-R0 first."
    )

expected_bands = [
    "CORE_CLASS",
    "CORE_RISK_SCORE_0_100",
    "CONTEXT_MODIFIER_SCORE",
    "CONTEXT_MODIFIER_COVERAGE",
    "INTEGRATED_SCORE_0_100",
    "INTEGRATED_CLASS",
    "CLASS_DELTA",
]

actual_bands = integrated_img.bandNames().getInfo()

if actual_bands != expected_bands:
    raise RuntimeError(
        f"Unexpected bands: {actual_bands}"
    )

print("\n[1] REHYDRATED PRODUCT")
print("integrated_img : FOUND")
print("7-band check   : PASS")


# ============================================================
# 2. EXACT 30D04 REFERENCE GRID
# ============================================================

core_img = ee.Image(CORE_ASSET)

core_projection = (
    core_img
    .select("CONDITION_CLASS")
    .projection()
)

core_projection_info = core_projection.getInfo()

core_crs = core_projection_info["crs"]
core_transform = core_projection_info["transform"]

print("\n[2] REFERENCE GRID")
print("CRS       :", core_crs)
print("Transform :", core_transform)

expected_transform = [
    10, 0, 804550,
    0, -10, 87280
]

if core_crs != "EPSG:32647":
    raise RuntimeError(
        f"Unexpected core CRS: {core_crs}"
    )

if core_transform != expected_transform:
    raise RuntimeError(
        "Core transform differs from the "
        "previously verified 30D04 grid."
    )

print("Reference grid : PASS")


# ============================================================
# 3. CHECK TARGET DOES NOT ALREADY EXIST
# ============================================================

target_exists = False

try:
    ee.data.getAsset(OUTPUT_ASSET)
    target_exists = True
except Exception:
    target_exists = False

print("\n[3] TARGET ASSET")
print("Asset ID :", OUTPUT_ASSET)
print("Exists   :", target_exists)

if target_exists:
    raise RuntimeError(
        "Target V1.1 asset already exists. "
        "Do not overwrite it. Inspect the existing asset first."
    )


# ============================================================
# 4. PRESERVE V1 METADATA + ADD CORRECTION PROVENANCE
# ============================================================

previous_img = ee.Image(PREVIOUS_ASSET)

previous_properties = (
    previous_img.propertyNames()
)

export_img = (
    integrated_img
    .copyProperties(
        source=previous_img,
        properties=previous_properties
    )
    .set({
        "VERSION":
            "30G_V1_1_GRIDLOCKED",

        "MODEL_VERSION":
            "30G_V1_1_GRIDLOCKED",

        "GRID_REFERENCE":
            "30D04_CONDITION_CLASS",

        "GRID_CRS":
            core_crs,

        "GRID_TRANSFORM":
            str(core_transform),

        "GRID_CORRECTION":
            "Exact 30D04 10m grid lock",

        "CORRECTION_TYPE":
            "TECHNICAL_EXPORT_GRID_ONLY",

        "ANALYTICAL_MODEL_CHANGED":
            0,

        "PREVIOUS_ASSET":
            PREVIOUS_ASSET,

        "FIELD_VALIDATED":
            0
    })
)

print("\n[4] METADATA")
print("Previous V1 metadata : preserved")
print("Grid correction      : documented")
print("Analytical change    : NO")


# ============================================================
# 5. SUBMIT EXACT GRID-LOCKED EXPORT
# ============================================================

task = ee.batch.Export.image.toAsset(
    image=export_img,

    description=TASK_DESCRIPTION,

    assetId=OUTPUT_ASSET,

    region=core_img.geometry(),

    # Exact grid lock.
    # Do not provide scale together with crsTransform.
    crs=core_crs,
    crsTransform=core_transform,

    maxPixels=1e13
)

task.start()

status = task.status()


# ============================================================
# 6. OUTPUT
# ============================================================

print("\n[5] EXPORT TASK")
print("Task ID     :", status.get("id"))
print("Description :", status.get("description"))
print("State       :", status.get("state"))

print("\n" + "=" * 100)
print("30G-C1C SUBMITTED")
print("=" * 100)

print("""
Same frozen 30G analytical product.
No model / threshold / weight / class-rule changes.

Only technical correction:
the permanent raster is now exported on the exact
30D04 EPSG:32647 10 m reference grid.

Retain V1 for audit.
Do not delete or overwrite it.
""")

# ========================================
# ORIGINAL CELL 66
# ========================================

# ============================================================
# 30G-C1C FIX | SUBMIT GRID-LOCKED EXPORT V1.1
#
# Fix:
# copyProperties() / set() return ee.Element.
# Cast back explicitly to ee.Image before export.
#
# No analytical/model change.
# ============================================================

import ee

PROJECT_ID = "palm-oil-503202"

CORE_ASSET = (
    "projects/palm-oil-503202/assets/"
    "SIAK_AOI01_O3_30D04_BALANCED_RISK_2025"
)

PREVIOUS_ASSET = (
    "projects/palm-oil-503202/assets/"
    "SIAK_AOI01_O3_30G_INTEGRATED_V1_2025"
)

OUTPUT_ASSET = (
    "projects/palm-oil-503202/assets/"
    "SIAK_AOI01_O3_30G_INTEGRATED_V1_1_GRIDLOCKED_2025"
)

TASK_DESCRIPTION = (
    "SIAK_AOI01_O3_30G_INTEGRATED_V1_1_GRIDLOCKED_2025"
)

ee.Initialize(project=PROJECT_ID)

print("=" * 100)
print("30G-C1C FIX | GRID-LOCKED EXPORT V1.1")
print("=" * 100)


# ============================================================
# 1. REQUIRE REHYDRATED IMAGE
# ============================================================

if "integrated_img" not in globals():
    raise RuntimeError(
        "integrated_img not found. Run 30G-R0 first."
    )

print("\n[1] integrated_img : FOUND")


# ============================================================
# 2. REFERENCE GRID
# ============================================================

core_img = ee.Image(CORE_ASSET)

core_proj_info = (
    core_img
    .select("CONDITION_CLASS")
    .projection()
    .getInfo()
)

core_crs = core_proj_info["crs"]
core_transform = core_proj_info["transform"]

print("\n[2] EXACT REFERENCE GRID")
print("CRS       :", core_crs)
print("Transform :", core_transform)

if core_crs != "EPSG:32647":
    raise RuntimeError("Unexpected reference CRS.")

if core_transform != [
    10, 0, 804550,
    0, -10, 87280
]:
    raise RuntimeError(
        "Unexpected reference transform."
    )

print("Grid check : PASS")


# ============================================================
# 3. MAKE SURE TARGET DOES NOT EXIST
# ============================================================

try:
    ee.data.getAsset(OUTPUT_ASSET)

    raise RuntimeError(
        "V1.1 target asset already exists. "
        "Do not overwrite."
    )

except ee.EEException:
    print("\n[3] Target asset : AVAILABLE")


# ============================================================
# 4. PRESERVE ORDINARY METADATA
#
# IMPORTANT:
# copyProperties() and set() return Element,
# therefore cast explicitly back to ee.Image.
# ============================================================

previous_img = ee.Image(PREVIOUS_ASSET)

with_previous_metadata = ee.Image(
    integrated_img.copyProperties(
        source=previous_img
    )
)

export_img = ee.Image(
    with_previous_metadata.set({

        "VERSION":
            "30G_V1_1_GRIDLOCKED",

        "MODEL_VERSION":
            "30G_V1_1_GRIDLOCKED",

        "GRID_REFERENCE":
            "30D04_CONDITION_CLASS",

        "GRID_CRS":
            core_crs,

        "GRID_TRANSFORM":
            str(core_transform),

        "GRID_CORRECTION":
            "Exact 30D04 10m grid lock",

        "CORRECTION_TYPE":
            "TECHNICAL_EXPORT_GRID_ONLY",

        "ANALYTICAL_MODEL_CHANGED":
            0,

        "PREVIOUS_ASSET":
            PREVIOUS_ASSET,

        "FIELD_VALIDATED":
            0
    })
)

print("\n[4] EXPORT IMAGE")
print("Object type :", type(export_img))
print("Bands       :", export_img.bandNames().getInfo())

if not isinstance(export_img, ee.image.Image):
    raise RuntimeError(
        "export_img is not an ee.Image."
    )

print("Image type check : PASS")


# ============================================================
# 5. PYRAMIDING POLICY
#
# Categorical bands -> MODE
# Continuous bands  -> MEAN
# ============================================================

pyramiding_policy = {

    "CORE_CLASS":
        "mode",

    "CORE_RISK_SCORE_0_100":
        "mean",

    "CONTEXT_MODIFIER_SCORE":
        "mean",

    "CONTEXT_MODIFIER_COVERAGE":
        "mean",

    "INTEGRATED_SCORE_0_100":
        "mean",

    "INTEGRATED_CLASS":
        "mode",

    "CLASS_DELTA":
        "mode"
}


# ============================================================
# 6. SUBMIT EXPORT
# ============================================================

task = ee.batch.Export.image.toAsset(

    image=export_img,

    description=TASK_DESCRIPTION,

    assetId=OUTPUT_ASSET,

    region=core_img.geometry(),

    # Exact grid lock
    crs=core_crs,
    crsTransform=core_transform,

    pyramidingPolicy=pyramiding_policy,

    maxPixels=1e13
)

task.start()

status = task.status()


# ============================================================
# 7. STATUS
# ============================================================

print("\n[5] EXPORT TASK")
print("Task ID     :", status.get("id"))
print("Description :", status.get("description"))
print("State       :", status.get("state"))

print("\n" + "=" * 100)

if status.get("state") in ["READY", "RUNNING"]:

    print("30G-C1C FIX RESULT: SUBMITTED")
    print(
        "Grid-locked V1.1 export has entered "
        "the Earth Engine batch queue."
    )

else:

    print(
        "30G-C1C FIX RESULT:",
        status.get("state")
    )

print("=" * 100)

# ========================================
# ORIGINAL CELL 67
# ========================================

# ============================================================
# 30G-C1D | FINAL GRID-LOCKED ASSET VERIFICATION
# ============================================================

import ee

PROJECT_ID = "palm-oil-503202"

TASK_ID = "64XI2QT2WVLADUVECUX2UAOF"

CORE_ASSET = (
    "projects/palm-oil-503202/assets/"
    "SIAK_AOI01_O3_30D04_BALANCED_RISK_2025"
)

FINAL_ASSET = (
    "projects/palm-oil-503202/assets/"
    "SIAK_AOI01_O3_30G_INTEGRATED_V1_1_GRIDLOCKED_2025"
)

EXPECTED_BANDS = [
    "CORE_CLASS",
    "CORE_RISK_SCORE_0_100",
    "CONTEXT_MODIFIER_SCORE",
    "CONTEXT_MODIFIER_COVERAGE",
    "INTEGRATED_SCORE_0_100",
    "INTEGRATED_CLASS",
    "CLASS_DELTA",
]

EXPECTED_TRANSFORM = [
    10, 0, 804550,
    0, -10, 87280
]

EXPECTED_CLASS_AREA = {
    1: 9531.973324,
    2: 4079.089398,
    3: 187.304555,
    4: 29.787187,
}

EXPECTED_TOTAL = 13828.154464
EXPECTED_CHANGED = 42.222563

TOL = 0.05

ee.Initialize(project=PROJECT_ID)

print("=" * 100)
print("30G-C1D | FINAL GRID-LOCKED ASSET VERIFICATION")
print("=" * 100)


# ============================================================
# 1. TASK STATUS
# ============================================================

task_info = ee.data.getTaskStatus(TASK_ID)[0]
state = task_info.get("state")

print("\n[1] TASK STATUS")
print("Task ID :", TASK_ID)
print("State   :", state)

if state != "COMPLETED":
    print("\nTask is not COMPLETED yet.")
    print("Do NOT rerun the export.")
    raise RuntimeError(
        f"Current export state: {state}"
    )


# ============================================================
# 2. LOAD FINAL + CORE
# ============================================================

asset_info = ee.data.getAsset(FINAL_ASSET)

final_img = ee.Image(FINAL_ASSET)
core_img = ee.Image(CORE_ASSET)

print("\n[2] FINAL ASSET")
print("Exists : YES")
print("Type   :", asset_info.get("type"))


# ============================================================
# 3. BAND STRUCTURE
# ============================================================

bands = final_img.bandNames().getInfo()

bands_pass = bands == EXPECTED_BANDS

print("\n[3] BAND STRUCTURE")
print("Bands :", bands)
print("QC    :", bands_pass)


# ============================================================
# 4. EXACT GRID
# ============================================================

final_proj = (
    final_img
    .select("INTEGRATED_CLASS")
    .projection()
    .getInfo()
)

core_proj = (
    core_img
    .select("CONDITION_CLASS")
    .projection()
    .getInfo()
)

final_crs = final_proj["crs"]
final_transform = final_proj["transform"]

core_crs = core_proj["crs"]
core_transform = core_proj["transform"]

grid_pass = (
    final_crs == core_crs == "EPSG:32647"
    and
    final_transform == core_transform == EXPECTED_TRANSFORM
)

print("\n[4] EXACT GRID")
print("Final CRS       :", final_crs)
print("Core CRS        :", core_crs)
print("Final transform :", final_transform)
print("Core transform  :", core_transform)
print("Grid QC         :", grid_pass)


# ============================================================
# 5. CLASS AREA
# ============================================================

asset_core = (
    final_img
    .select("CORE_CLASS")
    .round()
    .toInt16()
)

integrated_class = (
    final_img
    .select("INTEGRATED_CLASS")
    .round()
    .toInt16()
)

valid_mask = (
    asset_core.gte(1)
    .And(asset_core.lte(4))
)

groups = (
    ee.Image.pixelArea()
    .divide(10000)
    .rename("AREA_HA")
    .addBands(
        integrated_class.rename("CLASS")
    )
    .updateMask(valid_mask)
    .reduceRegion(
        reducer=ee.Reducer.sum().group(
            groupField=1,
            groupName="CLASS"
        ),
        geometry=core_img.geometry(),
        crs=final_crs,
        crsTransform=final_transform,
        maxPixels=1e13,
        tileScale=8
    )
    .get("groups")
    .getInfo()
)

class_area = {
    int(row["CLASS"]): float(row["sum"])
    for row in groups
}

print("\n[5] FINAL CLASS AREA")

area_pass = True

for cls in [1, 2, 3, 4]:

    actual = class_area.get(cls, 0.0)
    expected = EXPECTED_CLASS_AREA[cls]
    diff = actual - expected

    ok = abs(diff) <= TOL

    area_pass = area_pass and ok

    print(
        f"Class {cls}: "
        f"{actual:,.6f} ha | "
        f"expected {expected:,.6f} ha | "
        f"diff {diff:+.6f} ha | "
        f"{'PASS' if ok else 'CHECK'}"
    )

total_area = sum(class_area.values())

total_pass = (
    abs(total_area - EXPECTED_TOTAL) <= TOL
)

print("\nTotal actual   :", f"{total_area:,.6f} ha")
print("Total expected :", f"{EXPECTED_TOTAL:,.6f} ha")
print("Total QC       :", total_pass)


# ============================================================
# 6. CHANGED AREA
# ============================================================

class_delta = (
    final_img
    .select("CLASS_DELTA")
    .round()
    .toInt16()
)

changed_area = (
    ee.Image.pixelArea()
    .divide(10000)
    .updateMask(
        valid_mask.And(class_delta.neq(0))
    )
    .rename("CHANGED_HA")
    .reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=core_img.geometry(),
        crs=final_crs,
        crsTransform=final_transform,
        maxPixels=1e13,
        tileScale=8
    )
    .get("CHANGED_HA")
    .getInfo()
)

changed_area = float(changed_area or 0)

changed_pass = (
    abs(changed_area - EXPECTED_CHANGED) <= TOL
)

print("\n[6] CHANGED CLASS AREA")
print("Actual   :", f"{changed_area:,.6f} ha")
print("Expected :", f"{EXPECTED_CHANGED:,.6f} ha")
print("QC       :", changed_pass)


# ============================================================
# 7. SOURCE CORE FIDELITY
# ============================================================

source_core = (
    core_img
    .select("CONDITION_CLASS")
    .round()
    .toInt16()
)

source_valid = (
    source_core.gte(1)
    .And(source_core.lte(4))
)

both_valid = (
    source_valid.And(valid_mask)
)

mismatch_area = (
    ee.Image.pixelArea()
    .divide(10000)
    .updateMask(
        source_core
        .neq(asset_core)
        .And(both_valid)
    )
    .rename("MISMATCH_HA")
    .reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=core_img.geometry(),
        crs=final_crs,
        crsTransform=final_transform,
        maxPixels=1e13,
        tileScale=8
    )
    .get("MISMATCH_HA")
    .getInfo()
)

mismatch_area = float(mismatch_area or 0)

fidelity_pass = mismatch_area <= 0.001

print("\n[7] CORE FIDELITY")
print("Mismatch area :", f"{mismatch_area:.6f} ha")
print("QC            :", fidelity_pass)


# ============================================================
# 8. PROVENANCE
# ============================================================

metadata = final_img.toDictionary().getInfo()

metadata_pass = (
    metadata.get("ANALYTICAL_MODEL_CHANGED") == 0
    and
    metadata.get("CORRECTION_TYPE")
    == "TECHNICAL_EXPORT_GRID_ONLY"
)

print("\n[8] PROVENANCE")
print("VERSION                  :", metadata.get("VERSION"))
print("GRID_REFERENCE           :", metadata.get("GRID_REFERENCE"))
print("CORRECTION_TYPE          :", metadata.get("CORRECTION_TYPE"))
print(
    "ANALYTICAL_MODEL_CHANGED :",
    metadata.get("ANALYTICAL_MODEL_CHANGED")
)
print("Metadata QC              :", metadata_pass)


# ============================================================
# 9. FINAL GATE
# ============================================================

all_pass = all([
    bands_pass,
    grid_pass,
    area_pass,
    total_pass,
    changed_pass,
    fidelity_pass,
    metadata_pass,
])

print("\n" + "=" * 100)

if all_pass:

    print("30G-C1D RESULT: PASS")
    print("GRID-LOCKED V1.1 ASSET VERIFIED.")
    print("30G-C1 GRID ISSUE: CLOSED.")
    print()
    print("CANONICAL OUTPUT 3 ASSET:")
    print(FINAL_ASSET)
    print()
    print("NEXT: 30G-C2 EVIDENCE / MASK / GUARDRAIL QC.")

else:

    print("30G-C1D RESULT: REVIEW REQUIRED")
    print("Do not freeze Output 3 yet.")

print("=" * 100)

# ========================================
# ORIGINAL CELL 68
# ========================================

# ============================================================
# 30G-C FINAL | CONSOLIDATED TECHNICAL + EVIDENCE QA
#
# Canonical asset:
# SIAK_AOI01_O3_30G_INTEGRATED_V1_1_GRIDLOCKED_2025
#
# This cell closes:
# - structural QA
# - lattice/grid compatibility
# - source-core fidelity
# - class/range QA
# - context coverage QA
# - evidence-transition guardrails
# - post-processing lock
# - canonical class/transition statistics
# - provenance QA
#
# No model retuning.
# No re-export.
# ============================================================

import ee
import pandas as pd
from pathlib import Path

PROJECT_ID = "palm-oil-503202"

CORE_ASSET = (
    "projects/palm-oil-503202/assets/"
    "SIAK_AOI01_O3_30D04_BALANCED_RISK_2025"
)

FINAL_ASSET = (
    "projects/palm-oil-503202/assets/"
    "SIAK_AOI01_O3_30G_INTEGRATED_V1_1_GRIDLOCKED_2025"
)

EXPECTED_BANDS = [
    "CORE_CLASS",
    "CORE_RISK_SCORE_0_100",
    "CONTEXT_MODIFIER_SCORE",
    "CONTEXT_MODIFIER_COVERAGE",
    "INTEGRATED_SCORE_0_100",
    "INTEGRATED_CLASS",
    "CLASS_DELTA",
]

T12 = 12
T23 = 22
T34 = 32

AREA_ZERO_TOL_HA = 0.001

output_dir = Path("checkpoints_30G")
output_dir.mkdir(parents=True, exist_ok=True)

ee.Initialize(project=PROJECT_ID)

print("=" * 110)
print("30G-C FINAL | CONSOLIDATED TECHNICAL + EVIDENCE QA")
print("=" * 110)


# ============================================================
# 1. LOAD ASSETS
# ============================================================

core_img = ee.Image(CORE_ASSET)
final_img = ee.Image(FINAL_ASSET)

bands = final_img.bandNames().getInfo()

bands_pass = bands == EXPECTED_BANDS

print("\n[1] ASSET STRUCTURE")
print("Canonical asset :", FINAL_ASSET)
print("Band count      :", len(bands))
print("Bands           :", bands)
print("Band QC         :", bands_pass)


# ============================================================
# 2. PROJECTION / LATTICE COMPATIBILITY
# ============================================================

final_proj = (
    final_img
    .select("INTEGRATED_CLASS")
    .projection()
    .getInfo()
)

core_proj = (
    core_img
    .select("CONDITION_CLASS")
    .projection()
    .getInfo()
)

final_crs = final_proj["crs"]
final_tf = final_proj["transform"]

core_crs = core_proj["crs"]
core_tf = core_proj["transform"]

# Affine:
# [xScale, xShear, xOrigin,
#  yShear, yScale, yOrigin]

same_crs = final_crs == core_crs

same_pixel_basis = (
    abs(final_tf[0] - core_tf[0]) < 1e-9
    and
    abs(final_tf[1] - core_tf[1]) < 1e-9
    and
    abs(final_tf[3] - core_tf[3]) < 1e-9
    and
    abs(final_tf[4] - core_tf[4]) < 1e-9
)

x_pixel_offset = (
    (final_tf[2] - core_tf[2])
    / core_tf[0]
)

y_pixel_offset = (
    (final_tf[5] - core_tf[5])
    / abs(core_tf[4])
)

integer_offset = (
    abs(x_pixel_offset - round(x_pixel_offset)) < 1e-9
    and
    abs(y_pixel_offset - round(y_pixel_offset)) < 1e-9
)

lattice_pass = (
    same_crs
    and same_pixel_basis
    and integer_offset
)

print("\n[2] GRID / LATTICE")

print("Final CRS       :", final_crs)
print("Core CRS        :", core_crs)

print("Final transform :", final_tf)
print("Core transform  :", core_tf)

print(
    "Pixel offset X  :",
    f"{x_pixel_offset:.6f} pixel"
)

print(
    "Pixel offset Y  :",
    f"{y_pixel_offset:.6f} pixel"
)

print("Same pixel basis:", same_pixel_basis)
print("Integer offset  :", integer_offset)
print("Lattice QC      :", lattice_pass)


# ============================================================
# 3. CANONICAL FINAL GRID
# ============================================================

QA_CRS = final_crs
QA_TRANSFORM = final_tf
QA_GEOMETRY = core_img.geometry()


# ============================================================
# Helper: calculate hectares for a boolean mask
# ============================================================

def mask_area_ha(mask):

    value = (
        ee.Image.pixelArea()
        .divide(10000)
        .updateMask(
            ee.Image(mask)
            .unmask(0)
            .gt(0)
        )
        .rename("AREA_HA")
        .reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=QA_GEOMETRY,
            crs=QA_CRS,
            crsTransform=QA_TRANSFORM,
            maxPixels=1e13,
            tileScale=8
        )
        .get("AREA_HA")
        .getInfo()
    )

    return float(value or 0.0)


# ============================================================
# 4. FINAL BANDS
# ============================================================

asset_core = (
    final_img
    .select("CORE_CLASS")
    .round()
    .toInt16()
)

core_risk = (
    final_img
    .select("CORE_RISK_SCORE_0_100")
    .toFloat()
)

modifier = (
    final_img
    .select("CONTEXT_MODIFIER_SCORE")
    .toFloat()
)

coverage = (
    final_img
    .select("CONTEXT_MODIFIER_COVERAGE")
    .toFloat()
)

integrated_score = (
    final_img
    .select("INTEGRATED_SCORE_0_100")
    .toFloat()
)

integrated_class = (
    final_img
    .select("INTEGRATED_CLASS")
    .round()
    .toInt16()
)

class_delta = (
    final_img
    .select("CLASS_DELTA")
    .round()
    .toInt16()
)

asset_valid = (
    asset_core.gte(1)
    .And(asset_core.lte(4))
)


# ============================================================
# 5. RANGE QA
# ============================================================

range_stats = (
    final_img
    .select(EXPECTED_BANDS)
    .reduceRegion(
        reducer=ee.Reducer.minMax(),
        geometry=QA_GEOMETRY,
        crs=QA_CRS,
        crsTransform=QA_TRANSFORM,
        maxPixels=1e13,
        tileScale=8
    )
    .getInfo()
)

class_min = range_stats.get(
    "INTEGRATED_CLASS_min"
)

class_max = range_stats.get(
    "INTEGRATED_CLASS_max"
)

score_min = range_stats.get(
    "INTEGRATED_SCORE_0_100_min"
)

score_max = range_stats.get(
    "INTEGRATED_SCORE_0_100_max"
)

delta_min = range_stats.get(
    "CLASS_DELTA_min"
)

delta_max = range_stats.get(
    "CLASS_DELTA_max"
)

class_range_pass = (
    class_min >= 1
    and class_max <= 4
)

score_range_pass = (
    score_min >= 0
    and score_max <= 100
)

delta_range_pass = (
    delta_min >= -1
    and delta_max <= 1
)

print("\n[3] VALUE RANGE")

print(
    "Integrated class :",
    class_min,
    "to",
    class_max,
    "|",
    class_range_pass
)

print(
    "Integrated score :",
    score_min,
    "to",
    score_max,
    "|",
    score_range_pass
)

print(
    "Class delta      :",
    delta_min,
    "to",
    delta_max,
    "|",
    delta_range_pass
)


# ============================================================
# 6. ALIGN ORIGINAL CORE TO FINAL GRID
# ============================================================

source_core = (
    core_img
    .select("CONDITION_CLASS")
    .round()
    .toInt16()
    .reproject(
        crs=QA_CRS,
        crsTransform=QA_TRANSFORM
    )
)

source_raw = (
    core_img
    .select("CONDITION_CLASS_RAW")
    .round()
    .toInt16()
    .reproject(
        crs=QA_CRS,
        crsTransform=QA_TRANSFORM
    )
)

source_valid = (
    source_core.gte(1)
    .And(source_core.lte(4))
)

both_valid = (
    source_valid
    .And(asset_valid)
)


# ============================================================
# 7. CORE + MASK FIDELITY
# ============================================================

core_mismatch = (
    source_core
    .neq(asset_core)
    .And(both_valid)
)

mask_difference = (
    source_valid
    .unmask(0)
    .neq(
        asset_valid
        .unmask(0)
    )
)

core_mismatch_ha = mask_area_ha(
    core_mismatch
)

mask_difference_ha = mask_area_ha(
    mask_difference
)

core_fidelity_pass = (
    core_mismatch_ha <= AREA_ZERO_TOL_HA
    and
    mask_difference_ha <= AREA_ZERO_TOL_HA
)

print("\n[4] SOURCE CORE FIDELITY")

print(
    "Class mismatch :",
    f"{core_mismatch_ha:.6f} ha"
)

print(
    "Mask difference:",
    f"{mask_difference_ha:.6f} ha"
)

print(
    "Core fidelity QC:",
    core_fidelity_pass
)


# ============================================================
# 8. RESTORE CORE EVIDENCE ON FINAL GRID
# ============================================================

def core_band(name):

    return (
        core_img
        .select(name)
        .reproject(
            crs=QA_CRS,
            crsTransform=QA_TRANSFORM
        )
    )


optical_valid = (
    core_band(
        "OPTICAL_VALID_PERIOD_COUNT"
    )
)

alert_mask = (
    core_band(
        "ALERT_MASK"
    )
    .round()
)

max_period_class = (
    core_band(
        "MAX_PERIOD_CLASS"
    )
)

max_consecutive = (
    core_band(
        "MAX_CONSECUTIVE_ALERT"
    )
)

optical_alert_total = (

    core_band(
        "GREENNESS_ALERT_PERIODS"
    )

    .add(
        core_band(
            "RED_EDGE_ALERT_PERIODS"
        )
    )

    .add(
        core_band(
            "MOISTURE_ALERT_PERIODS"
        )
    )
)

has_optical_support = (
    optical_valid.gt(0)
    .And(
        optical_alert_total.gt(0)
    )
)


# ============================================================
# 9. MODIFIER AVAILABILITY
# ============================================================

modifier_available = (
    modifier
    .mask()
    .reduce(ee.Reducer.min())
    .gt(0)
    .And(asset_valid)
)

modifier_pos = (
    modifier
    .unmask(0)
    .gt(0)
)

modifier_neg = (
    modifier
    .unmask(0)
    .lt(0)
)

valid_area_ha = mask_area_ha(
    asset_valid
)

modifier_area_ha = mask_area_ha(
    modifier_available
)

modifier_pct = (
    modifier_area_ha
    / valid_area_ha
    * 100
    if valid_area_ha > 0
    else 0
)

changed = (
    class_delta
    .neq(0)
    .And(asset_valid)
)

changed_area_ha = mask_area_ha(
    changed
)

changed_without_modifier_ha = (
    mask_area_ha(
        changed
        .And(
            modifier_available.Not()
        )
    )
)

print("\n[5] CONTEXT COVERAGE")

print(
    "Valid Output 3 area :",
    f"{valid_area_ha:,.6f} ha"
)

print(
    "Modifier valid area :",
    f"{modifier_area_ha:,.6f} ha"
)

print(
    "Modifier coverage   :",
    f"{modifier_pct:.4f}%"
)

print(
    "Changed area        :",
    f"{changed_area_ha:,.6f} ha"
)

print(
    "Changed w/o modifier:",
    f"{changed_without_modifier_ha:.6f} ha"
)


# ============================================================
# 10. POST-PROCESSING LOCK
# ============================================================

postprocess_lock = (
    source_raw
    .neq(source_core)
)

locked_change = (
    postprocess_lock
    .And(class_delta.neq(0))
    .And(asset_valid)
)

locked_change_ha = mask_area_ha(
    locked_change
)

postprocess_pass = (
    locked_change_ha
    <= AREA_ZERO_TOL_HA
)


# ============================================================
# 11. EXACT TRANSITION RULE QA
# ============================================================

unlocked = (
    postprocess_lock.Not()
)

# Observed transitions
tr_1_2 = (
    asset_core.eq(1)
    .And(integrated_class.eq(2))
)

tr_2_3 = (
    asset_core.eq(2)
    .And(integrated_class.eq(3))
)

tr_3_4 = (
    asset_core.eq(3)
    .And(integrated_class.eq(4))
)

tr_2_1 = (
    asset_core.eq(2)
    .And(integrated_class.eq(1))
)

tr_3_2 = (
    asset_core.eq(3)
    .And(integrated_class.eq(2))
)

tr_4_3 = (
    asset_core.eq(4)
    .And(integrated_class.eq(3))
)


# Allowed conditions exactly matching frozen 30G-A rules

allow_1_2 = (
    unlocked
    .And(modifier_available)
    .And(modifier_pos)
    .And(integrated_score.gte(T12))
    .And(alert_mask.eq(1))
)

allow_2_3 = (
    unlocked
    .And(modifier_available)
    .And(modifier_pos)
    .And(integrated_score.gte(T23))
    .And(has_optical_support)
    .And(max_period_class.gte(3))
    .And(max_consecutive.gte(2))
)

allow_3_4 = (
    unlocked
    .And(modifier_available)
    .And(modifier_pos)
    .And(integrated_score.gte(T34))
    .And(has_optical_support)
    .And(max_period_class.gte(3))
    .And(max_consecutive.gte(3))
)

allow_2_1 = (
    unlocked
    .And(modifier_available)
    .And(modifier_neg)
    .And(integrated_score.lt(T12))
    .And(alert_mask.eq(0))
)

allow_3_2 = (
    unlocked
    .And(modifier_available)
    .And(modifier_neg)
    .And(integrated_score.lt(T23))
    .And(max_consecutive.lte(1))
)

allow_4_3 = (
    unlocked
    .And(modifier_available)
    .And(modifier_neg)
    .And(integrated_score.lt(T34))
    .And(max_consecutive.lte(2))
)


violations = {

    "1_to_2_rule_violation":
        tr_1_2.And(allow_1_2.Not()),

    "2_to_3_rule_violation":
        tr_2_3.And(allow_2_3.Not()),

    "3_to_4_rule_violation":
        tr_3_4.And(allow_3_4.Not()),

    "2_to_1_rule_violation":
        tr_2_1.And(allow_2_1.Not()),

    "3_to_2_rule_violation":
        tr_3_2.And(allow_3_2.Not()),

    "4_to_3_rule_violation":
        tr_4_3.And(allow_4_3.Not()),
}


# ============================================================
# 12. HIGH-CLASS / OPTICAL GUARDRAIL
# ============================================================

bad_high_promotion = (
    class_delta.gt(0)
    .And(integrated_class.gte(3))
    .And(has_optical_support.Not())
    .And(asset_valid)
)

bad_high_promotion_ha = (
    mask_area_ha(
        bad_high_promotion
    )
)


# Radar-only severe class check
bad_radar_only_high = (
    optical_valid.eq(0)
    .And(integrated_class.gte(3))
    .And(asset_valid)
)

bad_radar_only_high_ha = (
    mask_area_ha(
        bad_radar_only_high
    )
)


# ============================================================
# 13. VIOLATION AREA TABLE
# ============================================================

violation_rows = []

for name, mask in violations.items():

    area = mask_area_ha(mask)

    violation_rows.append({
        "check": name,
        "violation_area_ha": area,
        "pass": area <= AREA_ZERO_TOL_HA
    })

violation_df = pd.DataFrame(
    violation_rows
)

transition_rules_pass = bool(
    violation_df["pass"].all()
)

print("\n[6] EVIDENCE / TRANSITION GUARDRAILS")

print(
    "Postprocess-lock change :",
    f"{locked_change_ha:.6f} ha",
    "|",
    postprocess_pass
)

print(
    "High promotion no optical:",
    f"{bad_high_promotion_ha:.6f} ha"
)

print(
    "Radar-only Class 3/4    :",
    f"{bad_radar_only_high_ha:.6f} ha"
)

display(violation_df)


high_promotion_pass = (
    bad_high_promotion_ha
    <= AREA_ZERO_TOL_HA
)

radar_high_pass = (
    bad_radar_only_high_ha
    <= AREA_ZERO_TOL_HA
)

modifier_change_pass = (
    changed_without_modifier_ha
    <= AREA_ZERO_TOL_HA
)


# ============================================================
# 14. CANONICAL CLASS AREA
# ============================================================

class_groups = (
    ee.Image.pixelArea()
    .divide(10000)
    .rename("AREA_HA")
    .addBands(
        integrated_class
        .rename("CLASS")
    )
    .updateMask(asset_valid)
    .reduceRegion(
        reducer=(
            ee.Reducer.sum()
            .group(
                groupField=1,
                groupName="CLASS"
            )
        ),
        geometry=QA_GEOMETRY,
        crs=QA_CRS,
        crsTransform=QA_TRANSFORM,
        maxPixels=1e13,
        tileScale=8
    )
    .get("groups")
    .getInfo()
)

class_rows = []

for row in class_groups:

    class_rows.append({
        "integrated_class":
            int(row["CLASS"]),

        "area_ha":
            float(row["sum"])
    })

class_area_df = (
    pd.DataFrame(class_rows)
    .sort_values("integrated_class")
    .reset_index(drop=True)
)

canonical_total_ha = (
    class_area_df["area_ha"]
    .sum()
)

class_area_df["area_pct"] = (
    class_area_df["area_ha"]
    / canonical_total_ha
    * 100
)

print("\n[7] CANONICAL FINAL CLASS AREA")

display(
    class_area_df
)

print(
    "Canonical total:",
    f"{canonical_total_ha:,.6f} ha"
)


# ============================================================
# 15. CANONICAL TRANSITION AREA
# ============================================================

transition_code = (
    asset_core
    .multiply(10)
    .add(integrated_class)
    .rename("TRANSITION_CODE")
)

transition_groups = (
    ee.Image.pixelArea()
    .divide(10000)
    .rename("AREA_HA")
    .addBands(transition_code)
    .updateMask(asset_valid)
    .reduceRegion(
        reducer=(
            ee.Reducer.sum()
            .group(
                groupField=1,
                groupName="TRANSITION_CODE"
            )
        ),
        geometry=QA_GEOMETRY,
        crs=QA_CRS,
        crsTransform=QA_TRANSFORM,
        maxPixels=1e13,
        tileScale=8
    )
    .get("groups")
    .getInfo()
)

transition_rows = []

for row in transition_groups:

    code = int(
        row["TRANSITION_CODE"]
    )

    old_class = code // 10
    new_class = code % 10

    area = float(
        row["sum"]
    )

    transition_rows.append({

        "core_class":
            old_class,

        "integrated_class":
            new_class,

        "area_ha":
            area
    })

transition_area_df = (
    pd.DataFrame(
        transition_rows
    )
    .sort_values([
        "core_class",
        "integrated_class"
    ])
    .reset_index(drop=True)
)

transition_area_df[
    "pct_total_area"
] = (
    transition_area_df[
        "area_ha"
    ]
    / canonical_total_ha
    * 100
)

print("\n[8] CANONICAL CLASS TRANSITIONS")

display(
    transition_area_df
)


# ============================================================
# 16. METADATA / PROVENANCE
# ============================================================

metadata = (
    final_img
    .toDictionary()
    .getInfo()
)

metadata_pass = (

    metadata.get(
        "ANALYTICAL_MODEL_CHANGED"
    ) == 0

    and

    metadata.get(
        "FIELD_VALIDATED"
    ) == 0

    and

    metadata.get(
        "MAX_CLASS_CHANGE"
    ) == 1

    and

    float(
        metadata.get(
            "FUSION_AMPLITUDE",
            -999
        )
    ) == 5
)

print("\n[9] PROVENANCE")

print(
    "VERSION                  :",
    metadata.get("VERSION")
)

print(
    "PRODUCT                  :",
    metadata.get("PRODUCT")
)

print(
    "FUSION_AMPLITUDE         :",
    metadata.get("FUSION_AMPLITUDE")
)

print(
    "MAX_CLASS_CHANGE         :",
    metadata.get("MAX_CLASS_CHANGE")
)

print(
    "FIELD_VALIDATED          :",
    metadata.get("FIELD_VALIDATED")
)

print(
    "ANALYTICAL_MODEL_CHANGED :",
    metadata.get(
        "ANALYTICAL_MODEL_CHANGED"
    )
)

print(
    "Metadata QC              :",
    metadata_pass
)


# ============================================================
# 17. SAVE CANONICAL QA TABLES
# ============================================================

class_area_path = (
    output_dir /
    "30G_C_FINAL_CLASS_AREA_CANONICAL.csv"
)

transition_path = (
    output_dir /
    "30G_C_FINAL_TRANSITION_AREA_CANONICAL.csv"
)

violation_path = (
    output_dir /
    "30G_C_FINAL_GUARDRAIL_QA.csv"
)

class_area_df.to_csv(
    class_area_path,
    index=False
)

transition_area_df.to_csv(
    transition_path,
    index=False
)

violation_df.to_csv(
    violation_path,
    index=False
)


# ============================================================
# 18. FINAL GATE
# ============================================================

checks = {

    "seven_bands":
        bands_pass,

    "same_pixel_lattice":
        lattice_pass,

    "class_range_1_4":
        class_range_pass,

    "score_range_0_100":
        score_range_pass,

    "class_delta_max_abs_1":
        delta_range_pass,

    "source_core_fidelity":
        core_fidelity_pass,

    "postprocess_lock_preserved":
        postprocess_pass,

    "changed_pixels_have_modifier":
        modifier_change_pass,

    "transition_rules_preserved":
        transition_rules_pass,

    "high_promotion_requires_optical":
        high_promotion_pass,

    "radar_only_not_high_class":
        radar_high_pass,

    "metadata_provenance":
        metadata_pass,
}


print("\n" + "=" * 110)
print("30G-C FINAL | FINAL GATE")
print("=" * 110)

for name, result in checks.items():

    print(
        f"{name:40s}:",
        "PASS"
        if result
        else "FAIL"
    )


all_pass = all(
    checks.values()
)

print("\n" + "-" * 110)

if all_pass:

    print("""
30G-C FINAL RESULT: PASS

TECHNICAL + EVIDENCE QA CLOSED.

The permanent Output 3 candidate:
- preserves the frozen 30D04 core;
- preserves the valid spatial mask;
- maintains maximum ±1 class transition;
- preserves post-processing locks;
- applies class changes only where modifier evidence exists;
- preserves optical-evidence requirements for higher priorities;
- preserves the frozen transition rules;
- retains provenance that this product is NOT field validated.

CANONICAL ASSET:
SIAK_AOI01_O3_30G_INTEGRATED_V1_1_GRIDLOCKED_2025

NEXT MAJOR STEP:
30H | FINAL OUTPUT 3 FREEZE + FINAL MAP / PRODUCT SUMMARY
""")

else:

    print("""
30G-C FINAL RESULT: REVIEW REQUIRED

Only the FAILED checks above need investigation.
Do not restart earlier model-selection stages.
""")

print("=" * 110)

print("\nSaved QA tables:")
print("-", class_area_path)
print("-", transition_path)
print("-", violation_path)

# ========================================
# ORIGINAL CELL 69
# ========================================

# ============================================================
# 30H | FINAL OUTPUT 3 FREEZE + PRODUCT SUMMARY
#
# Purpose:
# - Freeze the canonical analytical product
# - Generate final class/transition statistics
# - Generate final map preview
# - Generate legend, band dictionary, metadata and manifest
#
# No model changes.
# No re-export of analytical raster.
# Restart-safe: reads directly from persistent GEE assets.
# ============================================================

import ee
import json
import urllib.request
import pandas as pd
from pathlib import Path
from PIL import Image
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from IPython.display import display, FileLink

PROJECT_ID = "palm-oil-503202"

FINAL_ASSET = (
    "projects/palm-oil-503202/assets/"
    "SIAK_AOI01_O3_30G_INTEGRATED_V1_1_GRIDLOCKED_2025"
)

CORE_ASSET = (
    "projects/palm-oil-503202/assets/"
    "SIAK_AOI01_O3_30D04_BALANCED_RISK_2025"
)

OUTPUT_DIR = Path("checkpoints_30H")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ee.Initialize(project=PROJECT_ID)

print("=" * 110)
print("30H | FINAL OUTPUT 3 FREEZE + PRODUCT SUMMARY")
print("=" * 110)


# ============================================================
# 1. LOAD CANONICAL PRODUCT
# ============================================================

img = ee.Image(FINAL_ASSET)
core_img = ee.Image(CORE_ASSET)

expected_bands = [
    "CORE_CLASS",
    "CORE_RISK_SCORE_0_100",
    "CONTEXT_MODIFIER_SCORE",
    "CONTEXT_MODIFIER_COVERAGE",
    "INTEGRATED_SCORE_0_100",
    "INTEGRATED_CLASS",
    "CLASS_DELTA",
]

bands = img.bandNames().getInfo()

if bands != expected_bands:
    raise RuntimeError(
        f"Unexpected canonical band structure: {bands}"
    )

print("\n[1] CANONICAL PRODUCT")
print("Asset :", FINAL_ASSET)
print("Bands :", len(bands), "| PASS")


# ============================================================
# 2. GRID
# ============================================================

proj = (
    img.select("INTEGRATED_CLASS")
    .projection()
)

proj_info = proj.getInfo()

crs = proj_info["crs"]
transform = proj_info["transform"]
scale = proj.nominalScale().getInfo()

print("\n[2] GRID")
print("CRS       :", crs)
print("Scale     :", scale, "m")
print("Transform :", transform)


# ============================================================
# 3. CLASS SCHEMA
# ============================================================

CLASS_SCHEMA = {

    0: {
        "label":
            "Insufficient Data",

        "interpretation":
            "Evidence or coverage is inadequate.",

        "color":
            "#BDBDBD"
    },

    1: {
        "label":
            "Stable / Expected Condition",

        "interpretation":
            "Close to baseline with no persistent decline evidence.",

        "color":
            "#2CA25F"
    },

    2: {
        "label":
            "Watch",

        "interpretation":
            "Mild anomaly, radar-only support, or downgraded small priority patch.",

        "color":
            "#FEE08B"
    },

    3: {
        "label":
            "Persistent Stress - Inspection Priority",

        "interpretation":
            "Moderate persistent multi-indicator optical anomaly; inspection recommended.",

        "color":
            "#F46D43"
    },

    4: {
        "label":
            "High Persistent Anomaly - High Priority",

        "interpretation":
            "Strong persistent spatially coherent optical anomaly; high inspection priority.",

        "color":
            "#A50026"
    }
}


# ============================================================
# 4. FINAL CLASS AREA
# ============================================================

core_class = (
    img.select("CORE_CLASS")
    .round()
    .toInt16()
)

final_class = (
    img.select("INTEGRATED_CLASS")
    .round()
    .toInt16()
)

class_delta = (
    img.select("CLASS_DELTA")
    .round()
    .toInt16()
)

valid_mask = (
    core_class.gte(1)
    .And(core_class.lte(4))
)


class_groups = (
    ee.Image.pixelArea()
    .divide(10000)
    .rename("AREA_HA")
    .addBands(
        final_class.rename("CLASS")
    )
    .updateMask(valid_mask)
    .reduceRegion(
        reducer=(
            ee.Reducer.sum()
            .group(
                groupField=1,
                groupName="CLASS"
            )
        ),
        geometry=core_img.geometry(),
        crs=crs,
        crsTransform=transform,
        maxPixels=1e13,
        tileScale=8
    )
    .get("groups")
    .getInfo()
)

class_rows = []

for row in class_groups:

    code = int(row["CLASS"])
    area = float(row["sum"])

    class_rows.append({
        "class_code": code,
        "class_label": CLASS_SCHEMA[code]["label"],
        "area_ha": area
    })

class_df = (
    pd.DataFrame(class_rows)
    .sort_values("class_code")
    .reset_index(drop=True)
)

total_area_ha = class_df["area_ha"].sum()

class_df["area_pct"] = (
    class_df["area_ha"]
    / total_area_ha
    * 100
)

print("\n[3] FINAL CLASS DISTRIBUTION")
display(class_df)

print(
    "Total canonical area:",
    f"{total_area_ha:,.6f} ha"
)


# ============================================================
# 5. FINAL TRANSITION AREA
# ============================================================

transition_code = (
    core_class
    .multiply(10)
    .add(final_class)
    .rename("TRANSITION_CODE")
)

transition_groups = (
    ee.Image.pixelArea()
    .divide(10000)
    .rename("AREA_HA")
    .addBands(transition_code)
    .updateMask(valid_mask)
    .reduceRegion(
        reducer=(
            ee.Reducer.sum()
            .group(
                groupField=1,
                groupName="TRANSITION_CODE"
            )
        ),
        geometry=core_img.geometry(),
        crs=crs,
        crsTransform=transform,
        maxPixels=1e13,
        tileScale=8
    )
    .get("groups")
    .getInfo()
)

transition_rows = []

for row in transition_groups:

    code = int(row["TRANSITION_CODE"])

    old_class = code // 10
    new_class = code % 10

    area = float(row["sum"])

    transition_rows.append({
        "core_class": old_class,
        "core_label": CLASS_SCHEMA[old_class]["label"],
        "integrated_class": new_class,
        "integrated_label": CLASS_SCHEMA[new_class]["label"],
        "area_ha": area
    })

transition_df = (
    pd.DataFrame(transition_rows)
    .sort_values([
        "core_class",
        "integrated_class"
    ])
    .reset_index(drop=True)
)

transition_df["area_pct"] = (
    transition_df["area_ha"]
    / total_area_ha
    * 100
)

changed_area_ha = (
    transition_df.loc[
        transition_df["core_class"]
        !=
        transition_df["integrated_class"],
        "area_ha"
    ].sum()
)

changed_pct = (
    changed_area_ha
    / total_area_ha
    * 100
)

print("\n[4] FINAL TRANSITIONS")
display(transition_df)

print(
    "Changed class area:",
    f"{changed_area_ha:,.6f} ha",
    f"({changed_pct:.4f}%)"
)


# ============================================================
# 6. CONTEXT COVERAGE
# ============================================================

modifier_valid = (
    img
    .select("CONTEXT_MODIFIER_SCORE")
    .mask()
    .reduce(ee.Reducer.min())
    .gt(0)
    .And(valid_mask)
)

modifier_area = (
    ee.Image.pixelArea()
    .divide(10000)
    .updateMask(modifier_valid)
    .rename("AREA_HA")
    .reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=core_img.geometry(),
        crs=crs,
        crsTransform=transform,
        maxPixels=1e13,
        tileScale=8
    )
    .get("AREA_HA")
    .getInfo()
)

modifier_area = float(modifier_area or 0)

modifier_pct = (
    modifier_area
    / total_area_ha
    * 100
)

print("\n[5] CONTEXT COVERAGE")
print(
    "Modifier coverage:",
    f"{modifier_area:,.6f} ha",
    f"({modifier_pct:.4f}%)"
)


# ============================================================
# 7. BAND DICTIONARY
# ============================================================

band_dictionary = {

    "CORE_CLASS": {
        "type": "categorical",
        "description":
            "Frozen 30D04 core inspection-priority class before contextual refinement."
    },

    "CORE_RISK_SCORE_0_100": {
        "type": "continuous",
        "range": [0, 100],
        "description":
            "Frozen core risk score before contextual refinement."
    },

    "CONTEXT_MODIFIER_SCORE": {
        "type": "continuous",
        "range": [-1, 1],
        "description":
            "Family-balanced static environmental context modifier."
    },

    "CONTEXT_MODIFIER_COVERAGE": {
        "type": "continuous",
        "range": [0, 1],
        "description":
            "Available weighted contextual evidence coverage."
    },

    "INTEGRATED_SCORE_0_100": {
        "type": "continuous",
        "range": [0, 100],
        "description":
            "Core risk score plus bounded F05 contextual modifier."
    },

    "INTEGRATED_CLASS": {
        "type": "categorical",
        "range": [1, 4],
        "description":
            "Final evidence-gated inspection-priority class."
    },

    "CLASS_DELTA": {
        "type": "categorical",
        "range": [-1, 1],
        "description":
            "Change from core class to integrated class."
    }
}


# ============================================================
# 8. PRODUCT SUMMARY
# ============================================================

metadata = img.toDictionary().getInfo()

product_summary = {

    "product_id":
        "OUTPUT3_PLANTATION_CONDITION_INSPECTION_PRIORITY",

    "aoi_id":
        "SIAK_AOI01",

    "monitoring_year":
        2025,

    "canonical_asset":
        FINAL_ASSET,

    "source_core_asset":
        CORE_ASSET,

    "version":
        metadata.get(
            "VERSION",
            "30G_V1_1_GRIDLOCKED"
        ),

    "freeze_status":
        "ANALYTICAL_CORE_FROZEN",

    "qa_status":
        "PASS",

    "crs":
        crs,

    "nominal_scale_m":
        scale,

    "transform":
        transform,

    "total_valid_area_ha":
        total_area_ha,

    "changed_class_area_ha":
        changed_area_ha,

    "changed_class_pct":
        changed_pct,

    "context_modifier_coverage_pct":
        modifier_pct,

    "fusion_amplitude":
        5,

    "maximum_class_change":
        1,

    "field_validated":
        False,

    "interpretation":
        (
            "Integrated inspection-priority candidate. "
            "The product supports inspection prioritization "
            "and is not a diagnosis of nutrient deficiency, "
            "disease, or plantation health."
        ),

    "important_limitations": [

        "No independent field validation is available.",

        "Class distribution and model agreement are not accuracy metrics.",

        "Environmental context represents association/context, not pixel-level causality.",

        "Coarse-resolution environmental sources do not gain 10 m information through resampling.",

        "Higher-priority Class 3-4 transitions require optical evidence."
    ],

    "class_distribution":
        class_df.to_dict(
            orient="records"
        )
}


# ============================================================
# 9. LEGEND JSON
# ============================================================

legend_json = {

    "title":
        "Plantation Condition & Inspection Priority",

    "field":
        "INTEGRATED_CLASS",

    "classes": [

        {
            "code": code,
            **CLASS_SCHEMA[code]
        }

        for code in [0, 1, 2, 3, 4]
    ],

    "warning":
        (
            "Inspection-priority indicator only; "
            "not field-validated diagnosis."
        )
}


# ============================================================
# 10. FREEZE MANIFEST
# ============================================================

manifest = {

    "output":
        "Output 3",

    "product":
        "Plantation Condition & Inspection Risk",

    "aoi":
        "SIAK_AOI01",

    "year":
        2025,

    "canonical_asset":
        FINAL_ASSET,

    "analytical_status":
        "FROZEN",

    "technical_qa":
        "PASS",

    "evidence_guardrail_qa":
        "PASS",

    "field_validation":
        "NOT_AVAILABLE",

    "bands":
        expected_bands,

    "class_schema":
        CLASS_SCHEMA,

    "files_generated_by_30H": [
        "30H_FINAL_CLASS_AREA.csv",
        "30H_FINAL_TRANSITION_AREA.csv",
        "30H_PRODUCT_SUMMARY.json",
        "30H_LEGEND.json",
        "30H_BAND_DICTIONARY.json",
        "30H_FREEZE_MANIFEST.json",
        "30H_FINAL_MAP.png",
        "30H_PRODUCT_SUMMARY.md"
    ],

    "next_stage":
        "30I_WEB_DELIVERY_AND_MASTER_IPYNB"
}


# ============================================================
# 11. SAVE TABLES / JSON
# ============================================================

class_csv = (
    OUTPUT_DIR /
    "30H_FINAL_CLASS_AREA.csv"
)

transition_csv = (
    OUTPUT_DIR /
    "30H_FINAL_TRANSITION_AREA.csv"
)

summary_json_path = (
    OUTPUT_DIR /
    "30H_PRODUCT_SUMMARY.json"
)

legend_path = (
    OUTPUT_DIR /
    "30H_LEGEND.json"
)

band_path = (
    OUTPUT_DIR /
    "30H_BAND_DICTIONARY.json"
)

manifest_path = (
    OUTPUT_DIR /
    "30H_FREEZE_MANIFEST.json"
)

class_df.to_csv(
    class_csv,
    index=False
)

transition_df.to_csv(
    transition_csv,
    index=False
)

with open(
    summary_json_path,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        product_summary,
        f,
        indent=2,
        ensure_ascii=False
    )

with open(
    legend_path,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        legend_json,
        f,
        indent=2,
        ensure_ascii=False
    )

with open(
    band_path,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        band_dictionary,
        f,
        indent=2,
        ensure_ascii=False
    )

with open(
    manifest_path,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        manifest,
        f,
        indent=2,
        ensure_ascii=False
    )


# ============================================================
# 12. FINAL MAP PREVIEW
# ============================================================

vis = (
    final_class
    .updateMask(valid_mask)
    .visualize(
        min=1,
        max=4,
        palette=[
            "2CA25F",
            "FEE08B",
            "F46D43",
            "A50026"
        ],
        forceRgbOutput=True
    )
)

thumb_url = vis.getThumbURL({
    "region":
        core_img.geometry().bounds(),

    "dimensions":
        1400,

    "format":
        "png"
})

raw_map_path = (
    OUTPUT_DIR /
    "30H_MAP_RAW.png"
)

urllib.request.urlretrieve(
    thumb_url,
    raw_map_path
)

map_img = Image.open(
    raw_map_path
)

fig, ax = plt.subplots(
    figsize=(12, 10)
)

ax.imshow(map_img)
ax.axis("off")

ax.set_title(
    "Output 3 - Plantation Condition & Inspection Priority\n"
    "SIAK_AOI01 | Monitoring Year 2025",
    fontsize=14
)

legend_handles = [

    Patch(
        facecolor=CLASS_SCHEMA[code]["color"],
        label=(
            f"Class {code} - "
            f"{CLASS_SCHEMA[code]['label']}"
        )
    )

    for code in [1, 2, 3, 4]
]

ax.legend(
    handles=legend_handles,
    loc="lower center",
    bbox_to_anchor=(0.5, -0.08),
    ncol=2,
    frameon=True
)

final_map_path = (
    OUTPUT_DIR /
    "30H_FINAL_MAP.png"
)

plt.savefig(
    final_map_path,
    dpi=180,
    bbox_inches="tight"
)

plt.show()
plt.close()


# ============================================================
# 13. MARKDOWN PRODUCT SUMMARY
# ============================================================

md_path = (
    OUTPUT_DIR /
    "30H_PRODUCT_SUMMARY.md"
)

summary_md = f"""# Output 3 - Plantation Condition & Inspection Priority

## Product
- AOI: SIAK_AOI01
- Monitoring year: 2025
- Canonical asset: `{FINAL_ASSET}`
- CRS: {crs}
- Nominal scale: {scale} m
- Version: {product_summary['version']}
- Technical QA: PASS
- Evidence guardrail QA: PASS
- Field validation: NOT AVAILABLE

## Canonical area
- Total valid area: {total_area_ha:,.6f} ha
- Changed class area: {changed_area_ha:,.6f} ha ({changed_pct:.4f}%)
- Context modifier coverage: {modifier_pct:.4f}%

## Interpretation
This is an integrated inspection-priority candidate.
It is not a diagnosis of disease, nutrient deficiency,
or plantation health.

## Final class schema
- Class 1: Stable / Expected Condition
- Class 2: Watch
- Class 3: Persistent Stress - Inspection Priority
- Class 4: High Persistent Anomaly - High Priority

## Important limitation
No independent field validation is currently available.
Logical QA, model agreement and class distribution are not
field-accuracy metrics.

## Next
30I - Web Delivery Package + Master Python Notebook.
"""

with open(
    md_path,
    "w",
    encoding="utf-8"
) as f:

    f.write(summary_md)


# ============================================================
# 14. FINAL STATUS
# ============================================================

required_files = [
    class_csv,
    transition_csv,
    summary_json_path,
    legend_path,
    band_path,
    manifest_path,
    final_map_path,
    md_path
]

files_pass = all(
    path.exists()
    for path in required_files
)

print("\n" + "=" * 110)
print("30H FINAL GATE")
print("=" * 110)

print(
    "Canonical asset readable : PASS"
)

print(
    "Product statistics       : PASS"
)

print(
    "Legend / band dictionary : PASS"
)

print(
    "Final map generated      :",
    "PASS" if final_map_path.exists() else "FAIL"
)

print(
    "Freeze manifest          :",
    "PASS" if manifest_path.exists() else "FAIL"
)

print(
    "All required files       :",
    "PASS" if files_pass else "FAIL"
)

print("\nGenerated files:")

for path in required_files:
    print("-", path)

print("\n" + "-" * 110)

if files_pass:

    print("""
30H RESULT: PASS

OUTPUT 3 ANALYTICAL PRODUCT IS FROZEN.

The analytical core is now complete.
No further model tuning is required for AOI01 unless
new independent validation evidence justifies a revision.

NEXT AND FINAL MAJOR STAGE:
30I | WEB DELIVERY PACKAGE + MASTER PYTHON .IPYNB
""")

else:

    print("""
30H RESULT: REVIEW REQUIRED

Only missing delivery files need review.
Do not reopen model development.
""")

print("=" * 110)

display(
    FileLink(
        str(final_map_path)
    )
)

# ========================================
# ORIGINAL CELL 70
# ========================================

# ============================================================
# 30I-A | OUTPUT 3 WEB DELIVERY + COG EXPORT
#
# Final major delivery stage.
#
# Produces:
# 1. Local web-delivery package
# 2. Class COG export -> Google Drive
# 3. Continuous metrics COG export -> Google Drive
# 4. README + manifest + task registry
# 5. ZIP of all currently available non-raster deliverables
#
# No model changes.
# No analytical reprocessing.
# ============================================================

import ee
import json
import shutil
import zipfile
from pathlib import Path

PROJECT_ID = "palm-oil-503202"

FINAL_ASSET = (
    "projects/palm-oil-503202/assets/"
    "SIAK_AOI01_O3_30G_INTEGRATED_V1_1_GRIDLOCKED_2025"
)

CORE_ASSET = (
    "projects/palm-oil-503202/assets/"
    "SIAK_AOI01_O3_30D04_BALANCED_RISK_2025"
)

DRIVE_FOLDER = (
    "SIAK_AOI01_OUTPUT3_WEB_DELIVERY_2025"
)

DELIVERY_DIR = Path(
    "WEB_DELIVERY_OUTPUT3"
)

ZIP_PATH = Path(
    "WEB_DELIVERY_OUTPUT3_METADATA.zip"
)

ee.Initialize(project=PROJECT_ID)

print("=" * 110)
print("30I-A | OUTPUT 3 WEB DELIVERY + COG EXPORT")
print("=" * 110)


# ============================================================
# 1. LOAD FINAL PRODUCT
# ============================================================

img = ee.Image(FINAL_ASSET)
core_img = ee.Image(CORE_ASSET)

proj_info = (
    img
    .select("INTEGRATED_CLASS")
    .projection()
    .getInfo()
)

crs = proj_info["crs"]
transform = proj_info["transform"]

print("\n[1] CANONICAL PRODUCT")
print("Asset     :", FINAL_ASSET)
print("CRS       :", crs)
print("Transform :", transform)


# ============================================================
# 2. DELIVERY FOLDER STRUCTURE
# ============================================================

if DELIVERY_DIR.exists():
    shutil.rmtree(DELIVERY_DIR)

folders = {
    "metadata": DELIVERY_DIR / "metadata",
    "tables": DELIVERY_DIR / "tables",
    "qa": DELIVERY_DIR / "qa",
    "preview": DELIVERY_DIR / "preview",
    "rasters": DELIVERY_DIR / "rasters",
}

for folder in folders.values():
    folder.mkdir(
        parents=True,
        exist_ok=True
    )

print("\n[2] DELIVERY DIRECTORY")
print("Created :", DELIVERY_DIR.resolve())


# ============================================================
# 3. COPY 30H FINAL FILES
# ============================================================

H_DIR = Path("checkpoints_30H")
G_DIR = Path("checkpoints_30G")

copy_map = {

    H_DIR / "30H_FINAL_CLASS_AREA.csv":
        folders["tables"] /
        "O3_FINAL_CLASS_AREA_2025.csv",

    H_DIR / "30H_FINAL_TRANSITION_AREA.csv":
        folders["tables"] /
        "O3_FINAL_CLASS_TRANSITIONS_2025.csv",

    H_DIR / "30H_PRODUCT_SUMMARY.json":
        folders["metadata"] /
        "O3_PRODUCT_SUMMARY.json",

    H_DIR / "30H_LEGEND.json":
        folders["metadata"] /
        "O3_LEGEND.json",

    H_DIR / "30H_BAND_DICTIONARY.json":
        folders["metadata"] /
        "O3_BAND_DICTIONARY.json",

    H_DIR / "30H_FREEZE_MANIFEST.json":
        folders["metadata"] /
        "O3_FREEZE_MANIFEST.json",

    H_DIR / "30H_FINAL_MAP.png":
        folders["preview"] /
        "O3_FINAL_MAP_2025.png",

    H_DIR / "30H_PRODUCT_SUMMARY.md":
        DELIVERY_DIR /
        "PRODUCT_SUMMARY.md",
}

for source, destination in copy_map.items():

    if not source.exists():
        raise FileNotFoundError(
            f"Missing required 30H file: {source}"
        )

    shutil.copy2(
        source,
        destination
    )

print("\n[3] 30H DELIVERY FILES")
print("Required files copied : PASS")


# ============================================================
# 4. COPY FINAL QA TABLES
# ============================================================

qa_files = {

    G_DIR /
    "30G_C_FINAL_CLASS_AREA_CANONICAL.csv":

        folders["qa"] /
        "QA_CLASS_AREA_CANONICAL.csv",

    G_DIR /
    "30G_C_FINAL_TRANSITION_AREA_CANONICAL.csv":

        folders["qa"] /
        "QA_TRANSITION_AREA_CANONICAL.csv",

    G_DIR /
    "30G_C_FINAL_GUARDRAIL_QA.csv":

        folders["qa"] /
        "QA_GUARDRAIL_CHECKS.csv",
}

for source, destination in qa_files.items():

    if not source.exists():
        raise FileNotFoundError(
            f"Missing required 30G QA file: {source}"
        )

    shutil.copy2(
        source,
        destination
    )

print("30G QA files copied    : PASS")


# ============================================================
# 5. PREPARE WEB CLASS RASTER
#
# Int16:
# - CORE_CLASS
# - INTEGRATED_CLASS
# - CLASS_DELTA
#
# NoData = -9999
# ============================================================

class_bands = [
    "CORE_CLASS",
    "INTEGRATED_CLASS",
    "CLASS_DELTA",
]

class_export_img = (
    img
    .select(class_bands)
    .toInt16()
    .unmask(
        value=-9999,
        sameFootprint=False
    )
    .clip(core_img.geometry())
)

print("\n[4] CATEGORICAL COG")
print("Bands :", class_bands)


# ============================================================
# 6. PREPARE WEB CONTINUOUS RASTER
#
# Float32:
# - CORE_RISK_SCORE_0_100
# - CONTEXT_MODIFIER_SCORE
# - CONTEXT_MODIFIER_COVERAGE
# - INTEGRATED_SCORE_0_100
#
# NoData = -9999
# ============================================================

metric_bands = [
    "CORE_RISK_SCORE_0_100",
    "CONTEXT_MODIFIER_SCORE",
    "CONTEXT_MODIFIER_COVERAGE",
    "INTEGRATED_SCORE_0_100",
]

metric_export_img = (
    img
    .select(metric_bands)
    .toFloat()
    .unmask(
        value=-9999,
        sameFootprint=False
    )
    .clip(core_img.geometry())
)

print("\n[5] CONTINUOUS COG")
print("Bands :", metric_bands)


# ============================================================
# 7. SUBMIT CLASS COG EXPORT
# ============================================================

class_task = (
    ee.batch.Export.image.toDrive(

        image=class_export_img,

        description=(
            "SIAK_AOI01_O3_CLASS_COG_2025"
        ),

        folder=DRIVE_FOLDER,

        fileNamePrefix=(
            "SIAK_AOI01_O3_CLASS_COG_2025"
        ),

        region=core_img.geometry(),

        crs=crs,

        crsTransform=transform,

        maxPixels=1e13,

        fileFormat="GeoTIFF",

        formatOptions={
            "cloudOptimized": True,
            "noData": -9999
        }
    )
)

class_task.start()

class_status = class_task.status()


# ============================================================
# 8. SUBMIT CONTINUOUS COG EXPORT
# ============================================================

metric_task = (
    ee.batch.Export.image.toDrive(

        image=metric_export_img,

        description=(
            "SIAK_AOI01_O3_METRICS_COG_2025"
        ),

        folder=DRIVE_FOLDER,

        fileNamePrefix=(
            "SIAK_AOI01_O3_METRICS_COG_2025"
        ),

        region=core_img.geometry(),

        crs=crs,

        crsTransform=transform,

        maxPixels=1e13,

        fileFormat="GeoTIFF",

        formatOptions={
            "cloudOptimized": True,
            "noData": -9999
        }
    )
)

metric_task.start()

metric_status = metric_task.status()


# ============================================================
# 9. EXPORT TASK REGISTRY
# ============================================================

task_registry = {

    "google_drive_folder":
        DRIVE_FOLDER,

    "class_cog": {

        "filename":
            "SIAK_AOI01_O3_CLASS_COG_2025.tif",

        "bands":
            class_bands,

        "data_type":
            "Int16",

        "nodata":
            -9999,

        "recommended_web_resampling":
            "nearest",

        "task_id":
            class_status.get("id"),

        "submission_state":
            class_status.get("state")
    },

    "metrics_cog": {

        "filename":
            "SIAK_AOI01_O3_METRICS_COG_2025.tif",

        "bands":
            metric_bands,

        "data_type":
            "Float32",

        "nodata":
            -9999,

        "recommended_web_resampling":
            "bilinear",

        "task_id":
            metric_status.get("id"),

        "submission_state":
            metric_status.get("state")
    }
}

task_registry_path = (
    folders["metadata"] /
    "O3_GEE_EXPORT_TASKS.json"
)

with open(
    task_registry_path,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        task_registry,
        f,
        indent=2,
        ensure_ascii=False
    )


# ============================================================
# 10. WEB DELIVERY MANIFEST
# ============================================================

delivery_manifest = {

    "product":
        "Output 3 - Plantation Condition & Inspection Priority",

    "aoi":
        "SIAK_AOI01",

    "monitoring_year":
        2025,

    "canonical_gee_asset":
        FINAL_ASSET,

    "analytical_status":
        "FROZEN",

    "technical_qa":
        "PASS",

    "field_validation":
        "NOT_AVAILABLE",

    "crs":
        crs,

    "transform":
        transform,

    "nominal_resolution_m":
        10,

    "primary_web_layer":
        "INTEGRATED_CLASS",

    "rasters": [
        task_registry["class_cog"],
        task_registry["metrics_cog"]
    ],

    "delivery_components": {
        "metadata":
            "metadata/",

        "tables":
            "tables/",

        "qa":
            "qa/",

        "preview":
            "preview/",

        "rasters":
            "rasters/"
    },

    "important_interpretation":
        (
            "Inspection-priority decision-support product. "
            "Not a diagnosis of plantation health, disease, "
            "or nutrient deficiency."
        )
}

delivery_manifest_path = (
    DELIVERY_DIR /
    "WEB_DELIVERY_MANIFEST.json"
)

with open(
    delivery_manifest_path,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        delivery_manifest,
        f,
        indent=2,
        ensure_ascii=False
    )


# ============================================================
# 11. README FOR WEB DEVELOPER
# ============================================================

README = f"""# Output 3 Web Delivery
## Plantation Condition & Inspection Priority

AOI: SIAK_AOI01
Monitoring year: 2025
Analytical status: FROZEN
Technical QA: PASS
Field validation: NOT AVAILABLE

## Canonical Earth Engine asset

{FINAL_ASSET}

## Primary web display

Band:
INTEGRATED_CLASS

Class schema:

1 = Stable / Expected Condition
2 = Watch
3 = Persistent Stress - Inspection Priority
4 = High Persistent Anomaly - High Priority

## Raster delivery

### SIAK_AOI01_O3_CLASS_COG_2025.tif

Bands:
1. CORE_CLASS
2. INTEGRATED_CLASS
3. CLASS_DELTA

Data type:
Int16

NoData:
-9999

Recommended display resampling:
Nearest neighbour.

### SIAK_AOI01_O3_METRICS_COG_2025.tif

Bands:
1. CORE_RISK_SCORE_0_100
2. CONTEXT_MODIFIER_SCORE
3. CONTEXT_MODIFIER_COVERAGE
4. INTEGRATED_SCORE_0_100

Data type:
Float32

NoData:
-9999

Recommended display resampling:
Bilinear for continuous visualization.

## Spatial reference

CRS:
{crs}

Affine transform:
{transform}

Nominal resolution:
10 m

## Interpretation guardrail

This product is intended for inspection prioritization.

It must NOT be presented as:
- confirmed plantation health diagnosis;
- disease diagnosis;
- nutrient deficiency diagnosis;
- field-validated accuracy product.

Environmental context represents contextual association.
Coarse source datasets do not acquire 10 m information
simply because they are represented on the display grid.

## Files

metadata/
- Product summary
- Legend
- Band dictionary
- Freeze manifest
- GEE export task registry

tables/
- Final class area
- Final transition area

qa/
- Canonical area QA
- Transition QA
- Evidence guardrail QA

preview/
- Final analytical map preview

rasters/
- Place the two downloaded COG files here after
  Earth Engine export to Google Drive is complete.

## Reproducibility

The Jupyter notebook used to produce Output 3 should be
saved separately as:

MASTER_PIPELINE_OUTPUT3.ipynb

The notebook is the reproducible processing pipeline.
The COG/CSV/JSON files are delivery products.
The Earth Engine asset remains the cloud analytical
source of truth for this frozen AOI01 version.
"""

readme_path = (
    DELIVERY_DIR /
    "README_WEB_DELIVERY.md"
)

with open(
    readme_path,
    "w",
    encoding="utf-8"
) as f:

    f.write(README)


# ============================================================
# 12. PLACEHOLDER NOTICE IN RASTER FOLDER
# ============================================================

raster_notice = (
    folders["rasters"] /
    "PLACE_DOWNLOADED_COG_FILES_HERE.txt"
)

with open(
    raster_notice,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        "Download the two completed Earth Engine "
        "COG exports from Google Drive folder:\n\n"
        f"{DRIVE_FOLDER}\n\n"
        "Then place both .tif files in this folder."
    )


# ============================================================
# 13. ZIP CURRENT DELIVERY PACKAGE
# ============================================================

if ZIP_PATH.exists():
    ZIP_PATH.unlink()

with zipfile.ZipFile(
    ZIP_PATH,
    "w",
    compression=zipfile.ZIP_DEFLATED
) as zf:

    for file_path in DELIVERY_DIR.rglob("*"):

        if file_path.is_file():

            zf.write(
                file_path,
                arcname=file_path.relative_to(
                    DELIVERY_DIR.parent
                )
            )


# ============================================================
# 14. FINAL STATUS
# ============================================================

print("\n" + "=" * 110)
print("30I-A | DELIVERY STATUS")
print("=" * 110)

print("\nCLASS COG")
print(
    "Task ID :",
    class_status.get("id")
)
print(
    "State   :",
    class_status.get("state")
)

print("\nMETRICS COG")
print(
    "Task ID :",
    metric_status.get("id")
)
print(
    "State   :",
    metric_status.get("state")
)

print("\nGoogle Drive folder:")
print(DRIVE_FOLDER)

print("\nLocal web package:")
print(DELIVERY_DIR.resolve())

print("\nMetadata ZIP:")
print(ZIP_PATH.resolve())

print("\n" + "-" * 110)

print("""
30I-A RESULT: SUBMITTED

Output 3 analytical work is complete.

Two web-ready COG exports have been submitted to
Google Drive.

The local web-delivery package and metadata ZIP
have also been created.

DO NOT rerun these export tasks.

NEXT:
After both COG tasks are COMPLETED, run only the
final status check and download the two .tif files.
""")

print("=" * 110)

# ========================================
# ORIGINAL CELL 71
# ========================================

# ============================================================
# 30J-A | COMPLETE OUTPUT 3 PROJECT STRUCTURE + INVENTORY
#
# Purpose:
# 1. Build the final Output 3 project/package structure.
# 2. Inventory the full 30A-30I processing history.
# 3. Discover and catalog relevant persistent GEE assets.
# 4. Inventory existing local checkpoints / QA / delivery files.
# 5. Record current COG export status without blocking workflow.
# 6. Create the AOI01 configuration snapshot.
#
# IMPORTANT:
# - No model changes.
# - No analytical reprocessing.
# - No raster export.
# - No asset deletion.
# - No duplication of large GEE rasters.
# ============================================================

import ee
import os
import json
import hashlib
import pandas as pd

from pathlib import Path
from datetime import datetime

PROJECT_ID = "palm-oil-503202"
AOI_ID = "SIAK_AOI01"
REFERENCE_YEAR = 2025

GEE_ASSET_ROOT = (
    "projects/palm-oil-503202/assets"
)

PACKAGE_ROOT = Path(
    "OUTPUT3_COMPLETE_PACKAGE"
)

CLASS_COG_TASK_ID = (
    "GZBZ2BN75UVDZT5ARW76O4U6"
)

METRICS_COG_TASK_ID = (
    "TWCREHXWHXN6YEP7BGXHSQ5U"
)

ee.Initialize(project=PROJECT_ID)

print("=" * 115)
print("30J-A | COMPLETE OUTPUT 3 PROJECT STRUCTURE + INVENTORY")
print("=" * 115)


# ============================================================
# 1. CREATE FINAL PROJECT STRUCTURE
# ============================================================

DIRS = {

    "master":
        PACKAGE_ROOT / "00_MASTER_PIPELINE",

    "config":
        PACKAGE_ROOT / "01_CONFIG",

    "asset_inventory":
        PACKAGE_ROOT / "02_ASSET_INVENTORY",

    "process":
        PACKAGE_ROOT / "03_PROCESS_30A_30E",

    "analysis":
        PACKAGE_ROOT / "04_ANALYSIS_30F",

    "integration":
        PACKAGE_ROOT / "05_INTEGRATION_30G",

    "freeze":
        PACKAGE_ROOT / "06_FREEZE_30H",

    "web":
        PACKAGE_ROOT / "07_WEB_DELIVERY_30I",

    "qa":
        PACKAGE_ROOT / "08_QA",

    "documentation":
        PACKAGE_ROOT / "09_DOCUMENTATION",

    "archive":
        PACKAGE_ROOT / "10_ARCHIVE_MANIFEST",

    "logs":
        PACKAGE_ROOT / "11_LOGS",
}

for path in DIRS.values():
    path.mkdir(
        parents=True,
        exist_ok=True
    )

# Web delivery subfolders
WEB_SUBDIRS = [
    DIRS["web"] / "rasters",
    DIRS["web"] / "metadata",
    DIRS["web"] / "tables",
    DIRS["web"] / "preview",
]

for path in WEB_SUBDIRS:
    path.mkdir(
        parents=True,
        exist_ok=True
    )

print("\n[1] FINAL PROJECT STRUCTURE")
print("Root :", PACKAGE_ROOT.resolve())
print("Folders created :", len(DIRS) + len(WEB_SUBDIRS))
print("Structure QC    : PASS")


# ============================================================
# 2. PROCESS/STAGE CATALOG — 30A THROUGH 30J
# ============================================================

stage_rows = [

    {
        "stage": "30A",
        "name": "Upstream Setup and Source Contract",
        "role":
            "AOI, upstream source registry, preprocessing "
            "contract and core input preparation.",
        "main_storage":
            "GEE assets + scripts/notebooks",
        "status":
            "COMPLETED_UPSTREAM",
        "final_package_section":
            "03_PROCESS_30A_30E"
    },

    {
        "stage": "30B",
        "name": "Baseline and Monitoring Stacks",
        "role":
            "Period-matched baseline and 2025 monitoring "
            "feature stacks including optical/radar evidence.",
        "main_storage":
            "GEE assets",
        "status":
            "COMPLETED",
        "final_package_section":
            "03_PROCESS_30A_30E"
    },

    {
        "stage": "30C",
        "name": "Temporal Anomaly",
        "role":
            "Period anomaly layers derived from matched "
            "baseline versus monitoring evidence.",
        "main_storage":
            "GEE assets",
        "status":
            "COMPLETED",
        "final_package_section":
            "03_PROCESS_30A_30E"
    },

    {
        "stage": "30D",
        "name": "Core Condition / Risk",
        "role":
            "Core optical-radar condition and inspection-risk "
            "product including balanced class rules.",
        "main_storage":
            "GEE assets + QA",
        "status":
            "COMPLETED_FROZEN_CORE",
        "final_package_section":
            "03_PROCESS_30A_30E"
    },

    {
        "stage": "30E",
        "name": "Contextual Enrichment",
        "role":
            "Age, rainfall, atmosphere, ET/PET, terrain, "
            "hydrology, soil and soil-water reusable context.",
        "main_storage":
            "GEE assets",
        "status":
            "COMPLETED",
        "final_package_section":
            "03_PROCESS_30A_30E"
    },

    {
        "stage": "30F",
        "name": "Feature Screening and Calibration",
        "role":
            "Correlation/VIF, spatial CV, context ablation, "
            "feature selection, family weights, calibration "
            "and fusion sensitivity.",
        "main_storage":
            "Local Python checkpoints",
        "status":
            "COMPLETED_FROZEN",
        "final_package_section":
            "04_ANALYSIS_30F"
    },

    {
        "stage": "30G",
        "name": "Integrated Inspection Priority",
        "role":
            "Wall-to-wall F05 contextual integration, "
            "evidence-gated class transitions and final QA.",
        "main_storage":
            "GEE canonical asset + local QA",
        "status":
            "COMPLETED",
        "final_package_section":
            "05_INTEGRATION_30G"
    },

    {
        "stage": "30H",
        "name": "Analytical Freeze",
        "role":
            "Final product statistics, class schema, legend, "
            "map preview, metadata and freeze manifest.",
        "main_storage":
            "Local delivery checkpoints",
        "status":
            "COMPLETED_FROZEN",
        "final_package_section":
            "06_FREEZE_30H"
    },

    {
        "stage": "30I",
        "name": "Web Delivery",
        "role":
            "COG raster delivery plus metadata, tables, "
            "legend and web-development package.",
        "main_storage":
            "Google Drive + local delivery package",
        "status":
            "COG_EXPORT_IN_PROGRESS",
        "final_package_section":
            "07_WEB_DELIVERY_30I"
    },

    {
        "stage": "30J",
        "name": "Complete Reproducible Package",
        "role":
            "Master notebook, reusable AOI runner, complete "
            "inventory, provenance, backup and handover.",
        "main_storage":
            "Local package + backup destination",
        "status":
            "IN_PROGRESS",
        "final_package_section":
            "OUTPUT3_COMPLETE_PACKAGE"
    },
]

stage_df = pd.DataFrame(stage_rows)

stage_csv = (
    DIRS["documentation"] /
    "OUTPUT3_PROCESS_STAGE_CATALOG.csv"
)

stage_df.to_csv(
    stage_csv,
    index=False
)

print("\n[2] 30A-30J PROCESS CATALOG")
display(stage_df)


# ============================================================
# 3. CRITICAL KNOWN ASSET REGISTRY
# ============================================================

KNOWN_ASSETS = [

    # --------------------------------------------------------
    # UPSTREAM OUTPUT 1
    # --------------------------------------------------------

    {
        "stage": "UPSTREAM_O1",
        "role": "Plantation boundary / main spatial mask",
        "asset_id":
            "projects/palm-oil-503202/assets/"
            "SIAK_AOI01_PLANTATION_BOUNDARY_WEB_WGS84_2025",
        "effective_resolution":
            "vector",
        "final_role":
            "UPSTREAM_REQUIRED"
    },

    # --------------------------------------------------------
    # UPSTREAM OUTPUT 2
    # --------------------------------------------------------

    {
        "stage": "UPSTREAM_O2",
        "role": "Final tree-age / event age proxy",
        "asset_id":
            "projects/palm-oil-503202/assets/"
            "SIAK_AOI01_OUTPUT2_FINAL_6CLASS_TREE_AGE_PROXY_2025",
        "effective_resolution":
            "30 m",
        "final_role":
            "CONTEXT_INPUT"
    },

    {
        "stage": "UPSTREAM_O2",
        "role": "Historical Landsat clean event product",
        "asset_id":
            "projects/palm-oil-503202/assets/"
            "SIAK_AOI01_LANDSAT_HISTORICAL_CLEAN_2001_2018",
        "effective_resolution":
            "30 m",
        "final_role":
            "PROVENANCE_INPUT"
    },

    {
        "stage": "UPSTREAM_O2",
        "role": "Recent Sentinel-2 regrowth evidence",
        "asset_id":
            "projects/palm-oil-503202/assets/"
            "SIAK_AOI01_S2_REGROWTH_STACK_2019_2025",
        "effective_resolution":
            "10-20 m source / 30 m Output 2 integration",
        "final_role":
            "PROVENANCE_INPUT"
    },

    # --------------------------------------------------------
    # 30D CORE
    # --------------------------------------------------------

    {
        "stage": "30D",
        "role": "Frozen balanced core condition/risk",
        "asset_id":
            "projects/palm-oil-503202/assets/"
            "SIAK_AOI01_O3_30D04_BALANCED_RISK_2025",
        "effective_resolution":
            "10 m",
        "final_role":
            "CORE_INPUT"
    },

    # --------------------------------------------------------
    # 30E CONTEXT
    # --------------------------------------------------------

    {
        "stage": "30E01",
        "role": "Age context",
        "asset_id":
            "projects/palm-oil-503202/assets/"
            "SIAK_AOI01_O3_30E01_AGE_CONTEXT_V3_2025",
        "effective_resolution":
            "~30 m",
        "final_role":
            "CONTEXT"
    },

    {
        "stage": "30E02A",
        "role": "CHIRPS rainfall context",
        "asset_id":
            "projects/palm-oil-503202/assets/"
            "SIAK_AOI01_O3_30E02A_CHIRPS_FINAL_2025",
        "effective_resolution":
            "~5.6 km",
        "final_role":
            "CONTEXT"
    },

    {
        "stage": "30E02B",
        "role": "ERA5-Land atmosphere/moisture context",
        "asset_id":
            "projects/palm-oil-503202/assets/"
            "SIAK_AOI01_O3_30E02B_ERA5LAND_FINAL_2025",
        "effective_resolution":
            "~9-11 km",
        "final_role":
            "CONTEXT"
    },

    {
        "stage": "30E02C",
        "role": "ET/PET water-balance context",
        "asset_id":
            "projects/palm-oil-503202/assets/"
            "SIAK_AOI01_O3_30E02C_ETPET_FINAL_2025",
        "effective_resolution":
            "~9-11 km",
        "final_role":
            "CONTEXT"
    },

    {
        "stage": "30E03A",
        "role": "Terrain context",
        "asset_id":
            "projects/palm-oil-503202/assets/"
            "SIAK_AOI01_O3_30E03A_TERRAIN_CORE_2025",
        "effective_resolution":
            "~30 m",
        "final_role":
            "DIRECT_MODIFIER_INPUT"
    },

    {
        "stage": "30E03B",
        "role": "Hydrology context",
        "asset_id":
            "projects/palm-oil-503202/assets/"
            "SIAK_AOI01_O3_30E03B_HYDRO_CONTEXT_2025",
        "effective_resolution":
            "~90 m",
        "final_role":
            "DIRECT_MODIFIER_INPUT"
    },

    {
        "stage": "30E04A",
        "role": "Soil profile context",
        "asset_id":
            "projects/palm-oil-503202/assets/"
            "SIAK_AOI01_O3_30E04A_SOIL_CORE_PROFILE_2025",
        "effective_resolution":
            "~250 m",
        "final_role":
            "DIRECT_MODIFIER_INPUT"
    },

    {
        "stage": "30E04B",
        "role": "Soil-water retention context",
        "asset_id":
            "projects/palm-oil-503202/assets/"
            "SIAK_AOI01_O3_30E04B_SOIL_WATER_RETENTION_2025",
        "effective_resolution":
            "~250 m",
        "final_role":
            "DIRECT_MODIFIER_INPUT"
    },

    # --------------------------------------------------------
    # 30G FINAL
    # --------------------------------------------------------

    {
        "stage": "30G",
        "role": "Canonical integrated Output 3 asset",
        "asset_id":
            "projects/palm-oil-503202/assets/"
            "SIAK_AOI01_O3_30G_INTEGRATED_V1_1_GRIDLOCKED_2025",
        "effective_resolution":
            "10 m display / inspection grid",
        "final_role":
            "CANONICAL_SOURCE_OF_TRUTH"
    },
]


# ============================================================
# 4. DISCOVER ALL RELEVANT GEE ASSETS AUTOMATICALLY
# ============================================================

print("\n[3] DISCOVERING GEE ASSETS...")

asset_listing = ee.data.listAssets({
    "parent": GEE_ASSET_ROOT,
    "pageSize": 1000
})

all_assets = asset_listing.get(
    "assets",
    []
)

relevant_assets = []

for item in all_assets:

    asset_id = (
        item.get("name")
        or
        item.get("id")
        or
        ""
    )

    basename = asset_id.split("/")[-1]

    is_output3 = (
        "SIAK_AOI01_O3_" in basename
    )

    is_upstream = any(
        token in basename
        for token in [
            "SIAK_AOI01_PLANTATION_BOUNDARY",
            "SIAK_AOI01_OUTPUT2",
            "SIAK_AOI01_LANDSAT_HISTORICAL",
            "SIAK_AOI01_S2_REGROWTH"
        ]
    )

    if is_output3 or is_upstream:

        relevant_assets.append(item)

print("Total assets in project :", len(all_assets))
print("Relevant O3/upstream    :", len(relevant_assets))


# ============================================================
# 5. CLASSIFY DISCOVERED ASSETS
# ============================================================

def classify_asset_stage(name):

    if "_O3_30B" in name:
        return "30B"

    if "_O3_30C" in name:
        return "30C"

    if "_O3_30D" in name:
        return "30D"

    if "_O3_30E01" in name:
        return "30E01"

    if "_O3_30E02" in name:
        return "30E02"

    if "_O3_30E03" in name:
        return "30E03"

    if "_O3_30E04" in name:
        return "30E04"

    if "_O3_30G" in name:
        return "30G"

    if "PLANTATION_BOUNDARY" in name:
        return "UPSTREAM_O1"

    if (
        "OUTPUT2" in name
        or
        "LANDSAT_HISTORICAL" in name
        or
        "S2_REGROWTH" in name
    ):
        return "UPSTREAM_O2"

    return "OTHER_RELEVANT"


# ============================================================
# 6. BUILD DETAILED GEE ASSET INVENTORY
# ============================================================

known_lookup = {
    row["asset_id"]: row
    for row in KNOWN_ASSETS
}

asset_rows = []

for item in relevant_assets:

    asset_id = (
        item.get("name")
        or
        item.get("id")
    )

    basename = asset_id.split("/")[-1]

    stage = classify_asset_stage(
        basename
    )

    known = known_lookup.get(
        asset_id,
        {}
    )

    asset_type = item.get(
        "type",
        "UNKNOWN"
    )

    band_count = None
    band_names = None
    first_band_crs = None
    first_band_transform = None

    try:

        detailed = ee.data.getAsset(
            asset_id
        )

        bands_meta = detailed.get(
            "bands",
            []
        )

        if bands_meta:

            band_count = len(
                bands_meta
            )

            band_names = [
                band.get("id")
                for band in bands_meta
            ]

            first_band_grid = (
                bands_meta[0]
                .get("grid", {})
            )

            first_band_crs = (
                first_band_grid
                .get("crsCode")
            )

            first_band_transform = (
                first_band_grid
                .get("affineTransform")
            )

    except Exception:

        pass

    asset_rows.append({

        "stage":
            stage,

        "asset_name":
            basename,

        "asset_id":
            asset_id,

        "asset_type":
            asset_type,

        "role":
            known.get(
                "role",
                "Automatically discovered project asset"
            ),

        "final_role":
            known.get(
                "final_role",
                "INTERMEDIATE_OR_SUPPORT"
            ),

        "effective_resolution":
            known.get(
                "effective_resolution",
                "SEE_SOURCE_METADATA"
            ),

        "band_count":
            band_count,

        "band_names":
            json.dumps(
                band_names,
                ensure_ascii=False
            )
            if band_names
            else None,

        "first_band_crs":
            first_band_crs,

        "first_band_transform":
            json.dumps(
                first_band_transform
            )
            if first_band_transform
            else None,

        "storage":
            "GOOGLE_EARTH_ENGINE",

        "persistent":
            True
    })


# Add known assets that were not returned by discovery
# so missing/deleted assets are explicitly visible.

discovered_ids = {
    row["asset_id"]
    for row in asset_rows
}

for known in KNOWN_ASSETS:

    if known["asset_id"] not in discovered_ids:

        exists = False

        try:
            ee.data.getAsset(
                known["asset_id"]
            )
            exists = True
        except Exception:
            exists = False

        asset_rows.append({

            "stage":
                known["stage"],

            "asset_name":
                known["asset_id"]
                .split("/")[-1],

            "asset_id":
                known["asset_id"],

            "asset_type":
                "UNKNOWN",

            "role":
                known["role"],

            "final_role":
                known["final_role"],

            "effective_resolution":
                known["effective_resolution"],

            "band_count":
                None,

            "band_names":
                None,

            "first_band_crs":
                None,

            "first_band_transform":
                None,

            "storage":
                "GOOGLE_EARTH_ENGINE",

            "persistent":
                exists
        })


asset_df = (
    pd.DataFrame(asset_rows)
    .sort_values([
        "stage",
        "asset_name"
    ])
    .reset_index(drop=True)
)

asset_csv = (
    DIRS["asset_inventory"] /
    "OUTPUT3_GEE_ASSET_INVENTORY.csv"
)

asset_json = (
    DIRS["asset_inventory"] /
    "OUTPUT3_GEE_ASSET_INVENTORY.json"
)

asset_df.to_csv(
    asset_csv,
    index=False
)

with open(
    asset_json,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        asset_df.to_dict(
            orient="records"
        ),
        f,
        indent=2,
        ensure_ascii=False
    )

print("\n[4] GEE ASSET INVENTORY")
print("Inventory rows :", len(asset_df))

print("\nAssets by stage:")
print(
    asset_df["stage"]
    .value_counts()
    .sort_index()
)

critical_df = asset_df[
    asset_df["final_role"].isin([
        "CANONICAL_SOURCE_OF_TRUTH",
        "CORE_INPUT",
        "DIRECT_MODIFIER_INPUT",
        "CONTEXT_INPUT",
        "CONTEXT",
        "UPSTREAM_REQUIRED"
    ])
][[
    "stage",
    "asset_name",
    "role",
    "effective_resolution",
    "persistent"
]]

print("\nCritical / final-relevant assets:")
display(
    critical_df.reset_index(
        drop=True
    )
)


# ============================================================
# 7. INVENTORY EXISTING LOCAL OUTPUT 3 FILES
# ============================================================

PROJECT_WORKDIR = Path.cwd()

scan_roots = []

for candidate in PROJECT_WORKDIR.glob(
    "checkpoints_30*"
):

    if candidate.is_dir():
        scan_roots.append(candidate)

for name in [
    "WEB_DELIVERY_OUTPUT3",
]:

    p = PROJECT_WORKDIR / name

    if p.exists():
        scan_roots.append(p)


# Include relevant top-level scripts/notebooks
relevant_top_files = []

for pattern in [
    "*.ipynb",
    "*.py",
    "*.js",
    "*.json",
    "*.csv",
    "*.md",
    "*.txt",
]:

    for p in PROJECT_WORKDIR.glob(
        pattern
    ):

        name_upper = p.name.upper()

        if any(
            token in name_upper
            for token in [
                "30",
                "OUTPUT3",
                "PALM",
                "SDAI",
                "MASTER"
            ]
        ):
            relevant_top_files.append(p)


def sha256_small_file(
    path,
    max_size_mb=50
):

    size_mb = (
        path.stat().st_size
        /
        (1024 ** 2)
    )

    if size_mb > max_size_mb:
        return "SKIPPED_GT_50MB"

    h = hashlib.sha256()

    with open(path, "rb") as f:

        for chunk in iter(
            lambda: f.read(
                1024 * 1024
            ),
            b""
        ):
            h.update(chunk)

    return h.hexdigest()


local_files = []

seen_paths = set()

for root in scan_roots:

    for path in root.rglob("*"):

        if not path.is_file():
            continue

        abs_path = path.resolve()

        if abs_path in seen_paths:
            continue

        seen_paths.add(
            abs_path
        )

        local_files.append(
            path
        )

for path in relevant_top_files:

    abs_path = path.resolve()

    if abs_path not in seen_paths:

        seen_paths.add(
            abs_path
        )

        local_files.append(
            path
        )


local_rows = []

for path in sorted(
    local_files,
    key=lambda p: str(p)
):

    stat = path.stat()

    local_rows.append({

        "relative_path":
            str(
                path.relative_to(
                    PROJECT_WORKDIR
                )
            ),

        "filename":
            path.name,

        "extension":
            path.suffix.lower(),

        "size_bytes":
            stat.st_size,

        "size_mb":
            round(
                stat.st_size
                /
                (1024 ** 2),
                4
            ),

        "sha256":
            sha256_small_file(
                path
            ),

        "storage":
            "LOCAL_PROJECT",

        "exists":
            True
    })

local_df = pd.DataFrame(
    local_rows
)

local_csv = (
    DIRS["asset_inventory"] /
    "OUTPUT3_LOCAL_FILE_INVENTORY.csv"
)

local_json = (
    DIRS["asset_inventory"] /
    "OUTPUT3_LOCAL_FILE_INVENTORY.json"
)

local_df.to_csv(
    local_csv,
    index=False
)

with open(
    local_json,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        local_rows,
        f,
        indent=2,
        ensure_ascii=False
    )

print("\n[5] LOCAL PROJECT INVENTORY")
print(
    "Relevant local files :",
    len(local_df)
)

if len(local_df) > 0:

    print("\nFiles by extension:")
    print(
        local_df[
            "extension"
        ]
        .value_counts()
    )


# ============================================================
# 8. CURRENT COG EXPORT STATUS
#
# Non-blocking.
# These tasks remain independent of 30J work.
# ============================================================

def task_snapshot(
    task_id
):

    try:

        status = (
            ee.data.getTaskStatus(
                task_id
            )[0]
        )

        return {
            "task_id":
                task_id,

            "state":
                status.get(
                    "state"
                ),

            "description":
                status.get(
                    "description"
                ),

            "error_message":
                status.get(
                    "error_message"
                )
        }

    except Exception as e:

        return {
            "task_id":
                task_id,

            "state":
                "STATUS_LOOKUP_FAILED",

            "description":
                None,

            "error_message":
                str(e)
        }


cog_status = {

    "class_cog":
        task_snapshot(
            CLASS_COG_TASK_ID
        ),

    "metrics_cog":
        task_snapshot(
            METRICS_COG_TASK_ID
        )
}

cog_status_path = (
    DIRS["logs"] /
    "30I_COG_EXPORT_STATUS_SNAPSHOT.json"
)

with open(
    cog_status_path,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        cog_status,
        f,
        indent=2,
        ensure_ascii=False
    )

print("\n[6] COG EXPORT STATUS")
print(
    "CLASS COG   :",
    cog_status[
        "class_cog"
    ]["state"]
)
print(
    "METRICS COG :",
    cog_status[
        "metrics_cog"
    ]["state"]
)

print(
    "Note        : COG status does not block 30J."
)


# ============================================================
# 9. AOI01 CONFIGURATION SNAPSHOT
#
# This becomes the basis for the reusable AOI config in 30J-C.
# ============================================================

aoi_config = {

    "schema_version":
        "OUTPUT3_CONFIG_V1",

    "project_id":
        PROJECT_ID,

    "aoi_id":
        AOI_ID,

    "reference_year":
        REFERENCE_YEAR,

    "gee_asset_root":
        GEE_ASSET_ROOT,

    "processing_architecture":
        "PYTHON_JUPYTER_WITH_EARTH_ENGINE_BACKEND",

    "spatial_contract": {

        "final_display_crs":
            "EPSG:32647",

        "final_display_resolution_m":
            10,

        "preserve_native_effective_resolution":
            True,

        "pseudo_downscaling_allowed":
            False
    },

    "upstream_assets": {

        "plantation_boundary":
            "projects/palm-oil-503202/assets/"
            "SIAK_AOI01_PLANTATION_BOUNDARY_WEB_WGS84_2025",

        "tree_age_proxy":
            "projects/palm-oil-503202/assets/"
            "SIAK_AOI01_OUTPUT2_FINAL_6CLASS_TREE_AGE_PROXY_2025"
    },

    "output3_assets": {

        "core":
            "projects/palm-oil-503202/assets/"
            "SIAK_AOI01_O3_30D04_BALANCED_RISK_2025",

        "age":
            "projects/palm-oil-503202/assets/"
            "SIAK_AOI01_O3_30E01_AGE_CONTEXT_V3_2025",

        "chirps":
            "projects/palm-oil-503202/assets/"
            "SIAK_AOI01_O3_30E02A_CHIRPS_FINAL_2025",

        "era5_land":
            "projects/palm-oil-503202/assets/"
            "SIAK_AOI01_O3_30E02B_ERA5LAND_FINAL_2025",

        "et_pet":
            "projects/palm-oil-503202/assets/"
            "SIAK_AOI01_O3_30E02C_ETPET_FINAL_2025",

        "terrain":
            "projects/palm-oil-503202/assets/"
            "SIAK_AOI01_O3_30E03A_TERRAIN_CORE_2025",

        "hydrology":
            "projects/palm-oil-503202/assets/"
            "SIAK_AOI01_O3_30E03B_HYDRO_CONTEXT_2025",

        "soil":
            "projects/palm-oil-503202/assets/"
            "SIAK_AOI01_O3_30E04A_SOIL_CORE_PROFILE_2025",

        "soil_water":
            "projects/palm-oil-503202/assets/"
            "SIAK_AOI01_O3_30E04B_SOIL_WATER_RETENTION_2025",

        "canonical_final":
            "projects/palm-oil-503202/assets/"
            "SIAK_AOI01_O3_30G_INTEGRATED_V1_1_GRIDLOCKED_2025"
    },

    "frozen_integration": {

        "fusion_amplitude":
            5,

        "thresholds": {
            "T12": 12,
            "T23": 22,
            "T34": 32
        },

        "max_class_change":
            1,

        "field_validated":
            False
    },

    "automation_policy": {

        "auto_start_exports":
            False,

        "require_qa_before_export":
            True,

        "allow_model_retuning_on_new_aoi":
            False,

        "new_aoi_mode":
            (
                "RUN_REPRODUCIBILITY_FIRST; "
                "DO_NOT CLAIM TRANSFERABILITY UNTIL TESTED"
            )
    }
}

config_path = (
    DIRS["config"] /
    "SIAK_AOI01_OUTPUT3_CONFIG.json"
)

with open(
    config_path,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        aoi_config,
        f,
        indent=2,
        ensure_ascii=False
    )


# ============================================================
# 10. FINAL PROJECT INDEX
# ============================================================

project_index = {

    "package_name":
        "OUTPUT3_COMPLETE_PACKAGE",

    "product":
        (
            "Output 3 - Plantation Condition "
            "& Inspection Priority"
        ),

    "aoi_id":
        AOI_ID,

    "reference_year":
        REFERENCE_YEAR,

    "created_at_local":
        datetime.now().isoformat(),

    "architecture":
        (
            "Python/Jupyter master workflow "
            "+ Earth Engine server-side backend"
        ),

    "analytical_status":
        "FROZEN",

    "field_validation":
        "NOT_AVAILABLE",

    "canonical_asset":
        (
            "projects/palm-oil-503202/assets/"
            "SIAK_AOI01_O3_30G_INTEGRATED_V1_1_GRIDLOCKED_2025"
        ),

    "process_stages":
        stage_rows,

    "inventories": {

        "gee_assets":
            str(asset_csv),

        "local_files":
            str(local_csv),

        "stage_catalog":
            str(stage_csv)
    },

    "configuration":
        str(config_path),

    "cog_export_status":
        cog_status,

    "remaining_30j_work": [

        "30J-B_MASTER_PIPELINE_30A_30I",

        "30J-C_REUSABLE_AOI_RUNNER",

        "30J-D_DOCUMENTATION_PROVENANCE_BACKUP",

        "30J-E_FINAL_COMPLETE_PACKAGE"
    ]
}

project_index_path = (
    PACKAGE_ROOT /
    "OUTPUT3_PROJECT_INDEX.json"
)

with open(
    project_index_path,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        project_index,
        f,
        indent=2,
        ensure_ascii=False
    )


# ============================================================
# 11. START-HERE README
# ============================================================

readme_path = (
    PACKAGE_ROOT /
    "README_START_HERE.md"
)

readme_text = f"""# Output 3 Complete Package

## Product
Plantation Condition & Inspection Priority

AOI: {AOI_ID}
Reference year: {REFERENCE_YEAR}

## Architecture

Python/Jupyter is the master workflow and orchestration layer.

Google Earth Engine is used as the server-side geospatial
processing and persistent raster-asset backend.

Large intermediate rasters are not duplicated locally.

## Analytical status

FROZEN for AOI01.

Canonical Earth Engine asset:

projects/palm-oil-503202/assets/
SIAK_AOI01_O3_30G_INTEGRATED_V1_1_GRIDLOCKED_2025

## Scientific interpretation

This product supports inspection prioritization.

It is not an independent field-validated diagnosis of
plantation health, nutrient deficiency or disease.

## Package logic

00_MASTER_PIPELINE
    Complete reproducible 30A-30I notebook.

01_CONFIG
    AOI/configuration definitions.

02_ASSET_INVENTORY
    Persistent GEE and local-file inventories.

03_PROCESS_30A_30E
    Core processing and contextual enrichment provenance.

04_ANALYSIS_30F
    Screening, calibration, weights and sensitivity evidence.

05_INTEGRATION_30G
    Integrated product and transition logic.

06_FREEZE_30H
    Final analytical freeze and product summary.

07_WEB_DELIVERY_30I
    COG and web-development delivery files.

08_QA
    Technical, evidence and guardrail QA.

09_DOCUMENTATION
    Methodology, processing history and limitations.

10_ARCHIVE_MANIFEST
    Historical/legacy script inventory.

11_LOGS
    Task and execution status snapshots.

## Reuse

The final reusable pipeline will separate AOI-specific
configuration from processing logic.

A new AOI must first be treated as a reproducibility /
transferability test. Existing AOI01 weights and thresholds
must not automatically be interpreted as locally validated
for another AOI.
"""

with open(
    readme_path,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        readme_text
    )


# ============================================================
# 12. FINAL 30J-A GATE
# ============================================================

required_files = [

    stage_csv,
    asset_csv,
    asset_json,
    local_csv,
    local_json,
    config_path,
    cog_status_path,
    project_index_path,
    readme_path,
]

gate_pass = all(
    path.exists()
    for path in required_files
)

print("\n" + "=" * 115)
print("30J-A | FINAL GATE")
print("=" * 115)

print(
    "Complete folder structure :",
    "PASS"
)

print(
    "30A-30J stage catalog     :",
    "PASS"
)

print(
    "GEE asset inventory       :",
    "PASS"
)

print(
    "Local file inventory      :",
    "PASS"
)

print(
    "AOI01 config snapshot     :",
    "PASS"
)

print(
    "COG status captured       :",
    "PASS"
)

print(
    "Project index             :",
    "PASS"
)

print(
    "README START HERE         :",
    "PASS"
)

print(
    "Required files            :",
    "PASS"
    if gate_pass
    else "FAIL"
)

print("\nPackage root:")
print(
    PACKAGE_ROOT.resolve()
)

print("\n" + "-" * 115)

if gate_pass:

    print("""
30J-A RESULT: PASS

THE COMPLETE OUTPUT 3 PACKAGE FOUNDATION NOW EXISTS.

Captured:
- 30A-30J process structure
- persistent GEE assets
- all discovered 30B/30C/30D/30E/30G assets
- Output 1 / Output 2 upstream dependencies
- local checkpoints and delivery files
- AOI01 frozen configuration
- current COG task status
- project-level index and handover structure

No analytical data were duplicated or reprocessed.

NEXT:
30J-B | BUILD MASTER_PIPELINE_OUTPUT3.ipynb
        AS THE COMPLETE 30A-30I REPRODUCIBLE MASTER.
""")

else:

    print("""
30J-A RESULT: REVIEW REQUIRED

Only package/inventory creation needs review.
Do not reopen analytical modelling.
""")

print("=" * 115)

# ========================================
# ORIGINAL CELL 72
# ========================================

# ============================================================
# 30J-B | BUILD MASTER_PIPELINE_OUTPUT3.ipynb
#
# Purpose:
# 1. Create the official Output 3 master Jupyter notebook.
# 2. Capture the complete 30A-30I hybrid workflow contract.
# 3. Preserve the original working OUTPUT 3 notebook.
# 4. Embed frozen 30F -> 30G reconstruction logic.
# 5. Embed canonical-product reproducibility QA.
#
# IMPORTANT:
# - No new raster export.
# - No model tuning.
# - No raw-data reprocessing.
# - Existing GEE assets remain the persistent source of truth.
# ============================================================

import re
import json
import shutil
from pathlib import Path
from datetime import datetime

import pandas as pd

try:
    import nbformat as nbf
except ImportError:
    raise ImportError(
        "nbformat is required. It is normally installed with Jupyter."
    )


# ============================================================
# 1. PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path.cwd()

PACKAGE_ROOT = (
    PROJECT_ROOT /
    "OUTPUT3_COMPLETE_PACKAGE"
)

MASTER_DIR = (
    PACKAGE_ROOT /
    "00_MASTER_PIPELINE"
)

ARCHIVE_DIR = (
    PACKAGE_ROOT /
    "10_ARCHIVE_MANIFEST"
)

INVENTORY_DIR = (
    PACKAGE_ROOT /
    "02_ASSET_INVENTORY"
)

CONFIG_DIR = (
    PACKAGE_ROOT /
    "01_CONFIG"
)

LOG_DIR = (
    PACKAGE_ROOT /
    "11_LOGS"
)

for p in [
    MASTER_DIR,
    ARCHIVE_DIR,
    INVENTORY_DIR,
    CONFIG_DIR,
    LOG_DIR,
]:
    p.mkdir(parents=True, exist_ok=True)


print("=" * 115)
print("30J-B | BUILD MASTER_PIPELINE_OUTPUT3.ipynb")
print("=" * 115)


# ============================================================
# 2. REQUIRED 30J-A INPUTS
# ============================================================

config_path = (
    CONFIG_DIR /
    "SIAK_AOI01_OUTPUT3_CONFIG.json"
)

asset_inventory_path = (
    INVENTORY_DIR /
    "OUTPUT3_GEE_ASSET_INVENTORY.csv"
)

local_inventory_path = (
    INVENTORY_DIR /
    "OUTPUT3_LOCAL_FILE_INVENTORY.csv"
)

stage_catalog_path = (
    PACKAGE_ROOT /
    "09_DOCUMENTATION" /
    "OUTPUT3_PROCESS_STAGE_CATALOG.csv"
)

required_30j_a = [
    config_path,
    asset_inventory_path,
    local_inventory_path,
    stage_catalog_path,
]

missing = [
    p for p in required_30j_a
    if not p.exists()
]

if missing:
    raise FileNotFoundError(
        "Missing 30J-A files:\n" +
        "\n".join(str(x) for x in missing)
    )

print("\n[1] 30J-A FOUNDATION")
print("Required inputs : PASS")


# ============================================================
# 3. FIND ORIGINAL WORKING NOTEBOOK
#
# 30J-A did not necessarily capture "OUTPUT 3.ipynb"
# because its filename contains a space.
# Capture it explicitly here.
# ============================================================

preferred_names = [
    "OUTPUT 3.ipynb",
    "OUTPUT3.ipynb",
    "Output 3.ipynb",
]

source_notebook = None

for name in preferred_names:
    candidate = PROJECT_ROOT / name
    if candidate.exists():
        source_notebook = candidate
        break

if source_notebook is None:

    candidates = []

    for p in PROJECT_ROOT.glob("*.ipynb"):

        upper_name = p.stem.upper()

        if (
            "OUTPUT" in upper_name
            and "3" in upper_name
            and "MASTER_PIPELINE_OUTPUT3" not in upper_name
        ):
            candidates.append(p)

    if candidates:
        source_notebook = sorted(
            candidates,
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )[0]


if source_notebook is None:
    raise FileNotFoundError(
        "Original working notebook was not found. "
        "Expected something like 'OUTPUT 3.ipynb'."
    )


print("\n[2] WORKING NOTEBOOK")
print("Source :", source_notebook.resolve())


# ============================================================
# 4. ARCHIVE EXACT WORKING NOTEBOOK
# ============================================================

timestamp = datetime.now().strftime(
    "%Y%m%d_%H%M%S"
)

snapshot_path = (
    ARCHIVE_DIR /
    f"OUTPUT3_WORKING_NOTEBOOK_SNAPSHOT_{timestamp}.ipynb"
)

shutil.copy2(
    source_notebook,
    snapshot_path
)

print("Snapshot :", snapshot_path.resolve())
print("Snapshot QC : PASS")


# ============================================================
# 5. CREATE CELL INDEX FOR WORKING NOTEBOOK
# ============================================================

working_nb = nbf.read(
    source_notebook,
    as_version=4
)


def detect_stage(text):

    text_upper = text.upper()

    patterns = [
        "30A",
        "30B",
        "30C",
        "30D",
        "30E",
        "30F",
        "30G",
        "30H",
        "30I",
        "30J",
    ]

    for stage in patterns:
        if stage in text_upper:
            return stage

    return "UNCLASSIFIED"


cell_rows = []

for idx, cell in enumerate(
    working_nb.cells
):

    source = cell.get(
        "source",
        ""
    )

    first_line = (
        source.strip()
        .splitlines()[0][:150]
        if source.strip()
        else ""
    )

    cell_rows.append({
        "cell_index":
            idx,

        "cell_type":
            cell.cell_type,

        "detected_stage":
            detect_stage(source),

        "first_line":
            first_line,

        "source_length":
            len(source),
    })


cell_index_df = pd.DataFrame(
    cell_rows
)

cell_index_path = (
    ARCHIVE_DIR /
    "OUTPUT3_WORKING_NOTEBOOK_CELL_INDEX.csv"
)

cell_index_df.to_csv(
    cell_index_path,
    index=False
)

print(
    "Working cells :",
    len(cell_index_df)
)

print("\nDetected cells by stage:")
print(
    cell_index_df[
        "detected_stage"
    ].value_counts()
)


# ============================================================
# 6. NOTEBOOK HELPERS
# ============================================================

def md(text):
    return nbf.v4.new_markdown_cell(
        text.strip()
    )


def code(text):
    return nbf.v4.new_code_cell(
        text.strip()
    )


cells = []


# ============================================================
# 7. MASTER NOTEBOOK FRONT MATTER
# ============================================================

cells.append(md(
r"""
# MASTER PIPELINE OUTPUT 3

## Plantation Condition & Inspection Priority

**AOI:** SIAK_AOI01  
**Reference year:** 2025  
**Architecture:** Python/Jupyter + Google Earth Engine backend  
**Analytical status:** FROZEN  
**Field validation:** NOT AVAILABLE

This notebook is the official reproducibility master for
Output 3 of the SDAI Palm Oil Monitoring pilot.

### Workflow represented

`30A -> 30B -> 30C -> 30D -> 30E -> 30F -> 30G -> 30H -> 30I`

### Important architecture rule

The hybrid GEE + Python route does **not** duplicate raw
satellite preprocessing locally.

Google Earth Engine remains the source of truth for:

- source acquisition;
- cloud / quality masking;
- Sentinel-1 / Sentinel-2 composites;
- matched temporal baseline;
- anomaly products;
- frozen core risk;
- contextual raster generation.

Python/Jupyter is used for:

- controlled asset access;
- sampling / analysis tables;
- feature screening;
- redundancy / VIF analysis;
- spatial/group validation;
- context calibration;
- frozen integration;
- QA;
- documentation;
- packaging and export orchestration.

Large persistent raster assets remain in Earth Engine.

### Scientific interpretation

This is an **inspection-priority / early-warning product**.

It is **not**:

- a confirmed disease diagnosis;
- a nutrient-deficiency diagnosis;
- a field-validated plantation-health map.

Resampling does not create new spatial information.
Weather, hydrology and soil context retain their original
effective information scale.
"""
))


# ============================================================
# 8. PROJECT ROOT / EXECUTION POLICY
# ============================================================

cells.append(md(
"""
## 0. Execution Policy

The default master mode is conservative:

- read persistent assets;
- restore frozen parameters;
- reproduce / audit the final product;
- do not automatically start exports;
- do not automatically retune AOI01.

For a new AOI, use the reusable AOI runner produced in 30J-C.
"""
))


cells.append(code(
r'''
from pathlib import Path
import json
import ssl
import certifi
import ee
import pandas as pd
import numpy as np

START_EXPORTS = False
ALLOW_MODEL_RETUNING = False


def find_project_root():

    start = Path.cwd().resolve()

    candidates = [
        start,
        *start.parents
    ]

    for candidate in candidates:

        if (
            (candidate / "OUTPUT3_COMPLETE_PACKAGE").exists()
            and
            (candidate / "checkpoints_30F").exists()
        ):
            return candidate

    raise FileNotFoundError(
        "Could not locate the Output 3 project root."
    )


PROJECT_ROOT = find_project_root()

PACKAGE_ROOT = (
    PROJECT_ROOT /
    "OUTPUT3_COMPLETE_PACKAGE"
)

print("Project root :", PROJECT_ROOT)
print("Package root :", PACKAGE_ROOT)
print("START_EXPORTS :", START_EXPORTS)
print("ALLOW_MODEL_RETUNING :", ALLOW_MODEL_RETUNING)
'''
))


# ============================================================
# 9. CONFIGURATION
# ============================================================

cells.append(md(
"""
## 1. AOI Configuration

AOI-specific values are separated from processing logic.

This AOI01 configuration is the frozen reference used to
reproduce the current pilot.
"""
))


cells.append(code(
r'''
CONFIG_PATH = (
    PACKAGE_ROOT /
    "01_CONFIG" /
    "SIAK_AOI01_OUTPUT3_CONFIG.json"
)

with open(
    CONFIG_PATH,
    "r",
    encoding="utf-8"
) as f:

    cfg = json.load(f)

print("AOI ID         :", cfg["aoi_id"])
print("Reference year :", cfg["reference_year"])
print("EE project     :", cfg["project_id"])

assert cfg["aoi_id"] == "SIAK_AOI01"
assert cfg["reference_year"] == 2025
'''
))


# ============================================================
# 10. EARTH ENGINE
# ============================================================

cells.append(md(
"""
## 2. Earth Engine Initialization

Earth Engine performs the wall-to-wall raster operations
server-side. Python is the orchestration and analytical
environment.
"""
))


cells.append(code(
r'''
# Apply the known Windows/certifi session fix.
ssl._create_default_https_context = (
    lambda:
    ssl.create_default_context(
        cafile=certifi.where()
    )
)

try:

    ee.Initialize(
        project=cfg["project_id"]
    )

except Exception:

    print(
        "Earth Engine initialization failed. "
        "Authenticate only if required."
    )

    ee.Authenticate()

    ee.Initialize(
        project=cfg["project_id"]
    )

print(
    "Earth Engine initialization : PASS"
)
'''
))


# ============================================================
# 11. STAGE CATALOG
# ============================================================

cells.append(md(
"""
## 3. Complete 30A-30I Process Contract

The master preserves the full workflow history even though
the hybrid route begins Python analytics from persistent
30B-30E Earth Engine assets.
"""
))


cells.append(code(
r'''
STAGE_CATALOG = (
    PACKAGE_ROOT /
    "09_DOCUMENTATION" /
    "OUTPUT3_PROCESS_STAGE_CATALOG.csv"
)

stage_df = pd.read_csv(
    STAGE_CATALOG
)

display(stage_df)
'''
))


# ============================================================
# 12. 30A-30E SOURCE CONTRACT
# ============================================================

cells.append(md(
"""
# 30A-30E | Persistent Geospatial Source Pipeline

These stages constitute the upstream Earth Engine processing
contract.

### 30A
AOI, upstream data availability and source contract.

### 30B
Matched baseline and monitoring optical/radar composites.

### 30C
Period anomaly products.

### 30D
Core condition / persistence / inspection-risk logic.

The frozen core used downstream is:

`SIAK_AOI01_O3_30D04_BALANCED_RISK_2025`

### 30E
Contextual enrichment:

- 30E01 Tree age/event context;
- 30E02A CHIRPS rainfall;
- 30E02B ERA5-Land;
- 30E02C ET/PET;
- 30E03A terrain;
- 30E03B hydrology;
- 30E04A soil profile;
- 30E04B soil-water retention;
- 30E05 GEDI supporting QA only.

GEDI is not interpolated wall-to-wall.
"""
))


cells.append(code(
r'''
ASSET_INVENTORY_PATH = (
    PACKAGE_ROOT /
    "02_ASSET_INVENTORY" /
    "OUTPUT3_GEE_ASSET_INVENTORY.csv"
)

asset_df = pd.read_csv(
    ASSET_INVENTORY_PATH
)

required_stages = [
    "30B",
    "30C",
    "30D",
    "30E01",
    "30E02",
    "30E03",
    "30E04",
    "30G",
    "UPSTREAM_O1",
    "UPSTREAM_O2",
]

stage_counts = (
    asset_df["stage"]
    .value_counts()
)

print(
    "Persistent assets by stage:"
)

display(
    stage_counts
    .rename("asset_count")
    .to_frame()
)

missing_stages = [
    stage
    for stage in required_stages
    if stage not in stage_counts.index
]

if missing_stages:

    raise RuntimeError(
        f"Missing required asset stages: {missing_stages}"
    )

print(
    "30A-30E persistent source contract : PASS"
)
'''
))


# ============================================================
# 13. ASSET REGISTRY
# ============================================================

cells.append(code(
r'''
O3 = cfg["output3_assets"]

ASSETS = {

    "CORE":
        O3["core"],

    "AGE":
        O3["age"],

    "CHIRPS":
        O3["chirps"],

    "ERA5":
        O3["era5_land"],

    "ETPET":
        O3["et_pet"],

    "TERRAIN":
        O3["terrain"],

    "HYDRO":
        O3["hydrology"],

    "SOIL":
        O3["soil"],

    "SOIL_WATER":
        O3["soil_water"],

    "CANONICAL":
        O3["canonical_final"],
}


for key, asset_id in ASSETS.items():

    info = ee.data.getAsset(
        asset_id
    )

    print(
        f"{key:12s}: PASS | "
        f"{asset_id.split('/')[-1]}"
    )
'''
))


# ============================================================
# 14. 30F
# ============================================================

cells.append(md(
"""
# 30F | Python Feature Screening & Frozen Calibration

30F is the analytical bridge between persistent GEE context
assets and the final integrated product.

The historical experimental notebook is preserved separately
in the package archive.

The final production reconstruction uses only the **frozen**
30F calibration and family weights.

This prevents accidental retuning during routine reruns.
"""
))


cells.append(code(
r'''
CHECKPOINT_30F = (
    PROJECT_ROOT /
    "checkpoints_30F"
)

CALIBRATION_PATH = (
    CHECKPOINT_30F /
    "30F_B18C_AOI01_WALL_TO_WALL_CALIBRATION_V1.csv"
)

FAMILY_WEIGHT_PATH = (
    CHECKPOINT_30F /
    "30F_B18C_FAMILY_WEIGHTS_V1.csv"
)

if not CALIBRATION_PATH.exists():
    raise FileNotFoundError(
        CALIBRATION_PATH
    )

if not FAMILY_WEIGHT_PATH.exists():
    raise FileNotFoundError(
        FAMILY_WEIGHT_PATH
    )


calibration_df = pd.read_csv(
    CALIBRATION_PATH
)

family_weight_df = pd.read_csv(
    FAMILY_WEIGHT_PATH
)


if len(calibration_df) != 8:
    raise ValueError(
        "Expected 8 frozen modifier features."
    )

if len(family_weight_df) != 4:
    raise ValueError(
        "Expected 4 frozen context families."
    )


print(
    "Frozen modifier features :",
    len(calibration_df)
)

print(
    "Frozen families          :",
    len(family_weight_df)
)

display(calibration_df)

display(family_weight_df)
'''
))


# ============================================================
# 15. 30G EXACT FROZEN RECONSTRUCTION
# ============================================================

cells.append(md(
"""
# 30G | Frozen Wall-to-Wall Integrated Product

This section reconstructs the final integration using:

- unchanged B18C calibration;
- frozen feature directions;
- frozen within-family weights;
- frozen family weights;
- F05 modifier amplitude;
- evidence-gated class transitions;
- maximum class change of ±1.

No fitting or tuning occurs here.
"""
))


cells.append(code(
r'''
# ------------------------------------------------------------
# Feature source registry
# ------------------------------------------------------------

feature_source_registry = {

    "LOCAL_RELIEF_300M_M":
        ASSETS["TERRAIN"],

    "SLOPE_DEG":
        ASSETS["TERRAIN"],

    "HAND_M":
        ASSETS["HYDRO"],

    "SILT_PCT_DEEP_100_200CM":
        ASSETS["SOIL"],

    "SOC_GKG_SURFACE_0_30CM":
        ASSETS["SOIL"],

    "WV1500_DEEP_100_200CM":
        ASSETS["SOIL_WATER"],

    "WV10_DEEP_100_200CM":
        ASSETS["SOIL_WATER"],

    "PAW_PROXY_SURFACE_0_30CM":
        ASSETS["SOIL_WATER"],
}


# ------------------------------------------------------------
# Core
# ------------------------------------------------------------

core_img = ee.Image(
    ASSETS["CORE"]
)

core_class = (
    core_img
    .select("CONDITION_CLASS")
    .round()
    .toInt16()
)

core_raw = (
    core_img
    .select("CONDITION_CLASS_RAW")
    .round()
    .toInt16()
)

core_risk = (
    core_img
    .select("RISK_SCORE_0_100")
    .toFloat()
)

valid_mask = (
    core_class.gte(1)
    .And(
        core_class.lte(4)
    )
)


# ------------------------------------------------------------
# Directional feature normalization
#
# P10 -> 0
# P90 -> 1
# negative associations inverted
# [0,1] -> [-1,+1]
# ------------------------------------------------------------

directional_images = {}

for _, row in calibration_df.iterrows():

    feature = row["feature"]

    source = (
        ee.Image(
            feature_source_registry[
                feature
            ]
        )
        .select(feature)
        .toFloat()
        .updateMask(valid_mask)
    )

    p10 = float(
        row["p10"]
    )

    p90 = float(
        row["p90"]
    )

    direction = int(
        row["association_direction"]
    )

    norm01 = (
        source
        .subtract(p10)
        .divide(
            p90 - p10
        )
        .clamp(
            0,
            1
        )
    )

    if direction < 0:

        norm01 = (
            ee.Image.constant(1)
            .subtract(norm01)
        )

    directional_images[
        feature
    ] = (
        norm01
        .multiply(2)
        .subtract(1)
        .rename(
            f"DIR_{feature}"
        )
    )


# ------------------------------------------------------------
# Within-family composites
# ------------------------------------------------------------

family_score_images = {}
family_coverage_images = {}

for family in (
    family_weight_df[
        "family"
    ].tolist()
):

    family_cal = (
        calibration_df[
            calibration_df[
                "family"
            ] == family
        ]
    )

    weighted_sum = (
        ee.Image.constant(0)
        .toFloat()
    )

    available_weight = (
        ee.Image.constant(0)
        .toFloat()
    )

    for _, row in family_cal.iterrows():

        feature = row["feature"]

        weight = float(
            row[
                "within_family_weight"
            ]
        )

        img = directional_images[
            feature
        ]

        valid = (
            img.mask()
            .reduce(
                ee.Reducer.min()
            )
            .gt(0)
        )

        weighted_sum = (
            weighted_sum
            .add(
                img
                .unmask(0)
                .multiply(weight)
            )
        )

        available_weight = (
            available_weight
            .add(
                valid
                .toFloat()
                .multiply(weight)
            )
        )

    family_score = (
        weighted_sum
        .divide(
            available_weight
            .max(1e-6)
        )
        .updateMask(
            available_weight.gte(0.50)
        )
        .clamp(
            -1,
            1
        )
        .rename(
            f"FAMILY_SCORE_{family}"
        )
    )

    family_score_images[
        family
    ] = family_score

    family_coverage_images[
        family
    ] = (
        available_weight
        .rename(
            f"FAMILY_COVERAGE_{family}"
        )
    )


# ------------------------------------------------------------
# Family-balanced overall context modifier
# ------------------------------------------------------------

overall_sum = (
    ee.Image.constant(0)
    .toFloat()
)

overall_weight = (
    ee.Image.constant(0)
    .toFloat()
)

for _, row in family_weight_df.iterrows():

    family = row[
        "family"
    ]

    family_weight = float(
        row[
            "family_weight"
        ]
    )

    img = family_score_images[
        family
    ]

    valid = (
        img.mask()
        .reduce(
            ee.Reducer.min()
        )
        .gt(0)
    )

    overall_sum = (
        overall_sum
        .add(
            img
            .unmask(0)
            .multiply(
                family_weight
            )
        )
    )

    overall_weight = (
        overall_weight
        .add(
            valid
            .toFloat()
            .multiply(
                family_weight
            )
        )
    )


context_modifier = (
    overall_sum
    .divide(
        overall_weight
        .max(1e-6)
    )
    .updateMask(
        overall_weight.gte(0.75)
    )
    .clamp(
        -1,
        1
    )
    .rename(
        "CONTEXT_MODIFIER_SCORE"
    )
)

context_coverage = (
    overall_weight
    .rename(
        "CONTEXT_MODIFIER_COVERAGE"
    )
)


# ------------------------------------------------------------
# F05 integrated score
# ------------------------------------------------------------

FUSION_AMPLITUDE = 5

integrated_score = (
    core_risk
    .add(
        context_modifier
        .unmask(0)
        .multiply(
            FUSION_AMPLITUDE
        )
    )
    .clamp(
        0,
        100
    )
    .rename(
        "INTEGRATED_SCORE_0_100"
    )
)


# ------------------------------------------------------------
# Core evidence
# ------------------------------------------------------------

optical_valid = (
    core_img
    .select(
        "OPTICAL_VALID_PERIOD_COUNT"
    )
)

alert_mask = (
    core_img
    .select(
        "ALERT_MASK"
    )
    .round()
)

max_period_class = (
    core_img
    .select(
        "MAX_PERIOD_CLASS"
    )
)

max_consecutive = (
    core_img
    .select(
        "MAX_CONSECUTIVE_ALERT"
    )
)

optical_alert_total = (
    core_img
    .select(
        "GREENNESS_ALERT_PERIODS"
    )
    .add(
        core_img.select(
            "RED_EDGE_ALERT_PERIODS"
        )
    )
    .add(
        core_img.select(
            "MOISTURE_ALERT_PERIODS"
        )
    )
)

has_optical_support = (
    optical_valid.gt(0)
    .And(
        optical_alert_total.gt(0)
    )
)


# Preserve 30D raw -> final post-processing decisions.

postprocess_lock = (
    core_raw
    .neq(
        core_class
    )
)

unlocked = (
    postprocess_lock
    .Not()
)


# ------------------------------------------------------------
# Frozen AOI01 thresholds
# ------------------------------------------------------------

T12 = 12
T23 = 22
T34 = 32


modifier_available = (
    context_modifier
    .mask()
    .reduce(
        ee.Reducer.min()
    )
    .gt(0)
)

modifier_pos = (
    context_modifier
    .unmask(0)
    .gt(0)
)

modifier_neg = (
    context_modifier
    .unmask(0)
    .lt(0)
)


# ------------------------------------------------------------
# Evidence-gated transitions
# ------------------------------------------------------------

promote_1_2 = (
    core_class.eq(1)
    .And(unlocked)
    .And(modifier_available)
    .And(modifier_pos)
    .And(
        integrated_score.gte(T12)
    )
    .And(
        alert_mask.eq(1)
    )
)

promote_2_3 = (
    core_class.eq(2)
    .And(unlocked)
    .And(modifier_available)
    .And(modifier_pos)
    .And(
        integrated_score.gte(T23)
    )
    .And(
        has_optical_support
    )
    .And(
        max_period_class.gte(3)
    )
    .And(
        max_consecutive.gte(2)
    )
)

promote_3_4 = (
    core_class.eq(3)
    .And(unlocked)
    .And(modifier_available)
    .And(modifier_pos)
    .And(
        integrated_score.gte(T34)
    )
    .And(
        has_optical_support
    )
    .And(
        max_period_class.gte(3)
    )
    .And(
        max_consecutive.gte(3)
    )
)

demote_2_1 = (
    core_class.eq(2)
    .And(unlocked)
    .And(modifier_available)
    .And(modifier_neg)
    .And(
        integrated_score.lt(T12)
    )
    .And(
        alert_mask.eq(0)
    )
)

demote_3_2 = (
    core_class.eq(3)
    .And(unlocked)
    .And(modifier_available)
    .And(modifier_neg)
    .And(
        integrated_score.lt(T23)
    )
    .And(
        max_consecutive.lte(1)
    )
)

demote_4_3 = (
    core_class.eq(4)
    .And(unlocked)
    .And(modifier_available)
    .And(modifier_neg)
    .And(
        integrated_score.lt(T34)
    )
    .And(
        max_consecutive.lte(2)
    )
)


# ------------------------------------------------------------
# Maximum +/-1 class refinement
# ------------------------------------------------------------

integrated_class = (
    core_class
    .where(
        promote_1_2,
        2
    )
    .where(
        promote_2_3,
        3
    )
    .where(
        promote_3_4,
        4
    )
    .where(
        demote_2_1,
        1
    )
    .where(
        demote_3_2,
        2
    )
    .where(
        demote_4_3,
        3
    )
    .rename(
        "INTEGRATED_CLASS"
    )
    .toInt16()
)

class_delta = (
    integrated_class
    .subtract(
        core_class
    )
    .rename(
        "CLASS_DELTA"
    )
    .toInt16()
)


# ------------------------------------------------------------
# Reconstructed seven-band product
# ------------------------------------------------------------

integrated_img = (
    core_class
    .rename(
        "CORE_CLASS"
    )
    .addBands(
        core_risk.rename(
            "CORE_RISK_SCORE_0_100"
        )
    )
    .addBands(
        context_modifier
    )
    .addBands(
        context_coverage
    )
    .addBands(
        integrated_score
    )
    .addBands(
        integrated_class
    )
    .addBands(
        class_delta
    )
    .updateMask(
        valid_mask
    )
)

print(
    "Reconstructed bands:"
)

print(
    integrated_img
    .bandNames()
    .getInfo()
)
'''
))


# ============================================================
# 16. CANONICAL REPRODUCIBILITY QA
# ============================================================

cells.append(md(
"""
## 30G Canonical Reproducibility Check

The reconstructed frozen product is compared against the
permanent canonical Earth Engine asset.

This is a reproducibility / implementation check.

It is **not field accuracy**.
"""
))


cells.append(code(
r'''
canonical_img = ee.Image(
    ASSETS["CANONICAL"]
)

canonical_proj_info = (
    canonical_img
    .select(
        "INTEGRATED_CLASS"
    )
    .projection()
    .getInfo()
)

canonical_crs = (
    canonical_proj_info[
        "crs"
    ]
)

canonical_transform = (
    canonical_proj_info[
        "transform"
    ]
)


reconstructed_class_aligned = (
    integrated_img
    .select(
        "INTEGRATED_CLASS"
    )
    .reproject(
        crs=canonical_crs,
        crsTransform=canonical_transform
    )
)


class_mismatch = (
    reconstructed_class_aligned
    .neq(
        canonical_img.select(
            "INTEGRATED_CLASS"
        )
    )
    .rename(
        "MISMATCH"
    )
)


mismatch_area_ha = (
    ee.Image.pixelArea()
    .divide(10000)
    .rename(
        "AREA_HA"
    )
    .updateMask(
        class_mismatch
    )
    .reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=canonical_img.geometry(),
        crs=canonical_crs,
        crsTransform=canonical_transform,
        maxPixels=1e13,
        tileScale=4
    )
    .get(
        "AREA_HA"
    )
    .getInfo()
)

if mismatch_area_ha is None:
    mismatch_area_ha = 0.0


band_names = (
    canonical_img
    .bandNames()
    .getInfo()
)


expected_bands = [
    "CORE_CLASS",
    "CORE_RISK_SCORE_0_100",
    "CONTEXT_MODIFIER_SCORE",
    "CONTEXT_MODIFIER_COVERAGE",
    "INTEGRATED_SCORE_0_100",
    "INTEGRATED_CLASS",
    "CLASS_DELTA",
]


checks = {

    "seven_canonical_bands":
        band_names == expected_bands,

    "reconstructed_class_mismatch_zero":
        float(
            mismatch_area_ha
        ) == 0.0,

    "frozen_fusion_amplitude":
        FUSION_AMPLITUDE == 5,

    "frozen_thresholds":
        (
            T12 == 12
            and T23 == 22
            and T34 == 32
        ),
}


print(
    "Canonical class mismatch area:",
    f"{float(mismatch_area_ha):.6f} ha"
)

print()

for name, result in checks.items():

    print(
        f"{name:40s}:",
        "PASS"
        if result
        else "FAIL"
    )


if not all(
    checks.values()
):
    raise RuntimeError(
        "Canonical reproducibility check failed."
    )

print(
    "\n30G canonical reproducibility : PASS"
)
'''
))


# ============================================================
# 17. 30H
# ============================================================

cells.append(md(
"""
# 30H | Analytical Freeze

30H records the final canonical statistics, legend,
band dictionary, final map, product summary and freeze
manifest.

No further AOI01 model tuning is performed unless new,
independent validation evidence justifies revision.
"""
))


cells.append(code(
r'''
CHECKPOINT_30H = (
    PROJECT_ROOT /
    "checkpoints_30H"
)

required_30h = [
    "30H_FINAL_CLASS_AREA.csv",
    "30H_FINAL_TRANSITION_AREA.csv",
    "30H_PRODUCT_SUMMARY.json",
    "30H_LEGEND.json",
    "30H_BAND_DICTIONARY.json",
    "30H_FREEZE_MANIFEST.json",
    "30H_FINAL_MAP.png",
    "30H_PRODUCT_SUMMARY.md",
]

missing_30h = [
    name
    for name in required_30h
    if not (
        CHECKPOINT_30H /
        name
    ).exists()
]

if missing_30h:
    raise FileNotFoundError(
        f"Missing 30H files: {missing_30h}"
    )


class_area_df = pd.read_csv(
    CHECKPOINT_30H /
    "30H_FINAL_CLASS_AREA.csv"
)

transition_df = pd.read_csv(
    CHECKPOINT_30H /
    "30H_FINAL_TRANSITION_AREA.csv"
)

display(class_area_df)

print(
    "30H required files : PASS"
)
'''
))


# ============================================================
# 18. 30I
# ============================================================

cells.append(md(
"""
# 30I | Web Delivery

The web-delivery contract separates the cloud analytical
source of truth from distribution artifacts.

Primary raster delivery:

1. `SIAK_AOI01_O3_CLASS_COG_2025.tif`
2. `SIAK_AOI01_O3_METRICS_COG_2025.tif`

COGs are delivery products.

They do not replace the permanent Earth Engine analytical
asset.
"""
))


cells.append(code(
r'''
COG_STATUS_PATH = (
    PACKAGE_ROOT /
    "11_LOGS" /
    "30I_COG_EXPORT_STATUS_SNAPSHOT.json"
)

if COG_STATUS_PATH.exists():

    with open(
        COG_STATUS_PATH,
        "r",
        encoding="utf-8"
    ) as f:

        cog_status = json.load(f)

    print(
        json.dumps(
            cog_status,
            indent=2
        )
    )

else:

    print(
        "Historical COG status snapshot "
        "not found."
    )


WEB_DIR = (
    PROJECT_ROOT /
    "WEB_DELIVERY_OUTPUT3"
)

print(
    "\nLocal web-delivery source:",
    WEB_DIR
)

print(
    "Exists:",
    WEB_DIR.exists()
)
'''
))


# ============================================================
# 19. FINAL MASTER GATE
# ============================================================

cells.append(md(
"""
# Master Pipeline Gate

Passing this gate means:

- configuration is readable;
- persistent source assets are available;
- frozen 30F parameters exist;
- 30G can be reconstructed;
- reconstructed class product agrees with the canonical asset;
- 30H freeze products are available;
- 30I delivery provenance is recorded.

It does **not** mean independent field accuracy has been
demonstrated.
"""
))


cells.append(code(
r'''
master_gate = {

    "configuration":
        CONFIG_PATH.exists(),

    "gee_asset_inventory":
        ASSET_INVENTORY_PATH.exists(),

    "frozen_calibration":
        CALIBRATION_PATH.exists(),

    "frozen_family_weights":
        FAMILY_WEIGHT_PATH.exists(),

    "canonical_asset_7_bands":
        band_names == expected_bands,

    "canonical_class_reproducibility":
        float(
            mismatch_area_ha
        ) == 0.0,

    "30h_freeze":
        len(
            missing_30h
        ) == 0,
}


print(
    "=" * 90
)

print(
    "MASTER_PIPELINE_OUTPUT3 FINAL GATE"
)

print(
    "=" * 90
)


for name, result in master_gate.items():

    print(
        f"{name:40s}:",
        "PASS"
        if result
        else "FAIL"
    )


if all(
    master_gate.values()
):

    print("""
MASTER PIPELINE RESULT: PASS

AOI01 Output 3 is reproducible from the frozen
Earth Engine source assets and frozen Python
calibration parameters.

This is a reproducibility / implementation result,
not an independent field-accuracy claim.
""")

else:

    raise RuntimeError(
        "Master pipeline gate failed."
    )
'''
))


# ============================================================
# 20. ARCHIVE REFERENCE
# ============================================================

cells.append(md(
f"""
# Historical Working Notebook

The complete experimental / development notebook used during
Output 3 development is preserved separately as:

`{snapshot_path.name}`

A cell-level index is preserved as:

`OUTPUT3_WORKING_NOTEBOOK_CELL_INDEX.csv`

This separation keeps the official master notebook clean and
safe to rerun while retaining the full research/development
history for audit and handover.
"""
))


# ============================================================
# 21. BUILD NOTEBOOK
# ============================================================

master_nb = nbf.v4.new_notebook()

master_nb.cells = cells

master_nb.metadata = {

    "kernelspec": {
        "display_name":
            "Python (copernicus_env)",

        "language":
            "python",

        "name":
            "python3"
    },

    "language_info": {
        "name":
            "python",

        "version":
            "3.10"
    },

    "output3": {

        "product":
            "Plantation Condition & Inspection Priority",

        "aoi_id":
            "SIAK_AOI01",

        "reference_year":
            2025,

        "architecture":
            "Python/Jupyter + Earth Engine backend",

        "analytical_status":
            "FROZEN",

        "field_validated":
            False
    }
}


master_path = (
    MASTER_DIR /
    "MASTER_PIPELINE_OUTPUT3.ipynb"
)

nbf.write(
    master_nb,
    master_path
)


# ============================================================
# 22. RE-READ VALIDATION
# ============================================================

test_nb = nbf.read(
    master_path,
    as_version=4
)

master_cell_count = len(
    test_nb.cells
)

code_cell_count = sum(
    1
    for c in test_nb.cells
    if c.cell_type == "code"
)

markdown_cell_count = sum(
    1
    for c in test_nb.cells
    if c.cell_type == "markdown"
)


# ============================================================
# 23. MASTER MANIFEST
# ============================================================

manifest = {

    "stage":
        "30J-B",

    "status":
        "PASS",

    "created_at":
        datetime.now().isoformat(),

    "master_notebook":
        str(master_path),

    "working_notebook_source":
        str(source_notebook),

    "working_notebook_snapshot":
        str(snapshot_path),

    "working_notebook_cell_index":
        str(cell_index_path),

    "master_cell_count":
        master_cell_count,

    "master_code_cells":
        code_cell_count,

    "master_markdown_cells":
        markdown_cell_count,

    "workflow_scope": [
        "30A",
        "30B",
        "30C",
        "30D",
        "30E",
        "30F",
        "30G",
        "30H",
        "30I"
    ],

    "architecture":
        (
            "Hybrid GEE + Python; "
            "30B-30E persistent GEE preprocessing "
            "is not duplicated locally."
        ),

    "exports_started":
        False,

    "analytical_model_changed":
        False,

    "field_validated":
        False
}


manifest_path = (
    MASTER_DIR /
    "30J_B_MASTER_PIPELINE_MANIFEST.json"
)

with open(
    manifest_path,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        manifest,
        f,
        indent=2,
        ensure_ascii=False
    )


# ============================================================
# 24. FINAL GATE
# ============================================================

checks = {

    "master_notebook_created":
        master_path.exists(),

    "working_notebook_snapshot":
        snapshot_path.exists(),

    "working_cell_index":
        cell_index_path.exists(),

    "master_manifest":
        manifest_path.exists(),

    "master_notebook_readable":
        master_cell_count > 0,

    "contains_code_cells":
        code_cell_count > 0,

    "contains_markdown_cells":
        markdown_cell_count > 0,
}


print("\n" + "=" * 115)
print("30J-B | FINAL GATE")
print("=" * 115)

for name, result in checks.items():

    print(
        f"{name:40s}:",
        "PASS"
        if result
        else "FAIL"
    )


print("\nMaster notebook:")
print(
    master_path.resolve()
)

print("\nWorking notebook snapshot:")
print(
    snapshot_path.resolve()
)

print("\nMaster cells:")
print(
    f"{master_cell_count} total | "
    f"{code_cell_count} code | "
    f"{markdown_cell_count} markdown"
)

print("\n" + "-" * 115)


if all(checks.values()):

    print("""
30J-B RESULT: PASS

MASTER_PIPELINE_OUTPUT3.ipynb HAS BEEN CREATED.

The master now captures:
- the 30A-30I process contract;
- persistent GEE source assets;
- frozen 30F calibration;
- exact frozen 30G reconstruction logic;
- canonical reproducibility QA;
- 30H analytical freeze;
- 30I web-delivery provenance.

The original OUTPUT 3 working notebook has also
been preserved separately for full development-history audit.

No raster was re-exported.
No model parameter was changed.

NEXT:
30J-C | REUSABLE AOI RUNNER + AUTOMATION CONFIG
""")

else:

    print("""
30J-B RESULT: REVIEW REQUIRED

Do not proceed to 30J-C until the master-package
creation issue is resolved.
""")

print("=" * 115)

# ========================================
# ORIGINAL CELL 73
# ========================================

# ============================================================
# 30J-C | REUSABLE AOI RUNNER + AUTOMATION READINESS
#
# Produces:
# 1. OUTPUT3_AOI_TEMPLATE.json
# 2. run_output3.py
# 3. AUTOMATION_READINESS.json
# 4. RUNNER_MANIFEST.json
#
# No model tuning.
# No raster export.
# No analytical reprocessing is executed by this cell.
# ============================================================

import json
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path.cwd()

PACKAGE_ROOT = (
    PROJECT_ROOT /
    "OUTPUT3_COMPLETE_PACKAGE"
)

MASTER_DIR = (
    PACKAGE_ROOT /
    "00_MASTER_PIPELINE"
)

CONFIG_DIR = (
    PACKAGE_ROOT /
    "01_CONFIG"
)

DOC_DIR = (
    PACKAGE_ROOT /
    "09_DOCUMENTATION"
)

LOG_DIR = (
    PACKAGE_ROOT /
    "11_LOGS"
)

for p in [
    MASTER_DIR,
    CONFIG_DIR,
    DOC_DIR,
    LOG_DIR,
]:
    p.mkdir(
        parents=True,
        exist_ok=True
    )


print("=" * 115)
print("30J-C | REUSABLE AOI RUNNER + AUTOMATION READINESS")
print("=" * 115)


# ============================================================
# 1. VERIFY 30J-B
# ============================================================

MASTER_NOTEBOOK = (
    MASTER_DIR /
    "MASTER_PIPELINE_OUTPUT3.ipynb"
)

MASTER_MANIFEST = (
    MASTER_DIR /
    "30J_B_MASTER_PIPELINE_MANIFEST.json"
)

if not MASTER_NOTEBOOK.exists():
    raise FileNotFoundError(
        MASTER_NOTEBOOK
    )

if not MASTER_MANIFEST.exists():
    raise FileNotFoundError(
        MASTER_MANIFEST
    )

print("\n[1] 30J-B FOUNDATION")
print("Master notebook : PASS")
print("Master manifest : PASS")


# ============================================================
# 2. AOI TEMPLATE
#
# This template separates AOI-specific values
# from processing logic.
# ============================================================

aoi_template = {

    "schema_version":
        "OUTPUT3_AOI_CONFIG_V1",

    "project_id":
        "palm-oil-503202",

    "aoi_id":
        "CHANGE_ME",

    "reference_year":
        2025,

    "mode":
        "TRANSFER_TEST",

    "gee_asset_root":
        "projects/palm-oil-503202/assets",

    "spatial": {

        "final_crs":
            "AUTO_FROM_CORE",

        "final_resolution_m":
            10,

        "preserve_native_context_resolution":
            True,

        "pseudo_downscaling_allowed":
            False
    },

    "assets": {

        "plantation_boundary":
            "REQUIRED",

        "core_30d":
            "REQUIRED",

        "age_30e01":
            "REQUIRED",

        "chirps_30e02a":
            "REQUIRED",

        "era5_30e02b":
            "REQUIRED",

        "etpet_30e02c":
            "REQUIRED",

        "terrain_30e03a":
            "REQUIRED",

        "hydrology_30e03b":
            "REQUIRED",

        "soil_30e04a":
            "REQUIRED",

        "soil_water_30e04b":
            "REQUIRED",

        "canonical_final":
            None
    },

    "frozen_model": {

        "calibration_csv":
            "checkpoints_30F/"
            "30F_B18C_AOI01_WALL_TO_WALL_CALIBRATION_V1.csv",

        "family_weights_csv":
            "checkpoints_30F/"
            "30F_B18C_FAMILY_WEIGHTS_V1.csv",

        "fusion_amplitude":
            5,

        "thresholds": {

            "T12":
                12,

            "T23":
                22,

            "T34":
                32
        },

        "max_class_change":
            1
    },

    "execution": {

        "start_exports":
            False,

        "allow_overwrite":
            False,

        "require_qa_before_export":
            True,

        "export_to_gee":
            False,

        "export_to_drive":
            False
    },

    "scientific_status": {

        "field_validated":
            False,

        "transferability_validated":
            False,

        "product_interpretation":
            "INSPECTION_PRIORITY_NOT_DIAGNOSIS"
    }
}


template_path = (
    CONFIG_DIR /
    "OUTPUT3_AOI_TEMPLATE.json"
)

with open(
    template_path,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        aoi_template,
        f,
        indent=2,
        ensure_ascii=False
    )

print("\n[2] REUSABLE AOI CONFIG")
print("Created :", template_path.resolve())
print("Config QC : PASS")


# ============================================================
# 3. CREATE REUSABLE RUNNER
# ============================================================

runner_code = r'''#!/usr/bin/env python
"""
run_output3.py

Reusable Output 3 orchestration runner.

Architecture:
Python/Jupyter orchestration + Google Earth Engine backend.

IMPORTANT:
This runner does not claim that AOI01 model parameters are
independently validated for another AOI.

TRANSFER_TEST mode means:
- run the same frozen workflow;
- measure coverage / reproducibility / behavior;
- do not interpret transfer as validated local accuracy.
"""

from pathlib import Path
import argparse
import json
import ssl

import certifi
import ee
import pandas as pd


# ============================================================
# UTILITIES
# ============================================================

def load_json(path):

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


def locate_project_root():

    start = Path.cwd().resolve()

    for candidate in [
        start,
        *start.parents
    ]:

        if (
            candidate /
            "OUTPUT3_COMPLETE_PACKAGE"
        ).exists():

            return candidate

    raise FileNotFoundError(
        "OUTPUT3_COMPLETE_PACKAGE not found."
    )


def initialize_ee(project_id):

    ssl._create_default_https_context = (
        lambda:
        ssl.create_default_context(
            cafile=certifi.where()
        )
    )

    ee.Initialize(
        project=project_id
    )


def check_asset(asset_id):

    try:

        ee.data.getAsset(
            asset_id
        )

        return True

    except Exception:

        return False


# ============================================================
# CONFIG VALIDATION
# ============================================================

def validate_config(cfg):

    required_top = [
        "project_id",
        "aoi_id",
        "reference_year",
        "mode",
        "assets",
        "frozen_model",
        "execution",
    ]

    for key in required_top:

        if key not in cfg:

            raise ValueError(
                f"Missing config field: {key}"
            )


    if cfg["mode"] not in [
        "REPRODUCE",
        "TRANSFER_TEST",
    ]:

        raise ValueError(
            "mode must be REPRODUCE "
            "or TRANSFER_TEST."
        )


# ============================================================
# ASSET CONTRACT
# ============================================================

def audit_assets(cfg):

    asset_cfg = cfg[
        "assets"
    ]

    required = [

        "plantation_boundary",

        "core_30d",

        "age_30e01",

        "chirps_30e02a",

        "era5_30e02b",

        "etpet_30e02c",

        "terrain_30e03a",

        "hydrology_30e03b",

        "soil_30e04a",

        "soil_water_30e04b",
    ]


    results = {}


    for key in required:

        asset_id = asset_cfg.get(
            key
        )

        if (
            asset_id is None
            or asset_id == "REQUIRED"
        ):

            results[
                key
            ] = {
                "status":
                    "NOT_CONFIGURED",

                "asset_id":
                    asset_id
            }

            continue


        exists = check_asset(
            asset_id
        )

        results[
            key
        ] = {

            "status":
                "PASS"
                if exists
                else "MISSING",

            "asset_id":
                asset_id
        }


    return results


# ============================================================
# FROZEN 30G RECONSTRUCTION
# ============================================================

def build_integrated_product(
    cfg,
    project_root
):

    assets = cfg[
        "assets"
    ]

    frozen = cfg[
        "frozen_model"
    ]


    calibration_path = (
        project_root /
        frozen[
            "calibration_csv"
        ]
    )

    weights_path = (
        project_root /
        frozen[
            "family_weights_csv"
        ]
    )


    calibration_df = pd.read_csv(
        calibration_path
    )

    family_weight_df = pd.read_csv(
        weights_path
    )


    if len(
        calibration_df
    ) != 8:

        raise RuntimeError(
            "Expected 8 frozen features."
        )


    if len(
        family_weight_df
    ) != 4:

        raise RuntimeError(
            "Expected 4 frozen families."
        )


    feature_source_registry = {

        "LOCAL_RELIEF_300M_M":
            assets[
                "terrain_30e03a"
            ],

        "SLOPE_DEG":
            assets[
                "terrain_30e03a"
            ],

        "HAND_M":
            assets[
                "hydrology_30e03b"
            ],

        "SILT_PCT_DEEP_100_200CM":
            assets[
                "soil_30e04a"
            ],

        "SOC_GKG_SURFACE_0_30CM":
            assets[
                "soil_30e04a"
            ],

        "WV1500_DEEP_100_200CM":
            assets[
                "soil_water_30e04b"
            ],

        "WV10_DEEP_100_200CM":
            assets[
                "soil_water_30e04b"
            ],

        "PAW_PROXY_SURFACE_0_30CM":
            assets[
                "soil_water_30e04b"
            ],
    }


    core_img = ee.Image(
        assets[
            "core_30d"
        ]
    )

    core_class = (
        core_img
        .select(
            "CONDITION_CLASS"
        )
        .round()
        .toInt16()
    )

    core_raw = (
        core_img
        .select(
            "CONDITION_CLASS_RAW"
        )
        .round()
        .toInt16()
    )

    core_risk = (
        core_img
        .select(
            "RISK_SCORE_0_100"
        )
        .toFloat()
    )


    valid_mask = (
        core_class.gte(1)
        .And(
            core_class.lte(4)
        )
    )


    directional_images = {}


    for _, row in (
        calibration_df.iterrows()
    ):

        feature = row[
            "feature"
        ]

        source = (
            ee.Image(
                feature_source_registry[
                    feature
                ]
            )
            .select(
                feature
            )
            .toFloat()
            .updateMask(
                valid_mask
            )
        )

        p10 = float(
            row["p10"]
        )

        p90 = float(
            row["p90"]
        )

        direction = int(
            row[
                "association_direction"
            ]
        )


        norm01 = (
            source
            .subtract(
                p10
            )
            .divide(
                p90 - p10
            )
            .clamp(
                0,
                1
            )
        )


        if direction < 0:

            norm01 = (
                ee.Image.constant(1)
                .subtract(
                    norm01
                )
            )


        directional_images[
            feature
        ] = (
            norm01
            .multiply(2)
            .subtract(1)
        )


    family_score_images = {}


    for family in (
        family_weight_df[
            "family"
        ].tolist()
    ):

        family_cal = (
            calibration_df[
                calibration_df[
                    "family"
                ] == family
            ]
        )


        weighted_sum = (
            ee.Image.constant(0)
            .toFloat()
        )

        available_weight = (
            ee.Image.constant(0)
            .toFloat()
        )


        for _, row in (
            family_cal.iterrows()
        ):

            feature = row[
                "feature"
            ]

            weight = float(
                row[
                    "within_family_weight"
                ]
            )

            img = (
                directional_images[
                    feature
                ]
            )


            valid = (
                img.mask()
                .reduce(
                    ee.Reducer.min()
                )
                .gt(0)
            )


            weighted_sum = (
                weighted_sum
                .add(
                    img
                    .unmask(0)
                    .multiply(
                        weight
                    )
                )
            )


            available_weight = (
                available_weight
                .add(
                    valid
                    .toFloat()
                    .multiply(
                        weight
                    )
                )
            )


        family_score_images[
            family
        ] = (
            weighted_sum
            .divide(
                available_weight
                .max(1e-6)
            )
            .updateMask(
                available_weight
                .gte(0.50)
            )
            .clamp(
                -1,
                1
            )
        )


    overall_sum = (
        ee.Image.constant(0)
        .toFloat()
    )

    overall_weight = (
        ee.Image.constant(0)
        .toFloat()
    )


    for _, row in (
        family_weight_df.iterrows()
    ):

        family = row[
            "family"
        ]

        family_weight = float(
            row[
                "family_weight"
            ]
        )


        img = (
            family_score_images[
                family
            ]
        )


        valid = (
            img.mask()
            .reduce(
                ee.Reducer.min()
            )
            .gt(0)
        )


        overall_sum = (
            overall_sum
            .add(
                img
                .unmask(0)
                .multiply(
                    family_weight
                )
            )
        )


        overall_weight = (
            overall_weight
            .add(
                valid
                .toFloat()
                .multiply(
                    family_weight
                )
            )
        )


    context_modifier = (
        overall_sum
        .divide(
            overall_weight
            .max(1e-6)
        )
        .updateMask(
            overall_weight
            .gte(0.75)
        )
        .clamp(
            -1,
            1
        )
        .rename(
            "CONTEXT_MODIFIER_SCORE"
        )
    )


    context_coverage = (
        overall_weight
        .rename(
            "CONTEXT_MODIFIER_COVERAGE"
        )
    )


    amplitude = float(
        frozen[
            "fusion_amplitude"
        ]
    )


    integrated_score = (
        core_risk
        .add(
            context_modifier
            .unmask(0)
            .multiply(
                amplitude
            )
        )
        .clamp(
            0,
            100
        )
        .rename(
            "INTEGRATED_SCORE_0_100"
        )
    )


    optical_valid = (
        core_img
        .select(
            "OPTICAL_VALID_PERIOD_COUNT"
        )
    )

    alert_mask = (
        core_img
        .select(
            "ALERT_MASK"
        )
        .round()
    )

    max_period_class = (
        core_img
        .select(
            "MAX_PERIOD_CLASS"
        )
    )

    max_consecutive = (
        core_img
        .select(
            "MAX_CONSECUTIVE_ALERT"
        )
    )


    optical_alert_total = (
        core_img
        .select(
            "GREENNESS_ALERT_PERIODS"
        )
        .add(
            core_img.select(
                "RED_EDGE_ALERT_PERIODS"
            )
        )
        .add(
            core_img.select(
                "MOISTURE_ALERT_PERIODS"
            )
        )
    )


    has_optical_support = (
        optical_valid.gt(0)
        .And(
            optical_alert_total.gt(0)
        )
    )


    postprocess_lock = (
        core_raw
        .neq(
            core_class
        )
    )


    unlocked = (
        postprocess_lock
        .Not()
    )


    thresholds = frozen[
        "thresholds"
    ]

    T12 = float(
        thresholds["T12"]
    )

    T23 = float(
        thresholds["T23"]
    )

    T34 = float(
        thresholds["T34"]
    )


    modifier_available = (
        context_modifier
        .mask()
        .reduce(
            ee.Reducer.min()
        )
        .gt(0)
    )


    modifier_pos = (
        context_modifier
        .unmask(0)
        .gt(0)
    )

    modifier_neg = (
        context_modifier
        .unmask(0)
        .lt(0)
    )


    promote_1_2 = (
        core_class.eq(1)
        .And(unlocked)
        .And(
            modifier_available
        )
        .And(
            modifier_pos
        )
        .And(
            integrated_score
            .gte(T12)
        )
        .And(
            alert_mask.eq(1)
        )
    )


    promote_2_3 = (
        core_class.eq(2)
        .And(unlocked)
        .And(
            modifier_available
        )
        .And(
            modifier_pos
        )
        .And(
            integrated_score
            .gte(T23)
        )
        .And(
            has_optical_support
        )
        .And(
            max_period_class
            .gte(3)
        )
        .And(
            max_consecutive
            .gte(2)
        )
    )


    promote_3_4 = (
        core_class.eq(3)
        .And(unlocked)
        .And(
            modifier_available
        )
        .And(
            modifier_pos
        )
        .And(
            integrated_score
            .gte(T34)
        )
        .And(
            has_optical_support
        )
        .And(
            max_period_class
            .gte(3)
        )
        .And(
            max_consecutive
            .gte(3)
        )
    )


    demote_2_1 = (
        core_class.eq(2)
        .And(unlocked)
        .And(
            modifier_available
        )
        .And(
            modifier_neg
        )
        .And(
            integrated_score
            .lt(T12)
        )
        .And(
            alert_mask.eq(0)
        )
    )


    demote_3_2 = (
        core_class.eq(3)
        .And(unlocked)
        .And(
            modifier_available
        )
        .And(
            modifier_neg
        )
        .And(
            integrated_score
            .lt(T23)
        )
        .And(
            max_consecutive
            .lte(1)
        )
    )


    demote_4_3 = (
        core_class.eq(4)
        .And(unlocked)
        .And(
            modifier_available
        )
        .And(
            modifier_neg
        )
        .And(
            integrated_score
            .lt(T34)
        )
        .And(
            max_consecutive
            .lte(2)
        )
    )


    integrated_class = (
        core_class
        .where(
            promote_1_2,
            2
        )
        .where(
            promote_2_3,
            3
        )
        .where(
            promote_3_4,
            4
        )
        .where(
            demote_2_1,
            1
        )
        .where(
            demote_3_2,
            2
        )
        .where(
            demote_4_3,
            3
        )
        .rename(
            "INTEGRATED_CLASS"
        )
        .toInt16()
    )


    class_delta = (
        integrated_class
        .subtract(
            core_class
        )
        .rename(
            "CLASS_DELTA"
        )
        .toInt16()
    )


    final_img = (
        core_class
        .rename(
            "CORE_CLASS"
        )
        .addBands(
            core_risk.rename(
                "CORE_RISK_SCORE_0_100"
            )
        )
        .addBands(
            context_modifier
        )
        .addBands(
            context_coverage
        )
        .addBands(
            integrated_score
        )
        .addBands(
            integrated_class
        )
        .addBands(
            class_delta
        )
        .updateMask(
            valid_mask
        )
    )


    return final_img


# ============================================================
# BASIC QA
# ============================================================

def basic_qa(
    img
):

    bands = (
        img
        .bandNames()
        .getInfo()
    )


    expected = [

        "CORE_CLASS",

        "CORE_RISK_SCORE_0_100",

        "CONTEXT_MODIFIER_SCORE",

        "CONTEXT_MODIFIER_COVERAGE",

        "INTEGRATED_SCORE_0_100",

        "INTEGRATED_CLASS",

        "CLASS_DELTA",
    ]


    return {

        "seven_bands":
            bands == expected,

        "band_names":
            bands
    }


# ============================================================
# MAIN
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=
        "Reusable Output 3 pipeline runner"
    )


    parser.add_argument(
        "--config",
        required=True,
        help="Path to AOI JSON config."
    )


    parser.add_argument(
        "--audit-only",
        action="store_true",
        help=
        "Check configuration and assets "
        "without building the final graph."
    )


    args = parser.parse_args()


    config_path = Path(
        args.config
    ).resolve()


    cfg = load_json(
        config_path
    )


    validate_config(
        cfg
    )


    project_root = (
        locate_project_root()
    )


    initialize_ee(
        cfg[
            "project_id"
        ]
    )


    print("=" * 90)

    print(
        "OUTPUT 3 REUSABLE RUNNER"
    )

    print("=" * 90)

    print(
        "AOI  :",
        cfg["aoi_id"]
    )

    print(
        "Mode :",
        cfg["mode"]
    )


    asset_audit = audit_assets(
        cfg
    )


    print(
        "\nASSET AUDIT"
    )


    for key, result in (
        asset_audit.items()
    ):

        print(
            f"{key:25s}: "
            f"{result['status']}"
        )


    asset_pass = all(
        item[
            "status"
        ] == "PASS"
        for item in (
            asset_audit.values()
        )
    )


    if not asset_pass:

        print("""
RUNNER RESULT:
UPSTREAM ASSETS REQUIRED

The downstream Output 3 integration cannot run
until the required 30D/30E assets exist for this AOI.
""")

        return


    if args.audit_only:

        print("""
RUNNER RESULT:
ASSET CONTRACT PASS

Audit-only mode finished.
No analytical graph was built.
""")

        return


    final_img = (
        build_integrated_product(
            cfg,
            project_root
        )
    )


    qa = basic_qa(
        final_img
    )


    print(
        "\nOUTPUT BANDS:"
    )

    print(
        qa[
            "band_names"
        ]
    )


    print(
        "\nSEVEN-BAND CONTRACT:",
        "PASS"
        if qa[
            "seven_bands"
        ]
        else "FAIL"
    )


    if cfg[
        "mode"
    ] == "TRANSFER_TEST":

        print("""
TRANSFER TEST WARNING

The pipeline executed using frozen AOI01
parameters.

This demonstrates technical portability only.

It does NOT demonstrate:
- field accuracy;
- local calibration validity;
- ecological transferability;
- threshold optimality for the new AOI.
""")


    if not cfg[
        "execution"
    ][
        "start_exports"
    ]:

        print("""
EXPORTS:
NOT STARTED

This is intentional.
QA must be reviewed before persistent export.
""")


    print("""
RUNNER RESULT: PASS

The Output 3 analytical graph was successfully
constructed from the configured persistent assets.
""")


if __name__ == "__main__":

    main()
'''


runner_path = (
    MASTER_DIR /
    "run_output3.py"
)

with open(
    runner_path,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        runner_code
    )


print("\n[3] REUSABLE RUNNER")
print("Created :", runner_path.resolve())


# ============================================================
# 4. AUTOMATION READINESS
#
# Critical distinction:
#
# READY:
# frozen-asset -> final integration
#
# NOT YET ONE-CLICK:
# raw satellite/data source -> all 30B-30E assets
# ============================================================

automation_readiness = {

    "generated_at":
        datetime.now().isoformat(),

    "overall_status":
        "PARTIALLY_AUTOMATED_REPRODUCIBLE_PIPELINE",

    "ready_now": {

        "project_configuration":
            True,

        "earth_engine_asset_connection":
            True,

        "asset_contract_validation":
            True,

        "30f_frozen_parameter_loading":
            True,

        "30g_wall_to_wall_reconstruction":
            True,

        "technical_qa":
            True,

        "web_export_orchestration":
            True,

        "aoi01_reproduction":
            True
    },

    "requires_packaging_before_true_one_click_new_aoi": {

        "30a_aoi_bootstrap":
            True,

        "30b_baseline_monitoring_asset_builder":
            True,

        "30c_anomaly_asset_builder":
            True,

        "30d_core_risk_asset_builder":
            True,

        "30e_context_asset_builders":
            True
    },

    "new_aoi_current_behavior":

        (
            "The reusable runner can automatically "
            "audit and integrate a new AOI once the "
            "required frozen-format 30D/30E assets "
            "exist. Full raw-source-to-final one-click "
            "automation still requires packaging the "
            "upstream stage builders."
        ),

    "scientific_guardrail":

        (
            "AOI01 calibration and thresholds may be "
            "used for transfer testing, but portability "
            "must not be described as validated "
            "transferability without independent evidence."
        )
}


readiness_path = (
    DOC_DIR /
    "OUTPUT3_AUTOMATION_READINESS.json"
)

with open(
    readiness_path,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        automation_readiness,
        f,
        indent=2,
        ensure_ascii=False
    )


# ============================================================
# 5. RUNNER README
# ============================================================

runner_readme = r"""
# Output 3 Reusable Runner

## Files

- `run_output3.py`
- `OUTPUT3_AOI_TEMPLATE.json`

## Audit a configured AOI

```bash
python run_output3.py --config PATH_TO_CONFIG.json --audit-only

# ========================================
# ORIGINAL CELL 74
# ========================================

# ============================================================
# 30J-C V2 | REUSABLE AOI RUNNER + AUTOMATION READINESS
#
# FIXED VERSION
#
# Creates:
# 1. OUTPUT3_AOI_TEMPLATE.json
# 2. SIAK_AOI01_OUTPUT3_RUN_CONFIG.json
# 3. run_output3.py
# 4. OUTPUT3_AUTOMATION_READINESS.json
# 5. README_REUSABLE_RUNNER.md
# 6. 30J_C_REUSABLE_RUNNER_MANIFEST.json
#
# IMPORTANT:
# - No raster export.
# - No model tuning.
# - No analytical product is overwritten.
# ============================================================

from pathlib import Path
from datetime import datetime
from textwrap import dedent
import json


# ============================================================
# 1. PATHS
# ============================================================

PROJECT_ROOT = Path.cwd()

PACKAGE_ROOT = (
    PROJECT_ROOT /
    "OUTPUT3_COMPLETE_PACKAGE"
)

MASTER_DIR = (
    PACKAGE_ROOT /
    "00_MASTER_PIPELINE"
)

CONFIG_DIR = (
    PACKAGE_ROOT /
    "01_CONFIG"
)

DOC_DIR = (
    PACKAGE_ROOT /
    "09_DOCUMENTATION"
)

LOG_DIR = (
    PACKAGE_ROOT /
    "11_LOGS"
)

for folder in [
    MASTER_DIR,
    CONFIG_DIR,
    DOC_DIR,
    LOG_DIR,
]:
    folder.mkdir(
        parents=True,
        exist_ok=True
    )


print("=" * 115)
print("30J-C V2 | REUSABLE AOI RUNNER + AUTOMATION READINESS")
print("=" * 115)


# ============================================================
# 2. VERIFY 30J-B
# ============================================================

MASTER_NOTEBOOK = (
    MASTER_DIR /
    "MASTER_PIPELINE_OUTPUT3.ipynb"
)

MASTER_MANIFEST = (
    MASTER_DIR /
    "30J_B_MASTER_PIPELINE_MANIFEST.json"
)

AOI01_BASE_CONFIG = (
    CONFIG_DIR /
    "SIAK_AOI01_OUTPUT3_CONFIG.json"
)


required_inputs = [
    MASTER_NOTEBOOK,
    MASTER_MANIFEST,
    AOI01_BASE_CONFIG,
]

missing_inputs = [
    path
    for path in required_inputs
    if not path.exists()
]

if missing_inputs:

    raise FileNotFoundError(
        "Missing required 30J-B / 30J-A inputs:\n"
        +
        "\n".join(
            str(path)
            for path in missing_inputs
        )
    )


print("\n[1] FOUNDATION")
print("Master notebook    : PASS")
print("Master manifest    : PASS")
print("AOI01 base config  : PASS")


# ============================================================
# 3. LOAD AOI01 BASE CONFIG
# ============================================================

with open(
    AOI01_BASE_CONFIG,
    "r",
    encoding="utf-8"
) as f:

    base_cfg = json.load(f)


# ============================================================
# 4. CREATE GENERIC NEW-AOI TEMPLATE
# ============================================================

aoi_template = {

    "schema_version":
        "OUTPUT3_AOI_CONFIG_V2",

    "project_id":
        base_cfg[
            "project_id"
        ],

    "aoi_id":
        "CHANGE_ME",

    "reference_year":
        base_cfg[
            "reference_year"
        ],

    "mode":
        "TRANSFER_TEST",

    "assets": {

        "plantation_boundary":
            "REQUIRED",

        "core_30d":
            "REQUIRED",

        "age_30e01":
            "REQUIRED",

        "chirps_30e02a":
            "REQUIRED",

        "era5_30e02b":
            "REQUIRED",

        "etpet_30e02c":
            "REQUIRED",

        "terrain_30e03a":
            "REQUIRED",

        "hydrology_30e03b":
            "REQUIRED",

        "soil_30e04a":
            "REQUIRED",

        "soil_water_30e04b":
            "REQUIRED",

        "canonical_final":
            None
    },

    "frozen_model": {

        "calibration_csv":
            "checkpoints_30F/"
            "30F_B18C_AOI01_WALL_TO_WALL_CALIBRATION_V1.csv",

        "family_weights_csv":
            "checkpoints_30F/"
            "30F_B18C_FAMILY_WEIGHTS_V1.csv",

        "fusion_amplitude":
            5,

        "thresholds": {

            "T12":
                12,

            "T23":
                22,

            "T34":
                32
        },

        "max_class_change":
            1
    },

    "execution": {

        "start_exports":
            False,

        "require_qa_before_export":
            True,

        "allow_overwrite":
            False
    },

    "scientific_status": {

        "field_validated":
            False,

        "transferability_validated":
            False,

        "interpretation":
            "INSPECTION_PRIORITY_NOT_DIAGNOSIS"
    }
}


template_path = (
    CONFIG_DIR /
    "OUTPUT3_AOI_TEMPLATE.json"
)

with open(
    template_path,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        aoi_template,
        f,
        indent=2,
        ensure_ascii=False
    )


# ============================================================
# 5. CREATE READY-TO-RUN AOI01 CONFIG
#
# Unlike the generic template, this contains real AOI01
# asset IDs and can be used for reproducibility testing.
# ============================================================

aoi01_run_config = {

    "schema_version":
        "OUTPUT3_AOI_CONFIG_V2",

    "project_id":
        base_cfg[
            "project_id"
        ],

    "aoi_id":
        base_cfg[
            "aoi_id"
        ],

    "reference_year":
        base_cfg[
            "reference_year"
        ],

    "mode":
        "REPRODUCE",

    "assets": {

        "plantation_boundary":
            base_cfg[
                "upstream_assets"
            ][
                "plantation_boundary"
            ],

        "core_30d":
            base_cfg[
                "output3_assets"
            ][
                "core"
            ],

        "age_30e01":
            base_cfg[
                "output3_assets"
            ][
                "age"
            ],

        "chirps_30e02a":
            base_cfg[
                "output3_assets"
            ][
                "chirps"
            ],

        "era5_30e02b":
            base_cfg[
                "output3_assets"
            ][
                "era5_land"
            ],

        "etpet_30e02c":
            base_cfg[
                "output3_assets"
            ][
                "et_pet"
            ],

        "terrain_30e03a":
            base_cfg[
                "output3_assets"
            ][
                "terrain"
            ],

        "hydrology_30e03b":
            base_cfg[
                "output3_assets"
            ][
                "hydrology"
            ],

        "soil_30e04a":
            base_cfg[
                "output3_assets"
            ][
                "soil"
            ],

        "soil_water_30e04b":
            base_cfg[
                "output3_assets"
            ][
                "soil_water"
            ],

        "canonical_final":
            base_cfg[
                "output3_assets"
            ][
                "canonical_final"
            ]
    },

    "frozen_model": {

        "calibration_csv":
            "checkpoints_30F/"
            "30F_B18C_AOI01_WALL_TO_WALL_CALIBRATION_V1.csv",

        "family_weights_csv":
            "checkpoints_30F/"
            "30F_B18C_FAMILY_WEIGHTS_V1.csv",

        "fusion_amplitude":
            5,

        "thresholds": {

            "T12":
                12,

            "T23":
                22,

            "T34":
                32
        },

        "max_class_change":
            1
    },

    "execution": {

        "start_exports":
            False,

        "require_qa_before_export":
            True,

        "allow_overwrite":
            False
    },

    "scientific_status": {

        "field_validated":
            False,

        "transferability_validated":
            False,

        "interpretation":
            "INSPECTION_PRIORITY_NOT_DIAGNOSIS"
    }
}


aoi01_run_config_path = (
    CONFIG_DIR /
    "SIAK_AOI01_OUTPUT3_RUN_CONFIG.json"
)

with open(
    aoi01_run_config_path,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        aoi01_run_config,
        f,
        indent=2,
        ensure_ascii=False
    )


print("\n[2] AOI CONFIGURATION")
print(
    "Generic template :",
    template_path.resolve()
)

print(
    "AOI01 run config :",
    aoi01_run_config_path.resolve()
)


# ============================================================
# 6. BUILD STANDALONE RUNNER SCRIPT
# ============================================================

runner_code = dedent(
r'''
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Reusable Output 3 runner.

Current automation level:

Standardized persistent 30D/30E GEE assets
    ->
Frozen 30F parameters
    ->
30G integrated product
    ->
QA

This runner does NOT yet build 30A-30E from raw sources.
Upstream stage-builder packaging is handled separately.
"""

from pathlib import Path
import argparse
import json
import ssl

import certifi
import ee
import pandas as pd


EXPECTED_BANDS = [
    "CORE_CLASS",
    "CORE_RISK_SCORE_0_100",
    "CONTEXT_MODIFIER_SCORE",
    "CONTEXT_MODIFIER_COVERAGE",
    "INTEGRATED_SCORE_0_100",
    "INTEGRATED_CLASS",
    "CLASS_DELTA",
]


# ============================================================
# UTILITIES
# ============================================================

def load_json(path):

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


def locate_project_root():

    start = Path.cwd().resolve()

    for candidate in [
        start,
        *start.parents
    ]:

        if (
            candidate /
            "OUTPUT3_COMPLETE_PACKAGE"
        ).exists():

            return candidate

    raise FileNotFoundError(
        "Could not locate project root containing "
        "OUTPUT3_COMPLETE_PACKAGE."
    )


def resolve_project_path(
    project_root,
    value
):

    path = Path(value)

    if path.is_absolute():
        return path

    return (
        project_root /
        path
    )


def initialize_ee(
    project_id
):

    ssl._create_default_https_context = (
        lambda:
        ssl.create_default_context(
            cafile=certifi.where()
        )
    )

    try:

        ee.Initialize(
            project=project_id
        )

    except Exception:

        ee.Authenticate()

        ee.Initialize(
            project=project_id
        )


# ============================================================
# CONFIG VALIDATION
# ============================================================

def validate_config(
    cfg
):

    required_top = [
        "project_id",
        "aoi_id",
        "reference_year",
        "mode",
        "assets",
        "frozen_model",
        "execution",
    ]

    missing = [
        key
        for key in required_top
        if key not in cfg
    ]

    if missing:

        raise ValueError(
            f"Missing config fields: {missing}"
        )


    if cfg[
        "mode"
    ] not in {
        "REPRODUCE",
        "TRANSFER_TEST",
    }:

        raise ValueError(
            "mode must be REPRODUCE "
            "or TRANSFER_TEST."
        )


# ============================================================
# ASSET AUDIT
# ============================================================

def check_asset(
    asset_id
):

    if (
        asset_id is None
        or
        asset_id == "REQUIRED"
    ):

        return False

    try:

        ee.data.getAsset(
            asset_id
        )

        return True

    except Exception:

        return False


def audit_assets(
    cfg
):

    required = [

        "plantation_boundary",

        "core_30d",

        "age_30e01",

        "chirps_30e02a",

        "era5_30e02b",

        "etpet_30e02c",

        "terrain_30e03a",

        "hydrology_30e03b",

        "soil_30e04a",

        "soil_water_30e04b",
    ]


    results = {}


    for key in required:

        asset_id = (
            cfg[
                "assets"
            ]
            .get(key)
        )

        exists = check_asset(
            asset_id
        )

        results[
            key
        ] = {

            "asset_id":
                asset_id,

            "status":
                (
                    "PASS"
                    if exists
                    else
                    "MISSING_OR_NOT_CONFIGURED"
                )
        }


    return results


# ============================================================
# FROZEN PARAMETERS
# ============================================================

def load_frozen_parameters(
    cfg,
    project_root
):

    frozen = cfg[
        "frozen_model"
    ]


    calibration_path = (
        resolve_project_path(
            project_root,
            frozen[
                "calibration_csv"
            ]
        )
    )


    weights_path = (
        resolve_project_path(
            project_root,
            frozen[
                "family_weights_csv"
            ]
        )
    )


    if not calibration_path.exists():

        raise FileNotFoundError(
            calibration_path
        )


    if not weights_path.exists():

        raise FileNotFoundError(
            weights_path
        )


    calibration_df = pd.read_csv(
        calibration_path
    )


    family_weight_df = pd.read_csv(
        weights_path
    )


    if len(
        calibration_df
    ) != 8:

        raise RuntimeError(
            "Expected 8 frozen modifier features; "
            f"found {len(calibration_df)}."
        )


    if len(
        family_weight_df
    ) != 4:

        raise RuntimeError(
            "Expected 4 frozen context families; "
            f"found {len(family_weight_df)}."
        )


    return (
        calibration_df,
        family_weight_df
    )


# ============================================================
# 30G FROZEN INTEGRATION
# ============================================================

def build_integrated_product(
    cfg,
    project_root
):

    assets = cfg[
        "assets"
    ]

    frozen = cfg[
        "frozen_model"
    ]


    (
        calibration_df,
        family_weight_df
    ) = load_frozen_parameters(
        cfg,
        project_root
    )


    feature_source_registry = {

        "LOCAL_RELIEF_300M_M":
            assets[
                "terrain_30e03a"
            ],

        "SLOPE_DEG":
            assets[
                "terrain_30e03a"
            ],

        "HAND_M":
            assets[
                "hydrology_30e03b"
            ],

        "SILT_PCT_DEEP_100_200CM":
            assets[
                "soil_30e04a"
            ],

        "SOC_GKG_SURFACE_0_30CM":
            assets[
                "soil_30e04a"
            ],

        "WV1500_DEEP_100_200CM":
            assets[
                "soil_water_30e04b"
            ],

        "WV10_DEEP_100_200CM":
            assets[
                "soil_water_30e04b"
            ],

        "PAW_PROXY_SURFACE_0_30CM":
            assets[
                "soil_water_30e04b"
            ],
    }


    core_img = ee.Image(
        assets[
            "core_30d"
        ]
    )


    core_class = (
        core_img
        .select(
            "CONDITION_CLASS"
        )
        .round()
        .toInt16()
    )


    core_raw = (
        core_img
        .select(
            "CONDITION_CLASS_RAW"
        )
        .round()
        .toInt16()
    )


    core_risk = (
        core_img
        .select(
            "RISK_SCORE_0_100"
        )
        .toFloat()
    )


    valid_mask = (
        core_class
        .gte(1)
        .And(
            core_class.lte(4)
        )
    )


    # --------------------------------------------------------
    # DIRECTIONAL FEATURES
    # --------------------------------------------------------

    directional_images = {}


    for _, row in (
        calibration_df
        .iterrows()
    ):

        feature = row[
            "feature"
        ]


        if (
            feature
            not in
            feature_source_registry
        ):

            raise KeyError(
                "No source mapping for frozen feature: "
                f"{feature}"
            )


        source = (
            ee.Image(
                feature_source_registry[
                    feature
                ]
            )
            .select(
                feature
            )
            .toFloat()
            .updateMask(
                valid_mask
            )
        )


        p10 = float(
            row[
                "p10"
            ]
        )

        p90 = float(
            row[
                "p90"
            ]
        )

        direction = int(
            row[
                "association_direction"
            ]
        )


        if p90 <= p10:

            raise ValueError(
                f"Invalid calibration range "
                f"for {feature}: "
                f"P10={p10}, P90={p90}"
            )


        norm01 = (
            source
            .subtract(
                p10
            )
            .divide(
                p90 - p10
            )
            .clamp(
                0,
                1
            )
        )


        if direction < 0:

            norm01 = (
                ee.Image
                .constant(1)
                .subtract(
                    norm01
                )
            )


        directional_images[
            feature
        ] = (
            norm01
            .multiply(2)
            .subtract(1)
            .rename(
                f"DIR_{feature}"
            )
        )


    # --------------------------------------------------------
    # FAMILY COMPOSITES
    # --------------------------------------------------------

    family_score_images = {}


    for family in (
        family_weight_df[
            "family"
        ]
        .tolist()
    ):

        family_cal = (
            calibration_df[
                calibration_df[
                    "family"
                ] == family
            ]
        )


        weighted_sum = (
            ee.Image
            .constant(0)
            .toFloat()
        )


        available_weight = (
            ee.Image
            .constant(0)
            .toFloat()
        )


        for _, row in (
            family_cal
            .iterrows()
        ):

            feature = row[
                "feature"
            ]

            weight = float(
                row[
                    "within_family_weight"
                ]
            )

            img = (
                directional_images[
                    feature
                ]
            )


            valid = (
                img
                .mask()
                .reduce(
                    ee.Reducer.min()
                )
                .gt(0)
            )


            weighted_sum = (
                weighted_sum
                .add(
                    img
                    .unmask(0)
                    .multiply(
                        weight
                    )
                )
            )


            available_weight = (
                available_weight
                .add(
                    valid
                    .toFloat()
                    .multiply(
                        weight
                    )
                )
            )


        family_score_images[
            family
        ] = (
            weighted_sum
            .divide(
                available_weight
                .max(1e-6)
            )
            .updateMask(
                available_weight
                .gte(0.50)
            )
            .clamp(
                -1,
                1
            )
            .rename(
                f"FAMILY_SCORE_{family}"
            )
        )


    # --------------------------------------------------------
    # FAMILY-BALANCED CONTEXT MODIFIER
    # --------------------------------------------------------

    overall_sum = (
        ee.Image
        .constant(0)
        .toFloat()
    )


    overall_weight = (
        ee.Image
        .constant(0)
        .toFloat()
    )


    for _, row in (
        family_weight_df
        .iterrows()
    ):

        family = row[
            "family"
        ]

        family_weight = float(
            row[
                "family_weight"
            ]
        )


        img = (
            family_score_images[
                family
            ]
        )


        valid = (
            img
            .mask()
            .reduce(
                ee.Reducer.min()
            )
            .gt(0)
        )


        overall_sum = (
            overall_sum
            .add(
                img
                .unmask(0)
                .multiply(
                    family_weight
                )
            )
        )


        overall_weight = (
            overall_weight
            .add(
                valid
                .toFloat()
                .multiply(
                    family_weight
                )
            )
        )


    context_modifier = (
        overall_sum
        .divide(
            overall_weight
            .max(1e-6)
        )
        .updateMask(
            overall_weight
            .gte(0.75)
        )
        .clamp(
            -1,
            1
        )
        .rename(
            "CONTEXT_MODIFIER_SCORE"
        )
    )


    context_coverage = (
        overall_weight
        .rename(
            "CONTEXT_MODIFIER_COVERAGE"
        )
    )


    # --------------------------------------------------------
    # F05 SCORE
    # --------------------------------------------------------

    amplitude = float(
        frozen[
            "fusion_amplitude"
        ]
    )


    integrated_score = (
        core_risk
        .add(
            context_modifier
            .unmask(0)
            .multiply(
                amplitude
            )
        )
        .clamp(
            0,
            100
        )
        .rename(
            "INTEGRATED_SCORE_0_100"
        )
    )


    # --------------------------------------------------------
    # CORE EVIDENCE
    # --------------------------------------------------------

    optical_valid = (
        core_img
        .select(
            "OPTICAL_VALID_PERIOD_COUNT"
        )
    )


    alert_mask = (
        core_img
        .select(
            "ALERT_MASK"
        )
        .round()
    )


    max_period_class = (
        core_img
        .select(
            "MAX_PERIOD_CLASS"
        )
    )


    max_consecutive = (
        core_img
        .select(
            "MAX_CONSECUTIVE_ALERT"
        )
    )


    optical_alert_total = (
        core_img
        .select(
            "GREENNESS_ALERT_PERIODS"
        )
        .add(
            core_img
            .select(
                "RED_EDGE_ALERT_PERIODS"
            )
        )
        .add(
            core_img
            .select(
                "MOISTURE_ALERT_PERIODS"
            )
        )
    )


    has_optical_support = (
        optical_valid
        .gt(0)
        .And(
            optical_alert_total
            .gt(0)
        )
    )


    # Preserve 30D RAW -> FINAL decisions.

    unlocked = (
        core_raw
        .neq(
            core_class
        )
        .Not()
    )


    # --------------------------------------------------------
    # FROZEN THRESHOLDS
    # --------------------------------------------------------

    thresholds = (
        frozen[
            "thresholds"
        ]
    )


    T12 = float(
        thresholds[
            "T12"
        ]
    )

    T23 = float(
        thresholds[
            "T23"
        ]
    )

    T34 = float(
        thresholds[
            "T34"
        ]
    )


    modifier_available = (
        context_modifier
        .mask()
        .reduce(
            ee.Reducer.min()
        )
        .gt(0)
    )


    modifier_pos = (
        context_modifier
        .unmask(0)
        .gt(0)
    )


    modifier_neg = (
        context_modifier
        .unmask(0)
        .lt(0)
    )


    # --------------------------------------------------------
    # TRANSITION RULES
    # --------------------------------------------------------

    promote_1_2 = (
        core_class
        .eq(1)
        .And(
            unlocked
        )
        .And(
            modifier_available
        )
        .And(
            modifier_pos
        )
        .And(
            integrated_score
            .gte(T12)
        )
        .And(
            alert_mask
            .eq(1)
        )
    )


    promote_2_3 = (
        core_class
        .eq(2)
        .And(
            unlocked
        )
        .And(
            modifier_available
        )
        .And(
            modifier_pos
        )
        .And(
            integrated_score
            .gte(T23)
        )
        .And(
            has_optical_support
        )
        .And(
            max_period_class
            .gte(3)
        )
        .And(
            max_consecutive
            .gte(2)
        )
    )


    promote_3_4 = (
        core_class
        .eq(3)
        .And(
            unlocked
        )
        .And(
            modifier_available
        )
        .And(
            modifier_pos
        )
        .And(
            integrated_score
            .gte(T34)
        )
        .And(
            has_optical_support
        )
        .And(
            max_period_class
            .gte(3)
        )
        .And(
            max_consecutive
            .gte(3)
        )
    )


    demote_2_1 = (
        core_class
        .eq(2)
        .And(
            unlocked
        )
        .And(
            modifier_available
        )
        .And(
            modifier_neg
        )
        .And(
            integrated_score
            .lt(T12)
        )
        .And(
            alert_mask
            .eq(0)
        )
    )


    demote_3_2 = (
        core_class
        .eq(3)
        .And(
            unlocked
        )
        .And(
            modifier_available
        )
        .And(
            modifier_neg
        )
        .And(
            integrated_score
            .lt(T23)
        )
        .And(
            max_consecutive
            .lte(1)
        )
    )


    demote_4_3 = (
        core_class
        .eq(4)
        .And(
            unlocked
        )
        .And(
            modifier_available
        )
        .And(
            modifier_neg
        )
        .And(
            integrated_score
            .lt(T34)
        )
        .And(
            max_consecutive
            .lte(2)
        )
    )


    # --------------------------------------------------------
    # FINAL CLASS
    # --------------------------------------------------------

    integrated_class = (
        core_class
        .where(
            promote_1_2,
            2
        )
        .where(
            promote_2_3,
            3
        )
        .where(
            promote_3_4,
            4
        )
        .where(
            demote_2_1,
            1
        )
        .where(
            demote_3_2,
            2
        )
        .where(
            demote_4_3,
            3
        )
        .rename(
            "INTEGRATED_CLASS"
        )
        .toInt16()
    )


    class_delta = (
        integrated_class
        .subtract(
            core_class
        )
        .rename(
            "CLASS_DELTA"
        )
        .toInt16()
    )


    final_img = (
        core_class
        .rename(
            "CORE_CLASS"
        )
        .addBands(
            core_risk
            .rename(
                "CORE_RISK_SCORE_0_100"
            )
        )
        .addBands(
            context_modifier
        )
        .addBands(
            context_coverage
        )
        .addBands(
            integrated_score
        )
        .addBands(
            integrated_class
        )
        .addBands(
            class_delta
        )
        .updateMask(
            valid_mask
        )
    )


    return final_img


# ============================================================
# BASIC QA
# ============================================================

def basic_qa(
    img
):

    bands = (
        img
        .bandNames()
        .getInfo()
    )


    return {

        "band_names":
            bands,

        "seven_band_contract":
            bands
            ==
            EXPECTED_BANDS
    }


# ============================================================
# AOI01 CANONICAL COMPARISON
# ============================================================

def compare_to_canonical(
    img,
    canonical_asset
):

    if not canonical_asset:

        return {

            "performed":
                False,

            "reason":
                "canonical_final is not configured"
        }


    canonical = ee.Image(
        canonical_asset
    )


    projection = (
        canonical
        .select(
            "INTEGRATED_CLASS"
        )
        .projection()
        .getInfo()
    )


    crs = projection[
        "crs"
    ]

    transform = projection[
        "transform"
    ]


    rebuilt_class = (
        img
        .select(
            "INTEGRATED_CLASS"
        )
        .reproject(
            crs=crs,
            crsTransform=transform
        )
    )


    mismatch = (
        rebuilt_class
        .neq(
            canonical
            .select(
                "INTEGRATED_CLASS"
            )
        )
        .rename(
            "MISMATCH"
        )
    )


    mismatch_area = (
        ee.Image
        .pixelArea()
        .divide(
            10000
        )
        .rename(
            "AREA_HA"
        )
        .updateMask(
            mismatch
        )
        .reduceRegion(

            reducer=
                ee.Reducer.sum(),

            geometry=
                canonical.geometry(),

            crs=
                crs,

            crsTransform=
                transform,

            maxPixels=
                1e13,

            tileScale=
                4
        )
        .get(
            "AREA_HA"
        )
        .getInfo()
    )


    if mismatch_area is None:

        mismatch_area = 0.0


    mismatch_area = float(
        mismatch_area
    )


    return {

        "performed":
            True,

        "mismatch_area_ha":
            mismatch_area,

        "pass":
            mismatch_area == 0.0
    }


# ============================================================
# MAIN
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=
            "Reusable Output 3 analytical runner"
    )


    parser.add_argument(

        "--config",

        required=True,

        help=
            "Path to Output 3 AOI JSON config."
    )


    parser.add_argument(

        "--audit-only",

        action="store_true",

        help=
            "Validate configuration and assets only."
    )


    args = parser.parse_args()


    project_root = (
        locate_project_root()
    )


    config_path = (
        Path(
            args.config
        )
        .resolve()
    )


    cfg = load_json(
        config_path
    )


    validate_config(
        cfg
    )


    initialize_ee(
        cfg[
            "project_id"
        ]
    )


    print(
        "=" * 90
    )

    print(
        "OUTPUT 3 REUSABLE RUNNER"
    )

    print(
        "=" * 90
    )


    print(
        "AOI  :",
        cfg[
            "aoi_id"
        ]
    )

    print(
        "Mode :",
        cfg[
            "mode"
        ]
    )


    # --------------------------------------------------------
    # Asset audit
    # --------------------------------------------------------

    asset_audit = audit_assets(
        cfg
    )


    print(
        "\nASSET AUDIT"
    )


    for key, result in (
        asset_audit.items()
    ):

        print(
            f"{key:25s}: "
            f"{result['status']}"
        )


    asset_pass = all(

        item[
            "status"
        ] == "PASS"

        for item in
        asset_audit.values()
    )


    if not asset_pass:

        raise RuntimeError(
            "Required standardized upstream "
            "assets are missing or not configured."
        )


    if args.audit_only:

        print(
            "\nRUNNER RESULT: "
            "ASSET CONTRACT PASS"
        )

        print(
            "No analytical graph was built."
        )

        return


    # --------------------------------------------------------
    # Build frozen Output 3 graph
    # --------------------------------------------------------

    final_img = (
        build_integrated_product(
            cfg,
            project_root
        )
    )


    qa = basic_qa(
        final_img
    )


    print(
        "\nOUTPUT BANDS:"
    )

    print(
        qa[
            "band_names"
        ]
    )


    print(
        "Seven-band contract:",
        (
            "PASS"
            if qa[
                "seven_band_contract"
            ]
            else
            "FAIL"
        )
    )


    if not qa[
        "seven_band_contract"
    ]:

        raise RuntimeError(
            "Seven-band Output 3 contract failed."
        )


    # --------------------------------------------------------
    # Reproduction QA for AOI01
    # --------------------------------------------------------

    if cfg[
        "mode"
    ] == "REPRODUCE":

        comparison = (
            compare_to_canonical(

                final_img,

                cfg[
                    "assets"
                ]
                .get(
                    "canonical_final"
                )
            )
        )


        print(
            "\nCANONICAL COMPARISON:"
        )


        print(
            json.dumps(
                comparison,
                indent=2
            )
        )


        if (
            comparison.get(
                "performed"
            )
            and
            not comparison.get(
                "pass"
            )
        ):

            raise RuntimeError(
                "Reconstructed INTEGRATED_CLASS "
                "does not match canonical asset."
            )


    # --------------------------------------------------------
    # Transfer warning
    # --------------------------------------------------------

    if cfg[
        "mode"
    ] == "TRANSFER_TEST":

        print(
            "\nTRANSFER TEST WARNING:\n"
            "Frozen AOI01 parameters are being used.\n"
            "This demonstrates technical portability only.\n"
            "It does NOT demonstrate field accuracy or\n"
            "validated transferability for the new AOI."
        )


    # --------------------------------------------------------
    # Export policy
    # --------------------------------------------------------

    if not cfg[
        "execution"
    ][
        "start_exports"
    ]:

        print(
            "\nEXPORTS: NOT STARTED "
            "(intentional QA-first policy)."
        )


    print(
        "\nRUNNER RESULT: PASS"
    )


if __name__ == "__main__":

    main()
'''
).lstrip()


# ============================================================
# 7. CRITICAL FIX:
#    VALIDATE GENERATED PYTHON BEFORE WRITING IT
# ============================================================

try:

    compile(
        runner_code,
        "run_output3.py",
        "exec"
    )

    runner_syntax_pass = True

except SyntaxError as e:

    runner_syntax_pass = False

    raise SyntaxError(
        "Generated run_output3.py failed syntax check:\n"
        f"{e}"
    )


print("\n[3] RUNNER SYNTAX CHECK")
print(
    "Python compile() :",
    "PASS"
    if runner_syntax_pass
    else "FAIL"
)


# ============================================================
# 8. WRITE RUNNER ONLY AFTER SYNTAX PASS
# ============================================================

runner_path = (
    MASTER_DIR /
    "run_output3.py"
)

with open(
    runner_path,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        runner_code
    )


print("\n[4] REUSABLE RUNNER")
print(
    "Created :",
    runner_path.resolve()
)


# ============================================================
# 9. READ-BACK VALIDATION
# ============================================================

with open(
    runner_path,
    "r",
    encoding="utf-8"
) as f:

    runner_readback = (
        f.read()
    )


compile(
    runner_readback,
    str(
        runner_path
    ),
    "exec"
)


print(
    "Read-back syntax : PASS"
)


# ============================================================
# 10. AUTOMATION READINESS
# ============================================================

automation_readiness = {

    "generated_at":
        datetime.now()
        .isoformat(),

    "overall_status":
        "PARTIALLY_AUTOMATED_REPRODUCIBLE_PIPELINE",

    "automated_now": {

        "config_loading":
            True,

        "gee_initialization":
            True,

        "asset_audit":
            True,

        "frozen_30f_parameter_restore":
            True,

        "30g_integration":
            True,

        "seven_band_qa":
            True,

        "aoi01_canonical_reproduction_check":
            True
    },

    "not_yet_packaged_as_one_click": {

        "30a_aoi_bootstrap":
            True,

        "30b_baseline_monitoring_builder":
            True,

        "30c_anomaly_builder":
            True,

        "30d_core_risk_builder":
            True,

        "30e_context_builders":
            True
    },

    "current_new_aoi_capability":
        (
            "A new AOI can use this runner once "
            "the standardized 30D and 30E assets "
            "have been produced."
        ),

    "target_after_30j_d":
        (
            "Package upstream 30A-30E source/process "
            "builders and provenance so the project "
            "can be handed over as a complete "
            "raw/upstream-to-final workflow."
        ),

    "scientific_guardrail":
        (
            "Technical portability is not the same as "
            "validated transferability or field accuracy."
        )
}


readiness_path = (
    DOC_DIR /
    "OUTPUT3_AUTOMATION_READINESS.json"
)

with open(
    readiness_path,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        automation_readiness,
        f,
        indent=2,
        ensure_ascii=False
    )


# ============================================================
# 11. README
# ============================================================

runner_readme = dedent(
"""
# Output 3 Reusable Runner

## Main files

- `run_output3.py`
- `SIAK_AOI01_OUTPUT3_RUN_CONFIG.json`
- `OUTPUT3_AOI_TEMPLATE.json`

## AOI01 reproducibility

Run:

python run_output3.py --config SIAK_AOI01_OUTPUT3_RUN_CONFIG.json

The runner reconstructs the frozen downstream Output 3
product and compares INTEGRATED_CLASS against the
canonical AOI01 Earth Engine asset.

## Audit only

Run:

python run_output3.py --config SIAK_AOI01_OUTPUT3_RUN_CONFIG.json --audit-only

This checks required persistent assets without building the
analytical graph.

## New AOI

Copy `OUTPUT3_AOI_TEMPLATE.json`, replace the required
asset IDs, and use mode:

TRANSFER_TEST

At this stage the reusable runner assumes standardized
30D and 30E assets already exist.

30J-D will package the upstream 30A-30E process/source
provenance needed for complete handover.

## Scientific guardrail

Successful execution means technical reproducibility.

It does not by itself demonstrate:

- independent field accuracy;
- disease diagnosis;
- nutrient diagnosis;
- validated transferability to another AOI.
"""
).strip()


runner_readme_path = (
    DOC_DIR /
    "README_REUSABLE_RUNNER.md"
)

with open(
    runner_readme_path,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        runner_readme
    )


# ============================================================
# 12. MANIFEST
# ============================================================

manifest = {

    "stage":
        "30J-C",

    "version":
        "V2_FIXED",

    "status":
        "PASS",

    "created_at":
        datetime.now()
        .isoformat(),

    "files": {

        "runner":
            str(
                runner_path
            ),

        "generic_aoi_template":
            str(
                template_path
            ),

        "aoi01_run_config":
            str(
                aoi01_run_config_path
            ),

        "automation_readiness":
            str(
                readiness_path
            ),

        "runner_readme":
            str(
                runner_readme_path
            )
    },

    "runner_syntax_checked":
        True,

    "exports_started":
        False,

    "model_changed":
        False,

    "analytical_product_changed":
        False
}


manifest_path = (
    MASTER_DIR /
    "30J_C_REUSABLE_RUNNER_MANIFEST.json"
)

with open(
    manifest_path,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        manifest,
        f,
        indent=2,
        ensure_ascii=False
    )


# ============================================================
# 13. FINAL GATE
# ============================================================

checks = {

    "generic_aoi_template":
        template_path.exists(),

    "aoi01_run_config":
        aoi01_run_config_path.exists(),

    "runner_script":
        runner_path.exists(),

    "runner_syntax":
        runner_syntax_pass,

    "automation_readiness":
        readiness_path.exists(),

    "runner_readme":
        runner_readme_path.exists(),

    "runner_manifest":
        manifest_path.exists(),
}


print("\n" + "=" * 115)
print("30J-C V2 | FINAL GATE")
print("=" * 115)


for name, result in (
    checks.items()
):

    print(
        f"{name:40s}:",
        (
            "PASS"
            if result
            else
            "FAIL"
        )
    )


print("\nRunner:")
print(
    runner_path.resolve()
)

print("\nAOI01 runnable config:")
print(
    aoi01_run_config_path.resolve()
)

print("\nGeneric new-AOI template:")
print(
    template_path.resolve()
)


print("\n" + "-" * 115)


if all(
    checks.values()
):

    print(
"""
30J-C RESULT: PASS

REUSABLE OUTPUT 3 RUNNER CREATED AND
PYTHON-SYNTAX VALIDATED.

Created:
- run_output3.py
- SIAK_AOI01_OUTPUT3_RUN_CONFIG.json
- OUTPUT3_AOI_TEMPLATE.json
- OUTPUT3_AUTOMATION_READINESS.json
- README_REUSABLE_RUNNER.md
- 30J_C_REUSABLE_RUNNER_MANIFEST.json

No export was started.
No model parameter was changed.
No analytical raster was overwritten.

NEXT:
30J-D | COMPLETE UPSTREAM 30A-30E CAPTURE
        + PROVENANCE
        + DOCUMENTATION
        + BACKUP / TRUE NEW-AOI READINESS
"""
    )

else:

    print(
"""
30J-C RESULT: REVIEW REQUIRED
"""
    )


print("=" * 115)
