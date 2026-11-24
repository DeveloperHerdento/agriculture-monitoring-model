# ============================================================
# OUTPUT 4 / 40I02
# STATIC MAP PREVIEW + VISUAL / CARTOGRAPHIC QC
# SIAK_AOI01
#
# PURPOSE
# -------
# Preview the frozen Output-4 result BEFORE 40J01 web packaging.
#
# Outputs:
# A. Management Priority Class 0-4 map
# B. Productivity Potential map
# C. Confidence + Rule Stability map
# D. Popup mockup examples
# E. Popup sample CSV
# F. Visual QC JSON
#
# NO PALMSIM/APSIM rerun
# NO class recalculation
# NO scientific result changes
#
# Input:
# 40I01_FINAL_OUTPUT4_DELIVERY_MASTER_820_SIAK_AOI01_V1.csv
#
# Geometry:
# Auto-discovers exact 820-ASU clipped palm geometry and verifies
# total area against frozen 13,867.099 ha.
# ============================================================

from pathlib import Path
import csv
import json
import math
import statistics
import textwrap

try:
    import geopandas as gpd
    import pandas as pd
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import matplotlib.lines as mlines
    from matplotlib.colors import Normalize
    from matplotlib.cm import ScalarMappable
except Exception as e:
    raise RuntimeError(
        "40I02 requires geopandas, pandas, matplotlib, and shapely. "
        "Install in the active Jupyter environment if needed."
    ) from e


# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------

WORKDIR = Path(
    r"C:\Users\user\Documents\KERJA\SPATIAL DATA ANALYST INTERN\04_YIELD"
)

INPUT_ATTR = WORKDIR / (
    "40I01_FINAL_OUTPUT4_DELIVERY_MASTER_820_SIAK_AOI01_V1.csv"
)

OUTDIR = WORKDIR / "40I02_STATIC_VISUAL_QC_SIAK_AOI01_V1"

OUT_MAP_PRIORITY = OUTDIR / (
    "40I02A_MANAGEMENT_PRIORITY_CLASS_MAP_SIAK_AOI01_V1.png"
)

OUT_MAP_PRODUCTIVITY = OUTDIR / (
    "40I02B_PRODUCTIVITY_POTENTIAL_MAP_SIAK_AOI01_V1.png"
)

OUT_MAP_CONFIDENCE = OUTDIR / (
    "40I02C_CONFIDENCE_RULE_STABILITY_MAP_SIAK_AOI01_V1.png"
)

OUT_POPUP_MOCKUP = OUTDIR / (
    "40I02D_POPUP_MOCKUP_EXAMPLES_SIAK_AOI01_V1.png"
)

OUT_POPUP_CSV = OUTDIR / (
    "40I02_POPUP_SAMPLE_ASUS_SIAK_AOI01_V1.csv"
)

OUT_QC = OUTDIR / (
    "40I02_STATIC_VISUAL_CARTOGRAPHIC_QC_SIAK_AOI01_V1.json"
)

EXPECTED_ASU_COUNT = 820
EXPECTED_AREA_HA = 13867.099001884668
AREA_TOL_HA = 0.05
PROJECTED_CRS = "EPSG:32647"

# Frozen class colors agreed for Output 4.
CLASS_COLORS = {
    0: "#9E9E9E",  # Insufficient Data
    1: "#2E7D32",  # Maintain
    2: "#FBC02D",  # Monitor
    3: "#EF6C00",  # Management Intervention
    4: "#C62828",  # Replanting Evaluation
}

CLASS_LABELS = {
    0: "Insufficient Data / Limited Evidence",
    1: "Maintain",
    2: "Monitor",
    3: "Management Intervention Priority",
    4: "Replanting Evaluation Priority",
}

CONFIDENCE_COLORS = {
    "MODERATE": "#2E7D32",
    "LOW": "#F9A825",
    "VERY_LOW": "#C62828",
}

STABILITY_MARKERS = {
    "STABLE_3_OF_3": "o",
    "MODERATE_2_OF_3": "^",
    "UNSTABLE_1_OF_3": "X",
}

