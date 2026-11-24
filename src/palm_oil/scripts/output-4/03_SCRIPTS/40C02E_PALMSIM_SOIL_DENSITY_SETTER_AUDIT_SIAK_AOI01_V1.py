# ============================================================
# OUTPUT 4 / 40C02E
# PALMSIM SOIL/DENSITY SETTER SEMANTICS AUDIT
# SIAK_AOI01
#
# RUN FROM JUPYTER VIA subprocess.
#
# PURPOSE
# - Resolve exactly HOW PALMSIM 2.5.2 expects:
#     planting density
#     soil depth
#     soil texture class
#     plant-available water
# - Identify public properties/setters and accepted texture classes.
# - Extract only source-backed evidence; do not guess.
#
# THIS STEP DOES NOT RUN THE 654-ASU BATCH.
# ============================================================

from pathlib import Path
import os
import sys
import json
import inspect
import re
import ast as pyast

import pandas as pd
import numpy as np

WORKDIR = Path(
    r"C:\Users\user\Documents\KERJA\SPATIAL DATA ANALYST INTERN\04_YIELD"
)
os.chdir(WORKDIR)

REG = WORKDIR / "40C01B_PALMSIM_SOURCE_REGISTRATION_SIAK_AOI01_V1.json"
OUT_JSON = WORKDIR / "40C02E_PALMSIM_SOIL_DENSITY_SETTER_AUDIT_SIAK_AOI01_V1.json"
OUT_TXT = WORKDIR / "40C02E_PALMSIM_SOIL_DENSITY_SETTER_AUDIT_SIAK_AOI01_V1.txt"

print("====================================================")
print("40C02E — PALMSIM SOIL / DENSITY SETTER AUDIT")
print("====================================================")
print("Python :", sys.executable)
print("Workdir:", WORKDIR)

if not REG.exists():
    raise FileNotFoundError(f"Missing registration JSON: {REG}")

registration = json.loads(REG.read_text(encoding="utf-8"))
working_root = Path(registration["working_root"])

palmsim_roots = list(working_root.rglob("palmsim-master"))
if not palmsim_roots:
    raise FileNotFoundError("Could not locate palmsim-master.")

palmsim_master = palmsim_roots[0]

for path in [str(palmsim_master / "PalmSim"), str(palmsim_master)]:
    if path not in sys.path:
        sys.path.insert(0, path)

from palmsim import PalmField

p = PalmField(year_of_planting=2015)
soil = p.soil

print("\nPalmField class:", type(p).__module__, type(p).__name__)
print("Soil class     :", type(soil).__module__, type(soil).__name__)

# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------

TOKENS = [
    "planting_density",
    "density",
    "soil_depth",
    "soil_texture",
    "texture",
    "plant_available_water",
    "available_water",
    "water_content",
    "sand",
    "silt",
    "clay",
]

def relevant(name):
    low = name.lower()
    return any(t in low for t in TOKENS)

def safe_repr(v, maxlen=500):
    try:
        s = repr(v)
    except Exception:
        s = f"<{type(v).__name__}>"
    return s[:maxlen]

# ------------------------------------------------------------
# 1. LIVE ATTRIBUTES / PUBLIC DESCRIPTORS
# ------------------------------------------------------------

live = []

for obj_name, obj in [("PalmField", p), ("PalmField.soil", soil)]:
    # vars
    try:
        for name, value in vars(obj).items():
            if relevant(name):
                live.append({
                    "object": obj_name,
                    "kind": "instance_attribute",
                    "name": name,
                    "path": f"{obj_name}.{name}",
                    "type": type(value).__name__,
                    "current_value": safe_repr(value),
                    "writable_hint": True,
                })
    except Exception:
        pass

    # class descriptors
    for name, descriptor in vars(type(obj)).items():
        if not relevant(name):
            continue

        writable = None
        getter = None
        setter = None

        if isinstance(descriptor, property):
            writable = descriptor.fset is not None
            getter = descriptor.fget.__name__ if descriptor.fget else None
            setter = descriptor.fset.__name__ if descriptor.fset else None

        live.append({
            "object": obj_name,
            "kind": type(descriptor).__name__,
            "name": name,
            "path": f"{obj_name}.{name}",
            "type": type(descriptor).__name__,
            "current_value": None,
            "writable_hint": writable,
            "getter": getter,
            "setter": setter,
        })

# Deduplicate
dedup = {}
for item in live:
    key = (item["path"], item["kind"])
    dedup[key] = item
live = list(dedup.values())

# ------------------------------------------------------------
# 2. CLASS SOURCE + RELEVANT FUNCTION/PROPERTY SNIPPETS
# ------------------------------------------------------------

