# ============================================================
# OUTPUT 4 / 40H02
# FINAL MANAGEMENT PRIORITY FREEZE
# + PER-ASU RULE STABILITY + CONFIDENCE
# SIAK_AOI01
#
# PURE PYTHON STANDARD LIBRARY ONLY
# NO numpy / pandas / scipy
# NO PALMSIM/APSIM rerun
#
# PURPOSE
# -------
# Freeze the 40H01 BASELINE candidate as final Management Priority
# Class 0-4, while explicitly quantifying per-ASU sensitivity across
# SENSITIVE / BASELINE / CONSERVATIVE rule sets.
#
# FINAL CLASS SCHEMA
# ------------------
# 0 = Insufficient Data / Limited Evidence
# 1 = Maintain
# 2 = Monitor
# 3 = Management Intervention Priority
# 4 = Replanting Evaluation Priority
#
# IMPORTANT
# ---------
# - Baseline final class is frozen because total switch rates under
#   alternative rule sets are < 10%.
# - Rule stability is carried per ASU, not hidden.
# - No HIGH confidence is allowed.
# - Class 4 is explicitly capped at LOW confidence because it is
#   threshold-sensitive and is only an evaluation priority.
# - Fallback ASUs remain unable to receive Class 4.
# - Fallback Class 3 is condition-driven, never productivity-driven.
#
# Next:
# 40I = Final Freeze & Spatial QA
# ============================================================

from pathlib import Path
import csv
import json
import math
import statistics

WORKDIR = Path(
    r"C:\Users\user\Documents\KERJA\SPATIAL DATA ANALYST INTERN\04_YIELD"
)

INPUT = WORKDIR / (
    "40H01_MANAGEMENT_PRIORITY_CANDIDATE_820_SIAK_AOI01_V1.csv"
)

SENS = WORKDIR / (
    "40H01_MANAGEMENT_PRIORITY_RULE_SENSITIVITY_SIAK_AOI01_V1.csv"
)

OUT_MASTER = WORKDIR / (
    "40H02_FINAL_MANAGEMENT_PRIORITY_820_SIAK_AOI01_V1.csv"
)

OUT_SUMMARY = WORKDIR / (
    "40H02_FINAL_MANAGEMENT_PRIORITY_SUMMARY_SIAK_AOI01_V1.csv"
)

OUT_QC = WORKDIR / (
    "40H02_FINAL_MANAGEMENT_PRIORITY_FREEZE_QC_SIAK_AOI01_V1.json"
)

print("====================================================")
print("40H02 — FINAL MANAGEMENT PRIORITY FREEZE")
print("+ PER-ASU RULE STABILITY + CONFIDENCE")
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


CLASS_LABEL = {
    0: "Insufficient Data / Limited Evidence",
    1: "Maintain",
    2: "Monitor",
    3: "Management Intervention Priority",
    4: "Replanting Evaluation Priority",
}


# ------------------------------------------------------------
# 1. PREFLIGHT
# ------------------------------------------------------------

for p in [INPUT, SENS]:
    if not p.exists():
        raise FileNotFoundError(p)

rows = read_csv_dict(INPUT)
sens_rows = read_csv_dict(SENS)

if len(rows) != 820:
    raise ValueError(
        f"Expected 820 rows; got {len(rows)}."
    )

if len({
    r["UNIT_ID"] for r in rows
}) != 820:
    raise ValueError(
        "Input UNIT_ID is not unique."
    )

if len(sens_rows) != 3:
    raise ValueError(
        f"Expected 3 sensitivity rows; got {len(sens_rows)}."
    )

direct = [
    r for r in rows
    if r["PRODUCTIVITY_PATHWAY"]
    == "DIRECT_MODEL_SUPPORTED"
]

fallback = [
    r for r in rows
    if r["PRODUCTIVITY_PATHWAY"]
    == "AGE_CENSORED_OR_UNRESOLVED_FALLBACK"
]

