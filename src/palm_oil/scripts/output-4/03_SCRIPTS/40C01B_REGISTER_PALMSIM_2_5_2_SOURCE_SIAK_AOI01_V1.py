# ============================================================
# OUTPUT 4 / 40C01B
# PALMSIM 2.5.2 SOURCE REGISTER + WORKING COPY PREP
# SIAK_AOI01
#
# RUN FROM JUPYTER VIA subprocess.
#
# EXPECTED USER ACTION BEFORE RUN:
# - Download the official WUR archive: palmsim_master_0.zip
# - Leave it in either:
#   1) Downloads
#   2) 04_YIELD
#
# THIS SCRIPT WILL:
# 1) Find palmsim_master_0.zip
# 2) Keep an immutable original extracted copy
# 3) Make a separate working copy
# 4) Apply the known pandas compatibility patch:
#       .iteritems() -> .items()
# 5) Discover likely PALMSIM package/root structure
# 6) Produce a registration JSON for 40C02
#
# IT DOES NOT RUN PALMSIM YET.
# ============================================================

from pathlib import Path
import os
import sys
import json
import shutil
import zipfile
import hashlib
import re

WORKDIR = Path(
    r"C:\Users\user\Documents\KERJA\SPATIAL DATA ANALYST INTERN\04_YIELD"
)
DOWNLOADS = Path.home() / "Downloads"

ORIGINAL_ROOT = WORKDIR / "PALMSIM_2.5.2_ORIGINAL"
WORKING_ROOT = WORKDIR / "PALMSIM_2.5.2_WORKING"

OUT_REG = WORKDIR / "40C01B_PALMSIM_SOURCE_REGISTRATION_SIAK_AOI01_V1.json"
OUT_PATCH = WORKDIR / "40C01B_PALMSIM_PATCH_REPORT_SIAK_AOI01_V1.txt"

ARCHIVE_NAME = "palmsim_master_0.zip"

print("====================================================")
print("40C01B — PALMSIM 2.5.2 SOURCE REGISTER")
print("====================================================")
print("Python :", sys.executable)
print("Workdir:", WORKDIR)

# ------------------------------------------------------------
# 1. LOCATE OFFICIAL ARCHIVE
# ------------------------------------------------------------

candidates = [
    WORKDIR / ARCHIVE_NAME,
    DOWNLOADS / ARCHIVE_NAME,
]

# Also tolerate browser-renamed copies such as palmsim_master_0 (1).zip
for root in [WORKDIR, DOWNLOADS]:
    if root.exists():
        candidates.extend(sorted(root.glob("palmsim_master_0*.zip")))

# Deduplicate while preserving order
seen = set()
ordered = []
for p in candidates:
    rp = str(p.resolve()) if p.exists() else str(p)
    if rp not in seen:
        ordered.append(p)
        seen.add(rp)

archive = next((p for p in ordered if p.exists() and p.is_file()), None)

if archive is None:
    print("\nARCHIVE NOT FOUND.")
    print("Download the official WUR file 'palmsim_master_0.zip' first,")
    print("then place it in:")
    print("  -", DOWNLOADS)
    print("  OR")
    print("  -", WORKDIR)
    print("\nThen rerun this script.")
    sys.exit(2)

print("\nArchive found:", archive)

# ------------------------------------------------------------
# 2. HASH FOR PROVENANCE
# ------------------------------------------------------------

sha256 = hashlib.sha256()
with open(archive, "rb") as f:
    for chunk in iter(lambda: f.read(1024 * 1024), b""):
        sha256.update(chunk)

archive_sha256 = sha256.hexdigest()

print("Archive SHA256:", archive_sha256)

# ------------------------------------------------------------
# 3. EXTRACT IMMUTABLE ORIGINAL COPY
# ------------------------------------------------------------

if ORIGINAL_ROOT.exists():
    print("\nOriginal extracted copy already exists; preserving it:")
    print(" ", ORIGINAL_ROOT)
else:
    print("\nExtracting immutable original copy...")
    ORIGINAL_ROOT.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(archive, "r") as zf:
        zf.extractall(ORIGINAL_ROOT)

    print("  extracted:", ORIGINAL_ROOT)

# ------------------------------------------------------------
# 4. CREATE / REFRESH WORKING COPY
# ------------------------------------------------------------

if WORKING_ROOT.exists():
    print("\nRefreshing working copy...")
    shutil.rmtree(WORKING_ROOT)

shutil.copytree(ORIGINAL_ROOT, WORKING_ROOT)

print("Working copy:", WORKING_ROOT)

# ------------------------------------------------------------
# 5. APPLY KNOWN PANDAS COMPATIBILITY PATCH
# ------------------------------------------------------------

