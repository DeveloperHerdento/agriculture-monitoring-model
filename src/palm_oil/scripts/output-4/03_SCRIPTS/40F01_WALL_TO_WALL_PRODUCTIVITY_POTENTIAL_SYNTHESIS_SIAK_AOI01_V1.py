# ============================================================
# OUTPUT 4 / 40F01
# WALL-TO-WALL PRODUCTIVITY POTENTIAL SYNTHESIS
# SIAK_AOI01
#
# PURE PYTHON STANDARD LIBRARY ONLY
# NO numpy / pandas / scipy
# NO PALMSIM/APSIM rerun
#
# PURPOSE
# -------
# Merge the two frozen Output-4 productivity pathways into one
# 820-ASU wall-to-wall analytical table:
#
#   654 ASUs -> direct PALMSIM modelled productivity potential
#   166 ASUs -> frozen indicative peer-based fallback potential
#
# IMPORTANT
# ---------
# - All 820 palm ASUs receive productivity information.
# - Direct and fallback pathways remain explicitly distinguishable.
# - Fallback estimates are NOT treated as equivalent-confidence
#   direct PALMSIM outputs.
# - No productivity classes or management-priority classes are
#   assigned here. Threshold/class calibration remains 40G.
# ============================================================

from pathlib import Path
import csv
import json
import math
import statistics

WORKDIR = Path(
    r"C:\Users\user\Documents\KERJA\SPATIAL DATA ANALYST INTERN\04_YIELD"
)

CONTRACT = WORKDIR / (
    "40E02_V2_WALL_TO_WALL_COVERAGE_CONTRACT_SIAK_AOI01.csv"
)

COMMON = WORKDIR / (
    "40B05_COMMON_MODEL_INPUT_MASTER_SIAK_AOI01_V1.csv"
)

PALMSIM = WORKDIR / (
    "40C04A_DIRECT_P00_BASELINE_RESULTS_SIAK_AOI01_V1.csv"
)

FALLBACK = WORKDIR / (
    "40E03C_FROZEN_FALLBACK_PRODUCTIVITY_166_SIAK_AOI01_V1.csv"
)

OUT_MASTER = WORKDIR / (
    "40F01_WALL_TO_WALL_PRODUCTIVITY_POTENTIAL_820_SIAK_AOI01_V1.csv"
)

OUT_SUMMARY = WORKDIR / (
    "40F01_PRODUCTIVITY_PATHWAY_SUMMARY_SIAK_AOI01_V1.csv"
)

OUT_QC = WORKDIR / (
    "40F01_WALL_TO_WALL_PRODUCTIVITY_POTENTIAL_QC_SIAK_AOI01_V1.json"
)

print("====================================================")
print("40F01 — WALL-TO-WALL PRODUCTIVITY POTENTIAL SYNTHESIS")
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


def get_value(row, candidates, default=""):
    for c in candidates:
        if c in row:
            return row[c]
    return default


# ------------------------------------------------------------
# 1. PREFLIGHT
# ------------------------------------------------------------

for p in [CONTRACT, COMMON, PALMSIM, FALLBACK]:
    if not p.exists():
        raise FileNotFoundError(p)

contract_rows = read_csv_dict(CONTRACT)
common_rows = read_csv_dict(COMMON)
palm_rows = read_csv_dict(PALMSIM)
fallback_rows = read_csv_dict(FALLBACK)

if len(contract_rows) != 820:
    raise ValueError(
        f"Expected 820 contract rows; got {len(contract_rows)}."
    )

if len(common_rows) != 820:
    raise ValueError(
        f"Expected 820 common input rows; got {len(common_rows)}."
    )

if len(palm_rows) != 654:
    raise ValueError(
        f"Expected 654 PALMSIM rows; got {len(palm_rows)}."
    )

if len(fallback_rows) != 166:
    raise ValueError(
        f"Expected 166 frozen fallback rows; got {len(fallback_rows)}."
    )

contract = {
    str(r["UNIT_ID"]): r
    for r in contract_rows
}

common = {
    str(r["UNIT_ID"]): r
    for r in common_rows
}

if len(contract) != 820:
    raise ValueError(
        "Contract UNIT_ID not unique."
    )

if len(common) != 820:
    raise ValueError(
        "Common-input UNIT_ID not unique."
    )

