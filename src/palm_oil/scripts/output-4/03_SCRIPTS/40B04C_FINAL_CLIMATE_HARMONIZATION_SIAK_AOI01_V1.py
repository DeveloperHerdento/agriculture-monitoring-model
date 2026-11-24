from pathlib import Path
import os, json
import numpy as np
import pandas as pd

WORKDIR = Path(r"C:\Users\user\Documents\KERJA\SPATIAL DATA ANALYST INTERN\04_YIELD")
os.chdir(WORKDIR)

ASU_MAP = WORKDIR / "40B04A_ASU_CLIMATE_CELL_MAPPING_SIAK_AOI01_V1.csv"
CHIRPS_DAILY = WORKDIR / "40B04B1_CHIRPS_V2_DAILY_NATIVE_CELLS_2001_2025_SIAK_AOI01_V1.csv"
ERA5_DAILY = WORKDIR / "40B04B2_ERA5LAND_DAILY_NATIVE_CELLS_2001_2025_SIAK_AOI01_V4.csv"

OUT_ASU_PAIR_MAP = WORKDIR / "40B04C_ASU_CLIMATE_PAIR_MAPPING_SIAK_AOI01_V1.csv"
OUT_PAIR_DAILY = WORKDIR / "40B04C_MODEL_READY_CLIMATE_PAIRS_DAILY_2001_2025_SIAK_AOI01_V1.csv"
OUT_PAIR_MONTHLY = WORKDIR / "40B04C_MODEL_READY_CLIMATE_PAIRS_MONTHLY_2001_2025_SIAK_AOI01_V1.csv"
OUT_RAIN_QC = WORKDIR / "40B04C_CHIRPS_VS_ERA5L_RAINFALL_DIAGNOSTIC_SIAK_AOI01_V1.csv"
OUT_QC = WORKDIR / "40B04C_FINAL_CLIMATE_HARMONIZATION_QC_SIAK_AOI01_V1.json"

START_DATE = pd.Timestamp("2001-01-01")
END_DATE = pd.Timestamp("2025-12-31")
EXPECTED_DAYS = len(pd.date_range(START_DATE, END_DATE, freq="D"))

for p in [ASU_MAP, CHIRPS_DAILY, ERA5_DAILY]:
    if not p.exists():
        raise FileNotFoundError(f"Missing required input: {p}")

asu = pd.read_csv(ASU_MAP)
chirps = pd.read_csv(CHIRPS_DAILY)
era = pd.read_csv(ERA5_DAILY)

chirps["DATE"] = pd.to_datetime(chirps["DATE"]).dt.normalize()
era["DATE"] = pd.to_datetime(era["DATE"]).dt.normalize()

print("====================================================")
print("40B04C — FINAL CLIMATE HARMONIZATION")
print("====================================================")
print("ASU rows:", len(asu))
print("CHIRPS daily rows:", len(chirps))
print("ERA5-Land daily rows:", len(era))

req_asu = ["UNIT_ID", "CHIRPS_CELL_ID", "ERA5L_CELL_ID"]
missing = [c for c in req_asu if c not in asu.columns]
if missing:
    raise ValueError(f"Missing ASU mapping columns: {missing}")
if len(asu) != 820:
    raise ValueError(f"Expected 820 ASUs, found {len(asu)}")
if asu[req_asu].isna().any().any():
    raise ValueError("Missing climate-cell assignment in ASU map.")

asu["CLIMATE_PAIR_ID"] = asu["CHIRPS_CELL_ID"].astype(str) + "__" + asu["ERA5L_CELL_ID"].astype(str)

pair_map_cols = ["UNIT_ID", "CHIRPS_CELL_ID", "ERA5L_CELL_ID", "CLIMATE_PAIR_ID"]
for c in ["ASU_AREA_HA_EXACT", "PLANTATION_FRACTION_EXACT"]:
    if c in asu.columns:
        pair_map_cols.append(c)
pair_map = asu[pair_map_cols].copy()

