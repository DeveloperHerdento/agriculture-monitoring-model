# ============================================================
# OUTPUT 4 / 40D04A
# APSIM OILPALM REPRESENTATIVE BENCHMARK EXECUTION
# SIAK_AOI01
#
# Run directly in Jupyter.
#
# Design:
# - 48 representative ASUs (same representative set as PALMSIM)
# - 12 CHIRPS + ERA5-Land climate pairs
# - CHIRPS V2 rainfall
# - ERA5-Land radiation, Tmin, Tmax
# - population = 143 palm/ha
# - cultivar = official APSIM OilPalm reference ("Dami")
# - soil/management = official APSIM OilPalm reference
# - serial execution only
# - SQLite .db = canonical numerical output
#
# IMPORTANT COMPARABILITY RULE:
# APSIM annual output is sampled at the row whose OilPalm.Age is
# closest to AGE_PROXY_YR. We DO NOT automatically use the final
# calendar-year row, because the Jan-1 sowing convention makes the
# final 2025 row approximately AGE_PROXY_YR + 1.
#
# This remains a representative process/scenario benchmark,
# NOT locally validated actual FFB yield.
# ============================================================

from pathlib import Path
import json
import shutil
import subprocess
import sqlite3
import time
import traceback

import numpy as np
import pandas as pd

WORKDIR = Path(
    r"C:\Users\user\Documents\KERJA\SPATIAL DATA ANALYST INTERN\04_YIELD"
)

APSIM_ROOT = Path(
    r"C:\Users\user\AppData\Local\Programs\APSIM2026.8.8099.0"
)

MODELS_EXE = APSIM_ROOT / "bin" / "Models.exe"
OFFICIAL_OILPALM = APSIM_ROOT / "Examples" / "OilPalm.apsimx"

DESIGN_CSV = WORKDIR / (
    "40D03C_APSIM_REPRESENTATIVE_BENCHMARK_DESIGN_SIAK_AOI01_V1.csv"
)

CHIRPS_CSV = WORKDIR / (
    "40B04B1_CHIRPS_V2_DAILY_NATIVE_CELLS_2001_2025_SIAK_AOI01_V1.csv"
)

ERA5_CSV = WORKDIR / (
    "40B04B2_ERA5LAND_DAILY_NATIVE_CELLS_2001_2025_SIAK_AOI01_V4.csv"
)

RUN_ROOT = WORKDIR / (
    "40D04A_APSIM_REPRESENTATIVE_RUNS_SIAK_AOI01_V1"
)

CHECKPOINT_CSV = WORKDIR / (
    "40D04A_APSIM_REPRESENTATIVE_RESULTS_CHECKPOINT_SIAK_AOI01_V1.csv"
)

FINAL_CSV = WORKDIR / (
    "40D04A_APSIM_REPRESENTATIVE_BENCHMARK_RESULTS_SIAK_AOI01_V1.csv"
)

QC_JSON = WORKDIR / (
    "40D04A_APSIM_REPRESENTATIVE_BENCHMARK_QC_SIAK_AOI01_V1.json"
)

FAIL_CSV = WORKDIR / (
    "40D04A_APSIM_REPRESENTATIVE_FAILURES_SIAK_AOI01_V1.csv"
)

BASELINE_POPULATION = 143
SIM_END = pd.Timestamp("2025-12-31")
MAX_AGE_MATCH_DIFF_YR = 0.05


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


def safe_unit_id(unit_id):
    return (
        str(unit_id)
        .replace(",", "_")
        .replace("+", "P")
        .replace("-", "M")
        .replace(" ", "_")
    )


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
        "stdout_tail": (cp.stdout or "").strip()[-3000:],
        "stderr_tail": (cp.stderr or "").strip()[-3000:],
    }


