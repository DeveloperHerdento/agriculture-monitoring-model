
# ============================================================
# OUTPUT 4 / 40J02
# FULL REPRODUCIBILITY + WEB HANDOFF ARCHIVE
# SIAK_AOI01 | V1
#
# Creates a final package comparable to Output 3:
# 01_WEB / 02_NOTEBOOK / 03_SCRIPTS / 04_CONFIG
# 05_MODEL_ARTIFACTS / 06_QA_METADATA / 07_PREVIEW
#
# STANDARD LIBRARY ONLY
# NO scientific recalculation
# ============================================================

from pathlib import Path
import hashlib
import json
import math
import platform
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone

# ------------------------------------------------------------
# 0. CONFIG
# ------------------------------------------------------------

WORKDIR = Path(
    r"C:\Users\user\Documents\KERJA\SPATIAL DATA ANALYST INTERN\04_YIELD"
)

AOI_ID = "SIAK_AOI01"
DISPLAY_NAME = "SIAK_AOI01"
REFERENCE_YEAR = 2025
MONITORING_YEAR = 2025
GRID_SIZE_M = 500
PROJECTED_CRS = "EPSG:32647"

EXPECTED_ASU_COUNT = 820
EXPECTED_PALM_AREA_HA = 13867.099001884668
PACKAGE_VERSION = "v1"

WEB_PACKAGE_DIR = WORKDIR / f"40J01_WEB_PACKAGE_{AOI_ID}_{PACKAGE_VERSION}"
WEB_PACKAGE_ZIP = WORKDIR / f"40J01_WEB_PACKAGE_{AOI_ID}_{PACKAGE_VERSION}.zip"

J01_CONFIG = WORKDIR / f"40J01_WEB_PACKAGE_CONFIG_{AOI_ID}_V1.json"

EXACT_ASU_GEOJSON = WORKDIR / f"40B03A_FINAL_ASU_500M_EXACT_{AOI_ID}_V1.geojson"
FINAL_MASTER_CSV = WORKDIR / f"40I01_FINAL_OUTPUT4_DELIVERY_MASTER_820_{AOI_ID}_V1.csv"

NOTEBOOK_CANDIDATES = [
    WORKDIR / "OUTPUT 4.ipynb",
    WORKDIR.parent / "OUTPUT 4.ipynb",
    WORKDIR.parent / "OUTPUT4.ipynb",
]

PREVIEW_CANDIDATES = [
    WORKDIR
    / "40I02A_EXACT_POLYGON_BROWSER_PREVIEW_SIAK_AOI01_V1"
    / "40I02A_EXACT_ASU_MANAGEMENT_PRIORITY_PREVIEW_NO_BOUNDARY_SIAK_AOI01_V2.html",

    WORKDIR
    / "40I02A_EXACT_POLYGON_BROWSER_PREVIEW_SIAK_AOI01_V1"
    / "40I02A_EXACT_ASU_MANAGEMENT_PRIORITY_PREVIEW_SIAK_AOI01_V1.html",
]

OUTDIR = WORKDIR / f"40J02_OUTPUT4_{AOI_ID}_FINAL_PACKAGE_{PACKAGE_VERSION}"
OUT_ZIP = WORKDIR / f"40J02_OUTPUT4_{AOI_ID}_FINAL_PACKAGE_{PACKAGE_VERSION}.zip"
OUT_QC = WORKDIR / f"40J02_FINAL_PACKAGE_QC_{AOI_ID}_{PACKAGE_VERSION}.json"

MAX_SMALL_FILE = 25 * 1024 * 1024

print("====================================================")
print("40J02 — FULL REPRODUCIBILITY + WEB HANDOFF ARCHIVE")
print("====================================================")
print("AOI                            :", AOI_ID)


# ------------------------------------------------------------
# 1. HELPERS
# ------------------------------------------------------------

def copy_file(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def write_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def rel(path):
    return str(path.relative_to(OUTDIR)).replace("\\", "/")


def first_existing(paths):
    for p in paths:
        if p.exists() and p.is_file():
            return p
    return None


def pip_freeze_text():
    try:
        cp = subprocess.run(
            [sys.executable, "-m", "pip", "freeze"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60,
            check=False,
        )
        if cp.returncode == 0:
            return cp.stdout.strip()
        return "pip freeze failed:\n" + cp.stderr.strip()
    except Exception as e:
        return "pip freeze unavailable: " + repr(e)


def md_cell(text):
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": [x + "\n" for x in text.strip().splitlines()],
    }


def code_cell(text):
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [x + "\n" for x in text.strip().splitlines()],
    }


