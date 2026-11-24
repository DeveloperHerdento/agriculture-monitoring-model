# ============================================================
# OUTPUT 4 / 40C04–40C05 COMBINED
# PALMSIM BATCH EXECUTION + SENSITIVITY/QC SUMMARY
# SIAK_AOI01
#
# RUN FROM JUPYTER VIA subprocess.
#
# WHY COMBINED?
# - 40C03 already proved all P00-P04 scenarios are deterministic
#   and responsive on the smoke-test ASU.
# - Therefore the 654-ASU batch only needs one execution per
#   scenario, followed immediately by lightweight aggregation/QC.
#
# MEMORY / STORAGE POLICY
# - Climate stays at 12 CHIRPS cells + 6 ERA5-Land cells.
# - Weather is joined on demand via climate-pair cache.
# - Full 181-column PALMSIM time series are NOT saved for 3270 runs.
# - Only compact per-run metrics + per-ASU summaries are retained.
# - Incremental checkpoints allow safe resume after interruption.
#
# SCIENTIFIC GUARDRAILS
# - No actual FFB/yield validation claim.
# - Age-derived planting year remains a proxy.
# - No missing-weather fallback.
# - SoilGrids sand/silt/clay are NOT injected into PALMSIM.
# - Density and soil depth are scenario assumptions.
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

# -----------------------------
# INPUTS
# -----------------------------

REG = WORKDIR / "40C01B_PALMSIM_SOURCE_REGISTRATION_SIAK_AOI01_V1.json"

ELIGIBLE_FILE = WORKDIR / (
    "40C01_PALMSIM_ELIGIBLE_ASU_MANIFEST_SIAK_AOI01_V1.csv"
)

SCENARIO_FILE = WORKDIR / (
    "40C01_PALMSIM_SENSITIVITY_SCENARIOS_SIAK_AOI01_V1.csv"
)

CHIRPS_FILE = WORKDIR / (
    "40B04B1_CHIRPS_V2_DAILY_NATIVE_CELLS_"
    "2001_2025_SIAK_AOI01_V1.csv"
)

ERA5_FILE = WORKDIR / (
    "40B04B2_ERA5LAND_DAILY_NATIVE_CELLS_"
    "2001_2025_SIAK_AOI01_V4.csv"
)

# -----------------------------
# OUTPUTS
# -----------------------------

OUT_RUNS = WORKDIR / (
    "40C04_05_PALMSIM_BATCH_SCENARIO_RESULTS_SIAK_AOI01_V1.csv"
)

OUT_ASU = WORKDIR / (
    "40C04_05_PALMSIM_ASU_SENSITIVITY_SUMMARY_SIAK_AOI01_V1.csv"
)

OUT_EXCLUSIONS = WORKDIR / (
    "40C04_05_PALMSIM_BATCH_EXCLUSIONS_SIAK_AOI01_V1.csv"
)

OUT_FAILURES = WORKDIR / (
    "40C04_05_PALMSIM_BATCH_FAILURES_SIAK_AOI01_V1.csv"
)

OUT_QC = WORKDIR / (
    "40C04_05_PALMSIM_BATCH_QC_SIAK_AOI01_V1.json"
)

CHECKPOINT = WORKDIR / (
    "40C04_05_PALMSIM_BATCH_CHECKPOINT_SIAK_AOI01_V1.csv"
)

REFERENCE_YEAR = 2025
CLIMATE_START = pd.Timestamp("2001-01-01")
CLIMATE_END = pd.Timestamp("2025-12-31")

CHECKPOINT_EVERY_ASU = 20

print("====================================================")
print("40C04–40C05 — PALMSIM BATCH + SENSITIVITY SUMMARY")
print("====================================================")
print("Python :", sys.executable)
print("Workdir:", WORKDIR)

for p in [REG, ELIGIBLE_FILE, SCENARIO_FILE, CHIRPS_FILE, ERA5_FILE]:
    if not p.exists():
        raise FileNotFoundError(f"Missing required input: {p}")

# Suppress only the known PALMSIM/pandas deprecation warning.
warnings.filterwarnings(
    "ignore",
    message=r".*errors='ignore' is deprecated.*",
    category=FutureWarning
)

# ============================================================
# 1. LOAD PALMSIM
# ============================================================

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

