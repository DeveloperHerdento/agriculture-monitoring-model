# ============================================================
# OUTPUT 4 / 40E02-V2
# FINAL MODEL ROLE + WALL-TO-WALL COVERAGE CONTRACT
# SIAK_AOI01
#
# PURE PYTHON STANDARD LIBRARY ONLY
# NO numpy / pandas / scipy
#
# IMPORTANT:
# - This stage DOES NOT rerun PALMSIM or APSIM.
# - This stage DOES NOT estimate fallback productivity yet.
# - This stage freezes:
#     (1) PALMSIM = primary process model,
#     (2) APSIM = representative benchmark,
#     (3) no model averaging / no bias correction,
#     (4) Output 4 spatial domain = all 820 ASUs,
#     (5) 654 direct-model pathway + 166 fallback pathway,
#     (6) no palm ASU may disappear simply because numeric age
#         is unavailable.
#
# Next:
# 40E03 = fallback productivity design/execution for the 166
# age-censored / unresolved ASUs.
# ============================================================

from pathlib import Path
import csv
import json
import math
import statistics

WORKDIR = Path(
    r"C:\Users\user\Documents\KERJA\SPATIAL DATA ANALYST INTERN\04_YIELD"
)

MASTER_ASU = WORKDIR / "40B04A_ASU_CLIMATE_CELL_MAPPING_SIAK_AOI01_V1.csv"
PAIR_MAP = WORKDIR / "40B04C_LITE_ASU_CLIMATE_PAIR_MAPPING_SIAK_AOI01_V1.csv"
PALMSIM_BASE = WORKDIR / "40C04A_DIRECT_P00_BASELINE_RESULTS_SIAK_AOI01_V1.csv"
APSIM_FROZEN = WORKDIR / "40D05_APSIM_REPRESENTATIVE_BENCHMARK_FROZEN_SIAK_AOI01_V1.csv"
COMP_48 = WORKDIR / "40E01A_V3_PALMSIM_APSIM_CORE_COMPARISON_SIAK_AOI01.csv"
AGE_DIAG = WORKDIR / "40E01B_AGE_DISCREPANCY_SUMMARY_SIAK_AOI01_V1.csv"
CLIMATE_DIAG = WORKDIR / "40E01B_CLIMATE_PAIR_DISCREPANCY_SUMMARY_SIAK_AOI01_V1.csv"

OUT_MASTER = WORKDIR / "40E02_V2_WALL_TO_WALL_COVERAGE_CONTRACT_SIAK_AOI01.csv"
OUT_SUMMARY = WORKDIR / "40E02_V2_COVERAGE_PATHWAY_SUMMARY_SIAK_AOI01.csv"
OUT_QC = WORKDIR / "40E02_V2_MODEL_ROLE_WALL_TO_WALL_FREEZE_QC_SIAK_AOI01.json"

print("====================================================")
print("40E02-V2 — FINAL MODEL ROLE + WALL-TO-WALL CONTRACT")
print("PURE PYTHON / NO MODEL RERUN")
print("====================================================")