class_reports = []

for obj_name, cls in [("PalmField", type(p)), ("Soil", type(soil))]:
    src_file = inspect.getsourcefile(cls)
    try:
        src = inspect.getsource(cls)
    except Exception:
        src = ""

    report = {
        "object": obj_name,
        "class": f"{cls.__module__}.{cls.__name__}",
        "source_file": src_file,
        "signature": None,
        "relevant_members": [],
        "relevant_source_lines": [],
    }

    try:
        report["signature"] = str(inspect.signature(cls))
    except Exception:
        report["signature"] = "UNAVAILABLE"

    # Members and source
    for name, member in vars(cls).items():
        if not relevant(name):
            continue

        m = {
            "name": name,
            "descriptor_type": type(member).__name__,
            "source": None,
        }

        try:
            if isinstance(member, property):
                pieces = []
                if member.fget:
                    pieces.append(inspect.getsource(member.fget))
                if member.fset:
                    pieces.append(inspect.getsource(member.fset))
                m["source"] = "\n".join(pieces)
            elif inspect.isfunction(member):
                m["source"] = inspect.getsource(member)
            else:
                m["source"] = safe_repr(member, 2000)
        except Exception as e:
            m["source"] = f"<source unavailable: {e!r}>"

        report["relevant_members"].append(m)

    for i, line in enumerate(src.splitlines(), start=1):
        if any(t in line.lower() for t in TOKENS):
            start = max(0, i - 3)
            end = min(len(src.splitlines()), i + 4)
            snippet = "\n".join(
                f"{j+1:04d}: {src.splitlines()[j]}"
                for j in range(start, end)
            )
            report["relevant_source_lines"].append({
                "class_relative_line": i,
                "snippet": snippet,
            })

    class_reports.append(report)

# ------------------------------------------------------------
# 3. MODULE-LEVEL CONSTANTS / DICTS / LISTS
# ------------------------------------------------------------

module_constants = []

modules = {
    "PalmField": sys.modules[type(p).__module__],
    "Soil": sys.modules[type(soil).__module__],
}

for mod_name, mod in modules.items():
    for name, value in vars(mod).items():
        if name.startswith("__"):
            continue

        # Capture relevant named constants OR containers containing texture words.
        name_rel = relevant(name)
        reprv = safe_repr(value, 4000)
        value_rel = any(
            word in reprv.lower()
            for word in [
                "sand", "silt", "clay", "loam", "peat",
                "coarse", "medium", "fine", "texture"
            ]
        )

        if name_rel or (
            isinstance(value, (dict, list, tuple, set))
            and value_rel
        ):
            module_constants.append({
                "module": mod.__name__,
                "name": name,
                "type": type(value).__name__,
                "value": reprv,
            })

# ------------------------------------------------------------
# 4. SOURCE-WIDE TEXT SEARCH FOR ACCEPTED CLASS NAMES / MAPPINGS
# ------------------------------------------------------------

source_hits = []

for py in sorted(palmsim_master.rglob("*.py")):
    text = py.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()

    for i, line in enumerate(lines, start=1):
        low = line.lower()
        if any(t in low for t in TOKENS):
            start = max(0, i - 2)
            end = min(len(lines), i + 3)
            snippet = "\n".join(
                f"{j+1:05d}: {lines[j]}"
                for j in range(start, end)
            )
            source_hits.append({
                "file": str(py.relative_to(palmsim_master)),
                "line": i,
                "snippet": snippet,
            })

# ------------------------------------------------------------
# 5. INFER ONLY FROM EXPLICIT CODE EVIDENCE
# ------------------------------------------------------------

all_text = json.dumps(
    {
        "live": live,
        "classes": class_reports,
        "constants": module_constants,
        "hits": source_hits,
    },
    ensure_ascii=False
).lower()

has_public_texture_property = any(
    x["path"] == "PalmField.soil.soil_texture_class"
    and x["kind"] == "property"
    for x in live
)

has_private_texture = any(
    x["path"] == "PalmField.soil._soil_texture_class"
    for x in live
)

has_density = any(
    x["path"] == "PalmField.planting_density"
    for x in live
)

has_depth = any(
    x["path"] == "PalmField.soil.soil_depth"
    for x in live
)

# Pull quoted string candidates from relevant Soil member source only.
texture_string_candidates = set()

