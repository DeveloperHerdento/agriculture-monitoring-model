# ============================================================
# OUTPUT 4 / 40G02
# PRODUCTIVITY THRESHOLD + CONFIDENCE FREEZE
# SIAK_AOI01
#
# PURE PYTHON STANDARD LIBRARY ONLY
# NO numpy / pandas / scipy
# NO PALMSIM/APSIM rerun
#
# PURPOSE
# -------
# Freeze the pilot relative productivity calibration after 40G01.
#
# DECISIONS
# ---------
# 1) Q25/Q75 of the 654 direct PALMSIM ASUs becomes the frozen
#    PILOT relative productivity-band reference.
# 2) Direct PALMSIM ASUs receive frozen relative bands:
#       RELATIVE_LOW / RELATIVE_TYPICAL / RELATIVE_HIGH
# 3) Fallback ASUs keep their center-based band ONLY as an
#    indicative display band because ALL 166 uncertainty intervals
#    span multiple bands.
# 4) Therefore fallback PRODUCTIVITY-BAND confidence is forced to
#    VERY_LOW and its productivity evidence is WEAK_CONTEXT_ONLY
#    for downstream management-priority integration.
# 5) No HIGH confidence is allowed without local actual FFB labels.
#
# IMPORTANT
# ---------
# Q25/Q75 are relative pilot thresholds, not agronomic yield standards.
# 40G02 does not assign final management-priority Class 0-4.
# ============================================================

from pathlib import Path
import csv
import json
import math
import statistics

WORKDIR = Path(
    r"C:\Users\user\Documents\KERJA\SPATIAL DATA ANALYST INTERN\04_YIELD"
)

CALIB = WORKDIR / (
    "40G01_PRODUCTIVITY_CALIBRATION_CONFIDENCE_820_SIAK_AOI01_V1.csv"
)

SENS = WORKDIR / (
    "40G01_PRODUCTIVITY_THRESHOLD_SENSITIVITY_SIAK_AOI01_V1.csv"
)

OUT_MASTER = WORKDIR / (
    "40G02_FROZEN_PRODUCTIVITY_CALIBRATION_820_SIAK_AOI01_V1.csv"
)

OUT_SUMMARY = WORKDIR / (
    "40G02_FROZEN_PRODUCTIVITY_CALIBRATION_SUMMARY_SIAK_AOI01_V1.csv"
)

OUT_QC = WORKDIR / (
    "40G02_PRODUCTIVITY_CALIBRATION_FREEZE_QC_SIAK_AOI01_V1.json"
)

print("====================================================")
print("40G02 — PRODUCTIVITY THRESHOLD + CONFIDENCE FREEZE")
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


def f(value):
    x = float(value)
    if not math.isfinite(x):
        raise ValueError(f"Non-finite numeric value: {value}")
    return x


# ------------------------------------------------------------
# 1. PREFLIGHT
# ------------------------------------------------------------

for p in [CALIB, SENS]:
    if not p.exists():
        raise FileNotFoundError(p)

rows = read_csv_dict(CALIB)
sens = read_csv_dict(SENS)

if len(rows) != 820:
    raise ValueError(
        f"Expected 820 calibration rows; got {len(rows)}."
    )

if len({r["UNIT_ID"] for r in rows}) != 820:
    raise ValueError(
        "40G01 UNIT_ID is not unique."
    )

