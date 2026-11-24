# ============================================================
# OUTPUT 4 / 40B04C-LITE
# FINAL CLIMATE HARMONIZATION — LOW-MEMORY / NO DAILY DUPLICATION
# SIAK_AOI01
#
# WHY LITE?
# - CHIRPS B1 is already PASS.
# - ERA5-Land B2 V4 is already PASS.
# - Building a combined 25-year daily table for every unique
#   CHIRPS×ERA5 climate pair is NOT required now and can waste RAM.
#
# FINAL STORAGE POLICY
# - Keep CHIRPS daily forcing ONCE at 12 native cells.
# - Keep ERA5-Land daily forcing ONCE at 6 native cells.
# - Keep only the ASU -> CHIRPS_CELL_ID + ERA5L_CELL_ID mapping.
# - During PALMSIM/APSIM execution, join one climate pair on demand.
#
# This is the preferred architecture for low RAM + low storage.
# ============================================================

from pathlib import Path
import os
import json
import gc
import numpy as np
import pandas as pd

WORKDIR = Path(
    r"C:\Users\user\Documents\KERJA\SPATIAL DATA ANALYST INTERN\04_YIELD"
)
os.chdir(WORKDIR)

ASU_MAP = WORKDIR / "40B04A_ASU_CLIMATE_CELL_MAPPING_SIAK_AOI01_V1.csv"
CHIRPS_DAILY = WORKDIR / "40B04B1_CHIRPS_V2_DAILY_NATIVE_CELLS_2001_2025_SIAK_AOI01_V1.csv"
ERA5_DAILY = WORKDIR / "40B04B2_ERA5LAND_DAILY_NATIVE_CELLS_2001_2025_SIAK_AOI01_V4.csv"

OUT_ASU_PAIR_MAP = WORKDIR / "40B04C_LITE_ASU_CLIMATE_PAIR_MAPPING_SIAK_AOI01_V1.csv"
OUT_PAIR_SUMMARY = WORKDIR / "40B04C_LITE_CLIMATE_PAIR_SUMMARY_SIAK_AOI01_V1.csv"
OUT_QC = WORKDIR / "40B04C_LITE_FINAL_CLIMATE_QC_SIAK_AOI01_V1.json"

START = pd.Timestamp("2001-01-01")
END = pd.Timestamp("2025-12-31")
EXPECTED_DAYS = len(pd.date_range(START, END, freq="D"))

print("====================================================")
print("40B04C-LITE — FINAL CLIMATE HARMONIZATION")
print("LOW-MEMORY / JOIN-ON-DEMAND ARCHITECTURE")
print("====================================================")

for p in [ASU_MAP, CHIRPS_DAILY, ERA5_DAILY]:
    if not p.exists():
        raise FileNotFoundError(f"Missing required input: {p}")

# ------------------------------------------------------------
# 1. ASU MAPPING
# ------------------------------------------------------------

asu_header = pd.read_csv(ASU_MAP, nrows=0).columns.tolist()

asu_cols = [
    "UNIT_ID",
    "CHIRPS_CELL_ID",
    "ERA5L_CELL_ID",
]
for c in ["ASU_AREA_HA_EXACT", "PLANTATION_FRACTION_EXACT"]:
    if c in asu_header:
        asu_cols.append(c)

asu = pd.read_csv(ASU_MAP, usecols=asu_cols)

if len(asu) != 820:
    raise ValueError(f"Expected 820 ASUs, found {len(asu)}")

if asu[["UNIT_ID","CHIRPS_CELL_ID","ERA5L_CELL_ID"]].isna().any().any():
    raise ValueError("Missing ASU climate-cell mapping.")

asu["CLIMATE_PAIR_ID"] = (
    asu["CHIRPS_CELL_ID"].astype(str)
    + "__"
    + asu["ERA5L_CELL_ID"].astype(str)
)

agg = {"ASU_COUNT": ("UNIT_ID", "count")}
if "ASU_AREA_HA_EXACT" in asu.columns:
    agg["PLANTATION_AREA_HA"] = ("ASU_AREA_HA_EXACT", "sum")

pairs = (
    asu.groupby(
        ["CLIMATE_PAIR_ID","CHIRPS_CELL_ID","ERA5L_CELL_ID"],
        as_index=False
    )
    .agg(**agg)
)

print("ASU count:", len(asu))
print("Unique CHIRPS cells:", asu["CHIRPS_CELL_ID"].nunique())
print("Unique ERA5-Land cells:", asu["ERA5L_CELL_ID"].nunique())
print("Unique climate pairs:", len(pairs))

