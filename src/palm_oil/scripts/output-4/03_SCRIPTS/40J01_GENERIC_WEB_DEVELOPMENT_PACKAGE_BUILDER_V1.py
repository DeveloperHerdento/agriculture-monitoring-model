# ============================================================
# OUTPUT 4 / 40J01
# GENERIC WEB DEVELOPMENT PACKAGE BUILDER
#
# REUSABLE FOR SIAK_AOI01, AOI02, AOI03, ETC.
#
# STANDARD LIBRARY ONLY
# NO geopandas / shapely / matplotlib
# NO model rerun / NO class recalculation
#
# INPUT:
# - one AOI config JSON
# - exact WGS84 GeoJSON geometry
# - frozen 40I01 attribute CSV
# - display-contract outputs from 40I02B
#
# OUTPUT:
# - web-ready enriched GeoJSON
# - legend JSON
# - popup contract JSON
# - class summary CSV
# - model/package metadata JSON
# - field inventory JSON
# - README for web developer
# - ZIP package
# ============================================================

from pathlib import Path
import csv
import json
import math
import shutil
import zipfile
from datetime import datetime, timezone

WORKDIR = Path(
    r"C:\Users\user\Documents\KERJA\SPATIAL DATA ANALYST INTERN\04_YIELD"
)

# For another AOI, normally only change this config filename
# (or copy/rename the config to the same canonical name).
CONFIG_PATH = WORKDIR / "40J01_WEB_PACKAGE_CONFIG_SIAK_AOI01_V1.json"


def read_csv(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def to_native(value):
    if value is None:
        return None

    s = str(value).strip()

    if s == "":
        return None

    low = s.lower()

    if low == "true":
        return True
    if low == "false":
        return False

    try:
        if "." not in s and "e" not in low:
            return int(s)
    except Exception:
        pass

    try:
        x = float(s)
        if math.isfinite(x):
            return x
    except Exception:
        pass

    return s


if not CONFIG_PATH.exists():
    raise FileNotFoundError(
        f"Config not found:\n{CONFIG_PATH}\n"
        "Run 40I02B first."
    )

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    cfg = json.load(f)

required_cfg = [
    "aoi_id",
    "display_name",
    "monitoring_year",
    "grid_size_m",
    "expected_asu_count",
    "expected_palm_area_ha",
    "package_version",
    "source_geometry",
    "source_attributes",
    "source_class_summary",
    "source_legend",
    "source_popup_contract",
]

missing_cfg = [k for k in required_cfg if k not in cfg]
if missing_cfg:
    raise ValueError("Config fields missing: " + ", ".join(missing_cfg))

AOI = cfg["aoi_id"]
VERSION = cfg["package_version"]

src_geo = WORKDIR / cfg["source_geometry"]
src_attr = WORKDIR / cfg["source_attributes"]
src_summary = WORKDIR / cfg["source_class_summary"]
src_legend = WORKDIR / cfg["source_legend"]
src_popup = WORKDIR / cfg["source_popup_contract"]

for p in [src_geo, src_attr, src_summary, src_legend, src_popup]:
    if not p.exists():
        raise FileNotFoundError(p)

OUTDIR = WORKDIR / f"40J01_WEB_PACKAGE_{AOI}_{VERSION}"
DATA_DIR = OUTDIR / "data"
CONFIG_DIR = OUTDIR / "config"
META_DIR = OUTDIR / "metadata"

OUT_GEOJSON = DATA_DIR / f"output4__{AOI.lower()}__management_priority__{cfg['monitoring_year']}__{VERSION}.geojson"
OUT_SUMMARY = DATA_DIR / "class_summary.csv"
OUT_LEGEND = CONFIG_DIR / "legend.json"
OUT_POPUP = CONFIG_DIR / "popup_fields.json"
OUT_AOI_CONFIG = CONFIG_DIR / "aoi_config.json"
OUT_FIELDS = META_DIR / "field_inventory.json"
OUT_MODEL_CARD = META_DIR / "model_card.json"
OUT_MANIFEST = META_DIR / "manifest.json"
OUT_README = OUTDIR / "README_WEB_DEVELOPMENT.txt"
OUT_ZIP = WORKDIR / f"40J01_WEB_PACKAGE_{AOI}_{VERSION}.zip"
OUT_QC = WORKDIR / f"40J01_WEB_PACKAGE_QC_{AOI}_{VERSION}.json"

print("====================================================")
print("40J01 — GENERIC WEB PACKAGE BUILDER")
print("====================================================")
print("AOI                            :", AOI)

attrs = read_csv(src_attr)

expected_asu = int(cfg["expected_asu_count"])

if len(attrs) != expected_asu:
    raise ValueError(
        f"Expected {expected_asu} attribute rows; got {len(attrs)}."
    )

attr_by_id = {
    str(r["UNIT_ID"]): r
    for r in attrs
}

if len(attr_by_id) != expected_asu:
    raise ValueError("Attribute UNIT_ID is not unique.")

with open(src_geo, "r", encoding="utf-8") as f:
    geo = json.load(f)

features = geo.get("features", [])

if len(features) != expected_asu:
    raise ValueError(
        f"Expected {expected_asu} geometry features; got {len(features)}."
    )

geo_ids = []

for feat in features:
    uid = str(
        feat.get("properties", {}).get("UNIT_ID", "")
    )

    if not uid:
        raise ValueError("Geometry feature without UNIT_ID.")

    geo_ids.append(uid)

if len(set(geo_ids)) != expected_asu:
    raise ValueError("Geometry UNIT_ID is not unique.")

if set(geo_ids) != set(attr_by_id):
    raise ValueError("Geometry and attributes UNIT_ID sets do not match.")

# ------------------------------------------------------------
# JOIN ALL FROZEN ATTRIBUTES TO EXACT GEOMETRY
# ------------------------------------------------------------

web_features = []

for feat in features:
    uid = str(feat["properties"]["UNIT_ID"])
    attr = attr_by_id[uid]

    props = {
        k: to_native(v)
        for k, v in attr.items()
    }

    # Keep stable UI-friendly aliases.
    props["AOI_ID"] = AOI
    props["MONITORING_YEAR"] = cfg["monitoring_year"]
    props["GRID_SIZE_M"] = cfg["grid_size_m"]

    web_features.append({
        "type": "Feature",
        "properties": props,
        "geometry": feat["geometry"],
    })

web_geojson = {
    "type": "FeatureCollection",
    "name": f"Output4_{AOI}_ManagementPriority",
    "features": web_features,
}

# ------------------------------------------------------------
# PACKAGE DIRECTORIES
# ------------------------------------------------------------

if OUTDIR.exists():
    shutil.rmtree(OUTDIR)

DATA_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
META_DIR.mkdir(parents=True, exist_ok=True)

with open(OUT_GEOJSON, "w", encoding="utf-8") as f:
    json.dump(
        web_geojson,
        f,
        ensure_ascii=False,
        separators=(",", ":"),
    )

shutil.copy2(src_summary, OUT_SUMMARY)
shutil.copy2(src_legend, OUT_LEGEND)
shutil.copy2(src_popup, OUT_POPUP)

with open(OUT_AOI_CONFIG, "w", encoding="utf-8") as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)

