# ============================================================
# OUTPUT 4 / 40C04A DIRECT-JUPYTER
# PALMSIM P00 BASELINE — SERIAL, CHECKPOINTED, LIVE ETA
# SIAK_AOI01
#
# RUN THIS FILE DIRECTLY INSIDE THE JUPYTER KERNEL:
#     exec(open(r"...\40C04A_DIRECT_JUPYTER_P00_BASELINE_SIAK_AOI01_V1.py",
#               encoding="utf-8").read())
#
# PURPOSE
# - Run P00_BASE for all climate-compatible PALMSIM ASUs.
# - No subprocess / no multiprocessing.
# - Autosave every 5 completed ASUs.
# - Resume automatically from checkpoint.
# - Show live progress, average time/run, and ETA.
#
# SCIENTIFIC GUARDRAILS
# - Output = modelled productivity potential, NOT actual yield.
# - Age-derived planting year remains a proxy.
# - No missing-weather fallback.
# - CHIRPS v2 Final = rainfall.
# - ERA5-Land = radiation.
# - SoilGrids sand/silt/clay are NOT injected into PALMSIM.
# ============================================================

from pathlib import Path
import os
import sys
import json
import time
import traceback
import warnings
import gc

import numpy as np
import pandas as pd

WORKDIR = Path(
    r"C:\Users\user\Documents\KERJA\SPATIAL DATA ANALYST INTERN\04_YIELD"
)
os.chdir(WORKDIR)

REG = WORKDIR / "40C01B_PALMSIM_SOURCE_REGISTRATION_SIAK_AOI01_V1.json"
ELIGIBLE_FILE = WORKDIR / "40C01_PALMSIM_ELIGIBLE_ASU_MANIFEST_SIAK_AOI01_V1.csv"
CHIRPS_FILE = WORKDIR / "40B04B1_CHIRPS_V2_DAILY_NATIVE_CELLS_2001_2025_SIAK_AOI01_V1.csv"
ERA5_FILE = WORKDIR / "40B04B2_ERA5LAND_DAILY_NATIVE_CELLS_2001_2025_SIAK_AOI01_V4.csv"

CHECKPOINT = WORKDIR / "40C04A_DIRECT_P00_BASELINE_CHECKPOINT_SIAK_AOI01_V1.csv"
OUT_RESULTS = WORKDIR / "40C04A_DIRECT_P00_BASELINE_RESULTS_SIAK_AOI01_V1.csv"
OUT_EXCLUSIONS = WORKDIR / "40C04A_DIRECT_P00_BASELINE_EXCLUSIONS_SIAK_AOI01_V1.csv"
OUT_FAILURES = WORKDIR / "40C04A_DIRECT_P00_BASELINE_FAILURES_SIAK_AOI01_V1.csv"
OUT_QC = WORKDIR / "40C04A_DIRECT_P00_BASELINE_QC_SIAK_AOI01_V1.json"

REFERENCE_YEAR = 2025
CLIMATE_START = pd.Timestamp("2001-01-01")
CLIMATE_END = pd.Timestamp("2025-12-31")

BASE_DENSITY = 143.0
BASE_SOIL_DEPTH = 1.0
SAVE_EVERY = 5

warnings.filterwarnings(
    "ignore",
    message=r".*errors='ignore' is deprecated.*",
    category=FutureWarning
)

print("====================================================")
print("40C04A DIRECT-JUPYTER — PALMSIM P00 BASELINE")
print("====================================================")
print("Python :", sys.executable)
print("Workdir:", WORKDIR)

for p in [REG, ELIGIBLE_FILE, CHIRPS_FILE, ERA5_FILE]:
    if not p.exists():
        raise FileNotFoundError(f"Missing required input: {p}")

# ------------------------------------------------------------
# 1. LOAD PALMSIM
# ------------------------------------------------------------

registration = json.loads(REG.read_text(encoding="utf-8"))
working_root = Path(registration["working_root"])

roots = list(working_root.rglob("palmsim-master"))
if not roots:
    raise FileNotFoundError("Could not locate palmsim-master.")

palmsim_master = roots[0]

for pth in [str(palmsim_master / "PalmSim"), str(palmsim_master)]:
    if pth not in sys.path:
        sys.path.insert(0, pth)

from palmsim import PalmField

print("PALMSIM import: PASS")

# ------------------------------------------------------------
# 2. ASU AUDIT
# ------------------------------------------------------------

asu = pd.read_csv(ELIGIBLE_FILE)

required = [
    "UNIT_ID", "AGE_PROXY_YR", "ASU_LATITUDE",
    "CHIRPS_CELL_ID", "ERA5L_CELL_ID"
]
missing = [c for c in required if c not in asu.columns]
if missing:
    raise ValueError(f"Missing ASU columns: {missing}")

