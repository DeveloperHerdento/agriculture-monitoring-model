# ============================================================
# OUTPUT 4 / 40H01
# MANAGEMENT PRIORITY INTEGRATION
# + RULE SENSITIVITY DIAGNOSTIC
# SIAK_AOI01
#
# PURE PYTHON STANDARD LIBRARY ONLY
# NO numpy / pandas / scipy
# NO PALMSIM/APSIM rerun
#
# PURPOSE
# -------
# Build a candidate wall-to-wall Management Priority Class 0-4
# for all 820 palm ASUs using:
#   - frozen productivity evidence (40G02)
#   - condition score + coverage
#   - age proxy + age coverage where available
#   - productivity confidence / structural disagreement as uncertainty
#
# IMPORTANT
# ---------
# This stage is a RULE-BASED CANDIDATE + SENSITIVITY diagnostic.
# It DOES NOT freeze the final classes yet.
#
# Class semantics:
#   0 Insufficient Data / Limited Evidence
#   1 Maintain
#   2 Monitor
#   3 Management Intervention Priority
#   4 Replanting Evaluation Priority
#
# Guardrails:
# - Class 4 only for DIRECT pathway with numeric age evidence.
# - Fallback productivity NEVER triggers Class 3/4 by itself.
# - Fallback ASUs may reach Class 3 only from strong condition risk.
# - Fallback ASUs cannot reach Class 4 in this version because
#   numeric age is unresolved.
# - Young palms (age <=3) are protected against escalation from
#   low productivity alone because immature yield can be expected.
# - Soil/climate are not direct priority triggers here; they remain
#   contextual because they are coarse/supporting evidence.
#
# Sensitivity candidates:
#   SENSITIVE     : condition Q40/Q70/Q85, replant age >=18
#   BASELINE      : condition Q50/Q75/Q90, replant age >=19
#   CONSERVATIVE  : condition Q60/Q80/Q95, replant age >=20
#
# Next:
# 40H02 = inspect class distributions/switches and freeze/adjust rules.
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
    "40G02_FROZEN_PRODUCTIVITY_CALIBRATION_820_SIAK_AOI01_V1.csv"
)

OUT_MASTER = WORKDIR / (
    "40H01_MANAGEMENT_PRIORITY_CANDIDATE_820_SIAK_AOI01_V1.csv"
)

OUT_SENS = WORKDIR / (
    "40H01_MANAGEMENT_PRIORITY_RULE_SENSITIVITY_SIAK_AOI01_V1.csv"
)

OUT_QC = WORKDIR / (
    "40H01_MANAGEMENT_PRIORITY_INTEGRATION_QC_SIAK_AOI01_V1.json"
)

print("====================================================")
print("40H01 — MANAGEMENT PRIORITY INTEGRATION + SENSITIVITY")
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

if not INPUT.exists():
    raise FileNotFoundError(INPUT)

rows = read_csv_dict(INPUT)

if len(rows) != 820:
    raise ValueError(
        f"Expected 820 rows; got {len(rows)}."
    )

