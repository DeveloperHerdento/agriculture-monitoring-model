# ============================================================
# OUTPUT 4 / 40I02 V2
# STATIC MAP PREVIEW + VISUAL / CARTOGRAPHIC QC
# MEMORY-SAFE VERSION
# SIAK_AOI01
#
# WHY V2
# ------
# V1 could exhaust RAM because geometry discovery recursively opened
# many vector files. V2 searches filenames first, then tests only a
# small targeted candidate list one-by-one and releases memory.
#
# NO MODEL RERUN
# NO CLASS RECALCULATION
# NO SCIENTIFIC RESULT CHANGE
# ============================================================

from pathlib import Path
import csv
import json
import math
import statistics
import textwrap
import gc

try:
    import geopandas as gpd
    import pandas as pd
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import matplotlib.lines as mlines
except Exception as e:
    raise RuntimeError(
        "40I02 V2 requires geopandas, pandas, matplotlib, and shapely."
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

OUTDIR = WORKDIR / "40I02_STATIC_VISUAL_QC_SIAK_AOI01_V2"

OUT_MAP_PRIORITY = OUTDIR / (
    "40I02A_MANAGEMENT_PRIORITY_CLASS_MAP_SIAK_AOI01_V2.png"
)

OUT_MAP_PRODUCTIVITY = OUTDIR / (
    "40I02B_PRODUCTIVITY_POTENTIAL_MAP_SIAK_AOI01_V2.png"
)

OUT_MAP_CONFIDENCE = OUTDIR / (
    "40I02C_CONFIDENCE_RULE_STABILITY_MAP_SIAK_AOI01_V2.png"
)

OUT_POPUP_MOCKUP = OUTDIR / (
    "40I02D_POPUP_MOCKUP_EXAMPLES_SIAK_AOI01_V2.png"
)

OUT_POPUP_CSV = OUTDIR / (
    "40I02_POPUP_SAMPLE_ASUS_SIAK_AOI01_V2.csv"
)

OUT_QC = OUTDIR / (
    "40I02_STATIC_VISUAL_CARTOGRAPHIC_QC_SIAK_AOI01_V2.json"
)

EXPECTED_ASU_COUNT = 820
EXPECTED_AREA_HA = 13867.099001884668
AREA_TOL_HA = 0.05
PROJECTED_CRS = "EPSG:32647"
DPI = 150

CLASS_LABELS = {
    0: "Insufficient Data / Limited Evidence",
    1: "Maintain",
    2: "Monitor",
    3: "Management Intervention Priority",
    4: "Replanting Evaluation Priority",
}

print("====================================================")
print("40I02 V2 — STATIC MAP PREVIEW + VISUAL QC")
print("MEMORY-SAFE GEOMETRY DISCOVERY")
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


def wrap(text, width=58):
    return "\n".join(
        textwrap.wrap(
            str(text),
            width=width,
            break_long_words=False,
            break_on_hyphens=False
        )
    )


def add_north_arrow(ax):
    ax.annotate(
        "N",
        xy=(0.95, 0.93),
        xytext=(0.95, 0.83),
        xycoords="axes fraction",
        ha="center",
        va="center",
        fontsize=10,
        fontweight="bold",
        arrowprops=dict(
            arrowstyle="-|>",
            linewidth=1.2
        )
    )


def nice_scale_length(width_m):
    target = width_m * 0.18

    if target <= 0:
        return 1000

    exponent = math.floor(
        math.log10(target)
    )

    base = 10 ** exponent
    fraction = target / base

    if fraction < 1.5:
        multiplier = 1
    elif fraction < 3.5:
        multiplier = 2
    elif fraction < 7.5:
        multiplier = 5
    else:
        multiplier = 10

    return multiplier * base


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
        linewidth=2.5,
        solid_capstyle="butt"
    )

    ax.plot(
        [x0, x0],
        [y0 - height * 0.007, y0 + height * 0.007],
        linewidth=1
    )

    ax.plot(
        [x0 + length_m, x0 + length_m],
        [y0 - height * 0.007, y0 + height * 0.007],
        linewidth=1
    )

    if length_m >= 1000:
        label = f"{length_m / 1000:g} km"
    else:
        label = f"{length_m:g} m"

    ax.text(
        x0 + length_m / 2,
        y0 + height * 0.014,
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
    gc.collect()


# ------------------------------------------------------------
# 1. CLEAN MATPLOTLIB STATE + PREFLIGHT
# ------------------------------------------------------------

plt.close("all")
gc.collect()

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
        "40I01 UNIT_ID is not unique."
    )

