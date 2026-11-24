# ============================================================
# OUTPUT 4 / 40I02A V5
# SIMPLE VISUAL PREVIEW — MANAGEMENT PRIORITY CLASS 0–4
# + TABLE KETERANGAN + POTENTIAL PRODUCTIVITY
#
# SAFE VERSION:
# - CSV only
# - no geopandas / shapely
# - no auto-detection
# - centroid fields locked from verified 40B04A:
#   CENTROID_LON_EXACT / CENTROID_LAT_EXACT
# - no model rerun / no class recalculation
# ============================================================

from pathlib import Path
import csv
import math
import statistics
import matplotlib.pyplot as plt

WORKDIR = Path(
    r"C:\Users\user\Documents\KERJA\SPATIAL DATA ANALYST INTERN\04_YIELD"
)

FINAL = WORKDIR / "40I01_FINAL_OUTPUT4_DELIVERY_MASTER_820_SIAK_AOI01_V1.csv"
SUMMARY = WORKDIR / "40I01_FINAL_CLASS_AREA_SUMMARY_SIAK_AOI01_V1.csv"
MAPPING = WORKDIR / "40B04A_ASU_CLIMATE_CELL_MAPPING_SIAK_AOI01_V1.csv"

OUTDIR = WORKDIR / "40I02A_SIMPLE_VISUAL_PREVIEW_SIAK_AOI01_V1"
OUTPNG = OUTDIR / "40I02A_MANAGEMENT_PRIORITY_MAP_TABLE_SIAK_AOI01_V1.png"
OUTCSV = OUTDIR / "40I02A_CLASS_TABLE_WITH_PRODUCTIVITY_SIAK_AOI01_V1.csv"

CLASS_LABEL = {
    0: "Insufficient Data / Limited Evidence",
    1: "Maintain",
    2: "Monitor",
    3: "Management Intervention Priority",
    4: "Replanting Evaluation Priority",
}

CLASS_COLOR = {
    0: "#9E9E9E",
    1: "#2E7D32",
    2: "#F9A825",
    3: "#EF6C00",
    4: "#C62828",
}


