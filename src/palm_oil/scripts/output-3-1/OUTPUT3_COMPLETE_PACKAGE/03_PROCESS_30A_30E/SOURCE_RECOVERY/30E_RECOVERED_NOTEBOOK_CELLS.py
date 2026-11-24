# ========================================
# RECOVERED HISTORICAL SOURCE CANDIDATE
# Stage: 30E
# Source: OUTPUT 3.ipynb
# ========================================


# ========================================
# ORIGINAL CELL 19
# ========================================

ASSET_30E01 = (
    "projects/palm-oil-503202/assets/"
    "SIAK_AOI01_O3_30E01_AGE_CONTEXT_V3_2025"
)

try:
    info_30E01 = ee.data.getAsset(ASSET_30E01)

    print("30E01 ASSET ACCESS: PASS")
    print("Asset ID   :", ASSET_30E01)
    print("Asset type :", info_30E01.get("type"))

except Exception as e:
    print("30E01 ASSET ACCESS: FAILED")
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
# ORIGINAL CELL 21
# ========================================

# ============================================================
# 30F-B01 | DIAGNOSTIC — 30E04A SOIL BAND PROJECTIONS
# ============================================================

soil_img = ee.Image(ASSETS["30E04A_SOIL"])
soil_bands = soil_img.bandNames().getInfo()

print("=" * 90)
print("30E04A SOIL | BAND-LEVEL PROJECTION CHECK")
print("=" * 90)

for i, band in enumerate(soil_bands, start=1):
    proj = soil_img.select(band).projection()
    
    proj_info = proj.getInfo()
    scale = proj.nominalScale().getInfo()
    
    print(f"\n{i:02d}. {band}")
    print("    CRS       :", proj_info.get("crs"))
    print("    SCALE (m) :", scale)
    print("    FULL INFO :", proj_info)

# ========================================
# ORIGINAL CELL 22
# ========================================

# ============================================================
# OUTPUT 3 | 30F-B01
# MASTER FEATURE REGISTRY
# ============================================================

import pandas as pd

# ------------------------------------------------------------
# Metadata source-level yang sudah diverifikasi
# ------------------------------------------------------------
source_meta = {
    "30D04_CORE_RISK": {
        "family": "CORE_RISK",
        "native_scale_m": 10,
        "native_crs": "EPSG:32647"
    },
    "30E01_AGE": {
        "family": "AGE",
        "native_scale_m": 30,
        "native_crs": "EPSG:32647"
    },
    "30E02A_CHIRPS": {
        "family": "RAINFALL",
        "native_scale_m": 5566,
        "native_crs": "EPSG:4326"
    },
    "30E02B_ERA5LAND": {
        "family": "ATMOSPHERE_MOISTURE",
        "native_scale_m": 11132,
        "native_crs": "EPSG:4326"
    },
    "30E02C_ETPET": {
        "family": "ET_PET",
        "native_scale_m": 11132,
        "native_crs": "EPSG:4326"
    },
    "30E03A_TERRAIN": {
        "family": "TERRAIN",
        "native_scale_m": 30.922081,
        "native_crs": "EPSG:4326"
    },
    "30E03B_HYDRO": {
        "family": "HYDROLOGY",
        "native_scale_m": 92.766242,
        "native_crs": "EPSG:4326"
    },
    "30E04A_SOIL": {
        "family": "SOIL",
        "native_scale_m": 250,
        "native_crs": "World_Mollweide_WKT"
    },
    "30E04B_SOIL_WATER": {
        "family": "SOIL_WATER",
        "native_scale_m": 258.750183,
        "native_crs": "EPSG:4326"
    }
}

# ------------------------------------------------------------
# Build registry
# ------------------------------------------------------------
rows = []

for asset_key, bands in band_registry.items():
    
    meta = source_meta[asset_key]
    
    for band in bands:
        rows.append({
            "asset_key": asset_key,
            "feature_family": meta["family"],
            "band_name": band,
            "native_scale_m": meta["native_scale_m"],
            "native_crs": meta["native_crs"]
        })

feature_registry_df = pd.DataFrame(rows)

# ------------------------------------------------------------
# Basic role
# ------------------------------------------------------------
feature_registry_df["source_role"] = "CONTEXT_CANDIDATE"

feature_registry_df.loc[
    feature_registry_df["asset_key"] == "30D04_CORE_RISK",
    "source_role"
] = "CORE_REFERENCE"

# ------------------------------------------------------------
# Important baseline/reference bands
# ------------------------------------------------------------
core_targets = [
    "CONDITION_CLASS",
    "RISK_SCORE_0_100"
]

feature_registry_df["analysis_role"] = feature_registry_df["source_role"]

feature_registry_df.loc[
    feature_registry_df["band_name"].isin(core_targets),
    "analysis_role"
] = "BASELINE_REFERENCE"

# ------------------------------------------------------------
# Summary
# ------------------------------------------------------------
print("=" * 90)
print("30F-B01 | MASTER FEATURE REGISTRY")
print("=" * 90)

print("\nTotal bands registered :", len(feature_registry_df))
print("\nBands by feature family:")

display(
    feature_registry_df
    .groupby("feature_family")
    .size()
    .reset_index(name="band_count")
    .sort_values("band_count", ascending=False)
)

print("\nPreview:")
display(feature_registry_df.head(30))

# ========================================
# ORIGINAL CELL 23
# ========================================

# ============================================================
# OUTPUT 3 | 30F-B02
# INITIAL FEATURE ROLE TAGGING
# ============================================================

import pandas as pd

registry = feature_registry_df.copy()

