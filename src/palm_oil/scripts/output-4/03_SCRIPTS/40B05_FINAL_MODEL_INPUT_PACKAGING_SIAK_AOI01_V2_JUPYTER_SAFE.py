# ============================================================
# OUTPUT 4 / 40B05
# FINAL MODEL-INPUT PACKAGING — SIAK_AOI01
# LOW-MEMORY / SCRIPT MODE
#
# PURPOSE
# - Merge the frozen Output 4 inputs into one ASU-level master table:
#   exact ASU geometry attributes + age/condition + SoilGrids + climate refs.
# - Build PALMSIM and APSIM-OilPalm input manifests.
# - DO NOT fabricate missing field data.
# - Preserve uncertainty / missingness.
#
# IMPORTANT
# - CHIRPS and ERA5-Land daily time series are NOT duplicated here.
# - Each ASU only carries CHIRPS_CELL_ID, ERA5L_CELL_ID, CLIMATE_PAIR_ID.
# - Daily weather will be joined on demand during process-model execution.
# ============================================================

from pathlib import Path
import os
import re
import json
import numpy as np
import pandas as pd

WORKDIR = Path(
    r"C:\Users\user\Documents\KERJA\SPATIAL DATA ANALYST INTERN\04_YIELD"
)
os.chdir(WORKDIR)

# ---------------------------
# INPUT FILES
# ---------------------------
ASU_EXACT = WORKDIR / "40B03A_FINAL_ASU_500M_EXACT_SIAK_AOI01_V1.csv"
AGE_COND = WORKDIR / "40B02A_GRID_500M_SIAK_AOI01_2025_V3.csv"
SOIL = WORKDIR / "40B03C1_FINAL_ASU_500M_SOIL_TEXTURE_SIAK_AOI01_V1.csv"
CLIMATE_MAP = WORKDIR / "40B04C_LITE_ASU_CLIMATE_PAIR_MAPPING_SIAK_AOI01_V1.csv"

# Optional exact geometry, used only if centroid coordinates are absent in CSVs.
ASU_GEOJSON = WORKDIR / "40B03A_FINAL_ASU_500M_EXACT_SIAK_AOI01_V1.geojson"

# ---------------------------
# OUTPUT FILES
# ---------------------------
OUT_MASTER = WORKDIR / "40B05_COMMON_MODEL_INPUT_MASTER_SIAK_AOI01_V1.csv"
OUT_PALMSIM = WORKDIR / "40B05_PALMSIM_STATIC_INPUT_MANIFEST_SIAK_AOI01_V1.csv"
OUT_APSIM = WORKDIR / "40B05_APSIM_OILPALM_INPUT_MANIFEST_SIAK_AOI01_V1.csv"
OUT_GAPS = WORKDIR / "40B05_PARAMETER_GAP_REGISTER_SIAK_AOI01_V1.csv"
OUT_READINESS = WORKDIR / "40B05_MODEL_READINESS_SUMMARY_SIAK_AOI01_V1.csv"
OUT_QC = WORKDIR / "40B05_FINAL_MODEL_INPUT_PACKAGING_QC_SIAK_AOI01_V1.json"

print("====================================================")
print("40B05 V2 — FINAL MODEL-INPUT PACKAGING / JUPYTER-SAFE")
print("====================================================")

for p in [ASU_EXACT, AGE_COND, SOIL, CLIMATE_MAP]:
    if not p.exists():
        raise FileNotFoundError(f"Missing required input: {p}")

# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------

def norm(s):
    return re.sub(r"[^A-Z0-9]+", "_", str(s).upper()).strip("_")