asu["AGE_PROXY_YR"] = pd.to_numeric(asu["AGE_PROXY_YR"], errors="coerce")
asu["ASU_LATITUDE"] = pd.to_numeric(asu["ASU_LATITUDE"], errors="coerce")
asu["CHIRPS_CELL_ID"] = asu["CHIRPS_CELL_ID"].astype(str)
asu["ERA5L_CELL_ID"] = asu["ERA5L_CELL_ID"].astype(str)

audit_rows = []

for _, r in asu.iterrows():
    age = r["AGE_PROXY_YR"]
    reason = None

    if pd.isna(age):
        reason = "MISSING_AGE_PROXY"
        model_age = yop = start = end = None
    else:
        model_age = int(round(float(age)))

        if model_age < 1:
            reason = "AGE_PROXY_LT_1_YEAR"

        yop = REFERENCE_YEAR - model_age
        start = pd.Timestamp(year=yop, month=1, day=1)
        duration = model_age * 365
        end = start + pd.Timedelta(days=duration - 1)

        if reason is None and start < CLIMATE_START:
            reason = "CLIMATE_WINDOW_START_BEFORE_2001"

        if reason is None and end > CLIMATE_END:
            reason = "CLIMATE_WINDOW_END_AFTER_2025"

    audit_rows.append({
        "UNIT_ID": str(r["UNIT_ID"]),
        "MODEL_AGE_YR_ROUNDED": model_age,
        "YEAR_OF_PLANTING_PROXY": yop,
        "SIMULATION_START": None if start is None else start.strftime("%Y-%m-%d"),
        "SIMULATION_END": None if end is None else end.strftime("%Y-%m-%d"),
        "EXCLUSION_REASON": reason,
    })

audit = pd.DataFrame(audit_rows)

asu = asu.merge(audit, on="UNIT_ID", how="left", validate="one_to_one")
batch_asu = asu[asu["EXCLUSION_REASON"].isna()].copy()
exclusions = asu[asu["EXCLUSION_REASON"].notna()].copy()

exclusions.to_csv(OUT_EXCLUSIONS, index=False, encoding="utf-8-sig")

print("\nInput PALMSIM ASUs :", len(asu))
print("Climate-compatible:", len(batch_asu))
print("Excluded          :", len(exclusions))

if len(exclusions):
    print(exclusions["EXCLUSION_REASON"].value_counts().to_string())

# ------------------------------------------------------------
# 3. LOAD CLIMATE ONCE
# ------------------------------------------------------------

chirps = pd.read_csv(
    CHIRPS_FILE,
    usecols=["DATE", "CHIRPS_CELL_ID", "RAIN_MM_DAY"]
)
era = pd.read_csv(
    ERA5_FILE,
    usecols=["DATE", "ERA5L_CELL_ID", "RAD_MJ_M2_DAY"]
)

chirps["DATE"] = pd.to_datetime(chirps["DATE"]).dt.normalize()
era["DATE"] = pd.to_datetime(era["DATE"]).dt.normalize()

chirps["CHIRPS_CELL_ID"] = chirps["CHIRPS_CELL_ID"].astype(str)
era["ERA5L_CELL_ID"] = era["ERA5L_CELL_ID"].astype(str)

chirps_by_cell = {
    cid: g[["DATE", "RAIN_MM_DAY"]].sort_values("DATE").set_index("DATE")
    for cid, g in chirps.groupby("CHIRPS_CELL_ID", sort=False)
}
era_by_cell = {
    cid: g[["DATE", "RAD_MJ_M2_DAY"]].sort_values("DATE").set_index("DATE")
    for cid, g in era.groupby("ERA5L_CELL_ID", sort=False)
}

pair_cache = {}
for _, rr in batch_asu[["CHIRPS_CELL_ID", "ERA5L_CELL_ID"]].drop_duplicates().iterrows():
    c_id = str(rr["CHIRPS_CELL_ID"])
    e_id = str(rr["ERA5L_CELL_ID"])
    pair_cache[(c_id, e_id)] = chirps_by_cell[c_id].join(
        era_by_cell[e_id],
        how="inner"
    )

print("Climate pairs cached:", len(pair_cache))

del chirps, era
gc.collect()

# ------------------------------------------------------------
# 4. RESUME
# ------------------------------------------------------------

records = []
completed = set()

if CHECKPOINT.exists():
    old = pd.read_csv(CHECKPOINT)
    if len(old) and "UNIT_ID" in old.columns:
        records = old.to_dict("records")
        completed = set(old["UNIT_ID"].astype(str))

print("Recovered checkpoint:", len(completed))

failures = []

