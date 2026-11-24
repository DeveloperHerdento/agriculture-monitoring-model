# ============================================================
# OUTPUT 4 / 40I02A V4 LITE
# MANAGEMENT PRIORITY CLASS 0-4 VISUAL PREVIEW
# + CLASS DESCRIPTION TABLE + PRODUCTIVITY POTENTIAL
#
# FIX V4:
# - Directly reads ONLY the known 820-row mapping file:
#   40B04A_ASU_CLIMATE_CELL_MAPPING_SIAK_AOI01_V1.csv
# - Does NOT scan other CSVs.
# - Auto-detects centroid coordinate columns flexibly from the
#   actual header and numeric ranges.
#
# MEMORY-SAFE: CSV ONLY
# NO GEOPANDAS / SHAPELY
# NO MODEL RERUN / NO CLASS RECALCULATION
# ============================================================

from pathlib import Path
import csv
import math
import json
import statistics
import matplotlib.pyplot as plt

WORKDIR = Path(
    r"C:\Users\user\Documents\KERJA\SPATIAL DATA ANALYST INTERN\04_YIELD"
)

FINAL = WORKDIR / (
    "40I01_FINAL_OUTPUT4_DELIVERY_MASTER_820_SIAK_AOI01_V1.csv"
)

CLASS_SUMMARY = WORKDIR / (
    "40I01_FINAL_CLASS_AREA_SUMMARY_SIAK_AOI01_V1.csv"
)

CENTROID_FILE = WORKDIR / (
    "40B04A_ASU_CLIMATE_CELL_MAPPING_SIAK_AOI01_V1.csv"
)

OUTDIR = WORKDIR / "40I02A_LITE_VISUAL_PREVIEW_SIAK_AOI01_V4"

OUT_PNG = OUTDIR / (
    "40I02A_MANAGEMENT_PRIORITY_CLASS_0_4_WITH_PRODUCTIVITY_SIAK_AOI01_V4.png"
)

OUT_TABLE_CSV = OUTDIR / (
    "40I02A_CLASS_DESCRIPTION_WITH_PRODUCTIVITY_SIAK_AOI01_V4.csv"
)

