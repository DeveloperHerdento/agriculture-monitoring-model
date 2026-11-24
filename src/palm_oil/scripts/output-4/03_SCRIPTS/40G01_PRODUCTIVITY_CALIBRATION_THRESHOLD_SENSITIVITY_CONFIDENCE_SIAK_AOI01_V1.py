# ============================================================
# OUTPUT 4 / 40G01
# PRODUCTIVITY REFERENCE CALIBRATION
# + THRESHOLD SENSITIVITY
# + CONFIDENCE / UNCERTAINTY DESIGN
# SIAK_AOI01
#
# PURE PYTHON STANDARD LIBRARY ONLY
# NO numpy / pandas / scipy
# NO PALMSIM/APSIM rerun
#
# PURPOSE
# -------
# 1) Build a RELATIVE productivity reference from the 654 direct
#    PALMSIM ASUs only.
# 2) Assign preliminary relative productivity bands to all 820 ASUs.
# 3) Test threshold sensitivity (Q20/Q80, Q25/Q75, Q30/Q70).
# 4) Add structural model-disagreement diagnostics from 40E01B.
# 5) Build preliminary confidence tiers:
#       MODERATE / LOW / VERY_LOW
#    with NO HIGH confidence because there is no local actual FFB
#    validation.
#
# IMPORTANT
# ---------
# - Productivity bands are RELATIVE / PILOT classes, not agronomic
#   yield standards.
# - Fallback ASUs may receive a center-based relative band, but
#   their wide uncertainty interval is retained and checked for
#   cross-band instability.
# - Final Output-4 management class 0-4 is NOT assigned here.
#
# Next:
# 40G02 = inspect sensitivity + freeze/adjust thresholds and confidence
#          before 40H management-priority integration.
# ============================================================

from pathlib import Path
import csv
import json
import math
import statistics

WORKDIR = Path(
    r"C:\Users\user\Documents\KERJA\SPATIAL DATA ANALYST INTERN\04_YIELD"
)

MASTER = WORKDIR / (
    "40F01_WALL_TO_WALL_PRODUCTIVITY_POTENTIAL_820_SIAK_AOI01_V1.csv"
)

AGE_DIAG = WORKDIR / (
    "40E01B_AGE_DISCREPANCY_SUMMARY_SIAK_AOI01_V1.csv"
)

CLIMATE_DIAG = WORKDIR / (
    "40E01B_CLIMATE_PAIR_DISCREPANCY_SUMMARY_SIAK_AOI01_V1.csv"
)

OUT_MASTER = WORKDIR / (
    "40G01_PRODUCTIVITY_CALIBRATION_CONFIDENCE_820_SIAK_AOI01_V1.csv"
)

OUT_SENS = WORKDIR / (
    "40G01_PRODUCTIVITY_THRESHOLD_SENSITIVITY_SIAK_AOI01_V1.csv"
)

OUT_QC = WORKDIR / (
    "40G01_PRODUCTIVITY_CALIBRATION_CONFIDENCE_QC_SIAK_AOI01_V1.json"
)

print("====================================================")
print("40G01 — PRODUCTIVITY CALIBRATION + CONFIDENCE DESIGN")
print("PURE PYTHON / NO MODEL RERUN")
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


def empirical_percentile(value, reference):
    """
    Mid-rank empirical percentile in [0,100].
    """
    less = sum(1 for x in reference if x < value)
    equal = sum(1 for x in reference if x == value)

    pct = (
        less + 0.5 * equal
    ) / len(reference) * 100.0

    return pct


def potential_band(value, low_thr, high_thr):
    if value <= low_thr:
        return "RELATIVE_LOW"
    elif value >= high_thr:
        return "RELATIVE_HIGH"
    else:
        return "RELATIVE_TYPICAL"


def age_group(age):
    if age is None:
        return "AGE_UNKNOWN"

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


def relative_tier(value, q1, q2):
    if value <= q1:
        return "RELATIVE_LOW"
    elif value <= q2:
        return "RELATIVE_MODERATE"
    else:
        return "RELATIVE_HIGH"


# ------------------------------------------------------------
# 1. PREFLIGHT
# ------------------------------------------------------------

for p in [MASTER, AGE_DIAG, CLIMATE_DIAG]:
    if not p.exists():
        raise FileNotFoundError(p)

