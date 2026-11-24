# ============================================================
# OUTPUT 4 / 40C02A
# PALMSIM 2.5.2 API CONTRACT + REFERENCE EXAMPLE DISCOVERY
# SIAK_AOI01
#
# RUN FROM JUPYTER VIA subprocess.
#
# PURPOSE
# - Inspect the registered PALMSIM 2.5.2 WORKING source.
# - Extract exact package structure, imports, model classes/functions,
#   weather schema clues, run/integration calls, and yield/output clues.
# - Identify the best official example/notebook to use for the smoke test.
# - DO NOT GUESS THE API.
#
# THIS STEP DOES NOT MODIFY PALMSIM AND DOES NOT RUN SIAK YET.
# ============================================================

from pathlib import Path
import os
import sys
import json
import re
import ast
import traceback

WORKDIR = Path(
    r"C:\Users\user\Documents\KERJA\SPATIAL DATA ANALYST INTERN\04_YIELD"
)
os.chdir(WORKDIR)

REG = WORKDIR / "40C01B_PALMSIM_SOURCE_REGISTRATION_SIAK_AOI01_V1.json"

OUT_JSON = WORKDIR / "40C02A_PALMSIM_API_CONTRACT_AUDIT_SIAK_AOI01_V1.json"
OUT_TXT = WORKDIR / "40C02A_PALMSIM_API_CONTRACT_AUDIT_SIAK_AOI01_V1.txt"

print("====================================================")
print("40C02A — PALMSIM API CONTRACT / EXAMPLE DISCOVERY")
print("====================================================")
print("Python :", sys.executable)
print("Workdir:", WORKDIR)

if not REG.exists():
    raise FileNotFoundError(f"Missing registration JSON: {REG}")

registration = json.loads(REG.read_text(encoding="utf-8"))
working_root = Path(registration["working_root"])

if not working_root.exists():
    raise FileNotFoundError(f"Working PALMSIM source not found: {working_root}")

print("Working source:", working_root)

# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------

def safe_read(path):
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""

def rel(path):
    try:
        return str(path.relative_to(working_root))
    except Exception:
        return str(path)

def compact(s, n=500):
    s = re.sub(r"\s+", " ", str(s)).strip()
    return s[:n]

# ------------------------------------------------------------
# 1. INVENTORY
# ------------------------------------------------------------

py_files = sorted(working_root.rglob("*.py"))
nb_files = sorted(working_root.rglob("*.ipynb"))
csv_files = sorted(working_root.rglob("*.csv"))
txt_files = sorted(working_root.rglob("*.txt"))

print("\nInventory:")
print("  Python files :", len(py_files))
print("  Notebooks    :", len(nb_files))
print("  CSV files    :", len(csv_files))
print("  TXT files    :", len(txt_files))

# ------------------------------------------------------------
# 2. PYTHON AST CONTRACT
# ------------------------------------------------------------

module_records = []
all_classes = []
all_functions = []
all_imports = []

for py in py_files:
    text = safe_read(py)
    rec = {
        "file": rel(py),
        "imports": [],
        "classes": [],
        "functions": [],
        "top_level_assignments": [],
        "interesting_lines": [],
    }

    try:
        tree = ast.parse(text)
    except Exception as e:
        rec["parse_error"] = repr(e)
        module_records.append(rec)
        continue

    for node in tree.body:
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
            rec["imports"].extend(names)
            all_imports.extend(names)

        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            names = [a.name for a in node.names]
            entry = f"from {mod} import {', '.join(names)}"
            rec["imports"].append(entry)
            all_imports.append(entry)

        elif isinstance(node, ast.ClassDef):
            bases = []
            for b in node.bases:
                try:
                    bases.append(ast.unparse(b))
                except Exception:
                    bases.append(type(b).__name__)

            methods = [
                x.name for x in node.body
                if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef))
            ]

            item = {
                "name": node.name,
                "bases": bases,
                "methods": methods,
                "file": rel(py),
            }
            rec["classes"].append(item)
            all_classes.append(item)

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = [a.arg for a in node.args.args]
            item = {
                "name": node.name,
                "args": args,
                "file": rel(py),
            }
            rec["functions"].append(item)
            all_functions.append(item)

        elif isinstance(node, ast.Assign):
            targets = []
            for t in node.targets:
                try:
                    targets.append(ast.unparse(t))
                except Exception:
                    pass
            if targets:
                rec["top_level_assignments"].extend(targets[:10])

    # Key lines around likely model contract words.
    keywords = [
        "PalmSim", "Model", "Engine", "run(", "integrat",
        "weather", "radiation", "rain", "precip", "temperature",
        "humidity", "wind", "soil", "sand", "clay", "silt",
        "density", "planting", "age", "ffb", "bunch", "yield",
        "dt", "latitude", "__version__",
    ]

    for i, line in enumerate(text.splitlines(), start=1):
        low = line.lower()
        if any(k.lower() in low for k in keywords):
            clean = line.strip()
            if clean and not clean.startswith("#"):
                rec["interesting_lines"].append({
                    "line": i,
                    "text": clean[:500]
                })

    # Avoid giant reports.
    rec["interesting_lines"] = rec["interesting_lines"][:120]
    module_records.append(rec)