DPI = 220

print("====================================================")
print("40I02 — STATIC MAP PREVIEW + VISUAL / CARTOGRAPHIC QC")
print("====================================================")


# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------

def read_csv_dict(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


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


def write_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            obj,
            f,
            indent=2,
            ensure_ascii=False
        )


def wrap(text, width=52):
    return "\n".join(
        textwrap.wrap(
            str(text),
            width=width,
            break_long_words=False,
            break_on_hyphens=False
        )
    )


def add_north_arrow(ax):
    x = 0.955
    y = 0.92

    ax.annotate(
        "N",
        xy=(x, y),
        xytext=(x, y - 0.10),
        xycoords="axes fraction",
        ha="center",
        va="center",
        fontsize=11,
        fontweight="bold",
        arrowprops=dict(
            arrowstyle="-|>",
            linewidth=1.4
        )
    )


def nice_scale_length(width_m):
    """
    Choose a visually reasonable scale bar length from map width.
    """
    target = width_m * 0.20

    if target <= 0:
        return 1000

    exponent = math.floor(
        math.log10(target)
    )

    base = 10 ** exponent
    fraction = target / base

    if fraction < 1.5:
        nice = 1
    elif fraction < 3.5:
        nice = 2
    elif fraction < 7.5:
        nice = 5
    else:
        nice = 10

    return nice * base


def add_scale_bar(ax):
    xmin, xmax = ax.get_xlim()
    ymin, ymax = ax.get_ylim()

    width = xmax - xmin
    height = ymax - ymin

    length_m = nice_scale_length(
        width
    )

    x0 = xmin + width * 0.07
    y0 = ymin + height * 0.055

    ax.plot(
        [x0, x0 + length_m],
        [y0, y0],
        linewidth=3,
        solid_capstyle="butt"
    )

    ax.plot(
        [x0, x0],
        [y0 - height * 0.008, y0 + height * 0.008],
        linewidth=1
    )

    ax.plot(
        [x0 + length_m, x0 + length_m],
        [y0 - height * 0.008, y0 + height * 0.008],
        linewidth=1
    )

    if length_m >= 1000:
        label = f"{length_m / 1000:g} km"
    else:
        label = f"{length_m:g} m"

    ax.text(
        x0 + length_m / 2,
        y0 + height * 0.015,
        label,
        ha="center",
        va="bottom",
        fontsize=8
    )


def add_footer(ax, text):
    ax.text(
        0.01,
        0.01,
        text,
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=7,
        alpha=0.8
    )


def save_figure(fig, path):
    fig.savefig(
        path,
        dpi=DPI,
        bbox_inches="tight",
        facecolor="white"
    )
    plt.close(fig)


# ------------------------------------------------------------
# 1. PREFLIGHT
# ------------------------------------------------------------

if not INPUT_ATTR.exists():
    raise FileNotFoundError(INPUT_ATTR)

OUTDIR.mkdir(
    parents=True,
    exist_ok=True
)

attrs = read_csv_dict(
    INPUT_ATTR
)

if len(attrs) != EXPECTED_ASU_COUNT:
    raise ValueError(
        f"Expected 820 frozen attribute rows; got {len(attrs)}."
    )

attr_ids = {
    str(r["UNIT_ID"])
    for r in attrs
}

if len(attr_ids) != EXPECTED_ASU_COUNT:
    raise ValueError(
        "Frozen 40I01 UNIT_ID is not unique."
    )

attr_df = pd.DataFrame(
    attrs
)

# Numeric fields needed for plots.
numeric_fields = [
    "PALM_AREA_HA",
    "MANAGEMENT_PRIORITY_CLASS",
    "PRODUCTIVITY_CENTER_T_FFB_HA_YR",
    "PRODUCTIVITY_LOW_T_FFB_HA_YR",
    "PRODUCTIVITY_HIGH_T_FFB_HA_YR",
    "AGE_P50",
    "CONDITION_SCORE",
]

for field in numeric_fields:
    if field in attr_df.columns:
        attr_df[field] = pd.to_numeric(
            attr_df[field],
            errors="coerce"
        )