agg_dict = {"ASU_COUNT": ("UNIT_ID", "count")}
if "ASU_AREA_HA_EXACT" in pair_map.columns:
    agg_dict["PLANTATION_AREA_HA"] = ("ASU_AREA_HA_EXACT", "sum")

pair_summary = (
    pair_map.groupby(["CLIMATE_PAIR_ID", "CHIRPS_CELL_ID", "ERA5L_CELL_ID"], as_index=False)
    .agg(**agg_dict)
)
print("Unique climate pairs:", len(pair_summary))

req_chirps = ["DATE", "CHIRPS_CELL_ID", "RAIN_MM_DAY"]
missing = [c for c in req_chirps if c not in chirps.columns]
if missing:
    raise ValueError(f"Missing CHIRPS columns: {missing}")

req_era = [
    "DATE","ERA5L_CELL_ID","TMEAN_C","TMIN_C","TMAX_C","TD_MEAN_C",
    "RH_MEAN_PCT","VPD_MEAN_KPA","VPD_MAX_KPA","WIND_MEAN_MS",
    "RAD_MJ_M2_DAY","PRESSURE_HPA","ERA5L_RAIN_MM_DAY"
]
missing = [c for c in req_era if c not in era.columns]
if missing:
    raise ValueError(f"Missing ERA5-Land columns: {missing}")

chirps = chirps[chirps["DATE"].between(START_DATE, END_DATE)].copy()
era = era[era["DATE"].between(START_DATE, END_DATE)].copy()

if chirps.duplicated(["CHIRPS_CELL_ID","DATE"]).any():
    raise ValueError("Duplicate CHIRPS cell-date rows found.")
if era.duplicated(["ERA5L_CELL_ID","DATE"]).any():
    raise ValueError("Duplicate ERA5-Land cell-date rows found.")

parts = []
for _, p in pair_summary.iterrows():
    c = chirps.loc[chirps["CHIRPS_CELL_ID"] == p["CHIRPS_CELL_ID"], ["DATE","RAIN_MM_DAY"]].copy()
    e = era.loc[era["ERA5L_CELL_ID"] == p["ERA5L_CELL_ID"], req_era].copy()
    m = c.merge(e, on="DATE", how="inner", validate="one_to_one")
    m["CLIMATE_PAIR_ID"] = p["CLIMATE_PAIR_ID"]
    m["CHIRPS_CELL_ID"] = p["CHIRPS_CELL_ID"]
    m["ERA5L_CELL_ID"] = p["ERA5L_CELL_ID"]
    m["RAIN_PRIMARY_MM_DAY"] = m["RAIN_MM_DAY"]
    m["RAIN_PRIMARY_SOURCE"] = "CHIRPS_v2_Final"
    m["ERA5L_RAIN_ROLE"] = "DIAGNOSTIC_ONLY"
    parts.append(m)

pair_daily = pd.concat(parts, ignore_index=True).sort_values(["CLIMATE_PAIR_ID","DATE"]).reset_index(drop=True)

pair_daily["PALMSIM_RAIN_MM_DAY"] = pair_daily["RAIN_PRIMARY_MM_DAY"]
pair_daily["PALMSIM_TMEAN_C"] = pair_daily["TMEAN_C"]
pair_daily["PALMSIM_RH_PCT"] = pair_daily["RH_MEAN_PCT"]
pair_daily["PALMSIM_WIND_MS"] = pair_daily["WIND_MEAN_MS"]
pair_daily["PALMSIM_RAD_MJ_M2_DAY"] = pair_daily["RAD_MJ_M2_DAY"]

pair_daily["APSIM_RAIN_MM_DAY"] = pair_daily["RAIN_PRIMARY_MM_DAY"]
pair_daily["APSIM_TMIN_C"] = pair_daily["TMIN_C"]
pair_daily["APSIM_TMAX_C"] = pair_daily["TMAX_C"]
pair_daily["APSIM_RAD_MJ_M2_DAY"] = pair_daily["RAD_MJ_M2_DAY"]

forcing_required = [
    "RAIN_PRIMARY_MM_DAY","TMEAN_C","TMIN_C","TMAX_C","RH_MEAN_PCT",
    "VPD_MEAN_KPA","WIND_MEAN_MS","RAD_MJ_M2_DAY","PRESSURE_HPA"
]

