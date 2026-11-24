# ============================================================
# OUTPUT 4 / 40E02
# PROCESS-MODEL AGREEMENT SYNTHESIS + ROLE DECISION
# SIAK_AOI01
#
# PURE PYTHON STANDARD LIBRARY ONLY
# NO numpy / pandas / scipy
#
# Purpose:
# 1) Freeze PALMSIM vs APSIM interpretation.
# 2) Do NOT average, calibrate, or bias-correct one model with the other.
# 3) Use representative APSIM comparison only as a structural
#    disagreement diagnostic.
# 4) Transfer that diagnostic to the 654 PALMSIM-eligible ASUs via
#    age-group + climate-pair summaries, explicitly as a proxy
#    (not empirical uncertainty / not validation).
# ============================================================

from pathlib import Path
import csv
import json
import math
import statistics

WORKDIR = Path(
    r"C:\Users\user\Documents\KERJA\SPATIAL DATA ANALYST INTERN\04_YIELD"
)

# 48-ASU direct model comparison
COMP_CSV = WORKDIR / (
    "40E01A_V3_PALMSIM_APSIM_CORE_COMPARISON_SIAK_AOI01.csv"
)

# 40E01B summaries
AGE_CSV = WORKDIR / (
    "40E01B_AGE_DISCREPANCY_SUMMARY_SIAK_AOI01_V1.csv"
)

CLIMATE_CSV = WORKDIR / (
    "40E01B_CLIMATE_PAIR_DISCREPANCY_SUMMARY_SIAK_AOI01_V1.csv"
)

# 654 PALMSIM-eligible ASUs
PALMSIM_BASE = WORKDIR / (
    "40C04A_DIRECT_P00_BASELINE_RESULTS_SIAK_AOI01_V1.csv"
)

# Authoritative age + climate mapping
ASU_MAP = WORKDIR / (
    "40B04A_ASU_CLIMATE_CELL_MAPPING_SIAK_AOI01_V1.csv"
)

PAIR_MAP = WORKDIR / (
    "40B04C_LITE_ASU_CLIMATE_PAIR_MAPPING_SIAK_AOI01_V1.csv"
)

OUT_REP = WORKDIR / (
    "40E02_REPRESENTATIVE_MODEL_DISAGREEMENT_DIAGNOSTIC_SIAK_AOI01_V1.csv"
)

OUT_654 = WORKDIR / (
    "40E02_PALMSIM_ELIGIBLE_STRUCTURAL_DISAGREEMENT_PROXY_SIAK_AOI01_V1.csv"
)

OUT_JSON = WORKDIR / (
    "40E02_MODEL_ROLE_DECISION_QC_SIAK_AOI01_V1.json"
)

print("====================================================")
print("40E02 — MODEL AGREEMENT SYNTHESIS + ROLE DECISION")
print("PURE PYTHON")
print("====================================================")


# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------

def read_csv_dict(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv_dict(path, rows):
    if not rows:
        raise ValueError(f"No rows to write: {path}")

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=list(rows[0].keys())
        )
        writer.writeheader()
        writer.writerows(rows)


def to_float(value, label="value"):
    try:
        x = float(value)
    except Exception:
        raise ValueError(f"Cannot convert {label}={value!r} to float.")

    if not math.isfinite(x):
        raise ValueError(f"Non-finite {label}: {value!r}")

    return x


def mean(values):
    return sum(values) / len(values)


def quantile(values, q):
    xs = sorted(values)

    if not xs:
        return None

    if len(xs) == 1:
        return xs[0]

    pos = (len(xs) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)

    if lo == hi:
        return xs[lo]

    frac = pos - lo

    return xs[lo] * (1.0 - frac) + xs[hi] * frac


def average_ranks(values):
    n = len(values)
    order = sorted(range(n), key=lambda i: values[i])
    ranks = [0.0] * n

    i = 0

    while i < n:
        j = i

        while (
            j + 1 < n
            and values[order[j + 1]] == values[order[i]]
        ):
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

    denom = math.sqrt(
        sum(v * v for v in dx)
        * sum(v * v for v in dy)
    )

    if denom == 0:
        return None

    return (
        sum(a * b for a, b in zip(dx, dy))
        / denom
    )


def spearman(x, y):
    return correlation(
        average_ranks(x),
        average_ranks(y)
    )


def age_group(age):
    if age <= 3:
        return "AGE_0_3"
    elif age <= 7:
        return "AGE_4_7"
    elif age <= 12:
        return "AGE_8_12"
    elif age <= 18:
        return "AGE_13_18"
    else:
        return "AGE_19_PLUS"