if len(direct) != 654:
    raise ValueError(
        f"Expected 654 direct rows; got {len(direct)}."
    )

if len(fallback) != 166:
    raise ValueError(
        f"Expected 166 fallback rows; got {len(fallback)}."
    )

print("Master ASUs                    :", len(rows))
print("Direct pathway                 :", len(direct))
print("Fallback pathway               :", len(fallback))


# ------------------------------------------------------------
# 2. CHECK AGGREGATE SENSITIVITY
# ------------------------------------------------------------

sens_by_name = {
    r["RULE_SET"]: r
    for r in sens_rows
}

required = {
    "SENSITIVE",
    "BASELINE",
    "CONSERVATIVE",
}

if set(sens_by_name) != required:
    raise ValueError(
        "Unexpected sensitivity rule sets."
    )

sensitive_switch = float(
    sens_by_name["SENSITIVE"][
        "SWITCH_FROM_BASELINE_ALL_PCT"
    ]
)

conservative_switch = float(
    sens_by_name["CONSERVATIVE"][
        "SWITCH_FROM_BASELINE_ALL_PCT"
    ]
)

max_switch = max(
    sensitive_switch,
    conservative_switch
)

if max_switch >= 10.0:
    raise ValueError(
        "Alternative rule-set switch rate >=10%; "
        "do not freeze automatically."
    )

print("Max alternative switch rate    :", max_switch, "%")
print("Freeze decision                 : BASELINE ACCEPTED")


# ------------------------------------------------------------
# 3. RECONSTRUCT CONDITION QUANTILES
# ------------------------------------------------------------

condition_values = []

for r in rows:

    cond = to_float_or_none(
        r.get("CONDITION_SCORE")
    )

    cond_valid = to_float_or_none(
        r.get("CONDITION_VALID_FRACTION")
    )

    if (
        cond is not None
        and cond_valid is not None
        and cond_valid > 0
    ):
        condition_values.append(cond)

Q = {
    "Q40": quantile(condition_values, 0.40),
    "Q50": quantile(condition_values, 0.50),
    "Q60": quantile(condition_values, 0.60),
    "Q70": quantile(condition_values, 0.70),
    "Q75": quantile(condition_values, 0.75),
    "Q80": quantile(condition_values, 0.80),
    "Q85": quantile(condition_values, 0.85),
    "Q90": quantile(condition_values, 0.90),
    "Q95": quantile(condition_values, 0.95),
}

RULES = {
    "SENSITIVE": {
        "WATCH_Q": "Q40",
        "ELEVATED_Q": "Q70",
        "HIGH_Q": "Q85",
        "REPLANT_AGE_MIN": 18.0,
    },

    "BASELINE": {
        "WATCH_Q": "Q50",
        "ELEVATED_Q": "Q75",
        "HIGH_Q": "Q90",
        "REPLANT_AGE_MIN": 19.0,
    },

    "CONSERVATIVE": {
        "WATCH_Q": "Q60",
        "ELEVATED_Q": "Q80",
        "HIGH_Q": "Q95",
        "REPLANT_AGE_MIN": 20.0,
    },
}


# ------------------------------------------------------------
# 4. CLASSIFICATION FUNCTION
# ------------------------------------------------------------

