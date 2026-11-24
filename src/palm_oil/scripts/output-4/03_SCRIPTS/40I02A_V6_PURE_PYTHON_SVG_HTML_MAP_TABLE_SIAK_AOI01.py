# ============================================================
# OUTPUT 4 / 40I02A V6 — PURE PYTHON SVG/HTML
# MANAGEMENT PRIORITY CLASS 0-4
# + CLASS TABLE + POTENTIAL PRODUCTIVITY
#
# NO matplotlib
# NO geopandas
# NO shapely
# NO pandas
# NO native plotting backend
#
# PURPOSE:
# Avoid Jupyter kernel crashes caused by rendering libraries.
# Output is a static HTML + SVG visualization that can be opened
# directly in Chrome/Edge, plus a CSV summary table.
# ============================================================

from pathlib import Path
import csv
import math
import statistics
import html

WORKDIR = Path(
    r"C:\Users\user\Documents\KERJA\SPATIAL DATA ANALYST INTERN\04_YIELD"
)

FINAL = WORKDIR / "40I01_FINAL_OUTPUT4_DELIVERY_MASTER_820_SIAK_AOI01_V1.csv"
SUMMARY = WORKDIR / "40I01_FINAL_CLASS_AREA_SUMMARY_SIAK_AOI01_V1.csv"
MAPPING = WORKDIR / "40B04A_ASU_CLIMATE_CELL_MAPPING_SIAK_AOI01_V1.csv"

OUTDIR = WORKDIR / "40I02A_SIMPLE_VISUAL_PREVIEW_SIAK_AOI01_V6"
OUT_HTML = OUTDIR / "40I02A_MANAGEMENT_PRIORITY_MAP_TABLE_SIAK_AOI01_V6.html"
OUT_SVG = OUTDIR / "40I02A_MANAGEMENT_PRIORITY_MAP_TABLE_SIAK_AOI01_V6.svg"
OUT_CSV = OUTDIR / "40I02A_CLASS_TABLE_WITH_PRODUCTIVITY_SIAK_AOI01_V6.csv"

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


def esc(s):
    return html.escape(str(s), quote=True)


for p in (FINAL, SUMMARY, MAPPING):
    if not p.exists():
        raise FileNotFoundError(p)

final_rows = read_csv(FINAL)
summary_rows = read_csv(SUMMARY)
mapping_rows = read_csv(MAPPING)

if len(final_rows) != 820:
    raise ValueError(f"FINAL rows harus 820, ditemukan {len(final_rows)}")

if len(mapping_rows) != 820:
    raise ValueError(f"MAPPING rows harus 820, ditemukan {len(mapping_rows)}")

final_by_id = {str(r["UNIT_ID"]): r for r in final_rows}
mapping_by_id = {str(r["UNIT_ID"]): r for r in mapping_rows}

if len(final_by_id) != 820 or len(mapping_by_id) != 820:
    raise ValueError("UNIT_ID tidak unik.")

if set(final_by_id) != set(mapping_by_id):
    raise ValueError("UNIT_ID FINAL dan MAPPING tidak sama persis.")

print("FINAL rows                     : 820")
print("MAPPING rows                   : 820")
print("Renderer                       : pure Python SVG/HTML (no matplotlib)")


# ------------------------------------------------------------
# PRODUCTIVITY SUMMARY PER CLASS
# ------------------------------------------------------------

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

    med = statistics.median(centers)

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
            "display": f"{med:.2f}",
            "note": "Median potential",
        }


# ------------------------------------------------------------
# AREA SUMMARY
# ------------------------------------------------------------

summary_by_class = {
    int(float(r["CLASS"])): r
    for r in summary_rows
}

csv_rows = []

for cls in range(5):
    s = summary_by_class[cls]

    csv_rows.append({
        "CLASS": cls,
        "STATUS": CLASS_LABEL[cls],
        "N_ASU": int(float(s["N_ASU"])),
        "AREA_HA": float(s["AREA_HA"]),
        "AREA_PCT": float(s["AREA_PCT"]),
        "POTENTIAL_PRODUCTIVITY_T_FFB_HA_YR": prod[cls]["display"],
        "PRODUCTIVITY_NOTE": prod[cls]["note"],
    })


# ------------------------------------------------------------
# MAP POINTS
# ------------------------------------------------------------

points = []

for uid, m in mapping_by_id.items():
    lon = num(m.get("CENTROID_LON_EXACT"))
    lat = num(m.get("CENTROID_LAT_EXACT"))

    if lon is None or lat is None:
        raise ValueError(f"Centroid kosong untuk {uid}")

    cls = int(float(final_by_id[uid]["MANAGEMENT_PRIORITY_CLASS"]))

    points.append((uid, lon, lat, cls))