def find_col(columns, include_any=None, include_all=None, exclude=None, preferred=None):
    """
    Robust field finder. Returns original column name or None.

    IMPORTANT V2 FIX:
    If only `preferred=` is supplied and none of the preferred names exists,
    return None instead of silently returning the first column.
    The V1 fallback could incorrectly treat UNIT_ID as latitude/longitude,
    which then removed UNIT_ID during rename and caused merge KeyError.
    """
    cols = list(columns)
    nmap = {c: norm(c) for c in cols}

    if preferred:
        pref_norm = [norm(x) for x in preferred]
        for p in pref_norm:
            for c, n in nmap.items():
                if n == p:
                    return c

    # No search rule beyond exact preferred names -> no match.
    if not include_any and not include_all:
        return None

    candidates = []
    for c, n in nmap.items():
        if include_all and not all(norm(x) in n for x in include_all):
            continue
        if include_any and not any(norm(x) in n for x in include_any):
            continue
        if exclude and any(norm(x) in n for x in exclude):
            continue
        candidates.append(c)

    return candidates[0] if candidates else None

def require_unit_id(df, label):
    c = find_col(
        df.columns,
        preferred=["UNIT_ID", "ASU_ID", "GRID_ID", "ID"]
    )
    if c is None:
        raise ValueError(f"{label}: UNIT_ID/ASU_ID field not found. Columns={list(df.columns)}")
    if c != "UNIT_ID":
        df = df.rename(columns={c: "UNIT_ID"})
    df["UNIT_ID"] = df["UNIT_ID"].astype(str)
    return df

def numeric(s):
    return pd.to_numeric(s, errors="coerce")

# ------------------------------------------------------------
# 1. LOAD
# ------------------------------------------------------------

asu = require_unit_id(pd.read_csv(ASU_EXACT), "ASU_EXACT")
agec = require_unit_id(pd.read_csv(AGE_COND), "AGE_COND")
soil = require_unit_id(pd.read_csv(SOIL), "SOIL")
clim = require_unit_id(pd.read_csv(CLIMATE_MAP), "CLIMATE_MAP")

print("ASU exact rows:", len(asu))
print("Age/condition rows:", len(agec))
print("Soil rows:", len(soil))
print("Climate map rows:", len(clim))

if len(asu) != 820:
    raise ValueError(f"Expected 820 exact ASUs; found {len(asu)}")

# ------------------------------------------------------------
# 2. DISCOVER IMPORTANT COLUMNS
# ------------------------------------------------------------

# Exact area
area_col = find_col(
    asu.columns,
    preferred=[
        "ASU_AREA_HA_EXACT", "AREA_HA_EXACT", "EXACT_AREA_HA",
        "PLANTATION_AREA_HA", "AREA_HA"
    ],
    include_all=["AREA", "HA"]
)

# Age: prefer P50/median.
age_col = find_col(
    agec.columns,
    preferred=[
        "AGE_P50", "AGE_MEDIAN", "AGE_PROXY_P50",
        "AGE_YEARS_P50", "AGE_YR_P50"
    ],
    include_all=["AGE"],
    include_any=["P50", "MEDIAN"],
    exclude=["VALID", "FRACTION", "RANGE", "P10", "P90", "COUNT"]
)
if age_col is None:
    age_col = find_col(
        agec.columns,
        include_all=["AGE"],
        exclude=["VALID", "FRACTION", "RANGE", "P10", "P90", "COUNT", "CLASS"]
    )

age_valid_frac_col = find_col(
    agec.columns,
    preferred=[
        "AGE_VALID_FRACTION", "AGE_VALID_FRAC",
        "AGE_COVERAGE_FRACTION", "AGE_VALID_PCT"
    ],
    include_all=["AGE"],
    include_any=["VALID", "COVER", "FRACTION", "FRAC"],
    exclude=["COUNT"]
)

age_range_col = find_col(
    agec.columns,
    preferred=["AGE_P90_P10_RANGE", "AGE_RANGE", "AGE_P90_MINUS_P10"],
    include_all=["AGE", "RANGE"]
)

# Condition score
cond_col = find_col(
    agec.columns,
    preferred=[
        "CONDITION_P50", "CONDITION_MEDIAN",
        "CONDITION_SCORE_P50", "COND_P50", "COND_MEDIAN"
    ]
)
# If no exact preferred field exists, look for a median/P50 condition field.
if cond_col is None:
    candidates = []
    for c in agec.columns:
        n = norm(c)
        if (
            ("CONDITION" in n or "COND" in n)
            and ("P50" in n or "MEDIAN" in n)
            and not any(
                x in n for x in ["VALID", "COVER", "FRACTION", "COUNT", "RANGE", "P10", "P90"]
            )
        ):
            candidates.append(c)
    cond_col = candidates[0] if candidates else None