if set(contract) != set(common):
    raise ValueError(
        "Contract and common-input UNIT_ID sets differ."
    )

print("Master spatial domain           :", len(contract))


# ------------------------------------------------------------
# 2. PALMSIM LOOKUP
# ------------------------------------------------------------

palm_columns = list(palm_rows[0].keys())

preferred_yield_fields = [
    "TRAILING_1Y_MEAN_T_HA_YR",
    "POTENTIAL_T_HA_YR",
    "BASELINE_T_HA_YR",
    "FFB_T_HA_YR",
]

yield_field = None

for c in preferred_yield_fields:
    if c in palm_columns:
        yield_field = c
        break

if yield_field is None:
    candidates = [
        c
        for c in palm_columns
        if (
            "T_HA_YR" in c.upper()
            and (
                "TRAIL" in c.upper()
                or "POTENTIAL" in c.upper()
                or "BASE" in c.upper()
            )
        )
    ]

    if len(candidates) != 1:
        raise ValueError(
            "Could not uniquely identify PALMSIM yield field. "
            f"Candidates={candidates}"
        )

    yield_field = candidates[0]

palm_lookup = {}

for r in palm_rows:
    uid = str(r["UNIT_ID"])

    if uid in palm_lookup:
        raise ValueError(
            f"Duplicate PALMSIM UNIT_ID: {uid}"
        )

    y = to_float_or_none(
        r.get(yield_field)
    )

    if y is None:
        raise ValueError(
            f"Non-finite PALMSIM yield: {uid}"
        )

    palm_lookup[uid] = y

if len(palm_lookup) != 654:
    raise ValueError(
        "PALMSIM lookup does not contain 654 unique ASUs."
    )

print("Direct PALMSIM estimates        :", len(palm_lookup))
print("PALMSIM yield field             :", yield_field)


# ------------------------------------------------------------
# 3. FROZEN FALLBACK LOOKUP
# ------------------------------------------------------------

fallback_lookup = {}

for r in fallback_rows:
    uid = str(r["UNIT_ID"])

    if uid in fallback_lookup:
        raise ValueError(
            f"Duplicate fallback UNIT_ID: {uid}"
        )

    low = to_float_or_none(
        r.get(
            "FINAL_INDICATIVE_LOW_T_FFB_HA_YR"
        )
    )

    center = to_float_or_none(
        r.get(
            "DISPLAY_CENTER_T_FFB_HA_YR"
        )
    )

    high = to_float_or_none(
        r.get(
            "FINAL_INDICATIVE_HIGH_T_FFB_HA_YR"
        )
    )

    if (
        low is None
        or center is None
        or high is None
    ):
        raise ValueError(
            f"Fallback range incomplete: {uid}"
        )

    if not (
        low <= center <= high
    ):
        raise ValueError(
            f"Fallback range unordered: {uid}"
        )

    fallback_lookup[uid] = {
        "LOW": low,
        "CENTER": center,
        "HIGH": high,
        "CONFIDENCE": str(
            r.get(
                "FALLBACK_CONFIDENCE",
                "VERY_LOW"
            )
        ),
        "MATCH_TIER": str(
            r.get(
                "CLIMATE_MATCH_TIER",
                ""
            )
        ),
        "FEATURE_MODE": str(
            r.get(
                "FEATURE_MODE",
                ""
            )
        ),
        "PEER_N": str(
            r.get(
                "SELECTED_PEER_N",
                ""
            )
        ),
    }

if len(fallback_lookup) != 166:
    raise ValueError(
        "Fallback lookup does not contain 166 unique ASUs."
    )

print("Frozen fallback estimates       :", len(fallback_lookup))


# ------------------------------------------------------------
# 4. VERIFY PATHWAY PARTITION
# ------------------------------------------------------------

direct_contract_ids = {
    uid
    for uid, r in contract.items()
    if r["OUTPUT4_ANALYTICAL_PATHWAY"]
    == "DIRECT_MODEL_SUPPORTED"
}

fallback_contract_ids = {
    uid
    for uid, r in contract.items()
    if r["OUTPUT4_ANALYTICAL_PATHWAY"]
    == "AGE_CENSORED_OR_UNRESOLVED_FALLBACK"
}

if direct_contract_ids != set(palm_lookup):
    raise ValueError(
        "40E02 direct pathway IDs do not match PALMSIM IDs."
    )