def classify(row, rule_name):

    cfg = RULES[rule_name]

    watch_thr = Q[
        cfg["WATCH_Q"]
    ]

    elevated_thr = Q[
        cfg["ELEVATED_Q"]
    ]

    high_thr = Q[
        cfg["HIGH_Q"]
    ]

    pathway = row[
        "PRODUCTIVITY_PATHWAY"
    ]

    prod_band = row[
        "PRODUCTIVITY_BAND_FINAL"
    ]

    prod_conf = row[
        "PRODUCTIVITY_BAND_CONFIDENCE_FINAL"
    ]

    structural_tier = row[
        "STRUCTURAL_MODEL_DISAGREEMENT_TIER"
    ]

    data_support = row[
        "DATA_SUPPORT_TIER"
    ]

    condition = to_float_or_none(
        row.get("CONDITION_SCORE")
    )

    condition_valid = to_float_or_none(
        row.get("CONDITION_VALID_FRACTION")
    )

    age = to_float_or_none(
        row.get("AGE_P50")
    )

    age_valid = to_float_or_none(
        row.get("AGE_VALID_FRACTION")
    )

    reasons = []

    # CONDITION STATE
    if (
        condition is None
        or condition_valid is None
        or condition_valid < 0.25
    ):
        condition_state = "INSUFFICIENT"

    elif condition >= high_thr:
        condition_state = "HIGH"

    elif condition >= elevated_thr:
        condition_state = "ELEVATED"

    elif condition >= watch_thr:
        condition_state = "WATCH"

    else:
        condition_state = "LOW"

    reasons.append(
        "COND_" + condition_state
    )

    # CLASS 0
    if (
        pathway
        == "AGE_CENSORED_OR_UNRESOLVED_FALLBACK"
        and condition_state == "INSUFFICIENT"
    ):
        reasons.extend([
            "AGE_UNRESOLVED",
            "FALLBACK_PRODUCTIVITY_VERY_LOW_CONFIDENCE",
        ])

        return (
            0,
            reasons,
            condition_state
        )

    # CLASS 4
    if (
        pathway == "DIRECT_MODEL_SUPPORTED"
        and age is not None
        and age >= cfg["REPLANT_AGE_MIN"]
        and age_valid is not None
        and age_valid >= 0.25
        and prod_band == "RELATIVE_LOW"
        and condition_state in {
            "ELEVATED",
            "HIGH",
        }
        and condition_valid is not None
        and condition_valid >= 0.50
    ):
        reasons.extend([
            "OLD_AGE_PROXY",
            "LOW_RELATIVE_PRODUCTIVITY",
            "CONDITION_DECLINE_SUPPORT",
            "REPLANT_EVALUATION_NOT_AUTOMATIC_ORDER",
        ])

        return (
            4,
            reasons,
            condition_state
        )

    # CLASS 3
    if (
        condition_state == "HIGH"
        and condition_valid is not None
        and condition_valid >= 0.50
    ):
        reasons.append(
            "HIGH_CONDITION_RISK"
        )

        if (
            pathway
            == "AGE_CENSORED_OR_UNRESOLVED_FALLBACK"
        ):
            reasons.append(
                "FALLBACK_PRODUCTIVITY_NOT_USED_AS_TRIGGER"
            )

        return (
            3,
            reasons,
            condition_state
        )

    if (
        pathway == "DIRECT_MODEL_SUPPORTED"
        and prod_band == "RELATIVE_LOW"
        and condition_state == "ELEVATED"
        and condition_valid is not None
        and condition_valid >= 0.50
        and (
            age is None
            or age > 3.0
        )
    ):
        reasons.extend([
            "LOW_RELATIVE_PRODUCTIVITY",
            "ELEVATED_CONDITION_RISK",
        ])

        return (
            3,
            reasons,
            condition_state
        )

    # CLASS 2
    if (
        pathway
        == "AGE_CENSORED_OR_UNRESOLVED_FALLBACK"
    ):
        reasons.extend([
            "AGE_UNRESOLVED",
            "FALLBACK_PRODUCTIVITY_VERY_LOW_CONFIDENCE",
        ])

        return (
            2,
            reasons,
            condition_state
        )

    if prod_band == "RELATIVE_LOW":
        reasons.append(
            "LOW_RELATIVE_PRODUCTIVITY"
        )

        if (
            age is not None
            and age <= 3.0
        ):
            reasons.append(
                "IMMATURE_AGE_GUARDRAIL"
            )

        return (
            2,
            reasons,
            condition_state
        )

    if condition_state in {
        "WATCH",
        "ELEVATED",
    }:
        reasons.append(
            "CONDITION_MONITORING_SIGNAL"
        )

        return (
            2,
            reasons,
            condition_state
        )

    if prod_conf == "VERY_LOW":
        reasons.append(
            "VERY_LOW_PRODUCTIVITY_CONFIDENCE"
        )

        return (
            2,
            reasons,
            condition_state
        )

    if structural_tier == "RELATIVE_HIGH":
        reasons.append(
            "HIGH_STRUCTURAL_MODEL_DISAGREEMENT"
        )

        return (
            2,
            reasons,
            condition_state
        )

    if data_support == "LIMITED":
        reasons.append(
            "LIMITED_DATA_SUPPORT"
        )

        return (
            2,
            reasons,
            condition_state
        )

    # CLASS 1
    reasons.append(
        "NO_PRIORITY_TRIGGER"
    )

    return (
        1,
        reasons,
        condition_state
    )


