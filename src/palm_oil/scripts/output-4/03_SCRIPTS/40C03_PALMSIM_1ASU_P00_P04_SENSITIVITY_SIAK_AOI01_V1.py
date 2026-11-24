# ============================================================
# OUTPUT 4 / 40C03
# PALMSIM P00-P04 SINGLE-ASU SENSITIVITY TEST
# SIAK_AOI01
#
# RUN FROM JUPYTER VIA subprocess.
#
# PURPOSE
# 1) Use the SAME Siak ASU that passed 40C02C.
# 2) Run P00-P04 with only CONFIRMED PALMSIM setters:
#       PalmField.planting_density
#       PalmField.soil.soil_depth
# 3) Run every scenario twice to confirm determinism.
# 4) Check whether density and soil-depth assumptions actually
#    change model outputs before any 654-ASU batch.
#
# IMPORTANT
# - SoilGrids sand/silt/clay are NOT injected into PALMSIM.
# - Density and soil depth remain scenario assumptions.
# - FFB is interpreted as MODELLED PRODUCTIVITY POTENTIAL,
#   not observed/validated actual yield.
# ============================================================

from pathlib import Path
import os
import sys
import json
import hashlib
import warnings

import numpy as np
import pandas as pd

WORKDIR = Path(
    r"C:\Users\user\Documents\KERJA\SPATIAL DATA ANALYST INTERN\04_YIELD"
)
os.chdir(WORKDIR)

REG = WORKDIR / "40C01B_PALMSIM_SOURCE_REGISTRATION_SIAK_AOI01_V1.json"
SELECTED = WORKDIR / "40C02C_PALMSIM_SIAK_SMOKE_SELECTED_ASU_SIAK_AOI01_V1.csv"
WEATHER_FILE = WORKDIR / "40C02C_PALMSIM_SIAK_SMOKE_WEATHER_SIAK_AOI01_V1.csv"
SCENARIO_FILE = WORKDIR / "40C01_PALMSIM_SENSITIVITY_SCENARIOS_SIAK_AOI01_V1.csv"

OUT_SUMMARY = WORKDIR / "40C03_PALMSIM_1ASU_SENSITIVITY_SUMMARY_SIAK_AOI01_V1.csv"
OUT_QC = WORKDIR / "40C03_PALMSIM_1ASU_SENSITIVITY_QC_SIAK_AOI01_V1.json"
OUT_RUN_DIR = WORKDIR / "40C03_PALMSIM_1ASU_RUNS"
OUT_RUN_DIR.mkdir(parents=True, exist_ok=True)

print("====================================================")
print("40C03 — PALMSIM P00-P04 SINGLE-ASU SENSITIVITY")
print("====================================================")
print("Python :", sys.executable)
print("Workdir:", WORKDIR)

for p in [REG, SELECTED, WEATHER_FILE, SCENARIO_FILE]:
    if not p.exists():
        raise FileNotFoundError(f"Missing required input: {p}")

# ------------------------------------------------------------
# 1. LOAD PALMSIM
# ------------------------------------------------------------

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

# ------------------------------------------------------------
# 2. LOAD SAME ASU + WEATHER USED IN 40C02C
# ------------------------------------------------------------

selected = pd.read_csv(SELECTED)
if len(selected) != 1:
    raise ValueError("40C02C selected-ASU file must contain exactly one row.")

row = selected.iloc[0]

unit_id = str(row["UNIT_ID"])
year_of_planting = int(row["YEAR_OF_PLANTING_PROXY"])
latitude = float(row["ASU_LATITUDE"])
duration_days = int(row["DURATION_DAYS"])

weather = pd.read_csv(WEATHER_FILE)
weather["DATE"] = pd.to_datetime(weather["DATE"]).dt.normalize()
weather = weather.sort_values("DATE").reset_index(drop=True)

required_weather = ["RAIN_MM_DAY", "RAD_MJ_M2_DAY"]
if weather[required_weather].isna().any().any():
    raise RuntimeError("Missing weather in 40C02C frozen smoke-test weather.")

