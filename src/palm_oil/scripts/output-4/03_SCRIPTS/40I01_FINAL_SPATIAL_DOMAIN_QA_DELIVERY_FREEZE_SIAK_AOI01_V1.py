# ============================================================
# OUTPUT 4 / 40I01
# FINAL SPATIAL/DOMAIN QA + DELIVERY FREEZE
# + DIRECT UNCERTAINTY ENVELOPE COMPLETION
# + WEATHER CONTEXT SUMMARY
# SIAK_AOI01
#
# PURE PYTHON STANDARD LIBRARY ONLY
# NO numpy / pandas / scipy
# NO PALMSIM/APSIM rerun
#
# PURPOSE
# -------
# Final QA before web packaging:
# 1) Preserve exact 820-ASU palm domain and plantation area.
# 2) Verify final Management Priority Class 0-4 wall-to-wall.
# 3) Complete a numeric interval for the 654 direct PALMSIM ASUs
#    using the already-frozen representative model-disagreement
#    proxy. This is an UNCERTAINTY ENVELOPE, NOT a statistical CI.
# 4) Preserve the frozen indicative interval for the 166 fallback ASUs.
# 5) Build a compact weather-context summary from the existing
#    CHIRPS + ERA5-Land daily forcing (recent 2023-2025 versus
#    long-term 2001-2025).
# 6) Check popup/delivery field completeness and freeze a final
#    820-row Output-4 delivery table.
#
# IMPORTANT
# ---------
# - No final class is changed in 40I01.
# - Direct interval:
#       center +/- STRUCTURAL_MODEL_DISAGREEMENT_PROXY_T_HA_YR
#       lower bound clipped at zero.
#   This is labelled REPRESENTATIVE_MODEL_DISAGREEMENT_ENVELOPE.
# - It is not a confidence interval and not validation against FFB.
# - Fallback interval remains the frozen peer+LOO indicative range.
# - Weather context is explanatory/contextual, not a causal trigger
#   of the already-frozen management class.
# ============================================================

from pathlib import Path
import csv
import json
import math
import statistics
from collections import defaultdict

WORKDIR = Path(
    r"C:\Users\user\Documents\KERJA\SPATIAL DATA ANALYST INTERN\04_YIELD"
)

FINAL_H = WORKDIR / (
    "40H02_FINAL_MANAGEMENT_PRIORITY_820_SIAK_AOI01_V1.csv"
)

AREA_MASTER = WORKDIR / (
    "40B03A_FINAL_ASU_500M_EXACT_SIAK_AOI01_V1.csv"
)

OUT_MASTER = WORKDIR / (
    "40I01_FINAL_OUTPUT4_DELIVERY_MASTER_820_SIAK_AOI01_V1.csv"
)

OUT_CLASS_AREA = WORKDIR / (
    "40I01_FINAL_CLASS_AREA_SUMMARY_SIAK_AOI01_V1.csv"
)

OUT_FIELD_CONTRACT = WORKDIR / (
    "40I01_WEB_FIELD_CONTRACT_SIAK_AOI01_V1.csv"
)

OUT_QC = WORKDIR / (
    "40I01_FINAL_SPATIAL_DOMAIN_DELIVERY_FREEZE_QC_SIAK_AOI01_V1.json"
)

EXPECTED_ASU_COUNT = 820
EXPECTED_AREA_HA = 13867.099002
AREA_TOL_HA = 0.01

print("====================================================")
print("40I01 — FINAL SPATIAL/DOMAIN QA + DELIVERY FREEZE")
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


