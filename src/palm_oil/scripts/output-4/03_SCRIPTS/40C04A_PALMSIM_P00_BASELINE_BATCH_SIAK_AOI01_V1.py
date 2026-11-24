# ============================================================
# OUTPUT 4 / 40C04A
# PALMSIM BASELINE BATCH — P00 ONLY
# SIAK_AOI01
#
# RUN FROM JUPYTER VIA subprocess/Popen.
#
# PURPOSE
# - Run ONLY P00_BASE across all climate-compatible PALMSIM ASUs.
# - Save compact per-ASU outputs only.
# - Use checkpoint/resume so interrupted runs can continue safely.
#
# SCIENTIFIC GUARDRAILS
# - Output = modelled productivity potential, NOT actual yield.
# - Age-derived planting year remains a proxy.
# - No missing-weather fallback.
# - CHIRPS v2 Final = rainfall forcing.
# - ERA5-Land = radiation forcing.
# - SoilGrids sand/silt/clay are NOT injected into PALMSIM.
# ============================================================

from pathlib import Path
import os
import sys
import json
import time
import traceback
import warnings

import numpy as np
import pandas as pd

WORKDIR = Path(
    r"C:\Users\user\Documents\KERJA\SPATIAL DATA ANALYST INTERN\04_YIELD"
)
os.chdir(WORKDIR)

REG = WORKDIR / "40C01B_PALMSIM_SOURCE_REGISTRATION_SIAK_AOI01_V1.json"

ELIGIBLE_FILE = WORKDIR / (
    "40C01_PALMSIM_ELIGIBLE_ASU_MANIFEST_SIAK_AOI01_V1.csv"
)

CHIRPS_FILE = WORKDIR / (
    "40B04B1_CHIRPS_V2_DAILY_NATIVE_CELLS_"
    "2001_2025_SIAK_AOI01_V1.csv"
)

ERA5_FILE = WORKDIR / (
    "40B04B2_ERA5LAND_DAILY_NATIVE_CELLS_"
    "2001_2025_SIAK_AOI01_V4.csv"
)

OUT_RESULTS = WORKDIR / (
    "40C04A_PALMSIM_P00_BASELINE_RESULTS_SIAK_AOI01_V1.csv"
)

OUT_EXCLUSIONS = WORKDIR / (
    "40C04A_PALMSIM_P00_BASELINE_EXCLUSIONS_SIAK_AOI01_V1.csv"
)

OUT_FAILURES = WORKDIR / (
    "40C04A_PALMSIM_P00_BASELINE_FAILURES_SIAK_AOI01_V1.csv"
)

OUT_QC = WORKDIR / (
    "40C04A_PALMSIM_P00_BASELINE_QC_SIAK_AOI01_V1.json"
)

CHECKPOINT = WORKDIR / (
    "40C04A_PALMSIM_P00_BASELINE_CHECKPOINT_SIAK_AOI01_V1.csv"
)

REFERENCE_YEAR = 2025
CLIMATE_START = pd.Timestamp("2001-01-01")
CLIMATE_END = pd.Timestamp("2025-12-31")
CHECKPOINT_EVERY = 10

BASE_DENSITY = 143.0
BASE_SOIL_DEPTH = 1.0

print("====================================================", flush=True)
print("40C04A — PALMSIM P00 BASELINE BATCH", flush=True)
print("====================================================", flush=True)
print("Python :", sys.executable, flush=True)
print("Workdir:", WORKDIR, flush=True)

for p in [REG, ELIGIBLE_FILE, CHIRPS_FILE, ERA5_FILE]:
    if not p.exists():
        raise FileNotFoundError(f"Missing required input: {p}")

warnings.filterwarnings(
    "ignore",
    message=r".*errors='ignore' is deprecated.*",
    category=FutureWarning
)

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

print("PALMSIM import: PASS", flush=True)

asu = pd.read_csv(ELIGIBLE_FILE)

required = [
    "UNIT_ID",
    "AGE_PROXY_YR",
    "ASU_LATITUDE",
    "CHIRPS_CELL_ID",
    "ERA5L_CELL_ID",
]
missing = [c for c in required if c not in asu.columns]
if missing:
    raise ValueError(f"Missing ASU columns: {missing}")

asu["AGE_PROXY_YR"] = pd.to_numeric(asu["AGE_PROXY_YR"], errors="coerce")
asu["ASU_LATITUDE"] = pd.to_numeric(asu["ASU_LATITUDE"], errors="coerce")
asu["CHIRPS_CELL_ID"] = asu["CHIRPS_CELL_ID"].astype(str)
asu["ERA5L_CELL_ID"] = asu["ERA5L_CELL_ID"].astype(str)

audit = []

for _, r in asu.iterrows():
    age = r["AGE_PROXY_YR"]
    reason = None

    if pd.isna(age):
        reason = "MISSING_AGE_PROXY"
        model_age = None
        yop = None
        start = None
        end = None
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

    audit.append({
        "UNIT_ID": str(r["UNIT_ID"]),
        "MODEL_AGE_YR_ROUNDED": model_age,
        "YEAR_OF_PLANTING_PROXY": yop,
        "SIMULATION_START": None if start is None else start.strftime("%Y-%m-%d"),
        "SIMULATION_END": None if end is None else end.strftime("%Y-%m-%d"),
        "EXCLUSION_REASON": reason,
    })