# Final cautious fallback: any condition-score-like field that is not QC/coverage/range.
if cond_col is None:
    candidates = []
    for c in agec.columns:
        n = norm(c)
        if ("CONDITION" in n or "COND" in n) and not any(
            x in n for x in ["VALID", "COVER", "FRACTION", "COUNT", "RANGE", "P10", "P90"]
        ):
            candidates.append(c)
    cond_col = candidates[0] if candidates else None

cond_valid_frac_col = find_col(
    agec.columns,
    preferred=[
        "CONDITION_VALID_FRACTION", "COND_VALID_FRACTION",
        "CONDITION_COVERAGE_FRACTION"
    ],
    include_any=["CONDITION", "COND"],
)
# Narrow the broad match if needed.
if cond_valid_frac_col is not None:
    n = norm(cond_valid_frac_col)
    if not any(x in n for x in ["VALID", "COVER", "FRACTION", "FRAC"]):
        cond_valid_frac_col = None
if cond_valid_frac_col is None:
    for c in agec.columns:
        n = norm(c)
        if ("CONDITION" in n or "COND" in n) and any(
            x in n for x in ["VALID", "COVER", "FRACTION", "FRAC"]
        ):
            cond_valid_frac_col = c
            break

# Soil 0-100 cm texture.
sand_col = find_col(
    soil.columns,
    preferred=[
        "SAND_0_100_PCT", "SAND_0_100_CM_PCT", "SAND_PCT_0_100",
        "SAND_0_100", "SAND_PCT"
    ],
    include_all=["SAND"],
)
silt_col = find_col(
    soil.columns,
    preferred=[
        "SILT_0_100_PCT", "SILT_0_100_CM_PCT", "SILT_PCT_0_100",
        "SILT_0_100", "SILT_PCT"
    ],
    include_all=["SILT"],
)
clay_col = find_col(
    soil.columns,
    preferred=[
        "CLAY_0_100_PCT", "CLAY_0_100_CM_PCT", "CLAY_PCT_0_100",
        "CLAY_0_100", "CLAY_PCT"
    ],
    include_all=["CLAY"],
)

# Climate refs
chirps_id_col = find_col(clim.columns, preferred=["CHIRPS_CELL_ID"])
era_id_col = find_col(clim.columns, preferred=["ERA5L_CELL_ID"])
pair_id_col = find_col(clim.columns, preferred=["CLIMATE_PAIR_ID"])

if not chirps_id_col or not era_id_col or not pair_id_col:
    raise ValueError("Climate reference columns are incomplete in 40B04C-LITE output.")

# Latitude/longitude: first try climate mapping, then ASU exact.
lat_col = find_col(
    clim.columns,
    preferred=["ASU_LAT", "CENTROID_LAT", "LATITUDE", "LAT"]
)
lon_col = find_col(
    clim.columns,
    preferred=["ASU_LON", "CENTROID_LON", "LONGITUDE", "LON"]
)

lat_source = "ASU/CLIMATE_MAP"

if lat_col is None:
    lat_col = find_col(
        asu.columns,
        preferred=["ASU_LAT", "CENTROID_LAT", "LATITUDE", "LAT"]
    )
    lon_col = find_col(
        asu.columns,
        preferred=["ASU_LON", "CENTROID_LON", "LONGITUDE", "LON"]
    )
    lat_source = "ASU_EXACT_CSV"

# If still unavailable, derive from exact GeoJSON when geopandas is available.
centroid_df = None
if lat_col is None and ASU_GEOJSON.exists():
    try:
        import geopandas as gpd

        g = gpd.read_file(ASU_GEOJSON)
        g = require_unit_id(g, "ASU_GEOJSON")

        # UTM47N -> WGS84 for physically meaningful lat/lon centroid.
        if g.crs is None:
            raise ValueError("Exact ASU GeoJSON has no CRS.")
        gm = g.to_crs("EPSG:32647")
        cent = gm.geometry.centroid
        pts = gpd.GeoSeries(cent, crs="EPSG:32647").to_crs("EPSG:4326")

        centroid_df = pd.DataFrame({
            "UNIT_ID": g["UNIT_ID"].astype(str),
            "ASU_CENTROID_LON": pts.x,
            "ASU_CENTROID_LAT": pts.y,
        })
        lat_source = "EXACT_ASU_GEOMETRY_CENTROID"
    except Exception as e:
        print("WARNING: Could not derive exact centroid from GeoJSON:", repr(e))

