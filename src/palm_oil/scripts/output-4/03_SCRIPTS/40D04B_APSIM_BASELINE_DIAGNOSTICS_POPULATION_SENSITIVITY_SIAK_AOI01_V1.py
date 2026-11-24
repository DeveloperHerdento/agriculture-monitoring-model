# ============================================================
# OUTPUT 4 / 40D04B
# APSIM OILPALM — BASELINE DIAGNOSTICS + POPULATION SENSITIVITY
# SIAK_AOI01
#
# Purpose:
# 1) Use the canonical 40D04A-V2 baseline (48 representative ASUs).
# 2) Run two one-at-a-time population scenarios:
#       A130_POP_LOW  = 130 palms/ha
#       A150_POP_HIGH = 150 palms/ha
#    Baseline remains A143_BASE = 143 palms/ha.
# 3) Keep weather, age proxy, cultivar, soil and all other management
#    identical to the corrected V2 benchmark.
# 4) Read SQLite .db as canonical numerical output.
# 5) Quantify APSIM population sensitivity without claiming local
#    calibration or empirical uncertainty.
#
# Soil sensitivity is intentionally NOT run here because the available
# SoilGrids texture data do not uniquely define APSIM LL15/DUL/SAT/KS/
# OilPalmSoil KL/XF profiles. Those are kept as reference assumptions.
# ============================================================

from pathlib import Path
import json
import shutil
import sqlite3
import subprocess
import time
import traceback

import numpy as np
import pandas as pd

# ------------------------------------------------------------
# PATHS / SETTINGS
# ------------------------------------------------------------

WORKDIR = Path(
    r"C:\Users\user\Documents\KERJA\SPATIAL DATA ANALYST INTERN\04_YIELD"
)

APSIM_ROOT = Path(
    r"C:\Users\user\AppData\Local\Programs\APSIM2026.8.8099.0"
)

MODELS_EXE = APSIM_ROOT / "bin" / "Models.exe"

BASELINE_CSV = WORKDIR / (
    "40D04A_V2_APSIM_REPRESENTATIVE_BENCHMARK_RESULTS_SIAK_AOI01.csv"
)

RUN_ROOT = WORKDIR / (
    "40D04B_APSIM_POPULATION_SENSITIVITY_RUNS_SIAK_AOI01_V1"
)

CHECKPOINT_CSV = WORKDIR / (
    "40D04B_APSIM_POPULATION_SENSITIVITY_CHECKPOINT_SIAK_AOI01_V1.csv"
)

RESULTS_CSV = WORKDIR / (
    "40D04B_APSIM_POPULATION_SENSITIVITY_RESULTS_SIAK_AOI01_V1.csv"
)

SUMMARY_CSV = WORKDIR / (
    "40D04B_APSIM_POPULATION_SENSITIVITY_SUMMARY_SIAK_AOI01_V1.csv"
)

PAIR_SUMMARY_CSV = WORKDIR / (
    "40D04B_APSIM_CLIMATE_PAIR_DIAGNOSTIC_SUMMARY_SIAK_AOI01_V1.csv"
)

AGE_SUMMARY_CSV = WORKDIR / (
    "40D04B_APSIM_AGE_DIAGNOSTIC_SUMMARY_SIAK_AOI01_V1.csv"
)

QC_JSON = WORKDIR / (
    "40D04B_APSIM_POPULATION_SENSITIVITY_QC_SIAK_AOI01_V1.json"
)

FAIL_CSV = WORKDIR / (
    "40D04B_APSIM_POPULATION_SENSITIVITY_FAILURES_SIAK_AOI01_V1.csv"
)

SCENARIOS = {
    "A130_POP_LOW": 130,
    "A150_POP_HIGH": 150,
}

BASE_POP = 143
MAX_AGE_MATCH_DIFF_YR = 0.05

# Percent-change summaries exclude tiny baselines because otherwise
# ratios become numerically explosive and hard to interpret.
PCT_BASELINE_THRESHOLD = 1.0

# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------

def walk(node, path=""):
    if isinstance(node, dict):
        name = str(node.get("Name", ""))
        p = f"{path}/{name}" if name else path
        yield p, node
        for child in node.get("Children", []) or []:
            yield from walk(child, p)
    elif isinstance(node, list):
        for child in node:
            yield from walk(child, path)


