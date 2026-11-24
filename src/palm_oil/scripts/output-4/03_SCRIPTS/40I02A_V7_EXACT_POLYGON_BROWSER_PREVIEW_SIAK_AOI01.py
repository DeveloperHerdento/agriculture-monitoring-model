# ============================================================
# OUTPUT 4 / 40I02A V7
# EXACT POLYGON BROWSER PREVIEW — SIAK_AOI01
#
# PURE PYTHON STANDARD LIBRARY ONLY
# NO matplotlib / geopandas / shapely / QGIS
# NO model rerun / NO class recalculation
# ============================================================

from pathlib import Path
import csv
import json
import math
import html

WORKDIR = Path(
    r"C:\Users\user\Documents\KERJA\SPATIAL DATA ANALYST INTERN\04_YIELD"
)

ASU_GEOJSON = WORKDIR / "40B03A_FINAL_ASU_500M_EXACT_SIAK_AOI01_V1.geojson"
FINAL_CSV = WORKDIR / "40I01_FINAL_OUTPUT4_DELIVERY_MASTER_820_SIAK_AOI01_V1.csv"

OUTDIR = WORKDIR / "40I02A_EXACT_POLYGON_BROWSER_PREVIEW_SIAK_AOI01_V1"
OUT_HTML = OUTDIR / "40I02A_EXACT_ASU_MANAGEMENT_PRIORITY_PREVIEW_SIAK_AOI01_V1.html"
OUT_QC = OUTDIR / "40I02A_EXACT_ASU_MANAGEMENT_PRIORITY_PREVIEW_QC_SIAK_AOI01_V1.json"

EXPECTED_ASU = 820

CLASS_COLOR = {
    0: "#9E9E9E",
    1: "#2E7D32",
    2: "#F9A825",
    3: "#EF6C00",
    4: "#C62828",
}

CLASS_LABEL = {
    0: "Insufficient Data / Limited Evidence",
    1: "Maintain",
    2: "Monitor",
    3: "Management Intervention Priority",
    4: "Replanting Evaluation Priority",
}

MAX_POINTS_PER_RING = 120
MAP_W = 1120
MAP_H = 720
PANEL_W = 430
PAD = 26

print("====================================================")
print("40I02A V7 — EXACT POLYGON BROWSER PREVIEW")
print("PURE PYTHON / NO MATPLOTLIB / NO GEOPANDAS")
print("====================================================")