if len(weather) != duration_days:
    raise RuntimeError(
        f"Weather rows {len(weather)} != duration days {duration_days}"
    )

weather_idx = weather.set_index("DATE")
rain_series = weather_idx["RAIN_MM_DAY"].copy()
radiation_series = weather_idx["RAD_MJ_M2_DAY"].copy()

print("\nFrozen smoke-test ASU:")
print("  UNIT_ID                :", unit_id)
print("  Year-of-planting proxy :", year_of_planting)
print("  Duration days          :", duration_days)
print("  Latitude               :", latitude)
print("  Weather rows           :", len(weather))

# ------------------------------------------------------------
# 3. LOAD FROZEN P00-P04 SCENARIOS
# ------------------------------------------------------------

scenarios = pd.read_csv(SCENARIO_FILE)

required_scenario_cols = [
    "SCENARIO_ID",
    "SCENARIO_ROLE",
    "PALM_DENSITY_PALMS_HA",
    "SOIL_DEPTH_M",
]

missing = [c for c in required_scenario_cols if c not in scenarios.columns]
if missing:
    raise ValueError(f"Scenario file missing columns: {missing}")

expected_ids = [
    "P00_BASE",
    "P01_DENS_LOW",
    "P02_DENS_HIGH",
    "P03_DEPTH_SHALLOW",
    "P04_DEPTH_DEEP",
]

actual_ids = scenarios["SCENARIO_ID"].astype(str).tolist()

if actual_ids != expected_ids:
    raise ValueError(
        f"Scenario order/content changed.\nExpected: {expected_ids}\nActual: {actual_ids}"
    )

print("\nScenario matrix:")
print(
    scenarios[
        [
            "SCENARIO_ID",
            "PALM_DENSITY_PALMS_HA",
            "SOIL_DEPTH_M",
        ]
    ].to_string(index=False)
)

# ------------------------------------------------------------
# 4. HELPERS
# ------------------------------------------------------------

def canonical_ffb_col(df):
    preferred = "generative_FFB_production (t/ha/yr)"
    if preferred in df.columns:
        return preferred

    candidates = [
        c for c in df.columns
        if "ffb" in str(c).lower()
        and "production" in str(c).lower()
    ]
    if not candidates:
        candidates = [c for c in df.columns if "ffb" in str(c).lower()]

    return candidates[0] if candidates else None


def frame_hash(df):
    text = df.to_csv(index=True)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def numeric_exact_equal(a, b):
    if not a.index.equals(b.index):
        return False, None
    if list(a.columns) != list(b.columns):
        return False, None

    max_diff = 0.0

    for col in a.columns:
        if not (
            pd.api.types.is_numeric_dtype(a[col])
            and pd.api.types.is_numeric_dtype(b[col])
        ):
            continue

        av = pd.to_numeric(a[col], errors="coerce").to_numpy(dtype=float)
        bv = pd.to_numeric(b[col], errors="coerce").to_numpy(dtype=float)

        if av.shape != bv.shape:
            return False, None

        same_nan = np.isnan(av) & np.isnan(bv)
        compare = ~same_nan

        if compare.any():
            if not np.array_equal(av[compare], bv[compare], equal_nan=True):
                diff = np.abs(av[compare] - bv[compare])
                finite = diff[np.isfinite(diff)]
                if len(finite):
                    max_diff = max(max_diff, float(finite.max()))
                return False, max_diff

    return True, max_diff


def make_model(density, soil_depth):
    p = PalmField(year_of_planting=year_of_planting)

    # Confirmed operational parameters from 40C02B/C
    p.latitude = latitude
    p.weather.radiation_series = radiation_series
    p.weather.rainfall_series = rain_series

    # Confirmed writable structural paths from 40C02D/E
    before = {
        "planting_density": getattr(p, "planting_density", None),
        "soil_depth": getattr(p.soil, "soil_depth", None),
        "plant_available_water_content": getattr(
            p.soil, "_plant_available_water_content", None
        ),
        "available_water": getattr(p.soil, "available_water", None),
    }

    p.planting_density = float(density)
    p.soil.soil_depth = float(soil_depth)

    after = {
        "planting_density": getattr(p, "planting_density", None),
        "soil_depth": getattr(p.soil, "soil_depth", None),
        "plant_available_water_content": getattr(
            p.soil, "_plant_available_water_content", None
        ),
        "available_water": getattr(p.soil, "available_water", None),
    }

    return p, before, after