def write_met(
    path,
    weather_full,
    start_date,
    end_date,
    latitude,
    longitude,
):
    wf = weather_full.copy()
    wf["MONTH"] = wf["DATE"].dt.month

    monthly_clim = wf.groupby("MONTH")["TMEAN_C"].mean()

    tav = float(monthly_clim.mean())
    amp = float(monthly_clim.max() - monthly_clim.min())

    sim = wf.loc[
        (wf["DATE"] >= start_date)
        & (wf["DATE"] <= end_date)
    ].copy()

    expected = pd.date_range(start_date, end_date, freq="D")

    if len(sim) != len(expected):
        raise ValueError(
            f"Incomplete simulation weather: {len(sim)} rows; "
            f"expected {len(expected)}."
        )

    if not sim["DATE"].reset_index(drop=True).equals(
        pd.Series(expected)
    ):
        raise ValueError("Simulation weather calendar is non-contiguous.")

    req = [
        "RAIN_MM_DAY",
        "RAD_MJ_M2_DAY",
        "TMIN_C",
        "TMAX_C",
        "TMEAN_C",
    ]

    if sim[req].isna().any().any():
        raise ValueError("Missing forcing value in simulation weather.")

    if (sim["RAIN_MM_DAY"] < 0).any():
        raise ValueError("Negative rainfall.")

    if (sim["RAD_MJ_M2_DAY"] < 0).any():
        raise ValueError("Negative solar radiation.")

    if (sim["TMIN_C"] > sim["TMAX_C"]).any():
        raise ValueError("Tmin > Tmax.")

    sim["year"] = sim["DATE"].dt.year.astype(int)
    sim["day"] = sim["DATE"].dt.dayofyear.astype(int)

    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("[weather.met.weather]\n")
        f.write(f"latitude = {latitude:.8f} (DECIMAL DEGREES)\n")
        f.write(f"longitude = {longitude:.8f} (DECIMAL DEGREES)\n")
        f.write(f"tav = {tav:.6f} (oC)\n")
        f.write(f"amp = {amp:.6f} (oC)\n")
        f.write("year day radn maxt mint rain\n")
        f.write("() () (MJ/m^2/day) (oC) (oC) (mm)\n")

        for row in sim[
            [
                "year",
                "day",
                "RAD_MJ_M2_DAY",
                "TMAX_C",
                "TMIN_C",
                "RAIN_MM_DAY",
            ]
        ].itertuples(index=False):

            f.write(
                f"{int(row.year):4d} "
                f"{int(row.day):3d} "
                f"{float(row.RAD_MJ_M2_DAY):10.5f} "
                f"{float(row.TMAX_C):9.4f} "
                f"{float(row.TMIN_C):9.4f} "
                f"{float(row.RAIN_MM_DAY):10.5f}\n"
            )

    return {
        "weather_rows": int(len(sim)),
        "weather_start": str(sim["DATE"].min().date()),
        "weather_end": str(sim["DATE"].max().date()),
        "tav_c": tav,
        "amp_c": amp,
    }


