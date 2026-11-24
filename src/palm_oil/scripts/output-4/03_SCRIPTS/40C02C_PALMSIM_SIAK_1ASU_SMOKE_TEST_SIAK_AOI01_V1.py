# ============================================================
# OUTPUT 4 / 40C02C
# PALMSIM SIAK 1-ASU WEATHER/AGE SMOKE TEST + DETERMINISM
# SIAK_AOI01
#
# RUN FROM JUPYTER VIA subprocess.
#
# PURPOSE
# 1) Select one strong, eligible ASU (age proxy available).
# 2) Join its locked CHIRPS + ERA5-Land native-cell weather.
# 3) Use the exact official PALMSIM API captured in 40C02B:
#       from palmsim import PalmField
#       p = PalmField(year_of_planting=...)
#       p.weather.radiation_series = ...
#       p.weather.rainfall_series = ...
#       df = p.run(duration=...)
# 4) Run the SAME ASU twice.
# 5) Confirm exact deterministic equality.
#
# IMPORTANT
# - This is the Siak adapter smoke test, NOT the 654-ASU batch yet.
# - Age is an event-age proxy; inferred year is NOT a confirmed planting year.
# - Density / soil-depth sensitivity is NOT activated in this step.
#   Their exact parameter contract is frozen in the next gate.
# - CHIRPS = primary rainfall.
# - ERA5-Land = radiation source here.
# - No missing-weather fallback is allowed inside the simulated period.
# ============================================================

from pathlib import Path
import os
import sys
import json
import hashlib
import traceback
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

OUT_RUN1 = WORKDIR / "40C02C_PALMSIM_SIAK_SMOKE_RUN1_SIAK_AOI01_V1.csv"
OUT_RUN2 = WORKDIR / "40C02C_PALMSIM_SIAK_SMOKE_RUN2_SIAK_AOI01_V1.csv"
OUT_WEATHER = WORKDIR / "40C02C_PALMSIM_SIAK_SMOKE_WEATHER_SIAK_AOI01_V1.csv"
OUT_SELECTED = WORKDIR / "40C02C_PALMSIM_SIAK_SMOKE_SELECTED_ASU_SIAK_AOI01_V1.csv"
OUT_QC = WORKDIR / "40C02C_PALMSIM_SIAK_SMOKE_TEST_QC_SIAK_AOI01_V1.json"

REFERENCE_YEAR = 2025

print("====================================================")
print("40C02C — PALMSIM SIAK 1-ASU SMOKE TEST")
print("====================================================")
print("Python :", sys.executable)
print("Workdir:", WORKDIR)

for p in [REG, ELIGIBLE_FILE, CHIRPS_FILE, ERA5_FILE]:
    if not p.exists():
        raise FileNotFoundError(f"Missing required input: {p}")

# ------------------------------------------------------------
# 1. REGISTER PALMSIM WORKING SOURCE
# ------------------------------------------------------------

registration = json.loads(REG.read_text(encoding="utf-8"))
working_root = Path(registration["working_root"])

palmsim_roots = list(working_root.rglob("palmsim-master"))
if not palmsim_roots:
    raise FileNotFoundError("Could not locate palmsim-master in working source.")

palmsim_master = palmsim_roots[0]
palmsim_pkg_parent = palmsim_master / "PalmSim"

