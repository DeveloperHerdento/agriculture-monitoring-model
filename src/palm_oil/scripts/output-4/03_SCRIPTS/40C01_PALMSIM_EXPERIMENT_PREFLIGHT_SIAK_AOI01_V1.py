# ============================================================
# OUTPUT 4 / 40C01
# PALMSIM EXPERIMENT PREFLIGHT + SCENARIO FREEZE
# SIAK_AOI01
#
# RUN THIS SCRIPT FROM JUPYTER THROUGH subprocess.
#
# PURPOSE
# 1) Audit the frozen 40B05 PALMSIM input package.
# 2) Verify 2001-2025 CHIRPS + ERA5-Land source coverage.
# 3) Discover the local PALMSIM installation/source without changing it.
# 4) Freeze a transparent one-at-a-time sensitivity design.
# 5) Build the eligible ASU x scenario run manifest.
#
# IMPORTANT
# - This step DOES NOT run PALMSIM yet.
# - No missing age is imputed.
# - Palm density and soil depth are SCENARIO assumptions, not observations.
# - Actual FFB accuracy is NOT evaluated because local FFB labels are absent.
# ============================================================

from pathlib import Path
import os
import sys
import json
import importlib.util
import traceback
import numpy as np
import pandas as pd

WORKDIR = Path(
    r"C:\Users\user\Documents\KERJA\SPATIAL DATA ANALYST INTERN\04_YIELD"
)
os.chdir(WORKDIR)

# ------------------------------------------------------------
# INPUTS
# ------------------------------------------------------------

PALMSIM_MANIFEST = WORKDIR / "40B05_PALMSIM_STATIC_INPUT_MANIFEST_SIAK_AOI01_V1.csv"
MASTER = WORKDIR / "40B05_COMMON_MODEL_INPUT_MASTER_SIAK_AOI01_V1.csv"

CHIRPS_DAILY = WORKDIR / (
    "40B04B1_CHIRPS_V2_DAILY_NATIVE_CELLS_"
    "2001_2025_SIAK_AOI01_V1.csv"
)

ERA5_DAILY = WORKDIR / (
    "40B04B2_ERA5LAND_DAILY_NATIVE_CELLS_"
    "2001_2025_SIAK_AOI01_V4.csv"
)

# ------------------------------------------------------------
# OUTPUTS
# ------------------------------------------------------------

OUT_SCENARIOS = WORKDIR / "40C01_PALMSIM_SENSITIVITY_SCENARIOS_SIAK_AOI01_V1.csv"
OUT_ELIGIBLE = WORKDIR / "40C01_PALMSIM_ELIGIBLE_ASU_MANIFEST_SIAK_AOI01_V1.csv"
OUT_RUN_MANIFEST = WORKDIR / "40C01_PALMSIM_PLANNED_RUN_MANIFEST_SIAK_AOI01_V1.csv"
OUT_CLIMATE_QC = WORKDIR / "40C01_PALMSIM_CLIMATE_PREFLIGHT_QC_SIAK_AOI01_V1.csv"
OUT_QC = WORKDIR / "40C01_PALMSIM_PREFLIGHT_QC_SIAK_AOI01_V1.json"

START = pd.Timestamp("2001-01-01")
END = pd.Timestamp("2025-12-31")
EXPECTED_DAYS = len(pd.date_range(START, END, freq="D"))

print("====================================================")
print("40C01 — PALMSIM EXPERIMENT PREFLIGHT")
print("====================================================")
print("Python:", sys.executable)
print("Workdir:", WORKDIR)

for p in [PALMSIM_MANIFEST, MASTER, CHIRPS_DAILY, ERA5_DAILY]:
    if not p.exists():
        raise FileNotFoundError(f"Missing required input: {p}")

# ------------------------------------------------------------
# 1. LOAD FROZEN 40B05 INPUT
# ------------------------------------------------------------

pal = pd.read_csv(PALMSIM_MANIFEST)
master = pd.read_csv(MASTER)

