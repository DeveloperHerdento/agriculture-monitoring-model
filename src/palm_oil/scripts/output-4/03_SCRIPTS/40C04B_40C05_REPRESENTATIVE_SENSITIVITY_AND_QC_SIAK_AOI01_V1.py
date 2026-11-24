# ============================================================
# OUTPUT 4 / 40C04B + 40C05 COMBINED
# REPRESENTATIVE PALMSIM SENSITIVITY + PALMSIM SYNTHESIS/QC
# SIAK_AOI01
#
# RUN DIRECTLY INSIDE THE JUPYTER KERNEL.
#
# DESIGN
# - P00 baseline for all 654 ASUs is already frozen from 40C04A.
# - Do NOT rerun P00.
# - Select up to 4 representative ASUs per climate pair (max 48 ASUs)
#   using deterministic maximin sampling across age proxy,
#   baseline PALMSIM potential, and condition score when available.
# - Run only P01-P04 on the representative sample.
# - Immediately synthesize sensitivity/QC in the same script.
#
# EXPECTED MAX MODEL RUNS:
#   12 climate pairs × 4 ASUs × 4 scenarios = 192 runs
#
# SCIENTIFIC GUARDRAILS
# - Sensitivity sample is representative, NOT local-yield validation.
# - Scenario spread = model sensitivity, NOT empirical uncertainty.
# - P00 baseline remains the PALMSIM productivity-potential backbone.
# - Density and soil depth remain scenario assumptions.
# - SoilGrids sand/silt/clay are NOT injected into PALMSIM.
# ============================================================

from pathlib import Path
import os, sys, json, time, traceback, warnings, gc
import numpy as np
import pandas as pd

WORKDIR = Path(r"C:\Users\user\Documents\KERJA\SPATIAL DATA ANALYST INTERN\04_YIELD")
os.chdir(WORKDIR)

REG = WORKDIR / "40C01B_PALMSIM_SOURCE_REGISTRATION_SIAK_AOI01_V1.json"
BASELINE_FILE = WORKDIR / "40C04A_DIRECT_P00_BASELINE_RESULTS_SIAK_AOI01_V1.csv"
ELIGIBLE_FILE = WORKDIR / "40C01_PALMSIM_ELIGIBLE_ASU_MANIFEST_SIAK_AOI01_V1.csv"
MASTER_FILE = WORKDIR / "40B05_COMMON_MODEL_INPUT_MASTER_SIAK_AOI01_V1.csv"
SCENARIO_FILE = WORKDIR / "40C01_PALMSIM_SENSITIVITY_SCENARIOS_SIAK_AOI01_V1.csv"
CHIRPS_FILE = WORKDIR / "40B04B1_CHIRPS_V2_DAILY_NATIVE_CELLS_2001_2025_SIAK_AOI01_V1.csv"
ERA5_FILE = WORKDIR / "40B04B2_ERA5LAND_DAILY_NATIVE_CELLS_2001_2025_SIAK_AOI01_V4.csv"

OUT_SAMPLE = WORKDIR / "40C04B_REPRESENTATIVE_SENSITIVITY_SAMPLE_SIAK_AOI01_V1.csv"
CHECKPOINT = WORKDIR / "40C04B_REPRESENTATIVE_SENSITIVITY_CHECKPOINT_SIAK_AOI01_V1.csv"
OUT_RUNS = WORKDIR / "40C04B_REPRESENTATIVE_SENSITIVITY_RESULTS_SIAK_AOI01_V1.csv"
OUT_FAILURES = WORKDIR / "40C04B_REPRESENTATIVE_SENSITIVITY_FAILURES_SIAK_AOI01_V1.csv"
OUT_ASU_SENS = WORKDIR / "40C05_PALMSIM_REPRESENTATIVE_ASU_SENSITIVITY_SIAK_AOI01_V1.csv"
OUT_SCEN_SUMMARY = WORKDIR / "40C05_PALMSIM_SCENARIO_SENSITIVITY_SUMMARY_SIAK_AOI01_V1.csv"
OUT_CLIMATE_SUMMARY = WORKDIR / "40C05_PALMSIM_CLIMATE_PAIR_SENSITIVITY_SUMMARY_SIAK_AOI01_V1.csv"
OUT_ZERO_BASELINE = WORKDIR / "40C05_PALMSIM_ZERO_BASELINE_ASUS_SIAK_AOI01_V1.csv"
OUT_QC = WORKDIR / "40C05_PALMSIM_SYNTHESIS_QC_SIAK_AOI01_V1.json"