# ------------------------------------------------------------
# 2. REQUIRED INPUT GATE
# ------------------------------------------------------------

required = {
    "40J01_WEB_PACKAGE": WEB_PACKAGE_DIR,
    "EXACT_ASU_GEOJSON": EXACT_ASU_GEOJSON,
    "FINAL_MASTER_CSV": FINAL_MASTER_CSV,
}

missing = [name for name, path in required.items() if not path.exists()]

if missing:
    raise FileNotFoundError(
        "Missing required prepared outputs:\n- " + "\n- ".join(missing)
    )

print("Required prepared outputs      : PASS")


# ------------------------------------------------------------
# 3. PACKAGE TREE
# ------------------------------------------------------------

if OUTDIR.exists():
    shutil.rmtree(OUTDIR)

folders = {
    "web": OUTDIR / "01_WEB",
    "notebook": OUTDIR / "02_NOTEBOOK",
    "scripts": OUTDIR / "03_SCRIPTS",
    "config": OUTDIR / "04_CONFIG",
    "model": OUTDIR / "05_MODEL_ARTIFACTS",
    "qa": OUTDIR / "06_QA_METADATA",
    "preview": OUTDIR / "07_PREVIEW",
}

for d in folders.values():
    d.mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------
# 4. 01_WEB
# ------------------------------------------------------------

for src in WEB_PACKAGE_DIR.rglob("*"):
    if src.is_file():
        copy_file(src, folders["web"] / src.relative_to(WEB_PACKAGE_DIR))

if WEB_PACKAGE_ZIP.exists():
    copy_file(WEB_PACKAGE_ZIP, folders["web"] / WEB_PACKAGE_ZIP.name)

print("01_WEB                         : PASS")


# ------------------------------------------------------------
# 5. 02_NOTEBOOK
# ------------------------------------------------------------

working_nb = first_existing(NOTEBOOK_CANDIDATES)
working_nb_status = "NOT_FOUND"

if working_nb is not None:
    copy_file(working_nb, folders["notebook"] / "OUTPUT 4.ipynb")
    working_nb_status = f"COPIED_FROM:{working_nb}"