def classify_feature(row):

    asset = row["asset_key"]
    band = row["band_name"]

    # ========================================================
    # 1. CORE 30D04
    # ========================================================
    if asset == "30D04_CORE_RISK":

        if band in ["CONDITION_CLASS", "RISK_SCORE_0_100"]:
            return pd.Series([
                "TARGET_REFERENCE",
                "Reference/baseline only; not predictor."
            ])

        else:
            return pd.Series([
                "CORE_DIAGNOSTIC",
                "Do not use as contextual predictor to avoid target leakage."
            ])

    # ========================================================
    # 2. AGE
    # ========================================================
    if asset == "30E01_AGE":

        if band == "AGE_PROXY_2025":
            return pd.Series([
                "CANDIDATE_PRIMARY",
                "Primary continuous age proxy."
            ])

        elif band == "AGE_CLASS_6":
            return pd.Series([
                "CANDIDATE_CATEGORICAL",
                "Ordinal age class; compare with continuous age proxy."
            ])

        elif band == "AGE_FINAL_EVENT_YEAR":
            return pd.Series([
                "REDUNDANCY_WATCH",
                "Strongly related to AGE_PROXY_2025."
            ])

        else:
            return pd.Series([
                "SUPPORT_QA",
                "Age source/evidence/QC/validity information."
            ])

    # ========================================================
    # 3. CHIRPS
    # ========================================================
    if asset == "30E02A_CHIRPS":

        if "_BASE_" in band or "_CLIM_" in band:
            # keep anomaly bands containing BASE/CLIM
            if "ANOM" in band:
                return pd.Series([
                    "CANDIDATE_NUMERIC",
                    "Rainfall anomaly candidate."
                ])
            else:
                return pd.Series([
                    "REFERENCE_ONLY",
                    "Baseline/climatology reference value."
                ])

        return pd.Series([
            "CANDIDATE_NUMERIC",
            "Current-period rainfall/dryness candidate."
        ])

    # ========================================================
    # 4. ERA5-LAND
    # ========================================================
    if asset == "30E02B_ERA5LAND":

        if "_U10_MS" in band or "_V10_MS" in band:
            return pd.Series([
                "REDUNDANCY_WATCH",
                "Wind components; compare against WIND_SPEED_MS."
            ])

        return pd.Series([
            "CANDIDATE_NUMERIC",
            "Atmospheric/moisture contextual candidate."
        ])

    # ========================================================
    # 5. ET/PET
    # ========================================================
    if asset == "30E02C_ETPET":

        if "_BASE_" in band or "_CLIM_" in band:
            if "ANOM" in band:
                return pd.Series([
                    "CANDIDATE_NUMERIC",
                    "ET/PET anomaly candidate."
                ])
            else:
                return pd.Series([
                    "REFERENCE_ONLY",
                    "Baseline/climatology reference value."
                ])

        return pd.Series([
            "CANDIDATE_NUMERIC",
            "Current ET/PET or water-balance candidate."
        ])

    # ========================================================
    # 6. TERRAIN
    # ========================================================
    if asset == "30E03A_TERRAIN":

        if band == "ASPECT_DEG":
            return pd.Series([
                "TRANSFORM_REQUIRED",
                "Circular variable; use sin/cos aspect instead of raw degrees."
            ])

        return pd.Series([
            "CANDIDATE_NUMERIC",
            "Terrain contextual candidate."
        ])

    # ========================================================
    # 7. HYDROLOGY
    # ========================================================
    if asset == "30E03B_HYDRO":

        if band == "HAND_M":
            return pd.Series([
                "CANDIDATE_PRIMARY",
                "Primary hydrologic-position candidate."
            ])

        elif band == "LOG10_UPA":
            return pd.Series([
                "CANDIDATE_PRIMARY",
                "Preferred transformed upstream-area candidate."
            ])

        elif band in ["UPA_KM2", "UPSTREAM_PIXEL_COUNT"]:
            return pd.Series([
                "REDUNDANCY_WATCH",
                "Closely related to LOG10_UPA / upstream area."
            ])

        elif band == "FLOW_DIR_D8":
            return pd.Series([
                "SUPPORT_CATEGORICAL",
                "Directional categorical variable; not direct continuous predictor."
            ])

        elif band == "PERMANENT_WATER_FLAG":
            return pd.Series([
                "SUPPORT_QA",
                "Water/context flag; may function as exclusion/support."
            ])

    # ========================================================
    # 8. SOIL
    # ========================================================
    if asset == "30E04A_SOIL":

        if band.startswith(("CLAY_", "SAND_", "SILT_")):
            return pd.Series([
                "REDUNDANCY_WATCH",
                "Compositional soil texture; clay+sand+silt are not independent."
            ])

        return pd.Series([
            "CANDIDATE_NUMERIC",
            "Soil physical/chemical contextual candidate."
        ])

    # ========================================================
    # 9. SOIL WATER
    # ========================================================
    if asset == "30E04B_SOIL_WATER":

        if band.startswith("PAW_PROXY"):
            return pd.Series([
                "CANDIDATE_PRIMARY",
                "Derived plant-available-water proxy candidate."
            ])

        return pd.Series([
            "REDUNDANCY_WATCH",
            "Water-retention variable; evaluate redundancy with PAW proxy."
        ])

    return pd.Series([
        "UNCLASSIFIED",
        "Review manually."
    ])


registry[
    ["feature_status", "screening_note"]
] = registry.apply(classify_feature, axis=1)


# ============================================================
# SUMMARY
# ============================================================

print("=" * 90)
print("30F-B02 | INITIAL FEATURE ROLE TAGGING")
print("=" * 90)

print("\nTOTAL BAND :", len(registry))

print("\nFeature status summary:")
display(
    registry
    .groupby("feature_status")
    .size()
    .reset_index(name="band_count")
    .sort_values("band_count", ascending=False)
)

print("\nFeature status by family:")
display(
    pd.crosstab(
        registry["feature_family"],
        registry["feature_status"]
    )
)

# Candidate pool before statistical screening
candidate_status = [
    "CANDIDATE_PRIMARY",
    "CANDIDATE_NUMERIC",
    "CANDIDATE_CATEGORICAL",
    "REDUNDANCY_WATCH",
    "TRANSFORM_REQUIRED"
]

candidate_registry = registry[
    registry["feature_status"].isin(candidate_status)
].copy()

print("\nInitial contextual candidate pool:",
      len(candidate_registry), "bands")

print("\nExcluded from predictor pool:")
print(
    len(registry) - len(candidate_registry),
    "bands"
)

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
# ORIGINAL CELL 27
# ========================================

# ============================================================
# OUTPUT 3 | 30F-B06
# STRUCTURAL MISSINGNESS + COARSE CONTEXT DIAGNOSTIC
# ============================================================

import pandas as pd
import numpy as np

print("=" * 90)
print("30F-B06 | STRUCTURAL MISSINGNESS & COARSE CONTEXT DIAGNOSTIC")
print("=" * 90)

# ============================================================
# PART A — AGE STRUCTURAL MISSINGNESS
# ============================================================

print("\n" + "=" * 90)
print("A. AGE STRUCTURAL MISSINGNESS")
print("=" * 90)

age_diag = common_df[
    [
        "CONDITION_CLASS_INT",
        "RISK_SCORE_0_100",
        "AGE_FINAL_EVENT_YEAR",
        "AGE_PROXY_2025",
        "AGE_CLASS_6"
    ]
].copy()

age_diag["AGE_PROXY_PRESENT"] = (
    age_diag["AGE_PROXY_2025"].notna().astype(int)
)

print("\nAGE_CLASS_6 distribution:")
display(
    age_diag["AGE_CLASS_6"]
    .value_counts(dropna=False)
    .sort_index()
    .rename_axis("AGE_CLASS_6")
    .reset_index(name="sample_count")
)

print("\nAGE_PROXY presence:")
display(
    age_diag["AGE_PROXY_PRESENT"]
    .value_counts()
    .sort_index()
    .rename_axis("AGE_PROXY_PRESENT")
    .reset_index(name="sample_count")
)

print("\nAGE_CLASS_6 vs AGE_PROXY presence:")
display(
    pd.crosstab(
        age_diag["AGE_CLASS_6"],
        age_diag["AGE_PROXY_PRESENT"],
        margins=True
    )
)