print("\nDetected fields:")
print("  area              :", area_col)
print("  age               :", age_col)
print("  age valid fraction:", age_valid_frac_col)
print("  age range         :", age_range_col)
print("  condition         :", cond_col)
print("  condition coverage:", cond_valid_frac_col)
print("  sand              :", sand_col)
print("  silt              :", silt_col)
print("  clay              :", clay_col)
print("  centroid source   :", lat_source)

if age_col is None:
    raise ValueError("Could not identify age proxy field.")
if cond_col is None:
    raise ValueError("Could not identify condition field.")
if sand_col is None or silt_col is None or clay_col is None:
    raise ValueError("Could not identify all SoilGrids sand/silt/clay fields.")

# ------------------------------------------------------------
# 3. BUILD SMALL SOURCE TABLES
# ------------------------------------------------------------

base_cols = ["UNIT_ID"]
if area_col:
    base_cols.append(area_col)
base = asu[base_cols].copy()
if area_col:
    base = base.rename(columns={area_col: "ASU_PLANTATION_AREA_HA"})

age_cols = ["UNIT_ID", age_col, cond_col]
for c in [age_valid_frac_col, age_range_col, cond_valid_frac_col]:
    if c and c not in age_cols:
        age_cols.append(c)

a = agec[age_cols].copy()
rename_a = {
    age_col: "AGE_PROXY_YR",
    cond_col: "CONDITION_SCORE",
}
if age_valid_frac_col:
    rename_a[age_valid_frac_col] = "AGE_VALID_FRACTION"
if age_range_col:
    rename_a[age_range_col] = "AGE_WITHIN_ASU_RANGE_YR"
if cond_valid_frac_col:
    rename_a[cond_valid_frac_col] = "CONDITION_VALID_FRACTION"
a = a.rename(columns=rename_a)

s = soil[["UNIT_ID", sand_col, silt_col, clay_col]].copy().rename(columns={
    sand_col: "SAND_0_100_PCT",
    silt_col: "SILT_0_100_PCT",
    clay_col: "CLAY_0_100_PCT",
})

c = clim[["UNIT_ID", chirps_id_col, era_id_col, pair_id_col]].copy().rename(columns={
    chirps_id_col: "CHIRPS_CELL_ID",
    era_id_col: "ERA5L_CELL_ID",
    pair_id_col: "CLIMATE_PAIR_ID",
})

# Add lat/lon if directly available.
if lat_col is not None:
    src = clim if lat_col in clim.columns else asu
    lon_to_use = lon_col if lon_col in src.columns else None
    coord_cols = ["UNIT_ID", lat_col] + ([lon_to_use] if lon_to_use else [])
    coords = src[coord_cols].copy()
    coords = coords.rename(columns={lat_col: "ASU_LATITUDE"})
    if lon_to_use:
        coords = coords.rename(columns={lon_to_use: "ASU_LONGITUDE"})
elif centroid_df is not None:
    coords = centroid_df.rename(columns={
        "ASU_CENTROID_LAT": "ASU_LATITUDE",
        "ASU_CENTROID_LON": "ASU_LONGITUDE",
    })
else:
    coords = None

# ------------------------------------------------------------
# 4. MERGE MASTER
# ------------------------------------------------------------

master = base.merge(a, on="UNIT_ID", how="left", validate="one_to_one")
master = master.merge(s, on="UNIT_ID", how="left", validate="one_to_one")
master = master.merge(c, on="UNIT_ID", how="left", validate="one_to_one")

if coords is not None:
    master = master.merge(coords, on="UNIT_ID", how="left", validate="one_to_one")