# ------------------------------------------------------------
# 5. RUN EVERY SCENARIO TWICE
# ------------------------------------------------------------

records = []
run_frames = {}

# Keep the deprecated pandas warning visible only once in console context.
warnings.simplefilter("default", FutureWarning)

for _, srow in scenarios.iterrows():
    sid = str(srow["SCENARIO_ID"])
    role = str(srow["SCENARIO_ROLE"])
    density = float(srow["PALM_DENSITY_PALMS_HA"])
    soil_depth = float(srow["SOIL_DEPTH_M"])

    print(f"\nRunning {sid}: density={density}, depth={soil_depth} m")

    scenario_runs = []
    state_records = []

    for repeat in [1, 2]:
        model, before, after = make_model(density, soil_depth)

        df = model.run(duration=duration_days)

        if not isinstance(df, pd.DataFrame) or len(df) == 0:
            raise RuntimeError(f"{sid} repeat {repeat}: empty/invalid PALMSIM output.")

        ffb_col = canonical_ffb_col(df)
        if ffb_col is None:
            raise RuntimeError(f"{sid}: FFB output column not found.")

        scenario_runs.append(df.copy())
        state_records.append({
            "before": before,
            "after": after,
        })

        out_csv = OUT_RUN_DIR / (
            f"40C03_{sid}_REPEAT{repeat}_{unit_id.replace(',', '_')}.csv"
        )
        df.to_csv(out_csv, index=True, encoding="utf-8-sig")

        print(
            f"  repeat {repeat}: rows={len(df)}, "
            f"hash={frame_hash(df)[:16]}..."
        )

    df1, df2 = scenario_runs
    exact_equal, max_diff = numeric_exact_equal(df1, df2)

    ffb_col = canonical_ffb_col(df1)
    raw = pd.to_numeric(df1[ffb_col], errors="coerce").dropna()

    if len(raw) == 0:
        raise RuntimeError(f"{sid}: FFB column contains no finite numeric output.")

    # Source audit established raw PALMSIM FFB as kg fresh mass/ha/yr,
    # despite inconsistent t/ha/yr label. Canonical conversion = /1000.
    canonical = raw / 1000.0

    final_ffb = float(canonical.iloc[-1])

    # PALMSIM returns about one record per 10 model-days.
    # Use trailing ~365 model-days as a stable summary where possible.
    trailing_n = min(36, len(canonical))
    trailing_mean = float(canonical.tail(trailing_n).mean())
    trailing_median = float(canonical.tail(trailing_n).median())

    before = state_records[0]["before"]
    after = state_records[0]["after"]

    rec = {
        "SCENARIO_ID": sid,
        "SCENARIO_ROLE": role,
        "UNIT_ID": unit_id,

        "REQUESTED_DENSITY_PALMS_HA": density,
        "REQUESTED_SOIL_DEPTH_M": soil_depth,

        "MODEL_DENSITY_BEFORE": before["planting_density"],
        "MODEL_DENSITY_AFTER_SET": after["planting_density"],

        "MODEL_SOIL_DEPTH_BEFORE_M": before["soil_depth"],
        "MODEL_SOIL_DEPTH_AFTER_SET_M": after["soil_depth"],

        "PAWC_BEFORE": before["plant_available_water_content"],
        "PAWC_AFTER_DEPTH_SET": after["plant_available_water_content"],

        "AVAILABLE_WATER_BEFORE": before["available_water"],
        "AVAILABLE_WATER_AFTER_DEPTH_SET": after["available_water"],

        "OUTPUT_ROWS": len(df1),
        "FFB_SOURCE_COLUMN": ffb_col,

        "FINAL_FFB_POTENTIAL_T_HA_YR": final_ffb,
        "TRAILING_MODEL_YEAR_MEAN_T_HA_YR": trailing_mean,
        "TRAILING_MODEL_YEAR_MEDIAN_T_HA_YR": trailing_median,

        "DETERMINISTIC_EQUAL": bool(exact_equal),
        "MAX_ABS_NUMERIC_DIFF": 0.0 if max_diff is None else float(max_diff),
        "RUN1_SHA256": frame_hash(df1),
        "RUN2_SHA256": frame_hash(df2),
    }

    records.append(rec)
    run_frames[sid] = df1