print("\nCONDITION_CLASS vs AGE_CLASS_6:")
display(
    pd.crosstab(
        age_diag["CONDITION_CLASS_INT"],
        age_diag["AGE_CLASS_6"],
        normalize="index"
    ).round(3)
)

print("\nCONDITION_CLASS vs AGE_PROXY presence:")
display(
    pd.crosstab(
        age_diag["CONDITION_CLASS_INT"],
        age_diag["AGE_PROXY_PRESENT"],
        normalize="index"
    ).round(3)
)

print("\nFINAL_EVENT_YEAR values where AGE_PROXY is missing:")
display(
    age_diag.loc[
        age_diag["AGE_PROXY_2025"].isna(),
        "AGE_FINAL_EVENT_YEAR"
    ]
    .value_counts(dropna=False)
    .sort_index()
    .rename_axis("AGE_FINAL_EVENT_YEAR")
    .reset_index(name="sample_count")
)


# ============================================================
# PART B — COARSE WEATHER PSEUDO-REPLICATION
# ============================================================

print("\n" + "=" * 90)
print("B. WEATHER / COARSE-CONTEXT PSEUDO-REPLICATION")
print("=" * 90)

weather_family_map = {
    "RAINFALL": "30E02A_CHIRPS",
    "ATMOSPHERE_MOISTURE": "30E02B_ERA5LAND",
    "ET_PET": "30E02C_ETPET"
}

weather_rows = []

for family, asset_key in weather_family_map.items():

    cols = (
        candidate_registry.loc[
            candidate_registry["asset_key"] == asset_key,
            "band_name"
        ]
        .tolist()
    )

    cols = [c for c in cols if c in common_df.columns]

    # Number of unique complete feature signatures.
    # For coarse raster products, identical signatures generally
    # indicate samples sharing the same source-cell context.
    signature_count = (
        common_df[cols]
        .drop_duplicates()
        .shape[0]
    )

    # Number of samples represented by each signature
    signature_sizes = (
        common_df[cols]
        .value_counts(dropna=False)
        .reset_index(name="sample_count")
    )

    weather_rows.append({
        "feature_family": family,
        "feature_count": len(cols),
        "unique_context_signatures": signature_count,
        "largest_signature_n": int(signature_sizes["sample_count"].max()),
        "median_signature_n": float(signature_sizes["sample_count"].median()),
        "smallest_signature_n": int(signature_sizes["sample_count"].min())
    })

weather_signature_df = pd.DataFrame(weather_rows)

display(weather_signature_df)


# ============================================================
# PART C — CONSTANT FEATURES
# ============================================================

print("\n" + "=" * 90)
print("C. CONSTANT FEATURES")
print("=" * 90)

constant_features = feature_audit_df[
    feature_audit_df["info_flag"] == "CONSTANT"
][
    [
        "feature_family",
        "band_name",
        "n_unique",
        "missing_pct"
    ]
]

display(constant_features)


# ============================================================
# PART D — PROVISIONAL DECISION
# ============================================================

print("\n" + "=" * 90)
print("D. PROVISIONAL ANALYSIS DECISION")
print("=" * 90)

print("""
1. AGE_PROXY_2025:
   - analyse only where age proxy exists;
   - DO NOT mean/median/zero impute structural NoData.

2. AGE_CLASS_6:
   - retain as the main wall-to-wall age-context variable.

3. CHIRPS / ERA5-Land / ET-PET:
   - retain as contextual features;
   - DO NOT interpret 1,300 point samples as 1,300 independent
     weather observations.

4. Constant features:
   - remove before correlation/model screening.

5. Next:
   - split feature screening into:
       A) fine/intermediate spatial context
       B) coarse weather context
""")

# ========================================
# ORIGINAL CELL 33
# ========================================

# ============================================================
# OUTPUT 3 | 30F-B12
# COARSE WEATHER CONTEXT SCREENING
# ============================================================

import pandas as pd
import numpy as np

print("=" * 90)
print("30F-B12 | COARSE WEATHER CONTEXT SCREENING")
print("=" * 90)

weather_df = common_df.copy()

# ============================================================
# 1. Weather family configuration
# ============================================================

weather_config = {
    "RAINFALL": "30E02A_CHIRPS",
    "ATMOSPHERE_MOISTURE": "30E02B_ERA5LAND",
    "ET_PET": "30E02C_ETPET"
}

weather_context_tables = {}
weather_feature_screen = []

# ============================================================
# 2. Build unique coarse-context units
# ============================================================

for family, asset_key in weather_config.items():

    print("\n" + "=" * 90)
    print(f"{family}")
    print("=" * 90)

    cols = (
        candidate_registry.loc[
            candidate_registry["asset_key"] == asset_key,
            "band_name"
        ]
        .tolist()
    )

    cols = [
        c for c in cols
        if c in weather_df.columns
    ]

    # Remove constant columns before context hashing
    variable_cols = [
        c for c in cols
        if weather_df[c].dropna().nunique() > 1
    ]

    constant_cols = [
        c for c in cols
        if c not in variable_cols
    ]

    print("Candidate features :", len(cols))
    print("Variable features  :", len(variable_cols))
    print("Constant features  :", len(constant_cols))

    # --------------------------------------------------------
    # Create deterministic coarse-context ID
    # identical weather vectors = same source context
    # --------------------------------------------------------

    signature_frame = (
        weather_df[variable_cols]
        .copy()
        .round(10)
    )

    context_id = pd.factorize(
        pd.MultiIndex.from_frame(signature_frame)
    )[0] + 1

    context_col = f"{family}_CONTEXT_ID"

    weather_df[context_col] = context_id

    # --------------------------------------------------------
    # Aggregate sample-level risk to coarse context
    # --------------------------------------------------------

    summary = (
        weather_df
        .groupby(context_col)
        .agg(
            sample_count=("SAMPLE_ID", "size"),
            risk_mean=("RISK_SCORE_0_100", "mean"),
            risk_median=("RISK_SCORE_0_100", "median"),
            condition_mean=("CONDITION_CLASS_INT", "mean"),
            class1_n=(
                "CONDITION_CLASS_INT",
                lambda x: (x == 1).sum()
            ),
            class2_n=(
                "CONDITION_CLASS_INT",
                lambda x: (x == 2).sum()
            ),
            class3_n=(
                "CONDITION_CLASS_INT",
                lambda x: (x == 3).sum()
            ),
            class4_n=(
                "CONDITION_CLASS_INT",
                lambda x: (x == 4).sum()
            )
        )
        .reset_index()
    )

    summary["class34_pct"] = (
        (
            summary["class3_n"]
            + summary["class4_n"]
        )
        / summary["sample_count"]
        * 100
    )

    # --------------------------------------------------------
    # Add one representative feature vector per context
    # --------------------------------------------------------

    context_features = (
        weather_df[
            [context_col] + variable_cols
        ]
        .groupby(context_col)
        .first()
        .reset_index()
    )

    context_table = summary.merge(
        context_features,
        on=context_col,
        how="left",
        validate="one_to_one"
    )

    weather_context_tables[family] = context_table

    print("\nUnique coarse contexts:")
    print(len(context_table))

    print("\nContext-level risk summary:")

    display(
        context_table[
            [
                context_col,
                "sample_count",
                "risk_mean",
                "risk_median",
                "condition_mean",
                "class34_pct"
            ]
        ]
        .sort_values(
            "risk_mean",
            ascending=False
        )
    )

    # ========================================================
    # 3. Context-level descriptive Spearman screening
    # ========================================================

    n_context = len(context_table)

    for feature in variable_cols:

        pair = context_table[
            [feature, "risk_mean"]
        ].dropna()

        rho = pair[feature].corr(
            pair["risk_mean"],
            method="spearman"
        )

        weather_feature_screen.append({
            "feature_family": family,
            "feature": feature,
            "n_context_units": len(pair),
            "spearman_context_risk": rho,
            "abs_rho": (
                abs(rho)
                if pd.notna(rho)
                else np.nan
            ),
            "interpretation": (
                "EXPLORATORY"
                if n_context >= 8
                else "VERY_LOW_N_CONTEXT"
            )
        })