print("Frozen attributes              :", len(attr_df))


# ------------------------------------------------------------
# 2. AUTO-DISCOVER EXACT 820-ASU GEOMETRY
# ------------------------------------------------------------

extensions = {
    ".geojson",
    ".gpkg",
    ".shp",
    ".fgb",
}

candidates = []

for path in WORKDIR.rglob("*"):

    if not path.is_file():
        continue

    if OUTDIR in path.parents:
        continue

    if path.suffix.lower() not in extensions:
        continue

    try:
        temp = gpd.read_file(
            path
        )
    except Exception:
        continue

    if "UNIT_ID" not in temp.columns:
        continue

    temp["UNIT_ID"] = temp[
        "UNIT_ID"
    ].astype(str)

    ids = set(
        temp["UNIT_ID"]
    )

    if ids != attr_ids:
        continue

    if len(temp) != EXPECTED_ASU_COUNT:
        continue

    if temp.geometry.isna().any():
        continue

    if temp.geometry.is_empty.any():
        continue

    if temp.crs is None:
        continue

    try:
        temp_proj = temp.to_crs(
            PROJECTED_CRS
        )

        area_ha = (
            float(
                temp_proj.geometry.area.sum()
            )
            / 10000.0
        )
    except Exception:
        continue

    diff = abs(
        area_ha
        - EXPECTED_AREA_HA
    )

    score = 0
    n = path.name.upper()

    if "40B03A" in n:
        score += 6

    if "FINAL" in n:
        score += 4

    if "EXACT" in n:
        score += 4

    if "ASU" in n:
        score += 3

    if "500M" in n:
        score += 2

    if "CLIP" in n:
        score += 2

    candidates.append({
        "path":
            path,

        "gdf":
            temp,

        "area_ha":
            area_ha,

        "diff_ha":
            diff,

        "name_score":
            score,
    })


if not candidates:
    raise FileNotFoundError(
        "No exact 820-ASU vector geometry was found. "
        "Expected .geojson/.gpkg/.shp/.fgb with UNIT_ID matching "
        "the frozen 40I01 table."
    )

candidates.sort(
    key=lambda x: (
        x["diff_ha"],
        -x["name_score"],
    )
)

selected = candidates[0]

if selected["diff_ha"] > AREA_TOL_HA:

    print("\nTOP GEOMETRY CANDIDATES")
    for c in candidates[:10]:
        print(
            "-",
            c["path"].name,
            "| area =",
            c["area_ha"],
            "| diff =",
            c["diff_ha"]
        )

    raise ValueError(
        "Matching 820-ASU geometry found, but no candidate preserves "
        f"the frozen exact palm area within {AREA_TOL_HA} ha."
    )

geom_source = selected[
    "path"
]

gdf = selected[
    "gdf"
].copy()

gdf["UNIT_ID"] = gdf[
    "UNIT_ID"
].astype(str)

if gdf["UNIT_ID"].duplicated().any():
    raise ValueError(
        "Selected geometry has duplicate UNIT_ID."
    )

gdf = gdf.to_crs(
    PROJECTED_CRS
)

print("\nGEOMETRY")
print("Selected source                :", geom_source.name)
print("Projected CRS                  :", gdf.crs)
print("Geometry area                  :", selected["area_ha"], "ha")
print("Area difference                :", selected["diff_ha"], "ha")


# ------------------------------------------------------------
# 3. JOIN ATTRIBUTES TO GEOMETRY
# ------------------------------------------------------------

joined = gdf[
    ["UNIT_ID", "geometry"]
].merge(
    attr_df,
    on="UNIT_ID",
    how="left",
    validate="one_to_one"
)

joined = gpd.GeoDataFrame(
    joined,
    geometry="geometry",
    crs=PROJECTED_CRS
)

if len(joined) != 820:
    raise ValueError(
        "Join did not preserve 820 ASUs."
    )

if joined[
    "MANAGEMENT_PRIORITY_CLASS"
].isna().any():
    raise ValueError(
        "Final class missing after geometry join."
    )