# Match the official notebook path setup.
for p in [str(palmsim_pkg_parent), str(palmsim_master)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from palmsim import PalmField

print("PALMSIM master:", palmsim_master)
print("PalmField import: PASS")

# ------------------------------------------------------------
# 2. SELECT ONE STRONG ELIGIBLE ASU
# ------------------------------------------------------------

eligible = pd.read_csv(ELIGIBLE_FILE)

required = [
    "UNIT_ID",
    "AGE_PROXY_YR",
    "CHIRPS_CELL_ID",
    "ERA5L_CELL_ID",
    "ASU_LATITUDE",
]
missing = [c for c in required if c not in eligible.columns]
if missing:
    raise ValueError(f"Missing eligible-ASU columns: {missing}")

eligible["AGE_PROXY_YR"] = pd.to_numeric(
    eligible["AGE_PROXY_YR"], errors="coerce"
)

if "AGE_VALID_FRACTION" in eligible.columns:
    eligible["AGE_VALID_FRACTION"] = pd.to_numeric(
        eligible["AGE_VALID_FRACTION"], errors="coerce"
    )
else:
    eligible["AGE_VALID_FRACTION"] = np.nan

# Prefer a mature but climate-period-safe ASU around the AOI median age.
# This avoids PALMSIM's missing-date fallback before 2001.
cand = eligible[
    eligible["AGE_PROXY_YR"].between(10, 20, inclusive="both")
].copy()

if len(cand) == 0:
    cand = eligible[
        eligible["AGE_PROXY_YR"].between(5, 24, inclusive="both")
    ].copy()

if len(cand) == 0:
    raise RuntimeError(
        "No PALMSIM-eligible ASU has an age proxy safely inside 2001-2025."
    )

cand["AGE_DISTANCE_FROM_16"] = (
    cand["AGE_PROXY_YR"] - 16.0
).abs()

cand = cand.sort_values(
    ["AGE_VALID_FRACTION", "AGE_DISTANCE_FROM_16", "UNIT_ID"],
    ascending=[False, True, True],
    na_position="last"
)

row = cand.iloc[0].copy()

unit_id = str(row["UNIT_ID"])
age_proxy = float(row["AGE_PROXY_YR"])
age_model_years = int(round(age_proxy))

year_of_planting_proxy = int(
    REFERENCE_YEAR - age_model_years
)

if year_of_planting_proxy < 2001:
    raise RuntimeError(
        f"Selected ASU implies year {year_of_planting_proxy}, "
        "before available climate forcing."
    )

duration_days = int(age_model_years * 365)

model_start = pd.Timestamp(
    year=year_of_planting_proxy,
    month=1,
    day=1
)
model_end = model_start + pd.Timedelta(
    days=duration_days - 1
)

if model_end > pd.Timestamp("2025-12-31"):
    raise RuntimeError(
        f"Smoke-test model end {model_end.date()} exceeds climate period."
    )

chirps_id = str(row["CHIRPS_CELL_ID"])
era_id = str(row["ERA5L_CELL_ID"])
latitude = float(row["ASU_LATITUDE"])

print("\nSelected ASU:")
print("  UNIT_ID                 :", unit_id)
print("  Age proxy (yr)          :", age_proxy)
print("  Model age rounded (yr)  :", age_model_years)
print("  Year-of-planting proxy  :", year_of_planting_proxy)
print("  Simulation period       :", model_start.date(), "->", model_end.date())
print("  Duration                :", duration_days, "days")
print("  CHIRPS cell             :", chirps_id)
print("  ERA5-Land cell          :", era_id)
print("  Latitude                :", latitude)

# ------------------------------------------------------------
# 3. BUILD EXACT DAILY WEATHER SERIES
# ------------------------------------------------------------

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
        "TMEAN_C",
        "RH_MEAN_PCT",
        "WIND_MEAN_MS",
    ]
)

chirps["DATE"] = pd.to_datetime(chirps["DATE"]).dt.normalize()
era["DATE"] = pd.to_datetime(era["DATE"]).dt.normalize()

chirps["CHIRPS_CELL_ID"] = chirps["CHIRPS_CELL_ID"].astype(str)
era["ERA5L_CELL_ID"] = era["ERA5L_CELL_ID"].astype(str)

c = chirps[
    chirps["CHIRPS_CELL_ID"] == chirps_id
][["DATE", "RAIN_MM_DAY"]].copy()

e = era[
    era["ERA5L_CELL_ID"] == era_id
][[
    "DATE",
    "RAD_MJ_M2_DAY",
    "TMEAN_C",
    "RH_MEAN_PCT",
    "WIND_MEAN_MS",
]].copy()

weather = c.merge(
    e,
    on="DATE",
    how="inner",
    validate="one_to_one"
)

weather = weather[
    weather["DATE"].between(model_start, model_end)
].copy()

weather = weather.sort_values("DATE").reset_index(drop=True)