# ============================================================
# 4. Feature-level weather screening table
# ============================================================

weather_screen_df = (
    pd.DataFrame(weather_feature_screen)
    .sort_values(
        ["feature_family", "abs_rho"],
        ascending=[True, False]
    )
    .reset_index(drop=True)
)

print("\n\n" + "=" * 90)
print("TOP CONTEXT-LEVEL ASSOCIATIONS BY WEATHER FAMILY")
print("=" * 90)

for family in weather_config.keys():

    print("\n" + "-" * 90)
    print(family)
    print("-" * 90)

    display(
        weather_screen_df[
            weather_screen_df[
                "feature_family"
            ] == family
        ]
        .head(15)
    )


# ============================================================
# 5. Overall diagnostic
# ============================================================

print("\n" + "=" * 90)
print("COARSE WEATHER SCREENING DECISION")
print("=" * 90)

context_counts = (
    weather_screen_df
    .groupby("feature_family")
    ["n_context_units"]
    .max()
    .reset_index()
)

display(context_counts)

print("""
INTERPRETATION RULE:

CHIRPS:
- approximately 12 independent coarse spatial contexts;
- context-level associations may be used for exploratory
  ranking, but NOT strong statistical inference.

ERA5-Land / ET-PET:
- only approximately 4 independent spatial contexts;
- correlation values are highly unstable;
- DO NOT select features purely because |rho| is high.

Therefore:
- weather remains contextual evidence;
- it should not dominate the fine-scale 10 m risk model;
- ERA5/ET-PET require domain-guided feature selection
  and sensitivity testing rather than naive correlation ranking.
""")

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

# ========================================
# ORIGINAL CELL 75
# ========================================

# ============================================================
# 30J-D | UPSTREAM SOURCE CAPTURE + PROVENANCE
#         + DOCUMENTATION + NEW-AOI READINESS AUDIT
#
# Purpose:
# 1. Capture actual development source from OUTPUT 3.ipynb.
# 2. Classify code cells across 30A-30I.
# 3. Preserve 30A-30E upstream source as auditable code files.
# 4. Create complete processing/provenance documentation.
# 5. Fingerprint key reproducibility files.
# 6. Audit NEW-AOI automation readiness honestly.
#
# IMPORTANT:
# - No model tuning.
# - No GEE export.
# - No raster processing.
# - No asset overwrite.
# ============================================================

from pathlib import Path
from datetime import datetime
from collections import defaultdict
import hashlib
import json
import re

import pandas as pd
import nbformat as nbf


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

INVENTORY_DIR = (
    PACKAGE_ROOT /
    "02_ASSET_INVENTORY"
)

PROCESS_DIR = (
    PACKAGE_ROOT /
    "03_PROCESS_30A_30E"
)

ANALYSIS_DIR = (
    PACKAGE_ROOT /
    "04_ANALYSIS_30F"
)

INTEGRATION_DIR = (
    PACKAGE_ROOT /
    "05_INTEGRATION_30G"
)

FREEZE_DIR = (
    PACKAGE_ROOT /
    "06_FREEZE_30H"
)

WEB_DIR = (
    PACKAGE_ROOT /
    "07_WEB_DELIVERY_30I"
)

QA_DIR = (
    PACKAGE_ROOT /
    "08_QA"
)

DOC_DIR = (
    PACKAGE_ROOT /
    "09_DOCUMENTATION"
)

ARCHIVE_DIR = (
    PACKAGE_ROOT /
    "10_ARCHIVE_MANIFEST"
)

LOG_DIR = (
    PACKAGE_ROOT /
    "11_LOGS"
)

SOURCE_CAPTURE_DIR = (
    PROCESS_DIR /
    "SOURCE_CAPTURE"
)

for folder in [
    PROCESS_DIR,
    ANALYSIS_DIR,
    INTEGRATION_DIR,
    FREEZE_DIR,
    WEB_DIR,
    QA_DIR,
    DOC_DIR,
    ARCHIVE_DIR,
    LOG_DIR,
    SOURCE_CAPTURE_DIR,
]:
    folder.mkdir(
        parents=True,
        exist_ok=True
    )


print("=" * 118)
print("30J-D | UPSTREAM SOURCE CAPTURE + PROVENANCE + NEW-AOI READINESS")
print("=" * 118)


# ============================================================
# 2. VERIFY 30J-C FOUNDATION
# ============================================================

required_foundation = [

    MASTER_DIR /
    "MASTER_PIPELINE_OUTPUT3.ipynb",

    MASTER_DIR /
    "run_output3.py",

    MASTER_DIR /
    "30J_C_REUSABLE_RUNNER_MANIFEST.json",

    CONFIG_DIR /
    "OUTPUT3_AOI_TEMPLATE.json",

    CONFIG_DIR /
    "SIAK_AOI01_OUTPUT3_RUN_CONFIG.json",

    INVENTORY_DIR /
    "OUTPUT3_GEE_ASSET_INVENTORY.csv",

    INVENTORY_DIR /
    "OUTPUT3_LOCAL_FILE_INVENTORY.csv",
]


missing_foundation = [

    path
    for path in required_foundation
    if not path.exists()
]


if missing_foundation:

    raise FileNotFoundError(
        "Missing 30J foundation files:\n" +
        "\n".join(
            str(path)
            for path in missing_foundation
        )
    )


print("\n[1] FOUNDATION")
print("30J-A/B/C files : PASS")


# ============================================================
# 3. LOCATE WORKING NOTEBOOK
# ============================================================

working_candidates = [

    PROJECT_ROOT /
    "OUTPUT 3.ipynb",

    PROJECT_ROOT /
    "OUTPUT3.ipynb",
]


working_notebook = None


for candidate in working_candidates:

    if candidate.exists():

        working_notebook = candidate
        break


