# ============================================================
# OUTPUT 4 / 40D04A-V2
# APSIM OILPALM REPRESENTATIVE BENCHMARK — CORRECTED EXECUTION
# SIAK_AOI01
#
# Correction from V1:
# The official APSIM OilPalm example contains an example-specific
# hard-coded EndCrop event on 2007-01-01. That event is disabled
# ONLY in generated benchmark copies (never in the installed file),
# because Output 4 is evaluating each ASU at its age proxy and does
# not prescribe a fixed 2007 replant/end-crop event.
#
# Execution:
# - 48 representative ASUs
# - serial, single-threaded
# - CHIRPS V2 rain + ERA5-Land radn/Tmin/Tmax
# - population 143 palm/ha
# - cultivar Dami
# - official APSIM reference soil/other management retained
# - SQLite .db is canonical numerical output
# - annual yield selected at OilPalm.Age nearest AGE_PROXY_YR
# - V1 PASS results are compared against V2 for parity
# ============================================================

from pathlib import Path
import json
import shutil
import subprocess
import sqlite3
import time
import traceback
import re

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

V1_RESULTS = WORKDIR / (
    "40D04A_APSIM_REPRESENTATIVE_BENCHMARK_RESULTS_SIAK_AOI01_V1.csv"
)

RUN_ROOT = WORKDIR / (
    "40D04A_V2_APSIM_REPRESENTATIVE_RUNS_SIAK_AOI01"
)

CHECKPOINT_CSV = WORKDIR / (
    "40D04A_V2_APSIM_REPRESENTATIVE_RESULTS_CHECKPOINT_SIAK_AOI01.csv"
)

FINAL_CSV = WORKDIR / (
    "40D04A_V2_APSIM_REPRESENTATIVE_BENCHMARK_RESULTS_SIAK_AOI01.csv"
)

QC_JSON = WORKDIR / (
    "40D04A_V2_APSIM_REPRESENTATIVE_BENCHMARK_QC_SIAK_AOI01.json"
)

FAIL_CSV = WORKDIR / (
    "40D04A_V2_APSIM_REPRESENTATIVE_FAILURES_SIAK_AOI01.csv"
)

PARITY_CSV = WORKDIR / (
    "40D04A_V2_VS_V1_PASS_PARITY_SIAK_AOI01.csv"
)

BASELINE_POPULATION = 143
SIM_END = pd.Timestamp("2025-12-31")
MAX_AGE_MATCH_DIFF_YR = 0.05
PARITY_TOL = 1e-8

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


def disable_fixed_2007_endcrop(manager):
    """
    Disable the example-specific:
        if (Clock.Today == new DateTime(2007,1,1))
            oilPalm.EndCrop();

    in the GENERATED COPY only.

    Returns number of lines changed.
    """
    code = manager.get("CodeArray", []) or []
    changed = 0
    out = []

    for line in code:
        stripped = line.replace(" ", "").lower()

        if (
            "if(clock.today==newdatetime(2007,1,1))"
            in stripped
        ):
            out.append(
                " // OUTPUT4: fixed 2007 EndCrop condition disabled "
                "for age-proxy benchmark."
            )
            changed += 1
            continue

        if "oilpalm.endcrop();" in stripped:
            out.append(
                " // OUTPUT4: oilPalm.EndCrop(); disabled; "
                "no fixed replant/end-crop date assumed."
            )
            changed += 1
            continue

        out.append(line)

    manager["CodeArray"] = out

    # Safety: no active line should still contain EndCrop().
    active_endcrop = [
        x for x in out
        if "oilpalm.endcrop();" in x.replace(" ", "").lower()
        and not x.lstrip().startswith("//")
    ]

    if active_endcrop:
        raise RuntimeError(
            "An active oilPalm.EndCrop() call remains in Palm Management."
        )

    return changed


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
        "stdout_tail": (cp.stdout or "").strip()[-2500:],
        "stderr_tail": (cp.stderr or "").strip()[-2500:],
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
            f"Incomplete simulation weather: {len(sim)} vs {len(expected)}"
        )

    if not sim["DATE"].reset_index(drop=True).equals(pd.Series(expected)):
        raise ValueError("Simulation weather calendar is non-contiguous.")

    req = [
        "RAIN_MM_DAY",
        "RAD_MJ_M2_DAY",
        "TMIN_C",
        "TMAX_C",
        "TMEAN_C",
    ]

    if sim[req].isna().any().any():
        raise ValueError("Missing forcing value.")

    if (sim["RAIN_MM_DAY"] < 0).any():
        raise ValueError("Negative rainfall.")

    if (sim["RAD_MJ_M2_DAY"] < 0).any():
        raise ValueError("Negative radiation.")

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
        query = """
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
        """
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