def read_annual_output(db_path, age_proxy):
    con = sqlite3.connect(db_path)

    try:
        query = '''
        SELECT
            "Clock.Today",
            "Clock.Today.Year",
            "OilPalm.Age",
            "OilPalm.LAI",
            "AnnualRain",
            "Calculations.Script.AnnualBunches",
            "Calculations.Script.AnnualBunchSize",
            "Calculations.Script.AnnualYield",
            "AnnualBunchNPP"
        FROM "AnnualOutput"
        ORDER BY "Clock.Today"
        '''
        df = pd.read_sql_query(query, con)
    finally:
        con.close()

    if df.empty:
        raise ValueError("AnnualOutput is empty.")

    ycol = "Calculations.Script.AnnualYield"
    agecol = "OilPalm.Age"

    df[ycol] = pd.to_numeric(df[ycol], errors="coerce")
    df[agecol] = pd.to_numeric(df[agecol], errors="coerce")

    valid = df.loc[
        df[ycol].notna() & df[agecol].notna()
    ].copy()

    if valid.empty:
        raise ValueError("No finite AnnualYield + OilPalm.Age rows.")

    valid["AGE_DIFF"] = (
        valid[agecol] - float(age_proxy)
    ).abs()

    matched = valid.sort_values(
        ["AGE_DIFF", "Clock.Today.Year"]
    ).iloc[0]

    final = valid.sort_values(
        "Clock.Today.Year"
    ).iloc[-1]

    matched_year = int(matched["Clock.Today.Year"])

    trailing3 = valid.loc[
        (valid["Clock.Today.Year"] <= matched_year)
        & (valid["Clock.Today.Year"] >= matched_year - 2)
    ]

    return {
        "annual_rows": int(len(df)),
        "age_matched_calendar_year":
            int(matched["Clock.Today.Year"]),
        "age_matched_model_age_yr":
            float(matched[agecol]),
        "age_match_abs_diff_yr":
            float(matched["AGE_DIFF"]),
        "age_matched_annual_yield_t_ha_yr":
            float(matched[ycol]),
        "age_matched_annual_bunches":
            float(matched["Calculations.Script.AnnualBunches"]),
        "age_matched_annual_bunch_size":
            float(matched["Calculations.Script.AnnualBunchSize"]),
        "age_matched_annual_bunch_npp":
            float(matched["AnnualBunchNPP"]),
        "age_matched_lai":
            float(matched["OilPalm.LAI"]),
        "age_matched_annual_rain_mm":
            float(matched["AnnualRain"])
            if pd.notna(matched["AnnualRain"])
            else None,
        "age_matched_trailing3y_mean_yield_t_ha_yr":
            float(trailing3[ycol].mean())
            if not trailing3.empty
            else None,
        "final_calendar_year":
            int(final["Clock.Today.Year"]),
        "final_model_age_yr":
            float(final[agecol]),
        "final_annual_yield_t_ha_yr":
            float(final[ycol]),
    }


print("====================================================")
print("40D04A — APSIM REPRESENTATIVE BENCHMARK EXECUTION")
print("====================================================")
print("Models.exe :", MODELS_EXE)
print("Design     :", DESIGN_CSV)
print("Run root   :", RUN_ROOT)

required = [
    MODELS_EXE,
    OFFICIAL_OILPALM,
    DESIGN_CSV,
    CHIRPS_CSV,
    ERA5_CSV,
]

missing = [str(p) for p in required if not p.exists()]
if missing:
    raise FileNotFoundError(
        "Missing required file(s):\n" + "\n".join(missing)
    )

RUN_ROOT.mkdir(parents=True, exist_ok=True)

design = pd.read_csv(DESIGN_CSV)

if len(design) != 48:
    raise ValueError(f"Expected 48 representative ASUs; found {len(design)}.")

if design["UNIT_ID"].duplicated().any():
    raise ValueError("Duplicate UNIT_ID in design.")

print("\nLoading climate tables...")

chirps = pd.read_csv(
    CHIRPS_CSV,
    usecols=[
        "DATE",
        "CHIRPS_CELL_ID",
        "RAIN_MM_DAY",
    ],
)

era5 = pd.read_csv(
    ERA5_CSV,
    usecols=[
        "DATE",
        "ERA5L_CELL_ID",
        "TMEAN_C",
        "TMIN_C",
        "TMAX_C",
        "RAD_MJ_M2_DAY",
    ],
)

chirps["DATE"] = pd.to_datetime(chirps["DATE"])
era5["DATE"] = pd.to_datetime(era5["DATE"])

pair_cache = {}

for row in (
    design[
        [
            "CLIMATE_PAIR_ID",
            "CHIRPS_CELL_ID",
            "ERA5L_CELL_ID",
        ]
    ]
    .drop_duplicates()
    .itertuples(index=False)
):

    c = chirps.loc[
        chirps["CHIRPS_CELL_ID"].astype(str)
        == str(row.CHIRPS_CELL_ID)
    ].copy()

    e = era5.loc[
        era5["ERA5L_CELL_ID"].astype(str)
        == str(row.ERA5L_CELL_ID)
    ].copy()

    pair = c.merge(
        e,
        on="DATE",
        how="inner",
        validate="one_to_one",
    ).sort_values("DATE").reset_index(drop=True)

    expected = pd.date_range(
        "2001-01-01",
        "2025-12-31",
        freq="D",
    )

    if len(pair) != len(expected):
        raise ValueError(
            f"{row.CLIMATE_PAIR_ID}: "
            f"{len(pair)} rows; expected {len(expected)}."
        )

    if not pair["DATE"].equals(pd.Series(expected)):
        raise ValueError(
            f"{row.CLIMATE_PAIR_ID}: calendar not contiguous."
        )

    pair_cache[str(row.CLIMATE_PAIR_ID)] = pair

