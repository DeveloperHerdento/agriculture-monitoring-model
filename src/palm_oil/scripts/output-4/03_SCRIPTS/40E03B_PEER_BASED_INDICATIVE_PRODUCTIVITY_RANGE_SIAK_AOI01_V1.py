# ============================================================
# OUTPUT 4 / 40E03B
# PEER-BASED INDICATIVE PRODUCTIVITY RANGE
# + LEAVE-ONE-OUT INTERNAL RECONSTRUCTION DIAGNOSTIC
# SIAK_AOI01
#
# PURE PYTHON STANDARD LIBRARY ONLY
# NO numpy / pandas / scipy
# NO PALMSIM/APSIM rerun
#
# PURPOSE
# -------
# Estimate an indicative productivity range for the 166 ASUs that
# cannot receive direct PALMSIM output because numeric age is absent.
#
# Scientific safeguards:
# - No fabricated age.
# - No APSIM interpolation.
# - No PALMSIM/APSIM averaging.
# - Donors are the 654 direct-PALMSIM ASUs.
# - Climate is matched first.
# - Similarity uses condition + soil texture.
# - Sand + clay are used as the two soil-composition dimensions;
#   silt is retained as metadata but omitted from distance because
#   sand+silt+clay are compositional/redundant.
# - Output is P10/P50/P90 indicative range, NOT direct PALMSIM yield.
# - 2 fallback ASUs with missing CONDITION_SCORE use soil-only matching
#   and receive lower confidence.
#
# Internal reconstruction diagnostic:
# Each of the 654 direct ASUs is temporarily treated as if age were
# unavailable; its productivity is reconstructed from other donors.
# This evaluates the fallback METHOD against PALMSIM output only.
# It is NOT validation against actual FFB.
#
# Next:
# 40E03C = interpret diagnostic + freeze/adjust fallback method.
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

OUT_FALLBACK = WORKDIR / (
    "40E03B_FALLBACK_INDICATIVE_PRODUCTIVITY_166_SIAK_AOI01_V1.csv"
)

OUT_CV = WORKDIR / (
    "40E03B_FALLBACK_METHOD_LOO_RECONSTRUCTION_654_SIAK_AOI01_V1.csv"
)

OUT_CV_AGE = WORKDIR / (
    "40E03B_FALLBACK_METHOD_LOO_BY_AGE_GROUP_SIAK_AOI01_V1.csv"
)

OUT_PAIR = WORKDIR / (
    "40E03B_FALLBACK_DONOR_RECIPIENT_CLIMATE_PAIR_SUMMARY_SIAK_AOI01_V1.csv"
)

OUT_QC = WORKDIR / (
    "40E03B_FALLBACK_INDICATIVE_PRODUCTIVITY_QC_SIAK_AOI01_V1.json"
)

TARGET_K = 20
MIN_POOL = 12

print("====================================================")
print("40E03B — PEER-BASED INDICATIVE PRODUCTIVITY RANGE")
print("+ INTERNAL LEAVE-ONE-OUT RECONSTRUCTION")
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


def robust_scale(values):
    """
    IQR-first robust scale.
    If IQR=0, use range.
    If still zero, return 1 to avoid division by zero.
    """
    vals = [
        x for x in values
        if x is not None and math.isfinite(x)
    ]

    if len(vals) < 2:
        return 1.0

    q25 = quantile(vals, 0.25)
    q75 = quantile(vals, 0.75)

    scale = q75 - q25

    if scale is None or scale <= 0:
        scale = max(vals) - min(vals)

    if scale <= 0:
        scale = 1.0

    return scale


def average_ranks(values):
    n = len(values)

    order = sorted(
        range(n),
        key=lambda i: values[i]
    )

    ranks = [0.0] * n
    i = 0

    while i < n:
        j = i

        while (
            j + 1 < n
            and values[order[j + 1]]
            == values[order[i]]
        ):
            j += 1

        avg_rank = (
            (i + 1) + (j + 1)
        ) / 2.0

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


# ------------------------------------------------------------
# 1. PREFLIGHT + LOAD
# ------------------------------------------------------------