summary = pd.DataFrame(records)

# ------------------------------------------------------------
# 6. BASELINE-RELATIVE RESPONSE
# ------------------------------------------------------------

base = summary.loc[
    summary["SCENARIO_ID"] == "P00_BASE"
].iloc[0]

base_final = float(base["FINAL_FFB_POTENTIAL_T_HA_YR"])
base_trailing = float(base["TRAILING_MODEL_YEAR_MEAN_T_HA_YR"])

summary["DELTA_FINAL_VS_BASE_T_HA_YR"] = (
    summary["FINAL_FFB_POTENTIAL_T_HA_YR"] - base_final
)

summary["DELTA_TRAILING_MEAN_VS_BASE_T_HA_YR"] = (
    summary["TRAILING_MODEL_YEAR_MEAN_T_HA_YR"] - base_trailing
)

if base_final != 0:
    summary["DELTA_FINAL_VS_BASE_PCT"] = (
        100.0
        * summary["DELTA_FINAL_VS_BASE_T_HA_YR"]
        / base_final
    )
else:
    summary["DELTA_FINAL_VS_BASE_PCT"] = np.nan

# Response detection with tiny numerical tolerance.
TOL = 1e-9

density_rows = summary[
    summary["SCENARIO_ID"].isin(["P01_DENS_LOW", "P02_DENS_HIGH"])
]

depth_rows = summary[
    summary["SCENARIO_ID"].isin(["P03_DEPTH_SHALLOW", "P04_DEPTH_DEEP"])
]

density_effect_detected = bool(
    (
        density_rows["DELTA_TRAILING_MEAN_VS_BASE_T_HA_YR"].abs()
        > TOL
    ).any()
)

depth_effect_detected = bool(
    (
        depth_rows["DELTA_TRAILING_MEAN_VS_BASE_T_HA_YR"].abs()
        > TOL
    ).any()
)

all_deterministic = bool(summary["DETERMINISTIC_EQUAL"].all())

all_finite_nonnegative = bool(
    np.isfinite(summary["FINAL_FFB_POTENTIAL_T_HA_YR"]).all()
    and (summary["FINAL_FFB_POTENTIAL_T_HA_YR"] >= 0).all()
    and np.isfinite(summary["TRAILING_MODEL_YEAR_MEAN_T_HA_YR"]).all()
    and (summary["TRAILING_MODEL_YEAR_MEAN_T_HA_YR"] >= 0).all()
)

# Check whether simply assigning soil_depth immediately changes
# available water state. If not, we flag it; this does NOT automatically
# mean soil depth has no model effect during run.
depth_state_changed_immediately = bool(
    (
        depth_rows["AVAILABLE_WATER_AFTER_DEPTH_SET"]
        - depth_rows["AVAILABLE_WATER_BEFORE"]
    ).abs().fillna(0).gt(TOL).any()
    or
    (
        depth_rows["PAWC_AFTER_DEPTH_SET"]
        - depth_rows["PAWC_BEFORE"]
    ).abs().fillna(0).gt(TOL).any()
)

# ------------------------------------------------------------
# 7. GATE
# ------------------------------------------------------------

if (
    all_deterministic
    and all_finite_nonnegative
    and density_effect_detected
    and depth_effect_detected
):
    status = "PASS"
    next_gate = (
        "40C04 batch PALMSIM P00-P04 across all 654 eligible ASUs "
        "using join-on-demand climate and the frozen density/depth scenarios."
    )