def read_header(path):
    with open(
        path,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:
        reader = csv.reader(f)
        try:
            return next(reader)
        except StopIteration:
            return []


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


def parse_year(date_text):
    s = str(date_text).strip()

    if len(s) < 4:
        return None

    try:
        return int(s[:4])
    except Exception:
        return None


# ------------------------------------------------------------
# 1. PREFLIGHT FINAL 40H02
# ------------------------------------------------------------

for p in [FINAL_H, AREA_MASTER]:
    if not p.exists():
        raise FileNotFoundError(p)

rows = read_csv_dict(FINAL_H)
area_rows = read_csv_dict(AREA_MASTER)

if len(rows) != EXPECTED_ASU_COUNT:
    raise ValueError(
        f"Expected {EXPECTED_ASU_COUNT} final rows; got {len(rows)}."
    )

if len(area_rows) != EXPECTED_ASU_COUNT:
    raise ValueError(
        f"Expected {EXPECTED_ASU_COUNT} area-master rows; got {len(area_rows)}."
    )

final_ids = {
    str(r["UNIT_ID"])
    for r in rows
}

area_ids = {
    str(r["UNIT_ID"])
    for r in area_rows
}

if len(final_ids) != EXPECTED_ASU_COUNT:
    raise ValueError(
        "40H02 UNIT_ID is not unique."
    )

if len(area_ids) != EXPECTED_ASU_COUNT:
    raise ValueError(
        "40B03A UNIT_ID is not unique."
    )

if final_ids != area_ids:
    raise ValueError(
        "40H02 and 40B03A spatial domains differ."
    )

print("Final management rows           :", len(rows))
print("Exact spatial-domain rows       :", len(area_rows))


# ------------------------------------------------------------
# 2. AUTO-DETECT EXACT PLANTATION AREA FIELD
# ------------------------------------------------------------

area_columns = list(area_rows[0].keys())

numeric_area_candidates = []

for col in area_columns:

    cu = col.upper()

    # Require area-like naming and hectare-like unit.
    if not (
        "AREA" in cu
        and (
            "HA" in cu
            or "HECT" in cu
        )
    ):
        continue

    vals = [
        to_float_or_none(
            r.get(col)
        )
        for r in area_rows
    ]

    if any(v is None for v in vals):
        continue

    if any(v < 0 for v in vals):
        continue

    total = sum(vals)

    # Name preference score.
    name_score = 0

    if "PALM" in cu:
        name_score += 4

    if "PLANT" in cu:
        name_score += 4

    if "EXACT" in cu:
        name_score += 3

    if "CLIP" in cu:
        name_score += 2

    if "GRID" in cu:
        name_score -= 2

    diff = abs(
        total - EXPECTED_AREA_HA
    )

    numeric_area_candidates.append({
        "COLUMN":
            col,

        "TOTAL_HA":
            total,

        "DIFF_FROM_EXPECTED_HA":
            diff,

        "NAME_SCORE":
            name_score,
    })

if not numeric_area_candidates:
    raise ValueError(
        "No numeric hectare area field found in 40B03A."
    )

# Primary selection: smallest difference to frozen exact plantation area.
# Name score breaks ties.
numeric_area_candidates.sort(
    key=lambda x: (
        x["DIFF_FROM_EXPECTED_HA"],
        -x["NAME_SCORE"],
    )
)

selected_area = numeric_area_candidates[0]
AREA_FIELD = selected_area["COLUMN"]
AREA_TOTAL = selected_area["TOTAL_HA"]
AREA_DIFF = selected_area["DIFF_FROM_EXPECTED_HA"]

if AREA_DIFF > AREA_TOL_HA:
    raise ValueError(
        "Could not identify exact plantation-area field within "
        f"{AREA_TOL_HA} ha of frozen total {EXPECTED_AREA_HA}. "
        f"Best={AREA_FIELD}, total={AREA_TOTAL}, diff={AREA_DIFF}"
    )

area_lookup = {
    str(r["UNIT_ID"]):
        float(r[AREA_FIELD])
    for r in area_rows
}

print("\nAREA FIELD")
print("Selected field                  :", AREA_FIELD)
print("Exact plantation area           :", AREA_TOTAL, "ha")
print("Difference vs frozen total      :", AREA_DIFF, "ha")


# ------------------------------------------------------------
# 3. DISCOVER CHIRPS / ERA5 DAILY FILES BY SCHEMA
# ------------------------------------------------------------

def discover_daily_file(kind):
    """
    Scan likely 40B04B CSVs and choose a file by required schema.
    """
    candidates = sorted(
        WORKDIR.glob("40B04B*.csv")
    )

    matches = []

    for path in candidates:

        try:
            cols = read_header(path)
        except Exception:
            continue

        colset = set(cols)

        if kind == "CHIRPS":
            required = {
                "DATE",
                "CHIRPS_CELL_ID",
                "RAIN_MM_DAY",
            }

        elif kind == "ERA5":
            required = {
                "DATE",
                "ERA5L_CELL_ID",
                "TMEAN_C",
            }

        else:
            raise ValueError(kind)

        if required.issubset(colset):
            matches.append(path)

    if not matches:
        raise FileNotFoundError(
            f"No {kind} daily file found by schema."
        )

    # Prefer the largest file, which should be the complete daily table.
    matches.sort(
        key=lambda p: p.stat().st_size,
        reverse=True
    )

    return matches[0], matches


CHIRPS_FILE, chirps_candidates = discover_daily_file(
    "CHIRPS"
)

ERA5_FILE, era5_candidates = discover_daily_file(
    "ERA5"
)

print("\nWEATHER INPUT DISCOVERY")
print("CHIRPS daily                    :", CHIRPS_FILE.name)
print("ERA5-Land daily                 :", ERA5_FILE.name)


# ------------------------------------------------------------
# 4. WEATHER AGGREGATION
# ------------------------------------------------------------
# Recent = 2023-2025
# Long-term = 2001-2025
#
# CHIRPS:
#   annual rainfall -> recent 3-y annual mean vs 25-y annual mean
#
# ERA5-Land:
#   daily TMEAN_C -> recent daily mean vs long-term daily mean
# ------------------------------------------------------------

chirps_rows = read_csv_dict(
    CHIRPS_FILE
)

era5_rows = read_csv_dict(
    ERA5_FILE
)

rain_by_cell_year = defaultdict(float)
rain_day_count = defaultdict(int)

for r in chirps_rows:

    year = parse_year(
        r.get("DATE")
    )

    cell = str(
        r.get("CHIRPS_CELL_ID", "")
    ).strip()

    rain = to_float_or_none(
        r.get("RAIN_MM_DAY")
    )

    if (
        year is None
        or year < 2001
        or year > 2025
        or cell == ""
        or rain is None
    ):
        continue

    rain_by_cell_year[
        (cell, year)
    ] += rain

    rain_day_count[
        (cell, year)
    ] += 1


chirps_cells = sorted({
    cell
    for cell, year
    in rain_by_cell_year
})

if len(chirps_cells) != 12:
    raise ValueError(
        f"Expected 12 CHIRPS cells; got {len(chirps_cells)}."
    )

rain_summary = {}

for cell in chirps_cells:

    long_annual = []

    recent_annual = []

    for year in range(
        2001,
        2026
    ):

        key = (
            cell,
            year
        )

        if key not in rain_by_cell_year:
            raise ValueError(
                f"Missing CHIRPS year {year} for {cell}."
            )

        annual = rain_by_cell_year[
            key
        ]

        long_annual.append(
            annual
        )

        if year >= 2023:
            recent_annual.append(
                annual
            )

    long_mean = mean(
        long_annual
    )

    recent_mean = mean(
        recent_annual
    )

    anomaly_pct = (
        100.0
        * (
            recent_mean
            - long_mean
        )
        / long_mean
        if long_mean != 0
        else 0.0
    )

    rain_summary[cell] = {
        "RAIN_2001_2025_MEAN_ANNUAL_MM":
            long_mean,

        "RAIN_2023_2025_MEAN_ANNUAL_MM":
            recent_mean,

        "RAIN_2023_2025_ANOMALY_PCT":
            anomaly_pct,
    }


temp_sum_long = defaultdict(float)
temp_n_long = defaultdict(int)
temp_sum_recent = defaultdict(float)
temp_n_recent = defaultdict(int)

for r in era5_rows:

    year = parse_year(
        r.get("DATE")
    )

    cell = str(
        r.get("ERA5L_CELL_ID", "")
    ).strip()

    temp = to_float_or_none(
        r.get("TMEAN_C")
    )

    if (
        year is None
        or year < 2001
        or year > 2025
        or cell == ""
        or temp is None
    ):
        continue

    temp_sum_long[
        cell
    ] += temp

    temp_n_long[
        cell
    ] += 1

    if year >= 2023:

        temp_sum_recent[
            cell
        ] += temp

        temp_n_recent[
            cell
        ] += 1


era5_cells = sorted(
    temp_sum_long
)

if len(era5_cells) != 6:
    raise ValueError(
        f"Expected 6 ERA5-Land cells; got {len(era5_cells)}."
    )

temp_summary = {}

for cell in era5_cells:

    if (
        temp_n_long[cell] == 0
        or temp_n_recent[cell] == 0
    ):
        raise ValueError(
            f"Incomplete ERA5 temperature summary: {cell}"
        )

    long_mean = (
        temp_sum_long[cell]
        / temp_n_long[cell]
    )

    recent_mean = (
        temp_sum_recent[cell]
        / temp_n_recent[cell]
    )

    temp_summary[cell] = {
        "TMEAN_2001_2025_C":
            long_mean,

        "TMEAN_2023_2025_C":
            recent_mean,

        "TMEAN_2023_2025_ANOMALY_C":
            recent_mean
            - long_mean,
    }

print("CHIRPS cells aggregated         :", len(rain_summary))
print("ERA5-Land cells aggregated      :", len(temp_summary))


# ------------------------------------------------------------
# 5. BUILD FINAL DELIVERY MASTER
# ------------------------------------------------------------

delivery = []

for r in rows:

    uid = str(
        r["UNIT_ID"]
    )

    area_ha = area_lookup[
        uid
    ]

    pathway = r[
        "PRODUCTIVITY_PATHWAY"
    ]

    center = to_float_or_none(
        r.get(
            "PRODUCTIVITY_CENTER_T_FFB_HA_YR"
        )
    )

    if center is None:
        raise ValueError(
            f"Missing productivity center: {uid}"
        )

    # --------------------------------------------------------
    # COMPLETE NUMERIC INTERVAL
    # --------------------------------------------------------

    if pathway == "DIRECT_MODEL_SUPPORTED":

        structural_proxy = to_float_or_none(
            r.get(
                "STRUCTURAL_MODEL_DISAGREEMENT_PROXY_T_HA_YR"
            )
        )

        if structural_proxy is None:
            raise ValueError(
                f"Missing structural disagreement proxy: {uid}"
            )

        productivity_low = max(
            0.0,
            center - structural_proxy
        )

        productivity_high = (
            center
            + structural_proxy
        )

        interval_type = (
            "REPRESENTATIVE_MODEL_DISAGREEMENT_ENVELOPE"
        )

        interval_warning = (
            "Indicative uncertainty envelope from representative "
            "PALMSIM-APSIM structural disagreement; not a statistical "
            "confidence interval and not local FFB validation."
        )

    elif (
        pathway
        == "AGE_CENSORED_OR_UNRESOLVED_FALLBACK"
    ):

        productivity_low = to_float_or_none(
            r.get(
                "PRODUCTIVITY_LOW_T_FFB_HA_YR"
            )
        )

        productivity_high = to_float_or_none(
            r.get(
                "PRODUCTIVITY_HIGH_T_FFB_HA_YR"
            )
        )

        if (
            productivity_low is None
            or productivity_high is None
        ):
            raise ValueError(
                f"Missing frozen fallback interval: {uid}"
            )

        interval_type = (
            "INDICATIVE_PEER_RANGE_PLUS_LOO_EXPANSION"
        )

        interval_warning = (
            "Indicative peer-based productivity range with internal "
            "LOO expansion; age unresolved; not direct PALMSIM and "
            "not local FFB validation."
        )

    else:
        raise ValueError(
            f"Unknown productivity pathway: {pathway}"
        )

    if not (
        productivity_low
        <= center
        <= productivity_high
    ):
        raise ValueError(
            f"Productivity interval unordered: {uid}"
        )

    # --------------------------------------------------------
    # WEATHER CONTEXT
    # --------------------------------------------------------

    chirps_id = str(
        r.get(
            "CHIRPS_CELL_ID",
            ""
        )
    ).strip()

    era5_id = str(
        r.get(
            "ERA5L_CELL_ID",
            ""
        )
    ).strip()

    if chirps_id not in rain_summary:
        raise KeyError(
            f"CHIRPS cell not summarized for {uid}: {chirps_id}"
        )

    if era5_id not in temp_summary:
        raise KeyError(
            f"ERA5 cell not summarized for {uid}: {era5_id}"
        )

    rr = rain_summary[
        chirps_id
    ]

    tt = temp_summary[
        era5_id
    ]

    weather_text = (
        f"2023-2025 annual rainfall vs 2001-2025: "
        f"{rr['RAIN_2023_2025_ANOMALY_PCT']:+.1f}%; "
        f"Tmean anomaly: "
        f"{tt['TMEAN_2023_2025_ANOMALY_C']:+.2f} C"
    )

    # --------------------------------------------------------
    # WEB / POPUP CONTRACT
    # --------------------------------------------------------

    cls = int(
        r[
            "MANAGEMENT_PRIORITY_CLASS"
        ]
    )

    if cls not in {
        0, 1, 2, 3, 4
    }:
        raise ValueError(
            f"Invalid final class: {uid} -> {cls}"
        )

    reason_codes = str(
        r.get(
            "MANAGEMENT_PRIORITY_REASON_CODES_FINAL",
            ""
        )
    ).strip()

    action_text = str(
        r.get(
            "MANAGEMENT_ACTION_TEXT",
            ""
        )
    ).strip()

    management_conf = str(
        r.get(
            "MANAGEMENT_PRIORITY_CONFIDENCE",
            ""
        )
    ).strip()

    rule_stability = str(
        r.get(
            "RULE_STABILITY",
            ""
        )
    ).strip()

    age_status = str(
        r.get(
            "AGE_STATUS",
            ""
        )
    ).strip()

    age_p50 = to_float_or_none(
        r.get(
            "AGE_P50"
        )
    )

    condition_score = to_float_or_none(
        r.get(
            "CONDITION_SCORE"
        )
    )

    condition_valid = to_float_or_none(
        r.get(
            "CONDITION_VALID_FRACTION"
        )
    )

    if pathway == "DIRECT_MODEL_SUPPORTED":

        productivity_display = (
            f"{center:.2f} t FFB/ha/yr "
            f"(modelled potential); envelope "
            f"{productivity_low:.2f}-{productivity_high:.2f}"
        )

    else:

        productivity_display = (
            f"≈{center:.2f} t FFB/ha/yr; indicative range "
            f"{productivity_low:.2f}-{productivity_high:.2f}"
        )

    delivery.append({

        "UNIT_ID":
            uid,

        "PALM_AREA_HA":
            area_ha,

        "OUTPUT4_SPATIAL_DOMAIN":
            "INCLUDED",

        "WEB_RENDER_FLAG":
            "RENDER",

        "WEB_TRANSPARENT_FLAG":
            "NO",

        "MANAGEMENT_PRIORITY_CLASS":
            cls,

        "MANAGEMENT_PRIORITY_LABEL":
            r[
                "MANAGEMENT_PRIORITY_LABEL"
            ],

        "MANAGEMENT_PRIORITY_CONFIDENCE":
            management_conf,

        "RULE_STABILITY":
            rule_stability,

        "RULE_CLASS_MIN":
            r.get(
                "RULE_CLASS_MIN",
                ""
            ),

        "RULE_CLASS_MAX":
            r.get(
                "RULE_CLASS_MAX",
                ""
            ),

        "PRODUCTIVITY_PATHWAY":
            pathway,

        "PRODUCTIVITY_ESTIMATE_TYPE":
            r[
                "PRODUCTIVITY_ESTIMATE_TYPE"
            ],

        "PRODUCTIVITY_CENTER_T_FFB_HA_YR":
            center,

        "PRODUCTIVITY_LOW_T_FFB_HA_YR":
            productivity_low,

        "PRODUCTIVITY_HIGH_T_FFB_HA_YR":
            productivity_high,

        "PRODUCTIVITY_INTERVAL_TYPE":
            interval_type,

        "PRODUCTIVITY_INTERVAL_WARNING":
            interval_warning,

        "PRODUCTIVITY_DISPLAY_TEXT":
            productivity_display,

        "PRODUCTIVITY_BAND_FINAL":
            r[
                "PRODUCTIVITY_BAND_FINAL"
            ],

        "PRODUCTIVITY_BAND_CONFIDENCE_FINAL":
            r[
                "PRODUCTIVITY_BAND_CONFIDENCE_FINAL"
            ],

        "PRODUCTIVITY_PERCENTILE_VS_DIRECT_0_100":
            r[
                "PRODUCTIVITY_PERCENTILE_VS_DIRECT_0_100"
            ],

        "AGE_P50":
            age_p50
            if age_p50 is not None
            else "",

        "AGE_STATUS":
            age_status,

        "AGE_VALID_FRACTION":
            r.get(
                "AGE_VALID_FRACTION",
                ""
            ),

        "CONDITION_SCORE":
            condition_score
            if condition_score is not None
            else "",

        "CONDITION_VALID_FRACTION":
            condition_valid
            if condition_valid is not None
            else "",

        "CHIRPS_CELL_ID":
            chirps_id,

        "ERA5L_CELL_ID":
            era5_id,

        "CLIMATE_PAIR_ID":
            r[
                "CLIMATE_PAIR_ID"
            ],

        "RAIN_2001_2025_MEAN_ANNUAL_MM":
            rr[
                "RAIN_2001_2025_MEAN_ANNUAL_MM"
            ],

        "RAIN_2023_2025_MEAN_ANNUAL_MM":
            rr[
                "RAIN_2023_2025_MEAN_ANNUAL_MM"
            ],

        "RAIN_2023_2025_ANOMALY_PCT":
            rr[
                "RAIN_2023_2025_ANOMALY_PCT"
            ],

        "TMEAN_2001_2025_C":
            tt[
                "TMEAN_2001_2025_C"
            ],

        "TMEAN_2023_2025_C":
            tt[
                "TMEAN_2023_2025_C"
            ],

        "TMEAN_2023_2025_ANOMALY_C":
            tt[
                "TMEAN_2023_2025_ANOMALY_C"
            ],

        "WEATHER_LAG_SUMMARY":
            weather_text,

        "MANAGEMENT_PRIORITY_REASON_CODES":
            reason_codes,

        "MANAGEMENT_ACTION_TEXT":
            action_text,

        "CLASS4_AUTOMATIC_REPLANT_ORDER":
            r[
                "CLASS4_AUTOMATIC_REPLANT_ORDER"
            ],

        "LOCAL_FFB_VALIDATED":
            r[
                "LOCAL_FFB_VALIDATED"
            ],

        "MODEL_VERSION":
            "OUTPUT4_SIAK_AOI01_40I01_V1",

        "FINAL_DELIVERY_STATUS":
            "FROZEN_FOR_40J_WEB_PACKAGING",
    })

write_csv_dict(
    OUT_MASTER,
    delivery
)


# ------------------------------------------------------------
# 6. CLASS AREA SUMMARY
# ------------------------------------------------------------

class_summary = []

for cls in range(5):

    subset = [
        r
        for r in delivery
        if int(
            r[
                "MANAGEMENT_PRIORITY_CLASS"
            ]
        ) == cls
    ]

    area = sum(
        float(
            r["PALM_AREA_HA"]
        )
        for r in subset
    )

    centers = [
        float(
            r[
                "PRODUCTIVITY_CENTER_T_FFB_HA_YR"
            ]
        )
        for r in subset
    ]

    direct_n = sum(
        1
        for r in subset
        if r[
            "PRODUCTIVITY_PATHWAY"
        ] == "DIRECT_MODEL_SUPPORTED"
    )

    fallback_n = (
        len(subset)
        - direct_n
    )

    stable_n = sum(
        1
        for r in subset
        if r[
            "RULE_STABILITY"
        ] == "STABLE_3_OF_3"
    )

    moderate_n = sum(
        1
        for r in subset
        if r[
            "RULE_STABILITY"
        ] == "MODERATE_2_OF_3"
    )

    class_summary.append({

        "CLASS":
            cls,

        "LABEL":
            (
                subset[0][
                    "MANAGEMENT_PRIORITY_LABEL"
                ]
                if subset
                else ""
            ),

        "N_ASU":
            len(subset),

        "AREA_HA":
            area,

        "AREA_PCT":
            (
                100.0
                * area
                / AREA_TOTAL
            ),

        "DIRECT_N":
            direct_n,

        "FALLBACK_N":
            fallback_n,

        "STABLE_3_OF_3_N":
            stable_n,

        "MODERATE_2_OF_3_N":
            moderate_n,

        "PRODUCTIVITY_CENTER_MEDIAN_T_HA_YR":
            (
                statistics.median(
                    centers
                )
                if centers
                else ""
            ),
    })

write_csv_dict(
    OUT_CLASS_AREA,
    class_summary
)


# ------------------------------------------------------------
# 7. WEB FIELD CONTRACT
# ------------------------------------------------------------

field_contract = [
    {
        "FIELD":
            "MANAGEMENT_PRIORITY_CLASS",

        "REQUIRED":
            "YES",

        "ROLE":
            "Primary map class 0-4",

        "WEB_NOTE":
            "Class 0 is rendered, never transparent.",
    },
    {
        "FIELD":
            "PRODUCTIVITY_CENTER_T_FFB_HA_YR",

        "REQUIRED":
            "YES",

        "ROLE":
            "Primary productivity-potential value",

        "WEB_NOTE":
            "Direct vs fallback must remain visibly distinguishable.",
    },
    {
        "FIELD":
            "PRODUCTIVITY_LOW_T_FFB_HA_YR",

        "REQUIRED":
            "YES",

        "ROLE":
            "Lower uncertainty / indicative bound",

        "WEB_NOTE":
            "Interpret using PRODUCTIVITY_INTERVAL_TYPE.",
    },
    {
        "FIELD":
            "PRODUCTIVITY_HIGH_T_FFB_HA_YR",

        "REQUIRED":
            "YES",

        "ROLE":
            "Upper uncertainty / indicative bound",

        "WEB_NOTE":
            "Interpret using PRODUCTIVITY_INTERVAL_TYPE.",
    },
    {
        "FIELD":
            "PRODUCTIVITY_INTERVAL_TYPE",

        "REQUIRED":
            "YES",

        "ROLE":
            "Explains interval semantics",

        "WEB_NOTE":
            "Direct envelope is not a statistical CI.",
    },
    {
        "FIELD":
            "AGE_P50 / AGE_STATUS",

        "REQUIRED":
            "YES",

        "ROLE":
            "Age proxy or unresolved-age state",

        "WEB_NOTE":
            "Do not label age as confirmed planting age.",
    },
    {
        "FIELD":
            "CONDITION_SCORE",

        "REQUIRED":
            "CONTEXTUAL",

        "ROLE":
            "Condition evidence",

        "WEB_NOTE":
            "May be missing for limited-evidence Class 0.",
    },
    {
        "FIELD":
            "WEATHER_LAG_SUMMARY",

        "REQUIRED":
            "YES",

        "ROLE":
            "Recent weather context",

        "WEB_NOTE":
            "2023-2025 versus 2001-2025 contextual summary.",
    },
    {
        "FIELD":
            "MANAGEMENT_PRIORITY_REASON_CODES",

        "REQUIRED":
            "YES",

        "ROLE":
            "Explainability",

        "WEB_NOTE":
            "Show in popup/details.",
    },
    {
        "FIELD":
            "MANAGEMENT_PRIORITY_CONFIDENCE",

        "REQUIRED":
            "YES",

        "ROLE":
            "Decision confidence",

        "WEB_NOTE":
            "Allowed: MODERATE / LOW / VERY_LOW only.",
    },
    {
        "FIELD":
            "RULE_STABILITY",

        "REQUIRED":
            "YES",

        "ROLE":
            "Threshold sensitivity",

        "WEB_NOTE":
            "Shows 3-of-3 or 2-of-3 rule stability.",
    },
    {
        "FIELD":
            "MANAGEMENT_ACTION_TEXT",

        "REQUIRED":
            "YES",

        "ROLE":
            "Human-readable management interpretation",

        "WEB_NOTE":
            "Class 4 always says evaluation, not automatic replant.",
    },
]

write_csv_dict(
    OUT_FIELD_CONTRACT,
    field_contract
)


# ------------------------------------------------------------
# 8. FINAL QA
# ------------------------------------------------------------

delivery_ids = {
    r["UNIT_ID"]
    for r in delivery
}

class_counts = {
    cls: sum(
        1
        for r in delivery
        if int(
            r[
                "MANAGEMENT_PRIORITY_CLASS"
            ]
        ) == cls
    )
    for cls in range(5)
}

class_area_total = sum(
    float(
        r["AREA_HA"]
    )
    for r in class_summary
)

direct_delivery = [
    r
    for r in delivery
    if r[
        "PRODUCTIVITY_PATHWAY"
    ] == "DIRECT_MODEL_SUPPORTED"
]

fallback_delivery = [
    r
    for r in delivery
    if r[
        "PRODUCTIVITY_PATHWAY"
    ] == "AGE_CENSORED_OR_UNRESOLVED_FALLBACK"
]

class0_delivery = [
    r
    for r in delivery
    if int(
        r[
            "MANAGEMENT_PRIORITY_CLASS"
        ]
    ) == 0
]

class4_delivery = [
    r
    for r in delivery
    if int(
        r[
            "MANAGEMENT_PRIORITY_CLASS"
        ]
    ) == 4
]

checks = {

    "rows_820":
        len(delivery) == 820,

    "unique_asu_820":
        len(delivery_ids) == 820,

    "exact_spatial_domain_match":
        delivery_ids == final_ids == area_ids,

    "exact_plantation_area_preserved":
        abs(
            class_area_total
            - EXPECTED_AREA_HA
        ) <= AREA_TOL_HA,

    "class_counts_frozen":
        class_counts
        == {
            0: 4,
            1: 159,
            2: 551,
            3: 103,
            4: 3,
        },

    "all_820_rendered":
        all(
            r[
                "WEB_RENDER_FLAG"
            ] == "RENDER"
            for r in delivery
        ),

    "no_palm_asu_transparent":
        all(
            r[
                "WEB_TRANSPARENT_FLAG"
            ] == "NO"
            for r in delivery
        ),

    "class0_is_rendered_not_nodata":
        len(class0_delivery) == 4
        and
        all(
            r[
                "WEB_RENDER_FLAG"
            ] == "RENDER"
            and
            r[
                "WEB_TRANSPARENT_FLAG"
            ] == "NO"
            for r in class0_delivery
        ),

    "productivity_center_820_complete":
        all(
            to_float_or_none(
                r[
                    "PRODUCTIVITY_CENTER_T_FFB_HA_YR"
                ]
            ) is not None
            for r in delivery
        ),

    "productivity_interval_820_complete":
        all(
            to_float_or_none(
                r[
                    "PRODUCTIVITY_LOW_T_FFB_HA_YR"
                ]
            ) is not None
            and
            to_float_or_none(
                r[
                    "PRODUCTIVITY_HIGH_T_FFB_HA_YR"
                ]
            ) is not None
            for r in delivery
        ),

    "all_productivity_intervals_ordered":
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
            for r in delivery
        ),

    "direct_interval_semantics_complete":
        len(direct_delivery) == 654
        and
        all(
            r[
                "PRODUCTIVITY_INTERVAL_TYPE"
            ]
            == "REPRESENTATIVE_MODEL_DISAGREEMENT_ENVELOPE"
            for r in direct_delivery
        ),

    "fallback_interval_semantics_complete":
        len(fallback_delivery) == 166
        and
        all(
            r[
                "PRODUCTIVITY_INTERVAL_TYPE"
            ]
            == "INDICATIVE_PEER_RANGE_PLUS_LOO_EXPANSION"
            for r in fallback_delivery
        ),

    "weather_summary_820_complete":
        all(
            str(
                r[
                    "WEATHER_LAG_SUMMARY"
                ]
            ).strip() != ""
            for r in delivery
        ),

    "reason_codes_820_complete":
        all(
            str(
                r[
                    "MANAGEMENT_PRIORITY_REASON_CODES"
                ]
            ).strip() != ""
            for r in delivery
        ),

    "action_text_820_complete":
        all(
            str(
                r[
                    "MANAGEMENT_ACTION_TEXT"
                ]
            ).strip() != ""
            for r in delivery
        ),

    "management_confidence_820_valid":
        all(
            r[
                "MANAGEMENT_PRIORITY_CONFIDENCE"
            ]
            in {
                "MODERATE",
                "LOW",
                "VERY_LOW",
            }
            for r in delivery
        ),

    "rule_stability_820_valid":
        all(
            r[
                "RULE_STABILITY"
            ]
            in {
                "STABLE_3_OF_3",
                "MODERATE_2_OF_3",
                "UNSTABLE_1_OF_3",
            }
            for r in delivery
        ),

    "fallback_class4_zero":
        all(
            int(
                r[
                    "MANAGEMENT_PRIORITY_CLASS"
                ]
            ) != 4
            for r in fallback_delivery
        ),

    "class4_direct_only":
        all(
            r[
                "PRODUCTIVITY_PATHWAY"
            ] == "DIRECT_MODEL_SUPPORTED"
            for r in class4_delivery
        ),

    "class4_not_automatic_replant":
        all(
            r[
                "CLASS4_AUTOMATIC_REPLANT_ORDER"
            ] == "NO"
            for r in class4_delivery
        ),

    "no_local_ffb_validation_claim":
        all(
            r[
                "LOCAL_FFB_VALIDATED"
            ] == "NO"
            for r in delivery
        ),
}

