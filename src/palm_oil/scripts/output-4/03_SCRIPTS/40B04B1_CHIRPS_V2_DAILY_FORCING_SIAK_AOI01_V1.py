# ============================================================
# OUTPUT 4 / 40B04B1
# CHIRPS v2 FINAL DAILY RAINFALL FORCING — SIAK_AOI01
# 12 UNIQUE NATIVE CELLS, 2001-2025
#
# DESIGN
# - Uses 40B04A unique CHIRPS-cell mapping (12 cells expected)
# - Retrieves UCSB CHIRPS v2 daily rainfall through ClimateSERV
#   server-side processing, avoiding ~9,131 individual raster downloads
# - Uses conservative 10-year request chunks with checkpoint caching
# - Cross-checks selected dates against official UCSB CHIRPS COGs
# - Exports compact native-cell daily forcing, not 820 redundant copies
#
# OUTPUT UNIT
# - RAIN_MM_DAY = mm/day
# ============================================================

from pathlib import Path
import os
import json
import time
import math
from datetime import datetime

import numpy as np
import pandas as pd
import requests
import rasterio

# ------------------------------------------------------------
# 0. CONFIG
# ------------------------------------------------------------

WORKDIR = Path(
    r"C:\Users\user\Documents\KERJA\SPATIAL DATA ANALYST INTERN\04_YIELD"
)
os.chdir(WORKDIR)

INPUT_CELLS = WORKDIR / "40B04A_UNIQUE_CHIRPS_CELLS_SIAK_AOI01_V1.csv"

RAW_DIR = WORKDIR / "climate_raw" / "chirps_v2"
RAW_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_DAILY = WORKDIR / "40B04B1_CHIRPS_V2_DAILY_NATIVE_CELLS_2001_2025_SIAK_AOI01_V1.csv"
OUTPUT_CELL_QC = WORKDIR / "40B04B1_CHIRPS_V2_CELL_QC_SIAK_AOI01_V1.csv"
OUTPUT_MONTHLY = WORKDIR / "40B04B1_CHIRPS_V2_MONTHLY_NATIVE_CELLS_2001_2025_SIAK_AOI01_V1.csv"
OUTPUT_ANNUAL = WORKDIR / "40B04B1_CHIRPS_V2_ANNUAL_NATIVE_CELLS_2001_2025_SIAK_AOI01_V1.csv"
OUTPUT_QC_JSON = WORKDIR / "40B04B1_CHIRPS_V2_QC_SUMMARY_SIAK_AOI01_V1.json"

START_DATE = "2001-01-01"
END_DATE = "2025-12-31"

# ClimateSERV currently limits requests to <=20 years.
# 10-year chunks are deliberately used for reliability/restartability.
DATE_CHUNKS = [
    ("2001-01-01", "2010-12-31"),
    ("2011-01-01", "2020-12-31"),
    ("2021-01-01", "2025-12-31"),
]

# Polygon stays well inside one 0.05° CHIRPS pixel.
CELL_INTERIOR_HALF_WIDTH_DEG = 0.020

# Current ClimateSERV API first, legacy endpoint as fallback.
API_BASES = [
    "https://climateserv.servirglobal.net/api",
    "https://climateserv.servirglobal.net/chirps",
]

POLL_SECONDS = 5
JOB_TIMEOUT_SECONDS = 45 * 60
REQUEST_TIMEOUT_SECONDS = 90
MAX_SUBMIT_RETRIES = 4

# Sparse independent cross-check against official UCSB COG archive.
CROSSCHECK_DATES = [
    "2005-06-15",
    "2015-06-15",
    "2025-06-15",
]
CROSSCHECK_ABS_TOL_MM = 0.05

EXPECTED_DAYS = len(pd.date_range(START_DATE, END_DATE, freq="D"))

# ------------------------------------------------------------
# 1. HELPERS
# ------------------------------------------------------------

def iso_to_api_date(s):
    return pd.Timestamp(s).strftime("%m/%d/%Y")

def make_interior_polygon(lon, lat, half_width=CELL_INTERIOR_HALF_WIDTH_DEG):
    x0, x1 = float(lon) - half_width, float(lon) + half_width
    y0, y1 = float(lat) - half_width, float(lat) + half_width
    return {
        "type": "Polygon",
        "coordinates": [[
            [x0, y1],
            [x1, y1],
            [x1, y0],
            [x0, y0],
            [x0, y1],
        ]]
    }

def robust_json_response(resp):
    resp.raise_for_status()
    try:
        return resp.json()
    except Exception:
        txt = resp.text.strip()
        # Some endpoints may return JSON encoded as text.
        return json.loads(txt)