# ------------------------------------------------------------
# 2. CHIRPS SOURCE QC — ONLY NECESSARY COLUMNS
# ------------------------------------------------------------

chirps = pd.read_csv(
    CHIRPS_DAILY,
    usecols=["DATE","CHIRPS_CELL_ID","RAIN_MM_DAY"]
)

chirps["DATE"] = pd.to_datetime(chirps["DATE"]).dt.normalize()
chirps = chirps[chirps["DATE"].between(START, END)].copy()

chirps["RAIN_MM_DAY"] = pd.to_numeric(
    chirps["RAIN_MM_DAY"], errors="coerce"
)

chirps_dup = int(
    chirps.duplicated(["CHIRPS_CELL_ID","DATE"]).sum()
)

chirps_qc = (
    chirps.groupby("CHIRPS_CELL_ID")
    .agg(
        DAYS=("DATE","nunique"),
        VALID_RAIN_DAYS=("RAIN_MM_DAY","count"),
        START_DATE=("DATE","min"),
        END_DATE=("DATE","max"),
    )
    .reset_index()
)

chirps_complete = bool(
    (len(chirps_qc) == 12)
    and (chirps_qc["DAYS"] == EXPECTED_DAYS).all()
    and (chirps_qc["VALID_RAIN_DAYS"] == EXPECTED_DAYS).all()
    and (chirps_dup == 0)
    and (chirps["RAIN_MM_DAY"] >= 0).all()
)

print("CHIRPS source:", "PASS" if chirps_complete else "CHECK")

# ------------------------------------------------------------
# 3. ERA5-LAND SOURCE QC — ONLY MODEL-RELEVANT COLUMNS
# ------------------------------------------------------------

era_cols = [
    "DATE",
    "ERA5L_CELL_ID",
    "TMEAN_C",
    "TMIN_C",
    "TMAX_C",
    "RH_MEAN_PCT",
    "VPD_MEAN_KPA",
    "WIND_MEAN_MS",
    "RAD_MJ_M2_DAY",
    "PRESSURE_HPA",
    "ERA5L_RAIN_MM_DAY",
]

era = pd.read_csv(
    ERA5_DAILY,
    usecols=era_cols
)

era["DATE"] = pd.to_datetime(era["DATE"]).dt.normalize()
era = era[era["DATE"].between(START, END)].copy()

for c in era_cols[2:]:
    era[c] = pd.to_numeric(era[c], errors="coerce")

era_dup = int(
    era.duplicated(["ERA5L_CELL_ID","DATE"]).sum()
)

era_required = [
    "TMEAN_C",
    "TMIN_C",
    "TMAX_C",
    "RH_MEAN_PCT",
    "VPD_MEAN_KPA",
    "WIND_MEAN_MS",
    "RAD_MJ_M2_DAY",
    "PRESSURE_HPA",
]

era["FORCING_VALID"] = era[era_required].notna().all(axis=1)

era_qc = (
    era.groupby("ERA5L_CELL_ID")
    .agg(
        DAYS=("DATE","nunique"),
        VALID_FORCING_DAYS=("FORCING_VALID","sum"),
        START_DATE=("DATE","min"),
        END_DATE=("DATE","max"),
    )
    .reset_index()
)

era_plausible = bool(
    era["TMEAN_C"].between(-10,45).all()
    and era["TMIN_C"].between(-20,45).all()
    and era["TMAX_C"].between(-5,55).all()
    and era["RH_MEAN_PCT"].between(0,100).all()
    and (era["VPD_MEAN_KPA"] >= 0).all()
    and (era["WIND_MEAN_MS"] >= 0).all()
    and era["RAD_MJ_M2_DAY"].between(0,45).all()
    and era["PRESSURE_HPA"].between(800,1100).all()
)

era_complete = bool(
    (len(era_qc) == 6)
    and (era_qc["DAYS"] == EXPECTED_DAYS).all()
    and (era_qc["VALID_FORCING_DAYS"] == EXPECTED_DAYS).all()
    and (era_dup == 0)
    and era_plausible
)

print("ERA5-Land source:", "PASS" if era_complete else "CHECK")

# ------------------------------------------------------------
# 4. PAIR-LEVEL REFERENCE QC WITHOUT MATERIALIZING DAILY PAIRS
# ------------------------------------------------------------

pair_rows = []

chirps_ids = set(chirps["CHIRPS_CELL_ID"].astype(str))
era_ids = set(era["ERA5L_CELL_ID"].astype(str))

