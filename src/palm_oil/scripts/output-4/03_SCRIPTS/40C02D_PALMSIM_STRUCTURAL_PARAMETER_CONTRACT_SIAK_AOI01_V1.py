# ============================================================
# OUTPUT 4 / 40C02D
# PALMSIM STRUCTURAL PARAMETER CONTRACT FREEZE
# SIAK_AOI01
#
# RUN FROM JUPYTER VIA subprocess.
#
# PURPOSE
# 1) Inspect the LIVE PALMSIM 2.5.2 object used in 40C02C.
# 2) Discover exact writable/internal paths related to:
#       - planting / palm density
#       - soil depth / rooting depth
#       - soil texture: sand / silt / clay
#       - latitude
#       - weather series
#       - water / soil-water state
# 3) Cross-check those paths against source-code evidence.
# 4) Freeze a parameter-contract report for the next sensitivity runner.
#
# IMPORTANT
# - This script DOES NOT invent parameter names.
# - This script DOES NOT run the 654-ASU batch.
# - This script DOES NOT activate P00-P04 yet.
# - It only freezes the exact PALMSIM parameter contract first.
# ============================================================

from pathlib import Path
import os
import sys
import json
import re
import inspect
import ast as pyast
from collections import defaultdict

import numpy as np
import pandas as pd

WORKDIR = Path(
    r"C:\Users\user\Documents\KERJA\SPATIAL DATA ANALYST INTERN\04_YIELD"
)
os.chdir(WORKDIR)

REG = WORKDIR / "40C01B_PALMSIM_SOURCE_REGISTRATION_SIAK_AOI01_V1.json"
SELECTED = WORKDIR / "40C02C_PALMSIM_SIAK_SMOKE_SELECTED_ASU_SIAK_AOI01_V1.csv"

OUT_JSON = WORKDIR / "40C02D_PALMSIM_STRUCTURAL_PARAMETER_CONTRACT_SIAK_AOI01_V1.json"
OUT_TXT = WORKDIR / "40C02D_PALMSIM_STRUCTURAL_PARAMETER_CONTRACT_SIAK_AOI01_V1.txt"
OUT_CSV = WORKDIR / "40C02D_PALMSIM_PARAMETER_PATHS_SIAK_AOI01_V1.csv"

print("====================================================")
print("40C02D — PALMSIM STRUCTURAL PARAMETER CONTRACT")
print("====================================================")
print("Python :", sys.executable)
print("Workdir:", WORKDIR)

for p in [REG, SELECTED]:
    if not p.exists():
        raise FileNotFoundError(f"Missing required input: {p}")

registration = json.loads(REG.read_text(encoding="utf-8"))
working_root = Path(registration["working_root"])

palmsim_roots = list(working_root.rglob("palmsim-master"))
if not palmsim_roots:
    raise FileNotFoundError("Could not locate palmsim-master.")

palmsim_master = palmsim_roots[0]