# ------------------------------------------------------------
# FIELD INVENTORY
# ------------------------------------------------------------

fields = list(attrs[0].keys())

field_inventory = {
    "field_count": len(fields),
    "fields": fields,
    "required_key": "UNIT_ID",
    "class_field": "MANAGEMENT_PRIORITY_CLASS",
    "geometry_join": "UNIT_ID one-to-one",
}

with open(OUT_FIELDS, "w", encoding="utf-8") as f:
    json.dump(field_inventory, f, indent=2, ensure_ascii=False)

# ------------------------------------------------------------
# MODEL CARD / DELIVERY NOTES
# ------------------------------------------------------------

model_card = {
    "product": "Output 4 — Productivity Potential & Management Priority",
    "aoi_id": AOI,
    "monitoring_year": cfg["monitoring_year"],
    "asu_framework": f"{cfg['grid_size_m']} x {cfg['grid_size_m']} m",
    "expected_asu_count": expected_asu,
    "expected_palm_area_ha": cfg["expected_palm_area_ha"],
    "primary_process_model": "PALMSIM",
    "representative_benchmark_model": "APSIM OilPalm",
    "productivity_claim": "modelled/indicative productivity potential",
    "actual_ffb_validation": bool(cfg.get("local_ffb_validation", False)),
    "class4_guardrail": "Replanting Evaluation Priority; not automatic replanting order",
    "class0_rendered": bool(cfg.get("class0_rendered", True)),
    "outside_palm_domain": cfg.get("outside_palm_domain", "transparent/noData"),
    "scientific_results_changed_in_packaging": False,
}

with open(OUT_MODEL_CARD, "w", encoding="utf-8") as f:
    json.dump(model_card, f, indent=2, ensure_ascii=False)

# ------------------------------------------------------------
# README FOR WEB DEVELOPER
# ------------------------------------------------------------

