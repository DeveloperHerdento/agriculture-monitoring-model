# ============================================================
# OUTPUT 4 / 40C04A V2
# PALMSIM P00 BASELINE BATCH — PARALLEL / RESUMABLE
# SIAK_AOI01
#
# RUN FROM JUPYTER VIA subprocess/Popen.
#
# KEY CHANGE VS V1:
# - Uses up to 3 parallel worker processes.
# - Reuses the SAME checkpoint file from V1, so completed ASUs
#   are skipped automatically.
# - Each worker loads only the tiny native-cell climate tables.
# ============================================================

from pathlib import Path
import os
import sys
import json
import time
import traceback
import warnings
from concurrent.futures import ProcessPoolExecutor, as_completed

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

OUT_RESULTS = WORKDIR / "40C04A_PALMSIM_P00_BASELINE_RESULTS_SIAK_AOI01_V2.csv"
OUT_EXCLUSIONS = WORKDIR / "40C04A_PALMSIM_P00_BASELINE_EXCLUSIONS_SIAK_AOI01_V2.csv"
OUT_FAILURES = WORKDIR / "40C04A_PALMSIM_P00_BASELINE_FAILURES_SIAK_AOI01_V2.csv"
OUT_QC = WORKDIR / "40C04A_PALMSIM_P00_BASELINE_QC_SIAK_AOI01_V2.json"

# Reuse V1 checkpoint so interrupted serial work is not lost.
CHECKPOINT = WORKDIR / "40C04A_PALMSIM_P00_BASELINE_CHECKPOINT_SIAK_AOI01_V1.csv"

REFERENCE_YEAR = 2025
CLIMATE_START = pd.Timestamp("2001-01-01")
CLIMATE_END = pd.Timestamp("2025-12-31")

BASE_DENSITY = 143.0
BASE_SOIL_DEPTH = 1.0

# Conservative laptop default.
WORKERS = min(3, max(1, (os.cpu_count() or 2) - 1))
SAVE_EVERY = 20

# Worker globals
PalmField = None
CHIRPS_BY_CELL = {}
ERA_BY_CELL = {}

def worker_init(reg_path, chirps_path, era_path):
    global PalmField, CHIRPS_BY_CELL, ERA_BY_CELL

    warnings.filterwarnings(
        "ignore",
        message=r".*errors='ignore' is deprecated.*",
        category=FutureWarning
    )

    registration = json.loads(Path(reg_path).read_text(encoding="utf-8"))
    working_root = Path(registration["working_root"])

    roots = list(working_root.rglob("palmsim-master"))
    if not roots:
        raise FileNotFoundError("Could not locate palmsim-master.")

    palmsim_master = roots[0]
    for pth in [str(palmsim_master / "PalmSim"), str(palmsim_master)]:
        if pth not in sys.path:
            sys.path.insert(0, pth)

    from palmsim import PalmField as _PalmField
    PalmField = _PalmField

    chirps = pd.read_csv(
        chirps_path,
        usecols=["DATE", "CHIRPS_CELL_ID", "RAIN_MM_DAY"]
    )
    era = pd.read_csv(
        era_path,
        usecols=["DATE", "ERA5L_CELL_ID", "RAD_MJ_M2_DAY"]
    )

    chirps["DATE"] = pd.to_datetime(chirps["DATE"]).dt.normalize()
    era["DATE"] = pd.to_datetime(era["DATE"]).dt.normalize()
    chirps["CHIRPS_CELL_ID"] = chirps["CHIRPS_CELL_ID"].astype(str)
    era["ERA5L_CELL_ID"] = era["ERA5L_CELL_ID"].astype(str)

    CHIRPS_BY_CELL = {
        cid: g[["DATE", "RAIN_MM_DAY"]].sort_values("DATE").set_index("DATE")
        for cid, g in chirps.groupby("CHIRPS_CELL_ID", sort=False)
    }
    ERA_BY_CELL = {
        cid: g[["DATE", "RAD_MJ_M2_DAY"]].sort_values("DATE").set_index("DATE")
        for cid, g in era.groupby("ERA5L_CELL_ID", sort=False)
    }

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

