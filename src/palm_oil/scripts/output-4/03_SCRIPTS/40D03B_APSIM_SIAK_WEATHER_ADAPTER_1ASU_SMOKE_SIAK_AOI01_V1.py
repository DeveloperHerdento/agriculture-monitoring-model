# ============================================================
# OUTPUT 4 / 40D03B
# APSIM OILPALM — SIAK WEATHER ADAPTER + 1-ASU SMOKE TEST
# SIAK_AOI01
#
# Run directly in Jupyter.
#
# Purpose:
# 1) Reuse the same 1-ASU smoke-test location used for PALMSIM.
# 2) Join CHIRPS V2 rainfall + ERA5-Land radiation/Tmin/Tmax.
# 3) Build an APSIM .met file.
# 4) Copy the official OilPalm example (never edit installed original).
# 5) Set Siak weather, age-proxy planting year, and baseline population.
# 6) Run APSIM twice and check deterministic CSV outputs.
#
# IMPORTANT:
# - Soil and cultivar remain the official APSIM OilPalm reference setup.
# - This is a process/scenario smoke test, NOT local yield validation.
# ============================================================

from pathlib import Path
import json
import shutil
import subprocess
import hashlib
import time

import numpy as np
import pandas as pd

# ------------------------------------------------------------
# PATHS / CONFIG
# ------------------------------------------------------------

WORKDIR = Path(
    r"C:\Users\user\Documents\KERJA\SPATIAL DATA ANALYST INTERN\04_YIELD"
)

APSIM_ROOT = Path(
    r"C:\Users\user\AppData\Local\Programs\APSIM2026.8.8099.0"
)

MODELS_EXE = APSIM_ROOT / "bin" / "Models.exe"
OFFICIAL_OILPALM = APSIM_ROOT / "Examples" / "OilPalm.apsimx"

MAP_CSV = WORKDIR / "40B04A_ASU_CLIMATE_CELL_MAPPING_SIAK_AOI01_V1.csv"
CHIRPS_CSV = WORKDIR / "40B04B1_CHIRPS_V2_DAILY_NATIVE_CELLS_2001_2025_SIAK_AOI01_V1.csv"
ERA5_CSV = WORKDIR / "40B04B2_ERA5LAND_DAILY_NATIVE_CELLS_2001_2025_SIAK_AOI01_V4.csv"

# Same ASU previously used for PALMSIM 1-ASU smoke test.
TARGET_ASU = "SIAK_AOI01_G500_1633,144"

# Align baseline density with PALMSIM Output 4 baseline.
BASELINE_POPULATION = 143

OUT_ROOT = WORKDIR / "40D03B_APSIM_SIAK_1ASU_SMOKE_SIAK_AOI01_V1"
RUN1 = OUT_ROOT / "RUN1"
RUN2 = OUT_ROOT / "RUN2"

MET_PATH = OUT_ROOT / "SIAK_AOI01_APSIM_WEATHER_2001_2025_V1.met"

AUDIT_JSON = WORKDIR / (
    "40D03B_APSIM_SIAK_WEATHER_ADAPTER_1ASU_SMOKE_QC_SIAK_AOI01_V1.json"
)

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
    params = manager.get("Parameters", []) or []
    for p in params:
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
            "--csv",
            "--verbose",
        ],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=1800,
    )
    return {
        "returncode": cp.returncode,
        "elapsed_sec": time.perf_counter() - t0,
        "stdout": (cp.stdout or "").strip(),
        "stderr": (cp.stderr or "").strip(),
    }


def normalized_hash(path):
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = "\n".join(line.rstrip() for line in text.split("\n")).strip() + "\n"
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def format_manager_date(dt):
    # Unambiguous for day=1, month=1; matches APSIM example style.
    return f"01/01/{dt.year} 00:00:00"


# ------------------------------------------------------------
# PREFLIGHT
# ------------------------------------------------------------

print("====================================================")
print("40D03B — APSIM SIAK WEATHER ADAPTER + 1-ASU SMOKE")
print("====================================================")
print("Target ASU :", TARGET_ASU)
print("Workdir    :", WORKDIR)

required = [
    MODELS_EXE,
    OFFICIAL_OILPALM,
    MAP_CSV,
    CHIRPS_CSV,
    ERA5_CSV,
]

missing = [str(p) for p in required if not p.exists()]
if missing:
    raise FileNotFoundError("Missing required file(s):\n" + "\n".join(missing))

OUT_ROOT.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------
# 1. TARGET ASU + CLIMATE CELL CONTRACT
# ------------------------------------------------------------

mapping = pd.read_csv(MAP_CSV)