# ------------------------------------------------------------
# 5. PER-ASU RULE STABILITY
# ------------------------------------------------------------

out = []

for r in rows:

    uid = r["UNIT_ID"]

    results = {}

    for rule_name in [
        "SENSITIVE",
        "BASELINE",
        "CONSERVATIVE",
    ]:

        cls, reasons, cond_state = classify(
            r,
            rule_name
        )

        results[rule_name] = {
            "CLASS": cls,
            "REASONS": reasons,
            "CONDITION_STATE": cond_state,
        }

    final_cls = results[
        "BASELINE"
    ]["CLASS"]

    # Ensure exact match to saved 40H01 baseline candidate.
    saved_candidate = int(
        r[
            "MANAGEMENT_PRIORITY_CLASS_CANDIDATE"
        ]
    )

    if final_cls != saved_candidate:
        raise ValueError(
            f"Recomputed baseline differs from 40H01 "
            f"for {uid}: {final_cls} vs {saved_candidate}"
        )

    class_vector = [
        results["SENSITIVE"]["CLASS"],
        results["BASELINE"]["CLASS"],
        results["CONSERVATIVE"]["CLASS"],
    ]

    same_as_final_n = sum(
        1
        for cls in class_vector
        if cls == final_cls
    )

    if same_as_final_n == 3:
        stability = "STABLE_3_OF_3"

    elif same_as_final_n == 2:
        stability = "MODERATE_2_OF_3"

    else:
        stability = "UNSTABLE_1_OF_3"

    class_min = min(
        class_vector
    )

    class_max = max(
        class_vector
    )

    pathway = r[
        "PRODUCTIVITY_PATHWAY"
    ]

    prod_conf = r[
        "PRODUCTIVITY_BAND_CONFIDENCE_FINAL"
    ]

    condition_valid = to_float_or_none(
        r.get("CONDITION_VALID_FRACTION")
    )

    # --------------------------------------------------------
    # FINAL MANAGEMENT CONFIDENCE
    # --------------------------------------------------------
    #
    # No HIGH confidence is allowed.
    #
    # Class 4 capped LOW because:
    # - age is proxy, not confirmed planting year
    # - productivity is modelled potential, not actual yield
    # - rule sensitivity is material for Class 4
    # --------------------------------------------------------

    if final_cls == 0:
        management_conf = "VERY_LOW"

    elif final_cls == 4:
        management_conf = (
            "LOW"
            if same_as_final_n >= 2
            else "VERY_LOW"
        )

    elif (
        pathway
        == "AGE_CENSORED_OR_UNRESOLVED_FALLBACK"
    ):

        if final_cls == 3:
            management_conf = (
                "LOW"
                if (
                    condition_valid is not None
                    and condition_valid >= 0.50
                    and same_as_final_n >= 2
                )
                else "VERY_LOW"
            )
        else:
            management_conf = "VERY_LOW"

    else:
        # DIRECT pathway
        if final_cls == 1:

            if (
                prod_conf == "MODERATE"
                and same_as_final_n == 3
            ):
                management_conf = "MODERATE"
            else:
                management_conf = "LOW"

        elif final_cls == 2:

            if same_as_final_n >= 2:
                management_conf = "LOW"
            else:
                management_conf = "VERY_LOW"

        elif final_cls == 3:

            if (
                condition_valid is not None
                and condition_valid >= 0.80
                and same_as_final_n == 3
                and prod_conf != "VERY_LOW"
            ):
                management_conf = "MODERATE"
            else:
                management_conf = "LOW"

        else:
            management_conf = "LOW"

    # --------------------------------------------------------
    # FINAL WEB / POPUP FIELDS
    # --------------------------------------------------------

    if final_cls == 0:
        action_text = (
            "Evidence is insufficient for a defensible management "
            "recommendation; prioritize data review."
        )

    elif final_cls == 1:
        action_text = (
            "Maintain current management and routine monitoring."
        )

    elif final_cls == 2:
        action_text = (
            "Monitor and review emerging condition/productivity "
            "signals or uncertainty."
        )

    elif final_cls == 3:
        action_text = (
            "Prioritize agronomic/operational inspection and "
            "management review."
        )

    else:
        action_text = (
            "Prioritize agronomist-led replanting evaluation; "
            "this is not an automatic replanting order."
        )

    out.append({
        **r,

        "CLASS_SENSITIVE":
            results["SENSITIVE"]["CLASS"],

        "CLASS_BASELINE":
            results["BASELINE"]["CLASS"],

        "CLASS_CONSERVATIVE":
            results["CONSERVATIVE"]["CLASS"],

        "RULE_SUPPORT_SAME_AS_FINAL_N":
            same_as_final_n,

        "RULE_STABILITY":
            stability,

        "RULE_CLASS_MIN":
            class_min,

        "RULE_CLASS_MAX":
            class_max,

        "MANAGEMENT_PRIORITY_CLASS":
            final_cls,

        "MANAGEMENT_PRIORITY_LABEL":
            CLASS_LABEL[final_cls],

        "MANAGEMENT_PRIORITY_CONFIDENCE":
            management_conf,

        "MANAGEMENT_PRIORITY_REASON_CODES_FINAL":
            ";".join(
                results["BASELINE"]["REASONS"]
            ),

        "MANAGEMENT_ACTION_TEXT":
            action_text,

        "FINAL_RULE_SET":
            "BASELINE_Q50_Q75_Q90_AGE19",

        "CLASS4_AUTOMATIC_REPLANT_ORDER":
            "NO",

        "HIGH_CONFIDENCE_ALLOWED":
            "NO",

        "OUTPUT4_WALL_TO_WALL_INCLUDED":
            "YES",

        "FINAL_MANAGEMENT_FREEZE_VERSION":
            "40H02_V1",
    })

