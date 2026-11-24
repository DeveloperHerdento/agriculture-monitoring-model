# ============================================================
# OUTPUT 4 / 40I02B
# WEB DISPLAY CONTRACT FREEZE — SIAK_AOI01
#
# PURPOSE
# -------
# Freeze the display-side contract BEFORE web packaging:
# - legend/class definitions
# - class summary + potential productivity
# - popup field contract
# - reusable AOI config for 40J01
#
# STANDARD LIBRARY ONLY
# NO geometry processing
# NO model rerun
# NO class recalculation
# ============================================================

from pathlib import Path
import csv
import json
import math
import statistics

WORKDIR = Path(
    r"C:\Users\user\Documents\KERJA\SPATIAL DATA ANALYST INTERN\04_YIELD"
)

FINAL_CSV = WORKDIR / "40I01_FINAL_OUTPUT4_DELIVERY_MASTER_820_SIAK_AOI01_V1.csv"
CLASS_SUMMARY_CSV = WORKDIR / "40I01_FINAL_CLASS_AREA_SUMMARY_SIAK_AOI01_V1.csv"
ASU_GEOJSON = WORKDIR / "40B03A_FINAL_ASU_500M_EXACT_SIAK_AOI01_V1.geojson"

OUTDIR = WORKDIR / "40I02B_WEB_DISPLAY_CONTRACT_SIAK_AOI01_V1"

OUT_CLASS_CSV = OUTDIR / "40I02B_CLASS_SUMMARY_WITH_PRODUCTIVITY_SIAK_AOI01_V1.csv"
OUT_LEGEND_JSON = OUTDIR / "40I02B_LEGEND_SIAK_AOI01_V1.json"
OUT_POPUP_JSON = OUTDIR / "40I02B_POPUP_FIELD_CONTRACT_SIAK_AOI01_V1.json"
OUT_DISPLAY_JSON = OUTDIR / "40I02B_DISPLAY_CONTRACT_SIAK_AOI01_V1.json"
OUT_CONFIG_JSON = WORKDIR / "40J01_WEB_PACKAGE_CONFIG_SIAK_AOI01_V1.json"
OUT_QC = OUTDIR / "40I02B_DISPLAY_CONTRACT_QC_SIAK_AOI01_V1.json"

EXPECTED_ASU = 820
EXPECTED_AREA_HA = 13867.099001884668

CLASS_DEF = {
    0: {
        "label": "Insufficient Data / Limited Evidence",
        "color": "#9E9E9E",
        "meaning": "Evidence belum cukup kuat untuk keputusan defensible.",
    },
    1: {
        "label": "Maintain",
        "color": "#2E7D32",
        "meaning": "Kondisi relatif baik; pertahankan pengelolaan dan monitoring rutin.",
    },
    2: {
        "label": "Monitor",
        "color": "#F9A825",
        "meaning": "Perlu monitoring karena indikasi penurunan, uncertainty, atau model disagreement.",
    },
    3: {
        "label": "Management Intervention Priority",
        "color": "#EF6C00",
        "meaning": "Prioritas pemeriksaan agronomis/operasional dan intervensi manajemen.",
    },
    4: {
        "label": "Replanting Evaluation Priority",
        "color": "#C62828",
        "meaning": "Prioritas evaluasi replanting oleh agronomist; bukan automatic replanting order.",
    },
}