target = mapping.loc[mapping["UNIT_ID"].astype(str) == TARGET_ASU].copy()

if len(target) != 1:
    raise ValueError(
        f"Expected exactly 1 mapping row for {TARGET_ASU}; found {len(target)}"
    )

r = target.iloc[0]

age_proxy = float(r["AGE_P50"])
if not np.isfinite(age_proxy):
    raise ValueError("Target ASU AGE_P50 is missing.")

age_proxy_yr = int(round(age_proxy))
reference_year = int(r["REFERENCE_YEAR"])
planting_year_proxy = reference_year - age_proxy_yr

chirps_id = str(r["CHIRPS_CELL_ID"])
era5_id = str(r["ERA5L_CELL_ID"])

lat = float(r["CENTROID_LAT_EXACT"])
lon = float(r["CENTROID_LON_EXACT"])

simulation_start = pd.Timestamp(f"{planting_year_proxy}-01-01")
simulation_end = pd.Timestamp("2025-12-31")

if simulation_start < pd.Timestamp("2001-01-01"):
    raise ValueError(
        "Planting-year proxy predates available 2001 climate forcing. "
        "Use another representative ASU or define a weather-extension policy."
    )

print("\n===== TARGET CONTRACT =====")
print("ASU                 :", TARGET_ASU)
print("Age proxy (P50)     :", age_proxy_yr, "yr")
print("Reference year      :", reference_year)
print("Planting year proxy :", planting_year_proxy)
print("CHIRPS cell         :", chirps_id)
print("ERA5-Land cell      :", era5_id)
print("Centroid lat/lon    :", lat, lon)
print("Simulation          :", simulation_start.date(), "to", simulation_end.date())

# ------------------------------------------------------------
# 2. BUILD DAILY WEATHER JOIN
# ------------------------------------------------------------

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

chirps = chirps.loc[chirps["CHIRPS_CELL_ID"].astype(str) == chirps_id].copy()
era5 = era5.loc[era5["ERA5L_CELL_ID"].astype(str) == era5_id].copy()

chirps["DATE"] = pd.to_datetime(chirps["DATE"])
era5["DATE"] = pd.to_datetime(era5["DATE"])

if chirps["DATE"].duplicated().any():
    raise ValueError("Duplicate CHIRPS dates detected for target cell.")

if era5["DATE"].duplicated().any():
    raise ValueError("Duplicate ERA5-Land dates detected for target cell.")

weather = chirps.merge(
    era5,
    on="DATE",
    how="inner",
    validate="one_to_one",
)

weather = weather.sort_values("DATE").reset_index(drop=True)

expected_full = pd.date_range("2001-01-01", "2025-12-31", freq="D")

if len(weather) != len(expected_full):
    raise ValueError(
        f"Joined climate rows={len(weather)}, expected={len(expected_full)}"
    )

if not weather["DATE"].equals(pd.Series(expected_full)):
    missing_dates = expected_full.difference(weather["DATE"])
    raise ValueError(
        f"Climate calendar is not complete. Missing dates: {list(missing_dates[:10])}"
    )

required_vars = [
    "RAIN_MM_DAY",
    "RAD_MJ_M2_DAY",
    "TMIN_C",
    "TMAX_C",
    "TMEAN_C",
]

if weather[required_vars].isna().any().any():
    raise ValueError("Missing values found in APSIM weather forcing.")

if (weather["RAIN_MM_DAY"] < 0).any():
    raise ValueError("Negative CHIRPS rainfall detected.")

if (weather["RAD_MJ_M2_DAY"] < 0).any():
    raise ValueError("Negative solar radiation detected.")

if (weather["TMIN_C"] > weather["TMAX_C"]).any():
    raise ValueError("At least one day has Tmin > Tmax.")

# ------------------------------------------------------------
# 3. TAV / AMP + APSIM .MET
# ------------------------------------------------------------

# Long-term monthly climatology over the complete 2001–2025 record.
weather["MONTH"] = weather["DATE"].dt.month
monthly_clim = weather.groupby("MONTH")["TMEAN_C"].mean()

tav = float(monthly_clim.mean())
amp = float(monthly_clim.max() - monthly_clim.min())

met = weather.copy()
met["year"] = met["DATE"].dt.year.astype(int)
met["day"] = met["DATE"].dt.dayofyear.astype(int)
met["radn"] = met["RAD_MJ_M2_DAY"].astype(float)
met["maxt"] = met["TMAX_C"].astype(float)
met["mint"] = met["TMIN_C"].astype(float)
met["rain"] = met["RAIN_MM_DAY"].astype(float)