else:
    # Fallback: use ERA5-Land cell latitude only if it exists in climate source.
    era_lat = find_col(clim.columns, preferred=["ERA5L_LAT"])
    era_lon = find_col(clim.columns, preferred=["ERA5L_LON"])
    if era_lat:
        fallback = clim[["UNIT_ID", era_lat] + ([era_lon] if era_lon else [])].copy()
        fallback = fallback.rename(columns={era_lat: "ASU_LATITUDE"})
        if era_lon:
            fallback = fallback.rename(columns={era_lon: "ASU_LONGITUDE"})
        master = master.merge(fallback, on="UNIT_ID", how="left", validate="one_to_one")
        lat_source = "ERA5L_NATIVE_CELL_CENTER_FALLBACK"
    else:
        master["ASU_LATITUDE"] = np.nan
        master["ASU_LONGITUDE"] = np.nan
        lat_source = "MISSING"

# Numeric normalization.
for col in [
    "ASU_PLANTATION_AREA_HA",
    "AGE_PROXY_YR",
    "AGE_VALID_FRACTION",
    "AGE_WITHIN_ASU_RANGE_YR",
    "CONDITION_SCORE",
    "CONDITION_VALID_FRACTION",
    "SAND_0_100_PCT",
    "SILT_0_100_PCT",
    "CLAY_0_100_PCT",
    "ASU_LATITUDE",
    "ASU_LONGITUDE",
]:
    if col in master.columns:
        master[col] = numeric(master[col])

# ------------------------------------------------------------
# 5. READINESS / UNCERTAINTY FLAGS
# ------------------------------------------------------------

master["AGE_AVAILABLE"] = master["AGE_PROXY_YR"].notna()
master["CONDITION_AVAILABLE"] = master["CONDITION_SCORE"].notna()

master["SOIL_TEXTURE_AVAILABLE"] = master[
    ["SAND_0_100_PCT", "SILT_0_100_PCT", "CLAY_0_100_PCT"]
].notna().all(axis=1)

master["SOIL_TEXTURE_SUM_PCT"] = master[
    ["SAND_0_100_PCT", "SILT_0_100_PCT", "CLAY_0_100_PCT"]
].sum(axis=1, min_count=3)

master["SOIL_TEXTURE_CLOSURE_PASS"] = master["SOIL_TEXTURE_SUM_PCT"].between(99.5, 100.5)

master["CLIMATE_REFERENCE_AVAILABLE"] = master[
    ["CHIRPS_CELL_ID", "ERA5L_CELL_ID", "CLIMATE_PAIR_ID"]
].notna().all(axis=1)

master["LATITUDE_AVAILABLE"] = master["ASU_LATITUDE"].notna()

# Age support is kept explicit; no filling of missing age.
if "AGE_VALID_FRACTION" in master.columns:
    master["AGE_SUPPORT_FLAG"] = np.select(
        [
            master["AGE_PROXY_YR"].isna(),
            master["AGE_VALID_FRACTION"] < 0.10,
            master["AGE_VALID_FRACTION"] < 0.50,
        ],
        [
            "MISSING",
            "VERY_LOW_SUPPORT",
            "PARTIAL_SUPPORT",
        ],
        default="MODERATE_OR_HIGH_SUPPORT"
    )
else:
    master["AGE_SUPPORT_FLAG"] = np.where(
        master["AGE_PROXY_YR"].notna(),
        "AVAILABLE_COVERAGE_FIELD_NOT_FOUND",
        "MISSING"
    )

# ------------------------------------------------------------
# 6. PALMSIM MANIFEST
# ------------------------------------------------------------

palmsim = master[[
    c for c in [
        "UNIT_ID",
        "ASU_PLANTATION_AREA_HA",
        "ASU_LATITUDE",
        "ASU_LONGITUDE",
        "AGE_PROXY_YR",
        "AGE_VALID_FRACTION",
        "AGE_SUPPORT_FLAG",
        "SAND_0_100_PCT",
        "SILT_0_100_PCT",
        "CLAY_0_100_PCT",
        "CHIRPS_CELL_ID",
        "ERA5L_CELL_ID",
        "CLIMATE_PAIR_ID",
    ]
    if c in master.columns
]].copy()