def run_one(task):
    unit_id = task["UNIT_ID"]

    try:
        model_age = int(task["MODEL_AGE_YR_ROUNDED"])
        yop = int(task["YEAR_OF_PLANTING_PROXY"])
        duration = model_age * 365
        start = pd.Timestamp(task["SIMULATION_START"])
        end = pd.Timestamp(task["SIMULATION_END"])

        c_id = str(task["CHIRPS_CELL_ID"])
        e_id = str(task["ERA5L_CELL_ID"])

        c = CHIRPS_BY_CELL[c_id].loc[start:end]
        e = ERA_BY_CELL[e_id].loc[start:end]
        w = c.join(e, how="inner")

        if len(w) != duration:
            raise RuntimeError(f"weather rows {len(w)} != duration {duration}")
        if w[["RAIN_MM_DAY", "RAD_MJ_M2_DAY"]].isna().any().any():
            raise RuntimeError("missing climate forcing")
        if not w.index.equals(pd.date_range(start, end, freq="D")):
            raise RuntimeError("non-contiguous daily forcing calendar")

        p = PalmField(year_of_planting=yop)
        p.latitude = float(task["ASU_LATITUDE"])
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

        return {
            "ok": True,
            "record": {
                "UNIT_ID": unit_id,
                "SCENARIO_ID": "P00_BASE",
                "AGE_PROXY_YR": float(task["AGE_PROXY_YR"]),
                "MODEL_AGE_YR_ROUNDED": model_age,
                "YEAR_OF_PLANTING_PROXY": yop,
                "ASU_LATITUDE": float(task["ASU_LATITUDE"]),
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
            }
        }

    except Exception as e:
        return {
            "ok": False,
            "failure": {
                "UNIT_ID": unit_id,
                "ERROR": repr(e),
                "TRACEBACK": traceback.format_exc()[-5000:],
            }
        }

def save_checkpoint(records):
    if not records:
        return
    tmp = CHECKPOINT.with_suffix(".tmp.csv")
    pd.DataFrame(records).to_csv(tmp, index=False, encoding="utf-8-sig")
    os.replace(tmp, CHECKPOINT)