# ============================================================
# 2. LOAD ELIGIBLE ASUs + SCENARIOS
# ============================================================

asu = pd.read_csv(ELIGIBLE_FILE)
scenarios = pd.read_csv(SCENARIO_FILE)

if len(asu) != 654:
    print(
        f"WARNING: frozen PALMSIM eligible manifest has {len(asu)} rows, "
        "not the previously expected 654. Continuing with file contents."
    )

required_asu = [
    "UNIT_ID",
    "AGE_PROXY_YR",
    "ASU_LATITUDE",
    "CHIRPS_CELL_ID",
    "ERA5L_CELL_ID",
]

missing = [c for c in required_asu if c not in asu.columns]
if missing:
    raise ValueError(f"Missing ASU columns: {missing}")

required_scen = [
    "SCENARIO_ID",
    "SCENARIO_ROLE",
    "PALM_DENSITY_PALMS_HA",
    "SOIL_DEPTH_M",
]

missing = [c for c in required_scen if c not in scenarios.columns]
if missing:
    raise ValueError(f"Missing scenario columns: {missing}")

expected_ids = [
    "P00_BASE",
    "P01_DENS_LOW",
    "P02_DENS_HIGH",
    "P03_DEPTH_SHALLOW",
    "P04_DEPTH_DEEP",
]

if scenarios["SCENARIO_ID"].astype(str).tolist() != expected_ids:
    raise ValueError("P00-P04 scenario matrix changed unexpectedly.")

asu["AGE_PROXY_YR"] = pd.to_numeric(asu["AGE_PROXY_YR"], errors="coerce")
asu["ASU_LATITUDE"] = pd.to_numeric(asu["ASU_LATITUDE"], errors="coerce")
asu["CHIRPS_CELL_ID"] = asu["CHIRPS_CELL_ID"].astype(str)
asu["ERA5L_CELL_ID"] = asu["ERA5L_CELL_ID"].astype(str)

# ============================================================
# 3. CLIMATE SUPPORT AUDIT PER ASU
# ============================================================

audit_rows = []

for _, r in asu.iterrows():
    unit_id = str(r["UNIT_ID"])
    age = r["AGE_PROXY_YR"]

    reason = None

    if pd.isna(age):
        reason = "MISSING_AGE_PROXY"
        model_age_years = None
        yop = None
        start = None
        end = None

    else:
        model_age_years = int(round(float(age)))

        if model_age_years < 1:
            reason = "AGE_PROXY_LT_1_YEAR"

        yop = REFERENCE_YEAR - model_age_years
        start = pd.Timestamp(year=yop, month=1, day=1)
        duration_days = model_age_years * 365
        end = start + pd.Timedelta(days=duration_days - 1)

        if reason is None and start < CLIMATE_START:
            reason = "CLIMATE_WINDOW_START_BEFORE_2001"

        if reason is None and end > CLIMATE_END:
            reason = "CLIMATE_WINDOW_END_AFTER_2025"

    audit_rows.append({
        "UNIT_ID": unit_id,
        "AGE_PROXY_YR": age,
        "MODEL_AGE_YR_ROUNDED": model_age_years,
        "YEAR_OF_PLANTING_PROXY": yop,
        "SIMULATION_START": None if start is None else start.strftime("%Y-%m-%d"),
        "SIMULATION_END": None if end is None else end.strftime("%Y-%m-%d"),
        "EXCLUSION_REASON": reason,
    })

audit = pd.DataFrame(audit_rows)

asu = asu.merge(
    audit,
    on=["UNIT_ID", "AGE_PROXY_YR"],
    how="left",
    validate="one_to_one"
)

batch_asu = asu[asu["EXCLUSION_REASON"].isna()].copy()
exclusions = asu[asu["EXCLUSION_REASON"].notna()].copy()

exclusions.to_csv(
    OUT_EXCLUSIONS,
    index=False,
    encoding="utf-8-sig"
)

print("\nBatch support audit:")
print("  PALMSIM input ASUs        :", len(asu))
print("  Climate-compatible ASUs   :", len(batch_asu))
print("  Excluded before model run :", len(exclusions))

if len(exclusions):
    print("  Exclusion reasons:")
    print(exclusions["EXCLUSION_REASON"].value_counts().to_string())

if len(batch_asu) == 0:
    raise RuntimeError("No ASUs remain eligible after climate-window audit.")