audit = pd.DataFrame(audit)

asu = asu.merge(
    audit,
    on="UNIT_ID",
    how="left",
    validate="one_to_one"
)

batch_asu = asu[asu["EXCLUSION_REASON"].isna()].copy()
exclusions = asu[asu["EXCLUSION_REASON"].notna()].copy()

exclusions.to_csv(OUT_EXCLUSIONS, index=False, encoding="utf-8-sig")

print("\nInput ASUs             :", len(asu), flush=True)
print("Climate-compatible    :", len(batch_asu), flush=True)
print("Pre-run exclusions    :", len(exclusions), flush=True)

if len(exclusions):
    print(exclusions["EXCLUSION_REASON"].value_counts().to_string(), flush=True)

if len(batch_asu) == 0:
    raise RuntimeError("No climate-compatible ASUs remain.")

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
    cid: g[["DATE", "RAIN_MM_DAY"]]
        .sort_values("DATE")
        .set_index("DATE")
    for cid, g in chirps.groupby("CHIRPS_CELL_ID", sort=False)
}

era_by_cell = {
    cid: g[["DATE", "RAD_MJ_M2_DAY"]]
        .sort_values("DATE")
        .set_index("DATE")
    for cid, g in era.groupby("ERA5L_CELL_ID", sort=False)
}

pair_cache = {}

for _, r in (
    batch_asu[["CHIRPS_CELL_ID", "ERA5L_CELL_ID"]]
    .drop_duplicates()
    .iterrows()
):
    c = str(r["CHIRPS_CELL_ID"])
    e = str(r["ERA5L_CELL_ID"])

    if c not in chirps_by_cell:
        raise KeyError(f"Missing CHIRPS cell: {c}")
    if e not in era_by_cell:
        raise KeyError(f"Missing ERA5-Land cell: {e}")

    pair_cache[(c, e)] = chirps_by_cell[c].join(
        era_by_cell[e],
        how="inner"
    )

print("\nClimate-pair cache:", len(pair_cache), flush=True)

del chirps, era

records = []
completed = set()

if CHECKPOINT.exists():
    try:
        old = pd.read_csv(CHECKPOINT)
        if len(old) and "UNIT_ID" in old.columns:
            records = old.to_dict("records")
            completed = set(old["UNIT_ID"].astype(str))
            print("Resume checkpoint rows:", len(completed), flush=True)
    except Exception as e:
        print("Checkpoint load warning:", repr(e), flush=True)

failures = []

def save_checkpoint():
    if not records:
        return
    tmp = CHECKPOINT.with_suffix(".tmp.csv")
    pd.DataFrame(records).to_csv(
        tmp,
        index=False,
        encoding="utf-8-sig"
    )
    os.replace(tmp, CHECKPOINT)

def get_ffb_col(df):
    preferred = "generative_FFB_production (t/ha/yr)"
    if preferred in df.columns:
        return preferred

    cands = [
        c for c in df.columns
        if "ffb" in str(c).lower()
        and "production" in str(c).lower()
    ]
    if not cands:
        cands = [c for c in df.columns if "ffb" in str(c).lower()]
    return cands[0] if cands else None

total = len(batch_asu)
t0 = time.time()

print("\nStarting P00 baseline batch...", flush=True)

for i, (_, r) in enumerate(batch_asu.iterrows(), start=1):

    unit_id = str(r["UNIT_ID"])

    if unit_id in completed:
        continue

    try:
        model_age = int(r["MODEL_AGE_YR_ROUNDED"])
        yop = int(r["YEAR_OF_PLANTING_PROXY"])
        duration = model_age * 365

        start = pd.Timestamp(r["SIMULATION_START"])
        end = pd.Timestamp(r["SIMULATION_END"])

        c_id = str(r["CHIRPS_CELL_ID"])
        e_id = str(r["ERA5L_CELL_ID"])

        w = pair_cache[(c_id, e_id)].loc[start:end].copy()

        if len(w) != duration:
            raise RuntimeError(
                f"weather rows {len(w)} != duration {duration}"
            )

        if w[["RAIN_MM_DAY", "RAD_MJ_M2_DAY"]].isna().any().any():
            raise RuntimeError("missing climate forcing")

        if not w.index.equals(pd.date_range(start, end, freq="D")):
            raise RuntimeError("non-contiguous daily forcing calendar")

        p = PalmField(year_of_planting=yop)
        p.latitude = float(r["ASU_LATITUDE"])
        p.weather.rainfall_series = w["RAIN_MM_DAY"].copy()
        p.weather.radiation_series = w["RAD_MJ_M2_DAY"].copy()

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

        ffb = raw / 1000.0

        n1 = min(36, len(ffb))
        n3 = min(109, len(ffb))

        trailing1 = ffb.tail(n1)
        trailing3 = ffb.tail(n3)

        rec = {
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
            "TRAILING_1Y_MEAN_T_HA_YR": float(trailing1.mean()),
            "TRAILING_1Y_MEDIAN_T_HA_YR": float(trailing1.median()),
            "TRAILING_3Y_MEAN_T_HA_YR": float(trailing3.mean()),
            "RUN_STATUS": "PASS",
        }

        records.append(rec)
        completed.add(unit_id)

    except Exception as e:
        failures.append({
            "UNIT_ID": unit_id,
            "ERROR": repr(e),
            "TRACEBACK": traceback.format_exc()[-5000:],
        })

    if i % CHECKPOINT_EVERY == 0 or i == total:
        save_checkpoint()

        elapsed = time.time() - t0
        done = len(completed)

        print(
            f"Progress: {done}/{total} "
            f"({100.0*done/total:.1f}%) | "
            f"failures={len(failures)} | "
            f"elapsed={elapsed/60:.1f} min",
            flush=True
        )