if len({r["UNIT_ID"] for r in rows}) != 820:
    raise ValueError(
        "Input UNIT_ID is not unique."
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
# 2. CONDITION REFERENCE
# ------------------------------------------------------------
# Higher CONDITION_SCORE = higher condition risk because this score
# originates from the Output-3 core risk evidence framework.
# Thresholds are RELATIVE pilot thresholds, not agronomic standards.
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

if len(condition_values) != 818:
    print(
        "WARNING: expected ~818 valid condition scores; got",
        len(condition_values)
    )

condition_quantiles = {
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

print("\nCONDITION SCORE REFERENCE")
for key in [
    "Q40", "Q50", "Q60",
    "Q70", "Q75", "Q80",
    "Q85", "Q90", "Q95"
]:
    print(
        f"{key:30s}:",
        condition_quantiles[key]
    )


# ------------------------------------------------------------
# 3. RULE SETTINGS
# ------------------------------------------------------------

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

    watch_thr = condition_quantiles[
        cfg["WATCH_Q"]
    ]

    elevated_thr = condition_quantiles[
        cfg["ELEVATED_Q"]
    ]

    high_thr = condition_quantiles[
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

    # --------------------------------------------------------
    # CONDITION STATE
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # CLASS 0 — insufficient evidence
    # --------------------------------------------------------
    #
    # Reserve Class 0 primarily for fallback cases where numeric
    # age is unresolved AND condition evidence is also insufficient.
    # Direct PALMSIM ASUs retain productivity evidence even if another
    # contextual component is weaker.
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # CLASS 4 — Replanting Evaluation Priority
    # --------------------------------------------------------
    #
    # Requires all:
    # - direct pathway
    # - old age proxy
    # - at least moderate age evidence
    # - low relative productivity
    # - elevated/high condition risk
    # - usable condition coverage
    #
    # Never available to fallback pathway in current version.
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # CLASS 3 — Management Intervention Priority
    # --------------------------------------------------------

    # Strong condition risk can independently trigger intervention
    # when condition coverage is usable.
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

    # Direct pathway: low productivity + elevated condition can also
    # trigger management review, except age<=3 where low productivity
    # can be expected from immature palms.
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

    # --------------------------------------------------------
    # CLASS 2 — Monitor
    # --------------------------------------------------------

    # Every fallback ASU with usable condition evidence is at least
    # Monitor because productivity is highly uncertain.
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

    # Direct pathway uncertainty / mild warning.
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

    # --------------------------------------------------------
    # CLASS 1 — Maintain
    # --------------------------------------------------------

    reasons.append(
        "NO_PRIORITY_TRIGGER"
    )

    return (
        1,
        reasons,
        condition_state
    )


# ------------------------------------------------------------
# 5. RUN ALL THREE RULE SETTINGS
# ------------------------------------------------------------

assignments = {}

for rule_name in RULES:

    rule_assign = {}

    for r in rows:

        cls, reasons, cond_state = classify(
            r,
            rule_name
        )

        rule_assign[
            r["UNIT_ID"]
        ] = {
            "CLASS": cls,
            "REASONS": reasons,
            "CONDITION_STATE": cond_state,
        }

    assignments[
        rule_name
    ] = rule_assign


# ------------------------------------------------------------
# 6. SENSITIVITY SUMMARY
# ------------------------------------------------------------

baseline = assignments["BASELINE"]

sens_rows = []

for rule_name in [
    "SENSITIVE",
    "BASELINE",
    "CONSERVATIVE",
]:

    current = assignments[
        rule_name
    ]

    counts = {
        0: 0,
        1: 0,
        2: 0,
        3: 0,
        4: 0,
    }

    direct_counts = counts.copy()
    fallback_counts = counts.copy()

    switched_all = 0
    switched_direct = 0
    switched_fallback = 0

    for r in rows:

        uid = r["UNIT_ID"]

        cls = current[uid]["CLASS"]

        counts[cls] += 1

        if (
            r["PRODUCTIVITY_PATHWAY"]
            == "DIRECT_MODEL_SUPPORTED"
        ):
            direct_counts[cls] += 1
        else:
            fallback_counts[cls] += 1

        if cls != baseline[uid]["CLASS"]:

            switched_all += 1

            if (
                r["PRODUCTIVITY_PATHWAY"]
                == "DIRECT_MODEL_SUPPORTED"
            ):
                switched_direct += 1
            else:
                switched_fallback += 1

    cfg = RULES[
        rule_name
    ]

    sens_rows.append({
        "RULE_SET":
            rule_name,

        "WATCH_THRESHOLD_SOURCE":
            cfg["WATCH_Q"],

        "WATCH_THRESHOLD_VALUE":
            condition_quantiles[
                cfg["WATCH_Q"]
            ],

        "ELEVATED_THRESHOLD_SOURCE":
            cfg["ELEVATED_Q"],

        "ELEVATED_THRESHOLD_VALUE":
            condition_quantiles[
                cfg["ELEVATED_Q"]
            ],

        "HIGH_THRESHOLD_SOURCE":
            cfg["HIGH_Q"],

        "HIGH_THRESHOLD_VALUE":
            condition_quantiles[
                cfg["HIGH_Q"]
            ],

        "REPLANT_AGE_MIN":
            cfg["REPLANT_AGE_MIN"],

        "CLASS0_N":
            counts[0],

        "CLASS1_N":
            counts[1],

        "CLASS2_N":
            counts[2],

        "CLASS3_N":
            counts[3],

        "CLASS4_N":
            counts[4],

        "DIRECT_CLASS0_N":
            direct_counts[0],

        "DIRECT_CLASS1_N":
            direct_counts[1],

        "DIRECT_CLASS2_N":
            direct_counts[2],

        "DIRECT_CLASS3_N":
            direct_counts[3],

        "DIRECT_CLASS4_N":
            direct_counts[4],

        "FALLBACK_CLASS0_N":
            fallback_counts[0],

        "FALLBACK_CLASS1_N":
            fallback_counts[1],

        "FALLBACK_CLASS2_N":
            fallback_counts[2],

        "FALLBACK_CLASS3_N":
            fallback_counts[3],

        "FALLBACK_CLASS4_N":
            fallback_counts[4],

        "SWITCH_FROM_BASELINE_ALL_N":
            switched_all,

        "SWITCH_FROM_BASELINE_ALL_PCT":
            (
                100.0
                * switched_all
                / 820.0
            ),

        "SWITCH_FROM_BASELINE_DIRECT_N":
            switched_direct,

        "SWITCH_FROM_BASELINE_DIRECT_PCT":
            (
                100.0
                * switched_direct
                / 654.0
            ),

        "SWITCH_FROM_BASELINE_FALLBACK_N":
            switched_fallback,

        "SWITCH_FROM_BASELINE_FALLBACK_PCT":
            (
                100.0
                * switched_fallback
                / 166.0
            ),
    })

write_csv_dict(
    OUT_SENS,
    sens_rows
)


# ------------------------------------------------------------
# 7. BUILD BASELINE CANDIDATE MASTER TABLE
# ------------------------------------------------------------

out = []

for r in rows:

    uid = r["UNIT_ID"]

    result = baseline[
        uid
    ]

    cls = result[
        "CLASS"
    ]

    reasons = result[
        "REASONS"
    ]

    cond_state = result[
        "CONDITION_STATE"
    ]

    out.append({
        **r,

        "CONDITION_PRIORITY_STATE_40H01":
            cond_state,

        "MANAGEMENT_PRIORITY_CLASS_CANDIDATE":
            cls,

        "MANAGEMENT_PRIORITY_LABEL_CANDIDATE":
            CLASS_LABEL[cls],

        "MANAGEMENT_PRIORITY_REASON_CODES":
            ";".join(reasons),

        "MANAGEMENT_RULE_SET":
            "BASELINE_Q50_Q75_Q90_AGE19",

        "MANAGEMENT_PRIORITY_CLASS":
            "PENDING_40H02_FREEZE",

        "CLASS4_AUTOMATIC_REPLANT_ORDER":
            "NO",

        "OUTPUT4_WALL_TO_WALL_INCLUDED":
            "YES",

        "MANAGEMENT_INTEGRATION_VERSION":
            "40H01_V1",
    })

write_csv_dict(
    OUT_MASTER,
    out
)


# ------------------------------------------------------------
# 8. BASELINE DIAGNOSTIC COUNTS
# ------------------------------------------------------------

baseline_counts = {
    0: 0,
    1: 0,
    2: 0,
    3: 0,
    4: 0,
}

direct_counts = baseline_counts.copy()
fallback_counts = baseline_counts.copy()

for r in out:

    cls = int(
        r[
            "MANAGEMENT_PRIORITY_CLASS_CANDIDATE"
        ]
    )

    baseline_counts[cls] += 1

    if (
        r["PRODUCTIVITY_PATHWAY"]
        == "DIRECT_MODEL_SUPPORTED"
    ):
        direct_counts[cls] += 1
    else:
        fallback_counts[cls] += 1


# ------------------------------------------------------------
# 9. QC
# ------------------------------------------------------------

fallback_out = [
    r for r in out
    if r["PRODUCTIVITY_PATHWAY"]
    == "AGE_CENSORED_OR_UNRESOLVED_FALLBACK"
]

class4_rows = [
    r for r in out
    if int(
        r["MANAGEMENT_PRIORITY_CLASS_CANDIDATE"]
    ) == 4
]

checks = {

    "rows_820":
        len(out) == 820,

    "unique_asu_820":
        len({
            r["UNIT_ID"]
            for r in out
        }) == 820,

    "all_820_included":
        all(
            r["OUTPUT4_WALL_TO_WALL_INCLUDED"]
            == "YES"
            for r in out
        ),

    "all_candidate_classes_0_4":
        all(
            int(
                r[
                    "MANAGEMENT_PRIORITY_CLASS_CANDIDATE"
                ]
            )
            in {0, 1, 2, 3, 4}
            for r in out
        ),

    "fallback_class4_zero":
        all(
            int(
                r[
                    "MANAGEMENT_PRIORITY_CLASS_CANDIDATE"
                ]
            ) != 4
            for r in fallback_out
        ),

    "class4_direct_only":
        all(
            r["PRODUCTIVITY_PATHWAY"]
            == "DIRECT_MODEL_SUPPORTED"
            for r in class4_rows
        ),

    "class4_age_at_least_19_baseline":
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

    "class4_low_productivity_only":
        all(
            r["PRODUCTIVITY_BAND_FINAL"]
            == "RELATIVE_LOW"
            for r in class4_rows
        ),

    "class4_not_automatic_replant":
        all(
            r[
                "CLASS4_AUTOMATIC_REPLANT_ORDER"
            ] == "NO"
            for r in class4_rows
        ),

    "three_rule_sets":
        len(sens_rows) == 3,

    "final_class_not_frozen_yet":
        all(
            r["MANAGEMENT_PRIORITY_CLASS"]
            == "PENDING_40H02_FREEZE"
            for r in out
        ),
}

status = (
    "PASS_MANAGEMENT_CANDIDATE_DIAGNOSTIC_COMPLETE"
    if all(checks.values())
    else "REVIEW"
)


# ------------------------------------------------------------
# 10. SAVE QC JSON
# ------------------------------------------------------------

qc = {
    "gate":
        "40H01_MANAGEMENT_PRIORITY_INTEGRATION_AND_RULE_SENSITIVITY",

    "status":
        status,

    "class_schema": {
        "0":
            "Insufficient Data / Limited Evidence",

        "1":
            "Maintain",

        "2":
            "Monitor",

        "3":
            "Management Intervention Priority",

        "4":
            "Replanting Evaluation Priority",
    },

    "baseline_rule": {
        "condition_watch":
            "Q50 of valid condition score",

        "condition_elevated":
            "Q75 of valid condition score",

        "condition_high":
            "Q90 of valid condition score",

        "replant_age_min":
            19,

        "class0":
            (
                "Fallback age unresolved + condition evidence "
                "insufficient."
            ),

        "class4":
            (
                "Direct only; age>=19; age coverage>=0.25; "
                "relative-low productivity; elevated/high condition; "
                "condition coverage>=0.50."
            ),

        "class3":
            (
                "High condition risk with adequate condition coverage, "
                "OR direct relative-low productivity + elevated "
                "condition risk outside immature age."
            ),

        "class2":
            (
                "Fallback with usable condition evidence; or direct "
                "low productivity / watch-elevated condition / "
                "very-low confidence / high structural disagreement / "
                "limited support."
            ),

        "class1":
            "No priority trigger.",
    },

    "guardrails": [
        "Fallback productivity may not trigger Class 3 or Class 4 by itself.",
        "Fallback ASUs cannot receive Class 4 while numeric age remains unresolved.",
        "Low productivity in age<=3 is protected by an immature-age guardrail.",
        "Class 4 means Replanting Evaluation Priority, not Replanting Required.",
        "Soil and climate remain contextual rather than direct management-priority triggers in 40H01.",
        "Thresholds and rules remain pilot settings pending 40H02 freeze."
    ],

    "condition_quantiles":
        condition_quantiles,

    "baseline_class_counts_820": {
        str(k): v
        for k, v in baseline_counts.items()
    },

    "baseline_direct_class_counts_654": {
        str(k): v
        for k, v in direct_counts.items()
    },

    "baseline_fallback_class_counts_166": {
        str(k): v
        for k, v in fallback_counts.items()
    },

    "rule_sensitivity":
        sens_rows,

    "checks":
        checks,

    "next":
        (
            "40H02 inspect rule sensitivity + class distribution "
            "and freeze/adjust final Management Priority Class 0-4."
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
# 11. PRINT
# ------------------------------------------------------------

print("\n====================================================")
print("40H01 FINISHED")
print("====================================================")
print("Status                         :", status)

print("\nBASELINE CONDITION THRESHOLDS")
print(
    "WATCH >= Q50                  :",
    condition_quantiles["Q50"]
)
print(
    "ELEVATED >= Q75               :",
    condition_quantiles["Q75"]
)
print(
    "HIGH >= Q90                   :",
    condition_quantiles["Q90"]
)
print(
    "Class 4 age minimum           : 19 years proxy"
)

print("\nBASELINE CLASS COUNTS — ALL 820")
for k in range(5):
    print(
        f"Class {k} {CLASS_LABEL[k]:38s}:",
        baseline_counts[k]
    )

print("\nDIRECT 654")
print(direct_counts)

print("\nFALLBACK 166")
print(fallback_counts)

print("\nRULE SENSITIVITY")
for r in sens_rows:
    print(
        r["RULE_SET"],
        "| classes 0-4 =",
        [
            r["CLASS0_N"],
            r["CLASS1_N"],
            r["CLASS2_N"],
            r["CLASS3_N"],
            r["CLASS4_N"],
        ],
        "| switches vs baseline =",
        round(
            r["SWITCH_FROM_BASELINE_ALL_PCT"],
            2
        ),
        "%"
    )

print("\nQC:")
for key, value in checks.items():
    print(
        f"{key:52s}: {value}"
    )

print("\nCandidate master CSV :", OUT_MASTER)
print("Sensitivity CSV      :", OUT_SENS)
print("QC JSON              :", OUT_QC)

if status == "PASS_MANAGEMENT_CANDIDATE_DIAGNOSTIC_COMPLETE":
    print(
        "Next                 : 40H02 inspect sensitivity "
        "and freeze/adjust final Class 0-4."
    )
else:
    print(
        "Next                 : Review failed QC before 40H02."
    )

print("====================================================")