write_csv_dict(
    OUT_MASTER,
    out
)


# ------------------------------------------------------------
# 6. SUMMARY COUNTS
# ------------------------------------------------------------

class_counts = {
    0: 0,
    1: 0,
    2: 0,
    3: 0,
    4: 0,
}

direct_counts = class_counts.copy()
fallback_counts = class_counts.copy()

confidence_counts = {
    "MODERATE": 0,
    "LOW": 0,
    "VERY_LOW": 0,
}

stability_counts = {
    "STABLE_3_OF_3": 0,
    "MODERATE_2_OF_3": 0,
    "UNSTABLE_1_OF_3": 0,
}

class_stability = {
    k: {
        "STABLE_3_OF_3": 0,
        "MODERATE_2_OF_3": 0,
        "UNSTABLE_1_OF_3": 0,
    }
    for k in range(5)
}

for r in out:

    cls = int(
        r["MANAGEMENT_PRIORITY_CLASS"]
    )

    class_counts[cls] += 1

    if (
        r["PRODUCTIVITY_PATHWAY"]
        == "DIRECT_MODEL_SUPPORTED"
    ):
        direct_counts[cls] += 1
    else:
        fallback_counts[cls] += 1

    confidence_counts[
        r["MANAGEMENT_PRIORITY_CONFIDENCE"]
    ] += 1

    stability_counts[
        r["RULE_STABILITY"]
    ] += 1

    class_stability[cls][
        r["RULE_STABILITY"]
    ] += 1