# ------------------------------------------------------------
# 1. PREFLIGHT
# ------------------------------------------------------------

for p in [
    COMP_CSV,
    AGE_CSV,
    CLIMATE_CSV,
    PALMSIM_BASE,
    ASU_MAP,
    PAIR_MAP,
]:
    if not p.exists():
        raise FileNotFoundError(p)

print("Input files found: PASS")


# ------------------------------------------------------------
# 2. LOAD REPRESENTATIVE COMPARISON
# ------------------------------------------------------------

comp = read_csv_dict(COMP_CSV)

if len(comp) != 48:
    raise ValueError(f"Expected 48 comparison rows; got {len(comp)}.")

if len({r["UNIT_ID"] for r in comp}) != 48:
    raise ValueError("Representative comparison UNIT_ID not unique.")

P = [
    to_float(r["PALMSIM_BASE_T_FFB_HA_YR"])
    for r in comp
]

A = [
    to_float(r["APSIM_A143_BASE_T_FFB_HA_YR"])
    for r in comp
]

abs_diff = [
    to_float(r["MODEL_ABS_DIFF_T_HA_YR"])
    for r in comp
]

sym_diff = [
    to_float(r["MODEL_SYMMETRIC_DIFF_PCT"])
    for r in comp
]

rank_diff = [
    to_float(r["MODEL_RANK_ABS_DIFF"])
    for r in comp
]

pearson_r = correlation(P, A)
spearman_rho = spearman(P, A)

mean_bias = mean([
    a - p
    for a, p in zip(A, P)
])

median_abs_diff = statistics.median(abs_diff)
median_sym_diff = statistics.median(sym_diff)
median_rank_diff = statistics.median(rank_diff)

print("Representative ASUs :", len(comp))
print("Pearson r           :", pearson_r)
print("Spearman rho        :", spearman_rho)
print("Median sym diff %   :", median_sym_diff)


# ------------------------------------------------------------
# 3. REPRESENTATIVE DISAGREEMENT DIAGNOSTIC
#
# Relative diagnostic tiers are based on the 48-ASU distribution.
# They are NOT agronomic thresholds and NOT validation classes.
# ------------------------------------------------------------

abs_q1 = quantile(abs_diff, 0.25)
abs_q3 = quantile(abs_diff, 0.75)

sym_q1 = quantile(sym_diff, 0.25)
sym_q3 = quantile(sym_diff, 0.75)

rank_q1 = quantile(rank_diff, 0.25)
rank_q3 = quantile(rank_diff, 0.75)

rep_out = []

for r in comp:

    ad = to_float(r["MODEL_ABS_DIFF_T_HA_YR"])
    sd = to_float(r["MODEL_SYMMETRIC_DIFF_PCT"])
    rd = to_float(r["MODEL_RANK_ABS_DIFF"])

    high_votes = (
        int(ad >= abs_q3)
        + int(sd >= sym_q3)
        + int(rd >= rank_q3)
    )

    low_votes = (
        int(ad <= abs_q1)
        + int(sd <= sym_q1)
        + int(rd <= rank_q1)
    )

    if high_votes >= 2:
        tier = "RELATIVE_HIGH"
    elif low_votes >= 2:
        tier = "RELATIVE_LOW"
    else:
        tier = "RELATIVE_MODERATE"

    rep_out.append({
        "UNIT_ID": r["UNIT_ID"],
        "AGE_PROXY_YR": r["AGE_PROXY_YR"],
        "CLIMATE_PAIR_ID": r["CLIMATE_PAIR_ID"],

        "PALMSIM_T_FFB_HA_YR":
            r["PALMSIM_BASE_T_FFB_HA_YR"],

        "APSIM_T_FFB_HA_YR":
            r["APSIM_A143_BASE_T_FFB_HA_YR"],

        "ABS_MODEL_DIFF_T_HA_YR":
            r["MODEL_ABS_DIFF_T_HA_YR"],

        "SYMMETRIC_MODEL_DIFF_PCT":
            r["MODEL_SYMMETRIC_DIFF_PCT"],

        "RANK_ABS_DIFF":
            r["MODEL_RANK_ABS_DIFF"],

        "RELATIVE_DISAGREEMENT_TIER":
            tier,

        "TIER_METHOD":
            "48_ASU_RELATIVE_QUARTILE_VOTING",

        "EMPIRICAL_VALIDATION":
            "NO",
    })

write_csv_dict(OUT_REP, rep_out)