rows = read_csv_dict(MASTER)
age_diag_rows = read_csv_dict(AGE_DIAG)
climate_diag_rows = read_csv_dict(CLIMATE_DIAG)

if len(rows) != 820:
    raise ValueError(
        f"Expected 820 40F01 rows; got {len(rows)}."
    )

if len(age_diag_rows) != 5:
    raise ValueError(
        f"Expected 5 age diagnostics; got {len(age_diag_rows)}."
    )

if len(climate_diag_rows) != 12:
    raise ValueError(
        f"Expected 12 climate diagnostics; got {len(climate_diag_rows)}."
    )

if len({r["UNIT_ID"] for r in rows}) != 820:
    raise ValueError(
        "40F01 UNIT_ID is not unique."
    )

direct_rows = [
    r for r in rows
    if r["PRODUCTIVITY_PATHWAY"]
    == "DIRECT_MODEL_SUPPORTED"
]

fallback_rows = [
    r for r in rows
    if r["PRODUCTIVITY_PATHWAY"]
    == "AGE_CENSORED_OR_UNRESOLVED_FALLBACK"
]

if len(direct_rows) != 654:
    raise ValueError(
        f"Expected 654 direct rows; got {len(direct_rows)}."
    )

if len(fallback_rows) != 166:
    raise ValueError(
        f"Expected 166 fallback rows; got {len(fallback_rows)}."
    )

print("Master ASUs                    :", len(rows))
print("Direct reference ASUs          :", len(direct_rows))
print("Fallback ASUs                  :", len(fallback_rows))


# ------------------------------------------------------------
# 2. DIRECT PALMSIM REFERENCE DISTRIBUTION
# ------------------------------------------------------------

direct_reference = [
    float(
        r[
            "PRODUCTIVITY_CENTER_T_FFB_HA_YR"
        ]
    )
    for r in direct_rows
]

if not all(
    math.isfinite(x)
    for x in direct_reference
):
    raise ValueError(
        "Non-finite direct reference productivity."
    )

# Baseline candidate = quartile tails.
Q25 = quantile(direct_reference, 0.25)
Q75 = quantile(direct_reference, 0.75)

# Alternative sensitivity schemes.
Q20 = quantile(direct_reference, 0.20)
Q80 = quantile(direct_reference, 0.80)

Q30 = quantile(direct_reference, 0.30)
Q70 = quantile(direct_reference, 0.70)

print("\nDIRECT PALMSIM REFERENCE")
print("Min                            :", min(direct_reference))
print("Q20                            :", Q20)
print("Q25                            :", Q25)
print("Q30                            :", Q30)
print("Median                         :", statistics.median(direct_reference))
print("Q70                            :", Q70)
print("Q75                            :", Q75)
print("Q80                            :", Q80)
print("Max                            :", max(direct_reference))


# ------------------------------------------------------------
# 3. LOAD MODEL-DISAGREEMENT DIAGNOSTICS
# ------------------------------------------------------------

age_mae = {
    r["AGE_GROUP"]: float(
        r["MAE_T_HA_YR"]
    )
    for r in age_diag_rows
}

climate_mae = {
    r["CLIMATE_PAIR_ID"]: float(
        r["MAE_T_HA_YR"]
    )
    for r in climate_diag_rows
}

# Build structural proxy for direct ASUs only:
# max(age-group MAE, climate-pair MAE).
# This remains a representative model-disagreement diagnostic,
# not observed prediction error.
direct_structural_proxy = []

for r in direct_rows:

    age = to_float_or_none(
        r.get("AGE_P50")
    )

    ag = age_group(age)

    pair = r["CLIMATE_PAIR_ID"]

    if ag not in age_mae:
        raise KeyError(
            f"Missing age diagnostic: {ag}"
        )

    if pair not in climate_mae:
        raise KeyError(
            f"Missing climate diagnostic: {pair}"
        )

    proxy = max(
        age_mae[ag],
        climate_mae[pair]
    )

    direct_structural_proxy.append(
        proxy
    )

STRUCT_Q33 = quantile(
    direct_structural_proxy,
    1.0 / 3.0
)

STRUCT_Q67 = quantile(
    direct_structural_proxy,
    2.0 / 3.0
)