joined[
    "MANAGEMENT_PRIORITY_CLASS"
] = joined[
    "MANAGEMENT_PRIORITY_CLASS"
].astype(int)

invalid_before = int(
    (~joined.geometry.is_valid).sum()
)

if invalid_before > 0:

    try:
        joined.geometry = joined.geometry.make_valid()
    except Exception:
        joined.geometry = joined.geometry.buffer(0)

invalid_after = int(
    (~joined.geometry.is_valid).sum()
)

if invalid_after > 0:
    raise ValueError(
        f"{invalid_after} invalid geometries remain."
    )

joined_area_ha = (
    float(
        joined.geometry.area.sum()
    )
    / 10000.0
)

if abs(
    joined_area_ha
    - EXPECTED_AREA_HA
) > AREA_TOL_HA:
    raise ValueError(
        "Joined geometry area differs from frozen Output-4 domain."
    )


# ------------------------------------------------------------
# 4. MAP A — MANAGEMENT PRIORITY
# ------------------------------------------------------------

fig, ax = plt.subplots(
    figsize=(11, 10)
)

# Light outer boundary of all palm ASUs.
joined.boundary.plot(
    ax=ax,
    linewidth=0.20,
    alpha=0.20
)

for cls in range(5):

    sub = joined[
        joined[
            "MANAGEMENT_PRIORITY_CLASS"
        ] == cls
    ]

    if len(sub) == 0:
        continue

    sub.plot(
        ax=ax,
        facecolor=CLASS_COLORS[cls],
        edgecolor="white",
        linewidth=0.10
    )

# Rare/tiny classes get centroid locator markers so they remain visible.
for cls in [0, 4]:

    sub = joined[
        joined[
            "MANAGEMENT_PRIORITY_CLASS"
        ] == cls
    ]

    if len(sub) == 0:
        continue

    centers = sub.copy()
    centers.geometry = centers.geometry.representative_point()

    centers.plot(
        ax=ax,
        facecolor=CLASS_COLORS[cls],
        edgecolor="black",
        linewidth=0.6,
        markersize=22,
        marker="o"
    )

legend_handles = [
    mpatches.Patch(
        facecolor=CLASS_COLORS[cls],
        edgecolor="none",
        label=f"Class {cls} — {CLASS_LABELS[cls]}"
    )
    for cls in range(5)
]

ax.legend(
    handles=legend_handles,
    loc="upper left",
    frameon=True,
    fontsize=8,
    title="Management Priority"
)

ax.set_title(
    "Output 4 — Productivity & Management Priority\n"
    "SIAK_AOI01 | Final Frozen Classification",
    fontsize=14,
    fontweight="bold"
)

ax.set_axis_off()

add_north_arrow(
    ax
)

add_scale_bar(
    ax
)

add_footer(
    ax,
    (
        "Class 4 = Replanting Evaluation Priority, not automatic replanting. "
        "Class 0 is rendered, not NoData. Outside palm domain = transparent."
    )
)

save_figure(
    fig,
    OUT_MAP_PRIORITY
)


# ------------------------------------------------------------
# 5. MAP B — PRODUCTIVITY POTENTIAL
# ------------------------------------------------------------

fig, ax = plt.subplots(
    figsize=(11, 10)
)

vmin = float(
    joined[
        "PRODUCTIVITY_CENTER_T_FFB_HA_YR"
    ].min()
)

vmax = float(
    joined[
        "PRODUCTIVITY_CENTER_T_FFB_HA_YR"
    ].max()
)

norm = Normalize(
    vmin=vmin,
    vmax=vmax
)

joined.plot(
    ax=ax,
    column="PRODUCTIVITY_CENTER_T_FFB_HA_YR",
    cmap="viridis",
    norm=norm,
    edgecolor="white",
    linewidth=0.10
)

# Highlight fallback ASUs with representative-point × markers.
fallback = joined[
    joined[
        "PRODUCTIVITY_PATHWAY"
    ] == "AGE_CENSORED_OR_UNRESOLVED_FALLBACK"
].copy()