def find_node(root, type_contains=None, name=None):
    for path, node in walk(root):
        model_type = str(node.get("$type", ""))
        if type_contains and type_contains.lower() not in model_type.lower():
            continue
        if name and str(node.get("Name", "")).lower() != name.lower():
            continue
        return path, node
    return None, None


def set_manager_parameter(manager, key, value):
    for p in manager.get("Parameters", []) or []:
        if p.get("Key") == key:
            p["Value"] = str(value)
            return
    raise KeyError(f"Manager parameter not found: {key}")


def run_apsim(apsimx_path, cwd):
    t0 = time.perf_counter()

    cp = subprocess.run(
        [
            str(MODELS_EXE),
            str(apsimx_path),
            "--single-threaded",
        ],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=1800,
    )

    return {
        "returncode": int(cp.returncode),
        "elapsed_sec": float(time.perf_counter() - t0),
        "stdout_tail": (cp.stdout or "").strip()[-2000:],
        "stderr_tail": (cp.stderr or "").strip()[-2000:],
    }


def read_age_matched_yield(db_path, age_proxy):
    con = sqlite3.connect(db_path)

    try:
        query = """
        SELECT
            "Clock.Today.Year",
            "OilPalm.Age",
            "OilPalm.LAI",
            "AnnualRain",
            "Calculations.Script.AnnualYield",
            "Calculations.Script.AnnualBunches",
            "Calculations.Script.AnnualBunchSize",
            "AnnualBunchNPP"
        FROM "AnnualOutput"
        ORDER BY "Clock.Today"
        """
        df = pd.read_sql_query(query, con)
    finally:
        con.close()

    ycol = "Calculations.Script.AnnualYield"
    agecol = "OilPalm.Age"

    df[ycol] = pd.to_numeric(df[ycol], errors="coerce")
    df[agecol] = pd.to_numeric(df[agecol], errors="coerce")

    valid = df.loc[
        df[ycol].notna() & df[agecol].notna()
    ].copy()

    if valid.empty:
        raise ValueError("No finite annual yield/age rows.")

    valid["AGE_DIFF"] = (
        valid[agecol] - float(age_proxy)
    ).abs()

    matched = valid.sort_values(
        ["AGE_DIFF", "Clock.Today.Year"]
    ).iloc[0]

    return {
        "MODEL_AGE_YR": float(matched[agecol]),
        "AGE_MATCH_ABS_DIFF_YR": float(matched["AGE_DIFF"]),
        "CALENDAR_YEAR": int(matched["Clock.Today.Year"]),
        "YIELD_T_FFB_HA_YR": float(matched[ycol]),
        "LAI": float(matched["OilPalm.LAI"]),
        "ANNUAL_RAIN_MM": (
            float(matched["AnnualRain"])
            if pd.notna(matched["AnnualRain"])
            else None
        ),
        "ANNUAL_BUNCHES": float(
            matched["Calculations.Script.AnnualBunches"]
        ),
        "ANNUAL_BUNCH_SIZE": float(
            matched["Calculations.Script.AnnualBunchSize"]
        ),
        "ANNUAL_BUNCH_NPP": float(matched["AnnualBunchNPP"]),
    }


def safe_name(text):
    return (
        str(text)
        .replace(",", "_")
        .replace("+", "P")
        .replace("-", "M")
        .replace(" ", "_")
    )


# ------------------------------------------------------------
# PREFLIGHT
# ------------------------------------------------------------

print("====================================================")
print("40D04B — APSIM BASELINE DIAGNOSTICS + POP SENSITIVITY")
print("====================================================")
print("Baseline :", BASELINE_CSV)
print("Run root :", RUN_ROOT)

for p in [MODELS_EXE, BASELINE_CSV]:
    if not p.exists():
        raise FileNotFoundError(p)

baseline = pd.read_csv(BASELINE_CSV)

if len(baseline) != 48:
    raise ValueError(f"Expected 48 baseline ASUs; found {len(baseline)}.")

if baseline["UNIT_ID"].nunique() != 48:
    raise ValueError("Baseline UNIT_ID is not unique.")

if not (baseline["STATUS"] == "PASS").all():
    raise ValueError("Not all 40D04A-V2 baseline rows are PASS.")

required_cols = [
    "UNIT_ID",
    "AGE_PROXY_YR",
    "CLIMATE_PAIR_ID",
    "APSIMX_PATH",
    "age_matched_annual_yield_t_ha_yr",
]