print("\nSTRUCTURAL DISAGREEMENT REFERENCE")
print("Q33                            :", STRUCT_Q33)
print("Q67                            :", STRUCT_Q67)


# ------------------------------------------------------------
# 4. PRODUCTIVITY CLASS SENSITIVITY
# ------------------------------------------------------------

schemes = [
    ("Q20_Q80", Q20, Q80),
    ("Q25_Q75_BASELINE", Q25, Q75),
    ("Q30_Q70", Q30, Q70),
]

sens_rows = []

# Track per-ASU bands for switch rates.
band_by_scheme = {}

for name, low_thr, high_thr in schemes:

    assignment = {}

    for r in rows:

        uid = r["UNIT_ID"]

        center = float(
            r[
                "PRODUCTIVITY_CENTER_T_FFB_HA_YR"
            ]
        )

        assignment[uid] = potential_band(
            center,
            low_thr,
            high_thr
        )

    band_by_scheme[name] = assignment

    counts_all = {
        "RELATIVE_LOW": 0,
        "RELATIVE_TYPICAL": 0,
        "RELATIVE_HIGH": 0,
    }

    counts_direct = counts_all.copy()
    counts_fallback = counts_all.copy()

    for r in rows:
        uid = r["UNIT_ID"]
        b = assignment[uid]

        counts_all[b] += 1

        if r["PRODUCTIVITY_PATHWAY"] == "DIRECT_MODEL_SUPPORTED":
            counts_direct[b] += 1
        else:
            counts_fallback[b] += 1

    sens_rows.append({
        "SCHEME":
            name,

        "LOW_THRESHOLD_T_HA_YR":
            low_thr,

        "HIGH_THRESHOLD_T_HA_YR":
            high_thr,

        "ALL_LOW_N":
            counts_all["RELATIVE_LOW"],

        "ALL_TYPICAL_N":
            counts_all["RELATIVE_TYPICAL"],

        "ALL_HIGH_N":
            counts_all["RELATIVE_HIGH"],

        "DIRECT_LOW_N":
            counts_direct["RELATIVE_LOW"],

        "DIRECT_TYPICAL_N":
            counts_direct["RELATIVE_TYPICAL"],

        "DIRECT_HIGH_N":
            counts_direct["RELATIVE_HIGH"],

        "FALLBACK_LOW_N":
            counts_fallback["RELATIVE_LOW"],

        "FALLBACK_TYPICAL_N":
            counts_fallback["RELATIVE_TYPICAL"],

        "FALLBACK_HIGH_N":
            counts_fallback["RELATIVE_HIGH"],
    })


# Switch rate relative to baseline Q25/Q75
baseline_assign = band_by_scheme[
    "Q25_Q75_BASELINE"
]

for rec in sens_rows:

    name = rec["SCHEME"]

    current = band_by_scheme[name]

    all_switch = sum(
        1
        for uid in baseline_assign
        if current[uid] != baseline_assign[uid]
    )

    direct_switch = sum(
        1
        for r in direct_rows
        if current[r["UNIT_ID"]]
        != baseline_assign[r["UNIT_ID"]]
    )

    fallback_switch = sum(
        1
        for r in fallback_rows
        if current[r["UNIT_ID"]]
        != baseline_assign[r["UNIT_ID"]]
    )

    rec["SWITCH_FROM_BASELINE_ALL_N"] = all_switch
    rec["SWITCH_FROM_BASELINE_ALL_PCT"] = (
        100.0 * all_switch / 820.0
    )

    rec["SWITCH_FROM_BASELINE_DIRECT_N"] = direct_switch
    rec["SWITCH_FROM_BASELINE_DIRECT_PCT"] = (
        100.0 * direct_switch / 654.0
    )

    rec["SWITCH_FROM_BASELINE_FALLBACK_N"] = fallback_switch
    rec["SWITCH_FROM_BASELINE_FALLBACK_PCT"] = (
        100.0 * fallback_switch / 166.0
    )

write_csv_dict(
    OUT_SENS,
    sens_rows
)


# ------------------------------------------------------------
# 5. BUILD 820-ASU CALIBRATION + CONFIDENCE TABLE
# ------------------------------------------------------------

out = []

