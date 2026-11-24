# ============================================================
# OUTPUT 4 / 40I02A V2 LITE
# MANAGEMENT PRIORITY CLASS 0-4 VISUAL PREVIEW
# + CLASS DESCRIPTION TABLE
# + PRODUCTIVITY POTENTIAL COLUMN
#
# MEMORY-SAFE: CSV ONLY, NO GEOPANDAS / SHAPELY
# NO MODEL RERUN, NO CLASS RECALCULATION
#
# PRODUCTIVITY DISPLAY RULE
# -------------------------
# Class 0:
#   Show indicative class envelope:
#   MIN(PRODUCTIVITY_LOW) to MAX(PRODUCTIVITY_HIGH)
#
# Class 1-4:
#   Show one representative numeric value:
#   MEDIAN(PRODUCTIVITY_CENTER) per class
#
# NOTE:
# This is a SPATIAL PATTERN PREVIEW using ASU centroids.
# It does NOT replace the final exact clipped-palm polygon map.
# ============================================================

from pathlib import Path
import csv
import math
import json
import statistics
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

WORKDIR = Path(
    r"C:\Users\user\Documents\KERJA\SPATIAL DATA ANALYST INTERN\04_YIELD"
)

FINAL = WORKDIR / (
    "40I01_FINAL_OUTPUT4_DELIVERY_MASTER_820_SIAK_AOI01_V1.csv"
)

CLASS_SUMMARY = WORKDIR / (
    "40I01_FINAL_CLASS_AREA_SUMMARY_SIAK_AOI01_V1.csv"
)

OUTDIR = WORKDIR / "40I02A_LITE_VISUAL_PREVIEW_SIAK_AOI01_V2"

OUT_PNG = OUTDIR / (
    "40I02A_MANAGEMENT_PRIORITY_CLASS_0_4_WITH_PRODUCTIVITY_SIAK_AOI01_V2.png"
)

OUT_TABLE_CSV = OUTDIR / (
    "40I02A_CLASS_DESCRIPTION_WITH_PRODUCTIVITY_SIAK_AOI01_V2.csv"
)

OUT_QC = OUTDIR / (
    "40I02A_MANAGEMENT_PRIORITY_CLASS_0_4_PREVIEW_QC_SIAK_AOI01_V2.json"
)

EXPECTED = 820

CLASS_LABEL = {
    0: "Insufficient Data / Limited Evidence",
    1: "Maintain",
    2: "Monitor",
    3: "Management Intervention Priority",
    4: "Replanting Evaluation Priority",
}

print("====================================================")
print("40I02A V2 — MANAGEMENT PRIORITY VISUAL PREVIEW")
print("+ PRODUCTIVITY POTENTIAL TABLE")
print("CSV ONLY / MEMORY SAFE")
print("====================================================")


# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------