if len(pal) != 820:
    raise ValueError(f"Expected 820 PALMSIM manifest rows, found {len(pal)}")

required_pal = [
    "UNIT_ID",
    "ASU_LATITUDE",
    "AGE_PROXY_YR",
    "SAND_0_100_PCT",
    "SILT_0_100_PCT",
    "CLAY_0_100_PCT",
    "CHIRPS_CELL_ID",
    "ERA5L_CELL_ID",
    "CLIMATE_PAIR_ID",
    "PALMSIM_STATIC_CORE_READY",
]

missing = [c for c in required_pal if c not in pal.columns]
if missing:
    raise ValueError(f"Missing PALMSIM manifest columns: {missing}")

# Robust bool normalization
pal["PALMSIM_STATIC_CORE_READY"] = (
    pal["PALMSIM_STATIC_CORE_READY"]
    .astype(str)
    .str.strip()
    .str.lower()
    .isin(["true", "1", "yes"])
)

eligible = pal[pal["PALMSIM_STATIC_CORE_READY"]].copy()
eligible = eligible.sort_values("UNIT_ID").reset_index(drop=True)

print("\nFrozen input:")
print("  ASUs total          :", len(pal))
print("  PALMSIM eligible    :", len(eligible))
print("  Held due core input :", len(pal) - len(eligible))

# Never silently fill age.
if eligible["AGE_PROXY_YR"].isna().any():
    raise ValueError("Eligible manifest contains missing AGE_PROXY_YR.")

# Soil texture closure.
eligible["SOIL_SUM_PCT"] = (
    pd.to_numeric(eligible["SAND_0_100_PCT"], errors="coerce")
    + pd.to_numeric(eligible["SILT_0_100_PCT"], errors="coerce")
    + pd.to_numeric(eligible["CLAY_0_100_PCT"], errors="coerce")
)

soil_closure_ok = bool(
    eligible["SOIL_SUM_PCT"].between(99.5, 100.5).all()
)

# ------------------------------------------------------------
# 2. CLIMATE PREFLIGHT — NATIVE CELL TABLES ONLY
# ------------------------------------------------------------

chirps = pd.read_csv(
    CHIRPS_DAILY,
    usecols=["DATE", "CHIRPS_CELL_ID", "RAIN_MM_DAY"]
)
era = pd.read_csv(
    ERA5_DAILY,
    usecols=[
        "DATE",
        "ERA5L_CELL_ID",
        "TMEAN_C",
        "RH_MEAN_PCT",
        "WIND_MEAN_MS",
        "RAD_MJ_M2_DAY",
    ]
)

chirps["DATE"] = pd.to_datetime(chirps["DATE"]).dt.normalize()
era["DATE"] = pd.to_datetime(era["DATE"]).dt.normalize()

chirps = chirps[chirps["DATE"].between(START, END)].copy()
era = era[era["DATE"].between(START, END)].copy()

chirps["CHIRPS_CELL_ID"] = chirps["CHIRPS_CELL_ID"].astype(str)
era["ERA5L_CELL_ID"] = era["ERA5L_CELL_ID"].astype(str)
eligible["CHIRPS_CELL_ID"] = eligible["CHIRPS_CELL_ID"].astype(str)
eligible["ERA5L_CELL_ID"] = eligible["ERA5L_CELL_ID"].astype(str)

needed_chirps = sorted(eligible["CHIRPS_CELL_ID"].unique())
needed_era = sorted(eligible["ERA5L_CELL_ID"].unique())

climate_rows = []

for cid in needed_chirps:
    s = chirps[chirps["CHIRPS_CELL_ID"] == cid]
    climate_rows.append({
        "SOURCE": "CHIRPS",
        "CELL_ID": cid,
        "EXPECTED_DAYS": EXPECTED_DAYS,
        "ROWS": int(len(s)),
        "VALID_DAYS": int(s["RAIN_MM_DAY"].notna().sum()),
        "COMPLETE": bool(
            len(s) == EXPECTED_DAYS
            and s["RAIN_MM_DAY"].notna().all()
            and (s["RAIN_MM_DAY"] >= 0).all()
        ),
    })