# ============================================================
# 4. LOAD CLIMATE ONCE + BUILD 12 PAIR CACHE
# ============================================================

chirps = pd.read_csv(
    CHIRPS_FILE,
    usecols=["DATE", "CHIRPS_CELL_ID", "RAIN_MM_DAY"]
)

era = pd.read_csv(
    ERA5_FILE,
    usecols=[
        "DATE",
        "ERA5L_CELL_ID",
        "RAD_MJ_M2_DAY",
    ]
)

chirps["DATE"] = pd.to_datetime(chirps["DATE"]).dt.normalize()
era["DATE"] = pd.to_datetime(era["DATE"]).dt.normalize()

chirps["CHIRPS_CELL_ID"] = chirps["CHIRPS_CELL_ID"].astype(str)
era["ERA5L_CELL_ID"] = era["ERA5L_CELL_ID"].astype(str)

# Compact dictionaries by native cell.
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

# Pair cache generated only for pairs needed by batch ASUs.
pair_cache = {}

unique_pairs = (
    batch_asu[["CHIRPS_CELL_ID", "ERA5L_CELL_ID"]]
    .drop_duplicates()
    .reset_index(drop=True)
)

for _, pr in unique_pairs.iterrows():
    c_id = str(pr["CHIRPS_CELL_ID"])
    e_id = str(pr["ERA5L_CELL_ID"])

    if c_id not in chirps_by_cell:
        raise KeyError(f"Missing CHIRPS cell: {c_id}")
    if e_id not in era_by_cell:
        raise KeyError(f"Missing ERA5-Land cell: {e_id}")

    w = chirps_by_cell[c_id].join(
        era_by_cell[e_id],
        how="inner"
    )

    pair_cache[(c_id, e_id)] = w

print("\nClimate cache:")
print("  CHIRPS cells loaded :", len(chirps_by_cell))
print("  ERA5L cells loaded  :", len(era_by_cell))
print("  Climate pairs cached:", len(pair_cache))

# Release original tables.
del chirps, era

# ============================================================
# 5. RESUME CHECKPOINT IF PRESENT
# ============================================================

result_records = []
completed_run_ids = set()

if CHECKPOINT.exists():
    try:
        old = pd.read_csv(CHECKPOINT)
        if len(old) and "RUN_ID" in old.columns:
            result_records = old.to_dict("records")
            completed_run_ids = set(old["RUN_ID"].astype(str))
            print("\nResume checkpoint:")
            print("  Existing completed runs:", len(completed_run_ids))
    except Exception as e:
        print("\nWARNING: checkpoint could not be loaded:", repr(e))
        print("Starting fresh.")
        result_records = []
        completed_run_ids = set()

failures = []

# ============================================================
# 6. HELPERS
# ============================================================

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


