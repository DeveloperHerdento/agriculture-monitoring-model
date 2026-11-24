# ============================================================
# OUTPUT 4 / 40C02B
# PALMSIM OFFICIAL REFERENCE SMOKE TEST + DETERMINISM CHECK
# SIAK_AOI01
#
# RUN FROM JUPYTER VIA subprocess.
#
# PURPOSE
# 1) Locate official/reference PALMSIM notebook:
#       examples/02 Potential Production.ipynb
# 2) Execute it twice in isolated output files.
# 3) Verify both runs finish successfully.
# 4) Compare normalized cell outputs for deterministic equality.
# 5) Extract the exact API code snippets needed for the next Siak adapter.
#
# THIS STEP DOES NOT MODIFY THE ORIGINAL NOTEBOOK.
# ============================================================

from pathlib import Path
import os
import sys
import json
import re
import shutil
import subprocess
import hashlib
import traceback

WORKDIR = Path(
    r"C:\Users\user\Documents\KERJA\SPATIAL DATA ANALYST INTERN\04_YIELD"
)
os.chdir(WORKDIR)

REG = WORKDIR / "40C01B_PALMSIM_SOURCE_REGISTRATION_SIAK_AOI01_V1.json"

RUN_DIR = WORKDIR / "40C02B_REFERENCE_SMOKE_TEST"
RUN_DIR.mkdir(parents=True, exist_ok=True)

OUT_QC = WORKDIR / "40C02B_PALMSIM_REFERENCE_SMOKE_TEST_QC_SIAK_AOI01_V1.json"
OUT_SNIPPETS = WORKDIR / "40C02B_PALMSIM_REFERENCE_API_SNIPPETS_SIAK_AOI01_V1.txt"

print("====================================================")
print("40C02B — PALMSIM OFFICIAL REFERENCE SMOKE TEST")
print("====================================================")
print("Python :", sys.executable)
print("Workdir:", WORKDIR)

if not REG.exists():
    raise FileNotFoundError(f"Missing registration JSON: {REG}")

registration = json.loads(REG.read_text(encoding="utf-8"))
working_root = Path(registration["working_root"])

if not working_root.exists():
    raise FileNotFoundError(f"Working PALMSIM source missing: {working_root}")

# ------------------------------------------------------------
# 1. LOCATE REFERENCE NOTEBOOK
# ------------------------------------------------------------

candidates = list(working_root.rglob("02 Potential Production.ipynb"))

if not candidates:
    raise FileNotFoundError(
        "Could not find '02 Potential Production.ipynb' in working source."
    )

reference_nb = candidates[0]
example_dir = reference_nb.parent

print("\nReference notebook:")
print(" ", reference_nb)

# ------------------------------------------------------------
# 2. CHECK JUPYTER EXECUTION TOOL
# ------------------------------------------------------------

jupyter_exe = shutil.which("jupyter")

if jupyter_exe is None:
    # Same environment often exposes jupyter-nbconvert directly.
    nbconvert_exe = shutil.which("jupyter-nbconvert")
else:
    nbconvert_exe = jupyter_exe

if nbconvert_exe is None:
    raise RuntimeError(
        "Could not locate jupyter/jupyter-nbconvert in current environment."
    )

print("Jupyter executable:", nbconvert_exe)

# ------------------------------------------------------------
# 3. EXECUTE TWICE — ORIGINAL NOTEBOOK IS NEVER OVERWRITTEN
# ------------------------------------------------------------

run_outputs = []
run_logs = []

for run_no in [1, 2]:

    out_name = f"40C02B_Potential_Production_EXECUTED_RUN{run_no}.ipynb"
    out_path = RUN_DIR / out_name

    if out_path.exists():
        out_path.unlink()

    if Path(nbconvert_exe).name.lower().startswith("jupyter-nbconvert"):
        cmd = [
            nbconvert_exe,
            "--to", "notebook",
            "--execute",
            str(reference_nb),
            "--output", out_name,
            "--output-dir", str(RUN_DIR),
            "--ExecutePreprocessor.timeout=900",
        ]
    else:
        cmd = [
            nbconvert_exe,
            "nbconvert",
            "--to", "notebook",
            "--execute",
            str(reference_nb),
            "--output", out_name,
            "--output-dir", str(RUN_DIR),
            "--ExecutePreprocessor.timeout=900",
        ]

    print(f"\nExecuting official reference run {run_no}/2 ...")

    proc = subprocess.run(
        cmd,
        cwd=str(example_dir),
        capture_output=True,
        text=True,
    )

    log = {
        "run": run_no,
        "returncode": proc.returncode,
        "stdout": proc.stdout[-10000:],
        "stderr": proc.stderr[-10000:],
        "output_notebook": str(out_path),
    }
    run_logs.append(log)

    print("  return code:", proc.returncode)

    if proc.stdout.strip():
        print("  stdout tail:")
        print(proc.stdout[-2500:])

    if proc.stderr.strip():
        print("  stderr tail:")
        print(proc.stderr[-2500:])

    if proc.returncode != 0:
        raise RuntimeError(
            f"Reference PALMSIM notebook failed on run {run_no}.\n"
            f"STDERR:\n{proc.stderr[-8000:]}"
        )

    if not out_path.exists():
        raise FileNotFoundError(
            f"Execution returned 0 but output notebook is missing: {out_path}"
        )

    run_outputs.append(out_path)

# ------------------------------------------------------------
# 4. NORMALIZE NOTEBOOK OUTPUTS FOR DETERMINISM CHECK
# ------------------------------------------------------------

