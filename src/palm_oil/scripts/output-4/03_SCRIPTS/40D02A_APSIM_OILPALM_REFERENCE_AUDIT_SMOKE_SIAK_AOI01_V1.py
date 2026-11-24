# ============================================================
# OUTPUT 4 / 40D02A
# APSIM NEXT GEN OILPALM — OFFICIAL REFERENCE AUDIT + SMOKE TEST
# SIAK_AOI01
#
# Run directly in Jupyter.
#
# What this does:
# - Audits the installed official OilPalm.apsimx example.
# - Lists simulations and referenced files via Models.exe.
# - Parses model structure (Clock, Weather, OilPalm nodes, Reports).
# - Copies the official example into isolated RUN1/RUN2 folders.
# - Runs the official example twice, single-threaded.
# - Checks deterministic equality of exported CSV outputs.
# - Does NOT modify the installed APSIM example.
# ============================================================

from pathlib import Path
import json
import shutil
import subprocess
import hashlib
import csv
import sys
import time
from collections import Counter

WORKDIR = Path(
    r"C:\Users\user\Documents\KERJA\SPATIAL DATA ANALYST INTERN\04_YIELD"
)

APSIM_ROOT = Path(
    r"C:\Users\user\AppData\Local\Programs\APSIM2026.8.8099.0"
)
MODELS_EXE = APSIM_ROOT / "bin" / "Models.exe"
OILPALM_EXAMPLE = APSIM_ROOT / "Examples" / "OilPalm.apsimx"

OUT_ROOT = WORKDIR / "40D02A_APSIM_OILPALM_REFERENCE_SMOKE_SIAK_AOI01_V1"
RUN1 = OUT_ROOT / "RUN1"
RUN2 = OUT_ROOT / "RUN2"

AUDIT_JSON = WORKDIR / "40D02A_APSIM_OILPALM_REFERENCE_AUDIT_SIAK_AOI01_V1.json"
DETERMINISM_JSON = WORKDIR / "40D02A_APSIM_OILPALM_REFERENCE_DETERMINISM_SIAK_AOI01_V1.json"

print("====================================================")
print("40D02A — APSIM NEXT GEN OILPALM REFERENCE SMOKE")
print("====================================================")
print("Python      :", sys.executable)
print("Models.exe  :", MODELS_EXE)
print("OilPalm ref :", OILPALM_EXAMPLE)
print("Workdir     :", WORKDIR)

# ------------------------------------------------------------
# Hard preflight
# ------------------------------------------------------------

if not MODELS_EXE.exists():
    raise FileNotFoundError(f"Models.exe not found: {MODELS_EXE}")

if not OILPALM_EXAMPLE.exists():
    raise FileNotFoundError(f"OilPalm example not found: {OILPALM_EXAMPLE}")

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def run_cmd(args, cwd=None, timeout=900):
    t0 = time.perf_counter()
    cp = subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    elapsed = time.perf_counter() - t0
    return {
        "returncode": cp.returncode,
        "stdout": (cp.stdout or "").strip(),
        "stderr": (cp.stderr or "").strip(),
        "elapsed_sec": elapsed,
    }

def walk_models(node, path=""):
    if isinstance(node, dict):
        name = str(node.get("Name", ""))
        node_path = f"{path}/{name}" if name else path
        yield node_path, node
        for child in node.get("Children", []) or []:
            yield from walk_models(child, node_path)
    elif isinstance(node, list):
        for item in node:
            yield from walk_models(item, path)

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def normalized_csv_hash(path):
    """
    Normalize line endings and strip trailing whitespace only.
    Keeps data values/order intact.
    """
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    norm = "\n".join(lines).strip() + "\n"
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()

# ------------------------------------------------------------
# Version / CLI metadata
# ------------------------------------------------------------

version = run_cmd([str(MODELS_EXE), "--version"], cwd=MODELS_EXE.parent, timeout=60)
list_sims = run_cmd(
    [str(MODELS_EXE), str(OILPALM_EXAMPLE), "--list-enabled-simulations"],
    cwd=OILPALM_EXAMPLE.parent,
    timeout=120,
)
list_refs = run_cmd(
    [str(MODELS_EXE), str(OILPALM_EXAMPLE), "--list-referenced-filenames"],
    cwd=OILPALM_EXAMPLE.parent,
    timeout=120,
)
file_version = run_cmd(
    [str(MODELS_EXE), str(OILPALM_EXAMPLE), "--file-version-number"],
    cwd=OILPALM_EXAMPLE.parent,
    timeout=120,
)