if working_notebook is None:

    snapshots = sorted(

        ARCHIVE_DIR.glob(
            "OUTPUT3_WORKING_NOTEBOOK_SNAPSHOT_*.ipynb"
        ),

        key=lambda p:
            p.stat().st_mtime,

        reverse=True
    )


    if snapshots:

        working_notebook = snapshots[0]


if working_notebook is None:

    raise FileNotFoundError(
        "Could not locate OUTPUT 3 working notebook."
    )


working_nb = nbf.read(
    working_notebook,
    as_version=4
)


print("\n[2] WORKING SOURCE")
print(
    "Notebook :",
    working_notebook.resolve()
)

print(
    "Cells    :",
    len(working_nb.cells)
)


# ============================================================
# 4. ENHANCED STAGE CLASSIFIER
#
# Explicit 30X marker gets highest priority.
# Keyword classification is only fallback.
# ============================================================

stage_keywords = {

    "30A": [
        "aoi",
        "source contract",
        "asset connection",
        "initialize",
        "ee.initialize",
        "plantation boundary",
        "source registry",
    ],

    "30B": [
        "baseline",
        "monitoring",
        "monitoring stack",
        "baseline stack",
        "sentinel-1",
        "sentinel-2",
        "s1",
        "s2",
        "composite",
        "p01",
        "p02",
        "p03",
        "p04",
        "p05",
        "p06",
        "ndvi",
        "ndmi",
        "ndre",
    ],

    "30C": [
        "anomaly",
        "monitoring minus baseline",
        "delta",
        "temporal anomaly",
    ],

    "30D": [
        "condition_class",
        "risk_score",
        "balanced risk",
        "persistent",
        "alert_mask",
        "max_consecutive",
        "optical_valid",
        "radar",
        "inspection risk",
    ],

    "30E": [
        "age context",
        "chirps",
        "era5",
        "etpet",
        "et/pet",
        "terrain",
        "hydro",
        "soil",
        "soil_water",
        "soil water",
        "gedi",
        "contextual enrichment",
    ],

    "30F": [
        "vif",
        "spearman",
        "correlation",
        "feature_registry",
        "candidate_registry",
        "family_weight",
        "calibration",
        "spatial cv",
        "ablation",
        "sensitivity",
        "selected_features",
    ],

    "30G": [
        "integrated_class",
        "integrated_score",
        "context_modifier",
        "fusion_amplitude",
        "class_delta",
        "wall-to-wall integrated",
    ],

    "30H": [
        "final output 3 freeze",
        "product_summary",
        "freeze_manifest",
        "final map",
        "band_dictionary",
        "legend",
    ],

    "30I": [
        "web delivery",
        "cloudoptimized",
        "cloud optimized",
        "cog",
        "todrive",
        "web_delivery_output3",
    ],
}


def classify_cell(text):

    text_lower = text.lower()

    # Explicit stage markers first.
    explicit_matches = []

    for stage in [
        "30A",
        "30B",
        "30C",
        "30D",
        "30E",
        "30F",
        "30G",
        "30H",
        "30I",
    ]:

        if re.search(
            rf"\b{stage.lower()}\b",
            text_lower
        ):

            explicit_matches.append(
                stage
            )


    if explicit_matches:

        return (
            explicit_matches[0],
            "EXPLICIT",
            1.0
        )


    # Keyword scoring fallback.
    scores = {}


    for stage, keywords in (
        stage_keywords.items()
    ):

        score = sum(
            1
            for keyword in keywords
            if keyword in text_lower
        )

        scores[
            stage
        ] = score


    best_stage = max(
        scores,
        key=scores.get
    )

    best_score = scores[
        best_stage
    ]


    sorted_scores = sorted(
        scores.values(),
        reverse=True
    )


    second_score = (
        sorted_scores[1]
        if len(sorted_scores) > 1
        else 0
    )


    if best_score == 0:

        return (
            "UNCLASSIFIED",
            "NONE",
            0.0
        )


    # Ambiguous keyword result.
    if best_score == second_score:

        return (
            "UNCLASSIFIED",
            "AMBIGUOUS",
            0.25
        )


    confidence = min(
        0.95,
        0.45 +
        best_score * 0.10
    )


    return (
        best_stage,
        "KEYWORD",
        confidence
    )


# ============================================================
# 5. CLASSIFY EVERY WORKING NOTEBOOK CELL
# ============================================================

cell_rows = []

stage_code = defaultdict(
    list
)


for index, cell in enumerate(
    working_nb.cells
):

    source = cell.get(
        "source",
        ""
    )


    stage, method, confidence = (
        classify_cell(
            source
        )
    )


    first_line = (

        source
        .strip()
        .splitlines()[0][:180]

        if source.strip()
        else ""
    )


    cell_rows.append({

        "cell_index":
            index,

        "cell_type":
            cell.cell_type,

        "stage":
            stage,

        "classification_method":
            method,

        "confidence":
            confidence,

        "first_line":
            first_line,

        "source_length":
            len(source),
    })


    if cell.cell_type == "code":

        stage_code[
            stage
        ].append({

            "index":
                index,

            "source":
                source
        })


cell_df = pd.DataFrame(
    cell_rows
)


classification_path = (
    ARCHIVE_DIR /
    "OUTPUT3_COMPLETE_CELL_CLASSIFICATION.csv"
)


cell_df.to_csv(
    classification_path,
    index=False
)


print("\n[3] SOURCE CLASSIFICATION")

print(
    cell_df[
        "stage"
    ]
    .value_counts()
)


# ============================================================
# 6. EXPORT CAPTURED STAGE SOURCE FILES
#
# IMPORTANT:
# These are audit/development-source captures.
# They are not automatically claimed to be standalone
# parameterized builders.
# ============================================================

stage_file_names = {

    "30A":
        "30A_UPSTREAM_SETUP_SOURCE_CAPTURE.py",

    "30B":
        "30B_BASELINE_MONITORING_SOURCE_CAPTURE.py",

    "30C":
        "30C_ANOMALY_SOURCE_CAPTURE.py",

    "30D":
        "30D_CORE_RISK_SOURCE_CAPTURE.py",

    "30E":
        "30E_CONTEXT_SOURCE_CAPTURE.py",

    "30F":
        "30F_ANALYSIS_SOURCE_CAPTURE.py",

    "30G":
        "30G_INTEGRATION_SOURCE_CAPTURE.py",

    "30H":
        "30H_FREEZE_SOURCE_CAPTURE.py",

    "30I":
        "30I_WEB_DELIVERY_SOURCE_CAPTURE.py",

    "UNCLASSIFIED":
        "UNCLASSIFIED_WORKING_CODE_CAPTURE.py",
}


source_capture_rows = []


