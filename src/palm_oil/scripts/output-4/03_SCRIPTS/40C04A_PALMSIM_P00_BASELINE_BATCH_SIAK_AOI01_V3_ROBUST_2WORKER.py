# ============================================================
# OUTPUT 4 / 40C04A V3
# PALMSIM P00 BASELINE — ROBUST 2-WORKER CHUNK RUNNER
# SIAK_AOI01
#
# RUN FROM JUPYTER.
#
# DESIGN
# - Avoid ProcessPoolExecutor on Windows/Jupyter.
# - Main process splits remaining ASUs into 2 chunks.
# - Two independent Python worker processes run this SAME file.
# - Each worker appends one compact result per finished ASU.
# - Main process polls worker CSVs and prints LIVE progress.
# - Existing V1 checkpoint is reused; completed ASUs are not rerun.
#
# SCIENTIFIC GUARDRAILS
# - Modelled productivity potential only, not actual yield.
# - Age-derived planting year remains a proxy.
# - CHIRPS v2 Final = rainfall forcing.
# - ERA5-Land = radiation forcing.
# - No missing-weather fallback.
# - SoilGrids sand/silt/clay are not injected into PALMSIM.
# ============================================================

from pathlib import Path
import os
import sys
import json
import time
import traceback
import warnings
import argparse
import subprocess
import csv

import numpy as np
import pandas as pd

WORKDIR = Path(
    r"C:\Users\user\Documents\KERJA\SPATIAL DATA ANALYST INTERN\04_YIELD"
)

REG = WORKDIR / "40C01B_PALMSIM_SOURCE_REGISTRATION_SIAK_AOI01_V1.json"
ELIGIBLE_FILE = WORKDIR / "40C01_PALMSIM_ELIGIBLE_ASU_MANIFEST_SIAK_AOI01_V1.csv"
CHIRPS_FILE = WORKDIR / "40B04B1_CHIRPS_V2_DAILY_NATIVE_CELLS_2001_2025_SIAK_AOI01_V1.csv"
ERA5_FILE = WORKDIR / "40B04B2_ERA5LAND_DAILY_NATIVE_CELLS_2001_2025_SIAK_AOI01_V4.csv"

# Reuse work already completed by earlier baseline attempt.
OLD_CHECKPOINT = WORKDIR / "40C04A_PALMSIM_P00_BASELINE_CHECKPOINT_SIAK_AOI01_V1.csv"

RUN_DIR = WORKDIR / "40C04A_V3_WORKERS"
CHUNK_DIR = RUN_DIR / "chunks"
RESULT_DIR = RUN_DIR / "results"
LOG_DIR = RUN_DIR / "logs"

OUT_RESULTS = WORKDIR / "40C04A_PALMSIM_P00_BASELINE_RESULTS_SIAK_AOI01_V3.csv"
OUT_EXCLUSIONS = WORKDIR / "40C04A_PALMSIM_P00_BASELINE_EXCLUSIONS_SIAK_AOI01_V3.csv"
OUT_FAILURES = WORKDIR / "40C04A_PALMSIM_P00_BASELINE_FAILURES_SIAK_AOI01_V3.csv"
OUT_QC = WORKDIR / "40C04A_PALMSIM_P00_BASELINE_QC_SIAK_AOI01_V3.json"

REFERENCE_YEAR = 2025
CLIMATE_START = pd.Timestamp("2001-01-01")
CLIMATE_END = pd.Timestamp("2025-12-31")

BASE_DENSITY = 143.0
BASE_SOIL_DEPTH = 1.0

N_WORKERS = 2
POLL_SECONDS = 5

RESULT_COLUMNS = [
    "UNIT_ID",
    "SCENARIO_ID",
    "AGE_PROXY_YR",
    "MODEL_AGE_YR_ROUNDED",
    "YEAR_OF_PLANTING_PROXY",
    "ASU_LATITUDE",
    "CHIRPS_CELL_ID",
    "ERA5L_CELL_ID",
    "PALM_DENSITY_PALMS_HA",
    "SOIL_DEPTH_M",
    "SIMULATION_START",
    "SIMULATION_END",
    "DURATION_DAYS",
    "MODEL_OUTPUT_ROWS",
    "FFB_SOURCE_COLUMN",
    "FINAL_FFB_POTENTIAL_T_HA_YR",
    "TRAILING_1Y_MEAN_T_HA_YR",
    "TRAILING_1Y_MEDIAN_T_HA_YR",
    "TRAILING_3Y_MEAN_T_HA_YR",
    "RUN_STATUS",
]

