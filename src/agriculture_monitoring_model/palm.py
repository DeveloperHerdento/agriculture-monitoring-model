"""Palm oil analysis models (ports of scripts/FIX notebooks) for one field AOI.

- palm_cover        : Output 1 "Plantation boundary & palm validation" (RF on S2 + S1, contextual V2,
                      MMU -> closing -> MMU), year of date_from
- palm_age          : Output 2 "Tree age proxy" (Landsat 2000..year + Sentinel-2 disturbance/regrowth)
- palm_condition    : Output 3.1 core model 30D-04 "balanced hybrid risk" (6 two-month S2/S1 anomalies
                      vs the 5 previous years), year of date_from
- palm_nutrient     : Output 3.2 "Nutrient assessment N/P/K/Mg" (S2 z-score vs matched-season 5-year
                      baseline), the two-month period starting at date_from
- palm_waterlogging : Output 5.2 "Waterlogging potential index" (HAND, upstream area, slope, TPI300 +
                      rain / soil-moisture wetness vs the 15 previous years, 90 m grid)
- palm_productivity : Output 4 "Productivity potential & management priority" — PalmSim runs per 500 m
                      ASU over the whole AOI, so the frozen SIAK_AOI01 2025 package is clipped to the field

The field polygon is the plantation mask (the notebooks read Output 1's boundary asset). Where a
notebook calibrates on the whole AOI, the per-field run uses frozen values instead, otherwise every
field would be judged against itself:
- palm_condition    : the 30D-04 p80/p92/p90 alert thresholds are taken over the surrounding plantation
                      (Output 1 boundary within 5 km) instead of the whole AOI, floored as in 30D-04; the
                      B18C context modifier is not applied (its weights come from AOI samples).
- palm_waterlogging : static factors scaled with the SIAK_AOI01 p05/p95 and classes cut at the SIAK_AOI01
                      T1-T3 (both from the delivered package), not the field's own range.
- palm_nutrient     : the delivered notebook builds the baseline with other index definitions than
                      the monitoring composite (NDRE from B8A, raw DN instead of reflectance, looser
                      cloud mask), which pushes N and Mg to ~95% "Excess" on SIAK_AOI01. Here baseline
                      and monitoring share one definition, so the z-score compares like with like.

Like paddy_models, GEE builds the composites and the notebooks' numpy rules run locally. Every
runner writes one float32 COG (nodata -9999, named bands) and returns summary numbers.
"""

import json
import math
import os
import warnings
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from functools import lru_cache
from pathlib import Path

import ee
import numpy as np
from rasterio.features import rasterize
from rasterio.transform import from_origin
from rasterio.warp import transform_geom
from scipy import ndimage
from shapely.geometry import mapping, shape
from shapely.ops import unary_union

from .gee import S2_SR, aoi_crs, download_arrays, init_ee, save_cog, utm_epsg


def palm_data_dir() -> Path:
    """Folder with the frozen SIAK_AOI01 geojson files (plantation_boundary, o1_training_aoi01,
    output4_management_priority). Read from env var PALM_DATA_DIR at call time; the caller sets it."""
    value = os.environ.get("PALM_DATA_DIR")
    if not value:
        raise RuntimeError(
            "PALM_DATA_DIR is not set: point it to the folder with plantation_boundary.geojson, "
            "o1_training_aoi01.geojson and output4_management_priority.geojson"
        )
    return Path(value)


S1_GRD = "COPERNICUS/S1_GRD"
CS_PLUS = "GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED"
S2_CLOUD_PROB = "COPERNICUS/S2_CLOUD_PROBABILITY"


# ============================================================================ shared helpers
def _year(date_from: str, first: int) -> int:
    """Analysis year of date_from; only finished calendar years (every notebook composites a whole year)."""
    y = date.fromisoformat(date_from).year
    if y < first:
        raise ValueError(f"Tahun analisis minimal {first}")
    if date(y, 12, 31) >= date.today():
        raise ValueError(f"Tahun {y} belum selesai; pilih tahun yang sudah lengkap")
    return y


def _px_ha(profile: dict) -> float:
    t = profile["transform"]
    return abs(t.a * t.e) / 1e4


def _areas(cls: np.ndarray, labels: dict[int, str], px_ha: float) -> dict[str, float]:
    return {labels[k]: round(float((cls == k).sum()) * px_ha, 2) for k in labels if (cls == k).any()}


def _r(v, n: int = 3):
    return round(float(v), n) if v is not None and np.isfinite(v) else None


def _mean(a, mask=None):
    a = np.asarray(a, dtype=float)
    if mask is not None:
        a = a[mask]
    a = a[np.isfinite(a)]
    return round(float(a.mean()), 4) if a.size else None


def _mmu(mask: np.ndarray, min_px: int) -> np.ndarray:
    """Keep 8-connected patches of at least min_px pixels (Output 1 `apply_mmu`)."""
    labels, n = ndimage.label(mask, structure=np.ones((3, 3)))
    if n == 0:
        return np.zeros_like(mask, dtype=bool)
    keep = np.bincount(labels.ravel()) >= min_px
    keep[0] = False
    return keep[labels]


def _round_half_up(a: np.ndarray) -> np.ndarray:
    """ee.Image.round(): halves away from zero (numpy rounds halves to even)."""
    return np.floor(a + 0.5)


# ============================================================================ Output 3.2: nutrient
NUT_BASELINE_YEARS = 5
NUT_CLOUD_PROB = 50
NUT_NIR_DARK_DN = 1500
NUT_SHADOW_KM = 1
NUT_CLOUD_BUFFER_M = 40
NUT_SPECTRAL = ["B2", "B3", "B4", "B5", "B6", "B7", "B8", "B8A", "B11", "B12"]
NUT_FEATURES = ["NDVI", "NDRE", "GNDVI", "NDMI", "MSAVI"]
NUT_WEIGHTS = {  # 03D, frozen
    "N": {"NDRE": 0.4, "GNDVI": 0.3, "NDVI": 0.2, "MSAVI": 0.1},
    "P": {"NDVI": 0.4, "MSAVI": 0.35, "GNDVI": 0.25},
    "K": {"NDMI": 0.5, "NDVI": 0.3, "MSAVI": 0.2},
    "MG": {"NDRE": 0.4, "GNDVI": 0.35, "NDVI": 0.25},
}
NUTRIENTS = list(NUT_WEIGHTS)
NUT_CLASS = {0: "Data unavailable", 1: "Very deficient", 2: "Deficient", 3: "Normal", 4: "Excess", 5: "Very excess"}
NUT_CONF = {1: "Low", 2: "Medium", 3: "High"}
NUTRIENT_BANDS = [f"{n}_{k}" for n in NUTRIENTS for k in ("SCORE", "CLASS", "CONF")]


def _nutrient_mask(img):
    """02C strict mask: SCL, cloud probability, projected cloud shadow, 40 m buffer; reflectance x0.0001."""
    cloud_prob = ee.Image(img.get("cloud_probability_image")).select("probability")
    scl = img.select("SCL")
    edge = img.select("B2").mask().And(img.select("B8A").mask()).And(img.select("B9").mask())
    scl_ok = scl.remap([0, 1, 2, 3, 8, 9, 10, 11], [0] * 8, 1)
    cloud = cloud_prob.gte(NUT_CLOUD_PROB).Or(scl.eq(8)).Or(scl.eq(9)).Or(scl.eq(10)).unmask(0)
    dark = img.select("B8").lt(NUT_NIR_DARK_DN).And(scl.neq(6))
    azimuth = ee.Number(90).subtract(ee.Number(img.get("MEAN_SOLAR_AZIMUTH_ANGLE")))
    projected = (cloud.directionalDistanceTransform(azimuth, NUT_SHADOW_KM * 10)
                 .reproject(crs=img.select("B8").projection(), scale=100).select("distance").mask())
    shadow = cloud.Or(projected.And(dark).unmask(0)).unmask(0)
    buffered = shadow.focalMax(radius=NUT_CLOUD_BUFFER_M, kernelType="circle", units="meters")
    valid = edge.And(scl_ok).And(buffered.Not()).unmask(0)
    return (img.select(NUT_SPECTRAL).multiply(0.0001).updateMask(valid)
            .copyProperties(img, ["system:time_start"]))


def _nutrient_features(img):
    """The monitoring composite's definitions (03A), used for the baseline too."""
    msavi = img.expression("(2*NIR+1-sqrt((2*NIR+1)*(2*NIR+1)-8*(NIR-RED)))/2",
                           {"NIR": img.select("B8"), "RED": img.select("B4")})
    return ee.Image(ee.Image.cat([
        img.normalizedDifference(["B8", "B4"]).rename("NDVI"),
        img.normalizedDifference(["B8", "B5"]).rename("NDRE"),
        img.normalizedDifference(["B8", "B3"]).rename("GNDVI"),
        img.normalizedDifference(["B8", "B11"]).rename("NDMI"),
        msavi.rename("MSAVI"),
    ]).copyProperties(img, ["system:time_start"]))