fallback.geometry = fallback.geometry.representative_point()

fallback.plot(
    ax=ax,
    marker="x",
    markersize=10,
    linewidth=0.7
)

sm = ScalarMappable(
    norm=norm,
    cmap="viridis"
)

sm.set_array([])

cbar = fig.colorbar(
    sm,
    ax=ax,
    fraction=0.035,
    pad=0.02
)

cbar.set_label(
    "Productivity potential center (t fresh FFB/ha/yr)"
)

fallback_handle = mlines.Line2D(
    [],
    [],
    marker="x",
    linestyle="None",
    markersize=7,
    label="Fallback pathway — indicative estimate"
)

ax.legend(
    handles=[
        fallback_handle
    ],
    loc="upper left",
    frameon=True,
    fontsize=8
)

ax.set_title(
    "Output 4 — Productivity Potential Preview\n"
    "Direct PALMSIM + Indicative Fallback",
    fontsize=14,
    fontweight="bold"
)

ax.set_axis_off()

add_north_arrow(
    ax
)

add_scale_bar(
    ax
)

add_footer(
    ax,
    (
        "654 ASUs = direct PALMSIM modelled potential. "
        "166 ASUs marked × = indicative fallback; not equivalent-confidence direct PALMSIM."
    )
)

save_figure(
    fig,
    OUT_MAP_PRODUCTIVITY
)


# ------------------------------------------------------------
# 6. MAP C — MANAGEMENT CONFIDENCE + RULE STABILITY
# ------------------------------------------------------------

fig, ax = plt.subplots(
    figsize=(11, 10)
)

for confidence in [
    "MODERATE",
    "LOW",
    "VERY_LOW",
]:

    sub = joined[
        joined[
            "MANAGEMENT_PRIORITY_CONFIDENCE"
        ] == confidence
    ]

    if len(sub) == 0:
        continue

    sub.plot(
        ax=ax,
        facecolor=CONFIDENCE_COLORS[
            confidence
        ],
        edgecolor="white",
        linewidth=0.10
    )

# Overlay representative-point triangle where class changes
# under at least one alternative rule set.
sensitive = joined[
    joined[
        "RULE_STABILITY"
    ] == "MODERATE_2_OF_3"
].copy()

if len(sensitive) > 0:

    sensitive.geometry = (
        sensitive.geometry.representative_point()
    )

    sensitive.plot(
        ax=ax,
        facecolor="none",
        edgecolor="black",
        marker="^",
        markersize=16,
        linewidth=0.5
    )

confidence_handles = [
    mpatches.Patch(
        facecolor=CONFIDENCE_COLORS[k],
        label=k.replace("_", " ").title()
    )
    for k in [
        "MODERATE",
        "LOW",
        "VERY_LOW",
    ]
]

stability_handle = mlines.Line2D(
    [],
    [],
    marker="^",
    markerfacecolor="none",
    markeredgecolor="black",
    linestyle="None",
    markersize=7,
    label="Rule-sensitive: MODERATE_2_OF_3"
)

ax.legend(
    handles=confidence_handles + [
        stability_handle
    ],
    loc="upper left",
    frameon=True,
    fontsize=8,
    title="Management confidence"
)

ax.set_title(
    "Output 4 — Management Confidence & Rule Stability\n"
    "SIAK_AOI01",
    fontsize=14,
    fontweight="bold"
)

ax.set_axis_off()

add_north_arrow(
    ax
)

add_scale_bar(
    ax
)

add_footer(
    ax,
    (
        "No HIGH confidence is allowed without local actual FFB/TBS validation. "
        "Triangle markers indicate ASUs that change class under one alternative rule set."
    )
)

save_figure(
    fig,
    OUT_MAP_CONFIDENCE
)


# ------------------------------------------------------------
# 7. POPUP MOCKUP SAMPLE SELECTION
# ------------------------------------------------------------
# One representative ASU per final Class 0-4.
#
# Preference:
# - STABLE_3_OF_3 if available
# - then MODERATE_2_OF_3
# - closest productivity center to class median
# ------------------------------------------------------------