def submit_job(api_base, begin_iso, end_iso, geometry):
    url = f"{api_base}/submitDataRequest/"
    params = {
        "datatype": 0,              # UCSB CHIRPS Rainfall
        "begintime": iso_to_api_date(begin_iso),
        "endtime": iso_to_api_date(end_iso),
        "intervaltype": 0,          # Daily
        "operationtype": 5,         # Average
        "dateType_Category": "default",
        "isZip_CurrentDataType": "false",
        "geometry": json.dumps(geometry, separators=(",", ":")),
    }

    last_err = None
    for attempt in range(1, MAX_SUBMIT_RETRIES + 1):
        try:
            r = requests.get(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
            obj = robust_json_response(r)

            if isinstance(obj, list) and len(obj) > 0:
                job_id = str(obj[0])
            elif isinstance(obj, str):
                job_id = obj
            elif isinstance(obj, dict):
                # Defensive fallbacks for API wrappers.
                job_id = (
                    obj.get("id")
                    or obj.get("job_id")
                    or obj.get("uniqueid")
                    or obj.get("uuid")
                )
            else:
                job_id = None

            if not job_id or "error" in str(job_id).lower():
                raise RuntimeError(f"Unexpected submit response: {obj}")

            return str(job_id)

        except Exception as e:
            last_err = e
            if attempt < MAX_SUBMIT_RETRIES:
                wait_s = 5 * attempt
                print(f"  submit retry {attempt}/{MAX_SUBMIT_RETRIES} after error: {e}")
                time.sleep(wait_s)

    raise RuntimeError(f"Submit failed after retries: {last_err}")

def parse_progress_object(obj):
    if isinstance(obj, (int, float)):
        return float(obj)
    if isinstance(obj, list) and obj:
        return parse_progress_object(obj[0])
    if isinstance(obj, dict):
        for k in ["progress", "value", "percent", "percentage"]:
            if k in obj:
                return parse_progress_object(obj[k])
    try:
        return float(obj)
    except Exception:
        return np.nan

def poll_job(api_base, job_id):
    url = f"{api_base}/getDataRequestProgress/"
    started = time.time()
    last_print_bucket = -1

    while True:
        if time.time() - started > JOB_TIMEOUT_SECONDS:
            raise TimeoutError(
                f"ClimateSERV job exceeded {JOB_TIMEOUT_SECONDS/60:.0f} minutes: {job_id}"
            )

        r = requests.get(
            url,
            params={"id": job_id},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        obj = robust_json_response(r)
        progress = parse_progress_object(obj)

        if np.isfinite(progress):
            if progress < 0:
                raise RuntimeError(f"ClimateSERV returned failed progress for {job_id}: {obj}")

            bucket = int(progress // 10) * 10
            if bucket != last_print_bucket:
                print(f"    progress ~{progress:.1f}%")
                last_print_bucket = bucket

            if progress >= 100:
                return

        time.sleep(POLL_SECONDS)

def get_job_data(api_base, job_id):
    url = f"{api_base}/getDataFromRequest/"
    r = requests.get(
        url,
        params={"id": job_id},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    obj = robust_json_response(r)

    if not isinstance(obj, dict) or "data" not in obj:
        raise RuntimeError(f"Unexpected ClimateSERV result for {job_id}: {str(obj)[:1000]}")

    return obj

def first_numeric_value(d):
    if isinstance(d, dict):
        preferred = ["avg", "average", "mean", "value"]
        lower_map = {str(k).lower(): v for k, v in d.items()}
        for k in preferred:
            if k in lower_map:
                try:
                    return float(lower_map[k])
                except Exception:
                    pass

        for v in d.values():
            try:
                return float(v)
            except Exception:
                continue
    try:
        return float(d)
    except Exception:
        return np.nan

def result_to_dataframe(result_obj, cell_id, cell_lon, cell_lat):
    records = []

    for item in result_obj.get("data", []):
        value = first_numeric_value(item.get("value", {}))

        # Prefer readable calendar date; use epoch only as fallback.
        dt = pd.to_datetime(item.get("date"), errors="coerce", dayfirst=False)

        if pd.isna(dt):
            epoch = pd.to_numeric(item.get("epochTime"), errors="coerce")
            if pd.notna(epoch):
                dt = pd.to_datetime(epoch, unit="s", utc=True).tz_convert(None).normalize()

        if pd.isna(dt):
            continue

        records.append({
            "DATE": pd.Timestamp(dt).normalize(),
            "CHIRPS_CELL_ID": cell_id,
            "CHIRPS_LON": float(cell_lon),
            "CHIRPS_LAT": float(cell_lat),
            "RAIN_MM_DAY": value,
            "RAIN_SOURCE": "UCSB_CHIRPS_v2_via_ClimateSERV",
        })

    out = pd.DataFrame.from_records(records)
    if not out.empty:
        out["RAIN_MM_DAY"] = pd.to_numeric(out["RAIN_MM_DAY"], errors="coerce")
    return out

def run_or_load_chunk(cell_id, lon, lat, begin_iso, end_iso):
    safe_chunk = f"{begin_iso.replace('-','')}_{end_iso.replace('-','')}"
    raw_path = RAW_DIR / f"{cell_id}_{safe_chunk}.json"

    if raw_path.exists() and raw_path.stat().st_size > 20:
        try:
            obj = json.loads(raw_path.read_text(encoding="utf-8"))
            df = result_to_dataframe(obj, cell_id, lon, lat)
            if len(df) > 0:
                print(f"  cached {begin_iso} → {end_iso}: {len(df)} rows")
                return df
        except Exception:
            pass

    geometry = make_interior_polygon(lon, lat)

    last_error = None
    for api_base in API_BASES:
        try:
            print(f"  request {begin_iso} → {end_iso}")
            job_id = submit_job(api_base, begin_iso, end_iso, geometry)
            print(f"    job: {job_id}")
            poll_job(api_base, job_id)
            obj = get_job_data(api_base, job_id)

            raw_path.write_text(
                json.dumps(obj, ensure_ascii=False),
                encoding="utf-8"
            )

            df = result_to_dataframe(obj, cell_id, lon, lat)
            if df.empty:
                raise RuntimeError("ClimateSERV returned no parseable daily records.")

            return df

        except Exception as e:
            last_error = e
            print(f"    endpoint failed: {api_base} | {e}")

    raise RuntimeError(
        f"All ClimateSERV endpoints failed for {cell_id} {begin_iso}-{end_iso}: {last_error}"
    )

def official_cog_url(date_str):
    d = pd.Timestamp(date_str)
    return (
        "https://data.chc.ucsb.edu/products/CHIRPS-2.0/"
        f"global_daily/cogs/p05/{d.year}/"
        f"chirps-v2.0.{d.year}.{d.month:02d}.{d.day:02d}.cog"
    )

def crosscheck_against_ucsb_cog(daily_df, cells_df):
    rows = []

    env_opts = {
        "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
        "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".cog,.tif,.tiff",
    }

    for date_str in CROSSCHECK_DATES:
        print(f"Cross-check official UCSB COG: {date_str}")
        url = official_cog_url(date_str)

        with rasterio.Env(**env_opts):
            with rasterio.open(url) as src:
                nodata = src.nodata

                for _, c in cells_df.iterrows():
                    cid = c["CHIRPS_CELL_ID"]
                    lon = float(c["CHIRPS_LON"])
                    lat = float(c["CHIRPS_LAT"])

                    val = next(src.sample([(lon, lat)]))[0]
                    val = float(val)

                    if nodata is not None and np.isclose(val, nodata):
                        val = np.nan

                    local = daily_df[
                        (daily_df["CHIRPS_CELL_ID"] == cid)
                        & (daily_df["DATE"] == pd.Timestamp(date_str))
                    ]["RAIN_MM_DAY"]

                    climate_val = (
                        float(local.iloc[0])
                        if len(local) == 1 and pd.notna(local.iloc[0])
                        else np.nan
                    )

                    diff = (
                        abs(climate_val - val)
                        if np.isfinite(climate_val) and np.isfinite(val)
                        else np.nan
                    )

                    rows.append({
                        "DATE": date_str,
                        "CHIRPS_CELL_ID": cid,
                        "CLIMATESERV_MM": climate_val,
                        "UCSB_COG_MM": val,
                        "ABS_DIFF_MM": diff,
                        "PASS": (
                            bool(diff <= CROSSCHECK_ABS_TOL_MM)
                            if np.isfinite(diff) else False
                        ),
                    })

    return pd.DataFrame(rows)

# ------------------------------------------------------------
# 2. LOAD UNIQUE CELLS
# ------------------------------------------------------------

if not INPUT_CELLS.exists():
    raise FileNotFoundError(f"Missing input: {INPUT_CELLS}")

cells = pd.read_csv(INPUT_CELLS)

required = ["CHIRPS_CELL_ID", "CHIRPS_LON", "CHIRPS_LAT"]
missing = [c for c in required if c not in cells.columns]
if missing:
    raise ValueError(f"Missing required columns: {missing}")

cells = (
    cells[required + [c for c in ["ASU_COUNT", "PLANTATION_AREA_HA"] if c in cells.columns]]
    .drop_duplicates(subset=["CHIRPS_CELL_ID"])
    .sort_values("CHIRPS_CELL_ID")
    .reset_index(drop=True)
)

print("====================================================")
print("40B04B1 — CHIRPS v2 DAILY RAINFALL")
print("====================================================")
print("Unique CHIRPS cells:", len(cells))
print("Period:", START_DATE, "→", END_DATE)
print("Expected days/cell:", EXPECTED_DAYS)
print("Expected final rows:", EXPECTED_DAYS * len(cells))
print("Checkpoint folder:", RAW_DIR)

if len(cells) != 12:
    print(f"WARNING: 40B04A previously expected 12 cells; current file has {len(cells)}.")

# ------------------------------------------------------------
# 3. RETRIEVE / LOAD DAILY DATA
# ------------------------------------------------------------

pieces = []

for i, c in cells.iterrows():
    cid = str(c["CHIRPS_CELL_ID"])
    clon = float(c["CHIRPS_LON"])
    clat = float(c["CHIRPS_LAT"])

    print("\n----------------------------------------------------")
    print(f"Cell {i+1}/{len(cells)}: {cid} @ ({clon:.6f}, {clat:.6f})")
    print("----------------------------------------------------")

    for begin_iso, end_iso in DATE_CHUNKS:
        piece = run_or_load_chunk(
            cid, clon, clat,
            begin_iso, end_iso
        )
        pieces.append(piece)

daily = pd.concat(pieces, ignore_index=True)

daily["DATE"] = pd.to_datetime(daily["DATE"]).dt.normalize()
daily["RAIN_MM_DAY"] = pd.to_numeric(daily["RAIN_MM_DAY"], errors="coerce")

# Restrict exact target period and de-duplicate defensively.
daily = daily[
    daily["DATE"].between(pd.Timestamp(START_DATE), pd.Timestamp(END_DATE))
].copy()

daily = (
    daily.sort_values(["CHIRPS_CELL_ID", "DATE"])
    .drop_duplicates(["CHIRPS_CELL_ID", "DATE"], keep="last")
    .reset_index(drop=True)
)

# CHIRPS precipitation should not be negative.
daily.loc[daily["RAIN_MM_DAY"] < 0, "RAIN_MM_DAY"] = np.nan

# ------------------------------------------------------------
# 4. COMPLETENESS QC
# ------------------------------------------------------------

full_dates = pd.date_range(START_DATE, END_DATE, freq="D")

qc_rows = []

for _, c in cells.iterrows():
    cid = str(c["CHIRPS_CELL_ID"])
    sub = daily[daily["CHIRPS_CELL_ID"] == cid].set_index("DATE")
    sub = sub.reindex(full_dates)

    vals = pd.to_numeric(sub["RAIN_MM_DAY"], errors="coerce")

    qc_rows.append({
        "CHIRPS_CELL_ID": cid,
        "EXPECTED_DAYS": EXPECTED_DAYS,
        "ROWS_PRESENT": int(sub["RAIN_SOURCE"].notna().sum()),
        "VALID_RAIN_DAYS": int(vals.notna().sum()),
        "MISSING_RAIN_DAYS": int(vals.isna().sum()),
        "MIN_RAIN_MM_DAY": float(vals.min()) if vals.notna().any() else np.nan,
        "MEDIAN_RAIN_MM_DAY": float(vals.median()) if vals.notna().any() else np.nan,
        "P95_RAIN_MM_DAY": float(vals.quantile(0.95)) if vals.notna().any() else np.nan,
        "MAX_RAIN_MM_DAY": float(vals.max()) if vals.notna().any() else np.nan,
        "MEAN_ANNUALIZED_RAIN_MM": float(vals.mean() * 365.25) if vals.notna().any() else np.nan,
        "COMPLETE": bool(vals.notna().sum() == EXPECTED_DAYS),
    })

cell_qc = pd.DataFrame(qc_rows)

# ------------------------------------------------------------
# 5. INDEPENDENT UCSB COG CROSS-CHECK
# ------------------------------------------------------------

crosscheck = crosscheck_against_ucsb_cog(daily, cells)

crosscheck_path = WORKDIR / "40B04B1_CHIRPS_V2_UCSB_COG_CROSSCHECK_SIAK_AOI01_V1.csv"
crosscheck.to_csv(crosscheck_path, index=False, encoding="utf-8-sig")

# ------------------------------------------------------------
# 6. MONTHLY + ANNUAL SUMMARIES
# ------------------------------------------------------------

daily["YEAR"] = daily["DATE"].dt.year
daily["MONTH"] = daily["DATE"].dt.month

monthly = (
    daily.groupby(["CHIRPS_CELL_ID", "CHIRPS_LON", "CHIRPS_LAT", "YEAR", "MONTH"], as_index=False)
    .agg(
        RAIN_MM_MONTH=("RAIN_MM_DAY", "sum"),
        VALID_DAYS=("RAIN_MM_DAY", "count"),
    )
)

annual = (
    daily.groupby(["CHIRPS_CELL_ID", "CHIRPS_LON", "CHIRPS_LAT", "YEAR"], as_index=False)
    .agg(
        RAIN_MM_YEAR=("RAIN_MM_DAY", "sum"),
        VALID_DAYS=("RAIN_MM_DAY", "count"),
    )
)

# ------------------------------------------------------------
# 7. FINAL QC DECISION
# ------------------------------------------------------------

all_cells_complete = bool(cell_qc["COMPLETE"].all())
all_crosschecks_pass = bool(crosscheck["PASS"].all()) if len(crosscheck) else False

status = (
    "PASS"
    if all_cells_complete and all_crosschecks_pass
    else "CHECK"
)

qc_summary = {
    "gate": "40B04B1",
    "status": status,
    "dataset": "CHIRPS v2 Final daily precipitation",
    "retrieval_service": "ClimateSERV",
    "independent_crosscheck_source": "official UCSB CHIRPS v2 daily p05 COG",
    "period": [START_DATE, END_DATE],
    "unique_chirps_cells": int(len(cells)),
    "expected_days_per_cell": int(EXPECTED_DAYS),
    "expected_total_rows": int(EXPECTED_DAYS * len(cells)),
    "actual_unique_cell_date_rows": int(len(daily)),
    "cells_complete": int(cell_qc["COMPLETE"].sum()),
    "cells_incomplete": int((~cell_qc["COMPLETE"]).sum()),
    "missing_daily_values_total": int(cell_qc["MISSING_RAIN_DAYS"].sum()),
    "crosscheck_samples": int(len(crosscheck)),
    "crosscheck_pass": int(crosscheck["PASS"].sum()) if len(crosscheck) else 0,
    "crosscheck_fail": int((~crosscheck["PASS"]).sum()) if len(crosscheck) else 0,
    "crosscheck_abs_tolerance_mm": CROSSCHECK_ABS_TOL_MM,
    "unit": "mm/day",
    "output_strategy": (
        "Keep forcing at native climate-cell level; join to 820 ASUs by CHIRPS_CELL_ID "
        "during model execution rather than duplicating daily records."
    ),
}

# ------------------------------------------------------------
# 8. EXPORT
# ------------------------------------------------------------

daily_out = daily[
    [
        "DATE",
        "CHIRPS_CELL_ID",
        "CHIRPS_LON",
        "CHIRPS_LAT",
        "RAIN_MM_DAY",
        "RAIN_SOURCE",
    ]
].copy()

daily_out.to_csv(OUTPUT_DAILY, index=False, encoding="utf-8-sig")
cell_qc.to_csv(OUTPUT_CELL_QC, index=False, encoding="utf-8-sig")
monthly.to_csv(OUTPUT_MONTHLY, index=False, encoding="utf-8-sig")
annual.to_csv(OUTPUT_ANNUAL, index=False, encoding="utf-8-sig")

OUTPUT_QC_JSON.write_text(
    json.dumps(qc_summary, indent=2),
    encoding="utf-8"
)

print("\n====================================================")
print("40B04B1 FINISHED")
print("====================================================")
print("Status:", qc_summary["status"])
print("Unique CHIRPS cells:", qc_summary["unique_chirps_cells"])
print("Daily rows:", qc_summary["actual_unique_cell_date_rows"], "/", qc_summary["expected_total_rows"])
print("Complete cells:", qc_summary["cells_complete"], "/", qc_summary["unique_chirps_cells"])
print("Missing daily values:", qc_summary["missing_daily_values_total"])
print(
    "UCSB COG cross-check:",
    qc_summary["crosscheck_pass"], "PASS /",
    qc_summary["crosscheck_fail"], "FAIL"
)
print("Daily output:", OUTPUT_DAILY)
print("Cell QC:", OUTPUT_CELL_QC)
print("Cross-check:", crosscheck_path)
print("Monthly:", OUTPUT_MONTHLY)
print("Annual:", OUTPUT_ANNUAL)
print("QC JSON:", OUTPUT_QC_JSON)
print("====================================================")
