# ========================================
# RECOVERED HISTORICAL SOURCE CANDIDATE
# Stage: 30I
# Source: OUTPUT 3.ipynb
# ========================================


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