def save_checkpoint():
    if not records:
        return
    tmp = CHECKPOINT.with_suffix(".tmp.csv")
    pd.DataFrame(records).to_csv(tmp, index=False, encoding="utf-8-sig")
    os.replace(tmp, CHECKPOINT)

def get_ffb_col(df):
    preferred = "generative_FFB_production (t/ha/yr)"
    if preferred in df.columns:
        return preferred
    cands = [
        c for c in df.columns
        if "ffb" in str(c).lower() and "production" in str(c).lower()
    ]
    if not cands:
        cands = [c for c in df.columns if "ffb" in str(c).lower()]
    return cands[0] if cands else None

todo = batch_asu[
    ~batch_asu["UNIT_ID"].astype(str).isin(completed)
].copy()

print("Remaining to run    :", len(todo))
print("\nStarting baseline loop...\n")

# ------------------------------------------------------------
# 5. SERIAL DIRECT-KERNEL LOOP
# ------------------------------------------------------------

t0 = time.perf_counter()
session_times = []

for session_i, (_, r) in enumerate(todo.iterrows(), start=1):

    unit_id = str(r["UNIT_ID"])
    run_t0 = time.perf_counter()

    try:
        model_age = int(r["MODEL_AGE_YR_ROUNDED"])
        yop = int(r["YEAR_OF_PLANTING_PROXY"])
        duration = model_age * 365

        start = pd.Timestamp(r["SIMULATION_START"])
        end = pd.Timestamp(r["SIMULATION_END"])

        c_id = str(r["CHIRPS_CELL_ID"])
        e_id = str(r["ERA5L_CELL_ID"])

        weather = pair_cache[(c_id, e_id)].loc[start:end]

        if len(weather) != duration:
            raise RuntimeError(
                f"weather rows {len(weather)} != duration {duration}"
            )

        if weather[["RAIN_MM_DAY", "RAD_MJ_M2_DAY"]].isna().any().any():
            raise RuntimeError("missing climate forcing")

        if not weather.index.equals(pd.date_range(start, end, freq="D")):
            raise RuntimeError("non-contiguous daily forcing calendar")

        p = PalmField(year_of_planting=yop)
        p.latitude = float(r["ASU_LATITUDE"])

        p.weather.rainfall_series = weather["RAIN_MM_DAY"].copy()
        p.weather.radiation_series = weather["RAD_MJ_M2_DAY"].copy()

        p.planting_density = BASE_DENSITY
        p.soil.soil_depth = BASE_SOIL_DEPTH

        df = p.run(duration=duration)

        if not isinstance(df, pd.DataFrame) or len(df) == 0:
            raise RuntimeError("PALMSIM returned empty output")

        ffb_col = get_ffb_col(df)
        if ffb_col is None:
            raise RuntimeError("FFB output column not found")

        raw = pd.to_numeric(df[ffb_col], errors="coerce").dropna()
        if len(raw) == 0:
            raise RuntimeError("FFB output contains no numeric values")

        # Audited PALMSIM source:
        # raw = kg fresh FFB/ha/yr, canonical Output-4 unit = /1000.
        ffb = raw / 1000.0

        n1 = min(36, len(ffb))
        n3 = min(109, len(ffb))

        records.append({
            "UNIT_ID": unit_id,
            "SCENARIO_ID": "P00_BASE",
            "AGE_PROXY_YR": float(r["AGE_PROXY_YR"]),
            "MODEL_AGE_YR_ROUNDED": model_age,
            "YEAR_OF_PLANTING_PROXY": yop,
            "ASU_LATITUDE": float(r["ASU_LATITUDE"]),
            "CHIRPS_CELL_ID": c_id,
            "ERA5L_CELL_ID": e_id,
            "PALM_DENSITY_PALMS_HA": BASE_DENSITY,
            "SOIL_DEPTH_M": BASE_SOIL_DEPTH,
            "SIMULATION_START": start.strftime("%Y-%m-%d"),
            "SIMULATION_END": end.strftime("%Y-%m-%d"),
            "DURATION_DAYS": duration,
            "MODEL_OUTPUT_ROWS": int(len(df)),
            "FFB_SOURCE_COLUMN": ffb_col,
            "FINAL_FFB_POTENTIAL_T_HA_YR": float(ffb.iloc[-1]),
            "TRAILING_1Y_MEAN_T_HA_YR": float(ffb.tail(n1).mean()),
            "TRAILING_1Y_MEDIAN_T_HA_YR": float(ffb.tail(n1).median()),
            "TRAILING_3Y_MEAN_T_HA_YR": float(ffb.tail(n3).mean()),
            "RUN_STATUS": "PASS",
        })

        completed.add(unit_id)

    except Exception as e:
        failures.append({
            "UNIT_ID": unit_id,
            "ERROR": repr(e),
            "TRACEBACK": traceback.format_exc()[-4000:],
        })

    run_sec = time.perf_counter() - run_t0
    session_times.append(run_sec)

    if session_i % SAVE_EVERY == 0 or session_i == len(todo):
        save_checkpoint()

        done_total = len(completed)
        remaining = len(batch_asu) - done_total

        avg_sec = float(np.mean(session_times[-20:]))
        eta_min = remaining * avg_sec / 60.0

        elapsed_min = (time.perf_counter() - t0) / 60.0

        print(
            f"Progress: {done_total}/{len(batch_asu)} "
            f"({100*done_total/len(batch_asu):.1f}%) | "
            f"last={run_sec:.1f}s | "
            f"avg20={avg_sec:.1f}s/run | "
            f"ETA≈{eta_min:.1f} min | "
            f"fail={len(failures)} | "
            f"elapsed={elapsed_min:.1f} min"
        )

    del p, df
    gc.collect()