pair_qc_rows = []
for pair_id, sub in pair_daily.groupby("CLIMATE_PAIR_ID"):
    sub = sub.set_index("DATE").reindex(pd.date_range(START_DATE, END_DATE, freq="D"))
    valid = sub[forcing_required].notna().all(axis=1)
    pair_qc_rows.append({
        "CLIMATE_PAIR_ID": pair_id,
        "EXPECTED_DAYS": EXPECTED_DAYS,
        "VALID_DAYS": int(valid.sum()),
        "MISSING_DAYS": int((~valid).sum()),
        "COMPLETE": bool(valid.sum() == EXPECTED_DAYS),
    })
pair_qc = pd.DataFrame(pair_qc_rows)

pair_daily["RAIN_DIFF_MM_DAY"] = pair_daily["ERA5L_RAIN_MM_DAY"] - pair_daily["RAIN_PRIMARY_MM_DAY"]
rain_qc_rows = []
for pair_id, sub in pair_daily.groupby("CLIMATE_PAIR_ID"):
    x = sub["RAIN_PRIMARY_MM_DAY"].astype(float)
    y = sub["ERA5L_RAIN_MM_DAY"].astype(float)
    valid = x.notna() & y.notna()
    rain_qc_rows.append({
        "CLIMATE_PAIR_ID": pair_id,
        "N_DAYS": int(valid.sum()),
        "CHIRPS_MEAN_MM_DAY": float(x[valid].mean()),
        "ERA5L_MEAN_MM_DAY": float(y[valid].mean()),
        "MEAN_BIAS_ERA5_MINUS_CHIRPS_MM_DAY": float((y[valid]-x[valid]).mean()),
        "MAE_MM_DAY": float((y[valid]-x[valid]).abs().mean()),
        "DAILY_CORRELATION": float(x[valid].corr(y[valid])) if valid.sum() > 1 else np.nan,
        "NOTE": "Diagnostic only; CHIRPS remains primary rainfall forcing.",
    })
rain_qc = pd.DataFrame(rain_qc_rows)

pair_daily["YEAR"] = pair_daily["DATE"].dt.year
pair_daily["MONTH"] = pair_daily["DATE"].dt.month
pair_monthly = (
    pair_daily.groupby(["CLIMATE_PAIR_ID","CHIRPS_CELL_ID","ERA5L_CELL_ID","YEAR","MONTH"], as_index=False)
    .agg(
        RAIN_PRIMARY_MM_MONTH=("RAIN_PRIMARY_MM_DAY","sum"),
        TMEAN_C=("TMEAN_C","mean"),
        TMIN_C=("TMIN_C","min"),
        TMAX_C=("TMAX_C","max"),
        RH_MEAN_PCT=("RH_MEAN_PCT","mean"),
        VPD_MEAN_KPA=("VPD_MEAN_KPA","mean"),
        VPD_MAX_KPA=("VPD_MAX_KPA","max"),
        WIND_MEAN_MS=("WIND_MEAN_MS","mean"),
        RAD_MJ_M2_MONTH=("RAD_MJ_M2_DAY","sum"),
        PRESSURE_HPA=("PRESSURE_HPA","mean"),
        ERA5L_RAIN_MM_MONTH=("ERA5L_RAIN_MM_DAY","sum"),
        VALID_DAYS=("TMEAN_C","count"),
    )
)

expected_pair_daily_rows = EXPECTED_DAYS * len(pair_summary)
plausibility = {
    "RAIN_PRIMARY_MM_DAY_nonnegative": bool((pair_daily["RAIN_PRIMARY_MM_DAY"] >= 0).all()),
    "TMEAN_C": bool(pair_daily["TMEAN_C"].between(-10,45).all()),
    "RH_MEAN_PCT": bool(pair_daily["RH_MEAN_PCT"].between(0,100).all()),
    "VPD_MEAN_KPA_nonnegative": bool((pair_daily["VPD_MEAN_KPA"] >= 0).all()),
    "WIND_MEAN_MS_nonnegative": bool((pair_daily["WIND_MEAN_MS"] >= 0).all()),
    "RAD_MJ_M2_DAY": bool(pair_daily["RAD_MJ_M2_DAY"].between(0,45).all()),
    "PRESSURE_HPA": bool(pair_daily["PRESSURE_HPA"].between(800,1100).all()),
}