MAX_PER_CLIMATE_PAIR = 4
SAVE_EVERY = 5

warnings.filterwarnings(
    "ignore",
    message=r".*errors='ignore' is deprecated.*",
    category=FutureWarning
)

print("====================================================")
print("40C04B + 40C05 — REPRESENTATIVE SENSITIVITY + QC")
print("====================================================")
print("Python :", sys.executable)
print("Workdir:", WORKDIR)

for p in [REG, BASELINE_FILE, ELIGIBLE_FILE, SCENARIO_FILE, CHIRPS_FILE, ERA5_FILE]:
    if not p.exists():
        raise FileNotFoundError(f"Missing required input: {p}")

# 1. PALMSIM
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

# 2. Frozen baseline + support features
base = pd.read_csv(BASELINE_FILE)
eligible = pd.read_csv(ELIGIBLE_FILE)

if len(base) != 654 or base["UNIT_ID"].astype(str).nunique() != 654:
    raise ValueError("Frozen baseline must contain 654 unique ASUs.")

base["UNIT_ID"] = base["UNIT_ID"].astype(str)
eligible["UNIT_ID"] = eligible["UNIT_ID"].astype(str)

sample_frame = base.merge(
    eligible,
    on="UNIT_ID",
    how="left",
    suffixes=("", "_ELIG"),
    validate="one_to_one"
)

condition_col = None
if MASTER_FILE.exists():
    master = pd.read_csv(MASTER_FILE)
    master["UNIT_ID"] = master["UNIT_ID"].astype(str)
    for candidate in ["COND_P50", "CONDITION_P50", "CONDITION_SCORE", "CONDITION_SCORE_P50"]:
        if candidate in master.columns:
            condition_col = candidate
            break
    if condition_col is not None:
        sample_frame = sample_frame.merge(
            master[["UNIT_ID", condition_col]],
            on="UNIT_ID",
            how="left",
            validate="one_to_one"
        )

if "CLIMATE_PAIR_ID" not in sample_frame.columns:
    sample_frame["CLIMATE_PAIR_ID"] = (
        sample_frame["CHIRPS_CELL_ID"].astype(str)
        + "__"
        + sample_frame["ERA5L_CELL_ID"].astype(str)
    )
else:
    sample_frame["CLIMATE_PAIR_ID"] = sample_frame["CLIMATE_PAIR_ID"].astype(str)

feature_cols = ["AGE_PROXY_YR", "TRAILING_1Y_MEAN_T_HA_YR"]
if condition_col is not None:
    feature_cols.append(condition_col)

for c in feature_cols:
    sample_frame[c] = pd.to_numeric(sample_frame[c], errors="coerce")

print("\nFrozen baseline:")
print("  ASUs            :", len(base))
print("  Climate pairs   :", sample_frame["CLIMATE_PAIR_ID"].nunique())
print("  Condition field :", condition_col or "not available; sampling uses age + baseline")

# 3. Deterministic representative maximin selection
def maximin_select(group, n_select, features):
    g = group.copy().reset_index(drop=True)
    if len(g) <= n_select:
        return g

    X = g[features].copy()

    for col in features:
        med = X[col].median()
        if pd.isna(med):
            med = 0.0
        X[col] = X[col].fillna(med)

        std = X[col].std(ddof=0)
        if pd.isna(std) or std == 0:
            X[col] = 0.0
        else:
            X[col] = (X[col] - X[col].mean()) / std

    arr = X.to_numpy(dtype=float)
    center_dist = np.sqrt((arr ** 2).sum(axis=1))
    first = int(np.argmin(center_dist))
    selected = [first]
    remaining = set(range(len(g))) - set(selected)

    while len(selected) < n_select and remaining:
        best_idx = None
        best_dist = -1.0

        for idx in sorted(remaining):
            dists = np.sqrt(((arr[idx] - arr[selected]) ** 2).sum(axis=1))
            min_dist = float(dists.min())

            if best_idx is None or min_dist > best_dist:
                best_dist = min_dist
                best_idx = idx
            elif np.isclose(min_dist, best_dist):
                if str(g.loc[idx, "UNIT_ID"]) < str(g.loc[best_idx, "UNIT_ID"]):
                    best_idx = idx

        selected.append(best_idx)
        remaining.remove(best_idx)

    return g.loc[selected].copy()