# ------------------------------------------------------------
# 6. FINALIZE
# ------------------------------------------------------------

results = pd.DataFrame(records)

if len(results):
    results = (
        results
        .drop_duplicates(subset=["UNIT_ID"], keep="last")
        .sort_values("UNIT_ID")
        .reset_index(drop=True)
    )

results.to_csv(OUT_RESULTS, index=False, encoding="utf-8-sig")

pd.DataFrame(
    failures,
    columns=["UNIT_ID", "ERROR", "TRACEBACK"]
).to_csv(
    OUT_FAILURES,
    index=False,
    encoding="utf-8-sig"
)

expected_ids = set(batch_asu["UNIT_ID"].astype(str))
actual_ids = set(results["UNIT_ID"].astype(str))
missing_ids = expected_ids - actual_ids

metric = pd.to_numeric(
    results["TRAILING_1Y_MEAN_T_HA_YR"],
    errors="coerce"
) if len(results) else pd.Series(dtype=float)

finite_nonnegative = bool(
    len(metric)
    and np.isfinite(metric).all()
    and (metric >= 0).all()
)

if not missing_ids and not failures and finite_nonnegative:
    status = (
        "PASS"
        if len(exclusions) == 0
        else "PASS_WITH_CLIMATE_WINDOW_EXCLUSIONS"
    )
    next_gate = (
        "40C04B representative P01-P04 sensitivity batch, "
        "then 40C05 PALMSIM synthesis/QC."
    )
else:
    status = "CHECK_PARTIAL_BASELINE"
    next_gate = (
        "Rerun this same Direct-Jupyter script; "
        "checkpoint will resume completed ASUs."
    )

qc = {
    "gate": "40C04A_DIRECT_JUPYTER",
    "status": status,
    "input_palmsim_asus": int(len(asu)),
    "climate_compatible_asus": int(len(batch_asu)),
    "pre_run_exclusions": int(len(exclusions)),
    "completed_baseline_asus": int(len(actual_ids)),
    "missing_baseline_asus": int(len(missing_ids)),
    "failure_rows": int(len(failures)),
    "median_trailing_1y_t_fresh_ffb_ha_yr":
        None if len(metric) == 0 else float(metric.median()),
    "min_trailing_1y_t_fresh_ffb_ha_yr":
        None if len(metric) == 0 else float(metric.min()),
    "max_trailing_1y_t_fresh_ffb_ha_yr":
        None if len(metric) == 0 else float(metric.max()),
    "scientific_guardrails": [
        "Productivity potential only; not actual FFB yield.",
        "Age-derived planting year is a proxy.",
        "No climate forcing before 2001 is fabricated.",
        "CHIRPS v2 Final rainfall + ERA5-Land radiation.",
        "SoilGrids sand/silt/clay not injected into PALMSIM.",
        "Baseline density=143 palms/ha and soil depth=1.0 m are scenario assumptions.",
    ],
    "next_gate": next_gate,
}

OUT_QC.write_text(json.dumps(qc, indent=2), encoding="utf-8")

print("\n====================================================")
print("40C04A DIRECT-JUPYTER FINISHED")
print("====================================================")
print("Status            :", status)
print("Completed baseline:", len(actual_ids), "/", len(batch_asu))
print("Missing baseline  :", len(missing_ids))
print("Failures          :", len(failures))

if len(metric):
    print("Potential min     :", float(metric.min()))
    print("Potential median  :", float(metric.median()))
    print("Potential max     :", float(metric.max()))
    print("Unit              : t fresh FFB/ha/yr")

print("Results           :", OUT_RESULTS)
print("Checkpoint        :", CHECKPOINT)
print("QC                :", OUT_QC)
print("Next              :", next_gate)
print("====================================================")