for r in rows:

    uid = r["UNIT_ID"]

    pathway = r[
        "PRODUCTIVITY_PATHWAY"
    ]

    center = float(
        r[
            "PRODUCTIVITY_CENTER_T_FFB_HA_YR"
        ]
    )

    percentile = empirical_percentile(
        center,
        direct_reference
    )

    baseline_band = potential_band(
        center,
        Q25,
        Q75
    )

    age = to_float_or_none(
        r.get("AGE_P50")
    )

    age_valid = to_float_or_none(
        r.get("AGE_VALID_FRACTION")
    )

    cond_valid = to_float_or_none(
        r.get("CONDITION_VALID_FRACTION")
    )

    pair = r["CLIMATE_PAIR_ID"]

    # --------------------------------------------------------
    # Structural disagreement proxy
    # --------------------------------------------------------

    if pathway == "DIRECT_MODEL_SUPPORTED":

        ag = age_group(age)

        structural_proxy = max(
            age_mae[ag],
            climate_mae[pair]
        )

        structural_source = (
            "MAX_REPRESENTATIVE_AGE_MAE_AND_CLIMATE_PAIR_MAE"
        )

    else:
        # Age unresolved: do NOT assign an age group.
        # Use climate-pair disagreement only and keep fallback
        # uncertainty separately.
        structural_proxy = (
            climate_mae[pair]
        )

        structural_source = (
            "REPRESENTATIVE_CLIMATE_PAIR_MAE_ONLY__AGE_UNKNOWN"
        )

    structural_tier = relative_tier(
        structural_proxy,
        STRUCT_Q33,
        STRUCT_Q67
    )

    # --------------------------------------------------------
    # Data support
    # --------------------------------------------------------
    #
    # Transparent pilot support thresholds:
    # - age >=0.50 means majority of ASU has valid age evidence
    # - age >=0.25 means at least quarter support
    # - condition >=0.80 strong, >=0.50 moderate
    #
    # These are internal support thresholds, NOT validation metrics.
    # They will be frozen/adjusted in 40G02 after diagnostics.
    # --------------------------------------------------------

    if pathway == "DIRECT_MODEL_SUPPORTED":

        if (
            age_valid is not None
            and cond_valid is not None
            and age_valid >= 0.50
            and cond_valid >= 0.80
        ):
            data_support = "STRONG"

        elif (
            age_valid is not None
            and cond_valid is not None
            and age_valid >= 0.25
            and cond_valid >= 0.50
        ):
            data_support = "MODERATE"

        else:
            data_support = "LIMITED"

    else:
        # No numeric age -> cannot be STRONG/MODERATE
        # for productivity modelling.
        data_support = "LIMITED"

    # --------------------------------------------------------
    # Fallback interval band stability
    # --------------------------------------------------------

    low_value = to_float_or_none(
        r.get(
            "PRODUCTIVITY_LOW_T_FFB_HA_YR"
        )
    )

    high_value = to_float_or_none(
        r.get(
            "PRODUCTIVITY_HIGH_T_FFB_HA_YR"
        )
    )

    if pathway == "AGE_CENSORED_OR_UNRESOLVED_FALLBACK":

        if low_value is None or high_value is None:
            raise ValueError(
                f"Fallback interval missing: {uid}"
            )

        low_band = potential_band(
            low_value,
            Q25,
            Q75
        )

        high_band = potential_band(
            high_value,
            Q25,
            Q75
        )

        if low_band == high_band:
            interval_band_stability = (
                "STABLE_WITHIN_ONE_BAND"
            )
        else:
            interval_band_stability = (
                "UNCERTAIN_SPANS_MULTIPLE_BANDS"
            )

        interval_band_span = (
            low_band + "__TO__" + high_band
        )

    else:
        low_band = ""
        high_band = ""
        interval_band_stability = (
            "DIRECT_INTERVAL_PENDING"
        )
        interval_band_span = ""

    # --------------------------------------------------------
    # Preliminary confidence tier
    # --------------------------------------------------------
    #
    # No HIGH confidence exists in current Route A because
    # there is no local actual FFB validation.
    # --------------------------------------------------------

    if pathway == "DIRECT_MODEL_SUPPORTED":

        if (
            data_support == "STRONG"
            and structural_tier
            in {
                "RELATIVE_LOW",
                "RELATIVE_MODERATE",
            }
        ):
            confidence = "MODERATE"

        elif (
            data_support == "LIMITED"
            and structural_tier == "RELATIVE_HIGH"
        ):
            confidence = "VERY_LOW"

        else:
            confidence = "LOW"

    else:
        existing_fb_conf = str(
            r.get(
                "PRODUCTIVITY_CONFIDENCE_PRELIM",
                ""
            )
        ).strip()

        # Preserve frozen fallback cap.
        if existing_fb_conf == "LOW":
            confidence = "LOW"
        else:
            confidence = "VERY_LOW"

        # If interval spans multiple productivity bands,
        # never upgrade above LOW (already enforced).
        if (
            interval_band_stability
            == "UNCERTAIN_SPANS_MULTIPLE_BANDS"
            and confidence not in {"LOW", "VERY_LOW"}
        ):
            confidence = "LOW"

    # --------------------------------------------------------
    # Reason code
    # --------------------------------------------------------

    reasons = []

    if pathway == "DIRECT_MODEL_SUPPORTED":
        reasons.append("DIRECT_PALMSIM")
    else:
        reasons.append("AGE_UNRESOLVED_FALLBACK")

    reasons.append(
        "STRUCTURAL_" + structural_tier
    )

    reasons.append(
        "DATA_SUPPORT_" + data_support
    )

    if (
        interval_band_stability
        == "UNCERTAIN_SPANS_MULTIPLE_BANDS"
    ):
        reasons.append(
            "FALLBACK_INTERVAL_SPANS_BANDS"
        )

    out.append({
        **r,

        "PRODUCTIVITY_REFERENCE":
            "DIRECT_PALMSIM_654",

        "PRODUCTIVITY_PERCENTILE_VS_DIRECT_0_100":
            percentile,

        "PRODUCTIVITY_BAND_BASELINE":
            baseline_band,

        "PRODUCTIVITY_BAND_SCHEMA":
            "Q25_Q75_RELATIVE_PILOT",

        "PRODUCTIVITY_LOW_THRESHOLD_T_HA_YR":
            Q25,

        "PRODUCTIVITY_HIGH_THRESHOLD_T_HA_YR":
            Q75,

        "STRUCTURAL_MODEL_DISAGREEMENT_PROXY_T_HA_YR":
            structural_proxy,

        "STRUCTURAL_MODEL_DISAGREEMENT_TIER":
            structural_tier,

        "STRUCTURAL_PROXY_SOURCE":
            structural_source,

        "DATA_SUPPORT_TIER":
            data_support,

        "FALLBACK_INTERVAL_LOW_BAND":
            low_band,

        "FALLBACK_INTERVAL_HIGH_BAND":
            high_band,

        "FALLBACK_INTERVAL_BAND_STABILITY":
            interval_band_stability,

        "FALLBACK_INTERVAL_BAND_SPAN":
            interval_band_span,

        "PRODUCTIVITY_CONFIDENCE_40G01":
            confidence,

        "CONFIDENCE_HIGH_ALLOWED":
            "NO_NO_LOCAL_FFB_VALIDATION",

        "PRODUCTIVITY_REASON_CODES_40G01":
            ";".join(reasons),

        "PRODUCTIVITY_CLASS":
            "PENDING_40G02_FREEZE",

        "MANAGEMENT_PRIORITY_CLASS":
            "PENDING_40H",

        "CALIBRATION_VERSION":
            "40G01_V1",
    })