# ------------------------------------------------------------
# 4. LOAD AGE + CLIMATE DIAGNOSTIC SUMMARIES
# ------------------------------------------------------------

age_rows = read_csv_dict(AGE_CSV)
climate_rows = read_csv_dict(CLIMATE_CSV)

age_lookup = {
    r["AGE_GROUP"]: {
        "MAE": to_float(r["MAE_T_HA_YR"]),
        "BIAS": to_float(
            r["BIAS_MEDIAN_APSIM_MINUS_PALMSIM"]
        ),
        "SYM": to_float(
            r["MEDIAN_SYMMETRIC_DIFF_PCT"]
        ),
    }
    for r in age_rows
}

climate_lookup = {
    r["CLIMATE_PAIR_ID"]: {
        "MAE": to_float(r["MAE_T_HA_YR"]),
        "BIAS": to_float(
            r["BIAS_MEDIAN_APSIM_MINUS_PALMSIM"]
        ),
        "SYM": to_float(
            r["MEDIAN_SYMMETRIC_DIFF_PCT"]
        ),
    }
    for r in climate_rows
}

if len(age_lookup) != 5:
    raise ValueError(
        f"Expected 5 age groups; got {len(age_lookup)}."
    )

if len(climate_lookup) != 12:
    raise ValueError(
        f"Expected 12 climate pairs; got {len(climate_lookup)}."
    )


# ------------------------------------------------------------
# 5. LOAD 654 PALMSIM-ELIGIBLE ASUs
# ------------------------------------------------------------

palm654 = read_csv_dict(PALMSIM_BASE)

eligible_ids = {
    r["UNIT_ID"]
    for r in palm654
}

if len(eligible_ids) != 654:
    raise ValueError(
        f"Expected 654 PALMSIM eligible ASUs; got {len(eligible_ids)}."
    )

asu_rows = read_csv_dict(ASU_MAP)
pair_rows = read_csv_dict(PAIR_MAP)

asu_lookup = {
    r["UNIT_ID"]: r
    for r in asu_rows
}

pair_lookup = {
    r["UNIT_ID"]: r["CLIMATE_PAIR_ID"]
    for r in pair_rows
}


# ------------------------------------------------------------
# 6. TRANSFER STRUCTURAL DISAGREEMENT PROXY TO 654 ASUs
#
# Proxy = max(age-group MAE, climate-pair MAE).
#
# Rationale:
# - conservative;
# - no arbitrary weighting;
# - if either age structure or climate-pair context showed large
#   PALMSIM/APSIM disagreement in the representative benchmark,
#   that disagreement is retained.
#
# This is NOT yield error and NOT empirical uncertainty.
# ------------------------------------------------------------

proxy_rows = []

for uid in sorted(eligible_ids):

    if uid not in asu_lookup:
        raise KeyError(f"ASU mapping missing: {uid}")

    if uid not in pair_lookup:
        raise KeyError(f"Climate pair mapping missing: {uid}")

    age = to_float(
        asu_lookup[uid]["AGE_P50"],
        f"{uid} AGE_P50"
    )

    ag = age_group(age)
    pair = pair_lookup[uid]

    if ag not in age_lookup:
        raise KeyError(f"Age summary missing: {ag}")

    if pair not in climate_lookup:
        raise KeyError(f"Climate summary missing: {pair}")

    age_mae = age_lookup[ag]["MAE"]
    climate_mae = climate_lookup[pair]["MAE"]

    structural_proxy = max(
        age_mae,
        climate_mae
    )

    proxy_rows.append({
        "UNIT_ID": uid,
        "AGE_PROXY_YR": age,
        "AGE_GROUP": ag,
        "CLIMATE_PAIR_ID": pair,

        "AGE_GROUP_MODEL_MAE_T_HA_YR":
            age_mae,

        "AGE_GROUP_MEDIAN_BIAS_A_MINUS_P":
            age_lookup[ag]["BIAS"],

        "AGE_GROUP_MEDIAN_SYM_DIFF_PCT":
            age_lookup[ag]["SYM"],

        "CLIMATE_PAIR_MODEL_MAE_T_HA_YR":
            climate_mae,

        "CLIMATE_PAIR_MEDIAN_BIAS_A_MINUS_P":
            climate_lookup[pair]["BIAS"],

        "CLIMATE_PAIR_MEDIAN_SYM_DIFF_PCT":
            climate_lookup[pair]["SYM"],

        "STRUCTURAL_DISAGREEMENT_PROXY_T_HA_YR":
            structural_proxy,

        "STRUCTURAL_PROXY_METHOD":
            "MAX_OF_REPRESENTATIVE_AGE_MAE_AND_CLIMATE_PAIR_MAE",

        "EMPIRICAL_UNCERTAINTY":
            "NO",

        "LOCAL_YIELD_VALIDATION":
            "NO",
    })