print("\n===== CLI AUDIT =====")
print("APSIM version:")
print(version["stdout"] or version["stderr"])
print("\nEnabled simulations:")
print(list_sims["stdout"] or list_sims["stderr"] or "(none printed)")
print("\nReferenced filenames:")
print(list_refs["stdout"] or list_refs["stderr"] or "(none printed)")
print("\nAPSIMX file version:")
print(file_version["stdout"] or file_version["stderr"] or "(none printed)")

# ------------------------------------------------------------
# Parse official OilPalm APSIMX
# ------------------------------------------------------------

with open(OILPALM_EXAMPLE, "r", encoding="utf-8-sig") as f:
    apsim = json.load(f)

nodes = list(walk_models(apsim))
types = [str(n.get("$type", "")) for _, n in nodes]
type_counts = Counter(types)

simulations = []
clocks = []
weathers = []
oilpalm_nodes = []
reports = []
soils = []
managers = []

for pth, n in nodes:
    t = str(n.get("$type", ""))
    low_t = t.lower()
    low_name = str(n.get("Name", "")).lower()

    if "models.core.simulation" in low_t:
        simulations.append({
            "path": pth,
            "name": n.get("Name"),
            "enabled": n.get("Enabled"),
        })

    if "models.clock" in low_t:
        clocks.append({
            "path": pth,
            "name": n.get("Name"),
            "start": n.get("Start"),
            "end": n.get("End"),
        })

    if "models.climate.weather" in low_t:
        weathers.append({
            "path": pth,
            "name": n.get("Name"),
            "filename": n.get("FileName"),
        })

    if "oilpalm" in low_t or "oil palm" in low_t or "oilpalm" in low_name or "oil palm" in low_name:
        # keep scalar/simple fields only in summary
        simple = {}
        for k, v in n.items():
            if k in {"Children"}:
                continue
            if isinstance(v, (str, int, float, bool)) or v is None:
                simple[k] = v
        oilpalm_nodes.append({
            "path": pth,
            "type": t,
            "name": n.get("Name"),
            "simple_fields": simple,
        })

    if "models.report" in low_t:
        reports.append({
            "path": pth,
            "name": n.get("Name"),
            "variables": n.get("VariableNames"),
            "events": n.get("EventNames"),
        })

    if "models.soils.soil" in low_t and n.get("Name"):
        soils.append({
            "path": pth,
            "name": n.get("Name"),
            "type": t,
        })

    if "models.manager" in low_t:
        managers.append({
            "path": pth,
            "name": n.get("Name"),
        })

audit = {
    "gate": "40D02A_APSIM_OILPALM_REFERENCE_AUDIT",
    "apsim_version_probe": version,
    "oilpalm_example": str(OILPALM_EXAMPLE),
    "oilpalm_example_sha256": sha256_file(OILPALM_EXAMPLE),
    "apsimx_top_level_version": apsim.get("Version"),
    "apsimx_top_level_apsim_version": apsim.get("ApsimVersion"),
    "cli_enabled_simulations": list_sims,
    "cli_referenced_filenames": list_refs,
    "cli_file_version": file_version,
    "parsed_simulations": simulations,
    "parsed_clocks": clocks,
    "parsed_weathers": weathers,
    "parsed_oilpalm_nodes": oilpalm_nodes,
    "parsed_reports": reports,
    "parsed_soils": soils,
    "parsed_managers": managers,
    "node_count": len(nodes),
    "model_type_counts": dict(type_counts),
}

AUDIT_JSON.write_text(json.dumps(audit, indent=2, default=str), encoding="utf-8")

print("\n===== STRUCTURE AUDIT =====")
print("Total model nodes :", len(nodes))
print("Simulation nodes  :", len(simulations))
for x in simulations:
    print("  ", x)

print("Clock nodes       :", len(clocks))
for x in clocks:
    print("  ", x)

print("Weather nodes     :", len(weathers))
for x in weathers:
    print("  ", x)

print("OilPalm hits      :", len(oilpalm_nodes))
for x in oilpalm_nodes[:20]:
    print("  ", x["path"], "|", x["type"])

print("Report nodes      :", len(reports))
for x in reports:
    nvars = len(x["variables"] or [])
    print("  ", x["path"], "| variables:", nvars)

print("Soil nodes        :", len(soils))
for x in soils[:20]:
    print("  ", x)

print("Manager nodes     :", len(managers))
for x in managers[:20]:
    print("  ", x)

# ------------------------------------------------------------
# Isolated reference smoke test, twice
# ------------------------------------------------------------

for d in [RUN1, RUN2]:
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True, exist_ok=True)
    shutil.copy2(OILPALM_EXAMPLE, d / "OilPalm_REFERENCE_8099.apsimx")