for p in [str(palmsim_master / "PalmSim"), str(palmsim_master)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from palmsim import PalmField

selected = pd.read_csv(SELECTED)
if len(selected) != 1:
    raise ValueError(f"Expected exactly one selected smoke ASU, got {len(selected)}")

year_of_planting = int(selected.loc[0, "YEAR_OF_PLANTING_PROXY"])
latitude = float(selected.loc[0, "ASU_LATITUDE"])

p = PalmField(year_of_planting=year_of_planting)

print("\nPalmField instantiated: PASS")
print("Year-of-planting proxy:", year_of_planting)
print("ASU latitude          :", latitude)

# ------------------------------------------------------------
# 1. SAFE LIVE-OBJECT INTROSPECTION
# ------------------------------------------------------------

KEYWORDS = {
    "density": ["density", "population", "palms_per", "plant_density"],
    "soil_depth": ["soil_depth", "depth", "root_depth", "rooting_depth"],
    "sand": ["sand"],
    "silt": ["silt"],
    "clay": ["clay"],
    "texture": ["texture"],
    "latitude": ["latitude", "lat"],
    "rainfall": ["rain", "rainfall", "precip"],
    "radiation": ["radiation", "solar"],
    "water": ["water", "soilwater", "soil_water", "moisture", "stress"],
}

def category_for(name):
    low = name.lower()
    cats = []
    for cat, keys in KEYWORDS.items():
        if any(k in low for k in keys):
            cats.append(cat)
    return cats

def primitive(v):
    return isinstance(
        v,
        (
            str, int, float, bool, np.integer, np.floating,
            type(None), pd.Series, np.ndarray, list, tuple, dict
        )
    )

records = []
visited = set()

def walk_object(obj, prefix="PalmField", depth=0, max_depth=3):
    oid = id(obj)
    if oid in visited:
        return
    visited.add(oid)

    try:
        attrs = vars(obj)
    except Exception:
        return

    for name, value in attrs.items():
        if name.startswith("__"):
            continue

        path = f"{prefix}.{name}"
        cats = category_for(name)

        value_type = type(value).__name__
        scalar_value = None
        if isinstance(value, (str, int, float, bool, np.integer, np.floating, type(None))):
            try:
                scalar_value = value.item() if hasattr(value, "item") else value
            except Exception:
                scalar_value = str(value)

        if cats:
            records.append({
                "SOURCE": "LIVE_OBJECT",
                "CATEGORY": ",".join(cats),
                "PATH": path,
                "ATTRIBUTE": name,
                "VALUE_TYPE": value_type,
                "CURRENT_VALUE": scalar_value,
                "DEPTH": depth,
                "EVIDENCE": f"Existing attribute in vars({prefix})",
            })

        if depth < max_depth and not primitive(value):
            mod = type(value).__module__.lower()
            # Recurse primarily into PALMSIM-owned objects.
            if "palmsim" in mod or mod == "__main__":
                walk_object(value, path, depth + 1, max_depth)

walk_object(p)

# Also inspect public @property / class attributes without calling arbitrary methods.
def inspect_class_properties(obj, prefix="PalmField", depth=0, max_depth=2, seen=None):
    if seen is None:
        seen = set()
    cls = type(obj)
    key = (id(obj), cls)
    if key in seen:
        return
    seen.add(key)

    for name, descriptor in vars(cls).items():
        if name.startswith("_"):
            continue

        cats = category_for(name)
        if cats:
            writable = False
            desc_type = type(descriptor).__name__

            if isinstance(descriptor, property):
                writable = descriptor.fset is not None
            elif not callable(descriptor):
                writable = True

            records.append({
                "SOURCE": "CLASS_DESCRIPTOR",
                "CATEGORY": ",".join(cats),
                "PATH": f"{prefix}.{name}",
                "ATTRIBUTE": name,
                "VALUE_TYPE": desc_type,
                "CURRENT_VALUE": None,
                "DEPTH": depth,
                "EVIDENCE": f"class descriptor; writable={writable}",
            })

    if depth < max_depth:
        try:
            attrs = vars(obj)
        except Exception:
            attrs = {}
        for name, value in attrs.items():
            if name.startswith("_") or primitive(value):
                continue
            if "palmsim" in type(value).__module__.lower():
                inspect_class_properties(
                    value,
                    f"{prefix}.{name}",
                    depth + 1,
                    max_depth,
                    seen
                )

inspect_class_properties(p)

# ------------------------------------------------------------
# 2. SOURCE-CODE AST + TEXT EVIDENCE
# ------------------------------------------------------------

py_files = sorted(palmsim_master.rglob("*.py"))
source_hits = []
self_assignments = []

for py in py_files:
    text = py.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()

    # Text hits.
    for i, line in enumerate(lines, start=1):
        low = line.lower()
        cats = []
        for cat, keys in KEYWORDS.items():
            if any(k in low for k in keys):
                cats.append(cat)
        if cats:
            source_hits.append({
                "FILE": str(py.relative_to(palmsim_master)),
                "LINE": i,
                "CATEGORY": ",".join(cats),
                "TEXT": line.strip()[:500],
            })

    # Exact "self.<attribute>" assignments via AST.
    try:
        tree = pyast.parse(text)
    except Exception:
        continue

    class StackVisitor(pyast.NodeVisitor):
        def __init__(self):
            self.class_name = None
            self.function_name = None

        def visit_ClassDef(self, node):
            prev = self.class_name
            self.class_name = node.name
            self.generic_visit(node)
            self.class_name = prev

        def visit_FunctionDef(self, node):
            prev = self.function_name
            self.function_name = node.name
            self.generic_visit(node)
            self.function_name = prev

        def visit_Assign(self, node):
            for target in node.targets:
                try:
                    target_txt = pyast.unparse(target)
                except Exception:
                    continue

                if target_txt.startswith("self."):
                    cats = category_for(target_txt)
                    if cats:
                        try:
                            value_txt = pyast.unparse(node.value)
                        except Exception:
                            value_txt = ""
                        self_assignments.append({
                            "FILE": str(py.relative_to(palmsim_master)),
                            "LINE": getattr(node, "lineno", None),
                            "CLASS": self.class_name,
                            "FUNCTION": self.function_name,
                            "TARGET": target_txt,
                            "CATEGORY": ",".join(cats),
                            "VALUE_EXPR": value_txt[:500],
                        })
            self.generic_visit(node)

        def visit_AnnAssign(self, node):
            try:
                target_txt = pyast.unparse(node.target)
            except Exception:
                target_txt = ""

            if target_txt.startswith("self."):
                cats = category_for(target_txt)
                if cats:
                    try:
                        value_txt = pyast.unparse(node.value) if node.value else ""
                    except Exception:
                        value_txt = ""
                    self_assignments.append({
                        "FILE": str(py.relative_to(palmsim_master)),
                        "LINE": getattr(node, "lineno", None),
                        "CLASS": self.class_name,
                        "FUNCTION": self.function_name,
                        "TARGET": target_txt,
                        "CATEGORY": ",".join(cats),
                        "VALUE_EXPR": value_txt[:500],
                    })
            self.generic_visit(node)

    StackVisitor().visit(tree)

# ------------------------------------------------------------
# 3. CONSTRUCTOR SIGNATURES
# ------------------------------------------------------------

signatures = []

classes_to_check = [PalmField]

# Add nested PALMSIM-owned classes from live object.
for value in vars(p).values():
    if not primitive(value) and "palmsim" in type(value).__module__.lower():
        classes_to_check.append(type(value))

seen_classes = set()

for cls in classes_to_check:
    if cls in seen_classes:
        continue
    seen_classes.add(cls)
    try:
        sig = str(inspect.signature(cls))
    except Exception:
        sig = "UNAVAILABLE"

    signatures.append({
        "class": f"{cls.__module__}.{cls.__name__}",
        "signature": sig,
    })

# ------------------------------------------------------------
# 4. BUILD CATEGORY SUMMARY
# ------------------------------------------------------------

df_live = pd.DataFrame(records)

if len(df_live):
    df_live = df_live.drop_duplicates(
        subset=["SOURCE", "CATEGORY", "PATH", "EVIDENCE"]
    ).reset_index(drop=True)
else:
    df_live = pd.DataFrame(columns=[
        "SOURCE", "CATEGORY", "PATH", "ATTRIBUTE",
        "VALUE_TYPE", "CURRENT_VALUE", "DEPTH", "EVIDENCE"
    ])

df_live.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")

category_summary = {}

for category in KEYWORDS:
    live_matches = []
    if len(df_live):
        live_matches = df_live[
            df_live["CATEGORY"].str.contains(category, regex=False, na=False)
        ]["PATH"].drop_duplicates().tolist()

    ast_matches = [
        x for x in self_assignments
        if category in x["CATEGORY"].split(",")
    ]

    txt_matches = [
        x for x in source_hits
        if category in x["CATEGORY"].split(",")
    ]

    category_summary[category] = {
        "live_object_paths": live_matches[:50],
        "self_assignment_evidence": ast_matches[:50],
        "source_text_hits": txt_matches[:80],
    }

# ------------------------------------------------------------
# 5. EXACT KNOWN CONTRACT FROM PREVIOUS SMOKE TEST
# ------------------------------------------------------------

known_contract = {
    "PalmField.year_of_planting": {
        "status": "CONFIRMED",
        "evidence": "40C02B official notebook + 40C02C successful Siak run"
    },
    "PalmField.latitude": {
        "status": "CONFIRMED",
        "evidence": "40C02C live attribute and successful assignment"
    },
    "PalmField.weather.radiation_series": {
        "status": "CONFIRMED",
        "evidence": "40C02B official notebook + 40C02C successful Siak run"
    },
    "PalmField.weather.rainfall_series": {
        "status": "CONFIRMED",
        "evidence": "40C02B official notebook + 40C02C successful Siak run"
    },
    "PalmField.run(duration=...)": {
        "status": "CONFIRMED",
        "evidence": "40C02B and 40C02C deterministic executions"
    },
}

# ------------------------------------------------------------
# 6. GATE LOGIC
# ------------------------------------------------------------

def count_paths(category):
    return len(category_summary[category]["live_object_paths"])

density_found = count_paths("density") > 0
depth_found = count_paths("soil_depth") > 0
sand_found = count_paths("sand") > 0
silt_found = count_paths("silt") > 0
clay_found = count_paths("clay") > 0

texture_all_found = sand_found and silt_found and clay_found

if density_found and depth_found and texture_all_found:
    status = "PASS"
    next_gate = (
        "40C03 activate P00-P04 on the same Siak ASU using only the "
        "confirmed parameter paths, verify response/plausibility, then batch."
    )
elif density_found and (depth_found or texture_all_found):
    status = "PASS_PARTIAL_CONTRACT"
    next_gate = (
        "Review the printed exact parameter paths. Freeze only parameters "
        "explicitly supported by PALMSIM; unsupported SoilGrids variables "
        "remain contextual rather than forced into the model."
    )
else:
    status = "CHECK"
    next_gate = (
        "Do not activate P00-P04 yet. Inspect exact source evidence because "
        "the assumed density/soil parameter interface is not fully exposed."
    )

# ------------------------------------------------------------
# 7. EXPORT
# ------------------------------------------------------------

report = {
    "gate": "40C02D",
    "status": status,
    "palmsim_master": str(palmsim_master),
    "known_confirmed_contract": known_contract,
    "constructor_signatures": signatures,
    "category_summary": category_summary,
    "self_assignment_evidence": self_assignments,
    "live_object_path_count": int(len(df_live)),
    "gate_checks": {
        "density_path_found": density_found,
        "soil_depth_path_found": depth_found,
        "sand_path_found": sand_found,
        "silt_path_found": silt_found,
        "clay_path_found": clay_found,
        "full_texture_contract_found": texture_all_found,
    },
    "scientific_policy": [
        "Do not create arbitrary attributes that PALMSIM does not use.",
        "A SoilGrids variable is only fed into PALMSIM if the exact source contract supports it.",
        "Unsupported soil variables remain contextual or APSIM inputs.",
        "Plant density and soil depth remain scenario assumptions unless observed locally.",
        "Age-derived planting year remains a proxy.",
        "No actual FFB validation claim.",
    ],
    "next_gate": next_gate,
}

OUT_JSON.write_text(
    json.dumps(report, indent=2),
    encoding="utf-8"
)

with open(OUT_TXT, "w", encoding="utf-8") as f:
    f.write("40C02D PALMSIM STRUCTURAL PARAMETER CONTRACT\n")
    f.write("=" * 78 + "\n")
    f.write(f"Status: {status}\n")
    f.write(f"PALMSIM master: {palmsim_master}\n\n")

    f.write("CONFIRMED FROM 40C02B/C\n")
    f.write("-" * 78 + "\n")
    for k, v in known_contract.items():
        f.write(f"{k}: {v['status']} | {v['evidence']}\n")

    f.write("\nLIVE PARAMETER PATHS BY CATEGORY\n")
    f.write("-" * 78 + "\n")
    for cat in KEYWORDS:
        f.write(f"\n[{cat}]\n")
        paths = category_summary[cat]["live_object_paths"]
        if paths:
            for path in paths:
                f.write(f"  {path}\n")
        else:
            f.write("  NONE FOUND\n")

    f.write("\nSOURCE SELF-ASSIGNMENT EVIDENCE\n")
    f.write("-" * 78 + "\n")
    for item in self_assignments:
        f.write(
            f"{item['CATEGORY']} | {item['FILE']}:{item['LINE']} | "
            f"{item['CLASS']}.{item['FUNCTION']} | "
            f"{item['TARGET']} = {item['VALUE_EXPR']}\n"
        )

    f.write("\nNEXT GATE\n")
    f.write("-" * 78 + "\n")
    f.write(next_gate + "\n")

# ------------------------------------------------------------
# 8. COMPACT CONSOLE OUTPUT
# ------------------------------------------------------------

print("\nConfirmed operational contract:")
for k in known_contract:
    print("  CONFIRMED:", k)

print("\nStructural parameter discovery:")

for cat in ["density", "soil_depth", "sand", "silt", "clay", "texture", "water"]:
    paths = category_summary[cat]["live_object_paths"]
    print(f"\n  [{cat}]")
    if paths:
        for path in paths[:12]:
            print("   -", path)
    else:
        print("   - NONE FOUND")

print("\nGate checks:")
print("  density path found     :", density_found)
print("  soil-depth path found  :", depth_found)
print("  sand path found        :", sand_found)
print("  silt path found        :", silt_found)
print("  clay path found        :", clay_found)
print("  full texture contract  :", texture_all_found)

print("\n====================================================")
print("40C02D FINISHED")
print("====================================================")
print("Status:", status)
print("Parameter paths CSV:", OUT_CSV)
print("Contract TXT:", OUT_TXT)
print("Contract JSON:", OUT_JSON)
print("Next:", next_gate)
print("====================================================")