if fallback_contract_ids != set(fallback_lookup):
    raise ValueError(
        "40E02 fallback pathway IDs do not match 40E03C frozen fallback IDs."
    )

if (
    direct_contract_ids
    & fallback_contract_ids
):
    raise ValueError(
        "Direct and fallback pathways overlap."
    )

if (
    direct_contract_ids
    | fallback_contract_ids
) != set(contract):
    raise ValueError(
        "Direct + fallback pathways do not cover all 820 ASUs."
    )


# ------------------------------------------------------------
# 5. BUILD UNIFIED 820-ASU PRODUCTIVITY TABLE
# ------------------------------------------------------------

master_out = []

for uid in sorted(contract):

    c = contract[uid]
    x = common[uid]

    age_p50 = to_float_or_none(
        c.get("AGE_P50")
    )

    condition_score = to_float_or_none(
        x.get("CONDITION_SCORE")
    )

    condition_valid_fraction = (
        to_float_or_none(
            x.get(
                "CONDITION_VALID_FRACTION"
            )
        )
    )

    age_valid_fraction = (
        to_float_or_none(
            x.get(
                "AGE_VALID_FRACTION"
            )
        )
    )

    sand = to_float_or_none(
        x.get("SAND_0_100_PCT")
    )

    silt = to_float_or_none(
        x.get("SILT_0_100_PCT")
    )

    clay = to_float_or_none(
        x.get("CLAY_0_100_PCT")
    )

    if uid in palm_lookup:

        pathway = "DIRECT_MODEL_SUPPORTED"

        estimate_type = (
            "PALMSIM_DIRECT_MODELLED_POTENTIAL"
        )

        center = palm_lookup[uid]

        # Direct PALMSIM interval is intentionally not invented here.
        low = ""
        high = ""
        range_available = "NO_PENDING_40G_UNCERTAINTY"

        support_tier = "A_DIRECT_PROCESS_MODEL"

        confidence = (
            "MODEL_SUPPORTED__FINAL_CONFIDENCE_PENDING_40G"
        )

        display_status = "DIRECT_MODELLED_POTENTIAL"

        popup_warning = (
            "Modelled productivity potential from PALMSIM; "
            "not actual or field-validated FFB yield."
        )

        fallback_match_tier = ""
        fallback_feature_mode = ""
        fallback_peer_n = ""

    else:

        fb = fallback_lookup[uid]

        pathway = (
            "AGE_CENSORED_OR_UNRESOLVED_FALLBACK"
        )

        estimate_type = (
            "INDICATIVE_PEER_BASED_FALLBACK"
        )

        center = fb["CENTER"]
        low = fb["LOW"]
        high = fb["HIGH"]
        range_available = "YES"

        support_tier = (
            "B_INDICATIVE_FALLBACK"
        )

        confidence = fb["CONFIDENCE"]

        display_status = (
            "INDICATIVE_RANGE__AGE_UNRESOLVED"
        )

        popup_warning = (
            "Age proxy unresolved; productivity is an "
            "indicative peer-based range, not a direct "
            "PALMSIM simulation."
        )

        fallback_match_tier = (
            fb["MATCH_TIER"]
        )

        fallback_feature_mode = (
            fb["FEATURE_MODE"]
        )

        fallback_peer_n = (
            fb["PEER_N"]
        )

    # Human-readable display text for later web use.
    if pathway == "DIRECT_MODEL_SUPPORTED":

        display_text = (
            f"{center:.2f} t FFB/ha/yr "
            "(modelled potential)"
        )

    else:

        display_text = (
            f"≈{center:.2f} t FFB/ha/yr; "
            f"indicative range {low:.2f}-{high:.2f}"
        )

    master_out.append({

        "UNIT_ID":
            uid,

        "OUTPUT4_SPATIAL_DOMAIN":
            "INCLUDED",

        "PRODUCTIVITY_PATHWAY":
            pathway,

        "PRODUCTIVITY_SUPPORT_TIER":
            support_tier,

        "PRODUCTIVITY_ESTIMATE_TYPE":
            estimate_type,

        "PRODUCTIVITY_CENTER_T_FFB_HA_YR":
            center,

        "PRODUCTIVITY_LOW_T_FFB_HA_YR":
            low,

        "PRODUCTIVITY_HIGH_T_FFB_HA_YR":
            high,

        "PRODUCTIVITY_RANGE_AVAILABLE":
            range_available,

        "PRODUCTIVITY_DISPLAY_STATUS":
            display_status,

        "PRODUCTIVITY_DISPLAY_TEXT":
            display_text,

        "PRODUCTIVITY_CONFIDENCE_PRELIM":
            confidence,

        "AGE_P50":
            age_p50 if age_p50 is not None else "",

        "AGE_STATUS":
            c.get(
                "AGE_STATUS_40E02",
                ""
            ),

        "AGE_VALID_FRACTION":
            (
                age_valid_fraction
                if age_valid_fraction is not None
                else ""
            ),

        "CONDITION_SCORE":
            (
                condition_score
                if condition_score is not None
                else ""
            ),

        "CONDITION_VALID_FRACTION":
            (
                condition_valid_fraction
                if condition_valid_fraction is not None
                else ""
            ),

        "SAND_0_100_PCT":
            sand if sand is not None else "",

        "SILT_0_100_PCT":
            silt if silt is not None else "",

        "CLAY_0_100_PCT":
            clay if clay is not None else "",

        "CHIRPS_CELL_ID":
            c.get(
                "CHIRPS_CELL_ID",
                ""
            ),

        "ERA5L_CELL_ID":
            c.get(
                "ERA5L_CELL_ID",
                ""
            ),

        "CLIMATE_PAIR_ID":
            c.get(
                "CLIMATE_PAIR_ID",
                ""
            ),

        "FALLBACK_CLIMATE_MATCH_TIER":
            fallback_match_tier,

        "FALLBACK_FEATURE_MODE":
            fallback_feature_mode,

        "FALLBACK_SELECTED_PEER_N":
            fallback_peer_n,

        "PRODUCTIVITY_CLASS":
            "PENDING_40G",

        "MANAGEMENT_PRIORITY_CLASS":
            "PENDING_40H",

        "COMPARABILITY_WARNING":
            (
                "DIRECT_AND_FALLBACK_CENTERS_HAVE_DIFFERENT_EVIDENCE_SUPPORT"
            ),

        "LOCAL_FFB_VALIDATED":
            "NO",

        "WALL_TO_WALL_SYNTHESIS_VERSION":
            "40F01_V1",

        "POPUP_WARNING":
            popup_warning,
    })

