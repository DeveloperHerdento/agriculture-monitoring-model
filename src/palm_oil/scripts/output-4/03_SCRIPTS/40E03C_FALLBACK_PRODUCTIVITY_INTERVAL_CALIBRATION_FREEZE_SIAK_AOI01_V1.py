# ============================================================
# OUTPUT 4 / 40E03C
# FALLBACK PRODUCTIVITY INTERVAL CALIBRATION + FREEZE
# SIAK_AOI01
#
# PURE PYTHON STANDARD LIBRARY ONLY
# NO numpy / pandas / scipy
# NO PALMSIM/APSIM rerun
#
# PURPOSE
# -------
# 1) Interpret 40E03B internal reconstruction results.
# 2) Keep the peer-based P50 as an indicative center.
# 3) Widen the raw peer P10-P90 interval using a conservative
#    leave-one-out (LOO) miss-distance expansion.
# 4) Freeze the fallback method for the 166 age-unresolved ASUs.
#
# IMPORTANT
# ---------
# - This is NOT calibration against actual FFB.
# - The expansion is based only on reconstruction error relative
#   to direct PALMSIM outputs on the 654 donor ASUs.
# - Unknown age is still NOT fabricated.
# - Final fallback confidence remains LOW / VERY_LOW.
# ============================================================

from pathlib import Path
import csv
import json
import math
import statistics

WORKDIR = Path(
    r"C:\Users\user\Documents\KERJA\SPATIAL DATA ANALYST INTERN\04_YIELD"
)

FALLBACK_RAW = WORKDIR / (
    "40E03B_FALLBACK_INDICATIVE_PRODUCTIVITY_166_SIAK_AOI01_V1.csv"
)

LOO = WORKDIR / (
    "40E03B_FALLBACK_METHOD_LOO_RECONSTRUCTION_654_SIAK_AOI01_V1.csv"
)

LOO_AGE = WORKDIR / (
    "40E03B_FALLBACK_METHOD_LOO_BY_AGE_GROUP_SIAK_AOI01_V1.csv"
)

OUT_FROZEN = WORKDIR / (
    "40E03C_FROZEN_FALLBACK_PRODUCTIVITY_166_SIAK_AOI01_V1.csv"
)

OUT_AGE = WORKDIR / (
    "40E03C_CALIBRATED_LOO_BY_AGE_GROUP_SIAK_AOI01_V1.csv"
)

OUT_QC = WORKDIR / (
    "40E03C_FALLBACK_PRODUCTIVITY_FREEZE_QC_SIAK_AOI01_V1.json"
)

print("====================================================")
print("40E03C — FALLBACK INTERVAL CALIBRATION + FREEZE")
print("PURE PYTHON / NO MODEL RERUN")
print("====================================================")


# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------