sample_parts = []

for pair_id, g in sample_frame.groupby("CLIMATE_PAIR_ID", sort=True):
    selected = maximin_select(
        g,
        min(MAX_PER_CLIMATE_PAIR, len(g)),
        feature_cols
    )
    selected["SAMPLE_SELECTION_METHOD"] = (
        "CLIMATE_PAIR_MAXIMIN_AGE_BASELINE"
        + ("_CONDITION" if condition_col else "")
    )
    sample_parts.append(selected)

sample = pd.concat(sample_parts, ignore_index=True)
sample = sample.sort_values(["CLIMATE_PAIR_ID", "UNIT_ID"]).reset_index(drop=True)
sample["SENSITIVITY_SAMPLE_ID"] = [
    f"SENS_{i:03d}" for i in range(1, len(sample) + 1)
]
sample.to_csv(OUT_SAMPLE, index=False, encoding="utf-8-sig")

pair_counts = sample["CLIMATE_PAIR_ID"].value_counts()

print("\nRepresentative sensitivity sample:")
print("  Selected ASUs          :", len(sample))
print("  Climate pairs covered  :", sample["CLIMATE_PAIR_ID"].nunique())
print("  Min sample / pair      :", int(pair_counts.min()))
print("  Max sample / pair      :", int(pair_counts.max()))
print("  Features used          :", ", ".join(feature_cols))

# 4. P01-P04 only
scenarios = pd.read_csv(SCENARIO_FILE)
expected_sens_ids = [
    "P01_DENS_LOW",
    "P02_DENS_HIGH",
    "P03_DEPTH_SHALLOW",
    "P04_DEPTH_DEEP",
]

sens_scenarios = scenarios[
    scenarios["SCENARIO_ID"].isin(expected_sens_ids)
].copy()

if sorted(sens_scenarios["SCENARIO_ID"].tolist()) != sorted(expected_sens_ids):
    raise ValueError("Sensitivity scenario matrix P01-P04 is incomplete.")

planned_runs = len(sample) * len(sens_scenarios)

print("  Sensitivity scenarios  :", len(sens_scenarios))
print("  Planned model runs     :", planned_runs)

# 5. Climate cache
chirps = pd.read_csv(CHIRPS_FILE, usecols=["DATE", "CHIRPS_CELL_ID", "RAIN_MM_DAY"])
era = pd.read_csv(ERA5_FILE, usecols=["DATE", "ERA5L_CELL_ID", "RAD_MJ_M2_DAY"])

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
for _, r in sample[["CHIRPS_CELL_ID", "ERA5L_CELL_ID"]].drop_duplicates().iterrows():
    c_id = str(r["CHIRPS_CELL_ID"])
    e_id = str(r["ERA5L_CELL_ID"])
    pair_cache[(c_id, e_id)] = chirps_by_cell[c_id].join(era_by_cell[e_id], how="inner")

del chirps, era
gc.collect()

print("  Climate pair cache     :", len(pair_cache))

# 6. Resume
records = []
completed_run_ids = set()

if CHECKPOINT.exists():
    old = pd.read_csv(CHECKPOINT)
    if len(old) and "RUN_ID" in old.columns:
        records = old.to_dict("records")
        completed_run_ids = set(old["RUN_ID"].astype(str))

print("  Recovered runs         :", len(completed_run_ids))
print("  Remaining runs         :", planned_runs - len(completed_run_ids))

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
    candidates = [
        c for c in df.columns
        if "ffb" in str(c).lower() and "production" in str(c).lower()
    ]
    if not candidates:
        candidates = [c for c in df.columns if "ffb" in str(c).lower()]
    return candidates[0] if candidates else None

# 7. Sensitivity loop
tasks = []
for _, r in sample.iterrows():
    for _, s in sens_scenarios.iterrows():
        run_id = f"{r['UNIT_ID']}__{s['SCENARIO_ID']}"
        if run_id not in completed_run_ids:
            tasks.append((r, s, run_id))

print("\nStarting representative sensitivity loop...\n")