write_csv_dict(
    OUT_MASTER,
    master_out
)


# ------------------------------------------------------------
# 6. SUMMARY
# ------------------------------------------------------------

direct_out = [
    r
    for r in master_out
    if r["PRODUCTIVITY_PATHWAY"]
    == "DIRECT_MODEL_SUPPORTED"
]

fallback_out = [
    r
    for r in master_out
    if r["PRODUCTIVITY_PATHWAY"]
    == "AGE_CENSORED_OR_UNRESOLVED_FALLBACK"
]

all_centers = [
    float(
        r[
            "PRODUCTIVITY_CENTER_T_FFB_HA_YR"
        ]
    )
    for r in master_out
]

direct_centers = [
    float(
        r[
            "PRODUCTIVITY_CENTER_T_FFB_HA_YR"
        ]
    )
    for r in direct_out
]

fallback_centers = [
    float(
        r[
            "PRODUCTIVITY_CENTER_T_FFB_HA_YR"
        ]
    )
    for r in fallback_out
]

fallback_widths = [
    float(
        r[
            "PRODUCTIVITY_HIGH_T_FFB_HA_YR"
        ]
    )
    -
    float(
        r[
            "PRODUCTIVITY_LOW_T_FFB_HA_YR"
        ]
    )
    for r in fallback_out
]

fallback_low_count = sum(
    1
    for r in fallback_out
    if r[
        "PRODUCTIVITY_CONFIDENCE_PRELIM"
    ] == "LOW"
)

fallback_very_low_count = sum(
    1
    for r in fallback_out
    if r[
        "PRODUCTIVITY_CONFIDENCE_PRELIM"
    ] == "VERY_LOW"
)