# ------------------------------------------------------------
# 3. NOTEBOOK CODE EXTRACTION
# ------------------------------------------------------------

notebook_records = []

nb_keywords = [
    "import ", "palmsim", "model", "engine", "run",
    "weather", "radiation", "rain", "temperature",
    "humidity", "wind", "soil", "density", "latitude",
    "yield", "bunch", "ffb", "north", "sumatra",
]

for nb in nb_files:
    rec = {
        "file": rel(nb),
        "code_cell_count": 0,
        "interesting_code": [],
        "score": 0,
    }

    try:
        doc = json.loads(nb.read_text(encoding="utf-8", errors="ignore"))
    except Exception as e:
        rec["error"] = repr(e)
        notebook_records.append(rec)
        continue

    cells = doc.get("cells", [])
    for idx, cell in enumerate(cells):
        if cell.get("cell_type") != "code":
            continue

        rec["code_cell_count"] += 1
        src = "".join(cell.get("source", []))
        low = src.lower()

        matched = [k for k in nb_keywords if k.lower() in low]
        if matched:
            rec["score"] += len(set(matched))

            # Keep focused, useful code only.
            lines = []
            for line in src.splitlines():
                llow = line.lower()
                if any(k.lower() in llow for k in nb_keywords):
                    lines.append(line.rstrip())

            if lines:
                rec["interesting_code"].append({
                    "cell": idx,
                    "code": "\n".join(lines[:35])[:5000],
                })

    rec["interesting_code"] = rec["interesting_code"][:15]
    notebook_records.append(rec)

# Rank notebooks for likely reference example.
ranked_notebooks = sorted(
    notebook_records,
    key=lambda x: (
        "north" in x["file"].lower() or "sumatra" in x["file"].lower(),
        "example" in x["file"].lower(),
        x.get("score", 0)
    ),
    reverse=True
)

# ------------------------------------------------------------
# 4. WEATHER / INPUT FILE SCHEMA DISCOVERY
# ------------------------------------------------------------

data_file_records = []

for f in csv_files + txt_files:
    text = safe_read(f)

    # Focus only on likely data/config/example files.
    name_low = f.name.lower()
    if not any(k in name_low for k in [
        "weather", "climate", "input", "example",
        "north", "sumatra", "parameter", "site"
    ]):
        continue

    lines = text.splitlines()
    data_file_records.append({
        "file": rel(f),
        "first_lines": lines[:20],
    })

# ------------------------------------------------------------
# 5. EXACT SEARCH FOR KNOWN IMPORTANT CONTRACT MARKERS
# ------------------------------------------------------------

search_terms = [
    ".items()",
    ".iteritems()",
    "dt =",
    "dt=",
    "latitude",
    "rainfall",
    "radiation",
    "temperature",
    "humidity",
    "wind",
    "sand",
    "clay",
    "silt",
    "density",
    "FFB",
    "yield",
    "__version__",
]

term_hits = {term: [] for term in search_terms}

for py in py_files:
    text = safe_read(py)
    for line_no, line in enumerate(text.splitlines(), start=1):
        for term in search_terms:
            if term.lower() in line.lower():
                term_hits[term].append({
                    "file": rel(py),
                    "line": line_no,
                    "text": line.strip()[:500]
                })

for term in term_hits:
    term_hits[term] = term_hits[term][:40]

# ------------------------------------------------------------
# 6. DETERMINE BEST NEXT CONTRACT
# ------------------------------------------------------------

best_notebook = ranked_notebooks[0]["file"] if ranked_notebooks else None

