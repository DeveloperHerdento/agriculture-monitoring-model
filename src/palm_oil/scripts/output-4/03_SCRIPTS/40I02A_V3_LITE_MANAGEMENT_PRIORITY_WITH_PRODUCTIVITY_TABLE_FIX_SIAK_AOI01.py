# ============================================================
# OUTPUT 4 / 40I02A V3 LITE
# MANAGEMENT PRIORITY CLASS 0-4 VISUAL PREVIEW
# + CLASS DESCRIPTION TABLE
# + PRODUCTIVITY POTENTIAL
#
# FIX V3:
# - Does NOT scan/read all 40B CSVs.
# - Uses only lightweight 40B04A mapping CSV candidates for centroids.
# - Avoids huge geometry/WKT CSV fields that caused:
#   "field larger than field limit (131072)"
#
# MEMORY-SAFE: CSV ONLY
# NO GEOPANDAS / SHAPELY
# NO MODEL RERUN / NO CLASS RECALCULATION
#
# PRODUCTIVITY DISPLAY
# --------------------
# Class 0  : indicative range = min(low) to max(high)
# Class 1-4: one representative value = median center per class
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

OUTDIR = WORKDIR / "40I02A_LITE_VISUAL_PREVIEW_SIAK_AOI01_V3"

OUT_PNG = OUTDIR / (
    "40I02A_MANAGEMENT_PRIORITY_CLASS_0_4_WITH_PRODUCTIVITY_SIAK_AOI01_V3.png"
)

OUT_TABLE_CSV = OUTDIR / (
    "40I02A_CLASS_DESCRIPTION_WITH_PRODUCTIVITY_SIAK_AOI01_V3.csv"
)