def read_csv(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def num(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except Exception:
        return None


final_rows = read_csv(FINAL)
summary_rows = read_csv(SUMMARY)
mapping_rows = read_csv(MAPPING)

if len(final_rows) != 820:
    raise ValueError(f"FINAL rows harus 820, ditemukan {len(final_rows)}")

if len(mapping_rows) != 820:
    raise ValueError(f"MAPPING rows harus 820, ditemukan {len(mapping_rows)}")

final_by_id = {str(r["UNIT_ID"]): r for r in final_rows}
mapping_by_id = {str(r["UNIT_ID"]): r for r in mapping_rows}

if set(final_by_id) != set(mapping_by_id):
    raise ValueError("UNIT_ID FINAL dan MAPPING tidak sama persis.")

print("FINAL rows                     :", len(final_rows))
print("MAPPING rows                   :", len(mapping_rows))
print("Centroid                       : CENTROID_LON_EXACT / CENTROID_LAT_EXACT")

prod = {}

for cls in range(5):
    rows = [
        r for r in final_rows
        if int(float(r["MANAGEMENT_PRIORITY_CLASS"])) == cls
    ]

    centers = [
        num(r.get("PRODUCTIVITY_CENTER_T_FFB_HA_YR"))
        for r in rows
    ]
    centers = [x for x in centers if x is not None]

    if not centers:
        raise ValueError(f"Tidak ada productivity center untuk Class {cls}")

    median_center = statistics.median(centers)

    if cls == 0:
        lows = [num(r.get("PRODUCTIVITY_LOW_T_FFB_HA_YR")) for r in rows]
        highs = [num(r.get("PRODUCTIVITY_HIGH_T_FFB_HA_YR")) for r in rows]
        lows = [x for x in lows if x is not None]
        highs = [x for x in highs if x is not None]

        if not lows or not highs:
            raise ValueError("Range productivity Class 0 tidak lengkap.")

        lo = min(lows)
        hi = max(highs)

        prod[cls] = {
            "display": f"{lo:.2f}–{hi:.2f}",
            "note": "Indicative range",
        }
    else:
        prod[cls] = {
            "display": f"{median_center:.2f}",
            "note": "Median potential",
        }

summary_by_class = {
    int(float(r["CLASS"])): r
    for r in summary_rows
}

table_rows = []
csv_rows = []

for cls in range(5):
    s = summary_by_class[cls]
    n = int(float(s["N_ASU"]))
    area = float(s["AREA_HA"])
    pct = float(s["AREA_PCT"])

    table_rows.append([
        str(cls),
        CLASS_LABEL[cls],
        str(n),
        f"{area:,.2f}",
        f"{pct:.2f}%",
        prod[cls]["display"],
    ])

    csv_rows.append({
        "CLASS": cls,
        "STATUS": CLASS_LABEL[cls],
        "N_ASU": n,
        "AREA_HA": area,
        "AREA_PCT": pct,
        "POTENTIAL_PRODUCTIVITY_T_FFB_HA_YR": prod[cls]["display"],
        "PRODUCTIVITY_NOTE": prod[cls]["note"],
    })

points = {cls: {"x": [], "y": []} for cls in range(5)}

for uid, m in mapping_by_id.items():
    lon = num(m.get("CENTROID_LON_EXACT"))
    lat = num(m.get("CENTROID_LAT_EXACT"))

    if lon is None or lat is None:
        raise ValueError(f"Centroid kosong untuk {uid}")

    cls = int(float(final_by_id[uid]["MANAGEMENT_PRIORITY_CLASS"]))
    points[cls]["x"].append(lon)
    points[cls]["y"].append(lat)

OUTDIR.mkdir(parents=True, exist_ok=True)
plt.close("all")

fig = plt.figure(figsize=(16, 9))

ax = fig.add_axes([0.05, 0.10, 0.56, 0.80])

for cls in range(5):
    size = 32 if cls in (0, 4) else 15

    ax.scatter(
        points[cls]["x"],
        points[cls]["y"],
        s=size,
        marker="s",
        c=CLASS_COLOR[cls],
        label=f"Class {cls} — {CLASS_LABEL[cls]}",
        alpha=0.90,
        edgecolors="none",
    )

ax.set_title(
    "Output 4 — Management Priority Class 0–4\n"
    "SIAK_AOI01 | Spatial Preview",
    fontsize=14,
    fontweight="bold",
)

ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
ax.grid(alpha=0.20)
ax.set_aspect("equal", adjustable="box")
ax.legend(loc="best", fontsize=8, frameon=True)

ax2 = fig.add_axes([0.64, 0.17, 0.35, 0.66])
ax2.axis("off")

ax2.set_title(
    "Keterangan Kelas & Potential Productivity",
    fontsize=12,
    fontweight="bold",
    pad=10,
)

tbl = ax2.table(
    cellText=table_rows,
    colLabels=[
        "Class",
        "Status",
        "ASU",
        "Luas\n(ha)",
        "% Area",
        "Potential\nProductivity*",
    ],
    loc="center",
    cellLoc="left",
    colLoc="left",
    colWidths=[0.07, 0.32, 0.08, 0.14, 0.10, 0.22],
)

tbl.auto_set_font_size(False)
tbl.set_fontsize(7.6)
tbl.scale(1.0, 2.0)

ax2.text(
    0.0,
    -0.06,
    (
        "* t fresh FFB/ha/tahun\n"
        "Class 0 = indicative range.\n"
        "Class 1–4 = median productivity potential per kelas.\n"
        "Bukan actual yield lapangan.\n"
        "Class 4 = evaluation priority, bukan automatic replanting."
    ),
    transform=ax2.transAxes,
    va="top",
    fontsize=8,
)

fig.text(
    0.05,
    0.025,
    "820 ASUs | Frozen Output 4 | No model rerun / no class recalculation",
    fontsize=8,
)

fig.savefig(
    OUTPNG,
    dpi=170,
    bbox_inches="tight",
    facecolor="white",
)

plt.close(fig)

with open(OUTCSV, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(csv_rows[0].keys()))
    writer.writeheader()
    writer.writerows(csv_rows)

print("\n====================================================")
print("40I02A V5 FINISHED")
print("====================================================")
print("PNG                            :", OUTPNG)
print("CSV table                      :", OUTCSV)

print("\nCLASS TABLE")
for cls in range(5):
    s = summary_by_class[cls]
    print(
        f"Class {cls} | "
        f"N={int(float(s['N_ASU']))} | "
        f"Area={float(s['AREA_HA']):.2f} ha | "
        f"Potential={prod[cls]['display']} t FFB/ha/yr "
        f"({prod[cls]['note']})"
    )

print("\nSTATUS                         : PASS_40I02A_SIMPLE_VISUAL")
print("Next                           : buka PNG hasilnya.")
print("====================================================")