missing_cols = [c for c in required_cols if c not in baseline.columns]
if missing_cols:
    raise ValueError(f"Missing baseline columns: {missing_cols}")

RUN_ROOT.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------
# BASELINE DIAGNOSTICS
# ------------------------------------------------------------

base_diag = baseline[
    [
        "UNIT_ID",
        "AGE_PROXY_YR",
        "CLIMATE_PAIR_ID",
        "age_matched_annual_yield_t_ha_yr",
    ]
].copy()

base_diag = base_diag.rename(
    columns={
        "age_matched_annual_yield_t_ha_yr":
            "BASE_YIELD_T_FFB_HA_YR"
    }
)

# Age groups are descriptive only, not agronomic class claims.
base_diag["AGE_GROUP"] = pd.cut(
    base_diag["AGE_PROXY_YR"],
    bins=[-np.inf, 3, 7, 12, 18, np.inf],
    labels=[
        "AGE_0_3",
        "AGE_4_7",
        "AGE_8_12",
        "AGE_13_18",
        "AGE_19_PLUS",
    ],
)

age_summary = (
    base_diag.groupby("AGE_GROUP", observed=False)
    .agg(
        N_ASU=("UNIT_ID", "count"),
        AGE_MIN=("AGE_PROXY_YR", "min"),
        AGE_MEDIAN=("AGE_PROXY_YR", "median"),
        AGE_MAX=("AGE_PROXY_YR", "max"),
        YIELD_MIN=("BASE_YIELD_T_FFB_HA_YR", "min"),
        YIELD_MEDIAN=("BASE_YIELD_T_FFB_HA_YR", "median"),
        YIELD_MEAN=("BASE_YIELD_T_FFB_HA_YR", "mean"),
        YIELD_MAX=("BASE_YIELD_T_FFB_HA_YR", "max"),
    )
    .reset_index()
)

age_summary.to_csv(AGE_SUMMARY_CSV, index=False)

pair_summary = (
    base_diag.groupby("CLIMATE_PAIR_ID")
    .agg(
        N_ASU=("UNIT_ID", "count"),
        AGE_MEDIAN=("AGE_PROXY_YR", "median"),
        YIELD_MIN=("BASE_YIELD_T_FFB_HA_YR", "min"),
        YIELD_MEDIAN=("BASE_YIELD_T_FFB_HA_YR", "median"),
        YIELD_MEAN=("BASE_YIELD_T_FFB_HA_YR", "mean"),
        YIELD_MAX=("BASE_YIELD_T_FFB_HA_YR", "max"),
    )
    .reset_index()
)

pair_summary.to_csv(PAIR_SUMMARY_CSV, index=False)

# ------------------------------------------------------------
# RESUME
# ------------------------------------------------------------

if CHECKPOINT_CSV.exists():
    checkpoint = pd.read_csv(CHECKPOINT_CSV)
    result_records = checkpoint.to_dict("records")

    completed = set(
        zip(
            checkpoint.loc[
                checkpoint["STATUS"] == "PASS",
                "UNIT_ID",
            ].astype(str),
            checkpoint.loc[
                checkpoint["STATUS"] == "PASS",
                "SCENARIO",
            ].astype(str),
        )
    )

    print("\nCheckpoint found.")
    print("Already PASS:", len(completed))
else:
    result_records = []
    completed = set()

fail_records = []

# ------------------------------------------------------------
# EXECUTE 96 SENSITIVITY RUNS
# ------------------------------------------------------------

planned = len(baseline) * len(SCENARIOS)
counter = 0
t_all = time.perf_counter()