expected_dates = pd.date_range(
    model_start,
    model_end,
    freq="D"
)

if len(weather) != duration_days:
    raise RuntimeError(
        f"Weather row count {len(weather)} != duration {duration_days}."
    )

if not weather["DATE"].equals(
    pd.Series(expected_dates, name="DATE")
):
    # Stronger direct set equality check in case Series metadata differs.
    if list(weather["DATE"]) != list(expected_dates):
        raise RuntimeError(
            "Weather dates are not a complete contiguous daily calendar."
        )

weather_required = [
    "RAIN_MM_DAY",
    "RAD_MJ_M2_DAY",
    "TMEAN_C",
    "RH_MEAN_PCT",
    "WIND_MEAN_MS",
]

if weather[weather_required].isna().any().any():
    raise RuntimeError(
        "Missing weather exists inside simulated period. "
        "PALMSIM fallback is not allowed for smoke test."
    )

if (weather["RAIN_MM_DAY"] < 0).any():
    raise RuntimeError("Negative CHIRPS rainfall detected.")

if (weather["RAD_MJ_M2_DAY"] < 0).any():
    raise RuntimeError("Negative ERA5-Land radiation detected.")

weather.to_csv(
    OUT_WEATHER,
    index=False,
    encoding="utf-8-sig"
)

print("\nWeather adapter:")
print("  Rows                    :", len(weather))
print("  Missing required values :", int(weather[weather_required].isna().sum().sum()))
print("  Complete calendar       : True")

# ------------------------------------------------------------
# 4. EXACT OFFICIAL PALMSIM API ADAPTER
# ------------------------------------------------------------

weather_indexed = weather.set_index("DATE")

rain_series = weather_indexed["RAIN_MM_DAY"].copy()
radiation_series = weather_indexed["RAD_MJ_M2_DAY"].copy()

def make_model():
    # Exact constructor captured from official notebook.
    p = PalmField(
        year_of_planting=year_of_planting_proxy
    )

    # Exact weather coupling captured from official notebook.
    p.weather.radiation_series = radiation_series
    p.weather.rainfall_series = rain_series

    # Latitude is applied ONLY if the registered PALMSIM object
    # explicitly exposes a writable latitude attribute.
    latitude_targets = []

    if hasattr(p, "latitude"):
        try:
            p.latitude = latitude
            latitude_targets.append("PalmField.latitude")
        except Exception:
            pass

    if hasattr(p, "weather") and hasattr(p.weather, "latitude"):
        try:
            p.weather.latitude = latitude
            latitude_targets.append("PalmField.weather.latitude")
        except Exception:
            pass

    return p, latitude_targets

# ------------------------------------------------------------
# 5. RUN TWICE
# ------------------------------------------------------------

run_outputs = []
latitude_targets_final = []

for run_no in [1, 2]:
    print(f"\nRunning Siak PALMSIM smoke test {run_no}/2 ...")

    model, lat_targets = make_model()

    if run_no == 1:
        latitude_targets_final = lat_targets

    # Exact run contract from official notebook.
    df = model.run(
        duration=duration_days
    )

    if not isinstance(df, pd.DataFrame):
        raise TypeError(
            f"PALMSIM run returned {type(df)}, expected pandas DataFrame."
        )

    if len(df) == 0:
        raise RuntimeError("PALMSIM returned an empty DataFrame.")

    run_outputs.append(df.copy())

    print("  rows   :", len(df))
    print("  columns:", len(df.columns))

print("  latitude target(s):", latitude_targets_final or "not exposed by API")

# ------------------------------------------------------------
# 6. DETERMINISM CHECK
# ------------------------------------------------------------

df1 = run_outputs[0]
df2 = run_outputs[1]

same_index = df1.index.equals(df2.index)
same_columns = list(df1.columns) == list(df2.columns)

numeric_cols = [
    c for c in df1.columns
    if pd.api.types.is_numeric_dtype(df1[c])
    and c in df2.columns
]

numeric_equal = True
max_abs_diff = 0.0