for _, p in pairs.iterrows():

    cid = str(p["CHIRPS_CELL_ID"])
    eid = str(p["ERA5L_CELL_ID"])

    pair_rows.append({
        "CLIMATE_PAIR_ID": p["CLIMATE_PAIR_ID"],
        "CHIRPS_CELL_ID": cid,
        "ERA5L_CELL_ID": eid,
        "ASU_COUNT": int(p["ASU_COUNT"]),
        "PLANTATION_AREA_HA": (
            float(p["PLANTATION_AREA_HA"])
            if "PLANTATION_AREA_HA" in p.index
            else np.nan
        ),
        "CHIRPS_SOURCE_FOUND": cid in chirps_ids,
        "ERA5L_SOURCE_FOUND": eid in era_ids,
        "MODEL_READY": (
            cid in chirps_ids
            and eid in era_ids
            and chirps_complete
            and era_complete
        ),
    })

pair_summary = pd.DataFrame(pair_rows)

all_pairs_ready = bool(pair_summary["MODEL_READY"].all())

status = (
    "PASS"
    if (
        len(asu) == 820
        and asu["CHIRPS_CELL_ID"].nunique() == 12
        and asu["ERA5L_CELL_ID"].nunique() == 6
        and chirps_complete
        and era_complete
        and all_pairs_ready
    )
    else "CHECK"
)

# ------------------------------------------------------------
# 5. FINAL QC
# ------------------------------------------------------------

qc = {
    "gate": "40B04C",
    "version": "LITE_V1_JOIN_ON_DEMAND",
    "status": status,

    "asu_count": int(len(asu)),
    "unique_chirps_cells": int(asu["CHIRPS_CELL_ID"].nunique()),
    "unique_era5land_cells": int(asu["ERA5L_CELL_ID"].nunique()),
    "unique_climate_pairs": int(len(pair_summary)),

    "period": [
        START.strftime("%Y-%m-%d"),
        END.strftime("%Y-%m-%d")
    ],
    "expected_days_per_native_cell": int(EXPECTED_DAYS),

    "chirps": {
        "status": "PASS" if chirps_complete else "CHECK",
        "daily_rows": int(len(chirps)),
        "duplicate_cell_dates": chirps_dup,
        "primary_rainfall": True,
    },

    "era5land": {
        "status": "PASS" if era_complete else "CHECK",
        "daily_rows": int(len(era)),
        "duplicate_cell_dates": era_dup,
        "plausibility_pass": era_plausible,
        "rainfall_role": "diagnostic_only",
    },

    "complete_climate_pairs": int(
        pair_summary["MODEL_READY"].sum()
    ),
    "incomplete_climate_pairs": int(
        (~pair_summary["MODEL_READY"]).sum()
    ),

    "palmsim_climate_ready": bool(
        chirps_complete and era_complete and all_pairs_ready
    ),
    "apsim_weather_ready": bool(
        chirps_complete and era_complete and all_pairs_ready
    ),

    "storage_architecture": (
        "NO combined 25-year daily climate-pair table is materialized. "
        "CHIRPS remains stored once at 12 native cells; ERA5-Land remains "
        "stored once at 6 native cells; 820 ASUs reference both source IDs. "
        "PALMSIM/APSIM runner joins one pair on demand."
    ),

    "next_step": (
        "40B05 / model-input packaging: join climate per ASU or unique "
        "climate pair only during PALMSIM/APSIM execution."
    ),
}

# ------------------------------------------------------------
# 6. EXPORT SMALL OUTPUTS ONLY
# ------------------------------------------------------------

asu.to_csv(
    OUT_ASU_PAIR_MAP,
    index=False,
    encoding="utf-8-sig"
)

pair_summary.to_csv(
    OUT_PAIR_SUMMARY,
    index=False,
    encoding="utf-8-sig"
)

OUT_QC.write_text(
    json.dumps(qc, indent=2),
    encoding="utf-8"
)

print("\n====================================================")
print("40B04C-LITE FINISHED")
print("====================================================")
print("Status:", status)
print("ASUs:", qc["asu_count"])
print("Unique CHIRPS cells:", qc["unique_chirps_cells"])
print("Unique ERA5-Land cells:", qc["unique_era5land_cells"])
print("Unique climate pairs:", qc["unique_climate_pairs"])
print(
    "Complete climate pairs:",
    qc["complete_climate_pairs"],
    "/",
    qc["unique_climate_pairs"]
)
print("PALMSIM climate-ready:", qc["palmsim_climate_ready"])
print("APSIM weather-ready:", qc["apsim_weather_ready"])
print("ASU climate map:", OUT_ASU_PAIR_MAP)
print("Climate pair summary:", OUT_PAIR_SUMMARY)
print("QC JSON:", OUT_QC)
print("====================================================")

# Explicit cleanup; useful when run inside Jupyter.
del chirps, era
gc.collect()