for row in baseline.itertuples(index=False):

    unit_id = str(row.UNIT_ID)
    age_proxy = float(row.AGE_PROXY_YR)
    source_apsimx = Path(str(row.APSIMX_PATH))

    if not source_apsimx.exists():
        raise FileNotFoundError(
            f"Corrected baseline APSIMX missing: {source_apsimx}"
        )

    for scenario, population in SCENARIOS.items():

        counter += 1
        key = (unit_id, scenario)

        if key in completed:
            print(
                f"[{counter:03d}/{planned}] SKIP PASS | "
                f"{scenario} | {unit_id}"
            )
            continue

        print(
            f"\n[{counter:03d}/{planned}] RUN | "
            f"{scenario} ({population}/ha) | {unit_id}"
        )

        try:
            with open(
                source_apsimx,
                "r",
                encoding="utf-8-sig",
            ) as f:
                sim = json.load(f)

            _, manager = find_node(
                sim,
                "Models.Manager",
                "Palm Management",
            )

            if manager is None:
                raise RuntimeError("Palm Management node not found.")

            # Safety: corrected baseline copy must NOT contain active EndCrop.
            active_endcrop = [
                line
                for line in manager.get("CodeArray", []) or []
                if (
                    "oilpalm.endcrop();"
                    in line.replace(" ", "").lower()
                    and not line.lstrip().startswith("//")
                )
            ]

            if active_endcrop:
                raise RuntimeError(
                    "Source corrected APSIMX contains active EndCrop."
                )

            set_manager_parameter(
                manager,
                "population",
                population,
            )

            run_dir = (
                RUN_ROOT
                / scenario
                / safe_name(unit_id)
            )

            if run_dir.exists():
                shutil.rmtree(run_dir)

            run_dir.mkdir(parents=True, exist_ok=True)

            apsimx_out = run_dir / (
                f"{safe_name(unit_id)}_{scenario}.apsimx"
            )

            with open(
                apsimx_out,
                "w",
                encoding="utf-8",
            ) as f:
                json.dump(sim, f, indent=2)

            run_meta = run_apsim(
                apsimx_out,
                run_dir,
            )

            if run_meta["returncode"] != 0:
                raise RuntimeError(
                    f"APSIM RC={run_meta['returncode']}\n"
                    f"{run_meta['stderr_tail']}"
                )

            db_path = apsimx_out.with_suffix(".db")

            if not db_path.exists():
                raise FileNotFoundError(db_path)

            output = read_age_matched_yield(
                db_path,
                age_proxy,
            )

            if (
                output["AGE_MATCH_ABS_DIFF_YR"]
                > MAX_AGE_MATCH_DIFF_YR
            ):
                raise ValueError(
                    "Age-match difference too large: "
                    f"{output['AGE_MATCH_ABS_DIFF_YR']:.6f}"
                )

            base_yield = float(
                row.age_matched_annual_yield_t_ha_yr
            )

            delta = (
                output["YIELD_T_FFB_HA_YR"]
                - base_yield
            )

            delta_pct = (
                100.0 * delta / base_yield
                if base_yield > PCT_BASELINE_THRESHOLD
                else np.nan
            )

            record = {
                "UNIT_ID": unit_id,
                "STATUS": "PASS",
                "SCENARIO": scenario,
                "POPULATION_PALM_HA": population,
                "BASE_POPULATION_PALM_HA": BASE_POP,
                "AGE_PROXY_YR": age_proxy,
                "CLIMATE_PAIR_ID": str(row.CLIMATE_PAIR_ID),
                "BASE_YIELD_T_FFB_HA_YR": base_yield,
                **output,
                "DELTA_T_FFB_HA_YR": float(delta),
                "DELTA_PCT_IF_BASE_GT_1":
                    float(delta_pct)
                    if np.isfinite(delta_pct)
                    else np.nan,
                "APSIM_ELAPSED_SEC":
                    run_meta["elapsed_sec"],
                "DB_PATH":
                    str(db_path),
                "APSIMX_PATH":
                    str(apsimx_out),
            }

            result_records = [
                x for x in result_records
                if not (
                    str(x.get("UNIT_ID")) == unit_id
                    and str(x.get("SCENARIO")) == scenario
                )
            ]

            result_records.append(record)

            pd.DataFrame(result_records).to_csv(
                CHECKPOINT_CSV,
                index=False,
            )

            completed.add(key)

            print(
                "  PASS | "
                f"yield={output['YIELD_T_FFB_HA_YR']:.4f} | "
                f"delta={delta:+.4f} | "
                f"{run_meta['elapsed_sec']:.1f}s"
            )

        except Exception as exc:
            fail_records.append({
                "UNIT_ID": unit_id,
                "SCENARIO": scenario,
                "STATUS": "FAIL",
                "ERROR": repr(exc),
                "TRACEBACK": traceback.format_exc(),
            })

            print("  FAIL:", repr(exc))

elapsed = time.perf_counter() - t_all

# ------------------------------------------------------------
# FINAL TABLES
# ------------------------------------------------------------

results = pd.DataFrame(result_records)