t0 = time.perf_counter()
recent_times = []

for task_i, (r, s, run_id) in enumerate(tasks, start=1):
    run_t0 = time.perf_counter()

    try:
        model_age = int(r["MODEL_AGE_YR_ROUNDED"])
        yop = int(r["YEAR_OF_PLANTING_PROXY"])
        duration = int(r["DURATION_DAYS"])
        start = pd.Timestamp(r["SIMULATION_START"])
        end = pd.Timestamp(r["SIMULATION_END"])
        c_id = str(r["CHIRPS_CELL_ID"])
        e_id = str(r["ERA5L_CELL_ID"])

        weather = pair_cache[(c_id, e_id)].loc[start:end]

        if len(weather) != duration:
            raise RuntimeError(
                f"{run_id}: weather rows {len(weather)} != duration {duration}"
            )

        if weather[["RAIN_MM_DAY", "RAD_MJ_M2_DAY"]].isna().any().any():
            raise RuntimeError(f"{run_id}: missing climate forcing")

        if not weather.index.equals(pd.date_range(start, end, freq="D")):
            raise RuntimeError(f"{run_id}: non-contiguous climate calendar")

        density = float(s["PALM_DENSITY_PALMS_HA"])
        soil_depth = float(s["SOIL_DEPTH_M"])

        p = PalmField(year_of_planting=yop)
        p.latitude = float(r["ASU_LATITUDE"])
        p.weather.rainfall_series = weather["RAIN_MM_DAY"].copy()
        p.weather.radiation_series = weather["RAD_MJ_M2_DAY"].copy()
        p.planting_density = density
        p.soil.soil_depth = soil_depth

        df = p.run(duration=duration)

        if not isinstance(df, pd.DataFrame) or len(df) == 0:
            raise RuntimeError(f"{run_id}: empty PALMSIM output")

        ffb_col = get_ffb_col(df)
        if ffb_col is None:
            raise RuntimeError(f"{run_id}: FFB column missing")

        raw = pd.to_numeric(df[ffb_col], errors="coerce").dropna()
        if len(raw) == 0:
            raise RuntimeError(f"{run_id}: no numeric FFB output")

        ffb = raw / 1000.0
        n1 = min(36, len(ffb))
        n3 = min(109, len(ffb))

        records.append({
            "RUN_ID": run_id,
            "UNIT_ID": str(r["UNIT_ID"]),
            "SENSITIVITY_SAMPLE_ID": str(r["SENSITIVITY_SAMPLE_ID"]),
            "CLIMATE_PAIR_ID": str(r["CLIMATE_PAIR_ID"]),
            "SCENARIO_ID": str(s["SCENARIO_ID"]),
            "SCENARIO_ROLE": str(s["SCENARIO_ROLE"]),
            "AGE_PROXY_YR": float(r["AGE_PROXY_YR"]),
            "ASU_LATITUDE": float(r["ASU_LATITUDE"]),
            "CHIRPS_CELL_ID": c_id,
            "ERA5L_CELL_ID": e_id,
            "PALM_DENSITY_PALMS_HA": density,
            "SOIL_DEPTH_M": soil_depth,
            "FINAL_FFB_POTENTIAL_T_HA_YR": float(ffb.iloc[-1]),
            "TRAILING_1Y_MEAN_T_HA_YR": float(ffb.tail(n1).mean()),
            "TRAILING_1Y_MEDIAN_T_HA_YR": float(ffb.tail(n1).median()),
            "TRAILING_3Y_MEAN_T_HA_YR": float(ffb.tail(n3).mean()),
            "RUN_STATUS": "PASS",
        })

        completed_run_ids.add(run_id)

    except Exception as e:
        failures.append({
            "RUN_ID": run_id,
            "UNIT_ID": str(r["UNIT_ID"]),
            "SCENARIO_ID": str(s["SCENARIO_ID"]),
            "ERROR": repr(e),
            "TRACEBACK": traceback.format_exc()[-4000:],
        })

    run_sec = time.perf_counter() - run_t0
    recent_times.append(run_sec)

    if task_i % SAVE_EVERY == 0 or task_i == len(tasks):
        save_checkpoint()

        done = len(completed_run_ids)
        remaining = planned_runs - done
        avg20 = float(np.mean(recent_times[-20:]))
        eta_min = remaining * avg20 / 60.0
        elapsed_min = (time.perf_counter() - t0) / 60.0

        print(
            f"Progress: {done}/{planned_runs} "
            f"({100*done/planned_runs:.1f}%) | "
            f"last={run_sec:.1f}s | "
            f"avg20={avg20:.1f}s/run | "
            f"ETA≈{eta_min:.1f} min | "
            f"fail={len(failures)} | "
            f"elapsed={elapsed_min:.1f} min"
        )

    try:
        del p, df
    except Exception:
        pass
    gc.collect()