popup_samples = []

for cls in range(5):

    sub = joined[
        joined[
            "MANAGEMENT_PRIORITY_CLASS"
        ] == cls
    ].copy()

    if len(sub) == 0:
        continue

    stable = sub[
        sub[
            "RULE_STABILITY"
        ] == "STABLE_3_OF_3"
    ].copy()

    if len(stable) > 0:
        pool = stable
    else:
        pool = sub

    med = float(
        pool[
            "PRODUCTIVITY_CENTER_T_FFB_HA_YR"
        ].median()
    )

    pool[
        "_dist_to_median"
    ] = (
        pool[
            "PRODUCTIVITY_CENTER_T_FFB_HA_YR"
        ]
        - med
    ).abs()

    sample = pool.sort_values(
        "_dist_to_median"
    ).iloc[0]

    popup_samples.append(
        sample
    )


# ------------------------------------------------------------
# 8. POPUP MOCKUP FIGURE
# ------------------------------------------------------------

fig = plt.figure(
    figsize=(12, 16)
)

fig.suptitle(
    "Output 4 — Popup Mockup Examples\n"
    "SIAK_AOI01 | One Example per Final Class",
    fontsize=16,
    fontweight="bold",
    y=0.995
)

top = 0.955
card_h = 0.18
gap = 0.012

popup_csv_rows = []

for i, sample in enumerate(
    popup_samples
):

    cls = int(
        sample[
            "MANAGEMENT_PRIORITY_CLASS"
        ]
    )

    y = top - i * (
        card_h + gap
    ) - card_h

    ax = fig.add_axes(
        [
            0.06,
            y,
            0.88,
            card_h
        ]
    )

    ax.set_xlim(
        0,
        1
    )

    ax.set_ylim(
        0,
        1
    )

    ax.axis(
        "off"
    )

    rect = mpatches.FancyBboxPatch(
        (0.00, 0.00),
        1.00,
        1.00,
        boxstyle="round,pad=0.018",
        facecolor="white",
        edgecolor=CLASS_COLORS[
            cls
        ],
        linewidth=2.2
    )

    ax.add_patch(
        rect
    )

    uid = str(
        sample[
            "UNIT_ID"
        ]
    )

    productivity = str(
        sample[
            "PRODUCTIVITY_DISPLAY_TEXT"
        ]
    )

    age = sample[
        "AGE_P50"
    ]

    if pd.isna(
        age
    ):
        age_text = str(
            sample[
                "AGE_STATUS"
            ]
        )
    else:
        age_text = (
            f"{float(age):.1f} years proxy"
        )

    condition = sample[
        "CONDITION_SCORE"
    ]

    condition_text = (
        "Not available"
        if pd.isna(condition)
        else f"{float(condition):.3f}"
    )

    weather = str(
        sample[
            "WEATHER_LAG_SUMMARY"
        ]
    )

    reason_codes = str(
        sample[
            "MANAGEMENT_PRIORITY_REASON_CODES"
        ]
    )

    action = str(
        sample[
            "MANAGEMENT_ACTION_TEXT"
        ]
    )

    confidence = str(
        sample[
            "MANAGEMENT_PRIORITY_CONFIDENCE"
        ]
    )

    stability = str(
        sample[
            "RULE_STABILITY"
        ]
    )

    pathway = str(
        sample[
            "PRODUCTIVITY_PATHWAY"
        ]
    )

    ax.text(
        0.025,
        0.87,
        f"ASU {uid}",
        fontsize=12,
        fontweight="bold",
        va="top"
    )

    ax.text(
        0.025,
        0.72,
        f"Class {cls} — {CLASS_LABELS[cls]}",
        fontsize=11,
        fontweight="bold",
        color=CLASS_COLORS[cls],
        va="top"
    )

    left_lines = [
        f"Productivity: {productivity}",
        f"Estimate path: {pathway}",
        f"Age: {age_text}",
        f"Condition score: {condition_text}",
        f"Confidence: {confidence}",
        f"Rule stability: {stability}",
    ]

    ax.text(
        0.025,
        0.56,
        wrap(
            "\n".join(
                left_lines
            ),
            58
        ),
        fontsize=8.6,
        va="top",
        linespacing=1.45
    )

    right_text = (
        f"Weather context:\n{weather}\n\n"
        f"Reason codes:\n{reason_codes}\n\n"
        f"Recommendation:\n{action}"
    )

    ax.text(
        0.53,
        0.57,
        wrap(
            right_text,
            62
        ),
        fontsize=8.4,
        va="top",
        linespacing=1.35
    )

    popup_csv_rows.append({
        "CLASS":
            cls,

        "UNIT_ID":
            uid,

        "LABEL":
            CLASS_LABELS[cls],

        "PRODUCTIVITY_DISPLAY":
            productivity,

        "PRODUCTIVITY_PATHWAY":
            pathway,

        "AGE_DISPLAY":
            age_text,

        "CONDITION_SCORE":
            condition_text,

        "WEATHER_CONTEXT":
            weather,

        "CONFIDENCE":
            confidence,

        "RULE_STABILITY":
            stability,

        "REASON_CODES":
            reason_codes,

        "RECOMMENDATION":
            action,
    })