FAIL_COLUMNS = ["UNIT_ID", "ERROR", "TRACEBACK"]


def load_palmsim():
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
    return PalmField


def load_climate():
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

    return chirps_by_cell, era_by_cell


def get_ffb_col(df):
    preferred = "generative_FFB_production (t/ha/yr)"
    if preferred in df.columns:
        return preferred

    candidates = [
        c for c in df.columns
        if "ffb" in str(c).lower()
        and "production" in str(c).lower()
    ]

    if not candidates:
        candidates = [
            c for c in df.columns
            if "ffb" in str(c).lower()
        ]

    return candidates[0] if candidates else None


def append_csv(path, row, columns):
    exists = path.exists()

    with open(path, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=columns)

        if not exists:
            writer.writeheader()

        writer.writerow({c: row.get(c) for c in columns})
        f.flush()


def worker_main(chunk_file, result_file, failure_file, worker_id):
    os.chdir(WORKDIR)

    warnings.filterwarnings(
        "ignore",
        message=r".*errors='ignore' is deprecated.*",
        category=FutureWarning
    )

    PalmField = load_palmsim()
    chirps_by_cell, era_by_cell = load_climate()

    tasks = pd.read_csv(chunk_file)

    print(
        f"[Worker {worker_id}] start | ASUs={len(tasks)}",
        flush=True
    )

    done = 0
    failed = 0

    for _, task in tasks.iterrows():
        unit_id = str(task["UNIT_ID"])

        try:
            model_age = int(task["MODEL_AGE_YR_ROUNDED"])
            yop = int(task["YEAR_OF_PLANTING_PROXY"])
            duration = model_age * 365

            start = pd.Timestamp(task["SIMULATION_START"])
            end = pd.Timestamp(task["SIMULATION_END"])

            c_id = str(task["CHIRPS_CELL_ID"])
            e_id = str(task["ERA5L_CELL_ID"])

            c = chirps_by_cell[c_id].loc[start:end]
            e = era_by_cell[e_id].loc[start:end]
            weather = c.join(e, how="inner")

            if len(weather) != duration:
                raise RuntimeError(
                    f"weather rows {len(weather)} != duration {duration}"
                )

            if weather[
                ["RAIN_MM_DAY", "RAD_MJ_M2_DAY"]
            ].isna().any().any():
                raise RuntimeError("missing climate forcing")

            expected = pd.date_range(start, end, freq="D")
            if not weather.index.equals(expected):
                raise RuntimeError(
                    "non-contiguous daily forcing calendar"
                )

            p = PalmField(year_of_planting=yop)
            p.latitude = float(task["ASU_LATITUDE"])

            p.weather.rainfall_series = (
                weather["RAIN_MM_DAY"].copy()
            )
            p.weather.radiation_series = (
                weather["RAD_MJ_M2_DAY"].copy()
            )

            p.planting_density = BASE_DENSITY
            p.soil.soil_depth = BASE_SOIL_DEPTH

            df = p.run(duration=duration)

            if not isinstance(df, pd.DataFrame) or len(df) == 0:
                raise RuntimeError("PALMSIM returned empty output")

            ffb_col = get_ffb_col(df)
            if ffb_col is None:
                raise RuntimeError("FFB output column not found")

            raw = pd.to_numeric(
                df[ffb_col],
                errors="coerce"
            ).dropna()

            if len(raw) == 0:
                raise RuntimeError(
                    "FFB output contains no numeric values"
                )

            # Audited PALMSIM source:
            # raw calculation is kg fresh mass/ha/yr.
            # Canonical Output-4 conversion = /1000.
            ffb = raw / 1000.0

            n1 = min(36, len(ffb))
            n3 = min(109, len(ffb))

            rec = {
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
                "FINAL_FFB_POTENTIAL_T_HA_YR":
                    float(ffb.iloc[-1]),
                "TRAILING_1Y_MEAN_T_HA_YR":
                    float(ffb.tail(n1).mean()),
                "TRAILING_1Y_MEDIAN_T_HA_YR":
                    float(ffb.tail(n1).median()),
                "TRAILING_3Y_MEAN_T_HA_YR":
                    float(ffb.tail(n3).mean()),
                "RUN_STATUS": "PASS",
            }

            append_csv(
                Path(result_file),
                rec,
                RESULT_COLUMNS
            )

            done += 1

        except Exception as e:
            fail = {
                "UNIT_ID": unit_id,
                "ERROR": repr(e),
                "TRACEBACK": traceback.format_exc()[-5000:],
            }

            append_csv(
                Path(failure_file),
                fail,
                FAIL_COLUMNS
            )

            failed += 1

        if (done + failed) % 10 == 0:
            print(
                f"[Worker {worker_id}] "
                f"processed={done + failed}/{len(tasks)} | "
                f"pass={done} | fail={failed}",
                flush=True
            )

    print(
        f"[Worker {worker_id}] FINISHED | pass={done} | fail={failed}",
        flush=True
    )