# Scenario parameter: not claimed as observed estate density.
palmsim["PALM_DENSITY_PALMS_HA"] = 143.0
palmsim["PALM_DENSITY_SOURCE"] = "DEFAULT_SCENARIO_NOT_OBSERVED"

# Do NOT fabricate soil depth.
palmsim["SOIL_DEPTH_M"] = np.nan
palmsim["SOIL_DEPTH_STATUS"] = "SCENARIO_PARAMETER_TO_TEST"

# Soil system uncertainty.
palmsim["PEAT_MINERAL_STATUS"] = "UNRESOLVED_OFFICIAL_FLAG_REQUIRED"

palmsim["PALMSIM_STATIC_CORE_READY"] = (
    palmsim["AGE_PROXY_YR"].notna()
    & palmsim["SAND_0_100_PCT"].notna()
    & palmsim["SILT_0_100_PCT"].notna()
    & palmsim["CLAY_0_100_PCT"].notna()
    & palmsim["CHIRPS_CELL_ID"].notna()
    & palmsim["ERA5L_CELL_ID"].notna()
    & palmsim["ASU_LATITUDE"].notna()
)

palmsim["PALMSIM_RUN_POLICY"] = np.where(
    palmsim["PALMSIM_STATIC_CORE_READY"],
    "ELIGIBLE_FOR_EXPERIMENTAL_RUN_WITH_SCENARIO_DEPTH_DENSITY_AND_PEAT_WARNING",
    "HOLD_MISSING_CORE_INPUT"
)

# ------------------------------------------------------------
# 7. APSIM-OILPALM MANIFEST
# ------------------------------------------------------------

apsim = master[[
    c for c in [
        "UNIT_ID",
        "ASU_PLANTATION_AREA_HA",
        "ASU_LATITUDE",
        "ASU_LONGITUDE",
        "AGE_PROXY_YR",
        "AGE_VALID_FRACTION",
        "AGE_SUPPORT_FLAG",
        "SAND_0_100_PCT",
        "SILT_0_100_PCT",
        "CLAY_0_100_PCT",
        "CHIRPS_CELL_ID",
        "ERA5L_CELL_ID",
        "CLIMATE_PAIR_ID",
    ]
    if c in master.columns
]].copy()

# Explicitly document missing detailed APSIM parameters.
apsim["DETAILED_SOIL_PROFILE_STATUS"] = "PARTIAL_TEXTURE_ONLY"
apsim["SOIL_HYDRAULIC_PROFILE_STATUS"] = "NOT_YET_PARAMETERIZED"
apsim["NITROGEN_PROFILE_STATUS"] = "NOT_AVAILABLE"
apsim["FERTILIZER_MANAGEMENT_STATUS"] = "NOT_AVAILABLE"
apsim["CULTIVAR_STATUS"] = "NOT_AVAILABLE"
apsim["DRAINAGE_MANAGEMENT_STATUS"] = "NOT_AVAILABLE"
apsim["PALM_DENSITY_STATUS"] = "SCENARIO_REQUIRED"
apsim["PEAT_MINERAL_STATUS"] = "UNRESOLVED_OFFICIAL_FLAG_REQUIRED"

apsim["APSIM_WEATHER_REFERENCE_READY"] = (
    apsim["CHIRPS_CELL_ID"].notna()
    & apsim["ERA5L_CELL_ID"].notna()
)

apsim["APSIM_BENCHMARK_POLICY"] = np.where(
    apsim["APSIM_WEATHER_REFERENCE_READY"],
    "REPRESENTATIVE_SCENARIO_BENCHMARK_ONLY",
    "HOLD_MISSING_WEATHER_REFERENCE"
)

# ------------------------------------------------------------
# 8. PARAMETER GAP REGISTER
# ------------------------------------------------------------