lons = [p[1] for p in points]
lats = [p[2] for p in points]

lon_min, lon_max = min(lons), max(lons)
lat_min, lat_max = min(lats), max(lats)

if lon_max == lon_min or lat_max == lat_min:
    raise ValueError("Extent centroid tidak valid.")


# ------------------------------------------------------------
# SVG CANVAS
# ------------------------------------------------------------

W = 1600
H = 900

MAP_X = 70
MAP_Y = 105
MAP_W = 900
MAP_H = 700

TABLE_X = 1010
TABLE_Y = 135
TABLE_W = 540

pad_lon = (lon_max - lon_min) * 0.03
pad_lat = (lat_max - lat_min) * 0.03

xmin = lon_min - pad_lon
xmax = lon_max + pad_lon
ymin = lat_min - pad_lat
ymax = lat_max + pad_lat


def sx(lon):
    return MAP_X + (lon - xmin) / (xmax - xmin) * MAP_W


def sy(lat):
    return MAP_Y + MAP_H - (lat - ymin) / (ymax - ymin) * MAP_H


svg = []

svg.append(
    f'<svg xmlns="http://www.w3.org/2000/svg" '
    f'width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
)

svg.append("""
<style>
text { font-family: Arial, Helvetica, sans-serif; fill: #222; }
.title { font-size: 25px; font-weight: 700; }
.subtitle { font-size: 16px; fill: #555; }
.axis { font-size: 12px; fill: #666; }
.legend { font-size: 13px; }
.th { font-size: 12px; font-weight: 700; }
.td { font-size: 11px; }
.note { font-size: 12px; fill: #555; }
</style>
""")

svg.append('<rect width="100%" height="100%" fill="#ffffff"/>')

svg.append(
    '<text x="70" y="45" class="title">'
    'Output 4 — Management Priority Class 0–4'
    '</text>'
)

svg.append(
    '<text x="70" y="72" class="subtitle">'
    'SIAK_AOI01 | Static Spatial Preview'
    '</text>'
)

# Map frame
svg.append(
    f'<rect x="{MAP_X}" y="{MAP_Y}" width="{MAP_W}" height="{MAP_H}" '
    f'fill="#fafafa" stroke="#999" stroke-width="1"/>'
)

# Grid lines
for i in range(6):
    x = MAP_X + MAP_W * i / 5
    y = MAP_Y + MAP_H * i / 5

    svg.append(
        f'<line x1="{x:.1f}" y1="{MAP_Y}" x2="{x:.1f}" y2="{MAP_Y+MAP_H}" '
        f'stroke="#e6e6e6" stroke-width="1"/>'
    )

    svg.append(
        f'<line x1="{MAP_X}" y1="{y:.1f}" x2="{MAP_X+MAP_W}" y2="{y:.1f}" '
        f'stroke="#e6e6e6" stroke-width="1"/>'
    )

# Points
for uid, lon, lat, cls in points:
    x = sx(lon)
    y = sy(lat)
    size = 7 if cls in (0, 4) else 5
    half = size / 2

    svg.append(
        f'<rect x="{x-half:.2f}" y="{y-half:.2f}" '
        f'width="{size}" height="{size}" '
        f'fill="{CLASS_COLOR[cls]}" opacity="0.90">'
        f'<title>{esc(uid)} | Class {cls} | {esc(CLASS_LABEL[cls])}</title>'
        '</rect>'
    )

# Axis labels / extent
svg.append(
    f'<text x="{MAP_X}" y="{MAP_Y+MAP_H+25}" class="axis">'
    f'{lon_min:.4f}° E'
    '</text>'
)

svg.append(
    f'<text x="{MAP_X+MAP_W}" y="{MAP_Y+MAP_H+25}" '
    f'text-anchor="end" class="axis">{lon_max:.4f}° E</text>'
)

svg.append(
    f'<text x="{MAP_X-10}" y="{MAP_Y+12}" '
    f'text-anchor="end" class="axis">{lat_max:.4f}°</text>'
)

svg.append(
    f'<text x="{MAP_X-10}" y="{MAP_Y+MAP_H}" '
    f'text-anchor="end" class="axis">{lat_min:.4f}°</text>'
)

# Legend
legend_y = MAP_Y + 25

for cls in range(5):
    yy = legend_y + cls * 27

    svg.append(
        f'<rect x="{MAP_X+20}" y="{yy-11}" width="14" height="14" '
        f'fill="{CLASS_COLOR[cls]}"/>'
    )

    svg.append(
        f'<text x="{MAP_X+44}" y="{yy}" class="legend">'
        f'Class {cls} — {esc(CLASS_LABEL[cls])}'
        '</text>'
    )