print("\n===== RUN 1 =====")
run1_file = RUN1 / "OilPalm_REFERENCE_8099.apsimx"
r1 = run_cmd(
    [
        str(MODELS_EXE),
        str(run1_file),
        "--single-threaded",
        "--csv",
        "--verbose",
    ],
    cwd=RUN1,
    timeout=1800,
)
print("Return code :", r1["returncode"])
print("Elapsed sec :", round(r1["elapsed_sec"], 2))
if r1["stdout"]:
    print(r1["stdout"][-5000:])
if r1["stderr"]:
    print("STDERR:")
    print(r1["stderr"][-5000:])

print("\n===== RUN 2 =====")
run2_file = RUN2 / "OilPalm_REFERENCE_8099.apsimx"
r2 = run_cmd(
    [
        str(MODELS_EXE),
        str(run2_file),
        "--single-threaded",
        "--csv",
        "--verbose",
    ],
    cwd=RUN2,
    timeout=1800,
)
print("Return code :", r2["returncode"])
print("Elapsed sec :", round(r2["elapsed_sec"], 2))
if r2["stdout"]:
    print(r2["stdout"][-5000:])
if r2["stderr"]:
    print("STDERR:")
    print(r2["stderr"][-5000:])

# ------------------------------------------------------------
# Collect output CSVs and compare
# ------------------------------------------------------------

csv1 = sorted([p for p in RUN1.glob("*.csv") if p.is_file()])
csv2 = sorted([p for p in RUN2.glob("*.csv") if p.is_file()])

by_name1 = {p.name: p for p in csv1}
by_name2 = {p.name: p for p in csv2}

common = sorted(set(by_name1) & set(by_name2))
only1 = sorted(set(by_name1) - set(by_name2))
only2 = sorted(set(by_name2) - set(by_name1))

comparisons = []
all_equal = True

for name in common:
    p1 = by_name1[name]
    p2 = by_name2[name]

    h1 = normalized_csv_hash(p1)
    h2 = normalized_csv_hash(p2)
    eq = h1 == h2

    if not eq:
        all_equal = False

    # Count rows / columns from first file where possible.
    rows = None
    cols = None
    header = None
    try:
        with open(p1, "r", encoding="utf-8-sig", errors="replace", newline="") as f:
            reader = csv.reader(f)
            data = list(reader)
        rows = max(len(data) - 1, 0) if data else 0
        header = data[0] if data else []
        cols = len(header)
    except Exception:
        pass

    comparisons.append({
        "file": name,
        "normalized_sha256_run1": h1,
        "normalized_sha256_run2": h2,
        "equal": eq,
        "rows_approx": rows,
        "columns": cols,
        "header": header,
    })

if only1 or only2:
    all_equal = False

status = (
    "PASS"
    if r1["returncode"] == 0
    and r2["returncode"] == 0
    and len(common) > 0
    and all_equal
    else "REVIEW"
)

det = {
    "gate": "40D02A_APSIM_OILPALM_REFERENCE_SMOKE",
    "status": status,
    "run1": r1,
    "run2": r2,
    "run1_csv_files": [p.name for p in csv1],
    "run2_csv_files": [p.name for p in csv2],
    "common_csv_files": common,
    "only_run1": only1,
    "only_run2": only2,
    "csv_comparisons": comparisons,
    "all_common_csv_equal": all_equal,
}

DETERMINISM_JSON.write_text(json.dumps(det, indent=2, default=str), encoding="utf-8")

print("\n===== OUTPUT / DETERMINISM CHECK =====")
print("RUN1 CSV count      :", len(csv1))
print("RUN2 CSV count      :", len(csv2))
print("Common CSV count    :", len(common))
print("Only RUN1           :", only1)
print("Only RUN2           :", only2)
print("All common CSV equal:", all_equal)

for x in comparisons:
    print(
        f"  {x['file']} | rows≈{x['rows_approx']} | "
        f"cols={x['columns']} | equal={x['equal']}"
    )

print("\n====================================================")
print("40D02A FINISHED")
print("====================================================")
print("Status       :", status)
print("Run1 RC      :", r1["returncode"])
print("Run2 RC      :", r2["returncode"])
print("CSV equal    :", all_equal)
print("Audit JSON   :", AUDIT_JSON)
print("QC JSON      :", DETERMINISM_JSON)

if status == "PASS":
    print("Next         : 40D02B OilPalm parameter/output contract audit.")
else:
    print("Next         : Review the printed APSIM error/output before 40D02B.")
print("====================================================")