with open(MET_PATH, "w", encoding="utf-8", newline="\n") as f:
    f.write("[weather.met.weather]\n")
    f.write(f"latitude = {lat:.8f} (DECIMAL DEGREES)\n")
    f.write(f"longitude = {lon:.8f} (DECIMAL DEGREES)\n")
    f.write(f"tav = {tav:.6f} (oC)\n")
    f.write(f"amp = {amp:.6f} (oC)\n")
    f.write("year day radn maxt mint rain\n")
    f.write("() () (MJ/m^2/day) (oC) (oC) (mm)\n")

    for row in met[["year", "day", "radn", "maxt", "mint", "rain"]].itertuples(index=False):
        f.write(
            f"{row.year:4d} {row.day:3d} "
            f"{row.radn:10.5f} {row.maxt:9.4f} "
            f"{row.mint:9.4f} {row.rain:10.5f}\n"
        )

print("\n===== WEATHER ADAPTER =====")
print("Rows     :", len(met))
print("Start    :", met["DATE"].min().date())
print("End      :", met["DATE"].max().date())
print("TAV      :", round(tav, 4), "°C")
print("AMP      :", round(amp, 4), "°C")
print("Rain mean:", round(met["rain"].mean(), 4), "mm/day")
print("Rad mean :", round(met["radn"].mean(), 4), "MJ/m²/day")
print("MET file :", MET_PATH)

# ------------------------------------------------------------
# 4. CREATE MODIFIED APSIMX FROM OFFICIAL EXAMPLE
# ------------------------------------------------------------

with open(OFFICIAL_OILPALM, "r", encoding="utf-8-sig") as f:
    official = json.load(f)

clock_path, clock = find_node(official, "Models.Clock")
weather_path, weather_node = find_node(official, "Models.Climate.Weather")
manager_path, manager = find_node(
    official,
    "Models.Manager",
    "Palm Management",
)

if not all([clock, weather_node, manager]):
    raise RuntimeError(
        "Could not identify Clock, Weather, and Palm Management nodes."
    )

clock["Start"] = simulation_start.strftime("%Y-%m-%dT00:00:00")
clock["End"] = simulation_end.strftime("%Y-%m-%dT00:00:00")

# Absolute local path for this controlled smoke test.
weather_node["FileName"] = str(MET_PATH).replace("\\", "/")

set_manager_parameter(
    manager,
    "sowing_date",
    format_manager_date(simulation_start),
)
set_manager_parameter(
    manager,
    "population",
    BASELINE_POPULATION,
)

# Keep official cultivar and sowing_depth unchanged.
manager_params = {
    p["Key"]: p["Value"]
    for p in manager.get("Parameters", []) or []
}

print("\n===== APSIM ADAPTATION =====")
print("Clock.Start :", clock["Start"])
print("Clock.End   :", clock["End"])
print("Weather     :", weather_node["FileName"])
print("Management  :", manager_params)
print("NOTE        : Soil and cultivar remain official reference setup.")

# ------------------------------------------------------------
# 5. TWO ISOLATED RUNS
# ------------------------------------------------------------

for d in [RUN1, RUN2]:
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True, exist_ok=True)

    apsimx_out = d / "OilPalm_SIAK_1ASU_SMOKE_V1.apsimx"
    with open(apsimx_out, "w", encoding="utf-8") as f:
        json.dump(official, f, indent=2)

print("\n===== RUN 1 =====")
run1_file = RUN1 / "OilPalm_SIAK_1ASU_SMOKE_V1.apsimx"
run1 = run_apsim(run1_file, RUN1)

print("Return code :", run1["returncode"])
print("Elapsed sec :", round(run1["elapsed_sec"], 2))

if run1["stdout"]:
    print(run1["stdout"][-3500:])
if run1["stderr"]:
    print("STDERR:")
    print(run1["stderr"][-3500:])

print("\n===== RUN 2 =====")
run2_file = RUN2 / "OilPalm_SIAK_1ASU_SMOKE_V1.apsimx"
run2 = run_apsim(run2_file, RUN2)

print("Return code :", run2["returncode"])
print("Elapsed sec :", round(run2["elapsed_sec"], 2))

if run2["stdout"]:
    print(run2["stdout"][-3500:])
if run2["stderr"]:
    print("STDERR:")
    print(run2["stderr"][-3500:])

# ------------------------------------------------------------
# 6. OUTPUT / DETERMINISM / YIELD CHECK
# ------------------------------------------------------------

csv1 = {p.name: p for p in RUN1.glob("*.csv")}
csv2 = {p.name: p for p in RUN2.glob("*.csv")}

common = sorted(set(csv1) & set(csv2))
comparisons = []