def read_csv(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def read_header(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return next(csv.reader(f))


def as_float(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except Exception:
        return None


# ------------------------------------------------------------
# 1. LOAD FINAL FROZEN OUTPUT
# ------------------------------------------------------------

if not FINAL.exists():
    raise FileNotFoundError(FINAL)

if not CLASS_SUMMARY.exists():
    raise FileNotFoundError(CLASS_SUMMARY)

final_rows = read_csv(FINAL)
summary_rows = read_csv(CLASS_SUMMARY)

if len(final_rows) != EXPECTED:
    raise ValueError(
        f"Expected 820 final ASUs; got {len(final_rows)}"
    )

final_by_id = {
    str(r["UNIT_ID"]): r
    for r in final_rows
}

if len(final_by_id) != EXPECTED:
    raise ValueError(
        "UNIT_ID final is not unique."
    )

print("Frozen ASUs                    :", len(final_rows))


# ------------------------------------------------------------
# 2. FIND LIGHTWEIGHT CSV WITH ASU CENTROIDS
# ------------------------------------------------------------

coordinate_pairs = [
    ("CENTROID_X", "CENTROID_Y", "UTM"),
    ("CENTROID_EASTING", "CENTROID_NORTHING", "UTM"),
    ("ASU_CENTROID_X", "ASU_CENTROID_Y", "UTM"),
    ("CENTROID_LON", "CENTROID_LAT", "LONLAT"),
    ("CENTROID_LONGITUDE", "CENTROID_LATITUDE", "LONLAT"),
    ("LON", "LAT", "LONLAT"),
    ("LONGITUDE", "LATITUDE", "LONLAT"),
]

csv_candidates = []

for path in sorted(WORKDIR.glob("40B*.csv")):
    try:
        header = read_header(path)
    except Exception:
        continue

    cols = set(header)

    if "UNIT_ID" not in cols:
        continue

    for xcol, ycol, mode in coordinate_pairs:
        if xcol in cols and ycol in cols:
            csv_candidates.append(
                (path, xcol, ycol, mode)
            )
            break

if not csv_candidates:
    raise FileNotFoundError(
        "No lightweight 40B CSV containing UNIT_ID + centroid coordinates found."
    )

selected = None

for path, xcol, ycol, mode in csv_candidates:
    rows = read_csv(path)

    ids = {
        str(r["UNIT_ID"])
        for r in rows
        if str(r.get("UNIT_ID", "")).strip()
    }

    if ids == set(final_by_id):
        selected = (
            path,
            rows,
            xcol,
            ycol,
            mode
        )
        break

if selected is None:
    raise ValueError(
        "Centroid CSV candidates exist, but none exactly matches all 820 final UNIT_IDs."
    )

centroid_file, centroid_rows, XCOL, YCOL, COORD_MODE = selected

print("Centroid source                :", centroid_file.name)
print("Coordinate fields              :", XCOL, "/", YCOL)
print("Coordinate mode                :", COORD_MODE)


# ------------------------------------------------------------
# 3. BUILD PLOT TABLE
# ------------------------------------------------------------

plot_rows = []

for r in centroid_rows:
    uid = str(r["UNIT_ID"])

    x = as_float(r.get(XCOL))
    y = as_float(r.get(YCOL))

    if x is None or y is None:
        continue

    f = final_by_id[uid]

    cls = int(
        float(
            f["MANAGEMENT_PRIORITY_CLASS"]
        )
    )

    plot_rows.append({
        "UNIT_ID":
            uid,

        "X":
            x,

        "Y":
            y,

        "CLASS":
            cls,
    })

if len(plot_rows) != EXPECTED:
    raise ValueError(
        f"Expected 820 plottable centroids; got {len(plot_rows)}."
    )


# ------------------------------------------------------------
# 4. PRODUCTIVITY SUMMARY PER FINAL CLASS
# ------------------------------------------------------------

productivity_summary = {}

for cls in range(5):

    class_rows = [
        r
        for r in final_rows
        if int(
            float(
                r[
                    "MANAGEMENT_PRIORITY_CLASS"
                ]
            )
        ) == cls
    ]

    centers = [
        as_float(
            r.get(
                "PRODUCTIVITY_CENTER_T_FFB_HA_YR"
            )
        )
        for r in class_rows
    ]

    centers = [
        x
        for x in centers
        if x is not None
    ]

    if not centers:
        raise ValueError(
            f"No productivity center values for Class {cls}."
        )

    if cls == 0:

        lows = [
            as_float(
                r.get(
                    "PRODUCTIVITY_LOW_T_FFB_HA_YR"
                )
            )
            for r in class_rows
        ]

        highs = [
            as_float(
                r.get(
                    "PRODUCTIVITY_HIGH_T_FFB_HA_YR"
                )
            )
            for r in class_rows
        ]

        lows = [
            x for x in lows
            if x is not None
        ]

        highs = [
            x for x in highs
            if x is not None
        ]

        if not lows or not highs:
            raise ValueError(
                "Class 0 productivity range is incomplete."
            )

        low = min(lows)
        high = max(highs)
        center_median = statistics.median(
            centers
        )

        display = (
            f"{low:.2f}–{high:.2f} t FFB/ha/yr"
        )

        productivity_summary[cls] = {
            "DISPLAY":
                display,

            "TYPE":
                "INDICATIVE_RANGE",

            "LOW":
                low,

            "HIGH":
                high,

            "MEDIAN_CENTER":
                center_median,
        }

    else:

        center_median = statistics.median(
            centers
        )

        display = (
            f"{center_median:.2f} t FFB/ha/yr"
        )

        productivity_summary[cls] = {
            "DISPLAY":
                display,

            "TYPE":
                "MEDIAN_CENTER",

            "LOW":
                None,

            "HIGH":
                None,

            "MEDIAN_CENTER":
                center_median,
        }


# ------------------------------------------------------------
# 5. BUILD TABLE ROWS
# ------------------------------------------------------------

summary_by_class = {
    int(
        float(
            r["CLASS"]
        )
    ): r
    for r in summary_rows
}

table_rows = []
table_csv_rows = []

for cls in range(5):

    r = summary_by_class[cls]

    n = int(
        float(
            r["N_ASU"]
        )
    )

    area = float(
        r["AREA_HA"]
    )

    pct = float(
        r["AREA_PCT"]
    )

    productivity_display = (
        productivity_summary[
            cls
        ]["DISPLAY"]
    )

    table_rows.append([
        str(cls),
        CLASS_LABEL[cls],
        f"{n}",
        f"{area:,.3f}",
        f"{pct:.2f}%",
        productivity_display,
    ])

    table_csv_rows.append({
        "CLASS":
            cls,

        "INTERPRETATION":
            CLASS_LABEL[cls],

        "N_ASU":
            n,

        "AREA_HA":
            area,

        "AREA_PCT":
            pct,

        "PRODUCTIVITY_POTENTIAL_DISPLAY":
            productivity_display,

        "PRODUCTIVITY_DISPLAY_TYPE":
            productivity_summary[
                cls
            ]["TYPE"],

        "PRODUCTIVITY_MEDIAN_CENTER_T_FFB_HA_YR":
            productivity_summary[
                cls
            ]["MEDIAN_CENTER"],

        "CLASS0_INDICATIVE_LOW_T_FFB_HA_YR":
            (
                productivity_summary[
                    cls
                ]["LOW"]
                if cls == 0
                else ""
            ),

        "CLASS0_INDICATIVE_HIGH_T_FFB_HA_YR":
            (
                productivity_summary[
                    cls
                ]["HIGH"]
                if cls == 0
                else ""
            ),
    })


# ------------------------------------------------------------
# 6. SAVE CLASS TABLE CSV
# ------------------------------------------------------------

OUTDIR.mkdir(
    parents=True,
    exist_ok=True
)

with open(
    OUT_TABLE_CSV,
    "w",
    encoding="utf-8",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=list(
            table_csv_rows[0].keys()
        )
    )

    writer.writeheader()
    writer.writerows(
        table_csv_rows
    )


# ------------------------------------------------------------
# 7. SINGLE FIGURE: MAP + TABLE
# ------------------------------------------------------------

plt.close("all")

fig = plt.figure(
    figsize=(16, 9)
)

ax = fig.add_axes(
    [0.05, 0.10, 0.58, 0.80]
)

ax_table = fig.add_axes(
    [0.66, 0.14, 0.33, 0.70]
)

default_colors = plt.rcParams[
    "axes.prop_cycle"
].by_key()["color"]

class_colors = {
    cls:
        default_colors[
            cls % len(
                default_colors
            )
        ]
    for cls in range(5)
}

# Spatial preview by ASU centroid.
for cls in range(5):

    sub = [
        r
        for r in plot_rows
        if r["CLASS"] == cls
    ]

    xs = [
        r["X"]
        for r in sub
    ]

    ys = [
        r["Y"]
        for r in sub
    ]

    size = (
        24
        if cls in (
            0,
            4
        )
        else 11
    )

    ax.scatter(
        xs,
        ys,
        s=size,
        marker="s",
        label=f"Class {cls}",
        alpha=0.90
    )

ax.set_title(
    "Output 4 — Management Priority Class 0–4\n"
    "SIAK_AOI01 | Static Spatial Preview",
    fontsize=14,
    fontweight="bold"
)

if COORD_MODE == "UTM":
    ax.set_xlabel(
        "Easting"
    )

    ax.set_ylabel(
        "Northing"
    )

    ax.set_aspect(
        "equal",
        adjustable="box"
    )

else:
    ax.set_xlabel(
        "Longitude"
    )

    ax.set_ylabel(
        "Latitude"
    )

ax.grid(
    alpha=0.15
)

legend_handles = [
    Line2D(
        [0],
        [0],
        marker="s",
        linestyle="None",
        markersize=7,
        label=(
            f"Class {cls} — "
            f"{CLASS_LABEL[cls]}"
        )
    )
    for cls in range(5)
]

ax.legend(
    handles=legend_handles,
    loc="best",
    fontsize=8,
    frameon=True
)


# ------------------------------------------------------------
# TABLE PANEL
# ------------------------------------------------------------

ax_table.axis(
    "off"
)

ax_table.set_title(
    "Keterangan Kelas & Potensi Produktivitas",
    fontsize=12,
    fontweight="bold",
    pad=12
)

tbl = ax_table.table(
    cellText=table_rows,
    colLabels=[
        "Class",
        "Interpretasi",
        "ASU",
        "Luas (ha)",
        "Area",
        "Potensi Produktivitas",
    ],
    loc="center",
    cellLoc="left",
    colLoc="left",
    colWidths=[
        0.08,
        0.30,
        0.08,
        0.14,
        0.10,
        0.30,
    ]
)

tbl.auto_set_font_size(
    False
)

tbl.set_fontsize(
    7.6
)

tbl.scale(
    1.0,
    1.90
)

ax_table.text(
    0.0,
    -0.05,
    (
        "Keterangan produktivitas:\n"
        "• Class 0 = indicative productivity range dari seluruh ASU Class 0.\n"
        "• Class 1–4 = median productivity-potential center pada masing-masing kelas.\n"
        "• Satuan = ton fresh FFB/ha/tahun.\n"
        "• Angka adalah productivity potential, bukan actual yield lapangan.\n"
        "• Class 4 = prioritas evaluasi replanting, bukan perintah otomatis."
    ),
    transform=ax_table.transAxes,
    va="top",
    fontsize=8
)

fig.text(
    0.05,
    0.025,
    (
        "Frozen Output 4: 820 ASUs | "
        "Class counts = 4 / 159 / 551 / 103 / 3 | "
        "No model or class recalculation."
    ),
    fontsize=8
)

fig.savefig(
    OUT_PNG,
    dpi=170,
    bbox_inches="tight",
    facecolor="white"
)

plt.close(
    fig
)


# ------------------------------------------------------------
# 8. QC
# ------------------------------------------------------------

class_counts = {
    cls:
        sum(
            1
            for r in plot_rows
            if r[
                "CLASS"
            ] == cls
        )
    for cls in range(5)
}

checks = {
    "frozen_rows_820":
        len(
            final_rows
        ) == 820,

    "plotted_asus_820":
        len(
            plot_rows
        ) == 820,

    "class_counts_preserved":
        class_counts
        == {
            0: 4,
            1: 159,
            2: 551,
            3: 103,
            4: 3,
        },

    "class0_range_available":
        productivity_summary[
            0
        ]["LOW"] is not None
        and
        productivity_summary[
            0
        ]["HIGH"] is not None,

    "class1_4_median_productivity_available":
        all(
            productivity_summary[
                cls
            ][
                "MEDIAN_CENTER"
            ] is not None
            for cls in range(
                1,
                5
            )
        ),

    "preview_png_created":
        OUT_PNG.exists(),

    "class_table_csv_created":
        OUT_TABLE_CSV.exists(),
}

status = (
    "PASS_40I02A_V2_VISUAL_PREVIEW"
    if all(
        checks.values()
    )
    else "REVIEW"
)

qc = {
    "status":
        status,

    "visualization_type":
        (
            "ASU centroid spatial preview; "
            "not final polygon rendering"
        ),

    "centroid_source":
        centroid_file.name,

    "coordinate_fields":
        [
            XCOL,
            YCOL
        ],

    "class_counts":
        {
            str(k): v
            for k, v
            in class_counts.items()
        },

    "productivity_display_rule":
        {
            "class0":
                (
                    "min final indicative low to "
                    "max final indicative high"
                ),

            "class1_4":
                (
                    "median productivity center "
                    "within each final class"
                ),
        },

    "productivity_summary":
        {
            str(cls):
                productivity_summary[
                    cls
                ]
            for cls in range(
                5
            )
        },

    "output_png":
        str(
            OUT_PNG
        ),

    "class_table_csv":
        str(
            OUT_TABLE_CSV
        ),

    "checks":
        checks,

    "next":
        (
            "Open PNG and inspect the spatial "
            "pattern + productivity table."
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
print("40I02A V2 FINISHED")
print("====================================================")
print("Status                         :", status)
print("Preview PNG                    :", OUT_PNG)
print("Class table CSV                :", OUT_TABLE_CSV)
print("QC JSON                        :", OUT_QC)

print("\nCLASS TABLE")
for cls in range(5):
    print(
        f"Class {cls} | "
        f"{CLASS_LABEL[cls]} | "
        f"N={class_counts[cls]} | "
        f"Productivity={productivity_summary[cls]['DISPLAY']}"
    )

print("\nNext                           : OPEN the PNG preview.")
print("====================================================")