write_csv_dict(
    OUT_MASTER,
    out
)


# ------------------------------------------------------------
# 6. DIAGNOSTIC COUNTS
# ------------------------------------------------------------

baseline_counts = {
    "RELATIVE_LOW": 0,
    "RELATIVE_TYPICAL": 0,
    "RELATIVE_HIGH": 0,
}

confidence_counts = {
    "MODERATE": 0,
    "LOW": 0,
    "VERY_LOW": 0,
}

support_counts = {
    "STRONG": 0,
    "MODERATE": 0,
    "LIMITED": 0,
}

struct_counts = {
    "RELATIVE_LOW": 0,
    "RELATIVE_MODERATE": 0,
    "RELATIVE_HIGH": 0,
}

fallback_stability_counts = {
    "STABLE_WITHIN_ONE_BAND": 0,
    "UNCERTAIN_SPANS_MULTIPLE_BANDS": 0,
}

for r in out:

    baseline_counts[
        r["PRODUCTIVITY_BAND_BASELINE"]
    ] += 1

    confidence_counts[
        r["PRODUCTIVITY_CONFIDENCE_40G01"]
    ] += 1

    support_counts[
        r["DATA_SUPPORT_TIER"]
    ] += 1

    struct_counts[
        r[
            "STRUCTURAL_MODEL_DISAGREEMENT_TIER"
        ]
    ] += 1

    if (
        r["PRODUCTIVITY_PATHWAY"]
        == "AGE_CENSORED_OR_UNRESOLVED_FALLBACK"
    ):
        fallback_stability_counts[
            r[
                "FALLBACK_INTERVAL_BAND_STABILITY"
            ]
        ] += 1