# 8. Final run table
runs = pd.DataFrame(records)

if len(runs):
    runs = (
        runs
        .drop_duplicates(subset=["RUN_ID"], keep="last")
        .sort_values(["UNIT_ID", "SCENARIO_ID"])
        .reset_index(drop=True)
    )

runs.to_csv(OUT_RUNS, index=False, encoding="utf-8-sig")

pd.DataFrame(
    failures,
    columns=["RUN_ID", "UNIT_ID", "SCENARIO_ID", "ERROR", "TRACEBACK"]
).to_csv(OUT_FAILURES, index=False, encoding="utf-8-sig")

# 9. 40C05 synthesis
sample_base = sample[
    [
        "UNIT_ID",
        "SENSITIVITY_SAMPLE_ID",
        "CLIMATE_PAIR_ID",
        "AGE_PROXY_YR",
        "TRAILING_1Y_MEAN_T_HA_YR",
        "TRAILING_3Y_MEAN_T_HA_YR",
        "FINAL_FFB_POTENTIAL_T_HA_YR",
    ]
].copy()

sample_base = sample_base.rename(columns={
    "TRAILING_1Y_MEAN_T_HA_YR": "P00_BASE_TRAILING_1Y_MEAN_T_HA_YR",
    "TRAILING_3Y_MEAN_T_HA_YR": "P00_BASE_TRAILING_3Y_MEAN_T_HA_YR",
    "FINAL_FFB_POTENTIAL_T_HA_YR": "P00_BASE_FINAL_T_HA_YR",
})

wide = runs.pivot_table(
    index=["UNIT_ID", "SENSITIVITY_SAMPLE_ID", "CLIMATE_PAIR_ID"],
    columns="SCENARIO_ID",
    values="TRAILING_1Y_MEAN_T_HA_YR",
    aggfunc="first"
).reset_index()

wide.columns.name = None

asu_sens = sample_base.merge(
    wide,
    on=["UNIT_ID", "SENSITIVITY_SAMPLE_ID", "CLIMATE_PAIR_ID"],
    how="left",
    validate="one_to_one"
)

base_col = "P00_BASE_TRAILING_1Y_MEAN_T_HA_YR"

for sid in expected_sens_ids:
    if sid not in asu_sens.columns:
        asu_sens[sid] = np.nan

    asu_sens[f"{sid}_DELTA_T_HA_YR"] = (
        asu_sens[sid] - asu_sens[base_col]
    )

    asu_sens[f"{sid}_DELTA_PCT"] = np.where(
        asu_sens[base_col].abs() > 1e-9,
        100.0 * asu_sens[f"{sid}_DELTA_T_HA_YR"] / asu_sens[base_col].abs(),
        np.nan
    )

scenario_value_cols = [base_col] + expected_sens_ids

asu_sens["SCENARIO_MIN_T_HA_YR"] = asu_sens[scenario_value_cols].min(axis=1)
asu_sens["SCENARIO_MAX_T_HA_YR"] = asu_sens[scenario_value_cols].max(axis=1)
asu_sens["SCENARIO_RANGE_T_HA_YR"] = (
    asu_sens["SCENARIO_MAX_T_HA_YR"]
    - asu_sens["SCENARIO_MIN_T_HA_YR"]
)

asu_sens["SCENARIO_RANGE_PCT_OF_BASE"] = np.where(
    asu_sens[base_col].abs() > 1e-9,
    100.0 * asu_sens["SCENARIO_RANGE_T_HA_YR"] / asu_sens[base_col].abs(),
    np.nan
)

asu_sens.to_csv(OUT_ASU_SENS, index=False, encoding="utf-8-sig")

scenario_summary_rows = []