master_nb = {
    "cells": [
        md_cell(f"""
# MASTER PIPELINE OUTPUT 4

Product: **Productivity Potential & Management Priority**  
Pilot AOI: **{AOI_ID}**  
Monitoring year: **{MONITORING_YEAR}**  
ASU framework: **{GRID_SIZE_M} × {GRID_SIZE_M} m**

This is the canonical reproducibility/AOI-transfer notebook.

Guardrails:
- productivity = modelled/indicative potential, not locally validated actual FFB yield;
- PALMSIM = primary experimental process model;
- APSIM OilPalm = representative benchmark;
- direct and fallback pathways remain distinguishable;
- Class 4 = Replanting Evaluation Priority, not automatic replanting.
"""),

        code_cell("""
from pathlib import Path
import json

PACKAGE_ROOT = Path.cwd().resolve().parent
CONFIG_PATH = PACKAGE_ROOT / "04_CONFIG" / "SIAK_AOI01_OUTPUT4_CONFIG.json"

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    cfg = json.load(f)

cfg
"""),

        md_cell("""
## AOI transfer rule

For another AOI, replace AOI-specific config and prepared inputs.
Keep the Output-4 schema, class semantics, guardrails, QA gates and web contract.
Siak numerical thresholds/calibration must only be used as transfer-test V0
until AOI-specific domain-shift and sensitivity QA passes.
"""),

        code_cell("""
for name in [
    "01_WEB",
    "02_NOTEBOOK",
    "03_SCRIPTS",
    "04_CONFIG",
    "05_MODEL_ARTIFACTS",
    "06_QA_METADATA",
    "07_PREVIEW",
]:
    p = PACKAGE_ROOT / name
    print(name, "| exists:", p.exists(), "| files:", sum(1 for x in p.rglob("*") if x.is_file()))
"""),

        md_cell("""
## Runner

Use `03_SCRIPTS/run_output4.py` with an explicit AOI config.
The runner intentionally does not guess among multiple development script versions.
Full raw-source zero-to-final one-click execution is **not claimed** by this archive.
"""),
    ],
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {
            "name": "python",
            "version": platform.python_version(),
        },
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

write_json(
    folders["notebook"] / "MASTER_PIPELINE_OUTPUT4.ipynb",
    master_nb,
)

print("02_NOTEBOOK                    :", working_nb_status)
print("                                 MASTER_PIPELINE_OUTPUT4.ipynb generated")


# ------------------------------------------------------------
# 6. 03_SCRIPTS
# ------------------------------------------------------------

script_candidates = []

for p in WORKDIR.rglob("*.py"):
    if not p.is_file():
        continue

    if OUTDIR in p.parents:
        continue

    parts_lower = {x.lower() for x in p.parts}
    if "__pycache__" in parts_lower or "site-packages" in parts_lower:
        continue

    name_u = p.name.upper()

    if not (
        name_u.startswith("40")
        or "OUTPUT4" in name_u
        or "PALMSIM" in name_u
        or "APSIM" in name_u
    ):
        continue

    if p.stat().st_size <= MAX_SMALL_FILE:
        script_candidates.append(p)

seen = set()
copied_scripts = 0

for p in sorted(script_candidates, key=lambda x: str(x).lower()):
    rp = str(p.resolve()).lower()
    if rp in seen:
        continue
    seen.add(rp)

    dst = folders["scripts"] / p.name

    if dst.exists():
        i = 2
        while dst.exists():
            dst = folders["scripts"] / f"{p.stem}__DUP{i}{p.suffix}"
            i += 1

    copy_file(p, dst)
    copied_scripts += 1

runner_text = r"""
#!/usr/bin/env python
from pathlib import Path
import argparse
import json
import subprocess
import sys

def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def validate(cfg):
    required = [
        "aoi_id",
        "monitoring_year",
        "projected_crs",
        "grid_size_m",
        "inputs",
        "transfer_policy",
    ]
    missing = [k for k in required if k not in cfg]
    if missing:
        raise ValueError("Missing config keys: " + ", ".join(missing))

    print("CONFIG VALID")
    print("AOI:", cfg["aoi_id"])
    print("Monitoring year:", cfg["monitoring_year"])
    print("CRS:", cfg["projected_crs"])
    print("Grid:", cfg["grid_size_m"], "m")

def resolve_script(config_path, script_value):
    p = Path(script_value)
    if p.is_absolute():
        return p

    package_root = config_path.resolve().parent.parent

    candidates = [
        package_root / "03_SCRIPTS" / script_value,
        package_root / script_value,
        config_path.resolve().parent / script_value,
    ]

    for c in candidates:
        if c.exists():
            return c

    return candidates[0]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--run-stage")
    args = ap.parse_args()

    config_path = Path(args.config)
    cfg = load_config(config_path)

    if args.validate:
        validate(cfg)

    stage_map = cfg.get("stage_script_map", {})

    if args.list:
        if not stage_map:
            print("No explicit stage_script_map configured.")
        for key, value in stage_map.items():
            print(key, "->", value)

    if args.run_stage:
        if args.run_stage not in stage_map:
            raise KeyError(
                f"Stage {args.run_stage!r} is not explicitly mapped. "
                "Do not auto-guess a development script."
            )

        script = resolve_script(config_path, stage_map[args.run_stage])

        if not script.exists():
            raise FileNotFoundError(script)

        print("Running:", script)
        subprocess.run(
            [sys.executable, str(script)],
            cwd=str(script.parent),
            check=True,
        )

if __name__ == "__main__":
    main()
"""

write_text(
    folders["scripts"] / "run_output4.py",
    runner_text.strip() + "\n",
)

print("03_SCRIPTS                     :", copied_scripts, "archived + run_output4.py")


# ------------------------------------------------------------
# 7. 04_CONFIG
# ------------------------------------------------------------

j01_cfg = {}

if J01_CONFIG.exists():
    with open(J01_CONFIG, "r", encoding="utf-8") as f:
        j01_cfg = json.load(f)

siak_cfg = {
    "schema_version": "OUTPUT4_AOI_CONFIG_V1",
    "aoi_id": AOI_ID,
    "display_name": DISPLAY_NAME,
    "reference_year": REFERENCE_YEAR,
    "monitoring_year": MONITORING_YEAR,
    "projected_crs": PROJECTED_CRS,
    "grid_size_m": GRID_SIZE_M,
    "expected_asu_count": EXPECTED_ASU_COUNT,
    "expected_palm_area_ha": EXPECTED_PALM_AREA_HA,

    "inputs": {
        "output1_palm_geometry": EXACT_ASU_GEOJSON.name,
        "output2_age_context": "AOI_SPECIFIC_INPUT",
        "output3_condition_context": "AOI_SPECIFIC_INPUT",
        "soil": "SoilGrids_2.0_0_100cm",
        "rainfall": "CHIRPS_v2_Final_primary",
        "era5_land": "ERA5-Land",
        "final_master_csv": FINAL_MASTER_CSV.name,
    },

    "model_roles": {
        "primary_process_model": "PALMSIM",
        "benchmark_process_model": "APSIM OilPalm",
        "supervised_yield_ml": "NO_GO_UNTIL_LOCAL_ACTUAL_FFB_LABELS",
        "priority_integration": "MCDA_RULE_BASED_WITH_SENSITIVITY",
    },

    "transfer_policy": {
        "logic_schema_reusable": True,
        "class_0_4_semantics_reusable": True,
        "web_contract_reusable": True,
        "siak_numeric_thresholds_universally_valid": False,
        "threshold_use_for_new_aoi": "TRANSFER_TEST_V0_ONLY_UNTIL_QA",
        "requires_domain_shift_qa": True,
        "requires_area_and_count_recalculation": True,
        "requires_climate_mapping_rebuild": True,
    },

    "web": {
        "default_show_asu_boundaries": False,
        "class0_rendered": True,
        "outside_palm_domain": "transparent/noData",
        "join_key": "UNIT_ID",
    },

    "stage_script_map": {
        "40I02B_DISPLAY_CONTRACT": "40I02B_WEB_DISPLAY_CONTRACT_FREEZE_SIAK_AOI01_V1.py",
        "40J01_WEB_PACKAGE": "40J01_GENERIC_WEB_DEVELOPMENT_PACKAGE_BUILDER_V1.py",
    },

    "web_subset_config": j01_cfg,
}

write_json(
    folders["config"] / f"{AOI_ID}_OUTPUT4_CONFIG.json",
    siak_cfg,
)

template_cfg = json.loads(json.dumps(siak_cfg))

template_cfg.update({
    "aoi_id": "AOI_ID_HERE",
    "display_name": "AOI_DISPLAY_NAME_HERE",
    "reference_year": "YYYY",
    "monitoring_year": "YYYY",
    "projected_crs": "EPSG:XXXXX",
    "expected_asu_count": "RECALCULATE",
    "expected_palm_area_ha": "RECALCULATE",
})

template_cfg["inputs"].update({
    "output1_palm_geometry": "NEW_AOI_OUTPUT1_PALM_GEOMETRY",
    "output2_age_context": "NEW_AOI_OUTPUT2_AGE_CONTEXT",
    "output3_condition_context": "NEW_AOI_OUTPUT3_CONDITION_CONTEXT",
    "final_master_csv": "GENERATED_BY_NEW_AOI_PIPELINE",
})

template_cfg["stage_script_map"] = {
    "NOTE": (
        "Populate explicit canonical script mappings for the new AOI. "
        "Do not auto-select among multiple development versions."
    )
}

write_json(
    folders["config"] / "OUTPUT4_AOI_TEMPLATE.json",
    template_cfg,
)

if J01_CONFIG.exists():
    copy_file(
        J01_CONFIG,
        folders["config"] / J01_CONFIG.name,
    )

transfer_guide = f"""
OUTPUT 4 — AOI TRANSFER GUIDE
=============================

CHANGE FOR A NEW AOI
--------------------
1. AOI ID / display name
2. Output-1 palm boundary/mask
3. reference + monitoring year
4. projected CRS
5. exact clipped 500 m ASU geometry
6. Output-2 age context
7. Output-3 condition context
8. SoilGrids extraction
9. CHIRPS + ERA5-Land cell mapping and prepared weather
10. PALMSIM prepared inputs/scenarios
11. APSIM representative benchmark design
12. expected ASU count
13. exact palm area
14. AOI-specific filenames / asset prefixes / package version

KEEP REUSABLE BY DEFAULT
------------------------
- Output-4 schema
- Class 0–4 semantic schema
- UNIT_ID join concept
- direct-vs-fallback distinction
- Class-4 guardrail
- outside-palm transparency
- legend/popup contract structure
- QA/freeze discipline
- web package contract

RE-TEST FOR EVERY NEW AOI
-------------------------
- ASU suitability
- source coverage
- age support
- climate mapping
- PALMSIM/APSIM behavior
- structural model disagreement
- fallback performance
- productivity thresholds
- condition/age sensitivity
- class switching sensitivity
- confidence distribution
- class-area distribution
- geometry/area freeze

Siak numerical thresholds are transfer-test V0 only until AOI-specific QA passes.
"""

write_text(
    folders["config"] / "AOI_TRANSFER_GUIDE.txt",
    transfer_guide.strip() + "\n",
)

print("04_CONFIG                      : PASS")


# ------------------------------------------------------------
# 8. 05_MODEL_ARTIFACTS
# ------------------------------------------------------------

allowed_model_ext = {
    ".json", ".csv", ".txt", ".md", ".apsimx", ".yaml", ".yml", ".ini"
}

model_prefix = ("40C", "40D", "40E", "40F", "40G", "40H")
skip_tokens = ("CHIRPS_DAILY", "ERA5L_DAILY", "WEATHER_DAILY", "CACHE")

model_count = 0
seen = set()

for p in WORKDIR.rglob("*"):
    if not p.is_file():
        continue
    if OUTDIR in p.parents:
        continue
    if p.suffix.lower() not in allowed_model_ext:
        continue

    name_u = p.name.upper()

    if not name_u.startswith(model_prefix):
        continue
    if any(tok in name_u for tok in skip_tokens):
        continue
    if p.stat().st_size > MAX_SMALL_FILE:
        continue

    rp = str(p.resolve()).lower()
    if rp in seen:
        continue
    seen.add(rp)

    dst = folders["model"] / p.name

    if dst.exists():
        i = 2
        while dst.exists():
            dst = folders["model"] / f"{p.stem}__DUP{i}{p.suffix}"
            i += 1

    copy_file(p, dst)
    model_count += 1

write_text(
    folders["model"] / "MODEL_ARTIFACTS_README.txt",
    f"""
OUTPUT 4 MODEL ARTIFACTS — {AOI_ID}
===================================

PALMSIM = primary experimental process model.
APSIM OilPalm = representative process/scenario benchmark.
Supervised yield ML = not activated without local actual FFB labels.
Final quantitative claim = modelled/indicative productivity potential.

Large raw climate caches are intentionally not duplicated here.

For another AOI:
- rebuild AOI-specific climate/model inputs;
- rerun PALMSIM/APSIM and uncertainty QA;
- do not treat Siak thresholds as locally validated values.
""".strip() + "\n",
)

print("05_MODEL_ARTIFACTS             :", model_count, "files")


# ------------------------------------------------------------
# 9. 06_QA_METADATA
# ------------------------------------------------------------

qa_ext = {".json", ".csv", ".txt", ".md"}
qa_tokens = ("QC", "FREEZE", "SUMMARY", "MANIFEST", "MODEL_CARD", "AUDIT", "METADATA")

qa_count = 0
seen = set()

for p in WORKDIR.rglob("*"):
    if not p.is_file():
        continue
    if OUTDIR in p.parents:
        continue
    if p.suffix.lower() not in qa_ext:
        continue

    name_u = p.name.upper()

    if not name_u.startswith("40"):
        continue
    if not any(tok in name_u for tok in qa_tokens):
        continue
    if p.stat().st_size > MAX_SMALL_FILE:
        continue

    rp = str(p.resolve()).lower()
    if rp in seen:
        continue
    seen.add(rp)

    dst = folders["qa"] / p.name

    if dst.exists():
        i = 2
        while dst.exists():
            dst = folders["qa"] / f"{p.stem}__DUP{i}{p.suffix}"
            i += 1

    copy_file(p, dst)
    qa_count += 1

write_text(
    folders["qa"] / "environment_runtime.txt",
    f"""
OUTPUT 4 ENVIRONMENT SNAPSHOT
=============================

Created UTC       : {datetime.now(timezone.utc).isoformat()}
Platform          : {platform.platform()}
Python executable : {sys.executable}
Python version    : {platform.python_version()}
Working directory : {WORKDIR}

PIP FREEZE
----------
{pip_freeze_text()}
""".strip() + "\n",
)

print("06_QA_METADATA                 :", qa_count, "files + environment")


# ------------------------------------------------------------
# 10. 07_PREVIEW
# ------------------------------------------------------------

preview = first_existing(PREVIEW_CANDIDATES)
preview_status = "NOT_FOUND"

if preview is not None:
    copy_file(
        preview,
        folders["preview"] / "OUTPUT4_INTERACTIVE_PREVIEW.html",
    )
    preview_status = f"COPIED_FROM:{preview}"

write_text(
    folders["preview"] / "README_PREVIEW.txt",
    """
OUTPUT 4 PREVIEW
================

Human review / presentation only.

The analytical and web source of truth is the exact GeoJSON plus frozen
attributes under 01_WEB, not the preview HTML or a screenshot.
""".strip() + "\n",
)

print("07_PREVIEW                     :", preview_status)


# ------------------------------------------------------------
# 11. ROOT README
# ------------------------------------------------------------

write_text(
    OUTDIR / "README_OUTPUT4.txt",
    f"""
OUTPUT 4 FINAL PACKAGE — {AOI_ID}
================================

Product:
Productivity Potential & Management Priority

AOI:
{AOI_ID}

Monitoring year:
{MONITORING_YEAR}

ASU:
Regular {GRID_SIZE_M} x {GRID_SIZE_M} m framework clipped to exact palm geometry.

Frozen domain:
{EXPECTED_ASU_COUNT} ASUs
{EXPECTED_PALM_AREA_HA:.2f} ha exact palm area

PACKAGE
-------
01_WEB
    PASS 40J01 deployable web subset.

02_NOTEBOOK
    OUTPUT 4.ipynb working snapshot when found.
    MASTER_PIPELINE_OUTPUT4.ipynb canonical reproducibility/AOI-transfer notebook.

03_SCRIPTS
    Archived Output-4 scripts + reusable run_output4.py.

04_CONFIG
    Siak AOI config + reusable OUTPUT4_AOI_TEMPLATE.json + transfer guide.

05_MODEL_ARTIFACTS
    Selected PALMSIM/APSIM/process-model artifacts.

06_QA_METADATA
    QC/freeze/summary/manifest assets + environment + checksums.

07_PREVIEW
    Interactive presentation/QC HTML when available.

SCIENTIFIC CLAIM
----------------
Not a locally validated actual FFB yield prediction product.
Productivity = modelled/indicative potential.

PALMSIM = primary experimental process model.
APSIM OilPalm = representative process/scenario benchmark.
Class 4 = Replanting Evaluation Priority, not automatic replanting.

AOI TRANSFER
------------
Logic/schema/web contract are reusable.
AOI-specific inputs, CRS, area/count, climate mapping and model inputs must be rebuilt.
Siak numerical thresholds/calibration are only transfer-test V0 until new-AOI QA passes.

REPRODUCIBILITY SCOPE
---------------------
This archive provides the full delivery/reproducibility framework and validated
prepared-output/web packaging chain.

It does NOT claim a validated raw-source zero-to-final one-click 40A–40J run.
Use explicit canonical stage mappings instead of guessing among development versions.
""".strip() + "\n",
)

print("README                         : generated")


# ------------------------------------------------------------
# 12. INVENTORY + SHA256
# ------------------------------------------------------------

inventory_files = sorted(
    [p for p in OUTDIR.rglob("*") if p.is_file()],
    key=lambda p: rel(p).lower(),
)

inventory = [
    {
        "path": rel(p),
        "size_bytes": p.stat().st_size,
        "sha256": sha256_file(p),
    }
    for p in inventory_files
]

write_json(
    folders["qa"] / "package_inventory.json",
    {
        "package_id": f"OUTPUT4_{AOI_ID}_FINAL_{PACKAGE_VERSION}",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "files": inventory,
    },
)

write_text(
    folders["qa"] / "SHA256SUMS.txt",
    "\n".join(
        f'{x["sha256"]}  {x["path"]}'
        for x in inventory
    ) + "\n",
)

write_json(
    folders["qa"] / "FINAL_PACKAGE_MANIFEST.json",
    {
        "package_id": f"OUTPUT4_{AOI_ID}_FINAL_{PACKAGE_VERSION}",
        "status": "PASS_FINAL_ARCHIVE_READY",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "aoi_id": AOI_ID,
        "monitoring_year": MONITORING_YEAR,
        "reference_year": REFERENCE_YEAR,
        "grid_size_m": GRID_SIZE_M,
        "projected_crs": PROJECTED_CRS,
        "expected_asu_count": EXPECTED_ASU_COUNT,
        "expected_palm_area_ha": EXPECTED_PALM_AREA_HA,
        "scientific_results_changed_by_40J02": False,
        "working_notebook_status": working_nb_status,
        "preview_status": preview_status,
        "reproducibility_scope": (
            "Full archive/AOI-transfer framework. "
            "Raw-source zero-to-final one-click execution is not claimed."
        ),
    },
)


# ------------------------------------------------------------
# 13. ZIP
# ------------------------------------------------------------

if OUT_ZIP.exists():
    OUT_ZIP.unlink()

with zipfile.ZipFile(
    OUT_ZIP,
    "w",
    compression=zipfile.ZIP_DEFLATED,
    compresslevel=6,
) as z:
    for p in sorted(
        [x for x in OUTDIR.rglob("*") if x.is_file()],
        key=lambda p: rel(p).lower(),
    ):
        z.write(p, arcname=rel(p))


# ------------------------------------------------------------
# 14. FINAL QC
# ------------------------------------------------------------

checks = {
    "web_subset_present": any(folders["web"].rglob("*")),
    "primary_web_geojson_present": len(list(folders["web"].rglob("*.geojson"))) >= 1,
    "master_pipeline_notebook_present": (
        folders["notebook"] / "MASTER_PIPELINE_OUTPUT4.ipynb"
    ).exists(),
    "run_output4_present": (
        folders["scripts"] / "run_output4.py"
    ).exists(),
    "aoi_template_present": (
        folders["config"] / "OUTPUT4_AOI_TEMPLATE.json"
    ).exists(),
    "siak_config_present": (
        folders["config"] / f"{AOI_ID}_OUTPUT4_CONFIG.json"
    ).exists(),
    "transfer_guide_present": (
        folders["config"] / "AOI_TRANSFER_GUIDE.txt"
    ).exists(),
    "environment_present": (
        folders["qa"] / "environment_runtime.txt"
    ).exists(),
    "checksums_present": (
        folders["qa"] / "SHA256SUMS.txt"
    ).exists(),
    "manifest_present": (
        folders["qa"] / "FINAL_PACKAGE_MANIFEST.json"
    ).exists(),
    "root_readme_present": (
        OUTDIR / "README_OUTPUT4.txt"
    ).exists(),
    "zip_created": OUT_ZIP.exists(),
}

status = (
    "PASS_40J02_FINAL_REPRODUCIBILITY_WEB_ARCHIVE"
    if all(checks.values())
    else "REVIEW"
)

write_json(
    OUT_QC,
    {
        "status": status,
        "aoi_id": AOI_ID,
        "checks": checks,
        "working_notebook_status": working_nb_status,
        "preview_status": preview_status,
        "archived_script_count": copied_scripts + 1,
        "archived_model_artifact_count": model_count,
        "archived_qa_artifact_count": qa_count,
        "final_package_folder": str(OUTDIR),
        "final_zip": str(OUT_ZIP),
        "scientific_results_changed": False,
    },
)

print("\n====================================================")
print("40J02 FINISHED")
print("====================================================")
print("Status                         :", status)
print("Final package folder           :", OUTDIR)
print("Final ZIP                      :", OUT_ZIP)
print("Working OUTPUT 4.ipynb         :", working_nb_status)
print("Archived scripts               :", copied_scripts + 1)
print("Model artifacts                :", model_count)
print("QA/metadata artifacts          :", qa_count)
print("Preview                        :", preview_status)
print("Scientific result changed      : False")
print("====================================================")