attr_df = pd.DataFrame(
    attrs
)

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
# 2. MEMORY-SAFE TARGETED GEOMETRY DISCOVERY
# ------------------------------------------------------------
#
# V2 NEVER recursively opens every vector.
# It first collects likely filenames, then opens one candidate at a time.
# ------------------------------------------------------------

vector_extensions = {
    ".gpkg",
    ".geojson",
    ".shp",
    ".fgb",
}

patterns = [
    "40B03A*.gpkg",
    "40B03A*.geojson",
    "40B03A*.shp",
    "40B03A*.fgb",

    "*FINAL_ASU_500M_EXACT*.gpkg",
    "*FINAL_ASU_500M_EXACT*.geojson",
    "*FINAL_ASU_500M_EXACT*.shp",
    "*FINAL_ASU_500M_EXACT*.fgb",

    "*ASU*500M*EXACT*.gpkg",
    "*ASU*500M*EXACT*.geojson",
    "*ASU*500M*EXACT*.shp",
    "*ASU*500M*EXACT*.fgb",

    "*ASU*500M*CLIP*.gpkg",
    "*ASU*500M*CLIP*.geojson",
    "*ASU*500M*CLIP*.shp",
    "*ASU*500M*CLIP*.fgb",

    "*ASU*.gpkg",
    "*ASU*.geojson",
    "*ASU*.shp",
    "*ASU*.fgb",
]

candidate_paths = []

# Search only WORKDIR first.
for pattern in patterns:
    candidate_paths.extend(
        WORKDIR.glob(pattern)
    )

# If nothing found, search only one directory level below.
if not candidate_paths:
    for child in WORKDIR.iterdir():

        if not child.is_dir():
            continue

        if child.name.startswith("40I02_"):
            continue

        for pattern in patterns:
            candidate_paths.extend(
                child.glob(pattern)
            )

# Dedupe while preserving order.
seen = set()
ordered_paths = []

for path in candidate_paths:

    try:
        rp = path.resolve()
    except Exception:
        rp = path

    if rp in seen:
        continue

    seen.add(
        rp
    )

    if path.suffix.lower() not in vector_extensions:
        continue

    ordered_paths.append(
        path
    )

if not ordered_paths:
    raise FileNotFoundError(
        "No likely ASU vector geometry found by targeted filename search. "
        "If your exact 820-ASU geometry uses a different filename, "
        "tell me the filename and I will lock the script directly to it."
    )

print("\nGeometry filename candidates   :", len(ordered_paths))

best = None
tested = []

for idx, path in enumerate(
    ordered_paths,
    start=1
):

    print(
        f"Testing geometry {idx}/{len(ordered_paths)} : {path.name}"
    )

    temp = None
    temp_proj = None

    try:
        temp = gpd.read_file(
            path
        )

        if "UNIT_ID" not in temp.columns:
            del temp
            gc.collect()
            continue

        if len(temp) != EXPECTED_ASU_COUNT:
            del temp
            gc.collect()
            continue

        temp["UNIT_ID"] = temp[
            "UNIT_ID"
        ].astype(str)

        ids = set(
            temp["UNIT_ID"]
        )

        if ids != attr_ids:
            del temp
            gc.collect()
            continue

        if temp.crs is None:
            del temp
            gc.collect()
            continue

        if (
            temp.geometry.isna().any()
            or temp.geometry.is_empty.any()
        ):
            del temp
            gc.collect()
            continue

        temp_proj = temp.to_crs(
            PROJECTED_CRS
        )

        area_ha = (
            float(
                temp_proj.geometry.area.sum()
            )
            / 10000.0
        )

        diff_ha = abs(
            area_ha
            - EXPECTED_AREA_HA
        )

        tested.append(
            (
                path.name,
                area_ha,
                diff_ha
            )
        )

        if (
            best is None
            or diff_ha < best[
                "diff_ha"
            ]
        ):
            best = {
                "path":
                    path,

                "diff_ha":
                    diff_ha,

                "area_ha":
                    area_ha,
            }

        # Exact enough: stop immediately.
        if diff_ha <= AREA_TOL_HA:
            break

    except Exception as e:
        print(
            "  skipped:",
            type(e).__name__,
            str(e)[:120]
        )

    finally:
        if temp_proj is not None:
            del temp_proj

        if temp is not None:
            del temp

        gc.collect()