def run_one(r, s):
    unit_id = str(r["UNIT_ID"])
    age_proxy = float(r["AGE_PROXY_YR"])
    model_age_years = int(r["MODEL_AGE_YR_ROUNDED"])
    yop = int(r["YEAR_OF_PLANTING_PROXY"])
    latitude = float(r["ASU_LATITUDE"])

    c_id = str(r["CHIRPS_CELL_ID"])
    e_id = str(r["ERA5L_CELL_ID"])

    start = pd.Timestamp(r["SIMULATION_START"])
    end = pd.Timestamp(r["SIMULATION_END"])
    duration_days = model_age_years * 365

    density = float(s["PALM_DENSITY_PALMS_HA"])
    soil_depth = float(s["SOIL_DEPTH_M"])
    sid = str(s["SCENARIO_ID"])

    run_id = f"{unit_id}__{sid}"

    w = pair_cache[(c_id, e_id)].loc[start:end].copy()

    if len(w) != duration_days:
        raise RuntimeError(
            f"{run_id}: weather rows {len(w)} != {duration_days}"
        )

    if w[["RAIN_MM_DAY", "RAD_MJ_M2_DAY"]].isna().any().any():
        raise RuntimeError(
            f"{run_id}: missing weather inside simulation window"
        )

    # Strong contiguous-calendar check.
    expected = pd.date_range(start, end, freq="D")
    if not w.index.equals(expected):
        raise RuntimeError(
            f"{run_id}: weather calendar is not contiguous"
        )

    p = PalmField(year_of_planting=yop)
    p.latitude = latitude

    p.weather.rainfall_series = w["RAIN_MM_DAY"].copy()
    p.weather.radiation_series = w["RAD_MJ_M2_DAY"].copy()

    # Confirmed setters from 40C02D/E.
    p.planting_density = density
    p.soil.soil_depth = soil_depth

    df = p.run(duration=duration_days)

    if not isinstance(df, pd.DataFrame) or len(df) == 0:
        raise RuntimeError(f"{run_id}: PALMSIM returned empty output")

    ffb_col = get_ffb_col(df)
    if ffb_col is None:
        raise RuntimeError(f"{run_id}: FFB output column missing")

    raw = pd.to_numeric(df[ffb_col], errors="coerce").dropna()

    if len(raw) == 0:
        raise RuntimeError(f"{run_id}: FFB output contains no numeric values")

    # Source audit: raw PALMSIM FFB is kg fresh mass/ha/yr,
    # despite inconsistent displayed label. Canonical Output-4 unit = /1000.
    ffb = raw / 1000.0

    # PALMSIM output is ~10-day steps.
    n1 = min(36, len(ffb))   # ~1 model year
    n3 = min(109, len(ffb))  # ~3 model years

    trailing1 = ffb.tail(n1)
    trailing3 = ffb.tail(n3)

    return {
        "RUN_ID": run_id,
        "UNIT_ID": unit_id,
        "SCENARIO_ID": sid,
        "SCENARIO_ROLE": str(s["SCENARIO_ROLE"]),

        "AGE_PROXY_YR": age_proxy,
        "MODEL_AGE_YR_ROUNDED": model_age_years,
        "YEAR_OF_PLANTING_PROXY": yop,
        "ASU_LATITUDE": latitude,

        "CHIRPS_CELL_ID": c_id,
        "ERA5L_CELL_ID": e_id,

        "PALM_DENSITY_PALMS_HA": density,
        "SOIL_DEPTH_M": soil_depth,

        "SIMULATION_START": start.strftime("%Y-%m-%d"),
        "SIMULATION_END": end.strftime("%Y-%m-%d"),
        "DURATION_DAYS": duration_days,

        "MODEL_OUTPUT_ROWS": int(len(df)),
        "FFB_SOURCE_COLUMN": ffb_col,

        "FINAL_FFB_POTENTIAL_T_HA_YR": float(ffb.iloc[-1]),

        "TRAILING_1Y_MEAN_T_HA_YR": float(trailing1.mean()),
        "TRAILING_1Y_MEDIAN_T_HA_YR": float(trailing1.median()),
        "TRAILING_1Y_MIN_T_HA_YR": float(trailing1.min()),
        "TRAILING_1Y_MAX_T_HA_YR": float(trailing1.max()),

        "TRAILING_3Y_MEAN_T_HA_YR": float(trailing3.mean()),
        "TRAILING_3Y_MEDIAN_T_HA_YR": float(trailing3.median()),

        "RUN_STATUS": "PASS",
    }


def save_checkpoint(records):
    if not records:
        return

    tmp = CHECKPOINT.with_suffix(".tmp.csv")
    pd.DataFrame(records).to_csv(
        tmp,
        index=False,
        encoding="utf-8-sig"
    )
    os.replace(tmp, CHECKPOINT)

# ============================================================
# 7. RUN BATCH
# ============================================================

planned_runs = len(batch_asu) * len(scenarios)

print("\nBatch execution:")
print("  ASUs               :", len(batch_asu))
print("  Scenarios / ASU    :", len(scenarios))
print("  Planned model runs :", planned_runs)
print("  Already completed  :", len(completed_run_ids))

t0 = time.time()
new_runs = 0