OUT_QC = OUTDIR / (
    "40I02A_MANAGEMENT_PRIORITY_CLASS_0_4_PREVIEW_QC_SIAK_AOI01_V3.json"
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
print("40I02A V3 — MANAGEMENT PRIORITY VISUAL PREVIEW")
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
# 1. LOAD FROZEN OUTPUT
# ------------------------------------------------------------

for p in [FINAL, CLASS_SUMMARY]:
    if not p.exists():
        raise FileNotFoundError(p)

final_rows = read_csv(FINAL)
summary_rows = read_csv(CLASS_SUMMARY)

if len(final_rows) != EXPECTED:
    raise ValueError(
        f"Expected 820 final ASUs; got {len(final_rows)}."
    )

final_by_id = {
    str(r["UNIT_ID"]): r
    for r in final_rows
}

if len(final_by_id) != EXPECTED:
    raise ValueError(
        "Final UNIT_ID is not unique."
    )

print("Frozen ASUs                    :", len(final_rows))


# ------------------------------------------------------------
# 2. FIND ONLY LIGHTWEIGHT 40B04A CENTROID FILE
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

# 40B04A is the frozen ASU -> climate-cell mapping stage
# and is known to contain centroid coordinates.
candidate_paths = sorted(
    WORKDIR.glob("40B04A*.csv")
)

if not candidate_paths:
    raise FileNotFoundError(
        "No 40B04A*.csv file found in WORKDIR."
    )

selected_path = None
XCOL = None
YCOL = None
COORD_MODE = None

for path in candidate_paths:

    try:
        header = read_header(path)
    except Exception:
        continue

    cols = set(header)

    if "UNIT_ID" not in cols:
        continue

    found_pair = None

    for xcol, ycol, mode in coordinate_pairs:
        if xcol in cols and ycol in cols:
            found_pair = (
                xcol,
                ycol,
                mode
            )
            break

    if found_pair is None:
        continue

    # Count UNIT_ID using only the normal lightweight 40B04A table.
    rows = read_csv(path)

    ids = {
        str(r["UNIT_ID"])
        for r in rows
        if str(
            r.get(
                "UNIT_ID",
                ""
            )
        ).strip()
    }

    if ids == set(final_by_id):

        selected_path = path
        XCOL, YCOL, COORD_MODE = found_pair
        centroid_rows = rows
        break

if selected_path is None:
    print("\n40B04A candidates:")
    for p in candidate_paths:
        print("-", p.name)

    raise ValueError(
        "A 40B04A file exists, but none has 820 matching UNIT_IDs "
        "plus recognized centroid columns."
    )

print("Centroid source                :", selected_path.name)
print("Coordinate fields              :", XCOL, "/", YCOL)
print("Coordinate mode                :", COORD_MODE)


# ------------------------------------------------------------
# 3. BUILD SPATIAL PREVIEW TABLE
# ------------------------------------------------------------

plot_rows = []

for r in centroid_rows:

    uid = str(r["UNIT_ID"])

    x = as_float(
        r.get(XCOL)
    )

    y = as_float(
        r.get(YCOL)
    )

    if x is None or y is None:
        continue

    f = final_by_id[
        uid
    ]

    cls = int(
        float(
            f[
                "MANAGEMENT_PRIORITY_CLASS"
            ]
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
# 4. PRODUCTIVITY SUMMARY BY FINAL CLASS
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
            f"No productivity centers for Class {cls}."
        )

    center_median = statistics.median(
        centers
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
            x
            for x in lows
            if x is not None
        ]

        highs = [
            x
            for x in highs
            if x is not None
        ]

        if not lows or not highs:
            raise ValueError(
                "Class 0 indicative ranges are incomplete."
            )

        low = min(lows)
        high = max(highs)

        productivity_summary[cls] = {
            "DISPLAY":
                f"{low:.2f}–{high:.2f}",

            "DISPLAY_LONG":
                f"{low:.2f}–{high:.2f} t FFB/ha/yr",

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

        productivity_summary[cls] = {
            "DISPLAY":
                f"{center_median:.2f}",

            "DISPLAY_LONG":
                f"{center_median:.2f} t FFB/ha/yr",

            "TYPE":
                "MEDIAN_PRODUCTIVITY_CENTER",

            "LOW":
                None,

            "HIGH":
                None,

            "MEDIAN_CENTER":
                center_median,
        }


# ------------------------------------------------------------
# 5. CLASS SUMMARY TABLE
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

    r = summary_by_class[
        cls
    ]

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

    potential = productivity_summary[
        cls
    ]

    table_rows.append([
        str(cls),
        CLASS_LABEL[cls],
        f"{n}",
        f"{area:,.2f}",
        f"{pct:.2f}%",
        potential["DISPLAY"],
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

        "PRODUCTIVITY_POTENTIAL":
            potential["DISPLAY_LONG"],

        "PRODUCTIVITY_DISPLAY_TYPE":
            potential["TYPE"],

        "MEDIAN_PRODUCTIVITY_CENTER_T_FFB_HA_YR":
            potential["MEDIAN_CENTER"],

        "INDICATIVE_LOW_T_FFB_HA_YR":
            (
                potential["LOW"]
                if cls == 0
                else ""
            ),

        "INDICATIVE_HIGH_T_FFB_HA_YR":
            (
                potential["HIGH"]
                if cls == 0
                else ""
            ),
    })


# ------------------------------------------------------------
# 6. SAVE TABLE CSV
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
# 7. VISUALIZATION
# ------------------------------------------------------------

plt.close("all")

fig = plt.figure(
    figsize=(16, 9)
)

ax = fig.add_axes(
    [0.05, 0.10, 0.57, 0.80]
)

ax_table = fig.add_axes(
    [0.65, 0.15, 0.34, 0.68]
)

# No manually specified palette:
# use matplotlib default series colors.
for cls in range(5):

    sub = [
        r
        for r in plot_rows
        if r[
            "CLASS"
        ] == cls
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
        28
        if cls in (
            0,
            4
        )
        else 12
    )

    ax.scatter(
        xs,
        ys,
        s=size,
        marker="s",
        alpha=0.90,
        label=(
            f"Class {cls} — "
            f"{CLASS_LABEL[cls]}"
        )
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

ax.legend(
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
        "Potensi\nProduktivitas*",
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
    7.5
)

tbl.scale(
    1.0,
    1.95
)

ax_table.text(
    0.0,
    -0.05,
    (
        "* Satuan: t fresh FFB/ha/tahun.\n"
        "Class 0 = indicative range karena evidence terbatas.\n"
        "Class 1–4 = median productivity-potential center per kelas.\n"
        "Angka bukan actual yield lapangan.\n"
        "Class 4 = Replanting Evaluation Priority, bukan replant otomatis."
    ),
    transform=ax_table.transAxes,
    va="top",
    fontsize=8
)

fig.text(
    0.05,
    0.025,
    (
        "Frozen Output 4 | 820 ASUs | "
        "No model rerun / no class recalculation | "
        "Preview uses ASU centroids for memory-safe visualization."
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
        (
            productivity_summary[
                0
            ]["LOW"] is not None
            and
            productivity_summary[
                0
            ]["HIGH"] is not None
        ),

    "class1_to_4_median_values_available":
        all(
            productivity_summary[
                cls
            ]["MEDIAN_CENTER"] is not None
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
    "PASS_40I02A_V3_VISUAL_PREVIEW"
    if all(
        checks.values()
    )
    else "REVIEW"
)

qc = {
    "status":
        status,

    "centroid_source":
        selected_path.name,

    "coordinate_fields":
        [
            XCOL,
            YCOL
        ],

    "visualization_type":
        (
            "Memory-safe ASU centroid preview; "
            "exact clipped polygon rendering deferred to final web packaging."
        ),

    "class_counts":
        {
            str(k): v
            for k, v
            in class_counts.items()
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
print("40I02A V3 FINISHED")
print("====================================================")
print("Status                         :", status)
print("Preview PNG                    :", OUT_PNG)
print("Class table CSV                :", OUT_TABLE_CSV)
print("QC JSON                        :", OUT_QC)

print("\nCLASS TABLE")
for cls in range(5):

    r = summary_by_class[
        cls
    ]

    print(
        f"Class {cls} | "
        f"N={int(float(r['N_ASU']))} | "
        f"Area={float(r['AREA_HA']):.3f} ha | "
        f"Potential={productivity_summary[cls]['DISPLAY_LONG']}"
    )

print("\nNext                           : OPEN the PNG preview.")
print("====================================================")