for cid in needed_era:
    s = era[era["ERA5L_CELL_ID"] == cid]
    vars_ = ["TMEAN_C", "RH_MEAN_PCT", "WIND_MEAN_MS", "RAD_MJ_M2_DAY"]
    climate_rows.append({
        "SOURCE": "ERA5L",
        "CELL_ID": cid,
        "EXPECTED_DAYS": EXPECTED_DAYS,
        "ROWS": int(len(s)),
        "VALID_DAYS": int(s[vars_].notna().all(axis=1).sum()),
        "COMPLETE": bool(
            len(s) == EXPECTED_DAYS
            and s[vars_].notna().all().all()
        ),
    })

climate_qc = pd.DataFrame(climate_rows)
climate_complete = bool(climate_qc["COMPLETE"].all())

print("\nClimate preflight:")
print("  Required CHIRPS cells:", len(needed_chirps))
print("  Required ERA5L cells :", len(needed_era))
print("  Climate complete     :", climate_complete)

# Free source tables early.
del chirps, era

# ------------------------------------------------------------
# 3. PALMSIM SOURCE / PACKAGE DISCOVERY
# ------------------------------------------------------------

discovery = {
    "importable": False,
    "module_origin": None,
    "reported_version": None,
    "candidate_paths": [],
    "import_error": None,
}

spec = importlib.util.find_spec("palmsim")

if spec is not None:
    discovery["importable"] = True
    discovery["module_origin"] = str(spec.origin)

    try:
        import palmsim
        for attr in ["__version__", "VERSION", "version"]:
            if hasattr(palmsim, attr):
                discovery["reported_version"] = str(getattr(palmsim, attr))
                break
    except Exception as e:
        discovery["import_error"] = repr(e)

# Search only a small number of likely locations. No huge recursive scan.
candidate_roots = [
    WORKDIR,
    WORKDIR.parent,
    Path.home() / "Documents",
    Path.home() / "Downloads",
]

candidate_names = [
    "palmsim",
    "PALMSIM",
    "palmsim_master",
    "palmsim_master_0",
    "PalmSim",
]

seen = set()

for root in candidate_roots:
    if not root.exists():
        continue

    for name in candidate_names:
        p = root / name
        if p.exists():
            rp = str(p.resolve())
            if rp not in seen:
                discovery["candidate_paths"].append(rp)
                seen.add(rp)

    # Shallow one-level directory name search only.
    try:
        for child in root.iterdir():
            if child.is_dir() and "palmsim" in child.name.lower():
                rp = str(child.resolve())
                if rp not in seen:
                    discovery["candidate_paths"].append(rp)
                    seen.add(rp)
    except Exception:
        pass

source_discovered = bool(
    discovery["importable"] or discovery["candidate_paths"]
)

print("\nPALMSIM source discovery:")
print("  Importable       :", discovery["importable"])
print("  Module origin    :", discovery["module_origin"])
print("  Reported version :", discovery["reported_version"])
print("  Candidate paths  :", len(discovery["candidate_paths"]))

for p in discovery["candidate_paths"][:10]:
    print("   -", p)

# ------------------------------------------------------------
# 4. FREEZE EXPERIMENTAL SENSITIVITY DESIGN
# ------------------------------------------------------------
#
# Plant density:
#   baseline = 143 palms/ha
#   low/high = 130 and 150 palms/ha
# These are scenario values, not measured estate density.
#
# Soil depth:
#   baseline = 1.0 m
#   shallow/deep = 0.5 and 1.5 m
# These are exploratory sensitivity brackets ONLY.
# They are not claimed as observed Siak soil depth.
#
# One-at-a-time design is intentionally used before any factorial expansion.
# ------------------------------------------------------------