for asu_counter, (_, r) in enumerate(batch_asu.iterrows(), start=1):

    for _, s in scenarios.iterrows():
        run_id = f"{r['UNIT_ID']}__{s['SCENARIO_ID']}"

        if run_id in completed_run_ids:
            continue

        try:
            rec = run_one(r, s)
            result_records.append(rec)
            completed_run_ids.add(run_id)
            new_runs += 1

        except Exception as e:
            failures.append({
                "RUN_ID": run_id,
                "UNIT_ID": str(r["UNIT_ID"]),
                "SCENARIO_ID": str(s["SCENARIO_ID"]),
                "ERROR": repr(e),
                "TRACEBACK": traceback.format_exc()[-6000:],
            })

    if (
        asu_counter % CHECKPOINT_EVERY_ASU == 0
        or asu_counter == len(batch_asu)
    ):
        save_checkpoint(result_records)

        elapsed = time.time() - t0
        done = len(completed_run_ids)
        pct = 100.0 * done / planned_runs if planned_runs else 100.0

        print(
            f"  Progress: ASU {asu_counter}/{len(batch_asu)} | "
            f"runs {done}/{planned_runs} ({pct:.1f}%) | "
            f"new this session={new_runs} | "
            f"elapsed={elapsed/60:.1f} min"
        )

# ============================================================
# 8. FINAL RUN TABLE
# ============================================================

runs = pd.DataFrame(result_records)

if len(runs):
    runs = (
        runs
        .drop_duplicates(subset=["RUN_ID"], keep="last")
        .sort_values(["UNIT_ID", "SCENARIO_ID"])
        .reset_index(drop=True)
    )

runs.to_csv(
    OUT_RUNS,
    index=False,
    encoding="utf-8-sig"
)

if failures:
    pd.DataFrame(failures).to_csv(
        OUT_FAILURES,
        index=False,
        encoding="utf-8-sig"
    )
else:
    pd.DataFrame(
        columns=["RUN_ID", "UNIT_ID", "SCENARIO_ID", "ERROR", "TRACEBACK"]
    ).to_csv(
        OUT_FAILURES,
        index=False,
        encoding="utf-8-sig"
    )

# ============================================================
# 9. 40C05 — PER-ASU SENSITIVITY SUMMARY
# ============================================================

expected_run_set = {
    f"{u}__{s}"
    for u in batch_asu["UNIT_ID"].astype(str)
    for s in expected_ids
}

actual_run_set = set(runs["RUN_ID"].astype(str)) if len(runs) else set()
missing_run_ids = sorted(expected_run_set - actual_run_set)

summary_rows = []

for unit_id, g in runs.groupby("UNIT_ID", sort=False):
    g = g.set_index("SCENARIO_ID")

    if not set(expected_ids).issubset(set(g.index)):
        continue

    b = g.loc["P00_BASE"]
    dl = g.loc["P01_DENS_LOW"]
    dh = g.loc["P02_DENS_HIGH"]
    zs = g.loc["P03_DEPTH_SHALLOW"]
    zd = g.loc["P04_DEPTH_DEEP"]

    base = float(b["TRAILING_1Y_MEAN_T_HA_YR"])

    density_vals = np.array([
        float(dl["TRAILING_1Y_MEAN_T_HA_YR"]),
        base,
        float(dh["TRAILING_1Y_MEAN_T_HA_YR"]),
    ])

    depth_vals = np.array([
        float(zs["TRAILING_1Y_MEAN_T_HA_YR"]),
        base,
        float(zd["TRAILING_1Y_MEAN_T_HA_YR"]),
    ])

    all_vals = g.loc[
        expected_ids,
        "TRAILING_1Y_MEAN_T_HA_YR"
    ].astype(float)

    overall_min_sid = str(all_vals.idxmin())
    overall_max_sid = str(all_vals.idxmax())
    overall_range = float(all_vals.max() - all_vals.min())

    summary_rows.append({
        "UNIT_ID": unit_id,

        "AGE_PROXY_YR": float(b["AGE_PROXY_YR"]),
        "MODEL_AGE_YR_ROUNDED": int(b["MODEL_AGE_YR_ROUNDED"]),
        "YEAR_OF_PLANTING_PROXY": int(b["YEAR_OF_PLANTING_PROXY"]),
        "ASU_LATITUDE": float(b["ASU_LATITUDE"]),

        "CHIRPS_CELL_ID": str(b["CHIRPS_CELL_ID"]),
        "ERA5L_CELL_ID": str(b["ERA5L_CELL_ID"]),

        # Baseline is the main PALMSIM productivity-potential metric.
        "PALMSIM_BASELINE_TRAILING_1Y_MEAN_T_HA_YR": base,
        "PALMSIM_BASELINE_TRAILING_3Y_MEAN_T_HA_YR":
            float(b["TRAILING_3Y_MEAN_T_HA_YR"]),
        "PALMSIM_BASELINE_FINAL_POINT_T_HA_YR":
            float(b["FINAL_FFB_POTENTIAL_T_HA_YR"]),

        "P01_DENS_LOW_TRAILING_1Y_MEAN_T_HA_YR":
            float(dl["TRAILING_1Y_MEAN_T_HA_YR"]),
        "P02_DENS_HIGH_TRAILING_1Y_MEAN_T_HA_YR":
            float(dh["TRAILING_1Y_MEAN_T_HA_YR"]),
        "P03_DEPTH_SHALLOW_TRAILING_1Y_MEAN_T_HA_YR":
            float(zs["TRAILING_1Y_MEAN_T_HA_YR"]),
        "P04_DEPTH_DEEP_TRAILING_1Y_MEAN_T_HA_YR":
            float(zd["TRAILING_1Y_MEAN_T_HA_YR"]),

        "DENSITY_SENSITIVITY_RANGE_T_HA_YR":
            float(density_vals.max() - density_vals.min()),

        "DEPTH_SENSITIVITY_RANGE_T_HA_YR":
            float(depth_vals.max() - depth_vals.min()),

        "OVERALL_SCENARIO_RANGE_T_HA_YR":
            overall_range,

        "OVERALL_SCENARIO_RANGE_PCT_OF_BASE":
            np.nan if base == 0 else 100.0 * overall_range / abs(base),

        "MIN_POTENTIAL_SCENARIO": overall_min_sid,
        "MAX_POTENTIAL_SCENARIO": overall_max_sid,

        # Model-only sensitivity indicator; not field uncertainty.
        "PALMSIM_SCENARIO_STD_T_HA_YR":
            float(all_vals.std(ddof=0)),

        "PALMSIM_SCENARIO_CV_PCT":
            np.nan if all_vals.mean() == 0
            else 100.0 * float(all_vals.std(ddof=0)) / abs(float(all_vals.mean())),
    })