summary_rows = [

    {
        "GROUP":
            "ALL_820_WALL_TO_WALL",

        "N_ASU":
            len(master_out),

        "CENTER_MIN_T_HA_YR":
            min(all_centers),

        "CENTER_MEDIAN_T_HA_YR":
            statistics.median(
                all_centers
            ),

        "CENTER_MEAN_T_HA_YR":
            mean(all_centers),

        "CENTER_MAX_T_HA_YR":
            max(all_centers),

        "RANGE_NOTE":
            (
                "Mixed evidence support; direct PALMSIM and "
                "fallback centers must remain distinguishable."
            ),
    },

    {
        "GROUP":
            "DIRECT_PALMSIM_654",

        "N_ASU":
            len(direct_out),

        "CENTER_MIN_T_HA_YR":
            min(direct_centers),

        "CENTER_MEDIAN_T_HA_YR":
            statistics.median(
                direct_centers
            ),

        "CENTER_MEAN_T_HA_YR":
            mean(direct_centers),

        "CENTER_MAX_T_HA_YR":
            max(direct_centers),

        "RANGE_NOTE":
            "Direct uncertainty interval pending 40G.",
    },

    {
        "GROUP":
            "INDICATIVE_FALLBACK_166",

        "N_ASU":
            len(fallback_out),

        "CENTER_MIN_T_HA_YR":
            min(fallback_centers),

        "CENTER_MEDIAN_T_HA_YR":
            statistics.median(
                fallback_centers
            ),

        "CENTER_MEAN_T_HA_YR":
            mean(fallback_centers),

        "CENTER_MAX_T_HA_YR":
            max(fallback_centers),

        "RANGE_NOTE":
            (
                "Frozen indicative peer-based center + "
                "conservative interval."
            ),
    },
]

write_csv_dict(
    OUT_SUMMARY,
    summary_rows
)


# ------------------------------------------------------------
# 7. QC
# ------------------------------------------------------------

out_ids = {
    r["UNIT_ID"]
    for r in master_out
}

checks = {

    "wall_to_wall_rows_820":
        len(master_out) == 820,

    "wall_to_wall_unique_asu_820":
        len(out_ids) == 820,

    "exact_master_spatial_domain":
        out_ids == set(contract),

    "direct_rows_654":
        len(direct_out) == 654,

    "fallback_rows_166":
        len(fallback_out) == 166,

    "direct_plus_fallback_equals_820":
        len(direct_out)
        + len(fallback_out)
        == 820,

    "all_820_have_productivity_center":
        all(
            math.isfinite(
                float(
                    r[
                        "PRODUCTIVITY_CENTER_T_FFB_HA_YR"
                    ]
                )
            )
            for r in master_out
        ),

    "fallback_all_have_ranges":
        all(
            str(
                r[
                    "PRODUCTIVITY_LOW_T_FFB_HA_YR"
                ]
            ).strip() != ""
            and
            str(
                r[
                    "PRODUCTIVITY_HIGH_T_FFB_HA_YR"
                ]
            ).strip() != ""
            for r in fallback_out
        ),

    "fallback_ranges_ordered":
        all(
            float(
                r[
                    "PRODUCTIVITY_LOW_T_FFB_HA_YR"
                ]
            )
            <=
            float(
                r[
                    "PRODUCTIVITY_CENTER_T_FFB_HA_YR"
                ]
            )
            <=
            float(
                r[
                    "PRODUCTIVITY_HIGH_T_FFB_HA_YR"
                ]
            )
            for r in fallback_out
        ),

    "direct_ranges_not_fabricated":
        all(
            str(
                r[
                    "PRODUCTIVITY_LOW_T_FFB_HA_YR"
                ]
            ).strip() == ""
            and
            str(
                r[
                    "PRODUCTIVITY_HIGH_T_FFB_HA_YR"
                ]
            ).strip() == ""
            for r in direct_out
        ),

    "productivity_class_not_prematurely_assigned":
        all(
            r["PRODUCTIVITY_CLASS"]
            == "PENDING_40G"
            for r in master_out
        ),

    "management_priority_not_prematurely_assigned":
        all(
            r[
                "MANAGEMENT_PRIORITY_CLASS"
            ] == "PENDING_40H"
            for r in master_out
        ),

    "no_local_ffb_validation_claim":
        all(
            r[
                "LOCAL_FFB_VALIDATED"
            ] == "NO"
            for r in master_out
        ),
}

status = (
    "PASS_WALL_TO_WALL_PRODUCTIVITY_SYNTHESIS"
    if all(checks.values())
    else "REVIEW"
)


# ------------------------------------------------------------
# 8. SAVE QC JSON
# ------------------------------------------------------------