def read_csv_dict(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def esc(value):
    return html.escape(str(value), quote=True)


def as_float(value):
    if value is None:
        return None
    s = str(value).strip()
    if s == "":
        return None
    try:
        x = float(s)
    except Exception:
        return None
    return x if math.isfinite(x) else None


def fmt_num(value, decimals=2):
    x = as_float(value)
    return "n/a" if x is None else f"{x:.{decimals}f}"


def decimate_ring(ring, max_points=MAX_POINTS_PER_RING):
    if not ring:
        return []

    closed = (
        len(ring) >= 2
        and ring[0][0] == ring[-1][0]
        and ring[0][1] == ring[-1][1]
    )

    core = ring[:-1] if closed else ring

    if len(core) <= max_points:
        out = list(core)
    else:
        step = max(1, math.ceil(len(core) / max_points))
        out = core[::step]
        if core[-1] != out[-1]:
            out.append(core[-1])

    if out and out[0] != out[-1]:
        out.append(out[0])

    return out


def iter_rings(geometry):
    if geometry is None:
        return

    gtype = geometry.get("type")
    coords = geometry.get("coordinates")

    if gtype == "Polygon":
        for ring in coords or []:
            yield ring
    elif gtype == "MultiPolygon":
        for polygon in coords or []:
            for ring in polygon:
                yield ring
    else:
        raise ValueError(f"Unsupported geometry type: {gtype}")


def feature_extent(geometry):
    xmin = float("inf")
    ymin = float("inf")
    xmax = float("-inf")
    ymax = float("-inf")
    found = False

    for ring in iter_rings(geometry):
        for pt in ring:
            if len(pt) < 2:
                continue
            x = float(pt[0])
            y = float(pt[1])
            xmin = min(xmin, x)
            ymin = min(ymin, y)
            xmax = max(xmax, x)
            ymax = max(ymax, y)
            found = True

    if not found:
        return None

    return xmin, ymin, xmax, ymax


# ------------------------------------------------------------
# 1. LOAD
# ------------------------------------------------------------

if not ASU_GEOJSON.exists():
    raise FileNotFoundError(f"Exact ASU GeoJSON not found:\n{ASU_GEOJSON}")

if not FINAL_CSV.exists():
    raise FileNotFoundError(f"Frozen 40I01 CSV not found:\n{FINAL_CSV}")

attrs = read_csv_dict(FINAL_CSV)

if len(attrs) != EXPECTED_ASU:
    raise ValueError(f"Expected {EXPECTED_ASU} frozen rows; got {len(attrs)}.")

attr_by_id = {str(r["UNIT_ID"]): r for r in attrs}

if len(attr_by_id) != EXPECTED_ASU:
    raise ValueError("Frozen UNIT_ID is not unique.")

print("Frozen attributes              :", len(attrs))
print("Loading exact GeoJSON          :", ASU_GEOJSON.name)

with open(ASU_GEOJSON, "r", encoding="utf-8") as f:
    geo = json.load(f)

features = geo.get("features", [])

if len(features) != EXPECTED_ASU:
    raise ValueError(f"Expected {EXPECTED_ASU} GeoJSON features; got {len(features)}.")

feature_ids = []

for feat in features:
    props = feat.get("properties", {})
    uid = str(props.get("UNIT_ID", ""))
    if not uid:
        raise ValueError("GeoJSON feature missing UNIT_ID.")
    feature_ids.append(uid)

if len(set(feature_ids)) != EXPECTED_ASU:
    raise ValueError("GeoJSON UNIT_ID is not unique.")

if set(feature_ids) != set(attr_by_id):
    raise ValueError("UNIT_ID mismatch between exact geometry and frozen attributes.")

print("Exact geometry features        :", len(features))
print("UNIT_ID match                  : 820 / 820")


# ------------------------------------------------------------
# 2. EXTENT + COUNTS
# ------------------------------------------------------------

xmin = float("inf")
ymin = float("inf")
xmax = float("-inf")
ymax = float("-inf")

geometry_types = set()
raw_ring_count = 0
raw_vertex_count = 0
class_counts = {i: 0 for i in range(5)}

for feat in features:
    geometry = feat.get("geometry")
    geometry_types.add(geometry.get("type"))

    extent = feature_extent(geometry)
    if extent is None:
        raise ValueError("Empty geometry encountered.")

    fxmin, fymin, fxmax, fymax = extent
    xmin = min(xmin, fxmin)
    ymin = min(ymin, fymin)
    xmax = max(xmax, fxmax)
    ymax = max(ymax, fymax)

    for ring in iter_rings(geometry):
        raw_ring_count += 1
        raw_vertex_count += len(ring)

    uid = str(feat["properties"]["UNIT_ID"])
    cls = int(float(attr_by_id[uid]["MANAGEMENT_PRIORITY_CLASS"]))
    class_counts[cls] += 1

expected_counts = {0: 4, 1: 159, 2: 551, 3: 103, 4: 3}

if class_counts != expected_counts:
    raise ValueError(f"Frozen class counts changed unexpectedly: {class_counts}")

print("Geometry types                 :", sorted(geometry_types))
print("Raw rings                      :", raw_ring_count)
print("Raw vertices                   :", raw_vertex_count)
print("Class counts                   :", class_counts)


# ------------------------------------------------------------
# 3. TRANSFORM
# ------------------------------------------------------------

if xmax <= xmin or ymax <= ymin:
    raise ValueError("Invalid spatial extent.")

mean_lat_rad = math.radians((ymin + ymax) / 2.0)
lon_scale = max(0.01, math.cos(mean_lat_rad))

world_w = (xmax - xmin) * lon_scale
world_h = ymax - ymin

usable_w = MAP_W - 2 * PAD
usable_h = MAP_H - 2 * PAD

scale = min(usable_w / world_w, usable_h / world_h)

draw_w = world_w * scale
draw_h = world_h * scale

offset_x = PAD + (usable_w - draw_w) / 2.0
offset_y = PAD + (usable_h - draw_h) / 2.0


def project_xy(lon, lat):
    px = offset_x + (lon - xmin) * lon_scale * scale
    py = offset_y + draw_h - (lat - ymin) * scale
    return px, py


def geometry_to_svg_path(geometry):
    path_parts = []

    for ring in iter_rings(geometry):
        ring2 = decimate_ring(ring)
        if len(ring2) < 4:
            continue

        projected = [
            project_xy(float(pt[0]), float(pt[1]))
            for pt in ring2
        ]

        x0, y0 = projected[0]
        cmds = [f"M{x0:.2f},{y0:.2f}"]

        for x, y in projected[1:]:
            cmds.append(f"L{x:.2f},{y:.2f}")

        cmds.append("Z")
        path_parts.append("".join(cmds))

    return "".join(path_parts)


# ------------------------------------------------------------
# 4. BUILD SVG PATHS
# ------------------------------------------------------------

print("Building browser paths         : started")

path_rows = []
display_ring_count = 0
display_vertex_count = 0

for feat in features:
    uid = str(feat["properties"]["UNIT_ID"])
    a = attr_by_id[uid]
    cls = int(float(a["MANAGEMENT_PRIORITY_CLASS"]))
    geometry = feat["geometry"]

    for ring in iter_rings(geometry):
        ring2 = decimate_ring(ring)
        if len(ring2) >= 4:
            display_ring_count += 1
            display_vertex_count += len(ring2)

    d = geometry_to_svg_path(geometry)
    if not d:
        continue

    productivity = str(a.get("PRODUCTIVITY_DISPLAY_TEXT", "")).strip()

    if not productivity:
        center = fmt_num(a.get("PRODUCTIVITY_CENTER_T_FFB_HA_YR"), 2)
        low = fmt_num(a.get("PRODUCTIVITY_LOW_T_FFB_HA_YR"), 2)
        high = fmt_num(a.get("PRODUCTIVITY_HIGH_T_FFB_HA_YR"), 2)
        productivity = f"{center} t FFB/ha/yr ({low}–{high})"

    pathway = a.get("PRODUCTIVITY_PATHWAY", "n/a")
    confidence = a.get("MANAGEMENT_PRIORITY_CONFIDENCE", "n/a")
    stability = a.get("RULE_STABILITY", "n/a")

    tooltip = (
        f"{uid}||"
        f"Class {cls} — {CLASS_LABEL[cls]}||"
        f"Productivity: {productivity}||"
        f"Pathway: {pathway}||"
        f"Confidence: {confidence}||"
        f"Rule stability: {stability}"
    )

    path_rows.append({
        "uid": uid,
        "cls": cls,
        "d": d,
        "tooltip": tooltip,
    })

if len(path_rows) != EXPECTED_ASU:
    raise ValueError(f"Expected {EXPECTED_ASU} rendered paths; got {len(path_rows)}.")

print("Browser paths                  :", len(path_rows))
print("Display rings                  :", display_ring_count)
print("Display vertices               :", display_vertex_count)


# ------------------------------------------------------------
# 5. HTML PARTS
# ------------------------------------------------------------

svg_paths = []

for row in path_rows:
    cls = row["cls"]
    svg_paths.append(
        f'<path class="asu class-{cls}" '
        f'd="{row["d"]}" '
        f'fill="{CLASS_COLOR[cls]}" '
        f'fill-rule="evenodd" '
        f'data-tip="{esc(row["tooltip"])}"></path>'
    )

legend_items = []

for cls in range(5):
    legend_items.append(
        '<div class="legend-row">'
        f'<span class="swatch" style="background:{CLASS_COLOR[cls]}"></span>'
        '<div>'
        f'<div class="legend-label">Class {cls} — {esc(CLASS_LABEL[cls])}</div>'
        f'<div class="legend-count">{class_counts[cls]} ASU</div>'
        '</div>'
        '</div>'
    )

html_text = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Output 4 — Management Priority — SIAK_AOI01</title>
<style>
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  font-family: Arial, Helvetica, sans-serif;
  background: #f3f5f7;
  color: #1f2937;
}}
.page {{
  max-width: 1600px;
  margin: 0 auto;
  padding: 24px;
}}
h1 {{
  margin: 0 0 4px 0;
  font-size: 26px;
}}
.subtitle {{
  color: #6b7280;
  margin-bottom: 18px;
}}
.layout {{
  display: grid;
  grid-template-columns: minmax(0, 1fr) {PANEL_W}px;
  gap: 18px;
  align-items: start;
}}
.map-card, .panel {{
  background: white;
  border: 1px solid #d1d5db;
  border-radius: 12px;
}}
.map-card {{ padding: 10px; }}
svg {{
  width: 100%;
  height: auto;
  display: block;
  background: white;
}}
.asu {{
  fill-opacity: 0.94;
  stroke: rgba(255,255,255,0.72);
  stroke-width: 0.42;
  vector-effect: non-scaling-stroke;
  cursor: crosshair;
}}
.asu:hover {{
  stroke: #111827;
  stroke-width: 1.15;
  fill-opacity: 1;
}}
.hide-boundary .asu {{ stroke: none; }}
.panel {{ padding: 18px; }}
.panel h2 {{
  font-size: 17px;
  margin: 0 0 12px 0;
}}
.legend-row {{
  display: flex;
  gap: 10px;
  align-items: flex-start;
  margin: 10px 0;
}}
.swatch {{
  width: 18px;
  height: 18px;
  border-radius: 3px;
  flex: none;
  margin-top: 1px;
}}
.legend-label {{
  font-size: 14px;
  font-weight: 600;
}}
.legend-count {{
  font-size: 12px;
  color: #6b7280;
  margin-top: 2px;
}}
.note {{
  font-size: 12px;
  color: #4b5563;
  line-height: 1.45;
  margin-top: 16px;
}}
.controls {{
  margin: 14px 0 18px 0;
  padding-bottom: 14px;
  border-bottom: 1px solid #e5e7eb;
}}
label {{ font-size: 13px; }}
#tooltip {{
  position: fixed;
  display: none;
  z-index: 1000;
  pointer-events: none;
  max-width: 430px;
  padding: 10px 12px;
  border-radius: 8px;
  background: rgba(17,24,39,0.96);
  color: white;
  font-size: 12px;
  line-height: 1.45;
  white-space: pre-line;
  box-shadow: 0 4px 16px rgba(0,0,0,0.25);
}}
.metric {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-top: 16px;
}}
.metric > div {{
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 9px;
}}
.metric .k {{
  color: #6b7280;
  font-size: 11px;
}}
.metric .v {{
  font-weight: 700;
  margin-top: 2px;
}}
@media (max-width: 1050px) {{
  .layout {{ grid-template-columns: 1fr; }}
}}
</style>
</head>
<body>
<div class="page">
  <h1>Output 4 — Productivity Potential & Management Priority</h1>
  <div class="subtitle">
    SIAK_AOI01 | Exact clipped 500×500 m ASU palm geometry | Frozen Output 4
  </div>

  <div class="layout">
    <div class="map-card" id="mapCard">
      <svg viewBox="0 0 {MAP_W} {MAP_H}"
           role="img"
           aria-label="Management Priority Class 0 to 4 across exact clipped palm ASUs in SIAK_AOI01">
        <rect x="0" y="0" width="{MAP_W}" height="{MAP_H}" fill="#ffffff"/>
        {''.join(svg_paths)}
      </svg>
    </div>

    <aside class="panel">
      <h2>Management Priority</h2>

      {''.join(legend_items)}

      <div class="controls">
        <label>
          <input id="boundaryToggle" type="checkbox" checked>
          Show thin ASU boundaries
        </label>
      </div>

      <div class="metric">
        <div>
          <div class="k">Total ASU</div>
          <div class="v">820</div>
        </div>
        <div>
          <div class="k">Palm area</div>
          <div class="v">13,867.10 ha</div>
        </div>
        <div>
          <div class="k">ASU framework</div>
          <div class="v">500 × 500 m</div>
        </div>
        <div>
          <div class="k">Monitoring year</div>
          <div class="v">2025</div>
        </div>
      </div>

      <div class="note">
        <b>How to read this map:</b><br>
        The colored footprint is the actual Output-1 palm geometry clipped by the
        500×500 m Analysis Spatial Unit. It should therefore look much denser than
        the earlier centroid preview while preserving ASU-level management classes.
      </div>

      <div class="note">
        Class 4 means <b>Replanting Evaluation Priority</b>, not an automatic replanting order.
        Productivity remains modelled/indicative potential rather than locally validated actual FFB yield.
      </div>

      <div class="note">
        Hover over the map to inspect UNIT_ID, class, productivity potential,
        pathway, confidence, and rule stability.
      </div>
    </aside>
  </div>