# ------------------------------------------------------------
# 7. RELATIVE 654-ASU STRUCTURAL PROXY TIER
#
# Terciles are relative presentation classes only.
# ------------------------------------------------------------

proxy_values = [
    r["STRUCTURAL_DISAGREEMENT_PROXY_T_HA_YR"]
    for r in proxy_rows
]

p33 = quantile(proxy_values, 1.0 / 3.0)
p67 = quantile(proxy_values, 2.0 / 3.0)

for r in proxy_rows:

    x = r[
        "STRUCTURAL_DISAGREEMENT_PROXY_T_HA_YR"
    ]

    if x <= p33:
        tier = "RELATIVE_LOW"
    elif x <= p67:
        tier = "RELATIVE_MODERATE"
    else:
        tier = "RELATIVE_HIGH"

    r[
        "STRUCTURAL_DISAGREEMENT_RELATIVE_TIER"
    ] = tier

    r[
        "RELATIVE_TIER_METHOD"
    ] = "654_ASU_PROXY_TERCILES"

write_csv_dict(OUT_654, proxy_rows)


# ------------------------------------------------------------
# 8. FINAL MODEL-ROLE DECISION
# ------------------------------------------------------------

tier_counts_48 = {
    "RELATIVE_LOW": 0,
    "RELATIVE_MODERATE": 0,
    "RELATIVE_HIGH": 0,
}

for r in rep_out:
    tier_counts_48[
        r["RELATIVE_DISAGREEMENT_TIER"]
    ] += 1

tier_counts_654 = {
    "RELATIVE_LOW": 0,
    "RELATIVE_MODERATE": 0,
    "RELATIVE_HIGH": 0,
}

for r in proxy_rows:
    tier_counts_654[
        r["STRUCTURAL_DISAGREEMENT_RELATIVE_TIER"]
    ] += 1


# Scientific role decision:
# PALMSIM remains primary because it was the pre-declared primary model
# and covers all 654 eligible ASUs.
#
# APSIM remains representative benchmark because:
# - only 48 representative ASUs were run;
# - soil/management are reference assumptions, not local calibration;
# - no observed FFB labels exist;
# - model-to-model rank agreement is weak;
# - age-specific disagreement is large and structurally inconsistent.
#
# Therefore:
# NO averaging
# NO bias correction
# NO APSIM interpolation to all 654 ASUs
# NO claim that disagreement = empirical uncertainty.

role_decision = {
    "PALMSIM_ROLE":
        "PRIMARY_PROCESS_MODEL_FOR_PRODUCTIVITY_POTENTIAL",

    "APSIM_ROLE":
        "REPRESENTATIVE_PROCESS_SCENARIO_BENCHMARK_ONLY",

    "MODEL_FUSION":
        "NO",

    "MODEL_AVERAGING":
        "NO",

    "CROSS_MODEL_BIAS_CORRECTION":
        "NO",

    "APSIM_SPATIAL_INTERPOLATION_TO_654":
        "NO",

    "STRUCTURAL_DISAGREEMENT_PROXY":
        "YES_DIAGNOSTIC_ONLY",
}


# ------------------------------------------------------------
# 9. QC / FREEZE
# ------------------------------------------------------------

checks = {
    "representative_rows_48":
        len(rep_out) == 48,

    "representative_unique_asu_48":
        len({r["UNIT_ID"] for r in rep_out}) == 48,

    "age_groups_5":
        len(age_lookup) == 5,

    "climate_pairs_12":
        len(climate_lookup) == 12,

    "palmsim_eligible_rows_654":
        len(proxy_rows) == 654,

    "palmsim_eligible_unique_asu_654":
        len({r["UNIT_ID"] for r in proxy_rows}) == 654,

    "all_structural_proxy_finite":
        all(
            math.isfinite(
                r["STRUCTURAL_DISAGREEMENT_PROXY_T_HA_YR"]
            )
            for r in proxy_rows
        ),

    "model_fusion_disabled":
        role_decision["MODEL_FUSION"] == "NO",

    "apsim_role_benchmark_only":
        role_decision["APSIM_ROLE"]
        == "REPRESENTATIVE_PROCESS_SCENARIO_BENCHMARK_ONLY",
}