# ------------------------------------------------------------
# 7. QC
# ------------------------------------------------------------

checks = {
    "rows_820":
        len(out) == 820,

    "unique_asu_820":
        len({
            r["UNIT_ID"]
            for r in out
        }) == 820,

    "direct_reference_654":
        len(direct_reference) == 654,

    "baseline_thresholds_ordered":
        min(direct_reference)
        <= Q25
        <= Q75
        <= max(direct_reference),

    "all_percentiles_0_100":
        all(
            0.0
            <= r[
                "PRODUCTIVITY_PERCENTILE_VS_DIRECT_0_100"
            ]
            <= 100.0
            for r in out
        ),

    "all_productivity_bands_assigned":
        all(
            r["PRODUCTIVITY_BAND_BASELINE"]
            in {
                "RELATIVE_LOW",
                "RELATIVE_TYPICAL",
                "RELATIVE_HIGH",
            }
            for r in out
        ),

    "all_confidence_assigned":
        all(
            r["PRODUCTIVITY_CONFIDENCE_40G01"]
            in {
                "MODERATE",
                "LOW",
                "VERY_LOW",
            }
            for r in out
        ),

    "no_high_confidence":
        all(
            r["PRODUCTIVITY_CONFIDENCE_40G01"]
            != "HIGH"
            for r in out
        ),

    "fallback_166_interval_stability_checked":
        sum(
            fallback_stability_counts.values()
        ) == 166,

    "structural_diagnostic_assigned_all_820":
        sum(
            struct_counts.values()
        ) == 820,

    "sensitivity_schemes_3":
        len(sens_rows) == 3,

    "final_productivity_class_not_frozen_yet":
        all(
            r["PRODUCTIVITY_CLASS"]
            == "PENDING_40G02_FREEZE"
            for r in out
        ),

    "management_priority_still_pending_40H":
        all(
            r["MANAGEMENT_PRIORITY_CLASS"]
            == "PENDING_40H"
            for r in out
        ),
}

status = (
    "PASS_CALIBRATION_DIAGNOSTIC_COMPLETE"
    if all(checks.values())
    else "REVIEW"
)


# ------------------------------------------------------------
# 8. SAVE QC
# ------------------------------------------------------------