def normalize_notebook_outputs(nb_path):
    doc = json.loads(nb_path.read_text(encoding="utf-8", errors="ignore"))

    normalized = []

    for idx, cell in enumerate(doc.get("cells", [])):
        if cell.get("cell_type") != "code":
            continue

        src = "".join(cell.get("source", []))

        outs = []
        for out in cell.get("outputs", []):
            out_type = out.get("output_type")

            if out_type == "stream":
                text = "".join(out.get("text", []))
                # Remove obvious timestamps / durations only.
                text = re.sub(
                    r"\b\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?\b",
                    "<TIMESTAMP>",
                    text
                )
                outs.append({
                    "type": "stream",
                    "name": out.get("name"),
                    "text": text.strip()
                })

            elif out_type in ["execute_result", "display_data"]:
                data = out.get("data", {})
                keep = {}

                for k, v in data.items():
                    # Compare textual / JSON-like outputs. Skip image binaries.
                    if k.startswith("image/"):
                        continue
                    keep[k] = v

                outs.append({
                    "type": out_type,
                    "data": keep
                })

            elif out_type == "error":
                outs.append({
                    "type": "error",
                    "ename": out.get("ename"),
                    "evalue": out.get("evalue"),
                    "traceback": out.get("traceback", []),
                })

        normalized.append({
            "cell": idx,
            "source": src,
            "outputs": outs
        })

    return normalized

norm1 = normalize_notebook_outputs(run_outputs[0])
norm2 = normalize_notebook_outputs(run_outputs[1])

json1 = json.dumps(norm1, sort_keys=True, ensure_ascii=False)
json2 = json.dumps(norm2, sort_keys=True, ensure_ascii=False)

hash1 = hashlib.sha256(json1.encode("utf-8")).hexdigest()
hash2 = hashlib.sha256(json2.encode("utf-8")).hexdigest()

deterministic_equal = bool(json1 == json2)

print("\nDeterminism check:")
print("  Run 1 normalized SHA256:", hash1)
print("  Run 2 normalized SHA256:", hash2)
print("  Exact normalized equality:", deterministic_equal)

# ------------------------------------------------------------
# 5. EXTRACT EXACT API SNIPPETS FROM REFERENCE NOTEBOOK
# ------------------------------------------------------------

ref_doc = json.loads(
    reference_nb.read_text(encoding="utf-8", errors="ignore")
)

keywords = [
    "import",
    "Model",
    "Engine",
    "Palm",
    "weather",
    "rain",
    "radiation",
    "temperature",
    "humidity",
    "wind",
    "soil",
    "density",
    "latitude",
    "dt",
    "run",
    "integr",
    "yield",
    "bunch",
    "ffb",
    "source",
]

interesting_cells = []

for idx, cell in enumerate(ref_doc.get("cells", [])):
    if cell.get("cell_type") != "code":
        continue

    src = "".join(cell.get("source", []))
    low = src.lower()

    score = sum(1 for k in keywords if k.lower() in low)

    if score >= 2:
        interesting_cells.append({
            "cell": idx,
            "score": score,
            "source": src.rstrip()
        })

interesting_cells.sort(key=lambda x: (-x["score"], x["cell"]))

with open(OUT_SNIPPETS, "w", encoding="utf-8") as f:
    f.write("40C02B PALMSIM REFERENCE API SNIPPETS\n")
    f.write("=" * 78 + "\n")
    f.write(f"Reference notebook: {reference_nb}\n")
    f.write(f"Deterministic normalized equality: {deterministic_equal}\n\n")

    for item in interesting_cells:
        f.write(
            f"\n--- CELL {item['cell']} | SCORE {item['score']} ---\n"
        )
        f.write(item["source"])
        f.write("\n")

# Also print a compact version directly to Jupyter output.
print("\nKey reference API cells:")
for item in interesting_cells[:8]:
    print(
        f"\n--- CELL {item['cell']} | SCORE {item['score']} ---"
    )
    # Keep stdout compact.
    lines = item["source"].splitlines()
    for line in lines[:30]:
        print(line)
    if len(lines) > 30:
        print("... [truncated in console; full snippet saved to TXT]")

# ------------------------------------------------------------
# 6. FINAL GATE
# ------------------------------------------------------------

official_reference_pass = bool(
    all(x["returncode"] == 0 for x in run_logs)
)

if official_reference_pass and deterministic_equal:
    status = "PASS"
    next_gate = (
        "40C02C build exact Siak adapter from captured reference API; "
        "run 1 eligible ASU x P00_BASE twice and compare model outputs."
    )
elif official_reference_pass:
    status = "PASS_REFERENCE_CHECK_DETERMINISM"
    next_gate = (
        "Inspect differing reference outputs before Siak batch execution. "
        "Do not batch yet."
    )
else:
    status = "CHECK"
    next_gate = "Fix PALMSIM reference environment before Siak adapter."

qc = {
    "gate": "40C02B",
    "status": status,
    "working_root": str(working_root),
    "reference_notebook": str(reference_nb),
    "run_logs": run_logs,
    "run1_normalized_sha256": hash1,
    "run2_normalized_sha256": hash2,
    "deterministic_normalized_equality": deterministic_equal,
    "reference_execution_pass": official_reference_pass,
    "api_snippet_file": str(OUT_SNIPPETS),
    "next_gate": next_gate,
}

OUT_QC.write_text(
    json.dumps(qc, indent=2),
    encoding="utf-8"
)

print("\n====================================================")
print("40C02B FINISHED")
print("====================================================")
print("Status:", status)
print("Reference execution PASS:", official_reference_pass)
print("Deterministic equality:", deterministic_equal)
print("Executed notebook 1:", run_outputs[0])
print("Executed notebook 2:", run_outputs[1])
print("API snippets:", OUT_SNIPPETS)
print("QC JSON:", OUT_QC)
print("Next:", next_gate)
print("====================================================")