results = pd.DataFrame(records)

if len(results):
    results = (
        results
        .drop_duplicates(subset=["UNIT_ID"], keep="last")
        .sort_values("UNIT_ID")
        .reset_index(drop=True)
    )

results.to_csv(
    OUT_RESULTS,
    index=False,
    encoding="utf-8-sig"
)

pd.DataFrame(
    failures,
    columns=["UNIT_ID", "ERROR", "TRACEBACK"]
).to_csv(
    OUT_FAILURES,
    index=False,
    encoding="utf-8-sig"
)

expected_ids = set(batch_asu["UNIT_ID"].astype(str))
actual_ids = set(results["UNIT_ID"].astype(str)) if len(results) else set()
missing_ids = expected_ids - actual_ids

metric = (
    results["TRAILING_1Y_MEAN_T_HA_YR"]
    if len(results)
    else pd.Series(dtype=float)
)

finite_nonnegative = bool(
    len(metric)
    and np.isfinite(pd.to_numeric(metric, errors="coerce")).all()
    and (pd.to_numeric(metric, errors="coerce") >= 0).all()
)

if len(missing_ids) == 0 and len(failures) == 0 and finite_nonnegative:
    status = (
        "PASS"
        if len(exclusions) == 0
        else "PASS_WITH_CLIMATE_WINDOW_EXCLUSIONS"
    )
    next_gate = (
        "40C04B-C combined sensitivity batch: "
        "P01/P02 density + P03/P04 soil-depth, then 40C05 summary."
    )
else:
    status = "CHECK_PARTIAL_BASELINE"
    next_gate = (
        "Rerun this same 40C04A script to resume missing baseline ASUs."
    )

def q(s, p):
    return None if len(s) == 0 else float(
        pd.to_numeric(s, errors="coerce").quantile(p)
    )

qc = {
    "gate": "40C04A",
    "status": status,
    "input_palmsim_asus": int(len(asu)),
    "climate_compatible_asus": int(len(batch_asu)),
    "pre_run_exclusions": int(len(exclusions)),
    "completed_baseline_asus": int(len(actual_ids)),
    "missing_baseline_asus": int(len(missing_ids)),
    "failures_this_session": int(len(failures)),
    "baseline_distribution_trailing_1y_t_ha_yr": {
        "min": None if len(metric) == 0 else float(metric.min()),
        "p05": q(metric, 0.05),
        "median": q(metric, 0.50),
        "p95": q(metric, 0.95),
        "max": None if len(metric) == 0 else float(metric.max()),
    },
    "scientific_guardrails": [
        "Modelled productivity potential only; not actual FFB yield.",
        "Age-derived planting year is a proxy.",
        "No climate forcing before 2001 is fabricated.",
        "CHIRPS v2 Final rainfall + ERA5-Land radiation.",
        "SoilGrids sand/silt/clay not injected into PALMSIM.",
        "Baseline density=143 palms/ha and soil depth=1.0 m are scenario assumptions.",
    ],
    "next_gate": next_gate,
}

OUT_QC.write_text(json.dumps(qc, indent=2), encoding="utf-8")

elapsed = time.time() - t0

print("\n====================================================", flush=True)
print("40C04A FINISHED", flush=True)
print("====================================================", flush=True)
print("Status                 :", status, flush=True)
print("Input PALMSIM ASUs     :", len(asu), flush=True)
print("Climate-compatible     :", len(batch_asu), flush=True)
print("Pre-run exclusions     :", len(exclusions), flush=True)
print("Completed baseline     :", len(actual_ids), flush=True)
print("Missing baseline       :", len(missing_ids), flush=True)
print("Failures this session  :", len(failures), flush=True)
print("Elapsed                :", f"{elapsed/60:.1f} min", flush=True)

if len(metric):
    print("\nBaseline trailing-1Y potential:", flush=True)
    print("  min    :", float(metric.min()), flush=True)
    print("  median :", float(metric.median()), flush=True)
    print("  max    :", float(metric.max()), flush=True)
    print("  unit   : t fresh FFB/ha/yr", flush=True)

print("\nResults:", OUT_RESULTS, flush=True)
print("QC     :", OUT_QC, flush=True)
print("Next   :", next_gate, flush=True)
print("====================================================", flush=True)