qc = {
    "gate":
        "40G01_PRODUCTIVITY_REFERENCE_CALIBRATION_THRESHOLD_SENSITIVITY_CONFIDENCE_DESIGN",

    "status":
        status,

    "reference_distribution": {
        "source":
            "654 direct PALMSIM ASUs only",

        "min_t_ha_yr":
            min(direct_reference),

        "q20_t_ha_yr":
            Q20,

        "q25_t_ha_yr":
            Q25,

        "q30_t_ha_yr":
            Q30,

        "median_t_ha_yr":
            statistics.median(
                direct_reference
            ),

        "q70_t_ha_yr":
            Q70,

        "q75_t_ha_yr":
            Q75,

        "q80_t_ha_yr":
            Q80,

        "max_t_ha_yr":
            max(direct_reference),
    },

    "baseline_candidate": {
        "schema":
            "Q25_Q75_RELATIVE_PILOT",

        "low":
            "center <= direct PALMSIM Q25",

        "typical":
            "direct Q25 < center < direct Q75",

        "high":
            "center >= direct PALMSIM Q75",

        "note":
            (
                "Relative analytical bands, not agronomic "
                "yield standards."
            ),
    },

    "threshold_sensitivity":
        sens_rows,

    "structural_model_disagreement": {
        "method":
            (
                "Direct: max(age-group MAE, climate-pair MAE); "
                "fallback: climate-pair MAE only because age is unresolved."
            ),

        "q33_t_ha_yr":
            STRUCT_Q33,

        "q67_t_ha_yr":
            STRUCT_Q67,

        "note":
            (
                "Representative PALMSIM-vs-APSIM disagreement "
                "diagnostic, not empirical prediction error."
            ),
    },

    "confidence_design": {
        "allowed_levels":
            [
                "MODERATE",
                "LOW",
                "VERY_LOW",
            ],

        "high_confidence":
            "NOT_ALLOWED_WITHOUT_LOCAL_FFB_VALIDATION",

        "direct_data_support_rule":
            {
                "STRONG":
                    "AGE_VALID_FRACTION>=0.50 and CONDITION_VALID_FRACTION>=0.80",

                "MODERATE":
                    "AGE_VALID_FRACTION>=0.25 and CONDITION_VALID_FRACTION>=0.50",

                "LIMITED":
                    "otherwise",
            },

        "direct_confidence_rule":
            {
                "MODERATE":
                    (
                        "STRONG data support + structural "
                        "disagreement not RELATIVE_HIGH"
                    ),

                "VERY_LOW":
                    (
                        "LIMITED data support + RELATIVE_HIGH "
                        "structural disagreement"
                    ),

                "LOW":
                    "all other direct cases",
            },

        "fallback_rule":
            (
                "Preserve frozen LOW/VERY_LOW fallback confidence; "
                "never upgrade."
            ),
    },

    "diagnostic_counts": {
        "productivity_band":
            baseline_counts,

        "confidence":
            confidence_counts,

        "data_support":
            support_counts,

        "structural_disagreement":
            struct_counts,

        "fallback_interval_band_stability":
            fallback_stability_counts,
    },

    "checks":
        checks,

    "next":
        (
            "40G02 inspect sensitivity and freeze/adjust productivity "
            "thresholds + confidence rules."
        ),
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
print("40G01 FINISHED")
print("====================================================")
print("Status                         :", status)

print("\nBASELINE PRODUCTIVITY BAND CANDIDATE")
print("Reference                      : Direct PALMSIM 654")
print("LOW <= Q25                     :", Q25)
print("HIGH >= Q75                    :", Q75)
print("Band counts 820                :", baseline_counts)

print("\nTHRESHOLD SENSITIVITY")
for r in sens_rows:
    print(
        r["SCHEME"],
        "| low/high =",
        round(
            r["LOW_THRESHOLD_T_HA_YR"],
            4
        ),
        "/",
        round(
            r["HIGH_THRESHOLD_T_HA_YR"],
            4
        ),
        "| switches all =",
        r["SWITCH_FROM_BASELINE_ALL_N"],
        "(",
        round(
            r["SWITCH_FROM_BASELINE_ALL_PCT"],
            2
        ),
        "% )"
    )

print("\nCONFIDENCE")
print("MODERATE / LOW / VERY_LOW      :", confidence_counts)

print("\nDATA SUPPORT")
print("STRONG / MODERATE / LIMITED    :", support_counts)

print("\nSTRUCTURAL MODEL DISAGREEMENT")
print("LOW / MODERATE / HIGH          :", struct_counts)

print("\nFALLBACK INTERVAL BAND STABILITY")
print(
    "Stable within one band         :",
    fallback_stability_counts[
        "STABLE_WITHIN_ONE_BAND"
    ]
)
print(
    "Spans multiple bands           :",
    fallback_stability_counts[
        "UNCERTAIN_SPANS_MULTIPLE_BANDS"
    ]
)

print("\nQC:")
for key, value in checks.items():
    print(
        f"{key:52s}: {value}"
    )

print("\nCalibration CSV :", OUT_MASTER)
print("Sensitivity CSV :", OUT_SENS)
print("QC JSON         :", OUT_QC)

if status == "PASS_CALIBRATION_DIAGNOSTIC_COMPLETE":
    print(
        "Next            : 40G02 inspect diagnostics and "
        "freeze/adjust thresholds + confidence."
    )
else:
    print(
        "Next            : Review failed QC before 40G02."
    )

print("====================================================")