elif (
    all_deterministic
    and all_finite_nonnegative
    and density_effect_detected
    and not depth_effect_detected
):
    status = "PASS_DENSITY_ONLY_DEPTH_INACTIVE"
    next_gate = (
        "Do not batch soil-depth sensitivity yet. Freeze density sensitivity, "
        "then inspect PALMSIM soil-water initialization semantics before deciding "
        "whether soil depth belongs in the batch."
    )

elif all_deterministic and all_finite_nonnegative:
    status = "CHECK_PARAMETER_RESPONSE"
    next_gate = (
        "Model runs are stable, but one or more structural scenarios did not "
        "produce a detectable response. Inspect parameter semantics before batch."
    )

else:
    status = "CHECK"
    next_gate = (
        "Resolve determinism/numerical issues before any 654-ASU batch."
    )

# ------------------------------------------------------------
# 8. EXPORT
# ------------------------------------------------------------

summary.to_csv(
    OUT_SUMMARY,
    index=False,
    encoding="utf-8-sig"
)

qc = {
    "gate": "40C03",
    "status": status,

    "selected_asu": {
        "UNIT_ID": unit_id,
        "year_of_planting_proxy": year_of_planting,
        "latitude": latitude,
        "duration_days": duration_days,
    },

    "scenario_count": int(len(summary)),
    "repeat_runs_per_scenario": 2,
    "total_model_runs": int(len(summary) * 2),

    "checks": {
        "all_deterministic": all_deterministic,
        "all_final_outputs_finite_nonnegative": all_finite_nonnegative,
        "density_effect_detected": density_effect_detected,
        "soil_depth_effect_detected": depth_effect_detected,
        "soil_water_state_changed_immediately_after_depth_assignment":
            depth_state_changed_immediately,
    },

    "baseline": {
        "final_ffb_potential_t_ha_yr": base_final,
        "trailing_model_year_mean_t_ha_yr": base_trailing,
    },

    "soil_policy": {
        "sand_silt_clay_injected": False,
        "reason": (
            "40C02D/E found no safe public PALMSIM sand/silt/clay "
            "input contract. SoilGrids texture fractions remain contextual."
        ),
    },

    "scientific_guardrails": [
        "FFB is modelled productivity potential, not actual observed yield.",
        "Density and soil depth are scenario assumptions, not estate observations.",
        "Age-derived year of planting remains a proxy.",
        "CHIRPS is rainfall forcing; ERA5-Land is radiation forcing.",
        "No missing-weather fallback is permitted in the run period.",
        "No 654-ASU batch until this single-ASU sensitivity gate passes.",
    ],

    "next_gate": next_gate,
}

OUT_QC.write_text(
    json.dumps(qc, indent=2),
    encoding="utf-8"
)

# ------------------------------------------------------------
# 9. CONSOLE SUMMARY
# ------------------------------------------------------------

print("\n====================================================")
print("40C03 RESULTS")
print("====================================================")

print(
    summary[
        [
            "SCENARIO_ID",
            "REQUESTED_DENSITY_PALMS_HA",
            "REQUESTED_SOIL_DEPTH_M",
            "FINAL_FFB_POTENTIAL_T_HA_YR",
            "TRAILING_MODEL_YEAR_MEAN_T_HA_YR",
            "DELTA_TRAILING_MEAN_VS_BASE_T_HA_YR",
            "DETERMINISTIC_EQUAL",
        ]
    ].to_string(index=False)
)

print("\nResponse checks:")
print("  All deterministic              :", all_deterministic)
print("  All outputs finite/nonnegative :", all_finite_nonnegative)
print("  Density effect detected        :", density_effect_detected)
print("  Soil-depth effect detected     :", depth_effect_detected)
print("  Immediate soil-water state chg :", depth_state_changed_immediately)

print("\n====================================================")
print("40C03 FINISHED")
print("====================================================")
print("Status:", status)
print("Summary CSV:", OUT_SUMMARY)
print("QC JSON:", OUT_QC)
print("Scenario run folder:", OUT_RUN_DIR)
print("Next:", next_gate)
print("====================================================")