scenarios = pd.DataFrame([
    {
        "SCENARIO_ID": "P00_BASE",
        "SCENARIO_ROLE": "BASELINE",
        "PALM_DENSITY_PALMS_HA": 143.0,
        "SOIL_DEPTH_M": 1.0,
        "DENSITY_STATUS": "SCENARIO_NOT_OBSERVED",
        "SOIL_DEPTH_STATUS": "SCENARIO_NOT_OBSERVED",
    },
    {
        "SCENARIO_ID": "P01_DENS_LOW",
        "SCENARIO_ROLE": "DENSITY_SENSITIVITY",
        "PALM_DENSITY_PALMS_HA": 130.0,
        "SOIL_DEPTH_M": 1.0,
        "DENSITY_STATUS": "SCENARIO_NOT_OBSERVED",
        "SOIL_DEPTH_STATUS": "SCENARIO_NOT_OBSERVED",
    },
    {
        "SCENARIO_ID": "P02_DENS_HIGH",
        "SCENARIO_ROLE": "DENSITY_SENSITIVITY",
        "PALM_DENSITY_PALMS_HA": 150.0,
        "SOIL_DEPTH_M": 1.0,
        "DENSITY_STATUS": "SCENARIO_NOT_OBSERVED",
        "SOIL_DEPTH_STATUS": "SCENARIO_NOT_OBSERVED",
    },
    {
        "SCENARIO_ID": "P03_DEPTH_SHALLOW",
        "SCENARIO_ROLE": "SOIL_DEPTH_SENSITIVITY",
        "PALM_DENSITY_PALMS_HA": 143.0,
        "SOIL_DEPTH_M": 0.5,
        "DENSITY_STATUS": "SCENARIO_NOT_OBSERVED",
        "SOIL_DEPTH_STATUS": "SCENARIO_NOT_OBSERVED",
    },
    {
        "SCENARIO_ID": "P04_DEPTH_DEEP",
        "SCENARIO_ROLE": "SOIL_DEPTH_SENSITIVITY",
        "PALM_DENSITY_PALMS_HA": 143.0,
        "SOIL_DEPTH_M": 1.5,
        "DENSITY_STATUS": "SCENARIO_NOT_OBSERVED",
        "SOIL_DEPTH_STATUS": "SCENARIO_NOT_OBSERVED",
    },
])

print("\nScenario design:")
print("  Scenarios:", len(scenarios))
print("  Design   : one-at-a-time baseline sensitivity")

# ------------------------------------------------------------
# 5. BUILD ELIGIBLE ASU MANIFEST
# ------------------------------------------------------------