asu_summary = pd.DataFrame(summary_rows)

# Carry frozen evidence/support columns into ASU summary when available.
carry_cols = [
    c for c in [
        "UNIT_ID",
        "AGE_VALID_FRACTION",
        "AGE_SUPPORT_FLAG",
        "SAND_0_100_PCT",
        "SILT_0_100_PCT",
        "CLAY_0_100_PCT",
        "CLIMATE_PAIR_ID",
    ]
    if c in batch_asu.columns
]

if len(asu_summary) and carry_cols:
    asu_summary = asu_summary.merge(
        batch_asu[carry_cols],
        on="UNIT_ID",
        how="left",
        validate="one_to_one"
    )

asu_summary.to_csv(
    OUT_ASU,
    index=False,
    encoding="utf-8-sig"
)

# ============================================================
# 10. FINAL QC / FREEZE DECISION
# ============================================================

completed_runs = len(actual_run_set & expected_run_set)
failed_count = len(failures)
missing_count = len(missing_run_ids)

baseline = runs[
    runs["SCENARIO_ID"] == "P00_BASE"
]["TRAILING_1Y_MEAN_T_HA_YR"] if len(runs) else pd.Series(dtype=float)

finite_nonnegative = bool(
    len(runs)
    and np.isfinite(
        pd.to_numeric(runs["TRAILING_1Y_MEAN_T_HA_YR"], errors="coerce")
    ).all()
    and (
        pd.to_numeric(
            runs["TRAILING_1Y_MEAN_T_HA_YR"],
            errors="coerce"
        ) >= 0
    ).all()
)

if (
    missing_count == 0
    and failed_count == 0
    and finite_nonnegative
    and len(asu_summary) == len(batch_asu)
):
    if len(exclusions) == 0:
        status = "PASS"
    else:
        status = "PASS_WITH_CLIMATE_WINDOW_EXCLUSIONS"

    next_gate = (
        "40D APSIM-OilPalm representative benchmark. "
        "PALMSIM batch and scenario-sensitivity outputs are frozen."
    )

elif completed_runs > 0:
    status = "CHECK_PARTIAL_BATCH"
    next_gate = (
        "Rerun this same script to resume missing/failed PALMSIM runs "
        "before moving to APSIM."
    )

else:
    status = "CHECK"
    next_gate = (
        "Resolve PALMSIM batch execution before moving to APSIM."
    )