def read_csv(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def fnum(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except Exception:
        return None


for p in [FINAL_CSV, CLASS_SUMMARY_CSV, ASU_GEOJSON]:
    if not p.exists():
        raise FileNotFoundError(p)

final_rows = read_csv(FINAL_CSV)
summary_rows = read_csv(CLASS_SUMMARY_CSV)

if len(final_rows) != EXPECTED_ASU:
    raise ValueError(f"Expected 820 final rows, got {len(final_rows)}")

ids = [str(r["UNIT_ID"]) for r in final_rows]
if len(set(ids)) != EXPECTED_ASU:
    raise ValueError("UNIT_ID final tidak unik.")

class_counts = {
    cls: sum(
        1
        for r in final_rows
        if int(float(r["MANAGEMENT_PRIORITY_CLASS"])) == cls
    )
    for cls in range(5)
}

expected_counts = {0: 4, 1: 159, 2: 551, 3: 103, 4: 3}
if class_counts != expected_counts:
    raise ValueError(f"Class count berubah: {class_counts}")

summary_by_class = {
    int(float(r["CLASS"])): r
    for r in summary_rows
}

# ------------------------------------------------------------
# PRODUCTIVITY DISPLAY PER CLASS
# Class 0 = indicative envelope
# Class 1–4 = median center per class
# ------------------------------------------------------------

prod = {}

for cls in range(5):
    rows = [
        r
        for r in final_rows
        if int(float(r["MANAGEMENT_PRIORITY_CLASS"])) == cls
    ]

    centers = [
        fnum(r.get("PRODUCTIVITY_CENTER_T_FFB_HA_YR"))
        for r in rows
    ]
    centers = [x for x in centers if x is not None]

    if not centers:
        raise ValueError(f"No productivity center for class {cls}")

    med = statistics.median(centers)

    if cls == 0:
        lows = [
            fnum(r.get("PRODUCTIVITY_LOW_T_FFB_HA_YR"))
            for r in rows
        ]
        highs = [
            fnum(r.get("PRODUCTIVITY_HIGH_T_FFB_HA_YR"))
            for r in rows
        ]
        lows = [x for x in lows if x is not None]
        highs = [x for x in highs if x is not None]

        if not lows or not highs:
            raise ValueError("Class 0 indicative range incomplete.")

        lo = min(lows)
        hi = max(highs)

        prod[cls] = {
            "display_type": "INDICATIVE_RANGE",
            "display": f"{lo:.2f}–{hi:.2f} t fresh FFB/ha/yr",
            "low": lo,
            "high": hi,
            "median_center": med,
        }
    else:
        prod[cls] = {
            "display_type": "MEDIAN_PRODUCTIVITY_CENTER",
            "display": f"{med:.2f} t fresh FFB/ha/yr",
            "low": None,
            "high": None,
            "median_center": med,
        }


# ------------------------------------------------------------
# CLASS SUMMARY OUTPUT
# ------------------------------------------------------------

class_rows = []

for cls in range(5):
    s = summary_by_class[cls]

    class_rows.append({
        "CLASS": cls,
        "STATUS": CLASS_DEF[cls]["label"],
        "N_ASU": int(float(s["N_ASU"])),
        "AREA_HA": float(s["AREA_HA"]),
        "AREA_PCT": float(s["AREA_PCT"]),
        "POTENTIAL_PRODUCTIVITY": prod[cls]["display"],
        "PRODUCTIVITY_DISPLAY_TYPE": prod[cls]["display_type"],
        "MEANING": CLASS_DEF[cls]["meaning"],
        "COLOR_HEX": CLASS_DEF[cls]["color"],
    })

OUTDIR.mkdir(parents=True, exist_ok=True)

with open(OUT_CLASS_CSV, "w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(class_rows[0].keys()))
    writer.writeheader()
    writer.writerows(class_rows)


legend = {
    "title": "Management Priority",
    "class_field": "MANAGEMENT_PRIORITY_CLASS",
    "classes": [
        {
            "code": cls,
            "label": CLASS_DEF[cls]["label"],
            "color": CLASS_DEF[cls]["color"],
            "meaning": CLASS_DEF[cls]["meaning"],
            "asu_count": class_counts[cls],
        }
        for cls in range(5)
    ],
    "render_class0": True,
    "outside_palm_domain": "transparent/noData",
}

with open(OUT_LEGEND_JSON, "w", encoding="utf-8") as f:
    json.dump(legend, f, indent=2, ensure_ascii=False)


# ------------------------------------------------------------
# POPUP CONTRACT
# ------------------------------------------------------------

preferred_popup = [
    {
        "label": "ASU ID",
        "candidates": ["UNIT_ID"],
        "required": True,
    },
    {
        "label": "Management Priority",
        "candidates": ["MANAGEMENT_PRIORITY_LABEL", "MANAGEMENT_PRIORITY_CLASS"],
        "required": True,
    },
    {
        "label": "Productivity Potential",
        "candidates": ["PRODUCTIVITY_DISPLAY_TEXT", "PRODUCTIVITY_CENTER_T_FFB_HA_YR"],
        "required": True,
    },
    {
        "label": "Productivity Range Low",
        "candidates": ["PRODUCTIVITY_LOW_T_FFB_HA_YR"],
        "required": True,
    },
    {
        "label": "Productivity Range High",
        "candidates": ["PRODUCTIVITY_HIGH_T_FFB_HA_YR"],
        "required": True,
    },
    {
        "label": "Estimate Pathway",
        "candidates": ["PRODUCTIVITY_PATHWAY"],
        "required": True,
    },
    {
        "label": "Productivity Band",
        "candidates": ["PRODUCTIVITY_BAND"],
        "required": False,
    },
    {
        "label": "Age Proxy",
        "candidates": ["AGE_P50", "AGE_PROXY_YR"],
        "required": False,
    },
    {
        "label": "Age Status",
        "candidates": ["AGE_STATUS"],
        "required": False,
    },
    {
        "label": "Condition Score",
        "candidates": ["CONDITION_SCORE", "COND_P50"],
        "required": False,
    },
    {
        "label": "Weather Context",
        "candidates": ["WEATHER_LAG_SUMMARY", "WEATHER_SUMMARY"],
        "required": False,
    },
    {
        "label": "Confidence",
        "candidates": ["MANAGEMENT_PRIORITY_CONFIDENCE"],
        "required": True,
    },
    {
        "label": "Rule Stability",
        "candidates": ["RULE_STABILITY"],
        "required": True,
    },
    {
        "label": "Reason Codes",
        "candidates": ["MANAGEMENT_PRIORITY_REASON_CODES", "REASON_CODES"],
        "required": False,
    },
    {
        "label": "Recommended Action",
        "candidates": ["MANAGEMENT_ACTION_TEXT", "ACTION_TEXT"],
        "required": False,
    },
]

header = set(final_rows[0].keys())
popup_fields = []

for spec in preferred_popup:
    selected = None

    for c in spec["candidates"]:
        if c in header:
            selected = c
            break

    popup_fields.append({
        "label": spec["label"],
        "field": selected,
        "required": spec["required"],
        "available": selected is not None,
    })

required_missing = [
    p["label"]
    for p in popup_fields
    if p["required"] and not p["available"]
]

if required_missing:
    raise ValueError(
        "Required popup fields missing: "
        + ", ".join(required_missing)
    )

popup_contract = {
    "title_template": "{UNIT_ID}",
    "fields": popup_fields,
    "guardrails": [
        "Productivity is modelled/indicative potential, not locally validated actual FFB yield.",
        "Fallback productivity has lower evidence strength than direct PALMSIM.",
        "Class 4 means Replanting Evaluation Priority, not automatic replanting.",
    ],
}

with open(OUT_POPUP_JSON, "w", encoding="utf-8") as f:
    json.dump(popup_contract, f, indent=2, ensure_ascii=False)


# ------------------------------------------------------------
# DISPLAY CONTRACT
# ------------------------------------------------------------

display_contract = {
    "contract_version": "OUTPUT4_WEB_DISPLAY_V1",
    "aoi_id": "SIAK_AOI01",
    "monitoring_year": 2025,
    "grid_size_m": 500,
    "total_asu": EXPECTED_ASU,
    "palm_area_ha": EXPECTED_AREA_HA,
    "legend_file": OUT_LEGEND_JSON.name,
    "popup_contract_file": OUT_POPUP_JSON.name,
    "class_summary_file": OUT_CLASS_CSV.name,
    "default_show_asu_boundaries": False,
    "class0_rendered": True,
    "outside_palm_domain": "transparent/noData",
    "popup_interaction": "hover/click supported by web implementation",
}

with open(OUT_DISPLAY_JSON, "w", encoding="utf-8") as f:
    json.dump(display_contract, f, indent=2, ensure_ascii=False)


# ------------------------------------------------------------
# AOI-SPECIFIC CONFIG FOR GENERIC 40J01 BUILDER
# ------------------------------------------------------------

config = {
    "aoi_id": "SIAK_AOI01",
    "display_name": "SIAK_AOI01",
    "monitoring_year": 2025,
    "grid_size_m": 500,
    "expected_asu_count": 820,
    "expected_palm_area_ha": EXPECTED_AREA_HA,
    "package_version": "v1",
    "source_geometry": ASU_GEOJSON.name,
    "source_attributes": FINAL_CSV.name,
    "source_class_summary": str(OUT_CLASS_CSV.relative_to(WORKDIR)),
    "source_legend": str(OUT_LEGEND_JSON.relative_to(WORKDIR)),
    "source_popup_contract": str(OUT_POPUP_JSON.relative_to(WORKDIR)),
    "default_show_asu_boundaries": False,
    "class0_rendered": True,
    "outside_palm_domain": "transparent/noData",
    "model_scope": "Productivity Potential & Management Priority",
    "local_ffb_validation": False,
}

with open(OUT_CONFIG_JSON, "w", encoding="utf-8") as f:
    json.dump(config, f, indent=2, ensure_ascii=False)


checks = {
    "final_rows_820": len(final_rows) == 820,
    "class_counts_preserved": class_counts == expected_counts,
    "class0_productivity_range_available": prod[0]["low"] is not None and prod[0]["high"] is not None,
    "class1_4_median_productivity_available": all(prod[c]["median_center"] is not None for c in range(1, 5)),
    "required_popup_fields_available": len(required_missing) == 0,
    "config_created": OUT_CONFIG_JSON.exists(),
}

status = (
    "PASS_40I02B_DISPLAY_CONTRACT_FROZEN"
    if all(checks.values())
    else "REVIEW"
)

qc = {
    "status": status,
    "checks": checks,
    "class_counts": {str(k): v for k, v in class_counts.items()},
    "productivity_by_class": {str(k): v for k, v in prod.items()},
    "outputs": {
        "class_summary_csv": str(OUT_CLASS_CSV),
        "legend_json": str(OUT_LEGEND_JSON),
        "popup_contract_json": str(OUT_POPUP_JSON),
        "display_contract_json": str(OUT_DISPLAY_JSON),
        "40J01_config_json": str(OUT_CONFIG_JSON),
    },
}

with open(OUT_QC, "w", encoding="utf-8") as f:
    json.dump(qc, f, indent=2, ensure_ascii=False)


print("====================================================")
print("40I02B FINISHED")
print("====================================================")
print("Status                         :", status)
print("Class summary                  :", OUT_CLASS_CSV)
print("Legend contract                :", OUT_LEGEND_JSON)
print("Popup contract                 :", OUT_POPUP_JSON)
print("Display contract               :", OUT_DISPLAY_JSON)
print("40J01 reusable AOI config      :", OUT_CONFIG_JSON)

print("\nCLASS PRODUCTIVITY SUMMARY")
for cls in range(5):
    print(
        f"Class {cls} | "
        f"N={class_counts[cls]} | "
        f"Potential={prod[cls]['display']}"
    )

print("\nNext                           : run generic 40J01 web package builder.")
print("====================================================")