keep_cols = [
    "UNIT_ID",
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

keep_cols = [c for c in keep_cols if c in eligible.columns]
eligible_out = eligible[keep_cols].copy()

# Pair × scenario run manifest, no daily climate duplication.
eligible_out["_KEY"] = 1
scenarios["_KEY"] = 1

run_manifest = eligible_out.merge(
    scenarios,
    on="_KEY",
    how="inner"
).drop(columns="_KEY")

eligible_out = eligible_out.drop(columns="_KEY")
scenarios = scenarios.drop(columns="_KEY")

run_manifest["RUN_ID"] = (
    run_manifest["UNIT_ID"].astype(str)
    + "__"
    + run_manifest["SCENARIO_ID"].astype(str)
)

run_manifest["WEATHER_JOIN_POLICY"] = "JOIN_NATIVE_CELLS_ON_DEMAND"
run_manifest["RAIN_SOURCE"] = "CHIRPS_V2_FINAL"
run_manifest["ATMOSPHERIC_SOURCE"] = "ERA5_LAND"
run_manifest["PRODUCT_CLAIM"] = "PRODUCTIVITY_POTENTIAL_NOT_ACTUAL_YIELD"

planned_runs = len(run_manifest)

print("\nPlanned PALMSIM experiment:")
print("  Eligible ASUs :", len(eligible_out))
print("  Scenarios     :", len(scenarios))
print("  Planned runs  :", planned_runs)

# ------------------------------------------------------------
# 6. FINAL PREFLIGHT GATE
# ------------------------------------------------------------

input_gate = bool(
    len(pal) == 820
    and len(eligible_out) == 654
    and soil_closure_ok
    and climate_complete
)

if input_gate and source_discovered:
    status = "PASS"
    next_action = (
        "40C02 PALMSIM adapter smoke test on 1 ASU x baseline scenario, "
        "then deterministic repeat test before batch runs."
    )
elif input_gate and not source_discovered:
    status = "PASS_INPUTS_CHECK_MODEL_SOURCE"
    next_action = (
        "Locate/register the already-audited PALMSIM 2.5.2 working source, "
        "then run 40C02 smoke test. Do not change frozen data inputs."
    )
else:
    status = "CHECK"
    next_action = "Resolve failed preflight input/QC items before PALMSIM execution."

qc = {
    "gate": "40C01",
    "status": status,
    "product_mode": "Productivity Potential",
    "actual_ffb_labels_available": False,

    "input": {
        "asu_total": int(len(pal)),
        "palmsim_eligible_asus": int(len(eligible_out)),
        "held_asus": int(len(pal) - len(eligible_out)),
        "soil_texture_closure_pass": soil_closure_ok,
    },

    "climate": {
        "period": [
            START.strftime("%Y-%m-%d"),
            END.strftime("%Y-%m-%d"),
        ],
        "expected_days": int(EXPECTED_DAYS),
        "required_chirps_cells": int(len(needed_chirps)),
        "required_era5land_cells": int(len(needed_era)),
        "complete": climate_complete,
        "rain_primary": "CHIRPS v2 Final",
        "era5land_role": (
            "temperature/RH/wind/radiation core; rainfall diagnostic only"
        ),
    },

    "palmsim_source_discovery": discovery,

    "scenario_design": {
        "type": "one_at_a_time",
        "scenario_count": int(len(scenarios)),
        "baseline_density_palms_ha": 143.0,
        "density_sensitivity_palms_ha": [130.0, 150.0],
        "baseline_soil_depth_m": 1.0,
        "soil_depth_sensitivity_m": [0.5, 1.5],
        "important_note": (
            "Density and soil depth values are experimental assumptions, "
            "not observed estate measurements. Confirm PALMSIM parameter "
            "contract/units in 40C02 before executing runs."
        ),
    },

    "planned_runs": int(planned_runs),

    "scientific_guardrails": [
        "No age imputation.",
        "No actual-yield accuracy claim.",
        "PALMSIM result interpreted as modelled productivity potential.",
        "Peat/mineral applicability remains an explicit uncertainty.",
        "Weather stays at native climate-cell support; no fake 500 m weather resolution.",
        "Scenario density/soil-depth values must remain labelled as assumptions.",
    ],

    "next_action": next_action,
}

# ------------------------------------------------------------
# 7. EXPORT
# ------------------------------------------------------------

scenarios.to_csv(OUT_SCENARIOS, index=False, encoding="utf-8-sig")
eligible_out.to_csv(OUT_ELIGIBLE, index=False, encoding="utf-8-sig")
run_manifest.to_csv(OUT_RUN_MANIFEST, index=False, encoding="utf-8-sig")
climate_qc.to_csv(OUT_CLIMATE_QC, index=False, encoding="utf-8-sig")
OUT_QC.write_text(json.dumps(qc, indent=2), encoding="utf-8")

print("\n====================================================")
print("40C01 FINISHED")
print("====================================================")
print("Status:", status)
print("Eligible ASUs:", len(eligible_out), "/ 820")
print("Climate complete:", climate_complete)
print("PALMSIM source discovered:", source_discovered)
print("Scenarios:", len(scenarios))
print("Planned runs:", planned_runs)
print("Scenario matrix:", OUT_SCENARIOS)
print("Eligible ASUs:", OUT_ELIGIBLE)
print("Run manifest:", OUT_RUN_MANIFEST)
print("Climate QC:", OUT_CLIMATE_QC)
print("QC JSON:", OUT_QC)
print("Next:", next_action)
print("====================================================")