# ------------------------------------------------------------
# PREFLIGHT
# ------------------------------------------------------------

print("====================================================")
print("40D04A-V2 — APSIM REPRESENTATIVE BENCHMARK")
print("CORRECTED: FIXED 2007 ENDCROP DISABLED")
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
    raise ValueError(f"Expected 48 ASUs; found {len(design)}.")

if design["UNIT_ID"].duplicated().any():
    raise ValueError("Duplicate UNIT_ID in design.")

# ------------------------------------------------------------
# LOAD/CACHE CLIMATE PAIRS
# ------------------------------------------------------------

print("\nLoading climate tables...")

chirps = pd.read_csv(
    CHIRPS_CSV,
    usecols=["DATE", "CHIRPS_CELL_ID", "RAIN_MM_DAY"],
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

expected_full = pd.date_range(
    "2001-01-01",
    "2025-12-31",
    freq="D",
)

pair_cache = {}

for row in (
    design[
        ["CLIMATE_PAIR_ID", "CHIRPS_CELL_ID", "ERA5L_CELL_ID"]
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

    if len(pair) != len(expected_full):
        raise ValueError(
            f"{row.CLIMATE_PAIR_ID}: incomplete climate rows."
        )

    if not pair["DATE"].equals(pd.Series(expected_full)):
        raise ValueError(
            f"{row.CLIMATE_PAIR_ID}: non-contiguous climate calendar."
        )

    pair_cache[str(row.CLIMATE_PAIR_ID)] = pair

print("Climate pairs cached:", len(pair_cache))

# ------------------------------------------------------------
# LOAD + CORRECT TEMPLATE IN MEMORY
# ------------------------------------------------------------

with open(OFFICIAL_OILPALM, "r", encoding="utf-8-sig") as f:
    corrected_template = json.load(f)

_, template_manager = find_node(
    corrected_template,
    "Models.Manager",
    "Palm Management",
)

if template_manager is None:
    raise RuntimeError("Palm Management node not found.")

patch_lines_changed = disable_fixed_2007_endcrop(template_manager)

if patch_lines_changed < 2:
    raise RuntimeError(
        "Expected to disable at least 2 fixed-EndCrop code lines; "
        f"changed {patch_lines_changed}."
    )

print("Fixed EndCrop code lines disabled:", patch_lines_changed)
print("Installed APSIM example remains untouched.")

# ------------------------------------------------------------
# RESUME SUPPORT
# ------------------------------------------------------------

if CHECKPOINT_CSV.exists():
    checkpoint = pd.read_csv(CHECKPOINT_CSV)

    completed = set(
        checkpoint.loc[
            checkpoint["STATUS"] == "PASS",
            "UNIT_ID",
        ].astype(str)
    )

    result_records = checkpoint.to_dict("records")

    print("\nV2 checkpoint found.")
    print("Already PASS:", len(completed))
else:
    completed = set()
    result_records = []

fail_records = []

# ------------------------------------------------------------
# EXECUTE ALL 48
# ------------------------------------------------------------

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
        weather_full = pair_cache[pair_id]

        safe_id = safe_unit_id(unit_id)
        run_dir = RUN_ROOT / safe_id

        if run_dir.exists():
            shutil.rmtree(run_dir)

        run_dir.mkdir(parents=True, exist_ok=True)

        met_path = run_dir / f"{safe_id}.met"
        apsimx_path = run_dir / f"{safe_id}.apsimx"

        weather_meta = write_met(
            path=met_path,
            weather_full=weather_full,
            start_date=start_date,
            end_date=SIM_END,
            latitude=float(row.CENTROID_LAT_EXACT),
            longitude=float(row.CENTROID_LON_EXACT),
        )

        sim = json.loads(json.dumps(corrected_template))

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

        clock["Start"] = start_date.strftime("%Y-%m-%dT00:00:00")
        clock["End"] = SIM_END.strftime("%Y-%m-%dT00:00:00")

        weather_node["FileName"] = str(met_path).replace("\\", "/")

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

        # Re-assert safety after per-run copy.
        active_endcrop = []
        for line in manager.get("CodeArray", []) or []:
            compact = line.replace(" ", "").lower()
            if (
                "oilpalm.endcrop();" in compact
                and not line.lstrip().startswith("//")
            ):
                active_endcrop.append(line)

        if active_endcrop:
            raise RuntimeError(
                "Active EndCrop call found in generated benchmark copy."
            )

        with open(apsimx_path, "w", encoding="utf-8") as f:
            json.dump(sim, f, indent=2)

        run_meta = run_apsim(apsimx_path, run_dir)

        if run_meta["returncode"] != 0:
            raise RuntimeError(
                f"APSIM return code {run_meta['returncode']}\n"
                f"{run_meta['stderr_tail']}"
            )

        db_path = apsimx_path.with_suffix(".db")

        if not db_path.exists():
            raise FileNotFoundError(f"DB not found: {db_path}")

        output = read_annual_output(
            db_path=db_path,
            age_proxy=age_proxy,
        )

        if output["age_match_abs_diff_yr"] > MAX_AGE_MATCH_DIFF_YR:
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
            "CENTROID_LAT_EXACT": float(row.CENTROID_LAT_EXACT),
            "CENTROID_LON_EXACT": float(row.CENTROID_LON_EXACT),
            "POPULATION_PALM_HA": BASELINE_POPULATION,
            "CULTIVAR": "Dami",
            "SOIL_POLICY":
                "OFFICIAL_APSIM_OILPALM_REFERENCE",
            "MANAGEMENT_POLICY":
                "OFFICIAL_REFERENCE_WITH_FIXED_2007_ENDCROP_DISABLED",
            "ENDCROP_POLICY":
                "NO_FIXED_ENDCROP_WITHIN_OUTPUT4_BENCHMARK",
            **weather_meta,
            **output,
            "APSIM_RETURN_CODE": run_meta["returncode"],
            "APSIM_ELAPSED_SEC": run_meta["elapsed_sec"],
            "DB_PATH": str(db_path),
            "APSIMX_PATH": str(apsimx_path),
            "MET_PATH": str(met_path),
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
            f"plant={planting_year} | "
            f"age-match={output['age_matched_model_age_yr']:.4f} "
            f"(diff={output['age_match_abs_diff_yr']:.4f}) | "
            f"yield={output['age_matched_annual_yield_t_ha_yr']:.4f} "
            "t FFB/ha/yr | "
            f"{run_meta['elapsed_sec']:.1f}s"
        )

    except Exception as exc:
        fail_records.append({
            "UNIT_ID": unit_id,
            "STATUS": "FAIL",
            "ERROR": repr(exc),
            "TRACEBACK": traceback.format_exc(),
        })

        print("  FAIL:", repr(exc))

elapsed_all = time.perf_counter() - start_all

# ------------------------------------------------------------
# FINAL RESULT
# ------------------------------------------------------------

results = pd.DataFrame(result_records)

if not results.empty:
    results = (
        results
        .drop_duplicates(subset=["UNIT_ID"], keep="last")
        .sort_values("UNIT_ID")
        .reset_index(drop=True)
    )

    results.to_csv(FINAL_CSV, index=False)

if fail_records:
    pd.DataFrame(fail_records).to_csv(FAIL_CSV, index=False)
elif FAIL_CSV.exists():
    FAIL_CSV.unlink()

pass_df = (
    results.loc[results["STATUS"] == "PASS"].copy()
    if not results.empty
    else pd.DataFrame()
)

yield_col = "age_matched_annual_yield_t_ha_yr"

# ------------------------------------------------------------
# V1 vs V2 PARITY FOR THE 29 PREVIOUSLY-PASSING ASUs
# ------------------------------------------------------------

parity_available = V1_RESULTS.exists()
parity_ok = True
parity_max_abs_diff = None
parity_n = 0

if parity_available and not pass_df.empty:
    v1 = pd.read_csv(V1_RESULTS)

    if (
        "UNIT_ID" in v1.columns
        and yield_col in v1.columns
    ):
        v1 = v1.loc[v1["STATUS"] == "PASS", ["UNIT_ID", yield_col]].copy()
        v1 = v1.rename(columns={yield_col: "V1_YIELD"})

        v2 = pass_df[["UNIT_ID", yield_col]].copy()
        v2 = v2.rename(columns={yield_col: "V2_YIELD"})

        parity = v1.merge(
            v2,
            on="UNIT_ID",
            how="inner",
            validate="one_to_one",
        )

        parity["ABS_DIFF"] = (
            pd.to_numeric(parity["V2_YIELD"], errors="coerce")
            - pd.to_numeric(parity["V1_YIELD"], errors="coerce")
        ).abs()

        parity_n = len(parity)

        if parity_n > 0:
            parity_max_abs_diff = float(parity["ABS_DIFF"].max())
            parity_ok = bool(
                np.isfinite(parity["ABS_DIFF"]).all()
                and parity_max_abs_diff <= PARITY_TOL
            )

        parity.to_csv(PARITY_CSV, index=False)

# ------------------------------------------------------------
# QC
# ------------------------------------------------------------

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

    "all_yield_finite":
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

    "fixed_2007_endcrop_disabled":
        patch_lines_changed >= 2,

    "v1_previous_pass_parity":
        parity_ok,
}

status = "PASS" if all(checks.values()) else "REVIEW"

if not pass_df.empty:
    y = pd.to_numeric(pass_df[yield_col], errors="coerce")

    yield_summary = {
        "min_t_ha_yr": float(y.min()),
        "median_t_ha_yr": float(y.median()),
        "mean_t_ha_yr": float(y.mean()),
        "max_t_ha_yr": float(y.max()),
        "zero_or_near_zero_count": int((y <= 0.01).sum()),
    }
else:
    yield_summary = {}

qc = {
    "gate":
        "40D04A_V2_APSIM_REPRESENTATIVE_BENCHMARK_CORRECTED",
    "status":
        status,
    "apsim_version":
        "2026.8.8099.0",
    "correction":
        "Disabled example-specific hard-coded EndCrop on 2007-01-01 "
        "in generated benchmark copies only.",
    "installed_example_modified":
        False,
    "patch_lines_changed":
        int(patch_lines_changed),
    "planned_asus":
        int(total),
    "completed_pass":
        int(len(pass_df)),
    "failures":
        int(len(fail_records)),
    "climate_pairs_completed":
        int(pass_df["CLIMATE_PAIR_ID"].nunique())
        if not pass_df.empty else 0,
    "canonical_output_source":
        "APSIM SQLite .db / AnnualOutput",
    "canonical_comparator":
        "Calculations.Script.AnnualYield at OilPalm.Age nearest AGE_PROXY_YR",
    "canonical_unit":
        "t fresh FFB/ha/year",
    "population_assumption_palm_ha":
        BASELINE_POPULATION,
    "cultivar_policy":
        "OFFICIAL_DAMI_REFERENCE",
    "soil_policy":
        "OFFICIAL_APSIM_OILPALM_REFERENCE_NOT_SIAK_CALIBRATED",
    "management_policy":
        "OFFICIAL_REFERENCE_EXCEPT_FIXED_2007_ENDCROP_DISABLED",
    "yield_summary":
        yield_summary,
    "v1_parity": {
        "available": bool(parity_available),
        "n_compared": int(parity_n),
        "tolerance": PARITY_TOL,
        "max_abs_yield_diff": parity_max_abs_diff,
        "pass": bool(parity_ok),
    },
    "checks":
        checks,
    "elapsed_total_sec":
        float(elapsed_all),
    "interpretation":
        (
            "Representative process/scenario benchmark only. "
            "The fixed 2007 EndCrop event belongs to the distributed example "
            "management script and is not treated as a Siak management fact. "
            "No local yield calibration or field validation is claimed."
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
print("40D04A-V2 FINISHED")
print("====================================================")
print("Status                    :", status)
print("Planned ASUs              :", total)
print("Completed PASS            :", len(pass_df))
print("Climate pairs completed   :", (
    pass_df["CLIMATE_PAIR_ID"].nunique()
    if not pass_df.empty else 0
))
print("Failures                  :", len(fail_records))
print("EndCrop lines disabled    :", patch_lines_changed)
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

print("\nV1 → V2 parity:")
print("Compared previous PASS ASUs:", parity_n)
print("Max abs yield difference    :", parity_max_abs_diff)
print("Parity PASS                 :", parity_ok)

print("\nQC:")
for key, value in checks.items():
    print(f"{key:45s}: {value}")

print("\nResults :", FINAL_CSV)
print("QC      :", QC_JSON)

if parity_available:
    print("Parity  :", PARITY_CSV)

if fail_records:
    print("Failures:", FAIL_CSV)

if status == "PASS":
    print(
        "Next    : 40D04B APSIM benchmark diagnostics/sensitivity, "
        "then 40D05 freeze."
    )
else:
    print(
        "Next    : Review V2 failures/QC before 40D04B."
    )

print("====================================================")