for col in numeric_cols:
    a = pd.to_numeric(df1[col], errors="coerce").to_numpy()
    b = pd.to_numeric(df2[col], errors="coerce").to_numpy()

    if a.shape != b.shape:
        numeric_equal = False
        break

    both_nan = np.isnan(a) & np.isnan(b)
    valid = ~(both_nan)

    if valid.any():
        diff = np.abs(a[valid] - b[valid])
        finite_diff = diff[np.isfinite(diff)]

        if len(finite_diff):
            max_abs_diff = max(
                max_abs_diff,
                float(finite_diff.max())
            )

        if not np.array_equal(
            a[valid],
            b[valid],
            equal_nan=True
        ):
            numeric_equal = False

deterministic_equal = bool(
    same_index
    and same_columns
    and numeric_equal
)

# Stable CSV hashes.
csv1 = df1.to_csv(index=True)
csv2 = df2.to_csv(index=True)

hash1 = hashlib.sha256(
    csv1.encode("utf-8")
).hexdigest()

hash2 = hashlib.sha256(
    csv2.encode("utf-8")
).hexdigest()

print("\nDeterminism:")
print("  same index      :", same_index)
print("  same columns    :", same_columns)
print("  numeric exact   :", numeric_equal)
print("  max abs diff    :", max_abs_diff)
print("  run 1 SHA256    :", hash1)
print("  run 2 SHA256    :", hash2)
print("  exact model pass:", deterministic_equal)

# ------------------------------------------------------------
# 7. FFB OUTPUT CHECK
# ------------------------------------------------------------

ffb_candidates = [
    c for c in df1.columns
    if "ffb" in str(c).lower()
    and "production" in str(c).lower()
]

if not ffb_candidates:
    ffb_candidates = [
        c for c in df1.columns
        if "ffb" in str(c).lower()
    ]

ffb_col = ffb_candidates[0] if ffb_candidates else None

ffb_summary = {
    "source_column": ffb_col,
    "raw_last_finite": None,
    "canonical_t_fresh_ffb_ha_yr_last": None,
    "unit_guardrail": (
        "PALMSIM 2.5.2 source audit previously found the FFB "
        "calculation to be kg fresh mass/ha/year despite an inconsistent "
        "t/ha/yr column label. Canonical Output-4 conversion is raw / 1000."
    ),
}

if ffb_col is not None:
    s = pd.to_numeric(
        df1[ffb_col],
        errors="coerce"
    ).dropna()

    if len(s):
        raw_last = float(s.iloc[-1])
        ffb_summary["raw_last_finite"] = raw_last
        ffb_summary[
            "canonical_t_fresh_ffb_ha_yr_last"
        ] = raw_last / 1000.0

print("\nFFB output:")
print("  source column :", ffb_col)
print(
    "  canonical last:",
    ffb_summary["canonical_t_fresh_ffb_ha_yr_last"],
    "t fresh FFB/ha/yr"
)

# ------------------------------------------------------------
# 8. SAVE OUTPUTS + SELECTED ASU
# ------------------------------------------------------------

df1.to_csv(
    OUT_RUN1,
    index=True,
    encoding="utf-8-sig"
)
df2.to_csv(
    OUT_RUN2,
    index=True,
    encoding="utf-8-sig"
)

selected_cols = [
    c for c in [
        "UNIT_ID",
        "ASU_LATITUDE",
        "ASU_LONGITUDE",
        "AGE_PROXY_YR",
        "AGE_VALID_FRACTION",
        "AGE_SUPPORT_FLAG",
        "SAND_0_100_PCT",
        "SILT_0_100_PCT",
        "CLAY_0_100_PCT",
        "CHIRPS_CELL_ID",
        "ERA5L_CELL_ID",
        "CLIMATE_PAIR_ID",
    ]
    if c in eligible.columns
]

selected = pd.DataFrame([row[selected_cols]])
selected["MODEL_AGE_YR_ROUNDED"] = age_model_years
selected["YEAR_OF_PLANTING_PROXY"] = year_of_planting_proxy
selected["SIMULATION_START"] = model_start.strftime("%Y-%m-%d")
selected["SIMULATION_END"] = model_end.strftime("%Y-%m-%d")
selected["DURATION_DAYS"] = duration_days