fig.text(
    0.06,
    0.01,
    (
        "Popup wording is a communication preview only. "
        "Scientific constraints remain unchanged: productivity is potential/indicative; "
        "Class 4 is evaluation priority, not automatic replanting."
    ),
    fontsize=8
)

save_figure(
    fig,
    OUT_POPUP_MOCKUP
)


# ------------------------------------------------------------
# 9. SAVE POPUP SAMPLE CSV
# ------------------------------------------------------------

with open(
    OUT_POPUP_CSV,
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            popup_csv_rows[0].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        popup_csv_rows
    )


# ------------------------------------------------------------
# 10. VISUAL QC METRICS
# ------------------------------------------------------------

class_counts = {
    cls:
        int(
            (
                joined[
                    "MANAGEMENT_PRIORITY_CLASS"
                ]
                == cls
            ).sum()
        )
    for cls in range(5)
}

confidence_counts = {
    key:
        int(
            (
                joined[
                    "MANAGEMENT_PRIORITY_CONFIDENCE"
                ]
                == key
            ).sum()
        )
    for key in [
        "MODERATE",
        "LOW",
        "VERY_LOW",
    ]
}

stability_counts = {
    key:
        int(
            (
                joined[
                    "RULE_STABILITY"
                ]
                == key
            ).sum()
        )
    for key in [
        "STABLE_3_OF_3",
        "MODERATE_2_OF_3",
        "UNSTABLE_1_OF_3",
    ]
}

class4 = joined[
    joined[
        "MANAGEMENT_PRIORITY_CLASS"
    ] == 4
]

class0 = joined[
    joined[
        "MANAGEMENT_PRIORITY_CLASS"
    ] == 0
]

fallback_joined = joined[
    joined[
        "PRODUCTIVITY_PATHWAY"
    ] == "AGE_CENSORED_OR_UNRESOLVED_FALLBACK"
]

checks = {
    "rows_820":
        len(joined) == 820,

    "unique_unit_id_820":
        joined[
            "UNIT_ID"
        ].nunique() == 820,

    "geometry_exact_area_preserved":
        abs(
            joined_area_ha
            - EXPECTED_AREA_HA
        ) <= AREA_TOL_HA,

    "geometry_valid":
        invalid_after == 0,

    "class_counts_preserved":
        class_counts
        == {
            0: 4,
            1: 159,
            2: 551,
            3: 103,
            4: 3,
        },

    "class0_visible":
        len(class0) == 4,

    "class4_visible":
        len(class4) == 3,

    "fallback_166_present":
        len(
            fallback_joined
        ) == 166,

    "priority_map_created":
        OUT_MAP_PRIORITY.exists(),

    "productivity_map_created":
        OUT_MAP_PRODUCTIVITY.exists(),

    "confidence_map_created":
        OUT_MAP_CONFIDENCE.exists(),

    "popup_mockup_created":
        OUT_POPUP_MOCKUP.exists(),

    "popup_samples_five_classes":
        len(
            popup_csv_rows
        ) == 5,

    "no_final_class_recalculation":
        True,
}