patch_hits = []

for py in WORKING_ROOT.rglob("*.py"):
    try:
        text = py.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            text = py.read_text(encoding="latin-1")
        except Exception:
            continue
    except Exception:
        continue

    count = text.count(".iteritems()")
    if count > 0:
        patched = text.replace(".iteritems()", ".items()")
        py.write_text(patched, encoding="utf-8")
        patch_hits.append({
            "file": str(py),
            "replacements": int(count),
        })

print("\nCompatibility patch:")
print("  files patched :", len(patch_hits))
print("  replacements  :", sum(x["replacements"] for x in patch_hits))

# ------------------------------------------------------------
# 6. DISCOVER STRUCTURE
# ------------------------------------------------------------

all_py = list(WORKING_ROOT.rglob("*.py"))
all_ipynb = list(WORKING_ROOT.rglob("*.ipynb"))
init_files = list(WORKING_ROOT.rglob("__init__.py"))

candidate_package_dirs = sorted(
    {p.parent for p in init_files},
    key=lambda p: len(p.parts)
)

candidate_model_files = []
patterns = [
    r"palm",
    r"model",
    r"sim",
    r"yield",
]

for py in all_py:
    low = py.name.lower()
    if any(re.search(pat, low) for pat in patterns):
        candidate_model_files.append(py)

# Search for version marker.
version_hits = []
for py in all_py:
    try:
        text = py.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue

    if "__version__" in text or "2.5.2" in text or "2.4.5" in text:
        for line in text.splitlines():
            if "__version__" in line or "2.5.2" in line or "2.4.5" in line:
                version_hits.append({
                    "file": str(py),
                    "line": line.strip()[:300],
                })

# Look for likely example/weather content.
example_candidates = []
for p in WORKING_ROOT.rglob("*"):
    if not p.is_file():
        continue
    low = p.name.lower()
    if any(k in low for k in [
        "example", "north", "sumatra", "weather", "climate"
    ]):
        example_candidates.append(str(p))

registration = {
    "gate": "40C01B",
    "status": "PASS" if len(all_py) > 0 else "CHECK",
    "official_release_expected": "2.5.2",
    "archive_name": archive.name,
    "archive_path": str(archive),
    "archive_sha256": archive_sha256,
    "original_root": str(ORIGINAL_ROOT),
    "working_root": str(WORKING_ROOT),
    "python_files_found": len(all_py),
    "notebooks_found": len(all_ipynb),
    "package_dirs": [str(p) for p in candidate_package_dirs[:30]],
    "candidate_model_files": [str(p) for p in candidate_model_files[:50]],
    "example_weather_candidates": example_candidates[:50],
    "version_markers": version_hits[:50],
    "compatibility_patch": {
        "rule": ".iteritems() -> .items()",
        "files_patched": len(patch_hits),
        "total_replacements": sum(x["replacements"] for x in patch_hits),
        "details": patch_hits,
    },
    "provenance_policy": (
        "Original extracted source preserved separately; "
        "only the working copy is patched."
    ),
    "next_gate": (
        "40C02 inspect registered working source and run "
        "1-ASU x baseline smoke test + deterministic repeat."
    ),
}

OUT_REG.write_text(
    json.dumps(registration, indent=2),
    encoding="utf-8"
)

with open(OUT_PATCH, "w", encoding="utf-8") as f:
    f.write("40C01B PALMSIM 2.5.2 PATCH REPORT\n")
    f.write("=" * 60 + "\n")
    f.write(f"Archive: {archive}\n")
    f.write(f"SHA256: {archive_sha256}\n")
    f.write(f"Original root: {ORIGINAL_ROOT}\n")
    f.write(f"Working root: {WORKING_ROOT}\n\n")
    f.write("Compatibility patch: .iteritems() -> .items()\n")
    f.write(f"Files patched: {len(patch_hits)}\n")
    f.write(
        f"Total replacements: "
        f"{sum(x['replacements'] for x in patch_hits)}\n\n"
    )
    for item in patch_hits:
        f.write(
            f"{item['replacements']} replacement(s): "
            f"{item['file']}\n"
        )

print("\nSource structure:")
print("  Python files :", len(all_py))
print("  Notebooks    :", len(all_ipynb))
print("  Package dirs :", len(candidate_package_dirs))
print("  Version hits :", len(version_hits))

print("\n====================================================")
print("40C01B FINISHED")
print("====================================================")
print("Status:", registration["status"])
print("Original source:", ORIGINAL_ROOT)
print("Working source :", WORKING_ROOT)
print("Registration   :", OUT_REG)
print("Patch report   :", OUT_PATCH)
print("Next:", registration["next_gate"])
print("====================================================")