# Class names that look most model-like.
model_like_classes = [
    c for c in all_classes
    if any(k in c["name"].lower() for k in [
        "palm", "model", "engine", "sim"
    ])
]

run_like_functions = [
    f for f in all_functions
    if any(k in f["name"].lower() for k in [
        "run", "simulate", "integrate", "step", "update"
    ])
]

# Successful contract audit means we found enough source structure
# to write a non-guessed smoke-test adapter.
contract_ready = bool(
    len(py_files) > 0
    and (
        len(model_like_classes) > 0
        or len(run_like_functions) > 0
        or best_notebook is not None
    )
)

status = "PASS" if contract_ready else "CHECK"

report = {
    "gate": "40C02A",
    "status": status,
    "working_root": str(working_root),
    "inventory": {
        "python_files": len(py_files),
        "notebooks": len(nb_files),
        "csv_files": len(csv_files),
        "txt_files": len(txt_files),
    },
    "model_like_classes": model_like_classes[:30],
    "run_like_functions": run_like_functions[:30],
    "all_classes": all_classes[:100],
    "all_functions": all_functions[:150],
    "ranked_reference_notebooks": [
        {
            "file": x["file"],
            "score": x.get("score", 0),
            "code_cell_count": x.get("code_cell_count", 0),
        }
        for x in ranked_notebooks[:15]
    ],
    "best_reference_notebook": best_notebook,
    "module_records": module_records,
    "notebook_records": notebook_records,
    "data_file_records": data_file_records,
    "term_hits": term_hits,
    "next_gate": (
        "40C02B build exact PALMSIM adapter from discovered official API, "
        "then run official/reference smoke test and 1 SIAK ASU baseline "
        "twice for deterministic equality."
        if status == "PASS"
        else
        "Inspect source manually before writing adapter; do not guess PALMSIM API."
    ),
}

OUT_JSON.write_text(
    json.dumps(report, indent=2),
    encoding="utf-8"
)

# Human-readable compact report.
with open(OUT_TXT, "w", encoding="utf-8") as f:
    f.write("40C02A PALMSIM API CONTRACT AUDIT\n")
    f.write("=" * 70 + "\n")
    f.write(f"Status: {status}\n")
    f.write(f"Working root: {working_root}\n")
    f.write(f"Python files: {len(py_files)}\n")
    f.write(f"Notebooks: {len(nb_files)}\n")
    f.write(f"Best reference notebook: {best_notebook}\n\n")

    f.write("MODEL-LIKE CLASSES\n")
    f.write("-" * 70 + "\n")
    for c in model_like_classes[:30]:
        f.write(
            f"{c['name']} | {c['file']} | "
            f"methods={', '.join(c['methods'][:25])}\n"
        )

    f.write("\nRUN-LIKE FUNCTIONS\n")
    f.write("-" * 70 + "\n")
    for fn in run_like_functions[:30]:
        f.write(
            f"{fn['name']}({', '.join(fn['args'])}) | {fn['file']}\n"
        )

    f.write("\nTOP REFERENCE NOTEBOOKS\n")
    f.write("-" * 70 + "\n")
    for nb in ranked_notebooks[:15]:
        f.write(
            f"score={nb.get('score',0):3d} | {nb['file']}\n"
        )

    f.write("\nKEY TERM HITS\n")
    f.write("-" * 70 + "\n")
    for term in [
        "__version__", "dt =", "latitude", "rainfall",
        "radiation", "temperature", "humidity", "wind",
        "sand", "clay", "silt", "density", "FFB", "yield"
    ]:
        f.write(f"\n[{term}]\n")
        for hit in term_hits.get(term, [])[:12]:
            f.write(
                f"{hit['file']}:{hit['line']} | {hit['text']}\n"
            )

print("\nContract discovery:")
print("  Model-like classes :", len(model_like_classes))
print("  Run-like functions :", len(run_like_functions))
print("  Best ref notebook  :", best_notebook)

print("\nTop candidate notebooks:")
for x in ranked_notebooks[:8]:
    print(f"  score={x.get('score',0):3d} | {x['file']}")

print("\n====================================================")
print("40C02A FINISHED")
print("====================================================")
print("Status:", status)
print("JSON report:", OUT_JSON)
print("Text report:", OUT_TXT)
print("Next:", report["next_gate"])
print("====================================================")