selected.to_csv(
    OUT_SELECTED,
    index=False,
    encoding="utf-8-sig"
)

# ------------------------------------------------------------
# 9. FINAL GATE
# ------------------------------------------------------------

smoke_pass = bool(
    len(df1) > 0
    and deterministic_equal
    and ffb_col is not None
    and len(weather) == duration_days
)

status = "PASS" if smoke_pass else "CHECK"

next_gate = (
    "40C02D freeze exact PALMSIM structural parameter contract "
    "(density, soil depth/texture, latitude/weather fields), "
    "then activate P00-P04 sensitivity scenarios."
    if status == "PASS"
    else
    "Inspect smoke-test failures before any PALMSIM batch execution."
)

qc = {
    "gate": "40C02C",
    "status": status,

    "selected_asu": {
        "UNIT_ID": unit_id,
        "age_proxy_years": age_proxy,
        "model_age_years_rounded": age_model_years,
        "year_of_planting_proxy": year_of_planting_proxy,
        "year_of_planting_interpretation": (
            "Derived from Output-2 event-age proxy; "
            "not a confirmed estate planting year."
        ),
        "CHIRPS_CELL_ID": chirps_id,
        "ERA5L_CELL_ID": era_id,
        "latitude": latitude,
    },

    "simulation": {
        "start": model_start.strftime("%Y-%m-%d"),
        "end": model_end.strftime("%Y-%m-%d"),
        "duration_days": duration_days,
        "weather_rows": int(len(weather)),
        "missing_weather_values": int(
            weather[weather_required].isna().sum().sum()
        ),
        "fallback_allowed": False,
    },

    "api_contract_used": {
        "constructor": "PalmField(year_of_planting=...)",
        "radiation": "p.weather.radiation_series",
        "rainfall": "p.weather.rainfall_series",
        "run": "p.run(duration=...)",
        "latitude_targets_applied": latitude_targets_final,
    },

    "determinism": {
        "same_index": same_index,
        "same_columns": same_columns,
        "numeric_exact": numeric_equal,
        "max_abs_difference": max_abs_diff,
        "run1_sha256": hash1,
        "run2_sha256": hash2,
        "pass": deterministic_equal,
    },

    "ffb_output": ffb_summary,

    "scientific_guardrails": [
        "CHIRPS v2 Final is primary rainfall.",
        "ERA5-Land provides radiation for this PALMSIM adapter.",
        "Temperature/RH/wind are preserved in the climate store but are not "
        "forced into PALMSIM unless the exact PALMSIM source contract supports them.",
        "No missing-date weather fallback is allowed in the simulation window.",
        "Age-derived planting year is a proxy, not confirmed planting year.",
        "No actual-yield accuracy claim is made.",
        "Density and soil-depth scenario assumptions are not yet activated in 40C02C.",
    ],

    "next_gate": next_gate,
}

OUT_QC.write_text(
    json.dumps(qc, indent=2),
    encoding="utf-8"
)

print("\n====================================================")
print("40C02C FINISHED")
print("====================================================")
print("Status:", status)
print("UNIT_ID:", unit_id)
print("Age proxy:", age_proxy, "yr")
print("Year-of-planting proxy:", year_of_planting_proxy)
print("Weather complete:", len(weather), "/", duration_days)
print("Run 1 rows:", len(df1))
print("Run 2 rows:", len(df2))
print("Deterministic equality:", deterministic_equal)
print("Max absolute difference:", max_abs_diff)
print("FFB source column:", ffb_col)
print(
    "Canonical final FFB potential:",
    ffb_summary["canonical_t_fresh_ffb_ha_yr_last"],
    "t fresh FFB/ha/yr"
)
print("Run 1 CSV:", OUT_RUN1)
print("Run 2 CSV:", OUT_RUN2)
print("Weather CSV:", OUT_WEATHER)
print("Selected ASU:", OUT_SELECTED)
print("QC JSON:", OUT_QC)
print("Next:", next_gate)
print("====================================================")