</div>

<div id="tooltip"></div>

<script>
(() => {{
  const mapCard = document.getElementById("mapCard");
  const toggle = document.getElementById("boundaryToggle");
  const tooltip = document.getElementById("tooltip");

  toggle.addEventListener("change", () => {{
    mapCard.classList.toggle("hide-boundary", !toggle.checked);
  }});

  document.querySelectorAll(".asu").forEach((el) => {{
    el.addEventListener("mousemove", (ev) => {{
      const raw = el.getAttribute("data-tip") || "";
      tooltip.textContent = raw.split("||").join("\\n");
      tooltip.style.display = "block";

      const pad = 16;
      const tw = tooltip.offsetWidth || 320;
      const th = tooltip.offsetHeight || 120;

      let left = ev.clientX + 14;
      let top = ev.clientY + 14;

      if (left + tw + pad > window.innerWidth) {{
        left = ev.clientX - tw - 14;
      }}

      if (top + th + pad > window.innerHeight) {{
        top = ev.clientY - th - 14;
      }}

      tooltip.style.left = left + "px";
      tooltip.style.top = top + "px";
    }});

    el.addEventListener("mouseleave", () => {{
      tooltip.style.display = "none";
    }});
  }});
}})();
</script>
</body>
</html>
"""

OUTDIR.mkdir(parents=True, exist_ok=True)

with open(OUT_HTML, "w", encoding="utf-8") as f:
    f.write(html_text)


# ------------------------------------------------------------
# 6. QC
# ------------------------------------------------------------

qc = {
    "status": "PASS_40I02A_EXACT_POLYGON_BROWSER_PREVIEW",
    "source_geometry": ASU_GEOJSON.name,
    "source_attributes": FINAL_CSV.name,
    "geometry_feature_count": len(features),
    "matched_unit_id_count": len(set(feature_ids) & set(attr_by_id)),
    "class_counts": {str(k): v for k, v in class_counts.items()},
    "raw_ring_count": raw_ring_count,
    "raw_vertex_count": raw_vertex_count,
    "display_ring_count": display_ring_count,
    "display_vertex_count": display_vertex_count,
    "display_decimation_only": True,
    "max_points_per_ring": MAX_POINTS_PER_RING,
    "scientific_results_changed": False,
    "output_html": str(OUT_HTML),
}

with open(OUT_QC, "w", encoding="utf-8") as f:
    json.dump(qc, f, indent=2)


print("\n====================================================")
print("40I02A V7 FINISHED")
print("====================================================")
print("Status                         : PASS_40I02A_EXACT_POLYGON_BROWSER_PREVIEW")
print("HTML preview                   :", OUT_HTML)
print("QC JSON                        :", OUT_QC)
print("Rendered ASUs                  :", len(path_rows))
print("Class counts                   :", class_counts)
print("Scientific result changed      : False")
print("\nNext                           : double-click HTML in File Explorer.")
print("====================================================")