def count_data_rows(path):
    if not path.exists():
        return 0

    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            n = sum(1 for _ in f)
        return max(0, n - 1)
    except Exception:
        return 0


def main():
    os.chdir(WORKDIR)

    print("====================================================", flush=True)
    print("40C04A V3 — PALMSIM P00 ROBUST 2-WORKER BATCH", flush=True)
    print("====================================================", flush=True)
    print("Python :", sys.executable, flush=True)
    print("Workers:", N_WORKERS, flush=True)

    for p in [
        REG,
        ELIGIBLE_FILE,
        CHIRPS_FILE,
        ERA5_FILE,
    ]:
        if not p.exists():
            raise FileNotFoundError(
                f"Missing required input: {p}"
            )

    RUN_DIR.mkdir(parents=True, exist_ok=True)
    CHUNK_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Clean ONLY V3 transient worker files from a prior interrupted V3.
    # Final prior baseline checkpoint is preserved.
    for p in RESULT_DIR.glob("worker_*.csv"):
        p.unlink()
    for p in RESULT_DIR.glob("worker_*_failures.csv"):
        p.unlink()
    for p in CHUNK_DIR.glob("worker_*.csv"):
        p.unlink()

    asu = pd.read_csv(ELIGIBLE_FILE)

    asu["AGE_PROXY_YR"] = pd.to_numeric(
        asu["AGE_PROXY_YR"],
        errors="coerce"
    )
    asu["ASU_LATITUDE"] = pd.to_numeric(
        asu["ASU_LATITUDE"],
        errors="coerce"
    )
    asu["CHIRPS_CELL_ID"] = asu[
        "CHIRPS_CELL_ID"
    ].astype(str)
    asu["ERA5L_CELL_ID"] = asu[
        "ERA5L_CELL_ID"
    ].astype(str)

    # --------------------------------------------------------
    # Climate-window audit
    # --------------------------------------------------------

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
            start = pd.Timestamp(
                year=yop,
                month=1,
                day=1
            )
            duration = model_age * 365
            end = start + pd.Timedelta(
                days=duration - 1
            )

            if (
                reason is None
                and start < CLIMATE_START
            ):
                reason = (
                    "CLIMATE_WINDOW_START_BEFORE_2001"
                )

            if (
                reason is None
                and end > CLIMATE_END
            ):
                reason = (
                    "CLIMATE_WINDOW_END_AFTER_2025"
                )

        audit.append({
            "UNIT_ID": str(r["UNIT_ID"]),
            "MODEL_AGE_YR_ROUNDED": model_age,
            "YEAR_OF_PLANTING_PROXY": yop,
            "SIMULATION_START":
                None if start is None
                else start.strftime("%Y-%m-%d"),
            "SIMULATION_END":
                None if end is None
                else end.strftime("%Y-%m-%d"),
            "EXCLUSION_REASON": reason,
        })

    audit = pd.DataFrame(audit)

    asu = asu.merge(
        audit,
        on="UNIT_ID",
        how="left",
        validate="one_to_one"
    )

    batch_asu = asu[
        asu["EXCLUSION_REASON"].isna()
    ].copy()

    exclusions = asu[
        asu["EXCLUSION_REASON"].notna()
    ].copy()

    exclusions.to_csv(
        OUT_EXCLUSIONS,
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------------
    # Recover prior V1 checkpoint
    # --------------------------------------------------------

    old_records = pd.DataFrame(
        columns=RESULT_COLUMNS
    )
    completed = set()

    if OLD_CHECKPOINT.exists():
        try:
            old = pd.read_csv(OLD_CHECKPOINT)

            if (
                len(old)
                and "UNIT_ID" in old.columns
            ):
                old_records = old.copy()
                completed = set(
                    old["UNIT_ID"].astype(str)
                )
        except Exception as e:
            print(
                "Old checkpoint warning:",
                repr(e),
                flush=True
            )

    todo = batch_asu[
        ~batch_asu["UNIT_ID"]
        .astype(str)
        .isin(completed)
    ].copy()

    print(
        "\nInput PALMSIM ASUs :", len(asu),
        flush=True
    )
    print(
        "Climate-compatible:", len(batch_asu),
        flush=True
    )
    print(
        "Excluded          :", len(exclusions),
        flush=True
    )
    print(
        "Recovered old work:", len(completed),
        flush=True
    )
    print(
        "Remaining for V3  :", len(todo),
        flush=True
    )

    if len(todo) == 0:
        print(
            "No remaining ASUs. Finalizing existing checkpoint.",
            flush=True
        )
        worker_frames = []

    else:
        # ----------------------------------------------------
        # Split remaining ASUs into 2 balanced chunks
        # ----------------------------------------------------

        chunks = np.array_split(
            todo.reset_index(drop=True),
            N_WORKERS
        )

        worker_files = []
        processes = []
        log_handles = []

        script_path = Path(__file__).resolve()

        for i, chunk in enumerate(chunks, start=1):
            if len(chunk) == 0:
                continue

            chunk_file = CHUNK_DIR / f"worker_{i}_chunk.csv"
            result_file = RESULT_DIR / f"worker_{i}.csv"
            failure_file = (
                RESULT_DIR / f"worker_{i}_failures.csv"
            )
            log_file = LOG_DIR / f"worker_{i}.log"

            chunk.to_csv(
                chunk_file,
                index=False,
                encoding="utf-8-sig"
            )

            log_handle = open(
                log_file,
                "w",
                encoding="utf-8",
                buffering=1
            )
            log_handles.append(log_handle)

            cmd = [
                sys.executable,
                "-u",
                str(script_path),
                "--worker",
                "--worker-id",
                str(i),
                "--chunk-file",
                str(chunk_file),
                "--result-file",
                str(result_file),
                "--failure-file",
                str(failure_file),
            ]

            proc = subprocess.Popen(
                cmd,
                cwd=str(WORKDIR),
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                text=True,
            )

            processes.append(
                (
                    i,
                    proc,
                    result_file,
                    failure_file,
                    log_file
                )
            )

            worker_files.append(result_file)

        # ----------------------------------------------------
        # Live polling
        # ----------------------------------------------------

        t0 = time.time()
        last_report = None

        while True:
            alive = any(
                proc.poll() is None
                for _, proc, _, _, _ in processes
            )

            new_pass = sum(
                count_data_rows(rf)
                for _, _, rf, _, _ in processes
            )

            new_fail = sum(
                count_data_rows(ff)
                for _, _, _, ff, _ in processes
            )

            total_done = (
                len(completed)
                + new_pass
            )

            report = (
                total_done,
                new_fail
            )

            if report != last_report:
                elapsed = (
                    time.time() - t0
                ) / 60.0

                print(
                    f"Progress: "
                    f"{total_done}/{len(batch_asu)} "
                    f"({100*total_done/len(batch_asu):.1f}%) | "
                    f"new failures={new_fail} | "
                    f"elapsed={elapsed:.1f} min",
                    flush=True
                )

                last_report = report

            if not alive:
                break

            time.sleep(POLL_SECONDS)

        for h in log_handles:
            h.close()

        # Print worker exit codes + final log tails if any error.
        for i, proc, _, _, log_file in processes:
            code = proc.returncode
            print(
                f"Worker {i} return code: {code}",
                flush=True
            )

            if code != 0:
                try:
                    text = log_file.read_text(
                        encoding="utf-8",
                        errors="ignore"
                    )
                    print(
                        f"\n--- Worker {i} log tail ---",
                        flush=True
                    )
                    print(
                        text[-5000:],
                        flush=True
                    )
                except Exception:
                    pass

        worker_frames = []

        for _, _, result_file, _, _ in processes:
            if result_file.exists():
                worker_frames.append(
                    pd.read_csv(result_file)
                )

    # --------------------------------------------------------
    # Merge old + new results
    # --------------------------------------------------------

    frames = []

    if len(old_records):
        frames.append(old_records)

    frames.extend(
        f for f in worker_frames
        if len(f)
    )

    if frames:
        results = pd.concat(
            frames,
            ignore_index=True,
            sort=False
        )
        results = (
            results
            .drop_duplicates(
                subset=["UNIT_ID"],
                keep="last"
            )
            .sort_values("UNIT_ID")
            .reset_index(drop=True)
        )
    else:
        results = pd.DataFrame(
            columns=RESULT_COLUMNS
        )

    results.to_csv(
        OUT_RESULTS,
        index=False,
        encoding="utf-8-sig"
    )

    # Merge worker failures.
    fail_frames = []

    for p in RESULT_DIR.glob(
        "worker_*_failures.csv"
    ):
        try:
            f = pd.read_csv(p)
            if len(f):
                fail_frames.append(f)
        except Exception:
            pass

    if fail_frames:
        failures = pd.concat(
            fail_frames,
            ignore_index=True
        )
    else:
        failures = pd.DataFrame(
            columns=FAIL_COLUMNS
        )

    failures.to_csv(
        OUT_FAILURES,
        index=False,
        encoding="utf-8-sig"
    )

    expected_ids = set(
        batch_asu["UNIT_ID"].astype(str)
    )
    actual_ids = set(
        results["UNIT_ID"].astype(str)
    )

    missing_ids = (
        expected_ids - actual_ids
    )

    metric = (
        pd.to_numeric(
            results["TRAILING_1Y_MEAN_T_HA_YR"],
            errors="coerce"
        )
        if len(results)
        else pd.Series(dtype=float)
    )

    finite_nonnegative = bool(
        len(metric)
        and np.isfinite(metric).all()
        and (metric >= 0).all()
    )

    if (
        len(missing_ids) == 0
        and len(failures) == 0
        and finite_nonnegative
    ):
        status = (
            "PASS"
            if len(exclusions) == 0
            else "PASS_WITH_CLIMATE_WINDOW_EXCLUSIONS"
        )
        next_gate = (
            "40C04B run P01-P04 sensitivity batch, "
            "then 40C05 summary/QC."
        )

    else:
        status = (
            "CHECK_PARTIAL_BASELINE"
        )
        next_gate = (
            "Rerun this same V3 script. "
            "Completed baseline results are preserved."
        )

    qc = {
        "gate": "40C04A_V3",
        "status": status,
        "worker_count": N_WORKERS,
        "input_palmsim_asus": int(
            len(asu)
        ),
        "climate_compatible_asus": int(
            len(batch_asu)
        ),
        "pre_run_exclusions": int(
            len(exclusions)
        ),
        "recovered_previous_asus": int(
            len(completed)
        ),
        "completed_baseline_asus": int(
            len(actual_ids)
        ),
        "missing_baseline_asus": int(
            len(missing_ids)
        ),
        "failure_rows": int(
            len(failures)
        ),
        "baseline_median_trailing_1y_t_ha_yr":
            None if len(metric) == 0
            else float(metric.median()),
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

    OUT_QC.write_text(
        json.dumps(qc, indent=2),
        encoding="utf-8"
    )

    print("\n====================================================", flush=True)
    print("40C04A V3 FINISHED", flush=True)
    print("====================================================", flush=True)
    print("Status            :", status, flush=True)
    print(
        "Completed baseline:",
        len(actual_ids),
        "/",
        len(batch_asu),
        flush=True
    )
    print(
        "Missing baseline  :",
        len(missing_ids),
        flush=True
    )
    print(
        "Failures          :",
        len(failures),
        flush=True
    )

    if len(metric):
        print(
            "Median potential  :",
            float(metric.median()),
            "t fresh FFB/ha/yr",
            flush=True
        )

    print("Results           :", OUT_RESULTS, flush=True)
    print("QC                :", OUT_QC, flush=True)
    print("Next              :", next_gate, flush=True)
    print("====================================================", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--worker",
        action="store_true"
    )
    parser.add_argument(
        "--worker-id",
        default="0"
    )
    parser.add_argument(
        "--chunk-file"
    )
    parser.add_argument(
        "--result-file"
    )
    parser.add_argument(
        "--failure-file"
    )

    args = parser.parse_args()

    if args.worker:
        worker_main(
            args.chunk_file,
            args.result_file,
            args.failure_file,
            args.worker_id,
        )
    else:
        main()