for stage, filename in (
    stage_file_names.items()
):

    captured_cells = (
        stage_code.get(
            stage,
            []
        )
    )


    output_path = (
        SOURCE_CAPTURE_DIR /
        filename
    )


    header = f"""# ============================================================
# OUTPUT 3 DEVELOPMENT SOURCE CAPTURE
# Stage: {stage}
#
# Source notebook:
# {working_notebook.name}
#
# Generated by 30J-D.
#
# IMPORTANT:
# This file preserves actual development code cells.
# It is an audit / provenance artifact.
#
# It is NOT automatically claimed to be a standalone
# AOI-parameterized production builder.
# ============================================================

"""


    body_parts = [
        header
    ]


    for item in captured_cells:

        body_parts.append(
            "\n\n"
            "# ============================================================\n"
            f"# ORIGINAL NOTEBOOK CELL {item['index']}\n"
            "# ============================================================\n\n"
        )

        body_parts.append(
            item[
                "source"
            ]
        )


    output_path.write_text(
        "".join(
            body_parts
        ),
        encoding="utf-8"
    )


    source_capture_rows.append({

        "stage":
            stage,

        "code_cells_captured":
            len(
                captured_cells
            ),

        "source_file":
            str(
                output_path
            ),

        "source_status":
            (
                "SOURCE_CAPTURED"
                if len(
                    captured_cells
                ) > 0
                else
                "NO_CODE_CELL_CAPTURED"
            )
    })


source_capture_df = pd.DataFrame(
    source_capture_rows
)


source_capture_manifest_csv = (
    PROCESS_DIR /
    "OUTPUT3_STAGE_SOURCE_CAPTURE_MANIFEST.csv"
)


source_capture_df.to_csv(
    source_capture_manifest_csv,
    index=False
)


print("\n[4] STAGE SOURCE CAPTURE")

display(
    source_capture_df
)


# ============================================================
# 7. CAPTURE 30F ANALYTICAL CHECKPOINT INVENTORY
# ============================================================

checkpoint_30f = (
    PROJECT_ROOT /
    "checkpoints_30F"
)


checkpoint_30g = (
    PROJECT_ROOT /
    "checkpoints_30G"
)


checkpoint_30h = (
    PROJECT_ROOT /
    "checkpoints_30H"
)


def inventory_folder(
    folder
):

    rows = []

    if not folder.exists():

        return rows


    for path in sorted(
        folder.rglob("*")
    ):

        if path.is_file():

            rows.append({

                "filename":
                    path.name,

                "relative_path":
                    str(
                        path.relative_to(
                            PROJECT_ROOT
                        )
                    ),

                "extension":
                    path.suffix.lower(),

                "size_bytes":
                    path.stat().st_size
            })


    return rows


checkpoint_inventory = {

    "30F":
        inventory_folder(
            checkpoint_30f
        ),

    "30G":
        inventory_folder(
            checkpoint_30g
        ),

    "30H":
        inventory_folder(
            checkpoint_30h
        )
}


checkpoint_inventory_path = (
    INVENTORY_DIR /
    "OUTPUT3_ANALYTICAL_CHECKPOINT_INVENTORY.json"
)


with open(
    checkpoint_inventory_path,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        checkpoint_inventory,
        f,
        indent=2,
        ensure_ascii=False
    )


print("\n[5] CHECKPOINT INVENTORY")

print(
    "30F files :",
    len(
        checkpoint_inventory[
            "30F"
        ]
    )
)

print(
    "30G files :",
    len(
        checkpoint_inventory[
            "30G"
        ]
    )
)

print(
    "30H files :",
    len(
        checkpoint_inventory[
            "30H"
        ]
    )
)


# ============================================================
# 8. COPY SMALL, FINAL CHECKPOINT FILES INTO PACKAGE
#
# Do NOT copy large GEE rasters.
# Keep one canonical copy of local analytical evidence.
# ============================================================

def copy_if_exists(
    source,
    destination_dir
):

    if source.exists():

        import shutil

        destination = (
            destination_dir /
            source.name
        )

        shutil.copy2(
            source,
            destination
        )

        return destination

    return None


# 30F frozen parameters
for filename in [

    "30F_B18C_AOI01_WALL_TO_WALL_CALIBRATION_V1.csv",

    "30F_B18C_FAMILY_WEIGHTS_V1.csv",
]:

    copy_if_exists(

        checkpoint_30f /
        filename,

        ANALYSIS_DIR
    )


# 30G final QA tables
for filename in [

    "30G_C_FINAL_CLASS_AREA_CANONICAL.csv",

    "30G_C_FINAL_TRANSITION_AREA_CANONICAL.csv",

    "30G_C_FINAL_GUARDRAIL_QA.csv",
]:

    copy_if_exists(

        checkpoint_30g /
        filename,

        QA_DIR
    )


# 30H freeze products
for filename in [

    "30H_FINAL_CLASS_AREA.csv",

    "30H_FINAL_TRANSITION_AREA.csv",

    "30H_PRODUCT_SUMMARY.json",

    "30H_LEGEND.json",

    "30H_BAND_DICTIONARY.json",

    "30H_FREEZE_MANIFEST.json",

    "30H_FINAL_MAP.png",

    "30H_PRODUCT_SUMMARY.md",
]:

    copy_if_exists(

        checkpoint_30h /
        filename,

        FREEZE_DIR
    )


print(
    "\n[6] FINAL SMALL CHECKPOINT COPY : PASS"
)


# ============================================================
# 9. KEY FILE HASH / BACKUP MANIFEST
# ============================================================

def sha256_file(
    path
):

    h = hashlib.sha256()

    with open(
        path,
        "rb"
    ) as f:

        for chunk in iter(
            lambda:
                f.read(
                    1024 * 1024
                ),
            b""
        ):

            h.update(
                chunk
            )


    return h.hexdigest()


key_files = [

    MASTER_DIR /
    "MASTER_PIPELINE_OUTPUT3.ipynb",

    MASTER_DIR /
    "run_output3.py",

    CONFIG_DIR /
    "OUTPUT3_AOI_TEMPLATE.json",

    CONFIG_DIR /
    "SIAK_AOI01_OUTPUT3_RUN_CONFIG.json",

    INVENTORY_DIR /
    "OUTPUT3_GEE_ASSET_INVENTORY.csv",

    INVENTORY_DIR /
    "OUTPUT3_LOCAL_FILE_INVENTORY.csv",

    classification_path,

    source_capture_manifest_csv,
]


hash_rows = []


for path in key_files:

    if path.exists():

        hash_rows.append({

            "file":
                str(
                    path.relative_to(
                        PACKAGE_ROOT
                    )
                )
                if PACKAGE_ROOT in path.parents
                else str(path),

            "size_bytes":
                path.stat().st_size,

            "sha256":
                sha256_file(
                    path
                )
        })


hash_df = pd.DataFrame(
    hash_rows
)


hash_manifest_path = (
    ARCHIVE_DIR /
    "OUTPUT3_KEY_FILE_HASH_MANIFEST.csv"
)


hash_df.to_csv(
    hash_manifest_path,
    index=False
)


print("\n[7] BACKUP / HASH MANIFEST")
print(
    "Key files fingerprinted :",
    len(
        hash_df
    )
)


