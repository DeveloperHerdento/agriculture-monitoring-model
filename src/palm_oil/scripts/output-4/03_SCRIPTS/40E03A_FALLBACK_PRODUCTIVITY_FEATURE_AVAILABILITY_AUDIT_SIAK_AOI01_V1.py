# ============================================================
# OUTPUT 4 / 40E03A
# FALLBACK PRODUCTIVITY — FEATURE AVAILABILITY & DESIGN AUDIT
# SIAK_AOI01
#
# PURE PYTHON STANDARD LIBRARY ONLY
# NO numpy / pandas / scipy
# NO PALMSIM/APSIM rerun
#
# Goal:
# Audit which existing ASU-level features can defensibly support
# fallback productivity estimation for the 166 age-unresolved ASUs.
#
# This stage DOES NOT estimate productivity yet.
# It identifies:
# - condition feature source
# - soil texture feature source
# - age/no-event evidence fields if available
# - climate-pair availability
# - donor/recipient coverage
#
# Next if PASS:
# 40E03B = peer-based indicative productivity range for 166 ASUs.
# ============================================================

from pathlib import Path
import csv
import json
import math

WORKDIR = Path(
    r"C:\Users\user\Documents\KERJA\SPATIAL DATA ANALYST INTERN\04_YIELD"
)

CONTRACT = WORKDIR / (
    "40E02_V2_WALL_TO_WALL_COVERAGE_CONTRACT_SIAK_AOI01.csv"
)

OUT_JSON = WORKDIR / (
    "40E03A_FALLBACK_FEATURE_AVAILABILITY_AUDIT_SIAK_AOI01_V1.json"
)

OUT_CSV = WORKDIR / (
    "40E03A_FALLBACK_FEATURE_CANDIDATE_FILES_SIAK_AOI01_V1.csv"
)

print("====================================================")
print("40E03A — FALLBACK FEATURE AVAILABILITY & DESIGN AUDIT")
print("PURE PYTHON / NO MODEL RERUN")
print("====================================================")


# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------