for sid in expected_sens_ids:
    delta_abs = asu_sens[f"{sid}_DELTA_T_HA_YR"].dropna()
    delta_pct = asu_sens[f"{sid}_DELTA_PCT"].dropna()

    scenario_summary_rows.append({
        "SCENARIO_ID": sid,
        "N_ASU": int(len(delta_abs)),
        "DELTA_T_HA_YR_MEAN":
            None if len(delta_abs) == 0 else float(delta_abs.mean()),
        "DELTA_T_HA_YR_MEDIAN":
            None if len(delta_abs) == 0 else float(delta_abs.median()),
        "DELTA_T_HA_YR_P05":
            None if len(delta_abs) == 0 else float(delta_abs.quantile(0.05)),
        "DELTA_T_HA_YR_P95":
            None if len(delta_abs) == 0 else float(delta_abs.quantile(0.95)),
        "DELTA_PCT_MEDIAN":
            None if len(delta_pct) == 0 else float(delta_pct.median()),
        "DELTA_PCT_P05":
            None if len(delta_pct) == 0 else float(delta_pct.quantile(0.05)),
        "DELTA_PCT_P95":
            None if len(delta_pct) == 0 else float(delta_pct.quantile(0.95)),
    })

scenario_summary = pd.DataFrame(scenario_summary_rows)
scenario_summary.to_csv(OUT_SCEN_SUMMARY, index=False, encoding="utf-8-sig")

climate_summary = (
    asu_sens
    .groupby("CLIMATE_PAIR_ID", as_index=False)
    .agg(
        N_SAMPLE_ASU=("UNIT_ID", "count"),
        BASELINE_MEDIAN_T_HA_YR=(base_col, "median"),
        SCENARIO_RANGE_MEDIAN_T_HA_YR=("SCENARIO_RANGE_T_HA_YR", "median"),
        SCENARIO_RANGE_P95_T_HA_YR=(
            "SCENARIO_RANGE_T_HA_YR",
            lambda x: x.quantile(0.95)
        ),
        SCENARIO_RANGE_MEDIAN_PCT=("SCENARIO_RANGE_PCT_OF_BASE", "median"),
    )
)

climate_summary.to_csv(OUT_CLIMATE_SUMMARY, index=False, encoding="utf-8-sig")

zero_base = base[
    pd.to_numeric(base["TRAILING_1Y_MEAN_T_HA_YR"], errors="coerce") <= 1e-9
].copy()

zero_base.to_csv(OUT_ZERO_BASELINE, index=False, encoding="utf-8-sig")

# 10. Final QC
expected_run_ids = {
    f"{u}__{sid}"
    for u in sample["UNIT_ID"].astype(str)
    for sid in expected_sens_ids
}

actual_run_ids = set(runs["RUN_ID"].astype(str)) if len(runs) else set()
missing_run_ids = expected_run_ids - actual_run_ids

all_pairs_covered = (
    sample["CLIMATE_PAIR_ID"].nunique()
    == sample_frame["CLIMATE_PAIR_ID"].nunique()
)

finite_sensitivity = bool(
    len(runs)
    and np.isfinite(
        pd.to_numeric(runs["TRAILING_1Y_MEAN_T_HA_YR"], errors="coerce")
    ).all()
    and (
        pd.to_numeric(runs["TRAILING_1Y_MEAN_T_HA_YR"], errors="coerce") >= 0
    ).all()
)

if (
    len(missing_run_ids) == 0
    and len(failures) == 0
    and all_pairs_covered
    and finite_sensitivity
):
    status = "PASS"
    next_gate = (
        "40D APSIM-OilPalm representative process/scenario benchmark. "
        "PALMSIM baseline and representative sensitivity are frozen."
    )
else:
    status = "CHECK_PARTIAL_SENSITIVITY"
    next_gate = (
        "Rerun this same 40C04B+40C05 script; "
        "checkpoint resumes missing sensitivity runs."
    )

baseline_metric = pd.to_numeric(
    base["TRAILING_1Y_MEAN_T_HA_YR"],
    errors="coerce"
)

range_pct = pd.to_numeric(
    asu_sens["SCENARIO_RANGE_PCT_OF_BASE"],
    errors="coerce"
).dropna()