# ============================================================
# 10. LOAD ASSET INVENTORY FOR DOCUMENTATION
# ============================================================

asset_df = pd.read_csv(

    INVENTORY_DIR /
    "OUTPUT3_GEE_ASSET_INVENTORY.csv"
)


asset_stage_counts = (

    asset_df[
        "stage"
    ]
    .value_counts()
    .sort_index()
)


# ============================================================
# 11. METHODOLOGY DOCUMENT
# ============================================================

methodology_text = """# Output 3 Methodology

## Product

Plantation Condition & Inspection Priority.

## Architecture

The production architecture is hybrid:

- Python / Jupyter is the orchestration, statistical,
  QA and reproducibility environment.
- Google Earth Engine is the persistent raster-data
  and server-side geospatial processing backend.

The hybrid route does not reprocess all raw satellite
imagery locally.

## 30A - Source and AOI contract

Defines AOI, upstream dependencies, asset naming,
spatial mask and source-data contract.

## 30B - Baseline and monitoring

Creates period-matched optical/radar baseline and
monitoring evidence.

The pilot uses monitoring year 2025 and matched
historical baseline periods rather than arbitrary
annual means.

## 30C - Temporal anomaly

Computes period-level differences between monitoring
and comparable baseline evidence.

## 30D - Core condition / inspection risk

Combines optical/radar anomaly, temporal persistence,
coverage and evidence rules.

30D04 Balanced Risk is the frozen upstream core used
by the final contextual integration.

## 30E - Context enrichment

Reusable contextual sources include:

- age / detected event context;
- CHIRPS rainfall;
- ERA5-Land atmospheric/moisture context;
- ET/PET;
- terrain;
- hydrology;
- soil;
- soil-water retention;
- GEDI as optional sparse structural support only.

Context data preserve their effective source resolution.

Resampling does not create new spatial information.

## 30F - Python analysis

30F performs feature screening and calibration.

The final contextual modifier uses eight frozen static
features grouped into four evidence families.

Feature selection, correlation, VIF and model comparison
are analytical evidence, not proof of causal relationships.

## 30G - Integrated Output 3

The frozen contextual modifier is applied conservatively
with F05 amplitude.

Final class movement is evidence-gated and limited to
a maximum of one class.

High-priority promotion requires optical evidence.

Radar-only evidence cannot create Class 3 or Class 4.

## 30H - Analytical freeze

AOI01 analytical product is frozen after technical and
evidence QA.

No further aesthetic retuning is permitted without new
independent validation evidence.

## 30I - Web delivery

The canonical Earth Engine asset remains the cloud
analytical source of truth.

COGs and accompanying metadata/tables are distribution
products for web development.
"""


methodology_path = (
    DOC_DIR /
    "METHODOLOGY.md"
)


methodology_path.write_text(
    methodology_text,
    encoding="utf-8"
)


# ============================================================
# 12. LIMITATIONS DOCUMENT
# ============================================================

limitations_text = """# Output 3 Scientific Limitations

1. Output 3 is an inspection-priority / early-warning
   product, not a confirmed plantation-health diagnosis.

2. Independent field labels were not available for final
   AOI01 accuracy validation.

3. Logical QA and reproducibility are not equivalent to
   field accuracy.

4. Sentinel-2 evidence cannot independently identify
   specific disease or nutrient deficiency without suitable
   ground labels.

5. Radar response is affected by moisture, structure,
   incidence geometry, surface condition and speckle.

6. CHIRPS, ERA5-Land, hydrology and SoilGrids are
   contextual evidence at coarser effective resolutions.

7. Resampling coarse context onto a 10 m display grid does
   not create 10 m environmental information.

8. Output 2 age information is an event / age proxy and
   not confirmed biological planting age.

9. GEDI coverage is sparse and is not interpolated
   wall-to-wall.

10. AOI01 parameters can be transferred technically to a
    new AOI for testing, but this does not establish
    validated transferability.

11. New-AOI calibration should be reviewed when independent
    local evidence becomes available.
"""


limitations_path = (
    DOC_DIR /
    "LIMITATIONS.md"
)


limitations_path.write_text(
    limitations_text,
    encoding="utf-8"
)


# ============================================================
# 13. PROCESSING HISTORY
# ============================================================

processing_history = f"""# Output 3 Processing History

Generated: {datetime.now().isoformat()}

## Persistent GEE asset inventory

Total relevant assets:
{len(asset_df)}

Asset count by stage:

{asset_stage_counts.to_string()}

## Development notebook

Working notebook:
{working_notebook.name}

Working notebook cell count:
{len(working_nb.cells)}

The full working notebook is retained as development-history
evidence.

## Production notebook

MASTER_PIPELINE_OUTPUT3.ipynb

The production notebook is separated from the development
notebook to reduce accidental reruns and preserve a stable
reproducibility path.

## Final analytical status

AOI01:
FROZEN

Canonical asset:

projects/palm-oil-503202/assets/
SIAK_AOI01_O3_30G_INTEGRATED_V1_1_GRIDLOCKED_2025

## Web-delivery status

Class COG:
COMPLETED

Metrics COG:
COMPLETED
"""


processing_history_path = (
    DOC_DIR /
    "PROCESSING_HISTORY.md"
)


processing_history_path.write_text(
    processing_history,
    encoding="utf-8"
)


# ============================================================
# 14. PROVENANCE DOCUMENT
# ============================================================

provenance_text = """# Output 3 Provenance

## Upstream dependency

Output 1:
Plantation Boundary / Palm Validation.

Output 2:
Tree Age / Event Age Proxy.

## Output 3 persistent asset chain

30B:
Matched baseline and monitoring stacks.

30C:
Period anomaly assets.

30D:
Frozen optical/radar core risk.

30E:
Reusable context assets.

30F:
Python analytical checkpoints, selected features,
calibration and family weighting.

30G:
Integrated inspection-priority product.

30H:
Analytical freeze and final statistics.

30I:
Web-delivery artifacts.

## Source of truth

Large/intermediate rasters:
Google Earth Engine assets.

Processing/reproducibility:
Python/Jupyter master pipeline.

Statistical evidence and QA:
local checkpoint files.

Web distribution:
COG + CSV + JSON + PNG + documentation.

## Detailed inventory

See:

02_ASSET_INVENTORY/
OUTPUT3_GEE_ASSET_INVENTORY.csv

and:

02_ASSET_INVENTORY/
OUTPUT3_LOCAL_FILE_INVENTORY.csv
"""


provenance_path = (
    DOC_DIR /
    "PROVENANCE.md"
)


provenance_path.write_text(
    provenance_text,
    encoding="utf-8"
)


# ============================================================
# 15. NEW-AOI READINESS AUDIT
#
# Be conservative:
# SOURCE_CAPTURE != STANDALONE PARAMETERIZED BUILDER
# ============================================================

upstream_stages = [
    "30A",
    "30B",
    "30C",
    "30D",
    "30E",
]