summary_rows = []

for cls in range(5):

    summary_rows.append({
        "CLASS":
            cls,

        "LABEL":
            CLASS_LABEL[cls],

        "ALL_N":
            class_counts[cls],

        "DIRECT_N":
            direct_counts[cls],

        "FALLBACK_N":
            fallback_counts[cls],

        "STABLE_3_OF_3_N":
            class_stability[cls][
                "STABLE_3_OF_3"
            ],

        "MODERATE_2_OF_3_N":
            class_stability[cls][
                "MODERATE_2_OF_3"
            ],

        "UNSTABLE_1_OF_3_N":
            class_stability[cls][
                "UNSTABLE_1_OF_3"
            ],
    })

write_csv_dict(
    OUT_SUMMARY,
    summary_rows
)


# ------------------------------------------------------------
# 7. QC
# ------------------------------------------------------------

class4_rows = [
    r
    for r in out
    if int(
        r["MANAGEMENT_PRIORITY_CLASS"]
    ) == 4
]

fallback_out = [
    r
    for r in out
    if r["PRODUCTIVITY_PATHWAY"]
    == "AGE_CENSORED_OR_UNRESOLVED_FALLBACK"
]

checks = {

    "rows_820":
        len(out) == 820,

    "unique_asu_820":
        len({
            r["UNIT_ID"]
            for r in out
        }) == 820,

    "all_820_wall_to_wall_included":
        all(
            r["OUTPUT4_WALL_TO_WALL_INCLUDED"]
            == "YES"
            for r in out
        ),

    "final_class_counts_match_40H01_baseline":
        class_counts
        == {
            0: 4,
            1: 159,
            2: 551,
            3: 103,
            4: 3,
        },

    "all_final_classes_0_4":
        all(
            int(
                r["MANAGEMENT_PRIORITY_CLASS"]
            )
            in {0, 1, 2, 3, 4}
            for r in out
        ),

    "all_rule_stability_assigned":
        sum(
            stability_counts.values()
        ) == 820,

    "all_management_confidence_assigned":
        sum(
            confidence_counts.values()
        ) == 820,

    "no_high_management_confidence":
        all(
            r["MANAGEMENT_PRIORITY_CONFIDENCE"]
            != "HIGH"
            for r in out
        ),

    "fallback_class4_zero":
        all(
            int(
                r["MANAGEMENT_PRIORITY_CLASS"]
            ) != 4
            for r in fallback_out
        ),

    "class4_direct_only":
        all(
            r["PRODUCTIVITY_PATHWAY"]
            == "DIRECT_MODEL_SUPPORTED"
            for r in class4_rows
        ),

    "class4_age_at_least_19":
        all(
            to_float_or_none(
                r.get("AGE_P50")
            ) is not None
            and
            to_float_or_none(
                r.get("AGE_P50")
            ) >= 19.0
            for r in class4_rows
        ),

    "class4_low_productivity":
        all(
            r["PRODUCTIVITY_BAND_FINAL"]
            == "RELATIVE_LOW"
            for r in class4_rows
        ),

    "class4_confidence_capped_low":
        all(
            r["MANAGEMENT_PRIORITY_CONFIDENCE"]
            in {"LOW", "VERY_LOW"}
            for r in class4_rows
        ),

    "class4_not_automatic_order":
        all(
            r["CLASS4_AUTOMATIC_REPLANT_ORDER"]
            == "NO"
            for r in class4_rows
        ),

    "max_alternative_switch_below_10pct":
        max_switch < 10.0,
}