OUT_QC = OUTDIR / (
    "40I02A_MANAGEMENT_PRIORITY_CLASS_0_4_PREVIEW_QC_SIAK_AOI01_V4.json"
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
print("40I02A V4 — MANAGEMENT PRIORITY VISUAL PREVIEW")
print("+ PRODUCTIVITY POTENTIAL TABLE")
print("CSV ONLY / MEMORY SAFE")
print("====================================================")


# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------

def read_csv(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def as_float(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except Exception:
        return None


def numeric_values(rows, col, max_n=50):
    out = []

    for r in rows:
        x = as_float(r.get(col))

        if x is not None:
            out.append(x)

        if len(out) >= max_n:
            break

    return out


def median(values):
    return statistics.median(values) if values else None


def classify_coord_col(name, values):
    """
    Return a rough coordinate semantic classification.
    """
    if not values:
        return None

    u = name.upper()
    med = median(values)
    vmin = min(values)
    vmax = max(values)

    # Strong name hints.
    if any(k in u for k in ["LON", "LONGITUDE"]):
        return "LON"

    if any(k in u for k in ["LAT", "LATITUDE"]):
        return "LAT"

    if any(k in u for k in ["EAST", "EASTING"]):
        return "X_UTM"

    if any(k in u for k in ["NORTH", "NORTHING"]):
        return "Y_UTM"

    # Generic centroid X/Y names.
    if "CENTROID" in u and (
        u.endswith("_X")
        or "_X_" in u
        or u == "X"
    ):
        return "X_GENERIC"

    if "CENTROID" in u and (
        u.endswith("_Y")
        or "_Y_" in u
        or u == "Y"
    ):
        return "Y_GENERIC"

    # Numeric-range fallback.
    # Siak longitude should be around 100-103 E.
    if 90 <= med <= 120 and -180 <= vmin <= 180 and -180 <= vmax <= 180:
        return "LON_RANGE"

    # Siak latitude should be around -2 to +2.
    if -10 <= med <= 10 and -90 <= vmin <= 90 and -90 <= vmax <= 90:
        return "LAT_RANGE"

    # UTM zone 47N/S-ish easting.
    if 100000 <= med <= 900000:
        return "X_UTM_RANGE"

    # UTM northing can vary widely; keep broad.
    if 0 <= med <= 10000000:
        return "Y_UTM_RANGE"

    return None


# ------------------------------------------------------------
# 1. PREFLIGHT
# ------------------------------------------------------------

for p in [FINAL, CLASS_SUMMARY, CENTROID_FILE]:
    if not p.exists():
        raise FileNotFoundError(p)

final_rows = read_csv(FINAL)
summary_rows = read_csv(CLASS_SUMMARY)
centroid_rows = read_csv(CENTROID_FILE)

if len(final_rows) != EXPECTED:
    raise ValueError(
        f"Expected 820 final ASUs; got {len(final_rows)}."
    )

if len(centroid_rows) != EXPECTED:
    raise ValueError(
        f"Expected 820 rows in 40B04A mapping; got {len(centroid_rows)}."
    )

final_by_id = {
    str(r["UNIT_ID"]): r
    for r in final_rows
}

centroid_by_id = {
    str(r["UNIT_ID"]): r
    for r in centroid_rows
}

if len(final_by_id) != EXPECTED:
    raise ValueError("Final UNIT_ID is not unique.")

if len(centroid_by_id) != EXPECTED:
    raise ValueError("40B04A UNIT_ID is not unique.")

if set(final_by_id) != set(centroid_by_id):
    raise ValueError(
        "40B04A UNIT_ID set does not exactly match final 820 ASUs."
    )

print("Frozen ASUs                    :", len(final_rows))
print("40B04A mapping rows            :", len(centroid_rows))


# ------------------------------------------------------------
# 2. AUTO-DETECT CENTROID COORDINATES FROM ACTUAL HEADER
# ------------------------------------------------------------

header = list(centroid_rows[0].keys())

print("\n40B04A HEADER")
print(header)

# Candidate columns exclude known non-coordinate model fields.
exclude_terms = [
    "AGE",
    "YEAR",
    "RAIN",
    "TEMP",
    "RH",
    "VPD",
    "WIND",
    "RAD",
    "PRESS",
    "SOIL",
    "SAND",
    "SILT",
    "CLAY",
    "SCORE",
    "FRACTION",
    "CELL_ID",
    "PAIR_ID",
    "UNIT_ID",
]

coord_candidates = []

for col in header:

    u = col.upper()

    if any(term in u for term in exclude_terms):
        # Allow obvious coordinate names even if "CELL" etc not relevant.
        if not any(
            k in u
            for k in [
                "CENTROID",
                "LON",
                "LAT",
                "EAST",
                "NORTH",
                "_X",
                "_Y",
            ]
        ):
            continue

    vals = numeric_values(
        centroid_rows,
        col,
        max_n=100
    )

    if len(vals) < 20:
        continue

    semantic = classify_coord_col(
        col,
        vals
    )

    if semantic is not None:
        coord_candidates.append({
            "col":
                col,

            "semantic":
                semantic,

            "median":
                median(vals),

            "min":
                min(vals),

            "max":
                max(vals),
        })

print("\nCOORDINATE CANDIDATES")
for c in coord_candidates:
    print(
        "-",
        c["col"],
        "|",
        c["semantic"],
        "| median=",
        c["median"]
    )

XCOL = None
YCOL = None
COORD_MODE = None

# First priority: explicit lon/lat names.
lon_cols = [
    c["col"]
    for c in coord_candidates
    if c["semantic"]
    in {
        "LON",
        "LON_RANGE",
    }
    and "CHIRPS" not in c["col"].upper()
    and "ERA5" not in c["col"].upper()
]

lat_cols = [
    c["col"]
    for c in coord_candidates
    if c["semantic"]
    in {
        "LAT",
        "LAT_RANGE",
    }
    and "CHIRPS" not in c["col"].upper()
    and "ERA5" not in c["col"].upper()
]

# Prefer columns with CENTROID in name.
lon_cols.sort(
    key=lambda c: (
        0 if "CENTROID" in c.upper() else 1,
        len(c)
    )
)

lat_cols.sort(
    key=lambda c: (
        0 if "CENTROID" in c.upper() else 1,
        len(c)
    )
)

if lon_cols and lat_cols:
    XCOL = lon_cols[0]
    YCOL = lat_cols[0]
    COORD_MODE = "LONLAT"

else:
    # Second priority: explicit/generic UTM X/Y.
    x_cols = [
        c["col"]
        for c in coord_candidates
        if c["semantic"]
        in {
            "X_UTM",
            "X_GENERIC",
            "X_UTM_RANGE",
        }
        and "CHIRPS" not in c["col"].upper()
        and "ERA5" not in c["col"].upper()
    ]

    y_cols = [
        c["col"]
        for c in coord_candidates
        if c["semantic"]
        in {
            "Y_UTM",
            "Y_GENERIC",
            "Y_UTM_RANGE",
        }
        and "CHIRPS" not in c["col"].upper()
        and "ERA5" not in c["col"].upper()
    ]

    x_cols.sort(
        key=lambda c: (
            0 if "CENTROID" in c.upper() else 1,
            len(c)
        )
    )

    y_cols.sort(
        key=lambda c: (
            0 if "CENTROID" in c.upper() else 1,
            len(c)
        )
    )

    if x_cols and y_cols:
        XCOL = x_cols[0]
        YCOL = y_cols[0]
        COORD_MODE = "UTM"

if XCOL is None or YCOL is None:
    raise ValueError(
        "Could not auto-detect ASU centroid coordinate columns. "
        "The actual 40B04A header has been printed above; send that header "
        "and we can lock the exact column names."
    )

print("\nCENTROID COORDINATES SELECTED")
print("X field                        :", XCOL)
print("Y field                        :", YCOL)
print("Mode                           :", COORD_MODE)


# ------------------------------------------------------------
# 3. BUILD PLOT DATA
# ------------------------------------------------------------

plot_rows = []

for uid, r in centroid_by_id.items():

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
        f"Expected 820 plottable ASUs; got {len(plot_rows)}."
    )


# ------------------------------------------------------------
# 4. PRODUCTIVITY SUMMARY BY CLASS
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
                "Class 0 range is incomplete."
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
# 5. CLASS TABLE
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

    p = productivity_summary[
        cls
    ]

    table_rows.append([
        str(cls),
        CLASS_LABEL[cls],
        f"{n}",
        f"{area:,.2f}",
        f"{pct:.2f}%",
        p["DISPLAY"],
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
            p["DISPLAY_LONG"],

        "PRODUCTIVITY_DISPLAY_TYPE":
            p["TYPE"],

        "MEDIAN_PRODUCTIVITY_CENTER_T_FFB_HA_YR":
            p["MEDIAN_CENTER"],

        "INDICATIVE_LOW_T_FFB_HA_YR":
            p["LOW"]
            if p["LOW"] is not None
            else "",

        "INDICATIVE_HIGH_T_FFB_HA_YR":
            p["HIGH"]
            if p["HIGH"] is not None
            else "",
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
        "Preview uses ASU centroids."
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
            if r["CLASS"] == cls
        )
    for cls in range(5)
}

checks = {
    "frozen_rows_820":
        len(final_rows) == 820,

    "mapping_rows_820":
        len(centroid_rows) == 820,

    "plotted_asus_820":
        len(plot_rows) == 820,

    "class_counts_preserved":
        class_counts
        == {
            0: 4,
            1: 159,
            2: 551,
            3: 103,
            4: 3,
        },

    "preview_png_created":
        OUT_PNG.exists(),

    "class_table_csv_created":
        OUT_TABLE_CSV.exists(),
}

status = (
    "PASS_40I02A_V4_VISUAL_PREVIEW"
    if all(
        checks.values()
    )
    else "REVIEW"
)

qc = {
    "status":
        status,

    "centroid_source":
        CENTROID_FILE.name,

    "coordinate_fields":
        [
            XCOL,
            YCOL
        ],

    "coordinate_mode":
        COORD_MODE,

    "class_counts":
        {
            str(k): v
            for k, v
            in class_counts.items()
        },

    "productivity_summary":
        {
            str(k):
                productivity_summary[k]
            for k in range(5)
        },

    "output_png":
        str(OUT_PNG),

    "class_table_csv":
        str(OUT_TABLE_CSV),

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
print("40I02A V4 FINISHED")
print("====================================================")
print("Status                         :", status)
print("Preview PNG                    :", OUT_PNG)
print("Class table CSV                :", OUT_TABLE_CSV)
print("QC JSON                        :", OUT_QC)

print("\nCLASS TABLE")
for cls in range(5):
    r = summary_by_class[cls]

    print(
        f"Class {cls} | "
        f"N={int(float(r['N_ASU']))} | "
        f"Area={float(r['AREA_HA']):.3f} ha | "
        f"Potential={productivity_summary[cls]['DISPLAY_LONG']}"
    )

print("\nNext                           : OPEN the PNG preview.")
print("====================================================")