gaps = pd.DataFrame([
    {
        "MODEL": "PALMSIM",
        "PARAMETER_GROUP": "Age",
        "CURRENT_STATUS": "Partial AOI coverage; age is an event-age proxy",
        "ACTION": "Preserve age support/uncertainty; do not impute silently",
        "BLOCKS_RUN_POLICY": "Run only ASUs with usable age unless explicit age scenarios are tested",
    },
    {
        "MODEL": "PALMSIM",
        "PARAMETER_GROUP": "Palm density",
        "CURRENT_STATUS": "No observed estate density",
        "ACTION": "Use 143 palms/ha only as documented baseline scenario; include sensitivity",
        "BLOCKS_RUN_POLICY": "Scenario parameter",
    },
    {
        "MODEL": "PALMSIM",
        "PARAMETER_GROUP": "Soil depth",
        "CURRENT_STATUS": "Not locally observed",
        "ACTION": "Define explicit sensitivity scenarios before model execution",
        "BLOCKS_RUN_POLICY": "Scenario parameter",
    },
    {
        "MODEL": "PALMSIM/APSIM",
        "PARAMETER_GROUP": "Peat/mineral",
        "CURRENT_STATUS": "Official flag not yet attached",
        "ACTION": "Keep explicit unresolved warning; do not infer mineral soil from SoilGrids completeness",
        "BLOCKS_RUN_POLICY": "Interpretation warning",
    },
    {
        "MODEL": "APSIM-OilPalm",
        "PARAMETER_GROUP": "Detailed soil hydraulic/N profile",
        "CURRENT_STATUS": "Not available from current core package",
        "ACTION": "Parameterize representative scenarios only; no claim of site-calibrated APSIM",
        "BLOCKS_RUN_POLICY": "Scenario benchmark only",
    },
    {
        "MODEL": "APSIM-OilPalm",
        "PARAMETER_GROUP": "Cultivar/fertilizer/drainage/management",
        "CURRENT_STATUS": "No estate records",
        "ACTION": "Use transparent representative scenarios; do not treat as actual management",
        "BLOCKS_RUN_POLICY": "Scenario benchmark only",
    },
    {
        "MODEL": "Both",
        "PARAMETER_GROUP": "Actual FFB yield",
        "CURRENT_STATUS": "Unavailable",
        "ACTION": "Do not evaluate actual yield accuracy; compare feasibility, stability, sensitivity, plausibility and agreement",
        "BLOCKS_RUN_POLICY": "Productivity Potential only",
    },
])

# ------------------------------------------------------------
# 9. QC / READINESS SUMMARY
# ------------------------------------------------------------

readiness = pd.DataFrame([
    {
        "CHECK": "ASU count",
        "VALUE": int(len(master)),
        "EXPECTED": 820,
        "PASS": bool(len(master) == 820),
    },
    {
        "CHECK": "Age available ASUs",
        "VALUE": int(master["AGE_AVAILABLE"].sum()),
        "EXPECTED": "Informational; expected approx. 654 from 40B03B",
        "PASS": True,
    },
    {
        "CHECK": "Condition available ASUs",
        "VALUE": int(master["CONDITION_AVAILABLE"].sum()),
        "EXPECTED": "Informational; expected approx. 818 from 40B03B",
        "PASS": True,
    },
    {
        "CHECK": "Soil texture complete ASUs",
        "VALUE": int(master["SOIL_TEXTURE_AVAILABLE"].sum()),
        "EXPECTED": 820,
        "PASS": bool(master["SOIL_TEXTURE_AVAILABLE"].sum() == 820),
    },
    {
        "CHECK": "Climate reference complete ASUs",
        "VALUE": int(master["CLIMATE_REFERENCE_AVAILABLE"].sum()),
        "EXPECTED": 820,
        "PASS": bool(master["CLIMATE_REFERENCE_AVAILABLE"].sum() == 820),
    },
    {
        "CHECK": "PALMSIM static core eligible ASUs",
        "VALUE": int(palmsim["PALMSIM_STATIC_CORE_READY"].sum()),
        "EXPECTED": "Subset controlled mainly by age availability",
        "PASS": True,
    },
    {
        "CHECK": "APSIM weather-reference ready ASUs",
        "VALUE": int(apsim["APSIM_WEATHER_REFERENCE_READY"].sum()),
        "EXPECTED": 820,
        "PASS": bool(apsim["APSIM_WEATHER_REFERENCE_READY"].sum() == 820),
    },
])