def _nutrient_scenes(aoi, s2_filter, prob_filter):
    s2 = ee.ImageCollection(S2_SR).filterBounds(aoi).filter(s2_filter).filter(ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE", 95))
    prob = ee.ImageCollection(S2_CLOUD_PROB).filterBounds(aoi).filter(prob_filter)
    joined = ee.ImageCollection(ee.Join.saveFirst("cloud_probability_image").apply(
        primary=s2, secondary=prob, condition=ee.Filter.equals(leftField="system:index", rightField="system:index")))
    return joined.filter(ee.Filter.notNull(["cloud_probability_image"])).map(_nutrient_mask)


def palm_nutrient(aoi_geojson: dict, date_from: str, date_to_exclusive: str, dest: Path) -> dict:
    """N/P/K/Mg condition for the two months starting at date_from vs the same months of the 5 previous years."""
    init_ee()
    aoi = ee.Geometry(aoi_geojson)
    crs = aoi_crs(aoi)
    start = date.fromisoformat(date_from)
    y, m0 = start.year, start.month
    m1 = m0 + 1

    period = ee.Filter.date(date_from, date_to_exclusive)
    scenes = _nutrient_scenes(aoi, period, period)
    days = scenes.aggregate_array("system:time_start").map(lambda t: ee.Date(t).format("YYYY-MM-dd")).distinct()

    def daily(day):
        d = ee.Date.parse("YYYY-MM-dd", day)
        return scenes.filterDate(d, d.advance(1, "day")).mosaic().set("system:time_start", d.millis())

    mon = ee.ImageCollection.fromImages(days.map(daily))
    feat = _nutrient_features(mon.median())
    valid = mon.select("B2").count().gte(1).unmask(0)

    seasonal = ee.Filter.And(ee.Filter.calendarRange(y - NUT_BASELINE_YEARS, y - 1, "year"),
                             ee.Filter.calendarRange(m0, m1, "month"))
    base_col = _nutrient_scenes(aoi, seasonal, seasonal).map(_nutrient_features)
    mean, std = base_col.mean(), base_col.reduce(ee.Reducer.stdDev()).rename(NUT_FEATURES)
    z = feat.subtract(mean).divide(std.updateMask(std.gt(0)))

    bands = []
    for n in NUTRIENTS:
        score = ee.Image(0)
        for b, w in NUT_WEIGHTS[n].items():  # add chain: a masked feature masks the score, as in 03D
            score = score.add(z.select(b).multiply(w))
        bands.append(score.rename(f"{n}_SCORE"))
    img = ee.Image.cat(bands + [valid.rename("VALID")])

    info = ee.Dictionary({"images": days.size(), "baseline_images": base_col.size()}).getInfo()
    if info["images"] == 0:
        raise ValueError(f"Tidak ada citra Sentinel-2 bersih antara {date_from} dan {date_to_exclusive}")
    if info["baseline_images"] == 0:
        raise ValueError("Tidak ada citra Sentinel-2 untuk baseline musim yang sama 5 tahun sebelumnya")

    arr, profile = download_arrays(img, aoi, crs)
    px = _px_ha(profile)
    inside = np.isfinite(arr[-1])
    has_data = inside & (arr[-1] == 1) & np.isfinite(arr[0])
    out, summary = [], {}
    for i, n in enumerate(NUTRIENTS):
        score = np.where(has_data, arr[i], np.nan)
        ok = np.isfinite(score)
        cls = np.where(inside, 0, np.nan).astype(np.float32)
        cls[ok] = np.digitize(score[ok], [-2, -1, 1, 2], right=True) + 1  # 03D CLASS_BREAKS
        conf = np.full(score.shape, np.nan, dtype=np.float32)
        conf[ok] = np.digitize(np.abs(score[ok]), [1, 2], right=True) + 1  # 03D CONF_BREAKS
        out += [score, cls, conf]
        summary[f"{n}_class_ha"] = _areas(cls, NUT_CLASS, px)
        summary[f"{n}_conf_ha"] = _areas(conf, NUT_CONF, px)
        summary[f"{n}_score_mean"] = _mean(score)
    save_cog(out, NUTRIENT_BANDS, profile, dest)

    field_ha = float(inside.sum()) * px
    no_data_ha = float((inside & ~has_data).sum()) * px
    return {
        "model": "Nutrient assessment (Output 3.2)",
        "bands": NUTRIENT_BANDS,
        "period": f"{y}-{m0:02d}/{y}-{m1:02d}",
        "baseline": f"{y - NUT_BASELINE_YEARS}–{y - 1}",
        "images": info["images"],
        "baseline_images": info["baseline_images"],
        "field_ha": round(field_ha, 2),
        "valid_ha": round(field_ha - no_data_ha, 2),
        "no_data_ha": round(no_data_ha, 2),
        "no_data_pct": round(100 * no_data_ha / field_ha, 1) if field_ha else None,
        **summary,
    }


# ============================================================================ Output 5.2: waterlogging
WL_SCALE_M = 90
WL_BASELINE_YEARS = 15
WL_Z_CLIP = 3.0
WL_DEM = "COPERNICUS/DEM/GLO30_2024_1"
WL_MERIT = "MERIT/Hydro/v1_0_1"
WL_CHIRPS = "UCSB-CHG/CHIRPS/DAILY"
WL_ERA5 = "ECMWF/ERA5_LAND/MONTHLY_AGGR"
# Frozen SIAK_AOI01 2025 calibration (package 08_INTERMEDIATE/STAGE4A_RAW_PIXEL_SAMPLE.csv, 02_STATISTICS):
# robust p05/p95 per static factor and its risk direction; class thresholds T1-T3.
WL_STATIC = {
    "HAND": (0.0, 13.5, True),                      # low value -> high risk
    "LOG10_UPA": (0.0036961942675364, 0.37515927726345344, False),
    "SLOPE": (0.34177196794974446, 8.966516314365245, True),
    "TPI300": (-5.800960731506348, 5.963826894760132, True),
}
WL_THRESHOLDS = [0.3718468087409409, 0.5236129759988584, 0.6753791432567758]
WL_WEIGHTS = {"HAND": 0.15, "LOG10_UPA": 0.15, "SLOPE": 0.15, "TPI300": 0.15, "RAIN": 0.20, "SOIL_MOISTURE": 0.20}
WL_CLASS = {1: "Low", 2: "Moderate", 3: "High", 4: "Extreme"}
WATERLOGGING_BANDS = ["WPI", "WPI_CLASS", "STATIC_INDEX", "DYNAMIC_INDEX"]


def _wet_top3(monthly_z: list) -> ee.Image:
    """Mean of the 3 wettest months of clip(z, 0, 3) / 3 (Stage 4A TOP3_WET)."""
    wet = ee.Image.cat([z.clamp(0, WL_Z_CLIP).divide(WL_Z_CLIP) for z in monthly_z])
    return wet.toArray().arraySort().arraySlice(0, 9, 12).arrayReduce(ee.Reducer.mean(), [0]).arrayGet([0])


def palm_waterlogging(aoi_geojson: dict, date_from: str, date_to_exclusive: str, dest: Path) -> dict:
    """Waterlogging potential index for the year of date_from (WPI = 0.6 static + 0.4 dynamic)."""
    init_ee()
    aoi = ee.Geometry(aoi_geojson)
    crs = aoi_crs(aoi)
    year = _year(date_from, 2010)
    grid = ee.Projection(crs).atScale(WL_SCALE_M)
    region = aoi.bounds(1).buffer(1000)

    dem_col = ee.ImageCollection(WL_DEM).filterBounds(region)
    dem_proj = ee.Image(dem_col.first()).select("DEM").projection()
    elev = dem_col.select("DEM").mosaic().setDefaultProjection(dem_proj).clip(region)
    slope = ee.Terrain.slope(elev)
    tpi = elev.subtract(elev.reduceNeighborhood(ee.Reducer.mean(), ee.Kernel.circle(300, "meters", False)))
    terrain = (ee.Image.cat([slope.rename("SLOPE"), tpi.rename("TPI300")]).setDefaultProjection(dem_proj)
               .reduceResolution(ee.Reducer.mean(), maxPixels=64).reproject(grid))
    merit = ee.Image(WL_MERIT)
    hydro = ee.Image.cat([merit.select("hnd").rename("HAND"),
                          merit.select("upa").add(1).log10().rename("LOG10_UPA")]).reproject(grid)
    raw = hydro.addBands(terrain)

    norm = []
    for f, (p05, p95, low_is_risk) in WL_STATIC.items():
        s = raw.select(f).unitScale(p05, p95).clamp(0, 1)
        norm.append((ee.Image(1).subtract(s) if low_is_risk else s).rename(f))

    chirps, era5 = ee.ImageCollection(WL_CHIRPS), ee.ImageCollection(WL_ERA5)
    base_years = list(range(year - WL_BASELINE_YEARS, year))

    def monthly(col, band, reducer, y, m):
        s = ee.Date.fromYMD(y, m, 1)
        return getattr(col.filterDate(s, s.advance(1, "month")).select(band), reducer)()

    def z_of(col, band, reducer, m, floor):
        base = ee.ImageCollection([monthly(col, band, reducer, y, m) for y in base_years])
        std = base.reduce(ee.Reducer.stdDev()).max(floor)
        return monthly(col, band, reducer, year, m).subtract(base.mean()).divide(std)

    rain_z = [z_of(chirps, "precipitation", "sum", m, 0.001).rename(f"RAIN_Z_{m:02d}") for m in range(1, 13)]
    sm_z = [z_of(era5, "volumetric_soil_water_layer_1", "mean", m, 0.000001).rename(f"SM_Z_{m:02d}")
            for m in range(1, 13)]
    rain = _wet_top3([z.clamp(-WL_Z_CLIP, WL_Z_CLIP) for z in rain_z]).rename("RAIN")
    sm = _wet_top3([z.clamp(-WL_Z_CLIP, WL_Z_CLIP) for z in sm_z]).rename("SOIL_MOISTURE")

    factors = ee.Image.cat(norm + [rain, sm]).reproject(grid)
    static = ee.Image.cat(norm).reduce(ee.Reducer.mean()).rename("STATIC_INDEX")
    dynamic = ee.Image.cat([rain, sm]).reduce(ee.Reducer.mean()).rename("DYNAMIC_INDEX")
    wpi = static.multiply(0.6).add(dynamic.multiply(0.4)).rename("WPI")
    img = ee.Image.cat([wpi, static, dynamic]).reproject(grid)

    region90 = dict(geometry=aoi, crs=crs, scale=WL_SCALE_M, maxPixels=1e9, bestEffort=True)
    info = ee.Dictionary({
        "factors": factors.reduceRegion(ee.Reducer.mean(), **region90),
        "z": ee.Image.cat(rain_z + sm_z).reproject(grid).reduceRegion(ee.Reducer.mean(), **region90),
        "cells": wpi.reduceRegion(ee.Reducer.count(), **region90).get("WPI"),
        "chirps_images": chirps.filterDate(f"{year}-01-01", f"{year + 1}-01-01").size(),
    }).getInfo()
    if not info["chirps_images"]:
        raise ValueError(f"Data hujan CHIRPS {year} belum tersedia")

    # 10 m download of the 90 m grid: every field pixel takes its 90 m cell, so areas follow the outline
    arr, profile = download_arrays(img, aoi, crs)
    w = arr[0]
    cls = np.full(w.shape, np.nan, dtype=np.float32)
    ok = np.isfinite(w)
    cls[ok] = np.digitize(w[ok], WL_THRESHOLDS, right=True) + 1
    save_cog([w, cls, arr[1], arr[2]], WATERLOGGING_BANDS, profile, dest)

    f = info["factors"] or {}
    z = info["z"] or {}
    return {
        "model": "Waterlogging potential (Output 5.2)",
        "bands": WATERLOGGING_BANDS,
        "year": year,
        "baseline": f"{base_years[0]}–{base_years[-1]}",
        "cells_90m": info["cells"],
        "field_ha": round(float(ok.sum()) * _px_ha(profile), 2),
        "wpi_mean": _mean(w), "wpi_min": _r(np.nanmin(w)) if ok.any() else None,
        "wpi_max": _r(np.nanmax(w)) if ok.any() else None,
        "static_mean": _mean(arr[1]), "dynamic_mean": _mean(arr[2]),
        "thresholds": [round(t, 4) for t in WL_THRESHOLDS],
        "class_ha": _areas(cls, WL_CLASS, _px_ha(profile)),
        "factors": [{"factor": k, "value": _r(f.get(k)), "weight": wt,
                     "contribution": _r(f[k] * wt) if f.get(k) is not None else None}
                    for k, wt in WL_WEIGHTS.items()],
        "monthly": [{"month": m, "rain_z": _r(z.get(f"RAIN_Z_{m:02d}"), 2), "sm_z": _r(z.get(f"SM_Z_{m:02d}"), 2)}
                    for m in range(1, 13)],
    }


# ============================================================================ Output 3.1: condition (30D-04)
COND_BASELINE_YEARS = 5
COND_PERIOD_STARTS = [1, 3, 5, 7, 9, 11]  # P01..P06, two months each
COND_CS_CLEAR = 0.60
COND_MIN_S2_CLEAR_DAYS_PER_YEAR = 2
COND_MIN_BASELINE_VALID_YEARS = 3
COND_MIN_S2_MON_CLEAR_DAYS = 2
COND_MIN_S1_DATES = 3
# 30D-04 thresholds = max(percentile over the plantation, floor), per period. The AOI run takes the percentiles
# over the whole Output 1 boundary, so a region-wide dry spell is not an alert. Per field the percentiles come
# from the surrounding plantation: the Output 1 boundary within COND_CONTEXT_M, or all land there when the
# field is outside the delivered AOI. A field of COND_SELF_CONTEXT_HA or more is an estate on its own and is
# its own context, like the notebook's AOI. The percentiles are taken at COND_THRESHOLD_SCALE (30D-04 uses 20 m
# over a batch export; 60 m keeps an interactive request inside GEE's memory limit, p80/p90 barely move).
COND_CONTEXT_M = 2000
COND_TILE_PX = 200  # 6-year daily composites: one request per 200 x 200 px (400 ha) stays under GEE's memory cap
COND_SELF_CONTEXT_HA = 500
COND_THRESHOLD_SCALE = 60
COND_PERCENTILE = {"GREEN": 80, "NDRE": 80, "NDMI": 80, "GREEN_STRONG": 92, "NDRE_STRONG": 92, "NDMI_STRONG": 92,
                   "VV": 90, "VH": 90, "VV_VH": 90}
COND_FLOORS = {"GREEN": 0.06, "NDRE": 0.05, "NDMI": 0.08, "GREEN_STRONG": 0.10, "NDRE_STRONG": 0.08,
               "NDMI_STRONG": 0.12, "VV": 2.0, "VH": 2.0, "VV_VH": 1.5}
COND_METRIC = {"GREEN": "GREEN", "NDRE": "NDRE", "NDMI": "NDMI", "GREEN_STRONG": "GREEN", "NDRE_STRONG": "NDRE",
               "NDMI_STRONG": "NDMI", "VV": "VV", "VH": "VH", "VV_VH": "VV_MINUS_VH"}
COND_MIN_RADAR_INDICATORS = 2
COND_MIN_TOTAL_VALID_PERIODS = 4
COND_MIN_PATCH_PX = 10
COND_CLASS = {0: "Insufficient data", 1: "Stable / expected", 2: "Watch",
              3: "Persistent stress – inspection", 4: "High persistent anomaly"}
COND_CONF = {1: "Low", 2: "Medium", 3: "High"}
COND_PERIOD_BANDS = ["PERIOD_CLASS", "TOTAL_VALID", "S2_VALID", "CONFIDENCE", "GREEN_FLAG", "NDRE_FLAG",
                     "NDMI_FLAG", "RADAR_CONFIRM", "RADAR_ONLY", "GREENNESS_DECLINE"]
CONDITION_BANDS = ["CONDITION_CLASS", "RISK_SCORE", "ANNUAL_CONFIDENCE", "ALERT_PERIODS", "REASON_CODE"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


@lru_cache(maxsize=1)
def _plantation_boundary():
    """Output 1 plantation boundary of the delivered AOI (SIAK_AOI01 2025), one shapely geometry."""
    with open(palm_data_dir() / "plantation_boundary.geojson", encoding="utf-8") as f:
        return unary_union([shape(ft["geometry"]) for ft in json.load(f)["features"]]).buffer(0)


def _cond_context(aoi_geojson: dict) -> tuple[ee.Geometry, str]:
    """Where the per-period percentile thresholds are taken: (geometry, "field" | "plantation" | "land")."""
    field = shape(aoi_geojson)
    if shape(transform_geom("EPSG:4326", f"EPSG:{utm_epsg(field.centroid.x, field.centroid.y)}", aoi_geojson)).area             >= COND_SELF_CONTEXT_HA * 1e4:
        return ee.Geometry(aoi_geojson), "field"
    ring = field.buffer(COND_CONTEXT_M / 111_320)  # degrees; ~2 km near the equator
    palm = _plantation_boundary().intersection(ring)
    if palm.area > field.area:
        return ee.Geometry(mapping(palm.union(field).simplify(0.0002))), "plantation"
    return ee.Geometry(mapping(ring.simplify(0.0002))), "land"


def _cond_window(year: int, start_month: int) -> tuple[str, str]:
    end = date(year + (start_month + 2 > 12), (start_month + 1) % 12 + 1, 1)
    return f"{year}-{start_month:02d}-01", end.isoformat()


def _empty(bands: list[str]):
    """One fully masked image, so a window without scenes yields masked bands (count 0), not a missing band."""
    return ee.ImageCollection([ee.Image.constant([0] * len(bands)).rename(bands).toFloat().updateMask(0)])


def _cond_s2(aoi, start: str, end: str):
    """30B: one cs_cdf quality mosaic per date, Cloud Score+ AND SCL 4/5/6, then median over the dates."""
    s2 = (ee.ImageCollection(S2_SR).filterBounds(aoi).filterDate(start, end)
          .linkCollection(ee.ImageCollection(CS_PLUS), ["cs_cdf"])
          .map(lambda i: i.set("DAY", i.date().format("YYYY-MM-dd"))))

    def daily(day):
        d = ee.Date(day)
        img = s2.filterDate(d, d.advance(1, "day")).qualityMosaic("cs_cdf")
        scl = img.select("SCL")
        ok = img.select("cs_cdf").gte(COND_CS_CLEAR).And(scl.eq(4).Or(scl.eq(5)).Or(scl.eq(6)))
        r = img.select(["B2", "B4", "B8", "B8A", "B5", "B11"]).multiply(0.0001).updateMask(ok)
        nir, red, blue = r.select("B8"), r.select("B4"), r.select("B2")
        term = nir.multiply(2).add(1)
        return ee.Image.cat([
            nir.subtract(red).divide(nir.add(red)).rename("NDVI"),
            nir.subtract(red).multiply(2.5).divide(nir.add(red.multiply(6)).subtract(blue.multiply(7.5)).add(1)).rename("EVI"),
            term.subtract(term.pow(2).subtract(nir.subtract(red).multiply(8)).max(0).sqrt()).divide(2).rename("MSAVI"),
            r.normalizedDifference(["B8A", "B5"]).rename("NDRE").resample("bilinear"),
            r.normalizedDifference(["B8A", "B11"]).rename("NDMI").resample("bilinear"),
            ee.Image(1).rename("VALID").updateMask(ok),
        ]).toFloat()  # one band type for every image, incl. _empty()

    col = ee.ImageCollection.fromImages(ee.List(s2.aggregate_array("DAY")).distinct().map(daily)).merge(
        _empty(["NDVI", "EVI", "MSAVI", "NDRE", "NDMI", "VALID"]))
    days = col.select("VALID").count()
    return col.select(["NDVI", "EVI", "MSAVI", "NDRE", "NDMI"]).median(), days


def _cond_s1(aoi, start: str, end: str):
    """30B: ascending IW, incidence 30-45 deg, median per date, then median over the dates (dB)."""
    s1 = (ee.ImageCollection(S1_GRD).filterBounds(aoi).filterDate(start, end)
          .filter(ee.Filter.eq("instrumentMode", "IW")).filter(ee.Filter.eq("resolution_meters", 10))
          .filter(ee.Filter.eq("orbitProperties_pass", "ASCENDING"))
          .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
          .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VH"))
          .map(lambda i: i.set("DAY", i.date().format("YYYY-MM-dd"))))

    def params(img):
        ang = img.select("angle")
        ok = ang.gt(30).And(ang.lt(45))
        vv, vh = img.select("VV"), img.select("VH")
        return ee.Image.cat([vv.rename("VV"), vh.rename("VH"), vv.subtract(vh).rename("VV_MINUS_VH"),
                             ee.Image(1).rename("VALID")]).updateMask(ok).toFloat()

    def daily(day):
        d = ee.Date(day)
        return s1.filterDate(d, d.advance(1, "day")).map(params).median()

    col = ee.ImageCollection.fromImages(ee.List(s1.aggregate_array("DAY")).distinct().map(daily)).merge(
        _empty(["VV", "VH", "VV_MINUS_VH", "VALID"]))
    return col.select(["VV", "VH", "VV_MINUS_VH"]).median(), col.select("VALID").count()


def _cond_period(context, year: int, start_month: int) -> tuple[ee.Image, dict]:
    """30B-30D04 for one two-month period: anomaly vs the 5 previous years -> period class + flags.

    Composites cover the context, because the thresholds are percentiles over it (one getInfo).
    """
    aoi = context
    s2_mon, s2_days = _cond_s2(aoi, *_cond_window(year, start_month))
    s1_mon, s1_dates = _cond_s1(aoi, *_cond_window(year, start_month))
    s2_years, s2_flags, s1_years, s1_flags = [], [], [], []
    for by in range(year - COND_BASELINE_YEARS, year):
        img, days = _cond_s2(aoi, *_cond_window(by, start_month))
        ok = days.gte(COND_MIN_S2_CLEAR_DAYS_PER_YEAR).unmask(0)
        s2_years.append(img.updateMask(ok))
        s2_flags.append(ok)
        img, dates = _cond_s1(aoi, *_cond_window(by, start_month))
        ok = dates.gte(COND_MIN_S1_DATES).unmask(0)
        s1_years.append(img.updateMask(ok))
        s1_flags.append(ok)
    s2_base_years = ee.ImageCollection(s2_flags).sum()
    s1_base_years = ee.ImageCollection(s1_flags).sum()
    s2_base = ee.ImageCollection(s2_years).median().updateMask(s2_base_years.gte(COND_MIN_BASELINE_VALID_YEARS))
    s1_base = ee.ImageCollection(s1_years).median().updateMask(s1_base_years.gte(COND_MIN_BASELINE_VALID_YEARS))

    s2_days, s1_dates = s2_days.unmask(0), s1_dates.unmask(0)
    s2_valid = s2_base_years.gte(COND_MIN_BASELINE_VALID_YEARS).And(s2_days.gte(COND_MIN_S2_MON_CLEAR_DAYS))
    s1_valid = s1_base_years.gte(COND_MIN_BASELINE_VALID_YEARS).And(s1_dates.gte(COND_MIN_S1_DATES))
    decline = s2_base.subtract(s2_mon).max(0).updateMask(s2_valid)  # = -anomaly, floored at 0
    s1_abs = s1_mon.subtract(s1_base).abs().updateMask(s1_valid)

    green = decline.select(["NDVI", "EVI", "MSAVI"]).reduce(ee.Reducer.median()).rename("GREEN")
    metrics = ee.Image.cat([green, decline.select(["NDRE", "NDMI"]), s1_abs])
    stats = metrics.reduceRegion(ee.Reducer.percentile(sorted(set(COND_PERCENTILE.values()))), context,
                                 COND_THRESHOLD_SCALE, maxPixels=1e13, tileScale=16, bestEffort=True).getInfo()
    t = {k: round(max(stats.get(f"{COND_METRIC[k]}_p{q}") or COND_FLOORS[k], COND_FLOORS[k]), 4)
         for k, q in COND_PERCENTILE.items()}
    flag = lambda img, thr: img.gte(thr).And(s2_valid).unmask(0)  # noqa: E731
    g, n, m = flag(green, t["GREEN"]), flag(decline.select("NDRE"), t["NDRE"]), flag(decline.select("NDMI"), t["NDMI"])
    optical_alert = g.add(n).add(m).gte(2)
    strong = (flag(green, t["GREEN_STRONG"]).add(flag(decline.select("NDRE"), t["NDRE_STRONG"]))
              .add(flag(decline.select("NDMI"), t["NDMI_STRONG"])))
    optical_severe = optical_alert.And(strong.gte(1))
    radar = lambda b, thr: s1_abs.select(b).gte(thr).And(s1_valid).unmask(0)  # noqa: E731
    radar_confirm = radar("VV", t["VV"]).add(radar("VH", t["VH"])).add(radar("VV_MINUS_VH", t["VV_VH"])).gte(
        COND_MIN_RADAR_INDICATORS)
    radar_only = s2_valid.Not().And(s1_valid).And(radar_confirm)

    s2_conf = (ee.Image(0).where(s2_valid.And(s2_days.gte(2)).And(s2_days.lte(3)), 1)
               .where(s2_valid.And(s2_days.gte(4)).And(s2_days.lte(5)), 2).where(s2_valid.And(s2_days.gte(6)), 3))
    s1_conf = (ee.Image(0).where(s1_valid.And(s1_dates.eq(3)), 1)
               .where(s1_valid.And(s1_dates.gte(4)).And(s1_dates.lte(5)), 2).where(s1_valid.And(s1_dates.gte(6)), 3))
    confidence = s2_conf.add(s1_conf).divide(2)
    total_valid = s2_valid.Or(s1_valid)
    period_class = (ee.Image(0).where(total_valid, 1)
                    .where(total_valid.And(optical_alert.Or(radar_only)), 2)
                    .where(s2_valid.And(optical_severe.Or(optical_alert.And(radar_confirm))), 3)
                    .where(s2_valid.And(optical_severe).And(radar_confirm).And(confidence.gte(2)), 4))
    img = ee.Image.cat([period_class, total_valid, s2_valid, confidence, g, n, m, radar_confirm, radar_only,
                        green.unmask(-9999)]).rename(COND_PERIOD_BANDS).toFloat()
    return img, t


def _max_run(alert: np.ndarray) -> np.ndarray:
    """Longest run of consecutive alert periods per pixel (alert: periods x rows x cols, no wrap)."""
    run = best = np.zeros(alert.shape[1:], dtype=np.int16)
    for a in alert:
        run = np.where(a, run + 1, 0)
        best = np.maximum(best, run)
    return best


def condition_annual(p: dict) -> dict:
    """30D-04 annual rules on per-period arrays (each periods x rows x cols, 0/1 or class)."""
    valid_n = p["TOTAL_VALID"].sum(0)
    optical_n = p["S2_VALID"].sum(0)
    pc = p["PERIOD_CLASS"]
    alert, insp, high = (pc >= 2).sum(0), (pc >= 3).sum(0), (pc >= 4).sum(0)
    radar_only = p["RADAR_ONLY"].sum(0)
    max_pc = pc.max(0)
    run = _max_run(pc >= 2)
    with np.errstate(invalid="ignore", divide="ignore"):
        mean_conf = np.where(valid_n == 0, 0, p["CONFIDENCE"].sum(0) / np.maximum(valid_n, 1))
    enough = valid_n >= COND_MIN_TOTAL_VALID_PERIODS

    conf = np.zeros(valid_n.shape, dtype=np.float32)
    conf[enough] = 1
    conf[enough & (optical_n >= 2)] = 2
    conf[enough & (optical_n >= 4) & (mean_conf >= 2)] = 3

    raw = np.zeros(valid_n.shape, dtype=np.float32)
    raw[enough] = 1
    raw[enough & ((alert >= 2) | (max_pc >= 3) | (radar_only >= 2))] = 2
    raw[enough & (optical_n >= 2) & (((insp >= 2) & (run >= 2)) | ((alert >= 3) & (insp >= 1)))] = 3
    raw[enough & (optical_n >= 3) & (((high >= 2) & (run >= 2)) | ((insp >= 3) & (run >= 3)))] = 4
    priority = raw >= 3
    cls = np.where(priority & ~_mmu(priority, COND_MIN_PATCH_PX), 2, raw)  # 0.10 ha patch filter

    score = _round_half_up(np.minimum(alert / 6 * 25 + insp / 6 * 30 + high / 6 * 20 + run / 6 * 20
                                      + radar_only / 6 * 5, 100))
    score = np.where(cls == 0, 0, np.where(cls == 1, np.minimum(score, 19), score))
    reason = (p["GREEN_FLAG"].sum(0, where=pc >= 2) >= 1) * 1 + (p["NDRE_FLAG"].sum(0, where=pc >= 2) >= 1) * 2 \
        + (p["NDMI_FLAG"].sum(0, where=pc >= 2) >= 1) * 4 + (p["RADAR_CONFIRM"].sum(0, where=pc >= 2) >= 1) * 8 \
        + (run >= 2) * 16 + (run >= 3) * 32 + (radar_only >= 1) * 64
    reason = np.where(cls < 2, 0, reason)
    return {"class": cls, "score": score.astype(np.float32), "confidence": conf, "alert": alert.astype(np.float32),
            "reason": reason.astype(np.float32)}


def palm_condition(aoi_geojson: dict, date_from: str, date_to_exclusive: str, dest: Path) -> dict:
    """Condition / inspection priority for the year of date_from: 6 two-month periods vs the 5 previous years."""
    init_ee()
    aoi = ee.Geometry(aoi_geojson)
    crs = aoi_crs(aoi)
    year = _year(date_from, 2020)  # Sentinel-2 SR + Cloud Score+ from 2017 -> baseline needs 5 years
    images = ee.ImageCollection(S2_SR).filterBounds(aoi).filterDate(f"{year}-01-01", f"{year + 1}-01-01").size().getInfo()
    if images == 0:
        raise ValueError(f"Tidak ada citra Sentinel-2 di lahan ini pada {year}")

    context, context_kind = _cond_context(aoi_geojson)

    def run(month):
        img, thresholds = _cond_period(context, year, month)
        return (*download_arrays(img, aoi, crs, tile_px=COND_TILE_PX), thresholds)

    with ThreadPoolExecutor(max_workers=3) as pool:
        downloads = list(pool.map(run, COND_PERIOD_STARTS))
    profile = downloads[0][1]
    inside = np.isfinite(downloads[0][0][0])
    stacks = {b: np.stack([np.nan_to_num(d[0][i]) for d in downloads]) for i, b in enumerate(COND_PERIOD_BANDS)}
    a = condition_annual(stacks)
    out = [np.where(inside, a[k], np.nan) for k in ("class", "score", "confidence", "alert", "reason")]
    save_cog(out, CONDITION_BANDS, profile, dest)

    px = _px_ha(profile)
    green = np.stack([d[0][COND_PERIOD_BANDS.index("GREENNESS_DECLINE")] for d in downloads])
    green[green == -9999] = np.nan
    n_in = max(int(inside.sum()), 1)
    periods = []
    for k, m in enumerate(COND_PERIOD_STARTS):
        pc = stacks["PERIOD_CLASS"][k]
        periods.append({
            "period": f"{MONTHS[m - 1]}–{MONTHS[m]}",
            "valid_pct": round(100 * float((stacks["TOTAL_VALID"][k] * inside).sum()) / n_in, 1),
            "alert_pct": round(100 * float(((pc >= 2) & inside).sum()) / n_in, 1),
            "inspection_pct": round(100 * float(((pc >= 3) & inside).sum()) / n_in, 1),
            "greenness_decline": _mean(green[k], inside),
            "thresholds": downloads[k][2],
        })
    return {
        "model": "Condition & inspection priority (Output 3.1, core 30D-04)",
        "bands": CONDITION_BANDS,
        "year": year,
        "baseline": f"{year - COND_BASELINE_YEARS}–{year - 1}",
        "images": images,
        "field_ha": round(float(inside.sum()) * px, 2),
        "risk_mean": _mean(out[1]),
        "class_ha": _areas(out[0], COND_CLASS, px),
        "confidence_ha": _areas(out[2], COND_CONF, px),
        "threshold_context": context_kind,
        "periods": periods,
    }


# ============================================================================ Output 2: tree age proxy
AGE_SCALE_M = 30
AGE = {  # METHOD, locked (validated for reference year 2025: S2 2019-2025, Landsat events 2001-2018)
    "S2_CLEAR": 0.60, "S2_MIN_CLEAR_OBS": 5, "S2_NDVI_DECLINE": -0.08, "S2_NBR_DECLINE": -0.10,
    "S2_MAX_REC_NDVI": 0.08, "S2_MAX_REC_NBR": 0.10, "S2_CUR_REC_NDVI": 0.04, "S2_CUR_REC_NBR": 0.05,
    "S2_MIN_POST_YEARS": 2,
    "L_MIN_CLEAR_OBS": 3, "L_NDVI_DECLINE": -0.08, "L_NBR_DECLINE": -0.12, "L_NDMI_DECLINE": -0.10,
    "L_BSI_INCREASE": 0.05, "PRE_NDVI_MIN": 0.55, "PRE_NBR_MIN": 0.30, "L_REC_NDVI": 0.08, "L_REC_NBR": 0.10,
    "CUR_NDVI_MIN": 0.55, "CUR_NBR_MIN": 0.35, "L_MIN_POST_YEARS": 2,
    "MIN_PATCH_PX": 6,
    "MED_DIST": 0.28, "MED_REC_NDVI": 0.10, "MED_REC_NBR": 0.12, "MED_PATCH": 10,
    "HIGH_DIST": 0.40, "HIGH_REC_NDVI": 0.15, "HIGH_REC_NBR": 0.18, "HIGH_PATCH": 20,
}
AGE_LANDSAT_START = 2000
AGE_CLASS = {0: "No event detected", 1: "20–24 years", 2: "15–19 years", 3: "10–14 years", 4: "5–9 years",
             5: "0–4 years"}
AGE_SOURCE = {1: "Landsat", 2: "Sentinel-2", 3: "Landsat (S2 uncertain)"}
AGE_BANDS = ["AGE_CLASS", "EVENT_YEAR", "AGE_PROXY", "SOURCE_CODE", "LANDSAT_CONFIDENCE"]
L57 = ["SR_B1", "SR_B2", "SR_B3", "SR_B4", "SR_B5", "SR_B7"]
L89 = ["SR_B2", "SR_B3", "SR_B4", "SR_B5", "SR_B6", "SR_B7"]
LANDSAT = [("LANDSAT/LT05/C02/T1_L2", L57), ("LANDSAT/LE07/C02/T1_L2", L57),
           ("LANDSAT/LC08/C02/T1_L2", L89), ("LANDSAT/LC09/C02/T1_L2", L89)]


def age_bins(event_year: np.ndarray, year: int) -> np.ndarray:
    """5-year bins ending at the reference year (2001-05 ... 2021-25 for 2025); 0 = no event."""
    out = np.zeros(event_year.shape, dtype=np.float32)
    for k in range(1, 6):
        lo = year - 24 + 5 * (k - 1)
        out[(event_year >= lo) & (event_year <= lo + 4)] = k
    return out


def _landsat_year(aoi, y: int) -> ee.Image:
    """Annual median NDVI/NDMI/NBR/BSI of Landsat 5/7/8/9 C2 L2 (QA clear, not saturated) + clear count."""
    def prep(bands):
        def f(img):
            ok = img.select("QA_PIXEL").bitwiseAnd(31).eq(0).And(img.select("QA_RADSAT").eq(0))
            o = img.select(bands, ["BLUE", "GREEN", "RED", "NIR", "SWIR1", "SWIR2"]).multiply(0.0000275).add(-0.2).updateMask(ok)
            bsi = o.expression("((S + R) - (N + B)) / ((S + R) + (N + B))",
                               {"S": o.select("SWIR1"), "R": o.select("RED"), "N": o.select("NIR"), "B": o.select("BLUE")})
            return ee.Image.cat([o.normalizedDifference(["NIR", "RED"]).rename("NDVI"),
                                 o.normalizedDifference(["NIR", "SWIR1"]).rename("NDMI"),
                                 o.normalizedDifference(["NIR", "SWIR2"]).rename("NBR"),
                                 bsi.rename("BSI"), o.select("RED")]).toFloat()
        return f

    col = _empty(["NDVI", "NDMI", "NBR", "BSI", "RED"])
    for cid, bands in LANDSAT:
        col = col.merge(ee.ImageCollection(cid).filterBounds(aoi).filterDate(f"{y}-01-01", f"{y + 1}-01-01").map(prep(bands)))
    return col.select(["NDVI", "NDMI", "NBR", "BSI"]).median().addBands(col.select("RED").count().rename("CLEAR_OBS"))


def _s2_year(aoi, y: int) -> ee.Image:
    """Annual median NDVI/NBR of Sentinel-2 (Cloud Score+ >= 0.60, granule edges masked) + clear count."""
    def prep(img):
        ok = img.select("B8A").mask().And(img.select("B9").mask()).And(img.select("cs_cdf").gte(AGE["S2_CLEAR"]))
        r = img.select(["B4", "B8", "B12"]).multiply(0.0001).updateMask(ok)
        return ee.Image.cat([r.normalizedDifference(["B8", "B4"]).rename("NDVI"),
                             r.normalizedDifference(["B8", "B12"]).rename("NBR"), r.select("B4")]).toFloat()

    col = (ee.ImageCollection(S2_SR).filterBounds(aoi).filterDate(f"{y}-01-01", f"{y + 1}-01-01")
           .filter(ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE", 80))
           .linkCollection(ee.ImageCollection(CS_PLUS), ["cs_cdf"]).map(prep).merge(_empty(["NDVI", "NBR", "B4"])))
    return col.select(["NDVI", "NBR"]).median().addBands(col.select("B4").count().rename("CLEAR_OBS"))


def _strongest(transitions: list[tuple[int, np.ndarray, np.ndarray]]):
    """qualityMosaic(score) over (year, score, valid): best score, its year, and pixels with any valid transition."""
    shp = transitions[0][1].shape
    best, best_year, covered = np.full(shp, -np.inf), np.zeros(shp, dtype=np.float32), np.zeros(shp, dtype=bool)
    for y, score, ok in transitions:
        take = ok & (score > best)
        best[take], best_year[take] = score[take], y
        covered |= ok
    best[~covered] = np.nan
    return best, np.where(best > 0, best_year, 0), covered


def _patch_size(cls: np.ndarray, mask: np.ndarray, cap: int = 100) -> np.ndarray:
    """connectedPixelCount(cap, eightConnected): size of each pixel's same-class 8-connected patch."""
    out = np.zeros(cls.shape, dtype=np.float32)
    for k in np.unique(cls[mask]):
        labels, n = ndimage.label(mask & (cls == k), structure=np.ones((3, 3)))
        sizes = np.bincount(labels.ravel())
        out[labels > 0] = np.minimum(sizes[labels[labels > 0]], cap)
    return out


def _mode3(cls: np.ndarray) -> np.ndarray:
    """focalMode radius 1 square: most frequent class in the 3x3 window (ties -> lowest class)."""
    k = np.unique(cls)
    counts = np.stack([ndimage.convolve((cls == v).astype(np.float32), np.ones((3, 3)), mode="constant") for v in k])
    return k[np.argmax(counts, axis=0)].astype(np.float32)


def age_from_annual(L: dict, S: dict, year: int) -> dict:
    """Output 2 rules (stages A-D) on annual arrays: L / S = {year: {band: array}} for Landsat / Sentinel-2."""
    a = AGE
    s2_start, ev_start, ev_end = year - 6, year - 24, year - 7
    with np.errstate(invalid="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # all-NaN windows (cloudy years) stay NaN
        # ---- Sentinel-2 decline (S2_START+1..year) and regrowth ----
        tr = []
        for y in range(s2_start + 1, year + 1):
            p, c = S[y - 1], S[y]
            ok = (p["CLEAR_OBS"] >= a["S2_MIN_CLEAR_OBS"]) & (c["CLEAR_OBS"] >= a["S2_MIN_CLEAR_OBS"])
            dn, db = c["NDVI"] - p["NDVI"], c["NBR"] - p["NBR"]
            ok &= np.isfinite(dn) & np.isfinite(db)
            strong = (dn <= a["S2_NDVI_DECLINE"]) & (db <= a["S2_NBR_DECLINE"])
            tr.append((y, np.where(strong, np.maximum(-dn, 0) + np.maximum(-db, 0), 0), ok))
        _, s2_year, s2_cov = _strongest(tr)
        final = S[year]
        s2_flag = np.zeros(s2_year.shape, dtype=bool)
        for ey in range(s2_start + 1, year - 1):  # events with >= 2 post-event years
            post = [S[k] for k in range(ey + 1, year + 1)]
            pmax_n = np.nanmax([q["NDVI"] for q in post], axis=0)
            pmax_b = np.nanmax([q["NBR"] for q in post], axis=0)
            post_n = sum((q["CLEAR_OBS"] >= a["S2_MIN_CLEAR_OBS"]).astype(int) for q in post)
            ev = S[ey]
            ok = ((pmax_n - ev["NDVI"] >= a["S2_MAX_REC_NDVI"]) & (pmax_b - ev["NBR"] >= a["S2_MAX_REC_NBR"])
                  & (final["NDVI"] - ev["NDVI"] >= a["S2_CUR_REC_NDVI"]) & (final["NBR"] - ev["NBR"] >= a["S2_CUR_REC_NBR"])
                  & (post_n >= a["S2_MIN_POST_YEARS"]))
            s2_flag |= (s2_year == ey) & ok
        s2_status = np.zeros(s2_year.shape, dtype=np.float32)
        s2_status[(s2_year > 0) & (s2_year <= year - 2)] = 1
        s2_status[s2_flag] = 2
        s2_status[s2_year >= year - 1] = 3
        s2_status[~s2_cov] = 0

        # ---- Landsat historical disturbance (ev_start..ev_end) and recovery ----
        tr = []
        for y in range(ev_start, ev_end + 1):
            p, e = L[y - 1], L[y]
            ok = (p["CLEAR_OBS"] >= a["L_MIN_CLEAR_OBS"]) & (e["CLEAR_OBS"] >= a["L_MIN_CLEAR_OBS"])
            d = {b: e[b] - p[b] for b in ("NDVI", "NDMI", "NBR", "BSI")}
            ok &= np.isfinite(d["NDVI"]) & np.isfinite(d["NBR"])
            pre = (p["NDVI"] >= a["PRE_NDVI_MIN"]) & (p["NBR"] >= a["PRE_NBR_MIN"])
            support = (d["NDMI"] <= a["L_NDMI_DECLINE"]) | (d["BSI"] >= a["L_BSI_INCREASE"])
            strong = (d["NDVI"] <= a["L_NDVI_DECLINE"]) & (d["NBR"] <= a["L_NBR_DECLINE"]) & support & pre
            score = (np.maximum(-d["NDVI"], 0) + np.maximum(-d["NBR"], 0) + 0.5 * np.maximum(-np.nan_to_num(d["NDMI"]), 0)
                     + 0.5 * np.maximum(np.nan_to_num(d["BSI"]), 0))
            tr.append((y, np.where(strong, score, 0), ok))
        l_score, l_year, l_cov = _strongest(tr)
        final = L[year]
        l_flag, l_post = np.zeros(l_year.shape, dtype=bool), np.zeros(l_year.shape)
        rec_n, rec_b = np.full(l_year.shape, np.nan), np.full(l_year.shape, np.nan)
        for ey in range(ev_start, ev_end + 1):
            here = l_year == ey
            if not here.any():
                continue
            post = [L[k] for k in range(ey + 1, min(ey + 5, year) + 1)]
            r_n = np.nanmax([q["NDVI"] for q in post], axis=0) - L[ey]["NDVI"]
            r_b = np.nanmax([q["NBR"] for q in post], axis=0) - L[ey]["NBR"]
            post_n = sum((q["CLEAR_OBS"] >= a["L_MIN_CLEAR_OBS"]).astype(int) for q in post)
            ok = ((r_n >= a["L_REC_NDVI"]) & (r_b >= a["L_REC_NBR"]) & (post_n >= a["L_MIN_POST_YEARS"])
                  & (final["NDVI"] >= a["CUR_NDVI_MIN"]) & (final["NBR"] >= a["CUR_NBR_MIN"]))
            l_flag |= here & ok
            l_post[here], rec_n[here], rec_b[here] = post_n[here], r_n[here], r_b[here]
        l_status = np.zeros(l_year.shape, dtype=np.float32)
        l_status[l_year > 0] = 1
        l_status[(l_year > 0) & (l_post < a["L_MIN_POST_YEARS"])] = 3
        l_status[l_flag] = 2
        l_status[~l_cov] = 0

        # ---- 19B cleaning: 3x3 mode of the confirmed class, patches >= 6 px, confidence ----
        cand = l_status == 2
        mode = _mode3(np.where(cand, age_bins(l_year, year), 0))
        patch = _patch_size(mode, cand)
        clean = cand & (patch >= a["MIN_PATCH_PX"]) & (mode > 0)
        l_event = np.where(clean, l_year, 0)
        medium = (l_score >= a["MED_DIST"]) & (rec_n >= a["MED_REC_NDVI"]) & (rec_b >= a["MED_REC_NBR"]) & (patch >= a["MED_PATCH"])
        high = (l_score >= a["HIGH_DIST"]) & (rec_n >= a["HIGH_REC_NDVI"]) & (rec_b >= a["HIGH_REC_NBR"]) & (patch >= a["HIGH_PATCH"])
        l_conf = np.where(clean, np.where(high, 3, np.where(medium, 2, 1)), 0).astype(np.float32)

        # ---- final integration: a confirmed Sentinel-2 regrowth overrides Landsat ----
        l_valid = (l_event >= ev_start) & (l_event <= ev_end)
        s2_valid = (s2_status == 2) & (s2_year >= s2_start) & (s2_year <= year)
        s2_unc = (s2_status == 1) | (s2_status == 3)
        event = np.where(s2_valid, s2_year, np.where(l_valid, l_event, 0)).astype(np.float32)
        source = np.zeros(event.shape, dtype=np.float32)
        source[l_valid] = 1
        source[s2_valid] = 2
        source[l_valid & s2_unc & ~s2_valid] = 3
    detected = event > 0
    return {"class": age_bins(event, year), "event": np.where(detected, event, np.nan),
            "age": np.where(detected, year - event, np.nan), "source": source, "confidence": l_conf}


def palm_age(aoi_geojson: dict, date_from: str, date_to_exclusive: str, dest: Path) -> dict:
    """Tree age proxy at the end of the year of date_from from disturbance -> regrowth events (30 m).

    GEE only builds the annual composites (one small download per year); the stage A-D rules run in
    numpy, which keeps every request far below the interactive memory limit.
    """
    init_ee()
    aoi = ee.Geometry(aoi_geojson)
    crs = aoi_crs(aoi)
    year = _year(date_from, 2025)
    l_years, s_years = list(range(AGE_LANDSAT_START, year + 1)), list(range(year - 6, year + 1))
    jobs = [("L", y, _landsat_year(aoi, y)) for y in l_years] + [("S", y, _s2_year(aoi, y)) for y in s_years]
    with ThreadPoolExecutor(max_workers=2) as pool:  # 33 small requests; GEE caps concurrent ones per project
        got = list(pool.map(lambda j: download_arrays(j[2], aoi, crs, scale=AGE_SCALE_M), jobs))
    profile = got[0][1]
    L, S = {}, {}
    for (src, y, img), (arr, _) in zip(jobs, got):
        names = ["NDVI", "NDMI", "NBR", "BSI", "CLEAR_OBS"] if src == "L" else ["NDVI", "NBR", "CLEAR_OBS"]
        (L if src == "L" else S)[y] = dict(zip(names, arr))
    inside = np.isfinite(L[year]["CLEAR_OBS"])
    for d in list(L.values()) + list(S.values()):
        d["CLEAR_OBS"] = np.nan_to_num(d["CLEAR_OBS"])
    r = age_from_annual(L, S, year)
    cut = lambda x: np.where(inside, x, np.nan).astype(np.float32)  # noqa: E731
    out = [cut(r["class"]), cut(r["event"]), cut(r["age"]), cut(r["source"]), cut(r["confidence"])]
    save_cog(out, AGE_BANDS, profile, dest)

    px = _px_ha(profile)
    det = inside & np.isfinite(out[1])
    n = max(int(inside.sum()), 1)
    return {
        "model": "Tree age proxy (Output 2)",
        "bands": AGE_BANDS,
        "year": year,
        "window": f"{year - 24}–{year}",
        "field_ha": round(float(inside.sum()) * px, 2),
        "detected_pct": round(100 * float(det.sum()) / n, 1),
        "no_event_pct": round(100 * float((inside & (out[0] == 0)).sum()) / n, 1),
        "age_median": _r(np.median(out[2][det]), 1) if det.any() else None,
        "class_ha": _areas(out[0], AGE_CLASS, px),
        "source_ha": _areas(out[3], AGE_SOURCE, px),
        "event_years": {str(int(y)): int(c) for y, c in zip(*np.unique(out[1][det], return_counts=True))},
        "series": [{"year": y, "ndvi": _mean(L[y]["NDVI"], inside), "nbr": _mean(L[y]["NBR"], inside)} for y in l_years],
    }


# ============================================================================ Output 1: palm cover
COVER_TRAINING_YEAR = 2025
COVER_CS_CLEAR = 0.60
COVER_CONTEXT_M = 250  # contextual V2 looks up to 250 m from raw palm, so the run covers a 250 m ring
COVER_RF = dict(numberOfTrees=500, minLeafPopulation=2, bagFraction=0.7, seed=42)
COVER_MAX_PX_POLYGON, COVER_MAX_PX_CLASS = 200, 600
COVER_CONF_THRESHOLD = 0.60
COVER_RADAR_FULL = 0.995
COVER_MMU_PX = 50  # 0.50 ha at 10 m
S2_BANDS = ["B2", "B3", "B4", "B5", "B6", "B7", "B8", "B8A", "B11", "B12"]
ROBUST_BANDS = ["NDVI", "NDMI", "NDRE", "EVI", "VV_ASC", "VH_ASC", "RATIO_ASC", "VV_DESC", "VH_DESC", "RATIO_DESC"]
COVER_CLASS5 = {1: "Palm", 2: "Forest / other trees", 3: "Open / bare", 4: "Built-up", 5: "Water"}
COVER_CLASS3 = {0: "Non-palm", 1: "Palm", 2: "Ambiguous"}
COVER_BANDS = ["PALM_CLASS", "CLEAN_PALM", "LAND_COVER", "PALM_PROBABILITY", "CONFIDENCE"]


@lru_cache(maxsize=1)
def _cover_training() -> dict:
    with open(palm_data_dir() / "o1_training_aoi01.geojson", encoding="utf-8") as f:
        return json.load(f)


def _cover_optical(geom, year: int) -> ee.Image:
    def clean(img):
        ok = img.select("cs_cdf").gte(COVER_CS_CLEAR)
        edge = img.select("B8A").mask().updateMask(img.select("B9").mask())
        return img.updateMask(ok).updateMask(edge).select(S2_BANDS).multiply(0.0001)

    s = (ee.ImageCollection(S2_SR).filterBounds(geom).filterDate(f"{year}-01-01", f"{year + 1}-01-01")
         .linkCollection(ee.ImageCollection(CS_PLUS), ["cs_cdf"]).map(clean).median())
    eps = 0.000001
    nd = lambda a, b: s.expression("(A - B) / (A + B + e)", {"A": s.select(a), "B": s.select(b), "e": eps})  # noqa: E731
    evi = s.expression("2.5 * ((N - R) / (N + 6 * R - 7.5 * B + 1))",
                       {"N": s.select("B8"), "R": s.select("B4"), "B": s.select("B2")})
    return ee.Image.cat([nd("B8", "B4").rename("NDVI"), nd("B8A", "B11").rename("NDMI"),
                         nd("B8A", "B5").rename("NDRE"), evi.updateMask(evi.gte(-1).And(evi.lte(1))).rename("EVI")])


def _cover_radar(geom, year: int) -> tuple[ee.Image, dict]:
    """Per pass: median per relative orbit, tracks stacked best-coverage first (Stage 0 radar6)."""
    s1 = (ee.ImageCollection(S1_GRD).filterBounds(geom).filterDate(f"{year}-01-01", f"{year + 1}-01-01")
          .filter(ee.Filter.eq("instrumentMode", "IW")).filter(ee.Filter.eq("resolution_meters", 10))
          .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
          .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VH")).select(["VV", "VH"]))
    total = ee.Image(1).clip(geom).reduceRegion(ee.Reducer.count(), geom, 30, maxPixels=1e9).get("constant")
    passes = {"ASC": "ASCENDING", "DESC": "DESCENDING"}
    tracks = ee.Dictionary({k: s1.filter(ee.Filter.eq("orbitProperties_pass", v))
                            .aggregate_array("relativeOrbitNumber_start").distinct() for k, v in passes.items()}).getInfo()
    medians, cover = {}, {}
    for k, v in passes.items():
        for t in tracks[k]:
            img = s1.filter(ee.Filter.eq("orbitProperties_pass", v)).filter(ee.Filter.eq("relativeOrbitNumber_start", t)).median().clip(geom)
            medians[(k, t)] = img
            cover[f"{k}_{t}"] = ee.Number(img.select("VV").mask().reduceRegion(
                ee.Reducer.sum(), geom, 30, maxPixels=1e9).get("VV")).divide(total)
    cover = ee.Dictionary(cover).getInfo() if cover else {}
    out = []
    for k in passes:
        ranked = sorted(tracks[k], key=lambda t: cover[f"{k}_{t}"], reverse=True)
        if not ranked:  # Sentinel-1 flies descending only over Kalimantan; palm_cover then drops the _ASC bands
            continue
        top = medians[(k, ranked[0])]
        m = top if cover[f"{k}_{ranked[0]}"] >= COVER_RADAR_FULL else ee.ImageCollection([medians[(k, t)] for t in ranked]).mosaic()
        vv, vh = m.select("VV"), m.select("VH")
        out += [vv.rename(f"VV_{k}"), vh.rename(f"VH_{k}"), vv.subtract(vh).rename(f"RATIO_{k}")]
    if not out:
        raise ValueError(f"Tidak ada citra Sentinel-1 di lahan ini pada {year}")
    return ee.Image.cat(out), {k: len(tracks[k]) for k in passes}


def _cover_stack(geom, year: int) -> tuple[ee.Image, dict]:
    radar, radar_info = _cover_radar(geom, year)
    stack = _cover_optical(geom, year).addBands(radar)
    return stack.updateMask(stack.mask().reduce(ee.Reducer.min())).toFloat(), radar_info


def _cover_classifier(bands: list[str]):
    """Random forest trained on the 75 frozen SIAK_AOI01 polygons over the AOI01 2025 stack (transfer learning).

    bands: the ROBUST_BANDS the field has; accuracy is re-measured on the same bands.
    """
    fc = _cover_training()
    feats = ee.FeatureCollection([ee.Feature(ee.Geometry(f["geometry"], None, False), f["properties"])
                                  for f in fc["features"]]).map(lambda f: f.set("LABEL", ee.Number(f.get("CLASS_ID")).subtract(1)))
    stack, _ = _cover_stack(ee.Geometry(fc["training_aoi"], None, False), COVER_TRAINING_YEAR)
    props = ["SAMP_ID", "LABEL"]
    train_poly, valid_poly = feats.filter(ee.Filter.eq("SPLIT", "TRAIN")), feats.filter(ee.Filter.eq("SPLIT", "VALID"))
    raw = stack.sampleRegions(collection=train_poly, properties=props, scale=10, tileScale=4)
    capped = ee.FeatureCollection(ee.List(train_poly.aggregate_array("SAMP_ID")).distinct().sort().map(
        lambda sid: raw.filter(ee.Filter.eq("SAMP_ID", sid)).randomColumn("R", COVER_RF["seed"]).sort("R")
        .limit(COVER_MAX_PX_POLYGON))).flatten()
    balanced = ee.FeatureCollection(ee.List.sequence(0, 4).map(
        lambda c: capped.filter(ee.Filter.eq("LABEL", c)).randomColumn("RC", COVER_RF["seed"] + 100).sort("RC")
        .limit(COVER_MAX_PX_CLASS))).flatten()
    clf = ee.Classifier.smileRandomForest(**COVER_RF).train(balanced, "LABEL", bands)
    matrix = (stack.sampleRegions(collection=valid_poly, properties=props, scale=10, tileScale=4)
              .classify(clf, "PRED").errorMatrix("LABEL", "PRED", [0, 1, 2, 3, 4]))
    return clf, matrix


def contextual_v2(class5: np.ndarray, prob: np.ndarray, conf: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Output 1 contextual V2: 3 classes (0 non-palm, 1 palm, 2 ambiguous), NaN where invalid."""
    out = np.where(valid, 0, np.nan).astype(np.float32)
    raw = (class5 == 1) & valid
    out[raw] = 1
    dist = ndimage.distance_transform_edt(~raw) * 10.0
    open_bare, forest = (class5 == 3) & valid, (class5 == 2) & valid
    out[(open_bare & (dist <= 100) & (prob >= 0.35)) | (forest & (dist <= 75) & (prob >= 0.45))] = 1
    rest = (forest | open_bare) & (out == 0)
    out[rest & (dist <= 250) & (prob >= 0.15) & (conf <= 0.60)] = 2
    return out


def clean_palm(class3: np.ndarray) -> np.ndarray:
    """Output 1 postprocess: MMU 0.5 ha -> 3x3 closing -> MMU 0.5 ha inside palm/ambiguous pixels (notebook's `valid`)."""
    valid = np.isin(class3, (1, 2))
    mmu1 = _mmu(class3 == 1, COVER_MMU_PX) & valid
    s = np.ones((3, 3))
    closed = ndimage.binary_erosion(ndimage.binary_dilation(mmu1, s, border_value=0), s, border_value=0) & valid
    return _mmu(closed, COVER_MMU_PX) & valid


def palm_cover(aoi_geojson: dict, date_from: str, date_to_exclusive: str, dest: Path) -> dict:
    """Palm / non-palm / ambiguous for the year of date_from, with the 250 m context Output 1 uses."""
    init_ee()
    aoi = ee.Geometry(aoi_geojson)
    crs = aoi_crs(aoi)
    year = _year(date_from, 2019)
    region = aoi.buffer(COVER_CONTEXT_M)
    stack, tracks = _cover_stack(region, year)
    missing = [k for k, n in tracks.items() if not n]
    clf, matrix = _cover_classifier([b for b in ROBUST_BANDS if not any(b.endswith(f"_{k}") for k in missing)])
    class5 = stack.classify(clf).add(1)
    probs = stack.classify(clf.setOutputMode("MULTIPROBABILITY")).arrayFlatten([["P1", "P2", "P3", "P4", "P5"]])
    in_field = ee.Image(1).clip(aoi).unmask(0)
    img = ee.Image.cat([class5, probs.select("P1"), probs.reduce(ee.Reducer.max()), in_field]).toFloat()

    info = ee.Dictionary({"oa": matrix.accuracy(), "kappa": matrix.kappa(),
                          "images": ee.ImageCollection(S2_SR).filterBounds(aoi)
                          .filterDate(f"{year}-01-01", f"{year + 1}-01-01").size()}).getInfo()
    arr, profile = download_arrays(img, region, crs)
    c5, prob, conf, field = arr
    valid = np.isfinite(c5) & np.isfinite(prob) & np.isfinite(conf)
    class3 = contextual_v2(np.nan_to_num(c5), np.nan_to_num(prob), np.nan_to_num(conf), valid)
    clean = clean_palm(class3)
    inside = field == 1
    cut = lambda a: np.where(inside, a, np.nan).astype(np.float32)  # noqa: E731
    out = [cut(class3), cut(np.where(np.isfinite(class3), clean, np.nan)), cut(np.where(valid, c5, np.nan)),
           cut(np.where(valid, prob, np.nan)), cut(np.where(valid, conf, np.nan))]
    save_cog(out, COVER_BANDS, profile, dest)

    px = _px_ha(profile)
    return {
        "model": "Palm cover (Output 1, RF transfer from SIAK_AOI01)",
        "bands": COVER_BANDS,
        "year": year,
        "images": info["images"],
        "radar_tracks": tracks,
        "validation_oa": _r(info["oa"]), "validation_kappa": _r(info["kappa"]),
        "field_ha": round(float(inside.sum()) * px, 2),
        "no_data_ha": round(float((inside & ~valid).sum()) * px, 2),
        "clean_palm_ha": round(float((out[1] == 1).sum()) * px, 2),
        "confidence_mean": _mean(out[4]),
        "class_ha": _areas(out[0], COVER_CLASS3, px),
        "land_cover_ha": _areas(out[2], COVER_CLASS5, px),
    }


# ============================================================================ Output 4: productivity (frozen package)
PRODUCTIVITY_YEAR = 2025
PRODUCTIVITY_BANDS = ["PRIORITY_CLASS", "PRODUCTIVITY", "PRODUCTIVITY_LOW", "PRODUCTIVITY_HIGH"]
PRIORITY_CLASS = {0: "Insufficient data", 1: "Maintain", 2: "Monitor", 3: "Management intervention",
                  4: "Replanting evaluation"}
ASU_FIELDS = {
    "unit_id": "UNIT_ID", "label": "MANAGEMENT_PRIORITY_LABEL", "confidence": "MANAGEMENT_PRIORITY_CONFIDENCE",
    "pathway": "PRODUCTIVITY_PATHWAY", "center": "PRODUCTIVITY_CENTER_T_FFB_HA_YR",
    "low": "PRODUCTIVITY_LOW_T_FFB_HA_YR", "high": "PRODUCTIVITY_HIGH_T_FFB_HA_YR", "age": "AGE_P50",
    "condition": "CONDITION_SCORE", "reasons": "MANAGEMENT_PRIORITY_REASON_CODES",
    "action": "MANAGEMENT_ACTION_TEXT", "weather": "WEATHER_LAG_SUMMARY",
}


@lru_cache(maxsize=1)
def _asu_package() -> list[tuple]:
    with open(palm_data_dir() / "output4_management_priority.geojson", encoding="utf-8") as f:
        fc = json.load(f)
    return [(shape(ft["geometry"]), ft["geometry"], ft["properties"]) for ft in fc["features"]]


def productivity_covers(aoi_geojson: dict) -> bool:
    """Whether the field overlaps the frozen Output 4 package (SIAK_AOI01), the only area it exists for."""
    field = shape(aoi_geojson)
    return any(g.intersects(field) for g, _, _ in _asu_package())


def palm_productivity(aoi_geojson: dict, date_from: str, date_to_exclusive: str, dest: Path) -> dict:
    """Output 4 for the field: the 500 m ASUs it overlaps, area-weighted, rasterised on a 10 m grid."""
    field = shape(aoi_geojson)
    hits = [(g, gj, p) for g, gj, p in _asu_package() if g.intersects(field)]
    if not hits:
        raise ValueError("Lahan ini di luar cakupan paket Output 4 (SIAK_AOI01, 2025)")

    lon, lat = field.centroid.x, field.centroid.y
    crs = f"EPSG:{utm_epsg(lon, lat)}"
    f_utm = shape(transform_geom("EPSG:4326", crs, aoi_geojson))
    minx, miny, maxx, maxy = f_utm.bounds
    x0, y1 = math.floor(minx / 10) * 10, math.ceil(maxy / 10) * 10
    w, h = math.ceil((maxx - x0) / 10), math.ceil((y1 - miny) / 10)
    transform = from_origin(x0, y1, 10, 10)
    profile = {"driver": "GTiff", "crs": crs, "transform": transform, "width": w, "height": h}
    inside = rasterize([(f_utm, 1)], (h, w), transform=transform, fill=0).astype(bool)

    rows, out = [], [np.full((h, w), np.nan, dtype=np.float32) for _ in PRODUCTIVITY_BANDS]
    for _, gj, p in hits:
        g_utm = transform_geom("EPSG:4326", crs, gj)
        burn = rasterize([(g_utm, 1)], (h, w), transform=transform, fill=0).astype(bool) & inside
        values = [p.get("MANAGEMENT_PRIORITY_CLASS"), p.get(ASU_FIELDS["center"]), p.get(ASU_FIELDS["low"]),
                  p.get(ASU_FIELDS["high"])]
        for band, v in zip(out, values):
            band[burn] = np.nan if v is None else v
        overlap = shape(g_utm).intersection(f_utm).area / 1e4
        rows.append({k: p.get(v) for k, v in ASU_FIELDS.items()} | {
            "class": p.get("MANAGEMENT_PRIORITY_CLASS"), "overlap_ha": round(overlap, 2)})
    save_cog(out, PRODUCTIVITY_BANDS, profile, dest)

    rows.sort(key=lambda r: -r["overlap_ha"])
    tot = sum(r["overlap_ha"] for r in rows) or 1
    wavg = lambda k: _r(sum(r[k] * r["overlap_ha"] for r in rows if r[k] is not None) / tot, 2)  # noqa: E731
    return {
        "model": "Productivity potential & management priority (Output 4, PalmSim)",
        "bands": PRODUCTIVITY_BANDS,
        "year": PRODUCTIVITY_YEAR,
        "source": "SIAK_AOI01 2025 package (500 m ASU, frozen)",
        "field_ha": round(f_utm.area / 1e4, 2),
        "covered_ha": round(float(inside.sum() - np.isnan(out[0][inside]).sum()) * 0.01, 2),
        "class_ha": _areas(np.where(inside, out[0], np.nan), PRIORITY_CLASS, 0.01),
        "productivity_center": wavg("center"), "productivity_low": wavg("low"), "productivity_high": wavg("high"),
        "asus": rows,
    }


RUNNERS = {
    "palm_cover": palm_cover, "palm_age": palm_age, "palm_condition": palm_condition,
    "palm_nutrient": palm_nutrient, "palm_waterlogging": palm_waterlogging, "palm_productivity": palm_productivity,
}


if __name__ == "__main__":
    # contextual V2: open/bare next to palm with p >= 0.35 becomes palm; far forest stays non-palm
    c5 = np.full((1, 40), 2.0); c5[0, :3] = 1; c5[0, 3:6] = 3
    pr = np.full((1, 40), 0.5); cf = np.full((1, 40), 0.5)
    c3 = contextual_v2(c5, pr, cf, np.ones((1, 40), bool))
    assert (c3[0, :6] == 1).all() and c3[0, 39] == 0 and c3[0, 20] == 2, c3
    # clean palm: a 49-pixel patch is dropped, a 64-pixel patch is kept
    cls3 = np.zeros((30, 30), dtype=np.float32); cls3[:7, :7] = 1; cls3[20:28, 20:28] = 1
    cp = clean_palm(cls3)
    assert not cp[:7, :7].any() and cp[20:28, 20:28].all()
    # condition: 3 consecutive inspection periods with full data -> class 4 needs high; here class 3
    shp = (6, 12, 12)
    z = lambda v=0: np.full(shp, v, dtype=np.float32)  # noqa: E731
    pc = z(1); pc[1:4] = 3
    a = condition_annual({"PERIOD_CLASS": pc, "TOTAL_VALID": z(1), "S2_VALID": z(1), "CONFIDENCE": z(2),
                          "GREEN_FLAG": z(1), "NDRE_FLAG": z(1), "NDMI_FLAG": z(0), "RADAR_CONFIRM": z(0),
                          "RADAR_ONLY": z(0)})
    # 3 inspection periods in a row: class 4; score 3/6*25 + 3/6*30 + 3/6*20 = 37.5 -> 38
    assert (a["class"] == 4).all() and (a["score"] == 38).all() and (a["reason"] == 1 + 2 + 16 + 32).all(), a["score"]
    pc = z(1); pc[1:4, :3, :3] = 3  # a 9-pixel priority patch is below the 0.10 ha (10 px) filter -> watch
    a = condition_annual({"PERIOD_CLASS": pc, "TOTAL_VALID": z(1), "S2_VALID": z(1), "CONFIDENCE": z(2),
                          "GREEN_FLAG": z(1), "NDRE_FLAG": z(1), "NDMI_FLAG": z(0), "RADAR_CONFIRM": z(0),
                          "RADAR_ONLY": z(0)})
    assert a["class"][0, 0] == 2 and a["class"][5, 5] == 1
    assert _round_half_up(np.array([11.5, 12.49])).tolist() == [12, 12]
    assert _max_run(np.array([[1], [1], [0], [1], [1], [1]], bool)[:, :, None])[0, 0] == 3
    print("palm_models OK")