readme = f"""OUTPUT 4 WEB DEVELOPMENT PACKAGE
================================

AOI
---
AOI ID          : {AOI}
Display name    : {cfg['display_name']}
Monitoring year : {cfg['monitoring_year']}
ASU framework   : {cfg['grid_size_m']} x {cfg['grid_size_m']} m
ASU count       : {expected_asu}
Palm area       : {cfg['expected_palm_area_ha']:.2f} ha

PRIMARY WEB DATA
----------------
data/{OUT_GEOJSON.name}

JOIN KEY
--------
UNIT_ID

DEFAULT STYLE
-------------
config/legend.json

POPUP CONTRACT
--------------
config/popup_fields.json

AOI CONFIG
----------
config/aoi_config.json

IMPORTANT INTERPRETATION
------------------------
- Productivity = modelled/indicative potential, NOT locally validated actual FFB yield.
- Direct PALMSIM and fallback pathways must remain distinguishable.
- Class 0 must be rendered, not treated as NoData.
- Class 4 = Replanting Evaluation Priority, NOT automatic replanting.
- Outside Output-1 palm geometry = transparent / NoData.

FOR ANOTHER AOI
---------------
Normally DO NOT edit the web front-end logic.

Replace/update only:
1. Exact clipped 500 m ASU GeoJSON.
2. Frozen 40I01 delivery master CSV.
3. 40I02B class-summary / legend / popup-contract outputs.
4. AOI config values:
   - aoi_id
   - display_name
   - monitoring_year
   - expected_asu_count
   - expected_palm_area_ha
   - source file names
   - package_version
5. If the scientific model version/calibration changes, update the model/version metadata.

Keep unchanged when the Output-4 framework is unchanged:
- UNIT_ID join logic
- Class 0–4 semantic labels
- default color convention
- popup schema structure
- Class-4 guardrail
- outside-palm transparency rule
- direct-vs-fallback distinction
- web field naming conventions

This package does NOT recalculate any scientific result.
"""

OUT_README.write_text(readme, encoding="utf-8")

# ------------------------------------------------------------
# MANIFEST
# ------------------------------------------------------------

files_for_manifest = [
    OUT_GEOJSON,
    OUT_SUMMARY,
    OUT_LEGEND,
    OUT_POPUP,
    OUT_AOI_CONFIG,
    OUT_FIELDS,
    OUT_MODEL_CARD,
    OUT_README,
]

manifest = {
    "package_id": f"OUTPUT4_{AOI}_{VERSION}",
    "created_utc": datetime.now(timezone.utc).isoformat(),
    "files": [
        str(p.relative_to(OUTDIR)).replace("\\", "/")
        for p in files_for_manifest
    ],
    "primary_web_vector": str(OUT_GEOJSON.relative_to(OUTDIR)).replace("\\", "/"),
    "ready_for_web_development": True,
}

with open(OUT_MANIFEST, "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2, ensure_ascii=False)

# ------------------------------------------------------------
# ZIP
# ------------------------------------------------------------

if OUT_ZIP.exists():
    OUT_ZIP.unlink()

with zipfile.ZipFile(
    OUT_ZIP,
    "w",
    compression=zipfile.ZIP_DEFLATED,
) as z:
    for path in OUTDIR.rglob("*"):
        if path.is_file():
            z.write(
                path,
                arcname=str(path.relative_to(OUTDIR)).replace("\\", "/"),
            )

checks = {
    "attribute_rows_match_expected": len(attrs) == expected_asu,
    "geometry_features_match_expected": len(features) == expected_asu,
    "unit_id_exact_match": set(geo_ids) == set(attr_by_id),
    "web_geojson_created": OUT_GEOJSON.exists(),
    "legend_created": OUT_LEGEND.exists(),
    "popup_contract_created": OUT_POPUP.exists(),
    "model_card_created": OUT_MODEL_CARD.exists(),
    "manifest_created": OUT_MANIFEST.exists(),
    "zip_created": OUT_ZIP.exists(),
}

status = (
    "PASS_WEB_DEVELOPMENT_PACKAGE_READY"
    if all(checks.values())
    else "REVIEW"
)

qc = {
    "status": status,
    "aoi_id": AOI,
    "checks": checks,
    "package_folder": str(OUTDIR),
    "zip_file": str(OUT_ZIP),
    "primary_web_geojson": str(OUT_GEOJSON),
}

with open(OUT_QC, "w", encoding="utf-8") as f:
    json.dump(qc, f, indent=2, ensure_ascii=False)

print("\n====================================================")
print("40J01 FINISHED")
print("====================================================")
print("Status                         :", status)
print("Package folder                 :", OUTDIR)
print("ZIP                            :", OUT_ZIP)
print("Primary web GeoJSON            :", OUT_GEOJSON)
print("README                         :", OUT_README)
print("Scientific result changed      : False")
print("====================================================")
