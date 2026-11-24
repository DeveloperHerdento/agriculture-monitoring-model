# ============================================================
# OUTPUT 4 / 40D01B
# APSIM NEXT GENERATION + OILPALM LOCAL DETECTION
# SIAK_AOI01
#
# Run directly in Jupyter.
#
# Purpose:
# 1) Detect APSIM Next Generation 8099 installation.
# 2) Locate runnable executables.
# 3) Detect local OilPalm example/assets.
# 4) Write an audit JSON for 40D02.
# ============================================================

from pathlib import Path
import json
import subprocess
import sys

WORKDIR = Path(
    r"C:\Users\user\Documents\KERJA\SPATIAL DATA ANALYST INTERN\04_YIELD"
)

OUT_JSON = WORKDIR / (
    "40D01B_APSIM_NEXTGEN_OILPALM_LOCAL_DETECTION_SIAK_AOI01_V1.json"
)

print("====================================================")
print("40D01B — APSIM NEXT GENERATION + OILPALM DETECTION")
print("====================================================")
print("Python :", sys.executable)
print("Workdir:", WORKDIR)

known_root = Path(
    r"C:\Users\user\AppData\Local\Programs\APSIM2026.8.8099.0"
)

candidate_roots = []
if known_root.exists():
    candidate_roots.append(known_root)

for base in [
    Path.home() / "AppData" / "Local" / "Programs",
    Path(r"C:\Program Files"),
    Path(r"C:\Program Files (x86)"),
]:
    if not base.exists():
        continue
    try:
        for child in base.iterdir():
            if child.is_dir() and "apsim" in child.name.lower():
                candidate_roots.append(child)
    except (PermissionError, OSError):
        pass

roots = []
seen = set()
for p in candidate_roots:
    try:
        key = str(p.resolve()).lower()
    except Exception:
        key = str(p).lower()
    if key not in seen and p.exists():
        seen.add(key)
        roots.append(p)

print("\nCandidate APSIM roots:")
if roots:
    for p in roots:
        print(" -", p)
else:
    print(" - NONE")

exe_names = ["Models.exe", "ApsimNG.exe", "APSIM.exe", "Apsim.exe"]
executables = []
assemblies = []

for root in roots:
    for name in exe_names:
        try:
            for hit in root.rglob(name):
                s = str(hit)
                if s not in executables:
                    executables.append(s)
        except (PermissionError, OSError):
            pass

    for name in ["Models.dll", "ApsimNG.dll"]:
        try:
            for hit in root.rglob(name):
                s = str(hit)
                if s not in assemblies:
                    assemblies.append(s)
        except (PermissionError, OSError):
            pass

oilpalm_name_hits = []
for root in roots:
    for pattern in ["*OilPalm*", "*Oil Palm*", "*oilpalm*", "*oil_palm*"]:
        try:
            for hit in root.rglob(pattern):
                s = str(hit)
                if s not in oilpalm_name_hits:
                    oilpalm_name_hits.append(s)
        except (PermissionError, OSError):
            pass

oilpalm_content_hits = []
text_exts = {".apsimx", ".json", ".txt", ".md", ".xml", ".cs", ".yaml", ".yml"}

for root in roots:
    try:
        for f in root.rglob("*"):
            if not f.is_file() or f.suffix.lower() not in text_exts:
                continue
            try:
                if f.stat().st_size > 20_000_000:
                    continue
                txt = f.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            low = txt.lower()
            if "oilpalm" in low or "oil palm" in low:
                s = str(f)
                if s not in oilpalm_content_hits:
                    oilpalm_content_hits.append(s)
    except (PermissionError, OSError):
        pass

models_exe = next(
    (x for x in executables if Path(x).name.lower() == "models.exe"),
    None
)
apsimng_exe = next(
    (x for x in executables if Path(x).name.lower() == "apsimng.exe"),
    None
)

version_probe = {
    "attempted": False,
    "executable": None,
    "returncode": None,
    "stdout": None,
    "stderr": None,
}

if models_exe:
    version_probe["attempted"] = True
    version_probe["executable"] = models_exe
    try:
        cp = subprocess.run(
            [models_exe, "--version"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(Path(models_exe).parent),
        )
        version_probe["returncode"] = cp.returncode
        version_probe["stdout"] = (cp.stdout or "").strip()[:4000]
        version_probe["stderr"] = (cp.stderr or "").strip()[:4000]
    except Exception as e:
        version_probe["stderr"] = repr(e)

nextgen_installed = bool(models_exe or apsimng_exe or assemblies)
oilpalm_local = bool(oilpalm_name_hits or oilpalm_content_hits)

if nextgen_installed and oilpalm_local:
    status = "PASS_NEXTGEN_INSTALLED_OILPALM_LOCAL_ASSET_FOUND"
    next_action = (
        "Proceed to 40D02: inspect the detected OilPalm APSIMX/example "
        "and run one reference smoke test before Siak adaptation."
    )
elif nextgen_installed and not oilpalm_local:
    status = "PASS_NEXTGEN_INSTALLED_OILPALM_LOCAL_ASSET_NOT_FOUND"
    next_action = (
        "APSIM Next Generation is installed, but no local OilPalm example/"
        "text asset was detected. 40D02 should obtain or locate the official "
        "OilPalm example compatible with this installation before running."
    )
else:
    status = "FAIL_NEXTGEN_INSTALL_NOT_DETECTED"
    next_action = (
        "APSIM installation was not detected. Verify the installation path "
        "and rerun 40D01B."
    )

report = {
    "gate": "40D01B_APSIM_NEXTGEN_OILPALM_LOCAL_DETECTION",
    "status": status,
    "known_expected_root": str(known_root),
    "candidate_roots": [str(x) for x in roots],
    "executables": executables,
    "assemblies": assemblies,
    "models_exe": models_exe,
    "apsimng_exe": apsimng_exe,
    "version_probe": version_probe,
    "oilpalm_name_hits": oilpalm_name_hits,
    "oilpalm_content_hits": oilpalm_content_hits,
    "next_action": next_action,
}

OUT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")

print("\n===== APSIM DETECTION =====")
print("NextGen installed :", nextgen_installed)
print("Models.exe        :", models_exe)
print("ApsimNG.exe       :", apsimng_exe)
print("Assemblies        :", len(assemblies))

if version_probe["attempted"]:
    print("\nVersion probe:")
    print("  returncode:", version_probe["returncode"])
    if version_probe["stdout"]:
        print("  stdout    :", version_probe["stdout"])
    if version_probe["stderr"]:
        print("  stderr    :", version_probe["stderr"])

print("\n===== OILPALM DETECTION =====")
print("Name hits    :", len(oilpalm_name_hits))
for x in oilpalm_name_hits[:30]:
    print("  ", x)

print("Content hits :", len(oilpalm_content_hits))
for x in oilpalm_content_hits[:30]:
    print("  ", x)

print("\n====================================================")
print("40D01B FINISHED")
print("====================================================")
print("Status:", status)
print("Next  :", next_action)
print("Audit :", OUT_JSON)
print("====================================================")