for p in [CONTRACT, COMMON, PALMSIM]:
    if not p.exists():
        raise FileNotFoundError(p)

contract_rows = read_csv_dict(CONTRACT)
common_rows = read_csv_dict(COMMON)
palm_rows = read_csv_dict(PALMSIM)

if len(contract_rows) != 820:
    raise ValueError(
        f"Expected 820 contract rows; got {len(contract_rows)}."
    )

if len(common_rows) != 820:
    raise ValueError(
        f"Expected 820 common-input rows; got {len(common_rows)}."
    )

if len(palm_rows) != 654:
    raise ValueError(
        f"Expected 654 PALMSIM rows; got {len(palm_rows)}."
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
    raise ValueError("Contract UNIT_ID not unique.")

if len(common) != 820:
    raise ValueError("Common-input UNIT_ID not unique.")

if set(contract) != set(common):
    raise ValueError(
        "Contract and common-input UNIT_ID sets differ."
    )

# PALMSIM canonical field
palm_columns = list(palm_rows[0].keys())

preferred = [
    "TRAILING_1Y_MEAN_T_HA_YR",
    "POTENTIAL_T_HA_YR",
    "BASELINE_T_HA_YR",
    "FFB_T_HA_YR",
]

yield_field = None

for c in preferred:
    if c in palm_columns:
        yield_field = c
        break

if yield_field is None:
    candidates = [
        c for c in palm_columns
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
            f"Could not identify PALMSIM yield field: {candidates}"
        )

    yield_field = candidates[0]

palm_yield = {}

for r in palm_rows:
    uid = str(r["UNIT_ID"])
    y = to_float_or_none(r.get(yield_field))

    if y is None:
        raise ValueError(
            f"Non-finite PALMSIM yield for {uid}"
        )

    palm_yield[uid] = y

if len(palm_yield) != 654:
    raise ValueError(
        "PALMSIM baseline UNIT_ID not unique."
    )

direct_ids = {
    uid
    for uid, r in contract.items()
    if r["OUTPUT4_ANALYTICAL_PATHWAY"]
    == "DIRECT_MODEL_SUPPORTED"
}

fallback_ids = {
    uid
    for uid, r in contract.items()
    if r["OUTPUT4_ANALYTICAL_PATHWAY"]
    == "AGE_CENSORED_OR_UNRESOLVED_FALLBACK"
}

if direct_ids != set(palm_yield):
    raise ValueError(
        "Direct-path IDs do not exactly match PALMSIM IDs."
    )

if len(fallback_ids) != 166:
    raise ValueError(
        f"Expected 166 fallback IDs; got {len(fallback_ids)}."
    )

print("Direct donors                  :", len(direct_ids))
print("Fallback recipients            :", len(fallback_ids))
print("PALMSIM yield field            :", yield_field)


# ------------------------------------------------------------
# 2. FEATURE EXTRACTION
# ------------------------------------------------------------

def feature_record(uid):
    c = common[uid]
    k = contract[uid]

    return {
        "UNIT_ID":
            uid,

        "CLIMATE_PAIR_ID":
            str(k.get("CLIMATE_PAIR_ID", "")).strip(),

        "CHIRPS_CELL_ID":
            str(k.get("CHIRPS_CELL_ID", "")).strip(),

        "ERA5L_CELL_ID":
            str(k.get("ERA5L_CELL_ID", "")).strip(),

        "AGE_P50":
            to_float_or_none(
                k.get("AGE_P50")
            ),

        "AGE_VALID_FRACTION":
            to_float_or_none(
                c.get("AGE_VALID_FRACTION")
            ),

        "CONDITION_SCORE":
            to_float_or_none(
                c.get("CONDITION_SCORE")
            ),

        "CONDITION_VALID_FRACTION":
            to_float_or_none(
                c.get("CONDITION_VALID_FRACTION")
            ),

        "SAND":
            to_float_or_none(
                c.get("SAND_0_100_PCT")
            ),

        "SILT":
            to_float_or_none(
                c.get("SILT_0_100_PCT")
            ),

        "CLAY":
            to_float_or_none(
                c.get("CLAY_0_100_PCT")
            ),
    }


features = {
    uid: feature_record(uid)
    for uid in contract
}

# Required donor features
for uid in direct_ids:
    f = features[uid]

    required = [
        f["CLIMATE_PAIR_ID"],
        f["SAND"],
        f["CLAY"],
        f["CONDITION_SCORE"],
    ]

    if (
        f["CLIMATE_PAIR_ID"] == ""
        or f["SAND"] is None
        or f["CLAY"] is None
        or f["CONDITION_SCORE"] is None
    ):
        raise ValueError(
            f"Direct donor missing required fallback feature: {uid}"
        )

# Required fallback soil+climate
for uid in fallback_ids:
    f = features[uid]

    if (
        f["CLIMATE_PAIR_ID"] == ""
        or f["SAND"] is None
        or f["CLAY"] is None
    ):
        raise ValueError(
            f"Fallback recipient missing climate/soil feature: {uid}"
        )


# ------------------------------------------------------------
# 3. DONOR POOL HIERARCHY
# ------------------------------------------------------------

donor_records = []

for uid in sorted(direct_ids):
    f = features[uid].copy()
    f["YIELD"] = palm_yield[uid]
    donor_records.append(f)


def choose_pool(target, exclude_uid=None):
    """
    Hierarchy:
    TIER_1: exact climate pair
    TIER_2: same ERA5-Land cell
    TIER_3: same CHIRPS cell
    TIER_4: all donors

    We keep the first pool with >= MIN_POOL candidates.
    """

    def allowed(d):
        return (
            exclude_uid is None
            or d["UNIT_ID"] != exclude_uid
        )

    tier1 = [
        d for d in donor_records
        if (
            allowed(d)
            and d["CLIMATE_PAIR_ID"]
            == target["CLIMATE_PAIR_ID"]
        )
    ]

    if len(tier1) >= MIN_POOL:
        return tier1, "TIER_1_EXACT_CLIMATE_PAIR"

    tier2 = [
        d for d in donor_records
        if (
            allowed(d)
            and d["ERA5L_CELL_ID"]
            == target["ERA5L_CELL_ID"]
        )
    ]

    if len(tier2) >= MIN_POOL:
        return tier2, "TIER_2_SAME_ERA5L_CELL"

    tier3 = [
        d for d in donor_records
        if (
            allowed(d)
            and d["CHIRPS_CELL_ID"]
            == target["CHIRPS_CELL_ID"]
        )
    ]

    if len(tier3) >= MIN_POOL:
        return tier3, "TIER_3_SAME_CHIRPS_CELL"

    tier4 = [
        d for d in donor_records
        if allowed(d)
    ]

    return tier4, "TIER_4_ALL_DONORS"


# ------------------------------------------------------------
# 4. PEER ESTIMATOR
# ------------------------------------------------------------

def estimate_from_peers(target, exclude_uid=None):
    pool, climate_tier = choose_pool(
        target,
        exclude_uid=exclude_uid
    )

    if len(pool) < 2:
        raise ValueError(
            f"Insufficient donor pool for {target['UNIT_ID']}"
        )

    condition_available = (
        target["CONDITION_SCORE"] is not None
    )

    # Robust scales are computed within the selected climate pool.
    sand_scale = robust_scale([
        d["SAND"]
        for d in pool
    ])

    clay_scale = robust_scale([
        d["CLAY"]
        for d in pool
    ])

    if condition_available:
        cond_scale = robust_scale([
            d["CONDITION_SCORE"]
            for d in pool
        ])
    else:
        cond_scale = None

    scored = []

    for d in pool:

        ds = (
            target["SAND"] - d["SAND"]
        ) / sand_scale

        dc = (
            target["CLAY"] - d["CLAY"]
        ) / clay_scale

        if condition_available:
            dq = (
                target["CONDITION_SCORE"]
                - d["CONDITION_SCORE"]
            ) / cond_scale

            # Group weighting:
            # 50% condition, 50% soil.
            # Soil half is split between sand and clay.
            dist = math.sqrt(
                0.50 * dq * dq
                + 0.25 * ds * ds
                + 0.25 * dc * dc
            )

            feature_mode = (
                "CONDITION_PLUS_SOIL"
            )

        else:
            # For 2 fallback recipients with missing condition:
            # soil-only distance.
            dist = math.sqrt(
                0.50 * ds * ds
                + 0.50 * dc * dc
            )

            feature_mode = (
                "SOIL_ONLY_CONDITION_MISSING"
            )

        scored.append(
            (dist, d)
        )

    scored.sort(
        key=lambda x: x[0]
    )

    k = min(
        TARGET_K,
        len(scored)
    )

    nearest = scored[:k]

    yields = [
        d["YIELD"]
        for _, d in nearest
    ]

    distances = [
        dist
        for dist, _ in nearest
    ]

    peer_ids = [
        d["UNIT_ID"]
        for _, d in nearest
    ]

    p10 = quantile(yields, 0.10)
    p50 = quantile(yields, 0.50)
    p90 = quantile(yields, 0.90)

    if p10 is None or p50 is None or p90 is None:
        raise ValueError(
            f"Could not estimate quantiles for {target['UNIT_ID']}"
        )

    # Confidence is intentionally capped below direct PALMSIM.
    if (
        climate_tier == "TIER_1_EXACT_CLIMATE_PAIR"
        and condition_available
        and k >= TARGET_K
    ):
        confidence = "LOW"
    else:
        confidence = "VERY_LOW"

    return {
        "CLIMATE_MATCH_TIER":
            climate_tier,

        "FEATURE_MODE":
            feature_mode,

        "DONOR_POOL_N":
            len(pool),

        "SELECTED_PEER_N":
            k,

        "PEER_DISTANCE_MEDIAN":
            statistics.median(
                distances
            ),

        "PEER_DISTANCE_MAX":
            max(distances),

        "INDICATIVE_P10_T_FFB_HA_YR":
            p10,

        "INDICATIVE_P50_T_FFB_HA_YR":
            p50,

        "INDICATIVE_P90_T_FFB_HA_YR":
            p90,

        "INDICATIVE_RANGE_WIDTH_T_HA_YR":
            p90 - p10,

        "PEER_YIELD_MIN_T_HA_YR":
            min(yields),

        "PEER_YIELD_MAX_T_HA_YR":
            max(yields),

        "PEER_IDS":
            ";".join(peer_ids),

        "FALLBACK_CONFIDENCE":
            confidence,
    }


# ------------------------------------------------------------
# 5. ESTIMATE 166 FALLBACK ASUs
# ------------------------------------------------------------

fallback_out = []

for uid in sorted(fallback_ids):

    target = features[uid]
    est = estimate_from_peers(
        target,
        exclude_uid=None
    )

    fallback_out.append({
        "UNIT_ID":
            uid,

        "CLIMATE_PAIR_ID":
            target["CLIMATE_PAIR_ID"],

        "CHIRPS_CELL_ID":
            target["CHIRPS_CELL_ID"],

        "ERA5L_CELL_ID":
            target["ERA5L_CELL_ID"],

        "AGE_P50":
            "",

        "AGE_STATUS":
            "NUMERIC_AGE_UNAVAILABLE",

        "AGE_VALID_FRACTION":
            target["AGE_VALID_FRACTION"],

        "CONDITION_SCORE":
            (
                target["CONDITION_SCORE"]
                if target["CONDITION_SCORE"] is not None
                else ""
            ),

        "CONDITION_VALID_FRACTION":
            target["CONDITION_VALID_FRACTION"],

        "SAND_0_100_PCT":
            target["SAND"],

        "SILT_0_100_PCT":
            target["SILT"],

        "CLAY_0_100_PCT":
            target["CLAY"],

        "PRODUCTIVITY_ESTIMATE_TYPE":
            "INDICATIVE_PEER_BASED_FALLBACK",

        "PRODUCTIVITY_NOT_DIRECT_PALMSIM":
            "YES",

        **est,

        "INTERPRETATION":
            (
                "Indicative productivity range derived from "
                "similar direct-PALMSIM ASUs; age is unknown "
                "and was not fabricated."
            ),

        "LOCAL_FFB_VALIDATED":
            "NO",

        "VERSION":
            "40E03B_V1",
    })

write_csv_dict(
    OUT_FALLBACK,
    fallback_out
)


# ------------------------------------------------------------
# 6. INTERNAL LEAVE-ONE-OUT RECONSTRUCTION FOR 654 DIRECT ASUs
# ------------------------------------------------------------

cv_rows = []

for uid in sorted(direct_ids):

    target = features[uid]

    est = estimate_from_peers(
        target,
        exclude_uid=uid
    )

    actual = palm_yield[uid]
    pred = est[
        "INDICATIVE_P50_T_FFB_HA_YR"
    ]

    p10 = est[
        "INDICATIVE_P10_T_FFB_HA_YR"
    ]

    p90 = est[
        "INDICATIVE_P90_T_FFB_HA_YR"
    ]

    error = pred - actual
    abs_error = abs(error)

    age = target["AGE_P50"]

    cv_rows.append({
        "UNIT_ID":
            uid,

        "AGE_P50":
            age,

        "AGE_GROUP":
            age_group(age),

        "CLIMATE_PAIR_ID":
            target["CLIMATE_PAIR_ID"],

        "PALMSIM_DIRECT_T_FFB_HA_YR":
            actual,

        "RECONSTRUCTED_P10_T_FFB_HA_YR":
            p10,

        "RECONSTRUCTED_P50_T_FFB_HA_YR":
            pred,

        "RECONSTRUCTED_P90_T_FFB_HA_YR":
            p90,

        "ERROR_P50_MINUS_DIRECT_T_HA_YR":
            error,

        "ABS_ERROR_T_HA_YR":
            abs_error,

        "DIRECT_WITHIN_P10_P90":
            (
                "YES"
                if p10 <= actual <= p90
                else "NO"
            ),

        "INTERVAL_WIDTH_T_HA_YR":
            p90 - p10,

        "CLIMATE_MATCH_TIER":
            est["CLIMATE_MATCH_TIER"],

        "SELECTED_PEER_N":
            est["SELECTED_PEER_N"],

        "PEER_DISTANCE_MEDIAN":
            est["PEER_DISTANCE_MEDIAN"],

        "DIAGNOSTIC_ONLY":
            "YES_NOT_ACTUAL_FFB_VALIDATION",
    })

write_csv_dict(
    OUT_CV,
    cv_rows
)


# ------------------------------------------------------------
# 7. GLOBAL INTERNAL RECONSTRUCTION DIAGNOSTICS
# ------------------------------------------------------------

actuals = [
    r["PALMSIM_DIRECT_T_FFB_HA_YR"]
    for r in cv_rows
]

preds = [
    r["RECONSTRUCTED_P50_T_FFB_HA_YR"]
    for r in cv_rows
]

errors = [
    r["ERROR_P50_MINUS_DIRECT_T_HA_YR"]
    for r in cv_rows
]

abs_errors = [
    r["ABS_ERROR_T_HA_YR"]
    for r in cv_rows
]

widths = [
    r["INTERVAL_WIDTH_T_HA_YR"]
    for r in cv_rows
]

coverage_n = sum(
    1
    for r in cv_rows
    if r["DIRECT_WITHIN_P10_P90"] == "YES"
)

cv_summary = {
    "N":
        len(cv_rows),

    "MAE_T_HA_YR":
        mean(abs_errors),

    "MEDIAN_ABS_ERROR_T_HA_YR":
        statistics.median(
            abs_errors
        ),

    "RMSE_T_HA_YR":
        math.sqrt(
            mean([
                e * e
                for e in errors
            ])
        ),

    "MEAN_BIAS_RECON_MINUS_DIRECT_T_HA_YR":
        mean(errors),

    "PEARSON_R":
        correlation(
            actuals,
            preds
        ),

    "SPEARMAN_RHO":
        spearman(
            actuals,
            preds
        ),

    "P10_P90_CONTAINMENT_PCT":
        100.0
        * coverage_n
        / len(cv_rows),

    "MEDIAN_INTERVAL_WIDTH_T_HA_YR":
        statistics.median(
            widths
        ),

    "P95_ABS_ERROR_T_HA_YR":
        quantile(
            abs_errors,
            0.95
        ),
}


# ------------------------------------------------------------
# 8. AGE-STRATIFIED INTERNAL RECONSTRUCTION DIAGNOSTICS
# ------------------------------------------------------------

age_groups = [
    "AGE_0_3",
    "AGE_4_7",
    "AGE_8_12",
    "AGE_13_18",
    "AGE_19_PLUS",
]

age_summary = []

for group in age_groups:

    subset = [
        r for r in cv_rows
        if r["AGE_GROUP"] == group
    ]

    if not subset:
        continue

    ae = [
        r["ABS_ERROR_T_HA_YR"]
        for r in subset
    ]

    er = [
        r["ERROR_P50_MINUS_DIRECT_T_HA_YR"]
        for r in subset
    ]

    aw = [
        r["INTERVAL_WIDTH_T_HA_YR"]
        for r in subset
    ]

    contained = sum(
        1
        for r in subset
        if r["DIRECT_WITHIN_P10_P90"] == "YES"
    )

    group_actual = [
        r["PALMSIM_DIRECT_T_FFB_HA_YR"]
        for r in subset
    ]

    group_pred = [
        r["RECONSTRUCTED_P50_T_FFB_HA_YR"]
        for r in subset
    ]

    age_summary.append({
        "AGE_GROUP":
            group,

        "N_ASU":
            len(subset),

        "MAE_T_HA_YR":
            mean(ae),

        "MEDIAN_ABS_ERROR_T_HA_YR":
            statistics.median(ae),

        "RMSE_T_HA_YR":
            math.sqrt(
                mean([
                    x * x
                    for x in er
                ])
            ),

        "MEAN_BIAS_RECON_MINUS_DIRECT_T_HA_YR":
            mean(er),

        "P10_P90_CONTAINMENT_PCT":
            100.0
            * contained
            / len(subset),

        "MEDIAN_INTERVAL_WIDTH_T_HA_YR":
            statistics.median(aw),

        "SPEARMAN_RHO":
            (
                spearman(
                    group_actual,
                    group_pred
                )
                if len(subset) >= 2
                else None
            ),
    })

write_csv_dict(
    OUT_CV_AGE,
    age_summary
)


# ------------------------------------------------------------
# 9. CLIMATE-PAIR DONOR / RECIPIENT SUMMARY
# ------------------------------------------------------------

pairs = sorted({
    features[uid]["CLIMATE_PAIR_ID"]
    for uid in contract
})

pair_summary = []

for pair in pairs:

    donor_n = sum(
        1
        for uid in direct_ids
        if features[uid]["CLIMATE_PAIR_ID"] == pair
    )

    fallback_n = sum(
        1
        for uid in fallback_ids
        if features[uid]["CLIMATE_PAIR_ID"] == pair
    )

    pair_summary.append({
        "CLIMATE_PAIR_ID":
            pair,

        "DIRECT_DONOR_N":
            donor_n,

        "FALLBACK_RECIPIENT_N":
            fallback_n,

        "EXACT_PAIR_MIN_POOL_OK":
            "YES"
            if donor_n >= MIN_POOL
            else "NO",
    })

write_csv_dict(
    OUT_PAIR,
    pair_summary
)


# ------------------------------------------------------------
# 10. FALLBACK OUTPUT DIAGNOSTICS
# ------------------------------------------------------------

fallback_p50 = [
    r["INDICATIVE_P50_T_FFB_HA_YR"]
    for r in fallback_out
]

fallback_widths = [
    r["INDICATIVE_RANGE_WIDTH_T_HA_YR"]
    for r in fallback_out
]

exact_pair_count = sum(
    1
    for r in fallback_out
    if r["CLIMATE_MATCH_TIER"]
    == "TIER_1_EXACT_CLIMATE_PAIR"
)

condition_plus_soil_count = sum(
    1
    for r in fallback_out
    if r["FEATURE_MODE"]
    == "CONDITION_PLUS_SOIL"
)

soil_only_count = sum(
    1
    for r in fallback_out
    if r["FEATURE_MODE"]
    == "SOIL_ONLY_CONDITION_MISSING"
)

low_conf_count = sum(
    1
    for r in fallback_out
    if r["FALLBACK_CONFIDENCE"] == "LOW"
)

very_low_conf_count = sum(
    1
    for r in fallback_out
    if r["FALLBACK_CONFIDENCE"] == "VERY_LOW"
)


# ------------------------------------------------------------
# 11. QC
# ------------------------------------------------------------

checks = {
    "direct_donors_654":
        len(direct_ids) == 654,

    "fallback_recipients_166":
        len(fallback_ids) == 166,

    "fallback_output_rows_166":
        len(fallback_out) == 166,

    "fallback_unique_asu_166":
        len({
            r["UNIT_ID"]
            for r in fallback_out
        }) == 166,

    "all_fallback_ranges_finite":
        all(
            math.isfinite(
                r["INDICATIVE_P10_T_FFB_HA_YR"]
            )
            and math.isfinite(
                r["INDICATIVE_P50_T_FFB_HA_YR"]
            )
            and math.isfinite(
                r["INDICATIVE_P90_T_FFB_HA_YR"]
            )
            for r in fallback_out
        ),

    "all_fallback_quantiles_ordered":
        all(
            r["INDICATIVE_P10_T_FFB_HA_YR"]
            <= r["INDICATIVE_P50_T_FFB_HA_YR"]
            <= r["INDICATIVE_P90_T_FFB_HA_YR"]
            for r in fallback_out
        ),

    "all_fallback_have_peers":
        all(
            r["SELECTED_PEER_N"] >= 2
            for r in fallback_out
        ),

    "loo_rows_654":
        len(cv_rows) == 654,

    "loo_unique_asu_654":
        len({
            r["UNIT_ID"]
            for r in cv_rows
        }) == 654,

    "climate_pairs_12":
        len(pair_summary) == 12,

    "no_fake_age_in_fallback":
        all(
            r["AGE_P50"] == ""
            for r in fallback_out
        ),

    "no_direct_palmsim_claim_for_fallback":
        all(
            r["PRODUCTIVITY_NOT_DIRECT_PALMSIM"]
            == "YES"
            for r in fallback_out
        ),
}

status = (
    "PASS_EXECUTION_DIAGNOSTIC_COMPLETE"
    if all(checks.values())
    else "REVIEW"
)


# ------------------------------------------------------------
# 12. SAVE QC
# ------------------------------------------------------------

qc = {
    "gate":
        "40E03B_PEER_BASED_INDICATIVE_PRODUCTIVITY_AND_INTERNAL_RECONSTRUCTION",

    "status":
        status,

    "method": {
        "donors":
            "654 direct-PALMSIM ASUs",

        "recipients":
            "166 age-unresolved ASUs",

        "target_k":
            TARGET_K,

        "minimum_climate_pool":
            MIN_POOL,

        "climate_hierarchy": [
            "exact CLIMATE_PAIR_ID",
            "same ERA5L cell if needed",
            "same CHIRPS cell if needed",
            "all donors if needed",
        ],

        "distance_when_condition_available":
            (
                "sqrt(0.50*condition^2 + "
                "0.25*sand^2 + 0.25*clay^2) "
                "after within-pool robust scaling"
            ),

        "distance_when_condition_missing":
            (
                "sqrt(0.50*sand^2 + 0.50*clay^2) "
                "after within-pool robust scaling"
            ),

        "productivity_output":
            "unweighted P10/P50/P90 of nearest donor PALMSIM potentials",

        "age_in_estimator":
            "NOT_USED__NOT_FABRICATED",

        "silt_in_distance":
            (
                "NOT_USED because sand+silt+clay are compositional; "
                "silt retained as metadata"
            ),
    },

    "fallback_summary": {
        "rows":
            len(fallback_out),

        "exact_climate_pair_count":
            exact_pair_count,

        "condition_plus_soil_count":
            condition_plus_soil_count,

        "soil_only_count":
            soil_only_count,

        "low_confidence_count":
            low_conf_count,

        "very_low_confidence_count":
            very_low_conf_count,

        "indicative_p50_min_t_ha_yr":
            min(fallback_p50),

        "indicative_p50_median_t_ha_yr":
            statistics.median(
                fallback_p50
            ),

        "indicative_p50_max_t_ha_yr":
            max(fallback_p50),

        "median_range_width_t_ha_yr":
            statistics.median(
                fallback_widths
            ),

        "p95_range_width_t_ha_yr":
            quantile(
                fallback_widths,
                0.95
            ),
    },

    "internal_reconstruction_diagnostic":
        cv_summary,

    "internal_reconstruction_by_age":
        age_summary,

    "interpretation_limits": [
        "Fallback estimates are indicative peer-based ranges, not direct PALMSIM simulations.",
        "Unknown numeric age is deliberately not fabricated.",
        "The leave-one-out diagnostic evaluates reconstruction of PALMSIM outputs, not accuracy against actual FFB.",
        "Poor reconstruction performance would indicate that climate+condition+soil cannot replace age information and should trigger a wider/more conservative fallback in 40E03C.",
        "Neither fallback P50 nor its range may be described as field-validated yield.",
        "Fallback confidence is capped below direct PALMSIM confidence.",
    ],

    "checks":
        checks,

    "next":
        "40E03C interpret reconstruction diagnostic and freeze/adjust fallback method.",
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
# 13. PRINT
# ------------------------------------------------------------

print("\n====================================================")
print("40E03B FINISHED")
print("====================================================")
print("Status                         :", status)

print("\nFALLBACK 166")
print("Rows                           :", len(fallback_out))
print("Exact climate-pair match       :", exact_pair_count)
print("Condition + soil               :", condition_plus_soil_count)
print("Soil only                      :", soil_only_count)
print("LOW confidence                 :", low_conf_count)
print("VERY_LOW confidence            :", very_low_conf_count)
print(
    "Indicative P50 min/median/max  :",
    min(fallback_p50),
    "/",
    statistics.median(fallback_p50),
    "/",
    max(fallback_p50)
)
print(
    "Median P10-P90 width           :",
    statistics.median(fallback_widths),
    "t FFB/ha/yr"
)

print("\nINTERNAL LOO RECONSTRUCTION — 654")
print("MAE                            :", cv_summary["MAE_T_HA_YR"])
print(
    "Median absolute error          :",
    cv_summary["MEDIAN_ABS_ERROR_T_HA_YR"]
)
print("RMSE                           :", cv_summary["RMSE_T_HA_YR"])
print(
    "Mean bias recon-direct         :",
    cv_summary["MEAN_BIAS_RECON_MINUS_DIRECT_T_HA_YR"]
)
print("Pearson r                      :", cv_summary["PEARSON_R"])
print("Spearman rho                   :", cv_summary["SPEARMAN_RHO"])
print(
    "Direct within P10-P90          :",
    cv_summary["P10_P90_CONTAINMENT_PCT"],
    "%"
)
print(
    "Median interval width          :",
    cv_summary["MEDIAN_INTERVAL_WIDTH_T_HA_YR"]
)
print(
    "P95 absolute error             :",
    cv_summary["P95_ABS_ERROR_T_HA_YR"]
)

print("\nLOO BY AGE GROUP")
for r in age_summary:
    print(
        r["AGE_GROUP"],
        "| N =", r["N_ASU"],
        "| MAE =", round(r["MAE_T_HA_YR"], 3),
        "| containment =", round(
            r["P10_P90_CONTAINMENT_PCT"],
            2
        ),
        "%",
        "| rho =",
        (
            round(r["SPEARMAN_RHO"], 3)
            if r["SPEARMAN_RHO"] is not None
            else None
        )
    )

print("\nQC:")
for key, value in checks.items():
    print(f"{key:48s}: {value}")

print("\nFallback output :", OUT_FALLBACK)
print("LOO diagnostic  :", OUT_CV)
print("LOO by age      :", OUT_CV_AGE)
print("Pair summary    :", OUT_PAIR)
print("QC JSON         :", OUT_QC)

if status == "PASS_EXECUTION_DIAGNOSTIC_COMPLETE":
    print(
        "Next            : 40E03C interpret diagnostic "
        "and freeze/adjust fallback method."
    )
else:
    print(
        "Next            : Review technical QC before 40E03C."
    )

print("====================================================")