qc = {
    "gate": "40C04B_40C05_COMBINED",
    "status": status,
    "baseline": {
        "asu_count": int(len(base)),
        "min_t_fresh_ffb_ha_yr": float(baseline_metric.min()),
        "p05_t_fresh_ffb_ha_yr": float(baseline_metric.quantile(0.05)),
        "median_t_fresh_ffb_ha_yr": float(baseline_metric.median()),
        "p95_t_fresh_ffb_ha_yr": float(baseline_metric.quantile(0.95)),
        "max_t_fresh_ffb_ha_yr": float(baseline_metric.max()),
        "zero_or_near_zero_asus": int(len(zero_base)),
    },
    "representative_sensitivity_design": {
        "sample_asus": int(len(sample)),
        "max_asus_per_climate_pair": MAX_PER_CLIMATE_PAIR,
        "climate_pairs_covered": int(sample["CLIMATE_PAIR_ID"].nunique()),
        "features_used": feature_cols,
        "selection_method": (
            "Within each climate pair, deterministic maximin sampling "
            "in standardized age + baseline potential"
            + (" + condition space." if condition_col else " space.")
        ),
        "scenario_ids": expected_sens_ids,
        "planned_runs": int(planned_runs),
        "completed_runs": int(len(actual_run_ids & expected_run_ids)),
        "missing_runs": int(len(missing_run_ids)),
    },
    "sensitivity": {
        "representative_asu_count": int(len(asu_sens)),
        "scenario_range_pct_median":
            None if len(range_pct) == 0 else float(range_pct.median()),
        "scenario_range_pct_p95":
            None if len(range_pct) == 0 else float(range_pct.quantile(0.95)),
        "interpretation": (
            "Scenario spread quantifies PALMSIM structural/scenario sensitivity "
            "under assumed density and soil-depth settings; it is not field "
            "validation and not full empirical uncertainty."
        ),
    },
    "scientific_guardrails": [
        "PALMSIM P00 is the modelled productivity-potential backbone.",
        "No actual FFB validation or accuracy claim.",
        "Representative P01-P04 sample covers all climate pairs.",
        "Sensitivity is not extrapolated as measured field uncertainty.",
        "Age-derived planting year remains a proxy.",
        "Density and soil depth remain scenario assumptions.",
        "SoilGrids sand/silt/clay remain contextual evidence.",
        "Zero baseline potential is flagged for review, not automatically treated as an error.",
    ],
    "outputs": {
        "representative_sample_csv": str(OUT_SAMPLE),
        "sensitivity_runs_csv": str(OUT_RUNS),
        "representative_asu_sensitivity_csv": str(OUT_ASU_SENS),
        "scenario_summary_csv": str(OUT_SCEN_SUMMARY),
        "climate_pair_summary_csv": str(OUT_CLIMATE_SUMMARY),
        "zero_baseline_asus_csv": str(OUT_ZERO_BASELINE),
    },
    "next_gate": next_gate,
}

OUT_QC.write_text(json.dumps(qc, indent=2), encoding="utf-8")

print("\n====================================================")
print("40C04B + 40C05 FINISHED")
print("====================================================")
print("Status                    :", status)
print("Baseline ASUs             :", len(base))
print("Representative ASUs       :", len(sample))
print("Climate pairs covered     :", sample["CLIMATE_PAIR_ID"].nunique())
print("Sensitivity planned runs  :", planned_runs)
print("Sensitivity completed     :", len(actual_run_ids & expected_run_ids))
print("Missing sensitivity runs  :", len(missing_run_ids))
print("Failures                  :", len(failures))
print("Zero/near-zero baseline   :", len(zero_base))

if len(range_pct):
    print("Median scenario range     :", float(range_pct.median()), "% of baseline")
    print("P95 scenario range        :", float(range_pct.quantile(0.95)), "% of baseline")

print("\nScenario response summary:")
print(scenario_summary.to_string(index=False))

print("\nOutputs:")
print("  Sample          :", OUT_SAMPLE)
print("  Sensitivity runs:", OUT_RUNS)
print("  ASU sensitivity :", OUT_ASU_SENS)
print("  Scenario summary:", OUT_SCEN_SUMMARY)
print("  Climate summary :", OUT_CLIMATE_SUMMARY)
print("  Zero baseline   :", OUT_ZERO_BASELINE)
print("  QC JSON         :", OUT_QC)

print("\nNext:", next_gate)
print("====================================================")