def read_header(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        try:
            return next(reader)
        except StopIteration:
            return []


def read_csv_dict(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv_dict(path, rows):
    if not rows:
        return
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


def keyword_hits(columns, keywords):
    out = []
    for c in columns:
        cu = c.upper()
        if any(k in cu for k in keywords):
            out.append(c)
    return out


def count_unit_overlap(path, target_ids):
    """
    Read only UNIT_ID column logically using DictReader.
    Returns unique overlap count if UNIT_ID exists.
    """
    rows = read_csv_dict(path)
    if not rows:
        return 0, 0

    if "UNIT_ID" not in rows[0]:
        return 0, 0

    ids = {
        str(r["UNIT_ID"])
        for r in rows
        if str(r.get("UNIT_ID", "")).strip() != ""
    }

    return len(ids), len(ids & target_ids)


# ------------------------------------------------------------
# 1. LOAD 40E02 CONTRACT
# ------------------------------------------------------------

if not CONTRACT.exists():
    raise FileNotFoundError(CONTRACT)

contract = read_csv_dict(CONTRACT)

if len(contract) != 820:
    raise ValueError(
        f"Expected 820 contract rows; got {len(contract)}."
    )

direct_ids = {
    r["UNIT_ID"]
    for r in contract
    if r["OUTPUT4_ANALYTICAL_PATHWAY"]
    == "DIRECT_MODEL_SUPPORTED"
}

fallback_ids = {
    r["UNIT_ID"]
    for r in contract
    if r["OUTPUT4_ANALYTICAL_PATHWAY"]
    == "AGE_CENSORED_OR_UNRESOLVED_FALLBACK"
}

all_ids = {
    r["UNIT_ID"]
    for r in contract
}

if len(direct_ids) != 654:
    raise ValueError(
        f"Expected 654 direct IDs; got {len(direct_ids)}."
    )

if len(fallback_ids) != 166:
    raise ValueError(
        f"Expected 166 fallback IDs; got {len(fallback_ids)}."
    )

print("Master ASUs                    :", len(all_ids))
print("Direct donors                  :", len(direct_ids))
print("Fallback recipients            :", len(fallback_ids))


# ------------------------------------------------------------
# 2. SCAN EXISTING CSV HEADERS
# ------------------------------------------------------------

csv_files = sorted(WORKDIR.glob("*.csv"))

candidate_rows = []

condition_keywords = [
    "CONDITION",
    "COND",
    "RISK",
    "SCORE",
]

soil_keywords = [
    "SAND",
    "SILT",
    "CLAY",
]

age_evidence_keywords = [
    "AGE_CLASS",
    "EVENT",
    "PRE2001",
    "PRE_2001",
    "NO_EVENT",
    "NOEVENT",
    "AGE_COVER",
    "AGE_VALID",
    "DETECTED",
]

for path in csv_files:

    # Do not treat outputs from this audit as inputs.
    if path.name.startswith("40E03"):
        continue

    try:
        cols = read_header(path)
    except Exception:
        continue

    if not cols:
        continue

    has_unit = "UNIT_ID" in cols

    cond_hits = keyword_hits(
        cols,
        condition_keywords
    )

    soil_hits = keyword_hits(
        cols,
        soil_keywords
    )

    age_hits = keyword_hits(
        cols,
        age_evidence_keywords
    )

    has_climate_pair = (
        "CLIMATE_PAIR_ID" in cols
    )

    # Keep files that may contain useful ASU-level evidence.
    useful = (
        has_unit
        and (
            len(cond_hits) > 0
            or len(soil_hits) > 0
            or len(age_hits) > 0
            or has_climate_pair
        )
    )

    if not useful:
        continue

    try:
        unique_unit_count, overlap_820 = count_unit_overlap(
            path,
            all_ids
        )
    except Exception:
        unique_unit_count, overlap_820 = 0, 0

    candidate_rows.append({
        "FILE_NAME":
            path.name,

        "HAS_UNIT_ID":
            has_unit,

        "UNIQUE_UNIT_ID_COUNT":
            unique_unit_count,

        "OVERLAP_WITH_MASTER_820":
            overlap_820,

        "CONDITION_COLUMNS":
            " | ".join(cond_hits),

        "SOIL_COLUMNS":
            " | ".join(soil_hits),

        "AGE_EVIDENCE_COLUMNS":
            " | ".join(age_hits),

        "HAS_CLIMATE_PAIR_ID":
            has_climate_pair,

        "TOTAL_COLUMNS":
            len(cols),
    })


# ------------------------------------------------------------
# 3. SCORE CANDIDATE FILES
# ------------------------------------------------------------

def split_hits(text):
    return [
        x.strip()
        for x in text.split("|")
        if x.strip()
    ]


for r in candidate_rows:

    cond_n = len(
        split_hits(r["CONDITION_COLUMNS"])
    )

    soil_n = len(
        split_hits(r["SOIL_COLUMNS"])
    )

    age_n = len(
        split_hits(r["AGE_EVIDENCE_COLUMNS"])
    )

    coverage_score = (
        3
        if r["OVERLAP_WITH_MASTER_820"] == 820
        else (
            2
            if r["OVERLAP_WITH_MASTER_820"] >= 654
            else 1
        )
    )

    score = 0

    if cond_n > 0:
        score += 4

    if soil_n >= 2:
        score += 5
    elif soil_n == 1:
        score += 2

    if age_n > 0:
        score += 3

    if r["HAS_CLIMATE_PAIR_ID"]:
        score += 2

    score += coverage_score

    r["CANDIDATE_SCORE"] = score


candidate_rows.sort(
    key=lambda r: (
        r["CANDIDATE_SCORE"],
        r["OVERLAP_WITH_MASTER_820"]
    ),
    reverse=True
)

write_csv_dict(
    OUT_CSV,
    candidate_rows
)


# ------------------------------------------------------------
# 4. IDENTIFY BEST SOURCE CANDIDATES
# ------------------------------------------------------------

condition_candidates = [
    r for r in candidate_rows
    if r["CONDITION_COLUMNS"]
    and r["OVERLAP_WITH_MASTER_820"] >= 654
]

soil_candidates = [
    r for r in candidate_rows
    if r["SOIL_COLUMNS"]
    and r["OVERLAP_WITH_MASTER_820"] >= 654
]

age_candidates = [
    r for r in candidate_rows
    if r["AGE_EVIDENCE_COLUMNS"]
    and r["OVERLAP_WITH_MASTER_820"] >= 654
]

climate_candidates = [
    r for r in candidate_rows
    if r["HAS_CLIMATE_PAIR_ID"]
    and r["OVERLAP_WITH_MASTER_820"] == 820
]


# ------------------------------------------------------------
# 5. FEATURE-LEVEL COVERAGE CHECK FOR TOP CANDIDATES
# ------------------------------------------------------------

feature_checks = []

top_paths = []

for group in [
    condition_candidates[:3],
    soil_candidates[:3],
    age_candidates[:3],
    climate_candidates[:2],
]:
    for r in group:
        p = WORKDIR / r["FILE_NAME"]
        if p not in top_paths:
            top_paths.append(p)


for path in top_paths:

    rows = read_csv_dict(path)

    if not rows or "UNIT_ID" not in rows[0]:
        continue

    by_id = {
        str(r["UNIT_ID"]): r
        for r in rows
        if str(r.get("UNIT_ID", "")).strip() != ""
    }

    cols = list(rows[0].keys())

    feature_cols = []

    for c in cols:

        cu = c.upper()

        if (
            any(k in cu for k in condition_keywords)
            or any(k in cu for k in soil_keywords)
            or any(k in cu for k in age_evidence_keywords)
        ):
            feature_cols.append(c)

    for col in feature_cols:

        direct_valid = 0
        fallback_valid = 0

        for uid in direct_ids:
            if uid in by_id:
                value = by_id[uid].get(col, "")
                if str(value).strip() != "":
                    direct_valid += 1

        for uid in fallback_ids:
            if uid in by_id:
                value = by_id[uid].get(col, "")
                if str(value).strip() != "":
                    fallback_valid += 1

        feature_checks.append({
            "FILE_NAME":
                path.name,

            "COLUMN":
                col,

            "DIRECT_VALID_N":
                direct_valid,

            "DIRECT_VALID_PCT":
                round(
                    100.0 * direct_valid / 654.0,
                    3
                ),

            "FALLBACK_VALID_N":
                fallback_valid,

            "FALLBACK_VALID_PCT":
                round(
                    100.0 * fallback_valid / 166.0,
                    3
                ),
        })


# ------------------------------------------------------------
# 6. DESIGN DECISION
# ------------------------------------------------------------

# We require:
# - climate pair for all 820
# - at least one plausible condition source
# - at least one plausible soil source with >=2 soil texture cols
#
# Age-evidence refinement is useful but not mandatory for the
# first fallback estimator because unknown age will be explicitly
# marginalized rather than fabricated.

has_climate = len(climate_candidates) >= 1
has_condition = len(condition_candidates) >= 1
has_soil = any(
    len(split_hits(r["SOIL_COLUMNS"])) >= 2
    for r in soil_candidates
)

design_ready = (
    has_climate
    and has_condition
    and has_soil
)

status = (
    "PASS_FEATURE_AUDIT_READY_FOR_40E03B"
    if design_ready
    else "REVIEW_FEATURE_SOURCES"
)

fallback_design = {
    "TARGET":
        "166 age-censored/unresolved ASUs",

    "DONORS":
        "654 direct PALMSIM ASUs",

    "AGE_TREATMENT":
        (
            "DO_NOT fabricate numeric age. "
            "Unknown age is marginalized through donor distribution."
        ),

    "PRIMARY_MATCH":
        "Exact CLIMATE_PAIR_ID where sufficient donors exist",

    "SIMILARITY_FEATURES":
        (
            "Condition + soil texture; exact fields selected after "
            "this audit from highest-coverage existing ASU files."
        ),

    "ESTIMATE_OUTPUT":
        (
            "Indicative productivity range (recommended P10-P90) "
            "+ indicative median/center for display."
        ),

    "CONFIDENCE":
        (
            "LOW / LIMITED relative to direct PALMSIM, with explicit "
            "fallback method and peer-count metadata."
        ),

    "NO_MODEL_RERUN":
        True,

    "NO_FAKE_AGE":
        True,

    "NO_APSIM_INTERPOLATION":
        True,

    "NO_EQUAL_STATUS_WITH_DIRECT_PALMSIM":
        True,
}


# ------------------------------------------------------------
# 7. SAVE JSON
# ------------------------------------------------------------

audit = {
    "gate":
        "40E03A_FALLBACK_PRODUCTIVITY_FEATURE_AVAILABILITY_AUDIT",

    "status":
        status,

    "counts": {
        "master_asus": 820,
        "direct_donors": 654,
        "fallback_recipients": 166,
        "candidate_csv_files": len(candidate_rows),
        "condition_candidate_files": len(condition_candidates),
        "soil_candidate_files": len(soil_candidates),
        "age_evidence_candidate_files": len(age_candidates),
        "climate_candidate_files": len(climate_candidates),
    },

    "best_candidates": {
        "condition":
            condition_candidates[:5],

        "soil":
            soil_candidates[:5],

        "age_evidence":
            age_candidates[:5],

        "climate":
            climate_candidates[:5],
    },

    "feature_coverage_checks":
        feature_checks,

    "fallback_design":
        fallback_design,

    "checks": {
        "climate_source_available":
            has_climate,

        "condition_source_available":
            has_condition,

        "soil_source_available":
            has_soil,

        "design_ready":
            design_ready,
    },

    "next":
        (
            "40E03B peer-based indicative productivity range "
            "for 166 fallback ASUs."
        ),
}

with open(
    OUT_JSON,
    "w",
    encoding="utf-8"
) as f:
    json.dump(
        audit,
        f,
        indent=2
    )


# ------------------------------------------------------------
# 8. PRINT
# ------------------------------------------------------------

print("\n====================================================")
print("40E03A FINISHED")
print("====================================================")

print("Status                         :", status)
print("Candidate CSV files            :", len(candidate_rows))
print("Condition candidate files      :", len(condition_candidates))
print("Soil candidate files           :", len(soil_candidates))
print("Age-evidence candidate files   :", len(age_candidates))
print("Climate candidate files        :", len(climate_candidates))

print("\nTOP CONDITION CANDIDATES")
for r in condition_candidates[:5]:
    print(
        "-",
        r["FILE_NAME"],
        "| overlap=", r["OVERLAP_WITH_MASTER_820"],
        "| cols=", r["CONDITION_COLUMNS"]
    )

print("\nTOP SOIL CANDIDATES")
for r in soil_candidates[:5]:
    print(
        "-",
        r["FILE_NAME"],
        "| overlap=", r["OVERLAP_WITH_MASTER_820"],
        "| cols=", r["SOIL_COLUMNS"]
    )

print("\nTOP AGE-EVIDENCE CANDIDATES")
for r in age_candidates[:5]:
    print(
        "-",
        r["FILE_NAME"],
        "| overlap=", r["OVERLAP_WITH_MASTER_820"],
        "| cols=", r["AGE_EVIDENCE_COLUMNS"]
    )

print("\nFEATURE COVERAGE CHECKS")
for r in feature_checks:
    print(
        r["FILE_NAME"],
        "|",
        r["COLUMN"],
        "| direct",
        f'{r["DIRECT_VALID_N"]}/654',
        "| fallback",
        f'{r["FALLBACK_VALID_N"]}/166'
    )

print("\nDESIGN CHECK")
print("Climate source available       :", has_climate)
print("Condition source available     :", has_condition)
print("Soil source available          :", has_soil)
print("Ready for 40E03B               :", design_ready)

print("\nCandidate table :", OUT_CSV)
print("Audit JSON      :", OUT_JSON)

if status == "PASS_FEATURE_AUDIT_READY_FOR_40E03B":
    print(
        "Next            : 40E03B peer-based indicative "
        "productivity range for 166 ASUs."
    )
else:
    print(
        "Next            : Resolve feature-source ambiguity "
        "before estimating fallback productivity."
    )

print("====================================================")