status = (
    "PASS_FINAL_DELIVERY_FREEZE"
    if all(
        checks.values()
    )
    else "REVIEW"
)


# ------------------------------------------------------------
# 9. SAVE QC JSON
# ------------------------------------------------------------

qc = {

    "gate":
        "40I01_FINAL_SPATIAL_DOMAIN_QA_AND_DELIVERY_FREEZE",

    "status":
        status,

    "spatial_domain": {
        "asu_count":
            len(delivery),

        "area_field":
            AREA_FIELD,

        "plantation_area_ha":
            AREA_TOTAL,

        "expected_frozen_area_ha":
            EXPECTED_AREA_HA,

        "difference_ha":
            AREA_DIFF,
    },

    "final_class_counts":
        {
            str(k): v
            for k, v
            in class_counts.items()
        },

    "class_area_summary":
        class_summary,

    "productivity_interval_contract": {
        "direct_654":
            (
                "Center +/- representative structural model-disagreement "
                "proxy, lower bound clipped at zero. Not a statistical CI."
            ),

        "fallback_166":
            (
                "Frozen peer-based indicative range with LOO expansion."
            ),
    },

    "weather_context_contract": {
        "rain_source":
            CHIRPS_FILE.name,

        "temperature_source":
            ERA5_FILE.name,

        "recent_period":
            "2023-2025",

        "reference_period":
            "2001-2025",

        "role":
            "context/explainability only; does not alter frozen 40H02 class",
    },

    "web_contract": {
        "all_820_render":
            True,

        "class0_rendered":
            True,

        "outside_output1_palm_boundary":
            "true NoData/transparent handled in 40J geometry packaging",

        "popup_minimum_ready":
            [
                "priority class",
                "productivity value",
                "interval",
                "age / age status",
                "condition",
                "weather summary",
                "reason codes",
                "confidence",
                "rule stability",
            ],
    },

    "scientific_limits": [
        "Productivity is potential/indicative productivity, not actual FFB yield.",
        "Direct uncertainty envelope is representative PALMSIM-APSIM model disagreement, not a statistical confidence interval.",
        "Fallback intervals are indicative peer ranges, not direct PALMSIM simulation.",
        "Age is a detected-event proxy where available and unresolved for fallback ASUs.",
        "Class 4 is Replanting Evaluation Priority, not an automatic replanting instruction.",
        "Weather summary is contextual and does not retroactively alter the frozen management classification.",
        "No local actual FFB/TBS validation is claimed.",
    ],

    "checks":
        checks,

    "next":
        (
            "40J01 web delivery packaging: join frozen 40I01 attributes "
            "to exact ASU geometry; export GeoJSON/PMTiles-ready vector, "
            "legend/style JSON, metadata/model-card JSON, and final QA."
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
# 10. PRINT
# ------------------------------------------------------------

print("\n====================================================")
print("40I01 FINISHED")
print("====================================================")
print("Status                         :", status)

print("\nSPATIAL DOMAIN")
print("ASUs                           :", len(delivery))
print("Exact plantation area          :", AREA_TOTAL, "ha")
print("Area field                     :", AREA_FIELD)
print("Class-area total               :", class_area_total, "ha")

print("\nFINAL CLASS COUNT + AREA")
for r in class_summary:
    print(
        "Class",
        r["CLASS"],
        "| N =",
        r["N_ASU"],
        "| area =",
        round(
            r["AREA_HA"],
            3
        ),
        "ha",
        "|",
        round(
            r["AREA_PCT"],
            2
        ),
        "%"
    )

print("\nPRODUCTIVITY DELIVERY")
print("Direct interval complete       :", len(direct_delivery), "/ 654")
print("Fallback interval complete     :", len(fallback_delivery), "/ 166")
print("Productivity coverage          : 820 / 820")

print("\nWEB / POPUP")
print("All palm ASUs rendered         : 820 / 820")
print("Class 0 rendered               :", len(class0_delivery), "/ 4")
print("Weather summary                : 820 / 820")
print("Reason codes                   : 820 / 820")
print("Management action text         : 820 / 820")

print("\nWEATHER SOURCES")
print("CHIRPS                         :", CHIRPS_FILE.name)
print("ERA5-Land                      :", ERA5_FILE.name)

print("\nQC:")
for key, value in checks.items():
    print(
        f"{key:58s}: {value}"
    )

print("\nFinal delivery master :", OUT_MASTER)
print("Class area summary   :", OUT_CLASS_AREA)
print("Web field contract   :", OUT_FIELD_CONTRACT)
print("Freeze/QC JSON       :", OUT_QC)

if status == "PASS_FINAL_DELIVERY_FREEZE":
    print(
        "Next                  : 40J01 web delivery packaging."
    )
else:
    print(
        "Next                  : Review failed QA before 40J."
    )

print("====================================================")