if best is None:
    raise FileNotFoundError(
        "Candidate vector files were found, but none matched "
        "820 frozen UNIT_IDs."
    )

if best[
    "diff_ha"
] > AREA_TOL_HA:

    print("\nGeometry candidates that matched 820 UNIT_IDs:")

    for name, area_ha, diff_ha in tested:
        print(
            "-",
            name,
            "| area =",
            area_ha,
            "| diff =",
            diff_ha
        )

    raise ValueError(
        "No matching geometry preserved the frozen exact palm area. "
        "Do not continue with a full 500 m square grid."
    )


geom_source = best[
    "path"
]

print("\nGEOMETRY SELECTED")
print("Source                         :", geom_source.name)
print("Frozen-area difference         :", best["diff_ha"], "ha")

# Read only the selected geometry once for the actual visualization.
gdf = gpd.read_file(
    geom_source
)

gdf["UNIT_ID"] = gdf[
    "UNIT_ID"
].astype(str)

if gdf[
    "UNIT_ID"
].duplicated().any():
    raise ValueError(
        "Selected geometry contains duplicate UNIT_ID."
    )

gdf = gdf.to_crs(
    PROJECTED_CRS
)

print("Projected CRS                  :", gdf.crs)


# ------------------------------------------------------------
# 3. JOIN FROZEN ATTRIBUTES
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

del gdf
gc.collect()

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

print("Joined geometry area           :", joined_area_ha, "ha")
print("Invalid geometry after repair  :", invalid_after)


# ------------------------------------------------------------
# 4. MAP A — FINAL MANAGEMENT PRIORITY
# ------------------------------------------------------------

fig, ax = plt.subplots(
    figsize=(10, 9)
)

# Use matplotlib's default categorical cycle without forcing colors.
default_colors = plt.rcParams[
    "axes.prop_cycle"
].by_key()[
    "color"
]

class_color = {
    cls:
        default_colors[
            cls % len(
                default_colors
            )
        ]
    for cls in range(5)
}

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
        facecolor=class_color[cls],
        edgecolor="white",
        linewidth=0.08
    )

# Locator points for tiny Class 0 and Class 4.
for cls in [
    0,
    4,
]:

    sub = joined[
        joined[
            "MANAGEMENT_PRIORITY_CLASS"
        ] == cls
    ].copy()

    if len(sub) == 0:
        continue

    sub.geometry = sub.geometry.representative_point()

    sub.plot(
        ax=ax,
        marker="o",
        markersize=20,
        facecolor=class_color[cls],
        edgecolor="black",
        linewidth=0.5
    )

legend_handles = [
    mpatches.Patch(
        facecolor=class_color[cls],
        label=f"Class {cls} — {CLASS_LABELS[cls]}"
    )
    for cls in range(5)
]

ax.legend(
    handles=legend_handles,
    loc="upper left",
    frameon=True,
    fontsize=7.5,
    title="Management Priority"
)

ax.set_title(
    "Output 4 — Final Management Priority\n"
    "SIAK_AOI01 | Static Preview",
    fontsize=13,
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
        "All 820 palm ASUs rendered. Class 0 is an analytical class, not NoData. "
        "Class 4 = Replanting Evaluation Priority, not an automatic replanting order."
    )
)

save_figure(
    fig,
    OUT_MAP_PRIORITY
)

print("Map A saved                    :", OUT_MAP_PRIORITY.name)


# ------------------------------------------------------------
# 5. MAP B — PRODUCTIVITY POTENTIAL
# ------------------------------------------------------------

fig, ax = plt.subplots(
    figsize=(10, 9)
)