for report in class_reports:
    if report["object"] != "Soil":
        continue

    for member in report["relevant_members"]:
        if "texture" not in member["name"].lower():
            continue

        src = member.get("source") or ""
        for match in re.findall(r"""['"]([^'"]+)['"]""", src):
            val = match.strip()
            if (
                1 <= len(val) <= 80
                and not val.startswith("_")
                and any(
                    k in val.lower()
                    for k in [
                        "sand", "loam", "clay", "silt",
                        "peat", "coarse", "medium", "fine"
                    ]
                )
            ):
                texture_string_candidates.add(val)

texture_string_candidates = sorted(texture_string_candidates)

if has_density and has_depth and (
    has_public_texture_property or texture_string_candidates
):
    status = "PASS"
    next_gate = (
        "40C03 run P00-P04 on the same Siak ASU using only confirmed setters; "
        "if a supported texture-class setter exists, map SoilGrids texture to "
        "that class explicitly and keep the mapping documented."
    )
elif has_density and has_depth:
    status = "PASS_DENSITY_DEPTH_ONLY"
    next_gate = (
        "40C03 run density/depth sensitivity using confirmed setters; "
        "keep SoilGrids sand/silt/clay contextual because no safe PALMSIM "
        "texture setter/mapping is evidenced."
    )
else:
    status = "CHECK"
    next_gate = (
        "Do not activate sensitivity scenarios until the setter contract is resolved."
    )

# ------------------------------------------------------------
# 6. EXPORT
# ------------------------------------------------------------

report = {
    "gate": "40C02E",
    "status": status,
    "palmsim_master": str(palmsim_master),
    "live_relevant_paths": live,
    "class_reports": class_reports,
    "module_constants": module_constants,
    "source_hits": source_hits,
    "gate_checks": {
        "planting_density_path_found": has_density,
        "soil_depth_path_found": has_depth,
        "public_soil_texture_property_found": has_public_texture_property,
        "private_soil_texture_attribute_found": has_private_texture,
        "texture_string_candidates": texture_string_candidates,
    },
    "policy": [
        "Never set a private texture attribute unless source code proves the intended setter semantics.",
        "Do not feed sand/silt/clay percentages directly unless PALMSIM explicitly accepts them.",
        "Density and soil depth remain scenario assumptions, not observed estate parameters.",
        "SoilGrids can remain contextual even if PALMSIM cannot safely ingest its texture fractions.",
    ],
    "next_gate": next_gate,
}

OUT_JSON.write_text(
    json.dumps(report, indent=2),
    encoding="utf-8"
)

with open(OUT_TXT, "w", encoding="utf-8") as f:
    f.write("40C02E PALMSIM SOIL / DENSITY SETTER AUDIT\n")
    f.write("=" * 80 + "\n")
    f.write(f"Status: {status}\n")
    f.write(f"PALMSIM master: {palmsim_master}\n\n")

    f.write("LIVE RELEVANT PATHS\n")
    f.write("-" * 80 + "\n")
    for x in live:
        f.write(
            f"{x['path']} | {x['kind']} | "
            f"writable={x.get('writable_hint')} | "
            f"value={x.get('current_value')}\n"
        )

    f.write("\nTEXTURE STRING CANDIDATES\n")
    f.write("-" * 80 + "\n")
    if texture_string_candidates:
        for x in texture_string_candidates:
            f.write(x + "\n")
    else:
        f.write("NONE\n")

    f.write("\nRELEVANT MEMBER SOURCE\n")
    f.write("-" * 80 + "\n")
    for cr in class_reports:
        f.write(f"\n[{cr['class']}]\n")
        for m in cr["relevant_members"]:
            f.write(f"\n--- {m['name']} ({m['descriptor_type']}) ---\n")
            f.write((m["source"] or "") + "\n")

    f.write("\nNEXT GATE\n")
    f.write("-" * 80 + "\n")
    f.write(next_gate + "\n")

# ------------------------------------------------------------
# 7. COMPACT CONSOLE
# ------------------------------------------------------------

print("\nExact live paths:")
for x in live:
    print(
        f"  {x['path']} | {x['kind']} | "
        f"writable={x.get('writable_hint')} | "
        f"value={x.get('current_value')}"
    )

print("\nTexture-class candidates from source:")
if texture_string_candidates:
    for x in texture_string_candidates:
        print("  -", x)
else:
    print("  - NONE")

print("\nGate checks:")
print("  planting density found       :", has_density)
print("  soil depth found             :", has_depth)
print("  public texture property      :", has_public_texture_property)
print("  private texture attr         :", has_private_texture)
print("  explicit texture candidates  :", len(texture_string_candidates))

print("\n====================================================")
print("40C02E FINISHED")
print("====================================================")
print("Status:", status)
print("Audit TXT :", OUT_TXT)
print("Audit JSON:", OUT_JSON)
print("Next:", next_gate)
print("====================================================")