hard_pass = bool(
    len(master) == 820
    and master["SOIL_TEXTURE_AVAILABLE"].sum() == 820
    and master["CLIMATE_REFERENCE_AVAILABLE"].sum() == 820
    and apsim["APSIM_WEATHER_REFERENCE_READY"].sum() == 820
)

status = "PASS" if hard_pass else "CHECK"

qc = {
    "gate": "40B05",
    "status": status,
    "asu_count": int(len(master)),
    "detected_columns": {
        "area": area_col,
        "age": age_col,
        "age_valid_fraction": age_valid_frac_col,
        "age_range": age_range_col,
        "condition": cond_col,
        "condition_valid_fraction": cond_valid_frac_col,
        "sand": sand_col,
        "silt": silt_col,
        "clay": clay_col,
        "latitude_source": lat_source,
    },
    "coverage": {
        "age_available_asus": int(master["AGE_AVAILABLE"].sum()),
        "condition_available_asus": int(master["CONDITION_AVAILABLE"].sum()),
        "soil_texture_complete_asus": int(master["SOIL_TEXTURE_AVAILABLE"].sum()),
        "climate_reference_complete_asus": int(master["CLIMATE_REFERENCE_AVAILABLE"].sum()),
        "latitude_available_asus": int(master["LATITUDE_AVAILABLE"].sum()),
    },
    "model_readiness": {
        "palmsim_static_core_eligible_asus": int(
            palmsim["PALMSIM_STATIC_CORE_READY"].sum()
        ),
        "palmsim_total_asus": int(len(palmsim)),
        "apsim_weather_reference_ready_asus": int(
            apsim["APSIM_WEATHER_REFERENCE_READY"].sum()
        ),
        "apsim_policy": "representative scenario/process benchmark; not site-calibrated",
    },
    "climate_storage_policy": (
        "Join-on-demand. No 25-year daily weather duplication at ASU level."
    ),
    "product_claim": (
        "Productivity Potential & Management Priority; no actual-yield accuracy claim "
        "without local FFB labels."
    ),
    "next_gate": (
        "40C01 PALMSIM experiment adapter + explicit density/soil-depth sensitivity scenarios"
    ),
}

# ------------------------------------------------------------
# 10. EXPORT
# ------------------------------------------------------------

master.to_csv(OUT_MASTER, index=False, encoding="utf-8-sig")
palmsim.to_csv(OUT_PALMSIM, index=False, encoding="utf-8-sig")
apsim.to_csv(OUT_APSIM, index=False, encoding="utf-8-sig")
gaps.to_csv(OUT_GAPS, index=False, encoding="utf-8-sig")
readiness.to_csv(OUT_READINESS, index=False, encoding="utf-8-sig")
OUT_QC.write_text(json.dumps(qc, indent=2), encoding="utf-8")

print("\n====================================================")
print("40B05 FINISHED")
print("====================================================")
print("Status:", status)
print("ASUs:", len(master))
print("Age available:", int(master["AGE_AVAILABLE"].sum()))
print("Condition available:", int(master["CONDITION_AVAILABLE"].sum()))
print("Soil texture complete:", int(master["SOIL_TEXTURE_AVAILABLE"].sum()), "/", len(master))
print("Climate refs complete:", int(master["CLIMATE_REFERENCE_AVAILABLE"].sum()), "/", len(master))
print("Latitude available:", int(master["LATITUDE_AVAILABLE"].sum()), "/", len(master))
print("PALMSIM static core eligible:", int(palmsim["PALMSIM_STATIC_CORE_READY"].sum()), "/", len(palmsim))
print("APSIM weather-reference ready:", int(apsim["APSIM_WEATHER_REFERENCE_READY"].sum()), "/", len(apsim))
print("Master:", OUT_MASTER)
print("PALMSIM manifest:", OUT_PALMSIM)
print("APSIM manifest:", OUT_APSIM)
print("Gap register:", OUT_GAPS)
print("Readiness summary:", OUT_READINESS)
print("QC JSON:", OUT_QC)
print("Next: 40C01 PALMSIM experimental adapter")
print("====================================================")