def main():
    print("====================================================", flush=True)
    print("40C04A V2 — PALMSIM P00 PARALLEL BASELINE", flush=True)
    print("====================================================", flush=True)
    print("Python :", sys.executable, flush=True)
    print("Workers:", WORKERS, flush=True)

    for p in [REG, ELIGIBLE_FILE, CHIRPS_FILE, ERA5_FILE]:
        if not p.exists():
            raise FileNotFoundError(f"Missing required input: {p}")

    asu = pd.read_csv(ELIGIBLE_FILE)
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

        audit.append({
            "UNIT_ID": str(r["UNIT_ID"]),
            "MODEL_AGE_YR_ROUNDED": model_age,
            "YEAR_OF_PLANTING_PROXY": yop,
            "SIMULATION_START": None if start is None else start.strftime("%Y-%m-%d"),
            "SIMULATION_END": None if end is None else end.strftime("%Y-%m-%d"),
            "EXCLUSION_REASON": reason,
        })

    audit = pd.DataFrame(audit)
    asu = asu.merge(audit, on="UNIT_ID", how="left", validate="one_to_one")

    batch_asu = asu[asu["EXCLUSION_REASON"].isna()].copy()
    exclusions = asu[asu["EXCLUSION_REASON"].notna()].copy()
    exclusions.to_csv(OUT_EXCLUSIONS, index=False, encoding="utf-8-sig")

    records = []
    completed = set()

    if CHECKPOINT.exists():
        old = pd.read_csv(CHECKPOINT)
        if len(old) and "UNIT_ID" in old.columns:
            records = old.to_dict("records")
            completed = set(old["UNIT_ID"].astype(str))

    todo = batch_asu[~batch_asu["UNIT_ID"].astype(str).isin(completed)].copy()

    print("Input PALMSIM ASUs :", len(asu), flush=True)
    print("Climate-compatible:", len(batch_asu), flush=True)
    print("Excluded          :", len(exclusions), flush=True)
    print("Already completed :", len(completed), flush=True)
    print("Remaining         :", len(todo), flush=True)

    failures = []
    t0 = time.time()
    newly_done = 0

    tasks = todo.to_dict("records")

    if tasks:
        with ProcessPoolExecutor(
            max_workers=WORKERS,
            initializer=worker_init,
            initargs=(str(REG), str(CHIRPS_FILE), str(ERA5_FILE)),
        ) as ex:

            futures = {ex.submit(run_one, task): task["UNIT_ID"] for task in tasks}

            for fut in as_completed(futures):
                result = fut.result()

                if result["ok"]:
                    rec = result["record"]
                    records.append(rec)
                    completed.add(str(rec["UNIT_ID"]))
                    newly_done += 1
                else:
                    failures.append(result["failure"])

                if newly_done % SAVE_EVERY == 0 or (
                    len(completed) + len(failures)
                ) >= len(batch_asu):
                    save_checkpoint(records)

                if newly_done % 10 == 0 or newly_done == len(tasks):
                    elapsed = time.time() - t0
                    done_total = len(completed)
                    print(
                        f"Progress: {done_total}/{len(batch_asu)} "
                        f"({100*done_total/len(batch_asu):.1f}%) | "
                        f"new={newly_done}/{len(tasks)} | "
                        f"failures={len(failures)} | "
                        f"elapsed={elapsed/60:.1f} min",
                        flush=True
                    )

    save_checkpoint(records)

    results = pd.DataFrame(records)
    if len(results):
        results = (
            results.drop_duplicates(subset=["UNIT_ID"], keep="last")
            .sort_values("UNIT_ID")
            .reset_index(drop=True)
        )

    results.to_csv(OUT_RESULTS, index=False, encoding="utf-8-sig")
    pd.DataFrame(
        failures,
        columns=["UNIT_ID", "ERROR", "TRACEBACK"]
    ).to_csv(OUT_FAILURES, index=False, encoding="utf-8-sig")

    expected = set(batch_asu["UNIT_ID"].astype(str))
    actual = set(results["UNIT_ID"].astype(str)) if len(results) else set()
    missing = expected - actual

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

    if not missing and not failures and finite_nonnegative:
        status = (
            "PASS"
            if len(exclusions) == 0
            else "PASS_WITH_CLIMATE_WINDOW_EXCLUSIONS"
        )
        next_gate = "40C04B sensitivity batch P01-P04."
    else:
        status = "CHECK_PARTIAL_BASELINE"
        next_gate = "Rerun this V2 script to resume missing baseline ASUs."

    qc = {
        "gate": "40C04A_V2_PARALLEL",
        "status": status,
        "workers": WORKERS,
        "input_palmsim_asus": int(len(asu)),
        "climate_compatible_asus": int(len(batch_asu)),
        "pre_run_exclusions": int(len(exclusions)),
        "completed_baseline_asus": int(len(actual)),
        "missing_baseline_asus": int(len(missing)),
        "failures_this_session": int(len(failures)),
        "baseline_median_trailing_1y_t_ha_yr":
            None if len(metric) == 0 else float(metric.median()),
        "next_gate": next_gate,
    }
    OUT_QC.write_text(json.dumps(qc, indent=2), encoding="utf-8")

    print("\n====================================================", flush=True)
    print("40C04A V2 FINISHED", flush=True)
    print("====================================================", flush=True)
    print("Status            :", status, flush=True)
    print("Completed baseline:", len(actual), "/", len(batch_asu), flush=True)
    print("Missing baseline  :", len(missing), flush=True)
    print("Failures          :", len(failures), flush=True)
    if len(metric):
        print("Median potential  :", float(metric.median()), "t/ha/yr", flush=True)
    print("Results           :", OUT_RESULTS, flush=True)
    print("QC                :", OUT_QC, flush=True)
    print("Next              :", next_gate, flush=True)
    print("====================================================", flush=True)

if __name__ == "__main__":
    main()
