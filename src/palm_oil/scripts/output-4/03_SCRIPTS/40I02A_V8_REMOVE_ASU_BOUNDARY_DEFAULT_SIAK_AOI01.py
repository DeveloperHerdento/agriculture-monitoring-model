# ============================================================
# OUTPUT 4 / 40I02A V8
# REMOVE ASU BOUNDARIES BY DEFAULT
#
# PURPOSE
# -------
# Modify the already-successful V7 HTML preview:
# - default map = NO white ASU boundary lines
# - checkbox remains available if you want to show boundaries
# - popup/hover behavior remains unchanged
#
# NO geometry processing
# NO model rerun
# NO geopandas / matplotlib / shapely
# ============================================================

from pathlib import Path

WORKDIR = Path(
    r"C:\Users\user\Documents\KERJA\SPATIAL DATA ANALYST INTERN\04_YIELD"
)

V7_DIR = WORKDIR / "40I02A_EXACT_POLYGON_BROWSER_PREVIEW_SIAK_AOI01_V1"

INPUT_HTML = V7_DIR / (
    "40I02A_EXACT_ASU_MANAGEMENT_PRIORITY_PREVIEW_SIAK_AOI01_V1.html"
)

OUTPUT_HTML = V7_DIR / (
    "40I02A_EXACT_ASU_MANAGEMENT_PRIORITY_PREVIEW_NO_BOUNDARY_SIAK_AOI01_V2.html"
)

if not INPUT_HTML.exists():
    raise FileNotFoundError(
        f"V7 HTML tidak ditemukan:\n{INPUT_HTML}"
    )

text = INPUT_HTML.read_text(
    encoding="utf-8"
)

# 1) Default polygon border = none.
old_stroke = """stroke: rgba(255,255,255,0.72);
  stroke-width: 0.42;"""

new_stroke = """stroke: none;
  stroke-width: 0.42;"""

if old_stroke not in text:
    raise ValueError(
        "CSS stroke V7 tidak ditemukan. "
        "Pastikan INPUT_HTML adalah hasil V7."
    )

text = text.replace(
    old_stroke,
    new_stroke,
    1
)

# 2) Boundary class now means SHOW, not HIDE.
old_boundary_css = """.hide-boundary .asu { stroke: none; }"""

new_boundary_css = """.show-boundary .asu {
  stroke: rgba(255,255,255,0.72);
  stroke-width: 0.42;
}"""

if old_boundary_css not in text:
    raise ValueError(
        "Boundary CSS V7 tidak ditemukan."
    )

text = text.replace(
    old_boundary_css,
    new_boundary_css,
    1
)

# 3) Checkbox default = unchecked.
text = text.replace(
    '<input id="boundaryToggle" type="checkbox" checked>',
    '<input id="boundaryToggle" type="checkbox">',
    1
)

# 4) JS toggle updated accordingly.
old_js = """mapCard.classList.toggle("hide-boundary", !toggle.checked);"""

new_js = """mapCard.classList.toggle("show-boundary", toggle.checked);"""

if old_js not in text:
    raise ValueError(
        "Boundary toggle JS V7 tidak ditemukan."
    )

text = text.replace(
    old_js,
    new_js,
    1
)

# 5) Slightly clearer subtitle note.
text = text.replace(
    "Show thin ASU boundaries",
    "Show ASU boundaries",
    1
)

OUTPUT_HTML.write_text(
    text,
    encoding="utf-8"
)

print("====================================================")
print("40I02A V8 FINISHED")
print("====================================================")
print("Status                         : PASS_BOUNDARYLESS_DEFAULT")
print("Input V7 HTML                  :", INPUT_HTML)
print("New HTML                       :", OUTPUT_HTML)
print("Default ASU boundary           : OFF")
print("Boundary checkbox              : AVAILABLE")
print("Popup/hover                    : UNCHANGED")
print("Scientific result changed      : False")
print("\nNext                           : double-click NEW HTML.")
print("====================================================")