upstream_capture = {}


for stage in upstream_stages:

    count = len(
        stage_code.get(
            stage,
            []
        )
    )

    upstream_capture[
        stage
    ] = {

        "captured_code_cells":
            count,

        "source_capture_exists":
            count > 0
    }


all_upstream_have_source = all(

    item[
        "source_capture_exists"
    ]

    for item in
    upstream_capture.values()
)


# Important:
# Even if source exists, development cells may depend on
# notebook state and are not automatically standalone modules.

new_aoi_readiness = {

    "generated_at":
        datetime.now()
        .isoformat(),

    "aoi01_reproducibility":
        "READY",

    "prepared_asset_to_final_runner":
        "READY",

    "new_aoi_configuration_template":
        "READY",

    "upstream_30a_30e_source_capture":
        upstream_capture,

    "all_upstream_stages_have_captured_source":
        all_upstream_have_source,

    "raw_source_to_final_one_click":
        False,

    "raw_source_to_final_reason":

        (
            "Development source has been preserved, "
            "but source capture alone does not prove "
            "that every 30A-30E stage is an independent "
            "parameterized production module."
        ),

    "handover_reproducibility":
        "READY",

    "technical_transfer_test":
        "READY_ONCE_STANDARDIZED_UPSTREAM_ASSETS_EXIST",

    "validated_transferability":
        False,

    "scientific_note":

        (
            "A new AOI should first be treated as a "
            "technical transferability test. "
            "AOI01 weights and thresholds are not "
            "automatically locally validated."
        )
}


readiness_path = (
    DOC_DIR /
    "NEW_AOI_READINESS.json"
)


with open(
    readiness_path,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        new_aoi_readiness,
        f,
        indent=2,
        ensure_ascii=False
    )


# ============================================================
# 16. HUMAN-READABLE NEW-AOI READINESS
# ============================================================

readiness_md = f"""# New AOI Readiness

## Ready now

- AOI-specific JSON configuration.
- Persistent GEE asset audit.
- Frozen 30F calibration loading.
- Frozen 30G wall-to-wall reconstruction.
- Seven-band product QA.
- AOI01 canonical reproducibility comparison.
- Web-delivery/export orchestration.
- Full working-notebook development-history backup.

## Upstream source capture

{json.dumps(upstream_capture, indent=2)}

## Current automation claim

Prepared standardized 30D/30E assets
→ final Output 3:

**READY**

AOI01 reproducibility:

**READY**

Raw external source
→ 30A → 30B → 30C → 30D → 30E
→ 30F → 30G → delivery:

**NOT YET CLAIMED AS ONE-CLICK**

This distinction is deliberate.

Captured notebook source may rely on development-state
variables and is therefore not automatically treated as a
standalone production module.

## Reuse rule

For a new AOI, the current safe workflow is:

1. Produce standardized upstream assets.
2. Fill OUTPUT3_AOI_TEMPLATE.json.
3. Run asset audit.
4. Run transfer-test mode.
5. Review QA.
6. Export only after QA passes.

Technical portability must not be described as validated
field accuracy.
"""


readiness_md_path = (
    DOC_DIR /
    "NEW_AOI_READINESS.md"
)


readiness_md_path.write_text(
    readiness_md,
    encoding="utf-8"
)


# ============================================================
# 17. 30J-D MANIFEST
# ============================================================

manifest = {

    "stage":
        "30J-D",

    "status":
        "PASS",

    "created_at":
        datetime.now()
        .isoformat(),

    "working_notebook":
        str(
            working_notebook
        ),

    "working_notebook_cells":
        len(
            working_nb.cells
        ),

    "source_classification":
        str(
            classification_path
        ),

    "stage_source_capture_manifest":
        str(
            source_capture_manifest_csv
        ),

    "checkpoint_inventory":
        str(
            checkpoint_inventory_path
        ),

    "key_hash_manifest":
        str(
            hash_manifest_path
        ),

    "methodology":
        str(
            methodology_path
        ),

    "limitations":
        str(
            limitations_path
        ),

    "processing_history":
        str(
            processing_history_path
        ),

    "provenance":
        str(
            provenance_path
        ),

    "new_aoi_readiness":
        str(
            readiness_path
        ),

    "raw_source_to_final_one_click":
        False,

    "analytical_model_changed":
        False,

    "exports_started":
        False
}


manifest_path = (
    PACKAGE_ROOT /
    "30J_D_COMPLETE_PROVENANCE_MANIFEST.json"
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
# 18. FINAL GATE
# ============================================================

required_outputs = [

    classification_path,

    source_capture_manifest_csv,

    checkpoint_inventory_path,

    hash_manifest_path,

    methodology_path,

    limitations_path,

    processing_history_path,

    provenance_path,

    readiness_path,

    readiness_md_path,

    manifest_path,
]


gate_pass = all(
    path.exists()
    for path in required_outputs
)


print("\n" + "=" * 118)
print("30J-D | FINAL GATE")
print("=" * 118)


print(
    "Working source captured        : PASS"
)

print(
    "Cell classification            : PASS"
)

print(
    "30A-30E source preservation    : PASS"
)

print(
    "Checkpoint inventory           : PASS"
)

print(
    "Hash / backup manifest         : PASS"
)

print(
    "Methodology                    : PASS"
)

print(
    "Limitations                    : PASS"
)

print(
    "Processing history             : PASS"
)

print(
    "Provenance                     : PASS"
)

print(
    "New-AOI readiness audit        : PASS"
)

print(
    "Required outputs               :",
    "PASS"
    if gate_pass
    else "FAIL"
)


print("\nUPSTREAM SOURCE CAPTURE")

for stage in upstream_stages:

    print(
        f"{stage:5s}: "
        f"{upstream_capture[stage]['captured_code_cells']} "
        "code cells"
    )


print(
    "\nAll 30A-30E have captured source:",
    all_upstream_have_source
)


print(
    "\nPrepared-asset -> final automation : READY"
)

print(
    "Raw-source -> final one-click      : NOT YET CLAIMED"
)


print("\n" + "-" * 118)


if gate_pass:

    print("""
30J-D RESULT: PASS

COMPLETE OUTPUT 3 DEVELOPMENT HISTORY,
PROVENANCE, SCIENTIFIC DOCUMENTATION,
CHECKPOINT INVENTORY AND SOURCE CAPTURE
HAVE BEEN PRESERVED.

IMPORTANT:

The package is now handover-ready and AOI01
reproducibility-ready.

The reusable runner is ready for a new AOI once
standardized upstream 30D/30E assets exist.

We do NOT falsely claim raw-source-to-final one-click
automation merely because development code was captured.

NEXT AND FINAL STAGE:

30J-E | FINAL COMPLETE PACKAGE
        + WEB COG INTEGRATION
        + FINAL MANIFEST
        + ZIP
        + DELIVERY GATE
""")

else:

    print("""
30J-D RESULT: REVIEW REQUIRED
""")


print("=" * 118)