joined.plot(
    ax=ax,
    column="PRODUCTIVITY_CENTER_T_FFB_HA_YR",
    legend=True,
    edgecolor="white",
    linewidth=0.08,
    legend_kwds={
        "label":
            "Productivity potential center (t fresh FFB/ha/yr)"
    }
)

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
    linewidth=0.6
)

fallback_handle = mlines.Line2D(
    [],
    [],
    marker="x",
    linestyle="None",
    markersize=7,
    label="Indicative fallback pathway"
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
    "Output 4 — Productivity Potential\n"
    "654 Direct PALMSIM + 166 Indicative Fallback",
    fontsize=13,
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
        "Fallback ASUs marked ×. Their productivity values are indicative and "
        "must not be interpreted as equivalent-confidence direct PALMSIM outputs."
    )
)

save_figure(
    fig,
    OUT_MAP_PRODUCTIVITY
)

del fallback
gc.collect()

print("Map B saved                    :", OUT_MAP_PRODUCTIVITY.name)


# ------------------------------------------------------------
# 6. MAP C — CONFIDENCE + RULE STABILITY
# ------------------------------------------------------------

fig, ax = plt.subplots(
    figsize=(10, 9)
)

confidence_order = [
    "MODERATE",
    "LOW",
    "VERY_LOW",
]

confidence_color = {
    key:
        default_colors[
            idx % len(
                default_colors
            )
        ]
    for idx, key
    in enumerate(
        confidence_order
    )
}

for confidence in confidence_order:

    sub = joined[
        joined[
            "MANAGEMENT_PRIORITY_CONFIDENCE"
        ] == confidence
    ]

    if len(sub) == 0:
        continue

    sub.plot(
        ax=ax,
        facecolor=confidence_color[
            confidence
        ],
        edgecolor="white",
        linewidth=0.08
    )

rule_sensitive = joined[
    joined[
        "RULE_STABILITY"
    ] == "MODERATE_2_OF_3"
].copy()

if len(rule_sensitive) > 0:

    rule_sensitive.geometry = (
        rule_sensitive.geometry.representative_point()
    )

    rule_sensitive.plot(
        ax=ax,
        marker="^",
        markersize=14,
        facecolor="none",
        edgecolor="black",
        linewidth=0.5
    )

confidence_handles = [
    mpatches.Patch(
        facecolor=confidence_color[key],
        label=key.replace("_", " ").title()
    )
    for key in confidence_order
]

stability_handle = mlines.Line2D(
    [],
    [],
    marker="^",
    markerfacecolor="none",
    markeredgecolor="black",
    linestyle="None",
    markersize=7,
    label="Rule-sensitive: 2 of 3 rule sets"
)

ax.legend(
    handles=confidence_handles + [
        stability_handle
    ],
    loc="upper left",
    frameon=True,
    fontsize=7.5,
    title="Management Confidence"
)

ax.set_title(
    "Output 4 — Confidence & Rule Stability\n"
    "SIAK_AOI01",
    fontsize=13,
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
        "No HIGH confidence is permitted without local actual FFB/TBS validation. "
        "Triangle = final class changes under one alternative rule set."
    )
)

save_figure(
    fig,
    OUT_MAP_CONFIDENCE
)

del rule_sensitive
gc.collect()

print("Map C saved                    :", OUT_MAP_CONFIDENCE.name)


# ------------------------------------------------------------
# 7. PICK ONE POPUP EXAMPLE PER CLASS
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

    pool = (
        stable
        if len(stable) > 0
        else sub
    )

    med = float(
        pool[
            "PRODUCTIVITY_CENTER_T_FFB_HA_YR"
        ].median()
    )

    pool[
        "_d"
    ] = (
        pool[
            "PRODUCTIVITY_CENTER_T_FFB_HA_YR"
        ]
        - med
    ).abs()

    sample = pool.sort_values(
        "_d"
    ).iloc[0]

    popup_samples.append(
        sample
    )


# ------------------------------------------------------------
# 8. POPUP MOCKUP
# ------------------------------------------------------------

fig, axes = plt.subplots(
    nrows=5,
    ncols=1,
    figsize=(11, 15)
)

popup_csv_rows = []