def q(series, p):
    if len(series) == 0:
        return None
    return float(pd.to_numeric(series, errors="coerce").quantile(p))

qc = {
    "gate": "40C04_40C05_COMBINED",
    "status": status,

    "input": {
        "frozen_palmsim_eligible_asus": int(len(asu)),
        "batch_climate_compatible_asus": int(len(batch_asu)),
        "pre_run_excluded_asus": int(len(exclusions)),
        "scenario_count": int(len(scenarios)),
        "planned_runs": int(planned_runs),
    },

    "execution": {
        "completed_expected_runs": int(completed_runs),
        "missing_expected_runs": int(missing_count),
        "failure_records_this_session": int(failed_count),
        "result_rows": int(len(runs)),
        "asu_summaries_complete": int(len(asu_summary)),
        "finite_nonnegative_outputs": finite_nonnegative,
    },

    "baseline_distribution_trailing_1y_t_ha_yr": {
        "count": int(len(baseline)),
        "min": None if len(baseline) == 0 else float(baseline.min()),
        "p05": q(baseline, 0.05),
        "p25": q(baseline, 0.25),
        "median": q(baseline, 0.50),
        "p75": q(baseline, 0.75),
        "p95": q(baseline, 0.95),
        "max": None if len(baseline) == 0 else float(baseline.max()),
    },

    "storage_policy": {
        "full_timeseries_saved_for_all_runs": False,
        "compact_scenario_metrics_only": True,
        "checkpoint_resume_enabled": True,
        "native_climate_join_on_demand": True,
    },

    "scientific_guardrails": [
        "PALMSIM outputs are modelled productivity potential, not actual FFB yield.",
        "No supervised/local yield accuracy metric is reported.",
        "Age-derived planting year is a proxy.",
        "ASUs requiring forcing before 2001 are excluded rather than silently filled.",
        "CHIRPS v2 Final is primary rainfall.",
        "ERA5-Land provides radiation.",
        "SoilGrids sand/silt/clay are not injected into PALMSIM.",
        "Plant density and soil depth are scenario assumptions.",
        "Scenario spread is model sensitivity, not full empirical uncertainty.",
    ],

    "outputs": {
        "scenario_results_csv": str(OUT_RUNS),
        "asu_sensitivity_summary_csv": str(OUT_ASU),
        "exclusions_csv": str(OUT_EXCLUSIONS),
        "failures_csv": str(OUT_FAILURES),
        "checkpoint_csv": str(CHECKPOINT),
    },

    "next_gate": next_gate,
}

OUT_QC.write_text(
    json.dumps(qc, indent=2),
    encoding="utf-8"
)

# ============================================================
# 11. CONSOLE SUMMARY
# ============================================================

elapsed = time.time() - t0

print("\n====================================================")
print("40C04–40C05 RESULTS")
print("====================================================")
print("Status                     :", status)
print("Input PALMSIM ASUs         :", len(asu))
print("Climate-compatible ASUs    :", len(batch_asu))
print("Pre-run exclusions         :", len(exclusions))
print("Planned runs               :", planned_runs)
print("Completed expected runs    :", completed_runs)
print("Missing expected runs      :", missing_count)
print("Failures this session      :", failed_count)
print("ASU summaries              :", len(asu_summary))
print("Elapsed                    :", f"{elapsed/60:.1f} min")

if len(baseline):
    print("\nBaseline trailing-1Y productivity potential:")
    print("  min    :", float(baseline.min()))
    print("  median :", float(baseline.median()))
    print("  max    :", float(baseline.max()))
    print("  unit   : t fresh FFB/ha/yr")

if len(asu_summary):
    sens = asu_summary["OVERALL_SCENARIO_RANGE_PCT_OF_BASE"]
    print("\nScenario sensitivity:")
    print("  median range vs base :", float(sens.median()), "%")
    print("  p95 range vs base    :", float(sens.quantile(0.95)), "%")

print("\nOutputs:")
print("  Scenario results :", OUT_RUNS)
print("  ASU summary      :", OUT_ASU)
print("  Exclusions       :", OUT_EXCLUSIONS)
print("  Failures         :", OUT_FAILURES)
print("  QC JSON          :", OUT_QC)

print("\nNext:", next_gate)
print("====================================================")