if len(sens) != 3:
    raise ValueError(
        f"Expected 3 sensitivity schemes; got {len(sens)}."
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
print("Direct PALMSIM                 :", len(direct))
print("Fallback                       :", len(fallback))


# ------------------------------------------------------------
# 2. FREEZE Q25/Q75 THRESHOLDS
# ------------------------------------------------------------

low_values = {
    f(r["PRODUCTIVITY_LOW_THRESHOLD_T_HA_YR"])
    for r in rows
}

high_values = {
    f(r["PRODUCTIVITY_HIGH_THRESHOLD_T_HA_YR"])
    for r in rows
}

if len(low_values) != 1 or len(high_values) != 1:
    raise ValueError(
        "40G01 threshold fields are not globally consistent."
    )

LOW_THR = next(iter(low_values))
HIGH_THR = next(iter(high_values))

if LOW_THR >= HIGH_THR:
    raise ValueError(
        "Frozen thresholds are not ordered."
    )

print("Frozen LOW threshold <=        :", LOW_THR)
print("Frozen HIGH threshold >=       :", HIGH_THR)


# ------------------------------------------------------------
# 3. READ THRESHOLD SENSITIVITY
# ------------------------------------------------------------

sens_by_name = {
    r["SCHEME"]: r
    for r in sens
}

required_schemes = {
    "Q20_Q80",
    "Q25_Q75_BASELINE",
    "Q30_Q70",
}

if set(sens_by_name) != required_schemes:
    raise ValueError(
        "Unexpected threshold sensitivity schemes."
    )

alt_switches = [
    f(
        sens_by_name["Q20_Q80"][
            "SWITCH_FROM_BASELINE_ALL_PCT"
        ]
    ),
    f(
        sens_by_name["Q30_Q70"][
            "SWITCH_FROM_BASELINE_ALL_PCT"
        ]
    ),
]

MAX_ALT_SWITCH_PCT = max(alt_switches)

# This is intentionally descriptive, not a statistical validity test.
THRESHOLD_SENSITIVITY_NOTE = (
    "Alternative quantile schemes change about "
    f"{MAX_ALT_SWITCH_PCT:.2f}% or less of all ASU assignments; "
    "Q25/Q75 is retained as a transparent pilot relative partition, "
    "not as an agronomic optimum."
)


# ------------------------------------------------------------
# 4. FREEZE ROW-LEVEL PRODUCTIVITY EVIDENCE
# ------------------------------------------------------------

out = []

for r in rows:

    pathway = r["PRODUCTIVITY_PATHWAY"]

    center_band = r["PRODUCTIVITY_BAND_BASELINE"]

    if center_band not in {
        "RELATIVE_LOW",
        "RELATIVE_TYPICAL",
        "RELATIVE_HIGH",
    }:
        raise ValueError(
            f"Invalid center band for {r['UNIT_ID']}: {center_band}"
        )

    if pathway == "DIRECT_MODEL_SUPPORTED":

        frozen_band = center_band

        band_status = (
            "FROZEN_DIRECT_RELATIVE_BAND"
        )

        band_confidence = (
            r["PRODUCTIVITY_CONFIDENCE_40G01"]
        )

        evidence_role_40h = (
            "STANDARD_RELATIVE_PRODUCTIVITY_EVIDENCE"
        )

        fallback_guardrail = (
            "NOT_APPLICABLE"
        )

    else:

        # All 166 fallback intervals crossed multiple bands in 40G01.
        if (
            r["FALLBACK_INTERVAL_BAND_STABILITY"]
            != "UNCERTAIN_SPANS_MULTIPLE_BANDS"
        ):
            raise ValueError(
                "Fallback interval stability changed unexpectedly "
                f"for {r['UNIT_ID']}."
            )

        # Keep the center band so the website can still show
        # a relative position, but explicitly do NOT treat it as
        # a stable classification.
        frozen_band = center_band

        band_status = (
            "INDICATIVE_CENTER_BAND_ONLY__"
            "INTERVAL_SPANS_MULTIPLE_BANDS"
        )

        band_confidence = "VERY_LOW"

        evidence_role_40h = (
            "WEAK_CONTEXT_ONLY"
        )

        fallback_guardrail = (
            "MAY_NOT_TRIGGER_CLASS_3_OR_4_FROM_PRODUCTIVITY_ALONE"
        )

    out.append({
        **r,

        "PRODUCTIVITY_BAND_FINAL":
            frozen_band,

        "PRODUCTIVITY_BAND_FINAL_STATUS":
            band_status,

        "PRODUCTIVITY_BAND_CONFIDENCE_FINAL":
            band_confidence,

        "PRODUCTIVITY_EVIDENCE_ROLE_40H":
            evidence_role_40h,

        "FALLBACK_MANAGEMENT_GUARDRAIL":
            fallback_guardrail,

        "PRODUCTIVITY_THRESHOLD_FREEZE":
            "Q25_Q75_DIRECT_PALMSIM_654",

        "FROZEN_LOW_THRESHOLD_T_HA_YR":
            LOW_THR,

        "FROZEN_HIGH_THRESHOLD_T_HA_YR":
            HIGH_THR,

        "THRESHOLD_INTERPRETATION":
            "RELATIVE_PILOT_NOT_AGRONOMIC_STANDARD",

        "HIGH_CONFIDENCE_ALLOWED":
            "NO_NO_LOCAL_FFB_VALIDATION",

        "MANAGEMENT_PRIORITY_CLASS":
            "PENDING_40H",

        "FREEZE_VERSION":
            "40G02_V1",
    })

write_csv_dict(
    OUT_MASTER,
    out
)


# ------------------------------------------------------------
# 5. SUMMARIES
# ------------------------------------------------------------

band_counts = {
    "RELATIVE_LOW": 0,
    "RELATIVE_TYPICAL": 0,
    "RELATIVE_HIGH": 0,
}

band_conf_counts = {
    "MODERATE": 0,
    "LOW": 0,
    "VERY_LOW": 0,
}

direct_band_conf = {
    "MODERATE": 0,
    "LOW": 0,
    "VERY_LOW": 0,
}

fallback_band_conf = {
    "MODERATE": 0,
    "LOW": 0,
    "VERY_LOW": 0,
}

for r in out:

    band_counts[
        r["PRODUCTIVITY_BAND_FINAL"]
    ] += 1

    bc = r[
        "PRODUCTIVITY_BAND_CONFIDENCE_FINAL"
    ]

    if bc not in band_conf_counts:
        raise ValueError(
            f"Unexpected final band confidence: {bc}"
        )

    band_conf_counts[bc] += 1

    if (
        r["PRODUCTIVITY_PATHWAY"]
        == "DIRECT_MODEL_SUPPORTED"
    ):
        direct_band_conf[bc] += 1
    else:
        fallback_band_conf[bc] += 1


summary_rows = [
    {
        "METRIC":
            "FROZEN_THRESHOLD_LOW_T_HA_YR",

        "VALUE":
            LOW_THR,

        "NOTE":
            "Direct PALMSIM Q25; relative pilot threshold.",
    },
    {
        "METRIC":
            "FROZEN_THRESHOLD_HIGH_T_HA_YR",

        "VALUE":
            HIGH_THR,

        "NOTE":
            "Direct PALMSIM Q75; relative pilot threshold.",
    },
    {
        "METRIC":
            "MAX_ALTERNATIVE_THRESHOLD_SWITCH_PCT",

        "VALUE":
            MAX_ALT_SWITCH_PCT,

        "NOTE":
            THRESHOLD_SENSITIVITY_NOTE,
    },
    {
        "METRIC":
            "FALLBACK_INTERVALS_SPANNING_MULTIPLE_BANDS",

        "VALUE":
            166,

        "NOTE":
            (
                "All fallback center bands are indicative only; "
                "final productivity-band confidence forced VERY_LOW."
            ),
    },
]

write_csv_dict(
    OUT_SUMMARY,
    summary_rows
)


# ------------------------------------------------------------
# 6. QC
# ------------------------------------------------------------

fallback_out = [
    r for r in out
    if r["PRODUCTIVITY_PATHWAY"]
    == "AGE_CENSORED_OR_UNRESOLVED_FALLBACK"
]

direct_out = [
    r for r in out
    if r["PRODUCTIVITY_PATHWAY"]
    == "DIRECT_MODEL_SUPPORTED"
]

checks = {

    "rows_820":
        len(out) == 820,

    "unique_asu_820":
        len({r["UNIT_ID"] for r in out}) == 820,

    "direct_rows_654":
        len(direct_out) == 654,

    "fallback_rows_166":
        len(fallback_out) == 166,

    "thresholds_consistent_and_ordered":
        LOW_THR < HIGH_THR,

    "all_final_bands_assigned":
        all(
            r["PRODUCTIVITY_BAND_FINAL"]
            in {
                "RELATIVE_LOW",
                "RELATIVE_TYPICAL",
                "RELATIVE_HIGH",
            }
            for r in out
        ),

    "all_fallback_intervals_span_multiple_bands":
        all(
            r["FALLBACK_INTERVAL_BAND_STABILITY"]
            == "UNCERTAIN_SPANS_MULTIPLE_BANDS"
            for r in fallback_out
        ),

    "all_fallback_band_confidence_very_low":
        all(
            r["PRODUCTIVITY_BAND_CONFIDENCE_FINAL"]
            == "VERY_LOW"
            for r in fallback_out
        ),

    "all_fallback_productivity_role_weak_context_only":
        all(
            r["PRODUCTIVITY_EVIDENCE_ROLE_40H"]
            == "WEAK_CONTEXT_ONLY"
            for r in fallback_out
        ),

    "fallback_cannot_trigger_class_3_4_from_productivity_alone":
        all(
            r["FALLBACK_MANAGEMENT_GUARDRAIL"]
            ==
            "MAY_NOT_TRIGGER_CLASS_3_OR_4_FROM_PRODUCTIVITY_ALONE"
            for r in fallback_out
        ),

    "no_high_productivity_band_confidence":
        all(
            r["PRODUCTIVITY_BAND_CONFIDENCE_FINAL"]
            != "HIGH"
            for r in out
        ),

    "management_priority_still_pending":
        all(
            r["MANAGEMENT_PRIORITY_CLASS"]
            == "PENDING_40H"
            for r in out
        ),
}

status = (
    "PASS_PRODUCTIVITY_CALIBRATION_FROZEN"
    if all(checks.values())
    else "REVIEW"
)


# ------------------------------------------------------------
# 7. SAVE QC JSON
# ------------------------------------------------------------

qc = {
    "gate":
        "40G02_PRODUCTIVITY_THRESHOLD_AND_CONFIDENCE_FREEZE",

    "status":
        status,

    "frozen_thresholds": {
        "reference":
            "654 direct PALMSIM ASUs",

        "scheme":
            "Q25_Q75",

        "low_threshold_t_ha_yr":
            LOW_THR,

        "high_threshold_t_ha_yr":
            HIGH_THR,

        "interpretation":
            "relative pilot bands, not agronomic standards",
    },

    "sensitivity": {
        "q20_q80_switch_pct":
            f(
                sens_by_name["Q20_Q80"][
                    "SWITCH_FROM_BASELINE_ALL_PCT"
                ]
            ),

        "q30_q70_switch_pct":
            f(
                sens_by_name["Q30_Q70"][
                    "SWITCH_FROM_BASELINE_ALL_PCT"
                ]
            ),

        "max_alternative_switch_pct":
            MAX_ALT_SWITCH_PCT,

        "decision":
            THRESHOLD_SENSITIVITY_NOTE,
    },

    "final_band_counts_820":
        band_counts,

    "productivity_band_confidence_counts_820":
        band_conf_counts,

    "direct_band_confidence_counts_654":
        direct_band_conf,

    "fallback_band_confidence_counts_166":
        fallback_band_conf,

    "fallback_decision": {
        "all_166_intervals_span_multiple_bands":
            True,

        "center_band_retained_for_display":
            True,

        "center_band_treated_as_stable_classification":
            False,

        "productivity_band_confidence":
            "VERY_LOW",

        "downstream_management_evidence_role":
            "WEAK_CONTEXT_ONLY",

        "guardrail":
            (
                "Fallback productivity alone may not trigger "
                "Management Priority Class 3 or Class 4."
            ),
    },

    "scientific_interpretation": [
        "Q25/Q75 is frozen because it is a transparent relative partition of the direct PALMSIM reference distribution, not because it is an optimized agronomic threshold.",
        "Alternative Q20/Q80 and Q30/Q70 schemes change roughly ten percent of wall-to-wall assignments, so threshold uncertainty remains material and must be documented.",
        "All 166 fallback uncertainty intervals span more than one productivity band; therefore the fallback center band is descriptive only.",
        "Fallback productivity-band confidence is set to VERY_LOW for all 166 ASUs.",
        "Direct productivity-band confidence retains the 40G01 MODERATE/LOW/VERY_LOW design.",
        "No HIGH confidence is allowed because actual local FFB/TBS validation is unavailable.",
        "Final management-priority Class 0-4 remains downstream in 40H."
    ],

    "checks":
        checks,

    "next":
        (
            "40H01 management-priority integration design/execution "
            "using productivity + condition + age/evidence + confidence."
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
# 8. PRINT
# ------------------------------------------------------------

print("\n====================================================")
print("40G02 FINISHED")
print("====================================================")
print("Status                         :", status)

print("\nFROZEN PRODUCTIVITY THRESHOLDS")
print("LOW <=                         :", LOW_THR)
print("HIGH >=                        :", HIGH_THR)
print("Schema                         : Q25/Q75 direct PALMSIM")
print("Interpretation                 : RELATIVE PILOT")

print("\nSENSITIVITY")
print(
    "Q20/Q80 switches              :",
    sens_by_name["Q20_Q80"][
        "SWITCH_FROM_BASELINE_ALL_PCT"
    ],
    "%"
)
print(
    "Q30/Q70 switches              :",
    sens_by_name["Q30_Q70"][
        "SWITCH_FROM_BASELINE_ALL_PCT"
    ],
    "%"
)
print(
    "Max alternative switch        :",
    MAX_ALT_SWITCH_PCT,
    "%"
)

print("\nFINAL PRODUCTIVITY BAND COUNTS")
print(band_counts)

print("\nPRODUCTIVITY-BAND CONFIDENCE 820")
print(band_conf_counts)

print("\nDIRECT BAND CONFIDENCE 654")
print(direct_band_conf)

print("\nFALLBACK BAND CONFIDENCE 166")
print(fallback_band_conf)
print("Fallback evidence role         : WEAK_CONTEXT_ONLY")
print(
    "Fallback Class 3/4 guardrail  : "
    "cannot trigger from productivity alone"
)

print("\nQC:")
for key, value in checks.items():
    print(f"{key:58s}: {value}")

print("\nFrozen master CSV :", OUT_MASTER)
print("Summary CSV       :", OUT_SUMMARY)
print("Freeze/QC JSON    :", OUT_QC)

if status == "PASS_PRODUCTIVITY_CALIBRATION_FROZEN":
    print(
        "Next              : 40H01 management-priority "
        "integration design/execution."
    )
else:
    print(
        "Next              : Review failed QC before 40H."
    )

print("====================================================")