# Table title
svg.append(
    f'<text x="{TABLE_X}" y="{TABLE_Y-30}" '
    f'class="title" style="font-size:19px">'
    'Keterangan Kelas & Potential Productivity'
    '</text>'
)

cols = [
    ("Class", 45),
    ("Status", 210),
    ("ASU", 55),
    ("Luas (ha)", 80),
    ("% Area", 70),
    ("Potential", 80),
]

col_x = [TABLE_X]
for _, cw in cols[:-1]:
    col_x.append(col_x[-1] + cw)

header_h = 42
row_h = 74
table_total_w = sum(cw for _, cw in cols)

svg.append(
    f'<rect x="{TABLE_X}" y="{TABLE_Y}" width="{table_total_w}" '
    f'height="{header_h + row_h*5}" fill="#fff" stroke="#aaa"/>'
)

# Header
x = TABLE_X
for label, cw in cols:
    svg.append(
        f'<rect x="{x}" y="{TABLE_Y}" width="{cw}" height="{header_h}" '
        f'fill="#f2f2f2" stroke="#bbb"/>'
    )
    svg.append(
        f'<text x="{x+6}" y="{TABLE_Y+25}" class="th">{esc(label)}</text>'
    )
    x += cw

# Rows
for idx, row in enumerate(csv_rows):
    y = TABLE_Y + header_h + idx * row_h

    vals = [
        str(row["CLASS"]),
        row["STATUS"],
        str(row["N_ASU"]),
        f'{row["AREA_HA"]:,.2f}',
        f'{row["AREA_PCT"]:.2f}%',
        row["POTENTIAL_PRODUCTIVITY_T_FFB_HA_YR"],
    ]

    x = TABLE_X

    for j, ((_, cw), val) in enumerate(zip(cols, vals)):
        svg.append(
            f'<rect x="{x}" y="{y}" width="{cw}" height="{row_h}" '
            f'fill="#ffffff" stroke="#ccc"/>'
        )

        if j == 1:
            words = val.split()
            lines = []
            line = ""

            for word in words:
                test = (line + " " + word).strip()

                if len(test) <= 25:
                    line = test
                else:
                    if line:
                        lines.append(line)
                    line = word

            if line:
                lines.append(line)

            for k, line in enumerate(lines[:3]):
                svg.append(
                    f'<text x="{x+6}" y="{y+21+k*16}" class="td">'
                    f'{esc(line)}</text>'
                )
        else:
            svg.append(
                f'<text x="{x+6}" y="{y+27}" class="td">{esc(val)}</text>'
            )

        x += cw

# Notes
note_y = TABLE_Y + header_h + row_h*5 + 35

notes = [
    "* Potential productivity: t fresh FFB/ha/tahun.",
    "Class 0 = indicative range.",
    "Class 1–4 = median productivity potential per kelas.",
    "Bukan actual yield lapangan.",
    "Class 4 = evaluation priority, bukan automatic replanting.",
    "Preview memakai centroid ASU; polygon exact tetap untuk final web map.",
]

for i, note in enumerate(notes):
    svg.append(
        f'<text x="{TABLE_X}" y="{note_y+i*20}" class="note">'
        f'{esc(note)}</text>'
    )

svg.append('</svg>')

svg_text = "\n".join(svg)

OUTDIR.mkdir(parents=True, exist_ok=True)

with open(OUT_SVG, "w", encoding="utf-8") as f:
    f.write(svg_text)

with open(OUT_HTML, "w", encoding="utf-8") as f:
    f.write(
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>40I02A Output 4 Preview</title>"
        "<style>body{margin:0;background:#f3f3f3}"
        "svg{display:block;margin:auto;max-width:100%;height:auto}</style>"
        "</head><body>"
        + svg_text +
        "</body></html>"
    )

with open(OUT_CSV, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(csv_rows[0].keys()))
    writer.writeheader()
    writer.writerows(csv_rows)


print("\n====================================================")
print("40I02A V6 FINISHED")
print("====================================================")

print("\nCLASS TABLE")
for row in csv_rows:
    print(
        f"Class {row['CLASS']} | "
        f"N={row['N_ASU']} | "
        f"Area={row['AREA_HA']:.2f} ha | "
        f"Potential={row['POTENTIAL_PRODUCTIVITY_T_FFB_HA_YR']} t FFB/ha/yr "
        f"({row['PRODUCTIVITY_NOTE']})"
    )

print("\nHTML visualization             :", OUT_HTML)
print("SVG visualization              :", OUT_SVG)
print("CSV table                      :", OUT_CSV)

print("\nSTATUS                         : PASS_40I02A_PURE_PYTHON_VISUAL")
print("Next                           : double-click file HTML di File Explorer.")
print("====================================================")