status = (
    "PASS_ROLE_DECISION_FROZEN"
    if all(checks.values())
    else "REVIEW"
)

worst_age = max(
    age_rows,
    key=lambda r: to_float(r["MAE_T_HA_YR"])
)

worst_climate = max(
    climate_rows,
    key=lambda r: to_float(r["MAE_T_HA_YR"])
)

qc = {
    "gate":
        "40E02_MODEL_AGREEMENT_SYNTHESIS_ROLE_DECISION",

    "status":
        status,

    "global_model_diagnostics": {
        "pearson_r":
            pearson_r,

        "spearman_rho":
            spearman_rho,

        "mean_bias_apsim_minus_palmsim_t_ha_yr":
            mean_bias,

        "median_absolute_difference_t_ha_yr":
            median_abs_diff,

        "median_symmetric_difference_pct":
            median_sym_diff,

        "median_rank_absolute_difference":
            median_rank_diff,
    },

    "worst_age_group_by_mae": {
        "age_group":
            worst_age["AGE_GROUP"],

        "mae_t_ha_yr":
            to_float(worst_age["MAE_T_HA_YR"]),
    },

    "worst_climate_pair_by_mae": {
        "climate_pair":
            worst_climate["CLIMATE_PAIR_ID"],

        "mae_t_ha_yr":
            to_float(worst_climate["MAE_T_HA_YR"]),
    },

    "representative_relative_disagreement_tiers":
        tier_counts_48,

    "palmsim_eligible_structural_proxy_relative_tiers":
        tier_counts_654,

    "structural_proxy_tercile_thresholds_t_ha_yr": {
        "p33":
            p33,
        "p67":
            p67,
    },

    "role_decision":
        role_decision,

    "checks":
        checks,

    "interpretation_limits": [
        "Neither PALMSIM nor APSIM is ground truth.",
        "No observed local FFB labels are available for yield validation.",
        "Cross-model disagreement is structural/model disagreement, not observed prediction error.",
        "The 654-ASU structural disagreement proxy is transferred from representative age-group and climate-pair diagnostics.",
        "Relative LOW/MODERATE/HIGH proxy tiers are descriptive, not agronomic thresholds.",
        "APSIM reference soil and management are not local Siak calibration.",
        "PALMSIM and APSIM outputs must not be blindly averaged.",
    ],

    "next":
        "40F01 final Productivity Potential synthesis for 654 eligible ASUs.",
}

with open(
    OUT_JSON,
    "w",
    encoding="utf-8"
) as f:
    json.dump(qc, f, indent=2)


# ------------------------------------------------------------
# 10. PRINT
# ------------------------------------------------------------

print("\n====================================================")
print("40E02 FINISHED")
print("====================================================")
print("Status                         :", status)

print("\nMODEL ROLE")
print(
    "PALMSIM                       :",
    role_decision["PALMSIM_ROLE"]
)
print(
    "APSIM                         :",
    role_decision["APSIM_ROLE"]
)
print(
    "Model fusion / averaging      :",
    role_decision["MODEL_FUSION"]
)

print("\nGLOBAL COMPARISON")
print("Pearson r                      :", pearson_r)
print("Spearman rho                   :", spearman_rho)
print("Mean bias APSIM-PALMSIM        :", mean_bias)
print("Median symmetric difference %  :", median_sym_diff)

print("\nSTRUCTURAL HOTSPOTS")
print(
    "Worst age group               :",
    worst_age["AGE_GROUP"],
    "| MAE =",
    worst_age["MAE_T_HA_YR"]
)
print(
    "Worst climate pair            :",
    worst_climate["CLIMATE_PAIR_ID"],
    "| MAE =",
    worst_climate["MAE_T_HA_YR"]
)

print("\n654-ASU STRUCTURAL PROXY")
print("Rows                           :", len(proxy_rows))
print("Relative tier P33              :", p33)
print("Relative tier P67              :", p67)
print("Tier counts                    :", tier_counts_654)

print("\nQC:")
for key, value in checks.items():
    print(f"{key:48s}: {value}")

print("\nRepresentative diagnostic :", OUT_REP)
print("654-ASU structural proxy  :", OUT_654)
print("Role/QC JSON              :", OUT_JSON)

if status == "PASS_ROLE_DECISION_FROZEN":
    print(
        "Next                       : 40F01 final Productivity "
        "Potential synthesis for 654 eligible ASUs."
    )
else:
    print(
        "Next                       : Review failed QC before 40F."
    )

print("====================================================")