if not results.empty:
    results = (
        results
        .drop_duplicates(
            subset=["UNIT_ID", "SCENARIO"],
            keep="last",
        )
        .sort_values(["SCENARIO", "UNIT_ID"])
        .reset_index(drop=True)
    )

    results.to_csv(
        RESULTS_CSV,
        index=False,
    )

if fail_records:
    pd.DataFrame(fail_records).to_csv(
        FAIL_CSV,
        index=False,
    )
elif FAIL_CSV.exists():
    FAIL_CSV.unlink()

pass_df = (
    results.loc[results["STATUS"] == "PASS"].copy()
    if not results.empty
    else pd.DataFrame()
)

summary_rows = []

for scenario, population in SCENARIOS.items():

    s = pass_df.loc[
        pass_df["SCENARIO"] == scenario
    ].copy()

    if s.empty:
        continue

    pct = pd.to_numeric(
        s["DELTA_PCT_IF_BASE_GT_1"],
        errors="coerce",
    )

    delta = pd.to_numeric(
        s["DELTA_T_FFB_HA_YR"],
        errors="coerce",
    )

    y = pd.to_numeric(
        s["YIELD_T_FFB_HA_YR"],
        errors="coerce",
    )

    summary_rows.append({
        "SCENARIO": scenario,
        "POPULATION_PALM_HA": population,
        "N_ASU": len(s),
        "YIELD_MIN_T_HA_YR": float(y.min()),
        "YIELD_MEDIAN_T_HA_YR": float(y.median()),
        "YIELD_MEAN_T_HA_YR": float(y.mean()),
        "YIELD_MAX_T_HA_YR": float(y.max()),
        "DELTA_MEAN_T_HA_YR": float(delta.mean()),
        "DELTA_MEDIAN_T_HA_YR": float(delta.median()),
        "DELTA_P05_T_HA_YR": float(delta.quantile(0.05)),
        "DELTA_P95_T_HA_YR": float(delta.quantile(0.95)),
        "DELTA_PCT_MEDIAN_BASE_GT_1": (
            float(pct.median())
            if pct.notna().any()
            else np.nan
        ),
        "DELTA_POSITIVE_COUNT": int((delta > 0).sum()),
        "DELTA_NEGATIVE_COUNT": int((delta < 0).sum()),
        "DELTA_ZERO_COUNT": int((delta == 0).sum()),
    })

summary = pd.DataFrame(summary_rows)

if not summary.empty:
    summary.to_csv(
        SUMMARY_CSV,
        index=False,
    )

# Per-ASU total population-response range, including baseline.
if len(pass_df) == planned:

    pivot = pass_df.pivot(
        index="UNIT_ID",
        columns="SCENARIO",
        values="YIELD_T_FFB_HA_YR",
    )

    base_series = baseline.set_index(
        "UNIT_ID"
    )["age_matched_annual_yield_t_ha_yr"]

    joined = pivot.join(
        base_series.rename("A143_BASE")
    )

    vals = joined[
        ["A130_POP_LOW", "A143_BASE", "A150_POP_HIGH"]
    ]

    joined["POP_RESPONSE_RANGE_T_HA_YR"] = (
        vals.max(axis=1) - vals.min(axis=1)
    )

    joined["POP_RESPONSE_RANGE_PCT_OF_BASE"] = (
        100.0
        * joined["POP_RESPONSE_RANGE_T_HA_YR"]
        / joined["A143_BASE"]
    ).where(joined["A143_BASE"] > PCT_BASELINE_THRESHOLD)

    response_range_median = float(
        joined["POP_RESPONSE_RANGE_T_HA_YR"].median()
    )

    response_range_p95 = float(
        joined["POP_RESPONSE_RANGE_T_HA_YR"].quantile(0.95)
    )

    pct_range = joined[
        "POP_RESPONSE_RANGE_PCT_OF_BASE"
    ].dropna()

    response_range_pct_median = (
        float(pct_range.median())
        if len(pct_range)
        else None
    )

else:
    response_range_median = None
    response_range_p95 = None
    response_range_pct_median = None

# ------------------------------------------------------------
# QC
# ------------------------------------------------------------