qc = {

    "gate":
        "40F01_WALL_TO_WALL_PRODUCTIVITY_POTENTIAL_SYNTHESIS",

    "status":
        status,

    "coverage": {
        "total_asus":
            len(master_out),

        "direct_palmsim_asus":
            len(direct_out),

        "indicative_fallback_asus":
            len(fallback_out),

        "productivity_center_coverage":
            "820_OF_820",
    },

    "direct_palmsim_summary": {
        "min_t_ha_yr":
            min(direct_centers),

        "median_t_ha_yr":
            statistics.median(
                direct_centers
            ),

        "mean_t_ha_yr":
            mean(direct_centers),

        "max_t_ha_yr":
            max(direct_centers),

        "interval_status":
            "PENDING_40G_UNCERTAINTY",
    },

    "fallback_summary": {
        "min_center_t_ha_yr":
            min(fallback_centers),

        "median_center_t_ha_yr":
            statistics.median(
                fallback_centers
            ),

        "mean_center_t_ha_yr":
            mean(fallback_centers),

        "max_center_t_ha_yr":
            max(fallback_centers),

        "median_final_range_width_t_ha_yr":
            statistics.median(
                fallback_widths
            ),

        "p95_final_range_width_t_ha_yr":
            quantile(
                fallback_widths,
                0.95
            ),

        "low_confidence_count":
            fallback_low_count,

        "very_low_confidence_count":
            fallback_very_low_count,
    },

    "all_820_center_summary": {
        "min_t_ha_yr":
            min(all_centers),

        "median_t_ha_yr":
            statistics.median(
                all_centers
            ),

        "mean_t_ha_yr":
            mean(all_centers),

        "max_t_ha_yr":
            max(all_centers),
    },

    "interpretation_contract": [
        "All 820 palm ASUs now carry productivity-potential information.",
        "654 direct ASUs use PALMSIM modelled productivity potential.",
        "166 fallback ASUs use indicative peer-based centers and conservative ranges because numeric age is unresolved.",
        "Direct and fallback estimates must remain visually and semantically distinguishable.",
        "Fallback centers are not equivalent-confidence substitutes for direct PALMSIM outputs.",
        "No productivity class is assigned in 40F01; threshold calibration remains 40G.",
        "No management-priority class is assigned in 40F01; integration remains 40H.",
        "No local actual FFB/TBS validation is claimed."
    ],

    "checks":
        checks,

    "next":
        (
            "40G01 productivity threshold/calibration and "
            "confidence/uncertainty design for wall-to-wall 820 ASUs."
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
print("40F01 FINISHED")
print("====================================================")
print("Status                         :", status)

print("\nWALL-TO-WALL COVERAGE")
print("Total ASUs                     :", len(master_out))
print("Direct PALMSIM                 :", len(direct_out))
print("Indicative fallback            :", len(fallback_out))
print("Productivity center coverage   : 820 / 820")

print("\nDIRECT PALMSIM 654")
print(
    "Min / median / mean / max      :",
    min(direct_centers),
    "/",
    statistics.median(direct_centers),
    "/",
    mean(direct_centers),
    "/",
    max(direct_centers)
)

print("\nFALLBACK 166")
print(
    "Center min/median/mean/max     :",
    min(fallback_centers),
    "/",
    statistics.median(fallback_centers),
    "/",
    mean(fallback_centers),
    "/",
    max(fallback_centers)
)
print(
    "Median final range width       :",
    statistics.median(fallback_widths),
    "t FFB/ha/yr"
)
print(
    "LOW / VERY_LOW confidence      :",
    fallback_low_count,
    "/",
    fallback_very_low_count
)

print("\nALL 820 CENTERS")
print(
    "Min / median / mean / max      :",
    min(all_centers),
    "/",
    statistics.median(all_centers),
    "/",
    mean(all_centers),
    "/",
    max(all_centers)
)

print("\nQC:")
for key, value in checks.items():
    print(
        f"{key:54s}: {value}"
    )

print("\nWall-to-wall CSV :", OUT_MASTER)
print("Summary CSV      :", OUT_SUMMARY)
print("QC JSON          :", OUT_QC)

if status == "PASS_WALL_TO_WALL_PRODUCTIVITY_SYNTHESIS":
    print(
        "Next             : 40G01 productivity threshold/"
        "calibration + confidence/uncertainty design."
    )
else:
    print(
        "Next             : Review failed QC before 40G."
    )

print("====================================================")
