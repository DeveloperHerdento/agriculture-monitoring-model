# ============================================================
# OUTPUT 4 / 40D01
# APSIM OIL PALM LOCAL PREFLIGHT & VARIANT AUDIT
# SIAK_AOI01
#
# Run directly in Jupyter.
#
# Purpose:
# 1) Detect APSIM Classic / APSIM Next Generation installations.
# 2) Detect OilPalm model files.
# 3) Avoid assuming that OilPalm exists in APSIM Next Generation.
# 4) Produce a small JSON audit for the next 40D step.
# ============================================================

from pathlib import Path
import os
import json

WORKDIR = Path(
    r"C:\Users\user\Documents\KERJA\SPATIAL DATA ANALYST INTERN\04_YIELD"
)

OUT_JSON = WORKDIR / (
    "40D01_APSIM_OILPALM_LOCAL_PREFLIGHT_SIAK_AOI01_V1.json"
)

print("====================================================")
print("40D01 — APSIM OIL PALM LOCAL PREFLIGHT")
print("====================================================")
print("Workdir:", WORKDIR)

# ------------------------------------------------------------
# Candidate APSIM roots only.
# Do NOT recursively scan the entire C: drive.
# ------------------------------------------------------------

candidate_roots = []

for base in [
    Path(r"C:\Program Files"),
    Path(r"C:\Program Files (x86)"),
    WORKDIR,
    Path.home() / "Documents",
    Path.home() / "Downloads",
]:
    if not base.exists():
        continue

    # Only direct APSIM-like child folders.
    try:
        for child in base.iterdir():
            name = child.name.lower()
            if child.is_dir() and (
                "apsim" in name
                or name == "apsim710"
                or name == "apsimx"
            ):
                candidate_roots.append(child)
    except PermissionError:
        pass

# Also include WORKDIR itself because files may have been placed directly there.
candidate_roots.append(WORKDIR)

# Unique existing roots
seen = set()
roots = []
for p in candidate_roots:
    try:
        key = str(p.resolve()).lower()
    except Exception:
        key = str(p).lower()

    if key not in seen and p.exists():
        seen.add(key)
        roots.append(p)

print("\nCandidate roots:")
for p in roots:
    print(" -", p)

# ------------------------------------------------------------
# Search known executable/model patterns inside candidate roots.
# ------------------------------------------------------------

patterns = {
    "classic_executables": [
        "ApsimModel.exe",
        "Apsim.exe",
        "ApsimUI.exe",
    ],
    "nextgen_executables": [
        "Models.exe",
        "ApsimNG.exe",
    ],
    "oilpalm_model_files": [
        "OilPalm.dll",
        "OilPalm.xml",
        "oilpalm.dll",
        "oilpalm.xml",
    ],
    "oilpalm_simulations": [
        "*OilPalm*.apsim",
        "*Oil Palm*.apsim",
        "*oilpalm*.apsim",
        "*OilPalm*.apsimx",
        "*oilpalm*.apsimx",
    ],
}

found = {k: [] for k in patterns}

for root in roots:
    # Limit recursion to APSIM candidate folders only.
    for category, pats in patterns.items():
        for pat in pats:
            try:
                for hit in root.rglob(pat):
                    s = str(hit)
                    if s not in found[category]:
                        found[category].append(s)
            except (PermissionError, OSError):
                pass

# ------------------------------------------------------------
# Classify each OilPalm file by likely APSIM variant.
# ------------------------------------------------------------

classic_oilpalm = []
nextgen_oilpalm = []
unknown_oilpalm = []

for f in found["oilpalm_model_files"] + found["oilpalm_simulations"]:
    low = f.lower()

    if (
        "apsim710" in low
        or "\\model\\" in low
        or low.endswith(".apsim")
    ):
        classic_oilpalm.append(f)

    elif (
        "apsimx" in low
        or low.endswith(".apsimx")
    ):
        nextgen_oilpalm.append(f)

    else:
        unknown_oilpalm.append(f)

classic_exe = found["classic_executables"]
nextgen_exe = found["nextgen_executables"]

# ------------------------------------------------------------
# Status
# ------------------------------------------------------------

if classic_exe and classic_oilpalm:
    status = "CLASSIC_OILPALM_LOCAL_ASSETS_FOUND"
    next_action = (
        "Proceed to 40D02: inspect the exact APSIM Classic OilPalm "
        "example/parameter contract and run one local reference smoke test."
    )

elif classic_oilpalm and not classic_exe:
    status = "CLASSIC_OILPALM_SOURCE_OR_MODEL_FOUND_BUT_NO_RUNNABLE_EXE"
    next_action = (
        "Need a runnable APSIM Classic 7.10 installation/build before "
        "40D02 smoke testing."
    )

elif nextgen_exe and not classic_oilpalm:
    status = "NEXTGEN_FOUND_BUT_CLASSIC_OILPALM_NOT_FOUND"
    next_action = (
        "Do not use Models.exe as an OilPalm benchmark yet. "
        "Obtain/locate APSIM Classic 7.10 OilPalm assets first."
    )

else:
    status = "APSIM_OILPALM_NOT_FOUND_LOCALLY"
    next_action = (
        "Install or obtain APSIM Classic 7.10 with its OilPalm model, "
        "then rerun this same preflight."
    )

report = {
    "gate": "40D01_APSIM_OILPALM_LOCAL_PREFLIGHT",
    "status": status,
    "candidate_roots": [str(x) for x in roots],
    "classic_executables": classic_exe,
    "nextgen_executables": nextgen_exe,
    "oilpalm_model_files": found["oilpalm_model_files"],
    "oilpalm_simulations": found["oilpalm_simulations"],
    "classic_oilpalm_assets": classic_oilpalm,
    "nextgen_oilpalm_assets": nextgen_oilpalm,
    "unknown_oilpalm_assets": unknown_oilpalm,
    "interpretation": (
        "For Output 4 benchmarking, OilPalm must be confirmed in the "
        "actual installed APSIM variant before any simulation is run."
    ),
    "next_action": next_action,
}

OUT_JSON.write_text(
    json.dumps(report, indent=2),
    encoding="utf-8"
)

print("\n===== DETECTION =====")
print("Classic executables :", len(classic_exe))
for x in classic_exe[:20]:
    print("  ", x)

print("\nNextGen executables :", len(nextgen_exe))
for x in nextgen_exe[:20]:
    print("  ", x)

print("\nOilPalm model files :", len(found["oilpalm_model_files"]))
for x in found["oilpalm_model_files"][:30]:
    print("  ", x)

print("\nOilPalm simulations :", len(found["oilpalm_simulations"]))
for x in found["oilpalm_simulations"][:30]:
    print("  ", x)

print("\n====================================================")
print("40D01 FINISHED")
print("====================================================")
print("Status:", status)
print("Next  :", next_action)
print("Audit :", OUT_JSON)
print("====================================================")