status = "PASS" if (
    len(pair_daily) == expected_pair_daily_rows
    and bool(pair_qc["COMPLETE"].all())
    and all(plausibility.values())
) else "CHECK"

qc = {
    "gate":"40B04C",
    "status":status,
    "asu_count":int(len(asu)),
    "unique_chirps_cells":int(asu["CHIRPS_CELL_ID"].nunique()),
    "unique_era5land_cells":int(asu["ERA5L_CELL_ID"].nunique()),
    "unique_climate_pairs":int(len(pair_summary)),
    "period":[START_DATE.strftime("%Y-%m-%d"),END_DATE.strftime("%Y-%m-%d")],
    "expected_days_per_climate_pair":int(EXPECTED_DAYS),
    "expected_pair_daily_rows":int(expected_pair_daily_rows),
    "actual_pair_daily_rows":int(len(pair_daily)),
    "complete_climate_pairs":int(pair_qc["COMPLETE"].sum()),
    "incomplete_climate_pairs":int((~pair_qc["COMPLETE"]).sum()),
    "missing_forcing_days_total":int(pair_qc["MISSING_DAYS"].sum()),
    "primary_rainfall_source":"CHIRPS v2 Final",
    "era5land_rainfall_role":"diagnostic_crosscheck_and_sensitivity_only",
    "palmsim_ready":bool(pair_daily[
        ["PALMSIM_RAIN_MM_DAY","PALMSIM_TMEAN_C","PALMSIM_RH_PCT","PALMSIM_WIND_MS","PALMSIM_RAD_MJ_M2_DAY"]
    ].notna().all().all()),
    "apsim_weather_ready":bool(pair_daily[
        ["APSIM_RAIN_MM_DAY","APSIM_TMIN_C","APSIM_TMAX_C","APSIM_RAD_MJ_M2_DAY"]
    ].notna().all().all()),
    "storage_strategy":"Daily climate retained once per unique CHIRPS×ERA5-Land pair; 820 ASUs reference CLIMATE_PAIR_ID.",
    "plausibility_checks":plausibility,
}

pair_map.to_csv(OUT_ASU_PAIR_MAP,index=False,encoding="utf-8-sig")
pair_daily.to_csv(OUT_PAIR_DAILY,index=False,encoding="utf-8-sig")
pair_monthly.to_csv(OUT_PAIR_MONTHLY,index=False,encoding="utf-8-sig")
rain_qc.to_csv(OUT_RAIN_QC,index=False,encoding="utf-8-sig")
OUT_QC.write_text(json.dumps(qc,indent=2),encoding="utf-8")

print("\n====================================================")
print("40B04C FINISHED")
print("====================================================")
print("Status:", status)
print("ASUs:", len(asu))
print("Unique CHIRPS cells:", qc["unique_chirps_cells"])
print("Unique ERA5-Land cells:", qc["unique_era5land_cells"])
print("Unique climate pairs:", qc["unique_climate_pairs"])
print("Daily rows:", qc["actual_pair_daily_rows"], "/", qc["expected_pair_daily_rows"])
print("Complete climate pairs:", qc["complete_climate_pairs"], "/", qc["unique_climate_pairs"])
print("Missing forcing days:", qc["missing_forcing_days_total"])
print("PALMSIM climate-ready:", qc["palmsim_ready"])
print("APSIM weather-ready:", qc["apsim_weather_ready"])
print("ASU-pair map:", OUT_ASU_PAIR_MAP)
print("Daily climate store:", OUT_PAIR_DAILY)
print("Monthly climate store:", OUT_PAIR_MONTHLY)
print("Rainfall diagnostic:", OUT_RAIN_QC)
print("QC JSON:", OUT_QC)
print("====================================================")