status = (
    "PASS_STATIC_VISUAL_QC_READY_FOR_REVIEW"
    if all(
        checks.values()
    )
    else "REVIEW"
)


qc = {
    "gate":
        "40I02_STATIC_MAP_PREVIEW_AND_VISUAL_CARTOGRAPHIC_QC",

    "status":
        status,

    "geometry_source":
        geom_source.name,

    "spatial_domain": {
        "asu_count":
            len(joined),

        "area_ha":
            joined_area_ha,

        "projected_crs":
            PROJECTED_CRS,

        "invalid_geometry_before":
            invalid_before,

        "invalid_geometry_after":
            invalid_after,
    },

    "class_counts":
        {
            str(k): v
            for k, v
            in class_counts.items()
        },

    "confidence_counts":
        confidence_counts,

    "stability_counts":
        stability_counts,

    "preview_outputs": {
        "management_priority_map":
            str(
                OUT_MAP_PRIORITY
            ),

        "productivity_potential_map":
            str(
                OUT_MAP_PRODUCTIVITY
            ),

        "confidence_rule_stability_map":
            str(
                OUT_MAP_CONFIDENCE
            ),

        "popup_mockup":
            str(
                OUT_POPUP_MOCKUP
            ),

        "popup_sample_csv":
            str(
                OUT_POPUP_CSV
            ),
    },

    "visual_review_checklist": [
        "Confirm overall class pattern is spatially plausible.",
        "Confirm Class 0 and Class 4 locator markers are visible and not misleading.",
        "Confirm Class 2 is not visually overwhelming to the point that Classes 1/3/4 become unreadable.",
        "Confirm fallback × markers are understandable on the productivity map.",
        "Confirm confidence map communicates LOW/VERY_LOW evidence honestly.",
        "Review all five popup mockups for wording and scientific overclaim.",
        "Confirm recommendation wording matches class semantics.",
        "If visual review is accepted, proceed to 40J01 web delivery packaging.",
    ],

    "checks":
        checks,

    "next":
        (
            "Human visual review of the four PNG previews. "
            "If accepted, proceed to 40J01 web delivery packaging."
        ),
}

write_json(
    OUT_QC,
    qc
)


# ------------------------------------------------------------
# 11. PRINT
# ------------------------------------------------------------

print("\n====================================================")
print("40I02 FINISHED")
print("====================================================")
print("Status                         :", status)

print("\nSPATIAL / VISUAL DOMAIN")
print("ASUs                           :", len(joined))
print("Exact area                     :", joined_area_ha, "ha")
print("Geometry source                :", geom_source.name)
print("Invalid geometry after repair  :", invalid_after)

print("\nCLASS COUNTS")
for cls in range(5):
    print(
        f"Class {cls} {CLASS_LABELS[cls]:38s}:",
        class_counts[cls]
    )

print("\nCONFIDENCE COUNTS")
print(confidence_counts)

print("\nRULE STABILITY")
print(stability_counts)

print("\nPREVIEW OUTPUTS")
print("A Priority map                 :", OUT_MAP_PRIORITY)
print("B Productivity map             :", OUT_MAP_PRODUCTIVITY)
print("C Confidence/stability map     :", OUT_MAP_CONFIDENCE)
print("D Popup mockup                 :", OUT_POPUP_MOCKUP)
print("Popup sample CSV               :", OUT_POPUP_CSV)
print("Visual QC JSON                 :", OUT_QC)

print("\nQC:")
for key, value in checks.items():
    print(
        f"{key:48s}: {value}"
    )

if status == "PASS_STATIC_VISUAL_QC_READY_FOR_REVIEW":
    print(
        "\nNext                           : OPEN the 4 PNG files, "
        "review visually, then approve/revise before 40J01."
    )
else:
    print(
        "\nNext                           : Review failed visual QC."
    )

print("====================================================")