for name in common:
    h1 = normalized_hash(csv1[name])
    h2 = normalized_hash(csv2[name])
    comparisons.append({
        "file": name,
        "run1_hash": h1,
        "run2_hash": h2,
        "equal": h1 == h2,
    })

csv_equal = (
    len(common) > 0
    and set(csv1) == set(csv2)
    and all(x["equal"] for x in comparisons)
)

annual_candidates = [
    p for p in csv1.values()
    if "annualoutput" in p.name.lower()
]

annual_summary = {}

if annual_candidates:
    annual_path = annual_candidates[0]
    annual_df = pd.read_csv(annual_path)

    yield_cols = [
        c for c in annual_df.columns
        if "annualyield" in str(c).lower()
    ]

    annual_summary["file"] = annual_path.name
    annual_summary["rows"] = int(len(annual_df))
    annual_summary["columns"] = list(map(str, annual_df.columns))
    annual_summary["yield_columns"] = yield_cols

    if yield_cols:
        ycol = yield_cols[0]
        y = pd.to_numeric(annual_df[ycol], errors="coerce")

        annual_summary["yield_nonmissing"] = int(y.notna().sum())
        annual_summary["yield_min"] = float(y.min()) if y.notna().any() else None
        annual_summary["yield_median"] = float(y.median()) if y.notna().any() else None
        annual_summary["yield_max"] = float(y.max()) if y.notna().any() else None
        annual_summary["yield_last"] = float(y.dropna().iloc[-1]) if y.notna().any() else None

yield_found = bool(annual_summary.get("yield_columns"))
yield_finite = (
    yield_found
    and annual_summary.get("yield_nonmissing", 0) > 0
    and np.isfinite(annual_summary.get("yield_last", np.nan))
)

status = (
    "PASS"
    if run1["returncode"] == 0
    and run2["returncode"] == 0
    and csv_equal
    and yield_finite
    else "REVIEW"
)

# ------------------------------------------------------------
# 7. AUDIT
# ------------------------------------------------------------

audit = {
    "gate": "40D03B_APSIM_SIAK_WEATHER_ADAPTER_1ASU_SMOKE",
    "status": status,
    "apsim_version": "2026.8.8099.0",
    "target_asu": TARGET_ASU,
    "age_proxy_yr": age_proxy_yr,
    "reference_year": reference_year,
    "planting_year_proxy": planting_year_proxy,
    "population_assumption": BASELINE_POPULATION,
    "chirps_cell_id": chirps_id,
    "era5l_cell_id": era5_id,
    "centroid_lat": lat,
    "centroid_lon": lon,
    "weather_start": str(weather["DATE"].min().date()),
    "weather_end": str(weather["DATE"].max().date()),
    "weather_rows": int(len(weather)),
    "met_tav_c": tav,
    "met_amp_c": amp,
    "met_path": str(MET_PATH),
    "simulation_start": str(simulation_start.date()),
    "simulation_end": str(simulation_end.date()),
    "soil_policy": "OFFICIAL_APSIM_OILPALM_REFERENCE_SOIL_NOT_SIAK_CALIBRATED",
    "cultivar_policy": "OFFICIAL_DAMI_REFERENCE",
    "run1": run1,
    "run2": run2,
    "csv_deterministic": csv_equal,
    "csv_comparisons": comparisons,
    "annual_output_summary": annual_summary,
    "interpretation": (
        "Technical compatibility smoke test only. "
        "A successful run demonstrates that the CHIRPS+ERA5-Land Siak forcing "
        "can drive APSIM OilPalm under the reference soil/cultivar configuration. "
        "It is not local yield validation."
    ),
}

AUDIT_JSON.write_text(
    json.dumps(audit, indent=2, default=str),
    encoding="utf-8",
)

print("\n===== OUTPUT / QC =====")
print("Common CSVs       :", common)
print("CSV deterministic :", csv_equal)
print("Annual summary    :", annual_summary)

print("\n====================================================")
print("40D03B FINISHED")
print("====================================================")
print("Status             :", status)
print("Target ASU         :", TARGET_ASU)
print("Age proxy          :", age_proxy_yr)
print("Planting year proxy:", planting_year_proxy)
print("CHIRPS             :", chirps_id)
print("ERA5-Land          :", era5_id)
print("Weather rows       :", len(weather))
print("Run1 RC            :", run1["returncode"])
print("Run2 RC            :", run2["returncode"])
print("CSV deterministic  :", csv_equal)
print("Yield found        :", yield_found)
print("Audit JSON         :", AUDIT_JSON)

if status == "PASS":
    print(
        "Next               : 40D03C representative APSIM benchmark scenario design."
    )
else:
    print(
        "Next               : Review the printed APSIM/weather/output issue before 40D03C."
    )

print("====================================================")