print("Climate pairs cached:", len(pair_cache))

with open(OFFICIAL_OILPALM, "r", encoding="utf-8-sig") as f:
    official_template = json.load(f)

if CHECKPOINT_CSV.exists():
    checkpoint = pd.read_csv(CHECKPOINT_CSV)

    if "UNIT_ID" in checkpoint.columns:
        completed = set(
            checkpoint.loc[
                checkpoint["STATUS"] == "PASS",
                "UNIT_ID",
            ].astype(str)
        )
    else:
        completed = set()

    result_records = checkpoint.to_dict("records")

    print("\nCheckpoint found.")
    print("Already PASS:", len(completed))
else:
    completed = set()
    result_records = []

fail_records = []

total = len(design)
start_all = time.perf_counter()

for idx, row in enumerate(design.itertuples(index=False), 1):

    unit_id = str(row.UNIT_ID)

    if unit_id in completed:
        print(f"[{idx:02d}/{total}] SKIP PASS | {unit_id}")
        continue

    print(f"\n[{idx:02d}/{total}] RUN | {unit_id}")

    try:
        age_proxy = int(row.AGE_PROXY_YR)
        planting_year = int(row.PLANTING_YEAR_PROXY)

        start_date = pd.Timestamp(f"{planting_year}-01-01")

        if start_date < pd.Timestamp("2001-01-01"):
            raise ValueError(
                f"Planting year {planting_year} predates forcing."
            )

        pair_id = str(row.CLIMATE_PAIR_ID)

        if pair_id not in pair_cache:
            raise KeyError(f"Climate pair not cached: {pair_id}")

        safe_id = safe_unit_id(unit_id)
        run_dir = RUN_ROOT / safe_id

        if run_dir.exists():
            shutil.rmtree(run_dir)

        run_dir.mkdir(parents=True, exist_ok=True)

        met_path = run_dir / f"{safe_id}.met"
        apsimx_path = run_dir / f"{safe_id}.apsimx"

        weather_meta = write_met(
            path=met_path,
            weather_full=pair_cache[pair_id],
            start_date=start_date,
            end_date=SIM_END,
            latitude=float(row.CENTROID_LAT_EXACT),
            longitude=float(row.CENTROID_LON_EXACT),
        )

        sim = json.loads(json.dumps(official_template))

        _, clock = find_node(sim, "Models.Clock")
        _, weather_node = find_node(sim, "Models.Climate.Weather")
        _, manager = find_node(
            sim,
            "Models.Manager",
            "Palm Management",
        )

        if clock is None or weather_node is None or manager is None:
            raise RuntimeError(
                "Clock/Weather/Palm Management node not found."
            )

        clock["Start"] = start_date.strftime(
            "%Y-%m-%dT00:00:00"
        )

        clock["End"] = SIM_END.strftime(
            "%Y-%m-%dT00:00:00"
        )

        weather_node["FileName"] = str(
            met_path
        ).replace("\\", "/")

        set_manager_parameter(
            manager,
            "sowing_date",
            f"01/01/{planting_year} 00:00:00",
        )

        set_manager_parameter(
            manager,
            "population",
            BASELINE_POPULATION,
        )

        with open(
            apsimx_path,
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(sim, f, indent=2)

        run_meta = run_apsim(
            apsimx_path,
            run_dir,
        )

        db_path = apsimx_path.with_suffix(".db")

        if run_meta["returncode"] != 0:
            raise RuntimeError(
                "APSIM return code "
                f"{run_meta['returncode']}\n"
                f"{run_meta['stderr_tail']}"
            )

        if not db_path.exists():
            raise FileNotFoundError(
                f"Expected APSIM DB not found: {db_path}"
            )

        output = read_annual_output(
            db_path=db_path,
            age_proxy=age_proxy,
        )

        if (
            output["age_match_abs_diff_yr"]
            > MAX_AGE_MATCH_DIFF_YR
        ):
            raise ValueError(
                "Age-match difference too large: "
                f"{output['age_match_abs_diff_yr']:.6f} yr"
            )

        record = {
            "UNIT_ID": unit_id,
            "STATUS": "PASS",
            "AGE_PROXY_YR": age_proxy,
            "PLANTING_YEAR_PROXY": planting_year,
            "CLIMATE_PAIR_ID": pair_id,
            "CHIRPS_CELL_ID": str(row.CHIRPS_CELL_ID),
            "ERA5L_CELL_ID": str(row.ERA5L_CELL_ID),
            "CENTROID_LAT_EXACT":
                float(row.CENTROID_LAT_EXACT),
            "CENTROID_LON_EXACT":
                float(row.CENTROID_LON_EXACT),
            "POPULATION_PALM_HA":
                BASELINE_POPULATION,
            "CULTIVAR": "Dami",
            "SOIL_POLICY":
                "OFFICIAL_APSIM_OILPALM_REFERENCE",
            "MANAGEMENT_POLICY":
                "OFFICIAL_APSIM_REFERENCE",
            **weather_meta,
            **output,
            "APSIM_RETURN_CODE":
                run_meta["returncode"],
            "APSIM_ELAPSED_SEC":
                run_meta["elapsed_sec"],
            "DB_PATH":
                str(db_path),
            "APSIMX_PATH":
                str(apsimx_path),
            "MET_PATH":
                str(met_path),
        }

        result_records = [
            x for x in result_records
            if str(x.get("UNIT_ID")) != unit_id
        ]

        result_records.append(record)

        pd.DataFrame(result_records).to_csv(
            CHECKPOINT_CSV,
            index=False,
        )

        completed.add(unit_id)

        print(
            "  PASS | "
            f"age-match={output['age_matched_model_age_yr']:.4f} "
            f"(diff={output['age_match_abs_diff_yr']:.4f}) | "
            f"yield={output['age_matched_annual_yield_t_ha_yr']:.4f} "
            "t FFB/ha/yr | "
            f"{run_meta['elapsed_sec']:.1f}s"
        )

    except Exception as exc:
        fail = {
            "UNIT_ID": unit_id,
            "STATUS": "FAIL",
            "ERROR": repr(exc),
            "TRACEBACK": traceback.format_exc(),
        }

        fail_records.append(fail)

        print("  FAIL:", repr(exc))

elapsed_all = time.perf_counter() - start_all

results = pd.DataFrame(result_records)

if not results.empty:
    results = (
        results
        .drop_duplicates(
            subset=["UNIT_ID"],
            keep="last",
        )
        .sort_values("UNIT_ID")
        .reset_index(drop=True)
    )

    results.to_csv(
        FINAL_CSV,
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
    if not results.empty and "STATUS" in results.columns
    else pd.DataFrame()
)

yield_col = "age_matched_annual_yield_t_ha_yr"

checks = {
    "planned_asus_48":
        total == 48,
    "completed_pass_48":
        len(pass_df) == 48,
    "unique_pass_asus_48":
        (
            pass_df["UNIT_ID"].nunique() == 48
            if not pass_df.empty
            else False
        ),
    "climate_pairs_12":
        (
            pass_df["CLIMATE_PAIR_ID"].nunique() == 12
            if not pass_df.empty
            else False
        ),
    "all_age_match_diff_within_tolerance":
        (
            bool(
                (
                    pass_df["age_match_abs_diff_yr"]
                    <= MAX_AGE_MATCH_DIFF_YR
                ).all()
            )
            if not pass_df.empty
            else False
        ),
    "all_age_matched_yield_finite":
        (
            bool(
                np.isfinite(
                    pd.to_numeric(
                        pass_df[yield_col],
                        errors="coerce",
                    )
                ).all()
            )
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

if not pass_df.empty:
    y = pd.to_numeric(
        pass_df[yield_col],
        errors="coerce",
    )

    yield_summary = {
        "min_t_ha_yr":
            float(y.min()),
        "median_t_ha_yr":
            float(y.median()),
        "mean_t_ha_yr":
            float(y.mean()),
        "max_t_ha_yr":
            float(y.max()),
        "zero_or_near_zero_count":
            int((y <= 0.01).sum()),
    }

    age_diff_summary = {
        "max_abs_diff_yr":
            float(
                pass_df[
                    "age_match_abs_diff_yr"
                ].max()
            ),
        "median_abs_diff_yr":
            float(
                pass_df[
                    "age_match_abs_diff_yr"
                ].median()
            ),
    }
else:
    yield_summary = {}
    age_diff_summary = {}

qc = {
    "gate":
        "40D04A_APSIM_REPRESENTATIVE_BENCHMARK_EXECUTION",
    "status":
        status,
    "apsim_version":
        "2026.8.8099.0",
    "planned_asus":
        int(total),
    "completed_pass":
        int(len(pass_df)),
    "failures_this_execution":
        int(len(fail_records)),
    "climate_pairs_completed":
        (
            int(pass_df["CLIMATE_PAIR_ID"].nunique())
            if not pass_df.empty
            else 0
        ),
    "canonical_output_source":
        "APSIM SQLite .db / AnnualOutput",
    "canonical_comparator":
        "Calculations.Script.AnnualYield at model age nearest AGE_PROXY_YR",
    "canonical_unit":
        "t fresh FFB/ha/year",
    "age_match_tolerance_yr":
        MAX_AGE_MATCH_DIFF_YR,
    "population_assumption_palm_ha":
        BASELINE_POPULATION,
    "cultivar_policy":
        "OFFICIAL_DAMI_REFERENCE",
    "soil_policy":
        "OFFICIAL_APSIM_OILPALM_REFERENCE_NOT_SIAK_CALIBRATED",
    "management_policy":
        "OFFICIAL_APSIM_REFERENCE_NOT_LOCAL_MANAGEMENT",
    "yield_summary":
        yield_summary,
    "age_match_summary":
        age_diff_summary,
    "checks":
        checks,
    "elapsed_total_sec":
        float(elapsed_all),
    "interpretation":
        (
            "Representative APSIM OilPalm process/scenario benchmark. "
            "Not locally calibrated or field-validated actual FFB yield. "
            "SQLite output is canonical because APSIM CSV export is "
            "locale-sensitive in this Windows environment."
        ),
}

QC_JSON.write_text(
    json.dumps(qc, indent=2),
    encoding="utf-8",
)

print("\n====================================================")
print("40D04A FINISHED")
print("====================================================")
print("Status                    :", status)
print("Planned ASUs              :", total)
print("Completed PASS            :", len(pass_df))
print("Climate pairs completed   :", (
    pass_df["CLIMATE_PAIR_ID"].nunique()
    if not pass_df.empty else 0
))
print("Failures this execution   :", len(fail_records))
print("Elapsed total             :", round(elapsed_all / 60, 2), "min")

if yield_summary:
    print(
        "Age-matched yield min    :",
        yield_summary["min_t_ha_yr"],
        "t FFB/ha/yr",
    )
    print(
        "Age-matched yield median :",
        yield_summary["median_t_ha_yr"],
        "t FFB/ha/yr",
    )
    print(
        "Age-matched yield mean   :",
        yield_summary["mean_t_ha_yr"],
        "t FFB/ha/yr",
    )
    print(
        "Age-matched yield max    :",
        yield_summary["max_t_ha_yr"],
        "t FFB/ha/yr",
    )
    print(
        "Zero/near-zero           :",
        yield_summary["zero_or_near_zero_count"],
    )

print("\nQC:")
for key, value in checks.items():
    print(f"{key:45s}: {value}")

print("\nResults    :", FINAL_CSV)
print("Checkpoint :", CHECKPOINT_CSV)
print("QC         :", QC_JSON)

if fail_records:
    print("Failures   :", FAIL_CSV)

if status == "PASS":
    print(
        "Next       : 40D04B APSIM benchmark diagnostics/sensitivity, "
        "then 40D05 freeze."
    )
else:
    print(
        "Next       : Review failed ASUs/QC before 40D04B."
    )

print("====================================================")