checks = {
    "baseline_48":
        len(baseline) == 48,

    "planned_sensitivity_runs_96":
        planned == 96,

    "completed_sensitivity_runs_96":
        len(pass_df) == 96,

    "unique_asu_scenario_96":
        (
            pass_df[
                ["UNIT_ID", "SCENARIO"]
            ].drop_duplicates().shape[0] == 96
            if not pass_df.empty
            else False
        ),

    "all_48_asus_each_scenario":
        (
            all(
                len(
                    pass_df.loc[
                        pass_df["SCENARIO"] == scenario
                    ]
                ) == 48
                for scenario in SCENARIOS
            )
            if not pass_df.empty
            else False
        ),

    "climate_pairs_12":
        (
            pass_df["CLIMATE_PAIR_ID"].nunique() == 12
            if not pass_df.empty
            else False
        ),

    "all_yields_finite":
        (
            np.isfinite(
                pd.to_numeric(
                    pass_df["YIELD_T_FFB_HA_YR"],
                    errors="coerce",
                )
            ).all()
            if not pass_df.empty
            else False
        ),

    "all_age_matches_within_tolerance":
        (
            (
                pass_df["AGE_MATCH_ABS_DIFF_YR"]
                <= MAX_AGE_MATCH_DIFF_YR
            ).all()
            if not pass_df.empty
            else False
        ),

    "failures_zero":
        len(fail_records) == 0,
}

status = (
    "PASS"
    if all(checks.values())
    else "REVIEW"
)

qc = {
    "gate":
        "40D04B_APSIM_BASELINE_DIAGNOSTICS_POPULATION_SENSITIVITY",

    "status":
        status,

    "baseline_population_palm_ha":
        BASE_POP,

    "sensitivity_scenarios":
        SCENARIOS,

    "planned_sensitivity_runs":
        planned,

    "completed_sensitivity_runs":
        int(len(pass_df)),

    "failures":
        int(len(fail_records)),

    "canonical_output":
        "SQLite AnnualOutput / Calculations.Script.AnnualYield",

    "canonical_unit":
        "t fresh FFB/ha/year",

    "soil_sensitivity":
        "NOT_RUN",

    "soil_sensitivity_reason":
        (
            "SoilGrids texture alone does not uniquely specify APSIM "
            "hydraulic/crop-soil arrays (LL15, DUL, SAT, KS, LL, KL, XF). "
            "Reference soil is retained rather than creating unsupported "
            "local hydraulic parameters."
        ),

    "population_response_range_median_t_ha_yr":
        response_range_median,

    "population_response_range_p95_t_ha_yr":
        response_range_p95,

    "population_response_range_pct_of_base_median_base_gt_1":
        response_range_pct_median,

    "checks":
        {k: bool(v) for k, v in checks.items()},

    "elapsed_total_sec":
        float(elapsed),

    "interpretation":
        (
            "One-at-a-time APSIM population sensitivity around the 143 palm/ha "
            "benchmark. This quantifies model response to an assumed management "
            "parameter; it is not empirical uncertainty and is not local yield "
            "validation."
        ),
}

QC_JSON.write_text(
    json.dumps(qc, indent=2),
    encoding="utf-8",
)

# ------------------------------------------------------------
# PRINT
# ------------------------------------------------------------

print("\n====================================================")
print("40D04B FINISHED")
print("====================================================")
print("Status                    :", status)
print("Baseline ASUs             :", len(baseline))
print("Sensitivity planned runs  :", planned)
print("Sensitivity completed     :", len(pass_df))
print("Failures                  :", len(fail_records))
print("Elapsed total             :", round(elapsed / 60, 2), "min")

print("\nScenario summary:")
if not summary.empty:
    print(summary.to_string(index=False))

print("\nPopulation response range:")
print(
    "Median absolute range     :",
    response_range_median,
    "t FFB/ha/yr",
)
print(
    "P95 absolute range        :",
    response_range_p95,
    "t FFB/ha/yr",
)
print(
    "Median % of baseline (>1) :",
    response_range_pct_median,
    "%",
)

print("\nQC:")
for key, value in checks.items():
    print(f"{key:45s}: {value}")

print("\nResults      :", RESULTS_CSV)
print("Summary      :", SUMMARY_CSV)
print("Age diag     :", AGE_SUMMARY_CSV)
print("Climate diag :", PAIR_SUMMARY_CSV)
print("QC           :", QC_JSON)

if fail_records:
    print("Failures     :", FAIL_CSV)

if status == "PASS":
    print("Next         : 40D05 APSIM benchmark QC/freeze.")
else:
    print("Next         : Review failures/QC before 40D05.")

print("====================================================")