def read_csv_dict(path):
    with open(
        path,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:
        return list(csv.DictReader(f))


def write_csv_dict(path, rows):
    if not rows:
        raise ValueError(f"No rows to write: {path}")

    with open(
        path,
        "w",
        encoding="utf-8",
        newline=""
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=list(rows[0].keys())
        )
        writer.writeheader()
        writer.writerows(rows)


def f(value):
    x = float(value)

    if not math.isfinite(x):
        raise ValueError(
            f"Non-finite numeric value: {value}"
        )

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

    return (
        xs[lo] * (1.0 - frac)
        + xs[hi] * frac
    )


# ------------------------------------------------------------
# 1. PREFLIGHT
# ------------------------------------------------------------

for p in [FALLBACK_RAW, LOO, LOO_AGE]:
    if not p.exists():
        raise FileNotFoundError(p)

fallback = read_csv_dict(FALLBACK_RAW)
loo = read_csv_dict(LOO)
loo_age_old = read_csv_dict(LOO_AGE)

if len(fallback) != 166:
    raise ValueError(
        f"Expected 166 fallback rows; got {len(fallback)}."
    )

if len(loo) != 654:
    raise ValueError(
        f"Expected 654 LOO rows; got {len(loo)}."
    )

print("Fallback rows                  :", len(fallback))
print("LOO diagnostic rows            :", len(loo))


# ------------------------------------------------------------
# 2. RAW LOO DIAGNOSTICS
# ------------------------------------------------------------

raw_contained = 0
miss_distances = []
abs_errors = []

for r in loo:

    actual = f(
        r["PALMSIM_DIRECT_T_FFB_HA_YR"]
    )

    p10 = f(
        r["RECONSTRUCTED_P10_T_FFB_HA_YR"]
    )

    p50 = f(
        r["RECONSTRUCTED_P50_T_FFB_HA_YR"]
    )

    p90 = f(
        r["RECONSTRUCTED_P90_T_FFB_HA_YR"]
    )

    if p10 <= actual <= p90:
        raw_contained += 1
        miss = 0.0

    elif actual < p10:
        miss = p10 - actual

    else:
        miss = actual - p90

    miss_distances.append(
        miss
    )

    abs_errors.append(
        abs(p50 - actual)
    )

raw_containment_pct = (
    100.0
    * raw_contained
    / len(loo)
)

# Conservative global expansion because recipient age is unknown.
# Q95 means the final interval is explicitly wide enough to absorb
# most LOO misses seen when age is withheld.
EXPANSION_Q = 0.95

expansion_margin = quantile(
    miss_distances,
    EXPANSION_Q
)

if expansion_margin is None:
    raise ValueError(
        "Could not compute expansion margin."
    )

print(
    "Raw P10-P90 containment       :",
    raw_containment_pct,
    "%"
)

print(
    "Q95 miss-distance expansion   :",
    expansion_margin,
    "t FFB/ha/yr"
)


# ------------------------------------------------------------
# 3. APPLY SAME EXPANSION TO LOO FOR DIAGNOSTIC
# ------------------------------------------------------------

calibrated_loo = []

for r in loo:

    actual = f(
        r["PALMSIM_DIRECT_T_FFB_HA_YR"]
    )

    raw_low = f(
        r["RECONSTRUCTED_P10_T_FFB_HA_YR"]
    )

    center = f(
        r["RECONSTRUCTED_P50_T_FFB_HA_YR"]
    )

    raw_high = f(
        r["RECONSTRUCTED_P90_T_FFB_HA_YR"]
    )

    low = max(
        0.0,
        raw_low - expansion_margin
    )

    high = (
        raw_high
        + expansion_margin
    )

    contained = (
        low <= actual <= high
    )

    calibrated_loo.append({
        "UNIT_ID":
            r["UNIT_ID"],

        "AGE_P50":
            r["AGE_P50"],

        "AGE_GROUP":
            r["AGE_GROUP"],

        "PALMSIM_DIRECT_T_FFB_HA_YR":
            actual,

        "RAW_P10_T_FFB_HA_YR":
            raw_low,

        "INDICATIVE_CENTER_P50_T_FFB_HA_YR":
            center,

        "RAW_P90_T_FFB_HA_YR":
            raw_high,

        "CALIBRATED_LOW_T_FFB_HA_YR":
            low,

        "CALIBRATED_HIGH_T_FFB_HA_YR":
            high,

        "CALIBRATED_RANGE_WIDTH_T_HA_YR":
            high - low,

        "DIRECT_WITHIN_CALIBRATED_RANGE":
            "YES" if contained else "NO",
    })


calibrated_contained = sum(
    1
    for r in calibrated_loo
    if r["DIRECT_WITHIN_CALIBRATED_RANGE"]
    == "YES"
)

calibrated_containment_pct = (
    100.0
    * calibrated_contained
    / len(calibrated_loo)
)


# ------------------------------------------------------------
# 4. AGE-GROUP DIAGNOSTICS AFTER CALIBRATION
# ------------------------------------------------------------

age_order = [
    "AGE_0_3",
    "AGE_4_7",
    "AGE_8_12",
    "AGE_13_18",
    "AGE_19_PLUS",
]

age_summary = []

for group in age_order:

    subset = [
        r
        for r in calibrated_loo
        if r["AGE_GROUP"] == group
    ]

    if not subset:
        continue

    contained = sum(
        1
        for r in subset
        if r[
            "DIRECT_WITHIN_CALIBRATED_RANGE"
        ] == "YES"
    )

    widths = [
        r[
            "CALIBRATED_RANGE_WIDTH_T_HA_YR"
        ]
        for r in subset
    ]

    age_summary.append({
        "AGE_GROUP":
            group,

        "N_ASU":
            len(subset),

        "CALIBRATED_CONTAINMENT_PCT":
            100.0
            * contained
            / len(subset),

        "MEDIAN_CALIBRATED_RANGE_WIDTH_T_HA_YR":
            statistics.median(
                widths
            ),
    })

write_csv_dict(
    OUT_AGE,
    age_summary
)


# ------------------------------------------------------------
# 5. FREEZE FALLBACK 166
# ------------------------------------------------------------

frozen = []

for r in fallback:

    raw_low = f(
        r[
            "INDICATIVE_P10_T_FFB_HA_YR"
        ]
    )

    center = f(
        r[
            "INDICATIVE_P50_T_FFB_HA_YR"
        ]
    )

    raw_high = f(
        r[
            "INDICATIVE_P90_T_FFB_HA_YR"
        ]
    )

    final_low = max(
        0.0,
        raw_low - expansion_margin
    )

    final_high = (
        raw_high
        + expansion_margin
    )

    confidence = r[
        "FALLBACK_CONFIDENCE"
    ]

    if confidence not in {
        "LOW",
        "VERY_LOW",
    }:
        confidence = "VERY_LOW"

    frozen.append({
        "UNIT_ID":
            r["UNIT_ID"],

        "PRODUCTIVITY_ESTIMATE_TYPE":
            "INDICATIVE_PEER_BASED_FALLBACK",

        "DISPLAY_CENTER_T_FFB_HA_YR":
            center,

        "FINAL_INDICATIVE_LOW_T_FFB_HA_YR":
            final_low,

        "FINAL_INDICATIVE_HIGH_T_FFB_HA_YR":
            final_high,

        "FINAL_INDICATIVE_RANGE_WIDTH_T_HA_YR":
            final_high - final_low,

        "RAW_PEER_P10_T_FFB_HA_YR":
            raw_low,

        "RAW_PEER_P50_T_FFB_HA_YR":
            center,

        "RAW_PEER_P90_T_FFB_HA_YR":
            raw_high,

        "LOO_INTERVAL_EXPANSION_Q":
            EXPANSION_Q,

        "LOO_INTERVAL_EXPANSION_MARGIN_T_HA_YR":
            expansion_margin,

        "CLIMATE_PAIR_ID":
            r["CLIMATE_PAIR_ID"],

        "CLIMATE_MATCH_TIER":
            r["CLIMATE_MATCH_TIER"],

        "FEATURE_MODE":
            r["FEATURE_MODE"],

        "SELECTED_PEER_N":
            r["SELECTED_PEER_N"],

        "DONOR_POOL_N":
            r["DONOR_POOL_N"],

        "PEER_DISTANCE_MEDIAN":
            r["PEER_DISTANCE_MEDIAN"],

        "FALLBACK_CONFIDENCE":
            confidence,

        "AGE_STATUS":
            "NUMERIC_AGE_UNAVAILABLE",

        "AGE_TREATMENT":
            "NOT_FABRICATED",

        "DIRECT_PALMSIM":
            "NO",

        "APSIM_INTERPOLATED":
            "NO",

        "LOCAL_FFB_VALIDATED":
            "NO",

        "SAFE_DISPLAY_LABEL":
            "Indicative Productivity Potential",

        "POPUP_WARNING":
            (
                "Age proxy unresolved; indicative range derived "
                "from climate-soil-condition peers and widened "
                "using internal LOO reconstruction miss-distance."
            ),

        "FREEZE_VERSION":
            "40E03C_V1",
    })

write_csv_dict(
    OUT_FROZEN,
    frozen
)


# ------------------------------------------------------------
# 6. FROZEN OUTPUT SUMMARY
# ------------------------------------------------------------

centers = [
    r["DISPLAY_CENTER_T_FFB_HA_YR"]
    for r in frozen
]

final_widths = [
    r[
        "FINAL_INDICATIVE_RANGE_WIDTH_T_HA_YR"
    ]
    for r in frozen
]

final_lows = [
    r["FINAL_INDICATIVE_LOW_T_FFB_HA_YR"]
    for r in frozen
]

final_highs = [
    r["FINAL_INDICATIVE_HIGH_T_FFB_HA_YR"]
    for r in frozen
]

low_count = sum(
    1
    for r in frozen
    if r["FALLBACK_CONFIDENCE"] == "LOW"
)

very_low_count = sum(
    1
    for r in frozen
    if r["FALLBACK_CONFIDENCE"] == "VERY_LOW"
)


# ------------------------------------------------------------
# 7. QC / FREEZE GATE
# ------------------------------------------------------------

checks = {
    "fallback_rows_166":
        len(frozen) == 166,

    "fallback_unique_asu_166":
        len({
            r["UNIT_ID"]
            for r in frozen
        }) == 166,

    "all_final_ranges_finite":
        all(
            math.isfinite(
                r[
                    "FINAL_INDICATIVE_LOW_T_FFB_HA_YR"
                ]
            )
            and math.isfinite(
                r[
                    "DISPLAY_CENTER_T_FFB_HA_YR"
                ]
            )
            and math.isfinite(
                r[
                    "FINAL_INDICATIVE_HIGH_T_FFB_HA_YR"
                ]
            )
            for r in frozen
        ),

    "all_final_ranges_ordered":
        all(
            r[
                "FINAL_INDICATIVE_LOW_T_FFB_HA_YR"
            ]
            <= r[
                "DISPLAY_CENTER_T_FFB_HA_YR"
            ]
            <= r[
                "FINAL_INDICATIVE_HIGH_T_FFB_HA_YR"
            ]
            for r in frozen
        ),

    "no_negative_lower_bounds":
        all(
            r[
                "FINAL_INDICATIVE_LOW_T_FFB_HA_YR"
            ] >= 0
            for r in frozen
        ),

    "age_not_fabricated":
        all(
            r["AGE_TREATMENT"]
            == "NOT_FABRICATED"
            for r in frozen
        ),

    "no_direct_palmsim_claim":
        all(
            r["DIRECT_PALMSIM"] == "NO"
            for r in frozen
        ),

    "no_apsim_interpolation":
        all(
            r["APSIM_INTERPOLATED"] == "NO"
            for r in frozen
        ),

    "local_ffb_validation_not_claimed":
        all(
            r["LOCAL_FFB_VALIDATED"] == "NO"
            for r in frozen
        ),

    "loo_calibrated_containment_at_least_90pct":
        calibrated_containment_pct >= 90.0,
}

status = (
    "PASS_FALLBACK_METHOD_FROZEN"
    if all(checks.values())
    else "REVIEW"
)


# ------------------------------------------------------------
# 8. SAVE QC JSON
# ------------------------------------------------------------

qc = {
    "gate":
        "40E03C_FALLBACK_PRODUCTIVITY_INTERVAL_CALIBRATION_AND_FREEZE",

    "status":
        status,

    "decision": {
        "raw_40E03B_peer_method":
            "RETAINED_WITH_CONSERVATIVE_INTERVAL_EXPANSION",

        "indicative_center":
            "RAW_PEER_P50_RETAINED",

        "final_interval":
            (
                "RAW_P10_P90 widened symmetrically by global "
                "Q95 LOO miss-distance; lower bound clipped at 0"
            ),

        "reason":
            (
                "40E03B reconstructed PALMSIM only moderately "
                "without age; raw P10-P90 containment was 77.37%, "
                "and age-specific performance was weak for some "
                "young-age groups. Recipient age is unknown, so "
                "a conservative global expansion is retained."
            ),

        "confidence":
            "LOW_OR_VERY_LOW_ONLY",

        "actual_ffb_validation":
            "NO",
    },

    "calibration": {
        "loo_rows":
            len(loo),

        "raw_p10_p90_containment_pct":
            raw_containment_pct,

        "expansion_quantile":
            EXPANSION_Q,

        "expansion_margin_t_ha_yr":
            expansion_margin,

        "calibrated_loo_containment_pct":
            calibrated_containment_pct,

        "loo_p95_absolute_center_error_t_ha_yr":
            quantile(
                abs_errors,
                0.95
            ),
    },

    "calibrated_loo_by_age":
        age_summary,

    "frozen_fallback_summary": {
        "rows":
            len(frozen),

        "center_min_t_ha_yr":
            min(centers),

        "center_median_t_ha_yr":
            statistics.median(
                centers
            ),

        "center_max_t_ha_yr":
            max(centers),

        "final_low_min_t_ha_yr":
            min(final_lows),

        "final_high_max_t_ha_yr":
            max(final_highs),

        "median_final_range_width_t_ha_yr":
            statistics.median(
                final_widths
            ),

        "p95_final_range_width_t_ha_yr":
            quantile(
                final_widths,
                0.95
            ),

        "low_confidence_count":
            low_count,

        "very_low_confidence_count":
            very_low_count,
    },

    "interpretation_limits": [
        "The indicative center is not a direct process-model simulation for the 166 fallback ASUs.",
        "The final interval is an uncertainty-oriented peer range calibrated only against direct PALMSIM reconstruction, not observed FFB.",
        "Unknown age remains unresolved and is not imputed as a planting year.",
        "The fallback output must be visually distinguished from direct PALMSIM in maps/popups.",
        "No local accuracy percentage may be claimed from this internal reconstruction diagnostic.",
        "Management Priority classification is downstream and must not treat fallback and direct pathways as equal-confidence evidence.",
    ],

    "checks":
        checks,

    "next":
        "40F01 wall-to-wall Productivity Potential synthesis for all 820 ASUs.",
}

with open(
    OUT_QC,
    "w",
    encoding="utf-8"
) as f:
    json.dump(
        qc,
        f,
        indent=2
    )


# ------------------------------------------------------------
# 9. PRINT
# ------------------------------------------------------------

print("\n====================================================")
print("40E03C FINISHED")
print("====================================================")
print("Status                         :", status)

print("\n40E03B INTERPRETATION")
print(
    "Raw LOO P10-P90 containment   :",
    raw_containment_pct,
    "%"
)
print(
    "Q95 miss-distance expansion   :",
    expansion_margin,
    "t FFB/ha/yr"
)
print(
    "Calibrated LOO containment    :",
    calibrated_containment_pct,
    "%"
)

print("\nCALIBRATED LOO BY AGE")
for r in age_summary:
    print(
        r["AGE_GROUP"],
        "| N =", r["N_ASU"],
        "| containment =",
        round(
            r["CALIBRATED_CONTAINMENT_PCT"],
            2
        ),
        "%",
        "| median width =",
        round(
            r[
                "MEDIAN_CALIBRATED_RANGE_WIDTH_T_HA_YR"
            ],
            3
        )
    )

print("\nFROZEN FALLBACK 166")
print("Rows                           :", len(frozen))
print(
    "Center min/median/max          :",
    min(centers),
    "/",
    statistics.median(centers),
    "/",
    max(centers)
)
print(
    "Median final range width       :",
    statistics.median(final_widths),
    "t FFB/ha/yr"
)
print(
    "Final low minimum              :",
    min(final_lows)
)
print(
    "Final high maximum             :",
    max(final_highs)
)
print("LOW confidence                 :", low_count)
print("VERY_LOW confidence            :", very_low_count)

print("\nQC:")
for key, value in checks.items():
    print(
        f"{key:52s}: {value}"
    )

print("\nFrozen fallback CSV :", OUT_FROZEN)
print("Age diagnostic CSV :", OUT_AGE)
print("Freeze/QC JSON      :", OUT_QC)

if status == "PASS_FALLBACK_METHOD_FROZEN":
    print(
        "Next                : 40F01 wall-to-wall Productivity "
        "Potential synthesis for 820 ASUs."
    )
else:
    print(
        "Next                : Review fallback calibration before 40F."
    )

print("====================================================")