def read_csv_dict(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv_dict(path, rows):
    if not rows:
        raise ValueError(f"No rows to write: {path}")
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def to_float_or_none(value):
    if value is None:
        return None
    s = str(value).strip()
    if s == "":
        return None
    try:
        x = float(s)
    except Exception:
        return None
    if not math.isfinite(x):
        return None
    return x


def mean(values):
    return sum(values) / len(values)


def average_ranks(values):
    n = len(values)
    order = sorted(range(n), key=lambda i: values[i])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg_rank = ((i + 1) + (j + 1)) / 2.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg_rank
        i = j + 1
    return ranks


def correlation(x, y):
    if len(x) != len(y):
        raise ValueError("Correlation lengths differ.")
    if len(x) < 2:
        return None
    mx = mean(x)
    my = mean(y)
    dx = [v - mx for v in x]
    dy = [v - my for v in y]
    denom = math.sqrt(sum(v * v for v in dx) * sum(v * v for v in dy))
    if denom == 0:
        return None
    return sum(a * b for a, b in zip(dx, dy)) / denom


def spearman(x, y):
    return correlation(average_ranks(x), average_ranks(y))


def get_first(row, candidates, default=""):
    for c in candidates:
        if c in row:
            return row[c]
    return default


# 1. PREFLIGHT
for p in [MASTER_ASU, PAIR_MAP, PALMSIM_BASE, APSIM_FROZEN, COMP_48, AGE_DIAG, CLIMATE_DIAG]:
    if not p.exists():
        raise FileNotFoundError(p)

print("Input files found              : PASS")

# 2. MASTER 820
master = read_csv_dict(MASTER_ASU)
if len(master) != 820:
    raise ValueError(f"Expected 820 master ASUs; got {len(master)}.")

master_ids = [str(r["UNIT_ID"]) for r in master]
master_set = set(master_ids)
if len(master_set) != 820:
    raise ValueError("Master ASU table does not contain 820 unique UNIT_IDs.")

print("Master ASUs                    :", len(master))

# 3. CLIMATE PAIR
pair_rows = read_csv_dict(PAIR_MAP)
if len(pair_rows) != 820:
    raise ValueError(f"Expected 820 climate-pair rows; got {len(pair_rows)}.")

pair_lookup = {}
for r in pair_rows:
    uid = str(r["UNIT_ID"])
    if uid in pair_lookup:
        raise ValueError(f"Duplicate UNIT_ID in climate-pair map: {uid}")
    pair_lookup[uid] = r

if set(pair_lookup) != master_set:
    raise ValueError("Climate-pair map UNIT_ID set does not exactly match master 820 ASUs.")

# 4. PALMSIM 654
palm = read_csv_dict(PALMSIM_BASE)
if len(palm) != 654:
    raise ValueError(f"Expected 654 PALMSIM baseline rows; got {len(palm)}.")

palm_columns = list(palm[0].keys())
preferred_yield_fields = [
    "TRAILING_1Y_MEAN_T_HA_YR",
    "POTENTIAL_T_HA_YR",
    "BASELINE_T_HA_YR",
    "FFB_T_HA_YR",
]

palm_yield_field = None
for c in preferred_yield_fields:
    if c in palm_columns:
        palm_yield_field = c
        break

if palm_yield_field is None:
    candidates = [
        c for c in palm_columns
        if "T_HA_YR" in c.upper()
        and (
            "TRAIL" in c.upper()
            or "POTENTIAL" in c.upper()
            or "BASE" in c.upper()
        )
    ]
    if len(candidates) != 1:
        raise ValueError(
            "Could not uniquely identify PALMSIM canonical yield field. "
            f"Candidates={candidates}"
        )
    palm_yield_field = candidates[0]

palm_ids = set()
palm_lookup = {}

for r in palm:
    uid = str(r["UNIT_ID"])
    if uid in palm_ids:
        raise ValueError(f"Duplicate PALMSIM UNIT_ID: {uid}")
    palm_ids.add(uid)
    palm_lookup[uid] = r

if not palm_ids.issubset(master_set):
    raise ValueError("PALMSIM baseline contains UNIT_ID outside master 820 ASUs.")

fallback_ids = master_set - palm_ids

if len(fallback_ids) != 166:
    raise ValueError(f"Expected 166 non-PALMSIM ASUs; got {len(fallback_ids)}.")

print("PALMSIM direct ASUs            :", len(palm_ids))
print("Fallback-path ASUs             :", len(fallback_ids))
print("PALMSIM yield field            :", palm_yield_field)

# 5. APSIM + 48 COMPARISON
apsim = read_csv_dict(APSIM_FROZEN)
if len(apsim) != 48:
    raise ValueError(f"Expected 48 APSIM benchmark rows; got {len(apsim)}.")

apsim_ids = {str(r["UNIT_ID"]) for r in apsim}
if len(apsim_ids) != 48:
    raise ValueError("APSIM benchmark does not contain 48 unique ASUs.")

if not apsim_ids.issubset(palm_ids):
    raise ValueError("APSIM benchmark ASUs must be a subset of PALMSIM direct ASUs.")

comp = read_csv_dict(COMP_48)
if len(comp) != 48:
    raise ValueError(f"Expected 48 core-comparison rows; got {len(comp)}.")

comp_ids = {str(r["UNIT_ID"]) for r in comp}
if comp_ids != apsim_ids:
    raise ValueError("40E01A comparison set does not exactly match frozen APSIM benchmark set.")

P = [float(r["PALMSIM_BASE_T_FFB_HA_YR"]) for r in comp]
A = [float(r["APSIM_A143_BASE_T_FFB_HA_YR"]) for r in comp]

pearson_r = correlation(P, A)
spearman_rho = spearman(P, A)
deltas = [a - p for a, p in zip(A, P)]
symdiffs = [float(r["MODEL_SYMMETRIC_DIFF_PCT"]) for r in comp]
rankdiffs = [float(r["MODEL_RANK_ABS_DIFF"]) for r in comp]

print("APSIM benchmark ASUs           :", len(apsim_ids))
print("Pearson r                      :", pearson_r)
print("Spearman rho                   :", spearman_rho)

# 6. DIAGNOSTICS
age_diag = read_csv_dict(AGE_DIAG)
climate_diag = read_csv_dict(CLIMATE_DIAG)

if len(age_diag) != 5:
    raise ValueError(f"Expected 5 age diagnostic groups; got {len(age_diag)}.")

if len(climate_diag) != 12:
    raise ValueError(f"Expected 12 climate-pair diagnostics; got {len(climate_diag)}.")

worst_age = max(age_diag, key=lambda r: float(r["MAE_T_HA_YR"]))
worst_climate = max(climate_diag, key=lambda r: float(r["MAE_T_HA_YR"]))

# 7. MODEL ROLE FREEZE
MODEL_ROLE = {
    "PALMSIM_ROLE": "PRIMARY_PROCESS_MODEL_FOR_NUMERIC_PRODUCTIVITY_POTENTIAL",
    "APSIM_ROLE": "REPRESENTATIVE_PROCESS_SCENARIO_BENCHMARK_ONLY",
    "MODEL_AVERAGING": "NO",
    "CROSS_MODEL_BIAS_CORRECTION": "NO",
    "APSIM_WALL_TO_WALL_INTERPOLATION": "NO",
    "APSIM_AS_GROUND_TRUTH": "NO",
    "PALMSIM_AS_GROUND_TRUTH": "NO",
    "OBSERVED_FFB_VALIDATION_AVAILABLE": "NO",
}

# 8. WALL-TO-WALL CONTRACT
WALL_TO_WALL_CONTRACT = {
    "SPATIAL_DOMAIN": "ALL_OUTPUT1_PALM_BOUNDARY_ASUS",
    "MASTER_ASU_COUNT": 820,
    "DIRECT_MODEL_SUPPORTED_COUNT": 654,
    "FALLBACK_PATH_COUNT": 166,
    "FINAL_MAP_COVERAGE_TARGET": "820_OF_820_ASUS",
    "PALM_ASU_MAY_BE_DROPPED_DUE_TO_MISSING_NUMERIC_AGE": "NO",
    "ALL_PALM_ASUS_REQUIRE_FINAL_ANALYTICAL_CLASS": "YES",
    "FINAL_CLASS_SCHEMA": "0_TO_4",
    "DIRECT_PATH_PRODUCTIVITY": "PALMSIM_NUMERIC_MODELLED_PRODUCTIVITY_POTENTIAL",
    "FALLBACK_PATH_PRODUCTIVITY": "INDICATIVE_PRODUCTIVITY_RANGE_TO_BE_BUILT_IN_40E03",
    "FALLBACK_POINT_ESTIMATE_EQUAL_TO_DIRECT_PALMSIM": "NO",
    "NO_DATA_OUTSIDE_PALM_BOUNDARY": "YES",
    "CLASS_0_IS_NOT_GEOGRAPHIC_NODATA": "YES",
}

# 9. BUILD 820 CONTRACT
contract_rows = []
direct_count = 0
fallback_count = 0
numeric_age_direct_count = 0
numeric_age_fallback_count = 0

for r in master:
    uid = str(r["UNIT_ID"])
    pair_row = pair_lookup[uid]

    age_raw = get_first(
        r,
        ["AGE_P50", "AGE_PROXY_YR", "AGE_MEDIAN"],
        ""
    )
    age_value = to_float_or_none(age_raw)

    reference_year = get_first(r, ["REFERENCE_YEAR"], "")

    centroid_lat = get_first(
        r,
        ["CENTROID_LAT_EXACT", "CENTROID_LAT", "LAT", "LATITUDE"],
        ""
    )
    centroid_lon = get_first(
        r,
        ["CENTROID_LON_EXACT", "CENTROID_LON", "LON", "LONGITUDE"],
        ""
    )

    chirps_id = get_first(
        pair_row,
        ["CHIRPS_CELL_ID"],
        get_first(r, ["CHIRPS_CELL_ID"], "")
    )
    era5_id = get_first(
        pair_row,
        ["ERA5L_CELL_ID"],
        get_first(r, ["ERA5L_CELL_ID"], "")
    )
    climate_pair = get_first(pair_row, ["CLIMATE_PAIR_ID"], "")

    if uid in palm_ids:
        direct_count += 1

        if age_value is not None:
            numeric_age_direct_count += 1

        palm_yield = to_float_or_none(
            palm_lookup[uid].get(palm_yield_field, "")
        )
        if palm_yield is None:
            raise ValueError(
                f"PALMSIM direct-path ASU has non-finite yield: {uid}"
            )

        pathway = "DIRECT_MODEL_SUPPORTED"
        productivity_method = "PALMSIM_DIRECT"
        productivity_status = "NUMERIC_MODELLED_POTENTIAL_AVAILABLE"
        productivity_value = palm_yield
        fallback_status = "NOT_REQUIRED"
        age_status = (
            "NUMERIC_AGE_PROXY_AVAILABLE"
            if age_value is not None
            else "CHECK_AGE_MAPPING_INCONSISTENCY"
        )
        confidence_stage = "MODEL_SUPPORTED__FINAL_CONFIDENCE_PENDING_40F_40G"

    else:
        fallback_count += 1

        if age_value is not None:
            numeric_age_fallback_count += 1

        pathway = "AGE_CENSORED_OR_UNRESOLVED_FALLBACK"
        productivity_method = "FALLBACK_PENDING_40E03"
        productivity_status = "INDICATIVE_RANGE_NOT_YET_ESTIMATED"
        productivity_value = ""
        fallback_status = "REQUIRED"
        age_status = (
            "NUMERIC_AGE_PRESENT_BUT_NOT_PALMSIM_ELIGIBLE__REVIEW"
            if age_value is not None
            else "NUMERIC_AGE_PROXY_UNAVAILABLE"
        )
        confidence_stage = "LOW_OR_LIMITED__TO_BE_RESOLVED_IN_40E03_40F_40G"

    contract_rows.append({
        "UNIT_ID": uid,
        "REFERENCE_YEAR": reference_year,
        "AGE_P50": age_raw,
        "AGE_STATUS_40E02": age_status,
        "CHIRPS_CELL_ID": chirps_id,
        "ERA5L_CELL_ID": era5_id,
        "CLIMATE_PAIR_ID": climate_pair,
        "CENTROID_LAT": centroid_lat,
        "CENTROID_LON": centroid_lon,
        "OUTPUT4_SPATIAL_DOMAIN": "INCLUDED",
        "OUTPUT4_ANALYTICAL_PATHWAY": pathway,
        "PRODUCTIVITY_ESTIMATE_METHOD": productivity_method,
        "PRODUCTIVITY_ESTIMATE_STATUS": productivity_status,
        "PALMSIM_DIRECT_T_FFB_HA_YR": productivity_value,
        "FALLBACK_PRODUCTIVITY_REQUIRED": fallback_status,
        "FINAL_CLASS_0_4_REQUIRED": "YES",
        "FINAL_CLASS": "PENDING_40H",
        "FINAL_CLASS_NOTES": "DO_NOT_DROP_ASU__CLASS_TO_BE_ASSIGNED_AFTER_PRODUCTIVITY_AND_MANAGEMENT_INTEGRATION",
        "CONFIDENCE_STATUS": confidence_stage,
        "WALL_TO_WALL_CONTRACT_VERSION": "40E02_V2",
    })

# 10. PATHWAY SUMMARY
summary_rows = [
    {
        "PATHWAY": "DIRECT_MODEL_SUPPORTED",
        "N_ASU": direct_count,
        "PRODUCTIVITY_OUTPUT": "PALMSIM numeric modelled productivity potential",
        "NEXT_STEP": "40F synthesis + 40G calibration/sensitivity",
    },
    {
        "PATHWAY": "AGE_CENSORED_OR_UNRESOLVED_FALLBACK",
        "N_ASU": fallback_count,
        "PRODUCTIVITY_OUTPUT": "Indicative productivity range (not direct PALMSIM)",
        "NEXT_STEP": "40E03 fallback productivity estimation",
    },
]

# 11. QC
contract_ids = {r["UNIT_ID"] for r in contract_rows}

included_count = sum(
    1 for r in contract_rows
    if r["OUTPUT4_SPATIAL_DOMAIN"] == "INCLUDED"
)

direct_rows = [
    r for r in contract_rows
    if r["OUTPUT4_ANALYTICAL_PATHWAY"] == "DIRECT_MODEL_SUPPORTED"
]

fallback_rows = [
    r for r in contract_rows
    if r["OUTPUT4_ANALYTICAL_PATHWAY"] == "AGE_CENSORED_OR_UNRESOLVED_FALLBACK"
]

checks = {
    "master_asu_820": len(master) == 820,
    "master_unique_asu_820": len(master_set) == 820,
    "contract_rows_820": len(contract_rows) == 820,
    "contract_unique_asu_820": len(contract_ids) == 820,
    "contract_exactly_matches_master_asus": contract_ids == master_set,
    "all_820_spatially_included": included_count == 820,
    "palmsim_direct_654": len(direct_rows) == 654,
    "fallback_path_166": len(fallback_rows) == 166,
    "direct_plus_fallback_equals_820": len(direct_rows) + len(fallback_rows) == 820,
    "direct_ids_exactly_match_palmsim_654": {r["UNIT_ID"] for r in direct_rows} == palm_ids,
    "fallback_ids_exactly_master_minus_palmsim": {r["UNIT_ID"] for r in fallback_rows} == fallback_ids,
    "apsim_representative_48": len(apsim_ids) == 48,
    "apsim_subset_of_palmsim_direct": apsim_ids.issubset(palm_ids),
    "comparison_48_matches_apsim_48": comp_ids == apsim_ids,
    "age_diagnostic_groups_5": len(age_diag) == 5,
    "climate_diagnostic_pairs_12": len(climate_diag) == 12,
    "model_averaging_disabled": MODEL_ROLE["MODEL_AVERAGING"] == "NO",
    "cross_model_bias_correction_disabled": MODEL_ROLE["CROSS_MODEL_BIAS_CORRECTION"] == "NO",
    "apsim_wall_to_wall_interpolation_disabled": MODEL_ROLE["APSIM_WALL_TO_WALL_INTERPOLATION"] == "NO",
    "all_asus_require_final_class": all(
        r["FINAL_CLASS_0_4_REQUIRED"] == "YES"
        for r in contract_rows
    ),
}

status = (
    "PASS_WALL_TO_WALL_ROLE_FREEZE"
    if all(checks.values())
    else "REVIEW"
)

# 12. SAVE
write_csv_dict(OUT_MASTER, contract_rows)
write_csv_dict(OUT_SUMMARY, summary_rows)

qc = {
    "gate": "40E02_V2_FINAL_MODEL_ROLE_AND_WALL_TO_WALL_COVERAGE_CONTRACT",
    "status": status,
    "model_role": MODEL_ROLE,
    "wall_to_wall_contract": WALL_TO_WALL_CONTRACT,
    "coverage": {
        "master_asus": 820,
        "direct_palmsim_asus": len(direct_rows),
        "fallback_path_asus": len(fallback_rows),
        "spatially_included_asus": included_count,
        "numeric_age_in_direct_path": numeric_age_direct_count,
        "numeric_age_in_fallback_path": numeric_age_fallback_count,
    },
    "model_comparison_evidence": {
        "representative_asus": len(comp),
        "pearson_r": pearson_r,
        "spearman_rho": spearman_rho,
        "mean_bias_apsim_minus_palmsim_t_ha_yr": mean(deltas),
        "median_symmetric_difference_pct": statistics.median(symdiffs),
        "median_rank_absolute_difference": statistics.median(rankdiffs),
        "worst_age_group_by_mae": worst_age["AGE_GROUP"],
        "worst_age_group_mae_t_ha_yr": float(worst_age["MAE_T_HA_YR"]),
        "worst_climate_pair_by_mae": worst_climate["CLIMATE_PAIR_ID"],
        "worst_climate_pair_mae_t_ha_yr": float(worst_climate["MAE_T_HA_YR"]),
    },
    "scientific_interpretation": [
        "PALMSIM remains the primary numeric productivity-potential process model for ASUs with defensible numeric age input.",
        "APSIM remains a representative process/scenario benchmark and is not used as a second wall-to-wall yield surface.",
        "PALMSIM and APSIM are not averaged because their representative agreement is weak and age-response disagreement is structurally large.",
        "The 166 non-PALMSIM ASUs remain inside the Output 4 spatial domain.",
        "The 166 ASUs will receive an indicative fallback productivity range in 40E03 rather than a fabricated direct PALMSIM point estimate.",
        "All 820 palm ASUs must receive a final Output 4 analytical class after downstream integration.",
        "Class 0 is an analytical class for limited evidence; it is not equivalent to geographic NoData/outside palm boundary.",
        "No observed local FFB/TBS validation is available, so neither process model is treated as ground truth.",
    ],
    "checks": checks,
    "next": "40E03 fallback productivity estimation for 166 age-censored/unresolved ASUs.",
}

with open(OUT_QC, "w", encoding="utf-8") as f:
    json.dump(qc, f, indent=2)

# 13. PRINT
print("\n====================================================")
print("40E02-V2 FINISHED")
print("====================================================")
print("Status                         :", status)

print("\nMODEL ROLE")
print("PALMSIM                        :", MODEL_ROLE["PALMSIM_ROLE"])
print("APSIM                          :", MODEL_ROLE["APSIM_ROLE"])
print("Model averaging                :", MODEL_ROLE["MODEL_AVERAGING"])
print("Cross-model bias correction    :", MODEL_ROLE["CROSS_MODEL_BIAS_CORRECTION"])

print("\nWALL-TO-WALL COVERAGE")
print("Master ASUs                    :", len(contract_rows))
print("Direct PALMSIM pathway         :", len(direct_rows))
print("Fallback pathway               :", len(fallback_rows))
print("Spatially included             :", included_count)
print("Final map target               : 820 / 820 ASUs")

print("\nMODEL COMPARISON EVIDENCE")
print("Pearson r                      :", pearson_r)
print("Spearman rho                   :", spearman_rho)
print("Median symmetric difference %  :", statistics.median(symdiffs))
print(
    "Worst age group               :",
    worst_age["AGE_GROUP"],
    "| MAE =",
    worst_age["MAE_T_HA_YR"]
)

print("\nAGE COVERAGE CHECK")
print("Numeric age in direct path     :", numeric_age_direct_count)
print("Numeric age in fallback path   :", numeric_age_fallback_count)

print("\nQC:")
for key, value in checks.items():
    print(f"{key:52s}: {value}")

print("\nMaster contract CSV :", OUT_MASTER)
print("Pathway summary CSV :", OUT_SUMMARY)
print("Freeze/QC JSON      :", OUT_QC)

if status == "PASS_WALL_TO_WALL_ROLE_FREEZE":
    print(
        "Next                : 40E03 fallback productivity "
        "estimation for 166 ASUs."
    )
else:
    print("Next                : Review failed QC before 40E03.")

print("====================================================")