for ax, sample in zip(
    axes,
    popup_samples
):

    cls = int(
        sample[
            "MANAGEMENT_PRIORITY_CLASS"
        ]
    )

    ax.axis(
        "off"
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

    if pd.isna(age):
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

    reasons = str(
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

    body = (
        f"ASU: {uid}\n"
        f"Class {cls}: {CLASS_LABELS[cls]}\n"
        f"Productivity: {productivity}\n"
        f"Estimate pathway: {pathway}\n"
        f"Age: {age_text}\n"
        f"Condition score: {condition_text}\n"
        f"Weather: {weather}\n"
        f"Confidence: {confidence} | Rule stability: {stability}\n"
        f"Reason codes: {reasons}\n"
        f"Recommendation: {action}"
    )

    ax.text(
        0.02,
        0.95,
        wrap(
            body,
            105
        ),
        va="top",
        ha="left",
        fontsize=9,
        linespacing=1.35,
        bbox=dict(
            boxstyle="round,pad=0.8",
            facecolor="white",
            edgecolor=class_color[cls],
            linewidth=2
        )
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
            reasons,

        "RECOMMENDATION":
            action,
    })


fig.suptitle(
    "Output 4 — Popup Mockup Examples\n"
    "One Representative ASU per Final Class",
    fontsize=14,
    fontweight="bold"
)

fig.tight_layout(
    rect=[
        0,
        0.01,
        1,
        0.97
    ]
)

save_figure(
    fig,
    OUT_POPUP_MOCKUP
)

print("Popup mockup saved             :", OUT_POPUP_MOCKUP.name)


# ------------------------------------------------------------
# 9. SAVE POPUP CSV
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
# 10. FINAL QC
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
    for key in confidence_order
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

checks = {
    "rows_820":
        len(joined) == 820,

    "unique_unit_id_820":
        joined[
            "UNIT_ID"
        ].nunique() == 820,

    "exact_area_preserved":
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

    "class0_present":
        class_counts[0] == 4,

    "class4_present":
        class_counts[4] == 3,

    "fallback_166_present":
        int(
            (
                joined[
                    "PRODUCTIVITY_PATHWAY"
                ]
                == "AGE_CENSORED_OR_UNRESOLVED_FALLBACK"
            ).sum()
        ) == 166,

    "priority_map_created":
        OUT_MAP_PRIORITY.exists(),

    "productivity_map_created":
        OUT_MAP_PRODUCTIVITY.exists(),

    "confidence_map_created":
        OUT_MAP_CONFIDENCE.exists(),

    "popup_mockup_created":
        OUT_POPUP_MOCKUP.exists(),

    "popup_samples_5":
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
        "40I02_V2_STATIC_MAP_PREVIEW_AND_VISUAL_QC",

    "status":
        status,

    "geometry_source":
        geom_source.name,

    "memory_safe_geometry_discovery":
        True,

    "asu_count":
        len(joined),

    "area_ha":
        joined_area_ha,

    "class_counts":
        {
            str(k): v
            for k, v
            in class_counts.items()
        },

    "confidence_counts":
        confidence_counts,

    "rule_stability_counts":
        stability_counts,

    "preview_outputs": {
        "priority_map":
            str(
                OUT_MAP_PRIORITY
            ),

        "productivity_map":
            str(
                OUT_MAP_PRODUCTIVITY
            ),

        "confidence_stability_map":
            str(
                OUT_MAP_CONFIDENCE
            ),

        "popup_mockup":
            str(
                OUT_POPUP_MOCKUP
            ),

        "popup_samples_csv":
            str(
                OUT_POPUP_CSV
            ),
    },

    "checks":
        checks,

    "next":
        (
            "Open the four PNG previews and visually review them. "
            "If accepted, proceed to 40J01 packaging."
        ),
}

write_json(
    OUT_QC,
    qc
)


# ------------------------------------------------------------
# 11. CLEANUP + PRINT
# ------------------------------------------------------------

del joined
del attr_df
gc.collect()

print("\n====================================================")
print("40I02 V2 FINISHED")
print("====================================================")
print("Status                         :", status)

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
        f"{key:42s}: {value}"
    )

if status == "PASS_STATIC_VISUAL_QC_READY_FOR_REVIEW":
    print(
        "\nNext                           : open the four PNG files "
        "and review visually before 40J01."
    )
else:
    print(
        "\nNext                           : review failed QC."
    )

print("====================================================")