status = (
    "PASS_MANAGEMENT_PRIORITY_FROZEN"
    if all(checks.values())
    else "REVIEW"
)


# ------------------------------------------------------------
# 8. SAVE QC JSON
# ------------------------------------------------------------

qc = {
    "gate":
        "40H02_FINAL_MANAGEMENT_PRIORITY_FREEZE_WITH_RULE_STABILITY",

    "status":
        status,

    "freeze_decision": {
        "final_rule_set":
            "BASELINE_Q50_Q75_Q90_AGE19",

        "sensitive_switch_pct":
            sensitive_switch,

        "conservative_switch_pct":
            conservative_switch,

        "max_alternative_switch_pct":
            max_switch,

        "decision":
            (
                "Baseline frozen because alternative full-map "
                "switch rates remain below 10%; per-ASU rule "
                "stability is retained explicitly."
            ),
    },

    "final_class_counts_820": {
        str(k): v
        for k, v in class_counts.items()
    },

    "final_direct_class_counts_654": {
        str(k): v
        for k, v in direct_counts.items()
    },

    "final_fallback_class_counts_166": {
        str(k): v
        for k, v in fallback_counts.items()
    },

    "management_confidence_counts":
        confidence_counts,

    "rule_stability_counts":
        stability_counts,

    "class_specific_rule_stability": {
        str(k): v
        for k, v in class_stability.items()
    },

    "scientific_interpretation": [
        "The baseline rule set is frozen as the pilot final Management Priority classification because whole-map class switching under the sensitive and conservative alternatives remains below 10 percent.",
        "Per-ASU rule stability is retained so threshold-sensitive locations can be distinguished from robust assignments.",
        "Class 0 remains a valid analytical class, not geographic NoData.",
        "Class 4 remains Replanting Evaluation Priority only and is not an automatic replanting instruction.",
        "Fallback ASUs cannot receive Class 4 because numeric age remains unresolved.",
        "Fallback Class 3 is driven by strong condition evidence and not by fallback productivity alone.",
        "No HIGH management confidence is allowed because actual local FFB/TBS validation is unavailable.",
        "Class 4 confidence is capped at LOW because age is a proxy, productivity is modelled potential, and Class 4 is sensitive to pilot thresholds."
    ],

    "checks":
        checks,

    "next":
        (
            "40I01 final spatial/domain QA, class coverage, "
            "reason-code completeness, and delivery freeze."
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
print("40H02 FINISHED")
print("====================================================")
print("Status                         :", status)

print("\nFINAL CLASS COUNTS — 820")
for k in range(5):
    print(
        f"Class {k} {CLASS_LABEL[k]:38s}:",
        class_counts[k]
    )

print("\nDIRECT 654")
print(direct_counts)

print("\nFALLBACK 166")
print(fallback_counts)

print("\nRULE STABILITY")
print(stability_counts)

print("\nMANAGEMENT CONFIDENCE")
print(confidence_counts)

print("\nCLASS-SPECIFIC STABILITY")
for k in range(5):
    print(
        f"Class {k}:",
        class_stability[k]
    )

print("\nCLASS 4")
print("Count                          :", len(class4_rows))
print("Direct only                    : YES")
print("Age proxy >=19                 : YES")
print("Automatic replant order        : NO")
print("Confidence cap                 : LOW / VERY_LOW")

print("\nQC:")
for key, value in checks.items():
    print(
        f"{key:58s}: {value}"
    )

print("\nFinal master CSV :", OUT_MASTER)
print("Summary CSV      :", OUT_SUMMARY)
print("Freeze/QC JSON   :", OUT_QC)

if status == "PASS_MANAGEMENT_PRIORITY_FROZEN":
    print(
        "Next              : 40I01 final spatial/domain QA "
        "+ delivery freeze."
    )
else:
    print(
        "Next              : Review failed QC before 40I."
    )

print("====================================================")
