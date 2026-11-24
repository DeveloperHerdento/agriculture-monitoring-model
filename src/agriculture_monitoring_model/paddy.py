"""Paddy analysis models (ports of scripts/padi notebooks) for one field AOI.

- productivity : Module 4 "LUE Constant Productivity" (Level-0 LUE, Sentinel-2)
- vhi          : Module 3 "VHI + Drought" (Landsat 8/9 NDVI + LST, alpha tuned against a SPEI proxy)
                 + VHI trend (Mann-Kendall + Sen's slope over the same month, 2016..year)
- growth_phase : Module 2.1 growth phase + cropping index (IP) + planting seasons
                 (13 monthly S2 + S1 + CHIRPS composites)

GEE builds the composites; the notebooks' numpy rules (classification, majority filter, sieve,
Mann-Kendall, peak detection) run locally unchanged. The paddy mask the notebooks read from
Module 1's `Klasifikasi_Sawah.tif` is rebuilt here from Dynamic World (12 months up to the
analysis end), exactly like our paddy extent run.

Every runner writes one float32 COG (nodata -9999, named bands) and returns summary numbers
for the history row (stats, class areas, chart series).
"""

import warnings
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import ee
import numpy as np
from rasterio.features import sieve as rio_sieve
from scipy.interpolate import PchipInterpolator, interp1d
from scipy.ndimage import convolve
from scipy.stats import fisk, norm, pearsonr

from .gee import (
    INDEX_NODATA, S2_SR, SCALE_M, aoi_crs, download_arrays, download_cog, init_ee, paddy_image, save_cog,
)

PX_HA = (SCALE_M * SCALE_M) / 1e4  # 0.01 ha per 10 m pixel
MAJORITY_WINDOW = 5
CHIRPS = "UCSB-CHG/CHIRPS/DAILY"


# ============================================================================ shared helpers
def add_months(d: date, n: int) -> date:
    """First day of the month n months from d's month."""
    y, m = divmod(d.month - 1 + n, 12)
    return date(d.year + y, m + 1, 1)


def paddy_reference(aoi: ee.Geometry, end_exclusive: str, crs: str) -> ee.Image:
    """Module 1 paddy map for the 12 months before end_exclusive: 1 paddy, 0 non-paddy, 255 outside."""
    img, _ = paddy_image(aoi, end_exclusive, crs)
    return img


def majority_filter(cls: np.ndarray, size: int = MAJORITY_WINDOW) -> np.ndarray:
    """Modules 2.1/3 majority (mode) filter: NaN = invalid, not counted as neighbour, stays NaN."""
    valid = ~np.isnan(cls)
    classes = np.unique(cls[valid]).astype(int)
    if classes.size == 0:
        return cls.copy()
    kernel = np.ones((size, size), dtype=np.float32)
    counts = np.stack([convolve(((cls == k) & valid).astype(np.float32), kernel, mode="constant", cval=0)
                       for k in classes])
    out = classes[np.argmax(counts, axis=0)].astype(np.float32)
    out[~valid] = np.nan
    return out


def sieve_classes(cls: np.ndarray, min_px: int, connectivity: int = 8) -> np.ndarray:
    """Module 3 `terapkan_sieve`: merge patches smaller than min_px into their neighbours."""
    if np.all(np.isnan(cls)):
        return cls
    u8 = np.where(np.isnan(cls), 255, cls).astype(np.uint8)
    out = rio_sieve(u8, size=min_px, connectivity=connectivity)
    return np.where(out == 255, np.nan, out).astype(np.float32)


def class_areas(cls: np.ndarray, labels: dict[int, str]) -> dict[str, float]:
    return {labels[k]: round(float((cls == k).sum()) * PX_HA, 2) for k in labels if (cls == k).any()}


def _nanmean(a) -> float | None:
    a = np.asarray(a, dtype=float)
    return round(float(np.nanmean(a)), 4) if np.isfinite(a).any() else None


# ============================================================================ Module 4: productivity (LUE)
LUE_PAR_SEASON = 1500.0      # total seasonal PAR (Module 4 constant)
LUE_EPSILON = 1.2            # light-use efficiency
YIELD_VALID = (0, 15)        # plausible paddy yield, t/ha (Module 4 filter)
PROD_CLASS = {0: "Low", 1: "Medium", 2: "High", 3: "Non-paddy"}
PRODUCTIVITY_BANDS = ["YIELD", "YIELD_CLASS"]


def productivity(aoi_geojson: dict, date_from: str, date_to_exclusive: str, dest: Path) -> dict:
    """Yield t/ha from a season S2 median: NDVI -> fPAR -> GPP -> yield; classes by 33/66 % quantiles."""
    init_ee()
    aoi = ee.Geometry(aoi_geojson)
    crs = aoi_crs(aoi)
    col = (ee.ImageCollection(S2_SR).filterBounds(aoi).filterDate(date_from, date_to_exclusive)
           .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20)))
    ndvi = col.median().normalizedDifference(["B8", "B4"])
    fpar = ndvi.multiply(1.25).subtract(0.15).clamp(0, 1)
    gpp = ee.Image.constant(LUE_PAR_SEASON).multiply(fpar).multiply(LUE_EPSILON)
    yld = gpp.multiply(2.22).multiply(0.45).multiply(0.01).rename("YIELD")

    paddy = paddy_reference(aoi, date_to_exclusive, crs)
    yld_paddy = yld.updateMask(paddy.eq(1))
    valid = yld_paddy.updateMask(yld_paddy.gt(YIELD_VALID[0]).And(yld_paddy.lt(YIELD_VALID[1])))
    area = ee.Image.pixelArea().divide(1e4)
    region = dict(geometry=aoi, scale=SCALE_M, crs=crs, maxPixels=1e13, tileScale=4)
    stats = valid.reduceRegion(
        ee.Reducer.mean()
        .combine(ee.Reducer.percentile([2, 33, 66, 98]), sharedInputs=True)
        .combine(ee.Reducer.fixedHistogram(YIELD_VALID[0], YIELD_VALID[1], 30), sharedInputs=True), **region)
    sums = (valid.multiply(area).rename("PROD").addBands(area.updateMask(valid.mask()).rename("AREA"))
            .reduceRegion(ee.Reducer.sum(), **region))
    info = ee.Dictionary({"images": col.size(), "stats": stats, "sums": sums}).getInfo()
    if info["images"] == 0:
        raise ValueError(f"Tidak ada citra Sentinel-2 (awan < 20%) antara {date_from} dan {date_to_exclusive}")
    st = info["stats"]
    if st.get("YIELD_mean") is None:
        raise ValueError("Tidak ada piksel sawah dengan estimasi hasil yang valid di lahan ini")
    q33, q66 = st["YIELD_p33"], st["YIELD_p66"]

    # np.digitize(bins=[q33, q66]) on paddy pixels; non-paddy inside the field -> class 3
    cls = ee.Image.constant(3).where(paddy.eq(1), yld_paddy.gte(q33).add(yld_paddy.gte(q66)))
    cls = cls.updateMask(paddy.neq(255)).rename("YIELD_CLASS")
    class_ha = (area.addBands(cls).reduceRegion(ee.Reducer.sum().group(1, "k"), **region)
                .get("groups").getInfo()) or []

    download_cog(ee.Image.cat([yld_paddy, cls]).toFloat().unmask(INDEX_NODATA).clip(aoi)
                 .unmask(INDEX_NODATA, False), aoi, crs, dest, INDEX_NODATA, PRODUCTIVITY_BANDS)
    r = lambda v, n=3: round(v, n) if v is not None else None  # noqa: E731
    return {
        "model": "LUE Level-0 (Module 4)",
        "bands": PRODUCTIVITY_BANDS,
        "images": info["images"],
        "paddy_ha": r(info["sums"].get("AREA"), 2),
        "mean_t_ha": r(st["YIELD_mean"]),
        "total_t": r(info["sums"].get("PROD"), 1),
        "q33": r(q33), "q66": r(q66), "p2": r(st["YIELD_p2"]), "p98": r(st["YIELD_p98"]),
        "histogram": [[round(b, 2), int(c)] for b, c in (st.get("YIELD_histogram") or [])],
        "class_ha": {PROD_CLASS[int(g["k"])]: round(g["sum"], 2) for g in class_ha if int(g["k"]) in PROD_CLASS},
    }


# ============================================================================ Module 3: VHI + trend
VHI_FIRST_YEAR = 2016
VHI_CLOUD_TIERS = (40, 60, 80, 100)
VHI_MIN_IMAGES = 15
VHI_MIN_TREND_YEARS = 4
VHI_MMU_PX = int(round(0.5 / PX_HA))  # 0.5 ha minimum mapping unit
VHI_CLASS = {0: "Non-paddy", 1: "Extreme drought", 2: "Severe drought", 3: "Moderate drought",
             4: "Mild drought", 5: "Normal"}
TREND_CLASS = {0: "Non-paddy", 1: "Significant wetting", 2: "Non-significant wetting",
               3: "Non-significant drying", 4: "Significant drying"}
VHI_BANDS = ["VHI", "VHI_CLASS", "VHI_SLOPE", "TREND_CLASS"]
L8, L9 = "LANDSAT/LC08/C02/T1_L2", "LANDSAT/LC09/C02/T1_L2"


def _landsat_ndvi_lst(img):
    """Module 3 `add_indices`: QA cloud/shadow/dilated-cloud mask, NDVI (SR_B5/B4), LST in degC."""
    qa = img.select("QA_PIXEL")
    clear = qa.bitwiseAnd(1 << 3).eq(0).And(qa.bitwiseAnd(1 << 4).eq(0)).And(qa.bitwiseAnd(1 << 1).eq(0))
    m = img.updateMask(clear)
    opt = m.select(["SR_B4", "SR_B5"]).multiply(0.0000275).add(-0.2)
    ndvi = opt.normalizedDifference(["SR_B5", "SR_B4"]).rename("NDVI")
    lst = m.select("ST_B10").multiply(0.00341802).add(149.0).subtract(273.15).rename("LST")
    return ee.Image(ndvi.addBands(lst).copyProperties(img, ["system:time_start"]))


def _landsat(aoi, cloud_max: int, year_to: int, month_lo: int | None = None, month_hi: int | None = None):
    def build(cid, year_from):
        c = (ee.ImageCollection(cid).filterBounds(aoi).filter(ee.Filter.lt("CLOUD_COVER", cloud_max))
             .filter(ee.Filter.calendarRange(year_from, year_to, "year")))
        if month_lo:
            c = c.filter(ee.Filter.calendarRange(month_lo, month_hi, "month"))
        return c.map(_landsat_ndvi_lst)
    return build(L8, VHI_FIRST_YEAR).merge(build(L9, max(VHI_FIRST_YEAR, 2021)))


def _optimise_alpha(aoi, cal, year: int) -> tuple[float, float | None, int]:
    """Module 3 TAHAP 3: pick alpha (0..1, step .05) maximising corr(VHI, SPEI proxy) over monthly means.

    SPEI proxy = log-logistic (fisk) CDF of CHIRPS rain - MODIS PET, mapped to a normal quantile.
    The calibration region is the field's bbox + 100 m, so tiny fields still hold whole 100 m cells.
    """
    chirps = ee.ImageCollection(CHIRPS)
    pet_col = ee.ImageCollection("MODIS/061/MOD16A2")
    window = (f"{year - 1}-01-01", f"{year + 1}-01-01")
    latest = ee.Dictionary({
        "chirps": chirps.filterDate(*window).aggregate_max("system:time_start"),
        "pet": pet_col.filterDate(*window).aggregate_max("system:time_start"),
    }).getInfo()
    if not latest.get("chirps") or not latest.get("pet"):
        return 0.5, None, 0
    last = min(datetime.fromtimestamp(latest[k] / 1000, tz=timezone.utc).date() for k in ("chirps", "pet"))
    cutoff = last.replace(day=1)
    pairs = [[y, m] for y in range(VHI_FIRST_YEAR, year + 1) for m in range(1, 13) if date(y, m, 1) < cutoff]

    ndvi_max, ndvi_min = cal.select("NDVI").max(), cal.select("NDVI").min()
    lst_max, lst_min = cal.select("LST").max(), cal.select("LST").min()
    region = aoi.bounds(1).buffer(100)

    def monthly(pair):
        pair = ee.List(pair)
        t0 = ee.Date.fromYMD(ee.Number(pair.get(0)), ee.Number(pair.get(1)), 1)
        t1 = t0.advance(1, "month")
        col = cal.filterDate(t0, t1)
        img = ee.Image(ee.Algorithms.If(col.size().gt(0), col.median(),
                                        ee.Image.constant([0, 0]).rename(["NDVI", "LST"]).updateMask(0)))
        vci = img.select("NDVI").subtract(ndvi_min).divide(ndvi_max.subtract(ndvi_min)).multiply(100)
        tci = lst_max.subtract(img.select("LST")).divide(lst_max.subtract(lst_min)).multiply(100)
        c_col, m_col = chirps.filterDate(t0, t1), pet_col.filterDate(t0, t1)
        pr = ee.Image(ee.Algorithms.If(c_col.size().gt(0), c_col.select("precipitation").sum(),
                                       ee.Image.constant(0).updateMask(0))).rename("PR")
        pet = ee.Image(ee.Algorithms.If(m_col.size().gt(0), m_col.select("PET").sum().multiply(0.1),
                                        ee.Image.constant(0).updateMask(0))).rename("PET")
        means = (ee.Image([vci.rename("VCI"), tci.rename("TCI"), pr.subtract(pet).rename("WB")])
                 .reduceRegion(ee.Reducer.mean(), region, 100, maxPixels=1e9))
        props = ee.Dictionary(ee.Algorithms.If(col.size().gt(0), means, ee.Dictionary({})))
        return ee.Feature(None, props)

    rows = (ee.FeatureCollection(ee.List(pairs).map(monthly))
            .filter(ee.Filter.notNull(["VCI", "TCI", "WB"]))
            .reduceColumns(ee.Reducer.toList(3), ["VCI", "TCI", "WB"]).get("list").getInfo()) if pairs else []
    if len(rows) < 3:
        return 0.5, None, len(rows)
    vci, tci, wb = (np.array(c, dtype=float) for c in zip(*rows))
    try:
        cdf = np.clip(fisk.cdf(wb, *fisk.fit(wb)), 1e-6, 1 - 1e-6)
        spei = norm.ppf(cdf)
    except Exception:  # noqa: BLE001 — Module 3 falls back to a z-score
        spei = (wb - wb.mean()) / wb.std()
    alphas = np.arange(0.0, 1.01, 0.05)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        corrs = np.array([pearsonr(a * vci + (1 - a) * tci, spei)[0] for a in alphas], dtype=float)
    if not np.isfinite(corrs).any():
        return 0.5, None, len(rows)
    best = int(np.nanargmax(corrs))
    return round(float(alphas[best]), 2), round(float(corrs[best]), 3), len(rows)


def mann_kendall_sen(stack: np.ndarray, years: np.ndarray, min_points: int = VHI_MIN_TREND_YEARS):
    """Module 3 `hitung_mk_dan_sen` (unchanged): per-pixel Sen's slope + Mann-Kendall p-value."""
    n_years = stack.shape[0]
    n_valid = np.sum(~np.isnan(stack), axis=0)
    signs, slopes = [], []
    for i in range(n_years):
        for j in range(i + 1, n_years):
            dy = stack[j] - stack[i]
            ok = ~np.isnan(dy)
            signs.append(np.where(ok, np.sign(dy), np.nan))
            slopes.append(np.where(ok, dy / (years[j] - years[i]), np.nan))
    with warnings.catch_warnings(), np.errstate(invalid="ignore", divide="ignore"):
        warnings.simplefilter("ignore", RuntimeWarning)  # all-NaN pixels outside the field
        s = np.nansum(np.stack(signs), axis=0)
        sen = np.nanmedian(np.stack(slopes), axis=0)
        var_s = (n_valid * (n_valid - 1) * (2 * n_valid + 5)) / 18.0
        z = np.where(s > 0, (s - 1) / np.sqrt(var_s), np.where(s < 0, (s + 1) / np.sqrt(var_s), 0.0))
    p = 2 * (1 - norm.cdf(np.abs(z)))
    too_few = n_valid < min_points
    return np.where(too_few, np.nan, sen), np.where(too_few, np.nan, p), n_valid


def vhi(aoi_geojson: dict, date_from: str, date_to_exclusive: str, dest: Path) -> dict:
    """VHI classes for the month of date_from + VHI trend for that month over 2016..year."""
    init_ee()
    aoi = ee.Geometry(aoi_geojson)
    crs = aoi_crs(aoi)
    target = date.fromisoformat(date_from)
    year, month = target.year, target.month
    if year < VHI_FIRST_YEAR:
        raise ValueError(f"VHI tersedia mulai {VHI_FIRST_YEAR}")
    lo, hi = max(1, month - 1), min(12, month + 1)

    hist, cloud_used, n_hist = None, None, 0
    for cloud_used in VHI_CLOUD_TIERS:  # relax cloud cover until the baseline has enough scenes
        hist = _landsat(aoi, cloud_used, year, lo, hi)
        n_hist = hist.size().getInfo()
        if n_hist >= VHI_MIN_IMAGES:
            break
    if n_hist == 0:
        raise ValueError("Tidak ada citra Landsat 8/9 untuk baseline VHI di lahan ini")

    alpha, alpha_corr, n_cal = _optimise_alpha(aoi, _landsat(aoi, 40, year), year)
    ndvi_max, ndvi_min = hist.select("NDVI").max(), hist.select("NDVI").min()
    lst_max, lst_min = hist.select("LST").max(), hist.select("LST").min()

    def vhi_of(col):
        img = col.median()
        vci = img.select("NDVI").subtract(ndvi_min).divide(ndvi_max.subtract(ndvi_min)).multiply(100)
        tci = lst_max.subtract(img.select("LST")).divide(lst_max.subtract(lst_min)).multiply(100)
        v = vci.multiply(alpha).add(tci.multiply(1 - alpha))
        return v.updateMask(v.gte(0))  # Module 3 treats VHI < 0 as invalid

    years = list(range(VHI_FIRST_YEAR, year + 1))
    per_year = {y: hist.filter(ee.Filter.calendarRange(y, y, "year")) for y in years}
    counts = ee.Dictionary({str(y): c.size() for y, c in per_year.items()}).getInfo()
    if counts[str(year)] == 0:
        raise ValueError(f"Tidak ada citra Landsat bersih untuk {year}-{month:02d} (±1 bulan)")
    empty = ee.Image.constant(0).toFloat().updateMask(0)
    bands = [(vhi_of(per_year[y]) if counts[str(y)] else empty).rename(f"Y{y}") for y in years]
    paddy = paddy_reference(aoi, add_months(target, 1).isoformat(), crs)
    arr, profile = download_arrays(ee.Image.cat(bands + [paddy.rename("PADDY")]), aoi, crs)

    stack, paddy_arr = arr[:-1], arr[-1]
    sawah, non_sawah = paddy_arr == 1, paddy_arr == 0
    vhi_now = np.where(sawah, stack[-1], np.nan)
    cls = np.full(vhi_now.shape, np.nan, dtype=np.float32)
    cls[(vhi_now >= 0) & (vhi_now <= 10)] = 1
    cls[(vhi_now > 10) & (vhi_now <= 20)] = 2
    cls[(vhi_now > 20) & (vhi_now <= 30)] = 3
    cls[(vhi_now > 30) & (vhi_now <= 40)] = 4
    cls[vhi_now > 40] = 5
    cls[non_sawah] = 0

    slope, p, _ = mann_kendall_sen(stack, np.array(years, dtype=np.float64))
    trend = np.full(slope.shape, np.nan, dtype=np.float32)
    ok = sawah & ~np.isnan(slope) & ~np.isnan(p)
    trend[ok & (slope > 0) & (p <= 0.05)] = 1
    trend[ok & (slope > 0) & (p > 0.05)] = 2
    trend[ok & (slope <= 0) & (p > 0.05)] = 3
    trend[ok & (slope <= 0) & (p <= 0.05)] = 4
    trend[non_sawah] = 0

    cls = sieve_classes(majority_filter(cls), VHI_MMU_PX)
    trend = sieve_classes(majority_filter(trend), VHI_MMU_PX)
    slope_paddy = np.where(sawah, slope, np.nan)
    save_cog([vhi_now, cls, slope_paddy, trend], VHI_BANDS, profile, dest)

    return {
        "model": "VHI (Module 3)",
        "bands": VHI_BANDS,
        "month": f"{year}-{month:02d}",
        "alpha": alpha, "alpha_corr": alpha_corr, "calibration_months": n_cal,
        "baseline_images": n_hist, "baseline_cloud_max": cloud_used, "target_images": counts[str(year)],
        "paddy_ha": round(float(sawah.sum()) * PX_HA, 2),
        "vhi_mean": _nanmean(vhi_now),
        "slope_mean": _nanmean(slope_paddy),
        "class_ha": class_areas(cls, VHI_CLASS),
        "trend_class_ha": class_areas(trend, TREND_CLASS),
        "years": [{"year": y, "vhi": _nanmean(np.where(sawah, stack[i], np.nan)), "images": counts[str(y)]}
                  for i, y in enumerate(years)],
    }


# ============================================================================ Module 2.1: growth phase
GP_MONTHS = 13
GP_CLOUD_TIERS = (20, 40, 60)
GP_MIN_SCENES = 3
S1_PASS = "DESCENDING"
GP_BANDS_IN = ["NDVI", "LSWI", "EVI2", "VH_db", "VV_db", "RVI", "RAIN"]
GROWTH_BANDS = ["PHASE", "IP"]
PHASE_CLASS = {0: "Fallow / bare", 1: "Flooded / planting", 2: "Vegetative", 3: "Generative / peak",
               4: "Harvest / senescence", 5: "Non-paddy crop", 6: "Non-paddy land", 7: "Paddy, no active cycle"}
IP_CLASS = {0: "IP 0 (fallow)", 1: "IP 100", 2: "IP 200", 3: "IP 300", 4: "Non-paddy crop",
            5: "Non-paddy land", 6: "Paddy, no active cycle"}
# Rice phenology (Fernandez-Jibaja et al. 2025), days after sowing
PHENO_DAS = {"Seedling": 11, "Tillering": 30, "Maximum Tillering": 48,
             "Inflorescence Emergence": 68, "Flowering": 86, "Ripening": 104}
DAS_PEAK = PHENO_DAS["Flowering"]
DAS_HARVEST = PHENO_DAS["Ripening"] + 8
WINDOW_PLANT_DAYS, WINDOW_HARVEST_DAYS, RAIN_SUPPORT_MM = 25, 20, 60
DAYS_PER_MONTH = 30.4375


def _s1(aoi, start: str, end: str) -> ee.ImageCollection:
    return (ee.ImageCollection("COPERNICUS/S1_GRD").filterBounds(aoi).filterDate(start, end)
            .filter(ee.Filter.eq("instrumentMode", "IW"))
            .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
            .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VH")))


def _s1_pass(aoi, start: date, end_exclusive: date) -> str:
    """The orbit pass with more scenes over the window. Since Sentinel-1B died (2021) many Indonesian sites
    get one pass only, and a fixed DESCENDING left VH empty there (no radar flood evidence -> real paddy
    became "non-paddy crop"). One pass for the whole window, so VH stays comparable month to month."""
    col = _s1(aoi, start.isoformat(), end_exclusive.isoformat())
    n = ee.Dictionary({p: col.filter(ee.Filter.eq("orbitProperties_pass", p)).size()
                       for p in ("DESCENDING", "ASCENDING")}).getInfo()
    return max(n, key=n.get)


def _monthly_composite(aoi, start: date, s1_pass: str = S1_PASS) -> tuple[ee.Image | None, dict]:
    """Module 2.1 `bangun_citra_bulanan_gabungan`: S2 median (SCL-masked, cloud tiers) + S1 + CHIRPS sum."""
    end = add_months(start, 1).isoformat()
    s2 = lambda cmax: (ee.ImageCollection(S2_SR).filterBounds(aoi).filterDate(start.isoformat(), end)  # noqa: E731
                       .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cmax)))
    s1 = _s1(aoi, start.isoformat(), end).filter(ee.Filter.eq("orbitProperties_pass", s1_pass))
    sizes = ee.Dictionary({**{str(c): s2(c).size() for c in GP_CLOUD_TIERS}, "s1": s1.size()}).getInfo()
    cloud_max = next((c for c in GP_CLOUD_TIERS if sizes[str(c)] >= GP_MIN_SCENES), GP_CLOUD_TIERS[-1])
    meta = {"month": start.strftime("%Y-%m"), "n_s2": sizes[str(cloud_max)], "n_s1": sizes["s1"], "cloud_max": cloud_max}
    if meta["n_s2"] == 0:
        return None, meta

    def mask_scl(img):
        return img.updateMask(img.select("SCL").remap([3, 8, 9, 10], [0, 0, 0, 0], 1))

    med = s2(cloud_max).map(mask_scl).median()
    b04, b08, b11 = (med.select(b).divide(10000) for b in ("B4", "B8", "B11"))
    ndvi = b08.subtract(b04).divide(b08.add(b04)).rename("NDVI")
    lswi = b08.subtract(b11).divide(b08.add(b11)).rename("LSWI")
    evi2 = b08.subtract(b04).multiply(2.5).divide(b08.add(b04.multiply(2.4)).add(1)).rename("EVI2")
    if meta["n_s1"] > 0:
        lin = s1.map(lambda i: ee.Image(10).pow(i.select("VV").divide(10)).rename("VV_lin")
                     .addBands(ee.Image(10).pow(i.select("VH").divide(10)).rename("VH_lin")))
        vv_lin, vh_lin = lin.select("VV_lin").median(), lin.select("VH_lin").median()
        radar = [s1.select("VH").median().rename("VH_db"), s1.select("VV").median().rename("VV_db"),
                 vh_lin.multiply(4).divide(vv_lin.add(vh_lin).add(1e-6)).rename("RVI")]
    else:
        radar = [ee.Image.constant(0).updateMask(0).rename(n) for n in ("VH_db", "VV_db", "RVI")]
    # CHIRPS lags a few weeks; an empty sum() has no bands, so recent months get a masked RAIN band
    chirps = ee.ImageCollection(CHIRPS).filterBounds(aoi).filterDate(start.isoformat(), end)
    rain = ee.Image(ee.Algorithms.If(chirps.size().gt(0), chirps.sum(),
                                     ee.Image.constant(0).updateMask(0))).rename("RAIN")
    return ee.Image.cat([ndvi, lswi, evi2, *radar, rain]), meta


def _daily_rain(aoi, start: date, end_exclusive: date) -> list[tuple[date, float]]:
    """Module 2.1 `kumpulkan_chirps_harian_gee`: field-mean daily CHIRPS in one request.

    The region is buffered 2.8 km (half a CHIRPS cell) so small fields still hit a cell centre.
    """
    region = aoi.buffer(2800)
    col = ee.ImageCollection(CHIRPS).filterBounds(region).filterDate(start.isoformat(), end_exclusive.isoformat())
    fc = col.map(lambda img: ee.Feature(None, {
        "date": img.date().format("YYYY-MM-dd"),
        "p": img.reduceRegion(ee.Reducer.mean(), region, 5566, maxPixels=1e9).get("precipitation")}))
    rows = fc.reduceColumns(ee.Reducer.toList(2), ["date", "p"]).get("list").getInfo()
    return sorted((date.fromisoformat(d), float(p or 0)) for d, p in rows)


def _rolling_mean(values: np.ndarray, window: int = 15) -> np.ndarray:
    """pandas rolling(window, center=True, min_periods=1).mean()."""
    half = window // 2
    return np.array([values[max(0, i - half): i + half + 1].mean() for i in range(len(values))])


def identify_paddy(ndvi, lswi, vh, mask_sawah):
    """Module 2.1 `identifikasi_piksel_padi`: paddy = active cycle with flooding evidence before the peak."""
    n = ndvi.shape[0]
    with np.errstate(invalid="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        ndvi_max = np.nanmax(ndvi, axis=0)
        peak_idx = np.nanargmax(np.nan_to_num(ndvi, nan=-99.0), axis=0)
    active = mask_sawah & (ndvi_max >= 0.35)
    vh_thr = np.nanpercentile(vh[:, mask_sawah], 30) if np.isfinite(vh[:, mask_sawah]).any() else np.nan
    flooded = np.zeros(mask_sawah.shape, dtype=bool)
    with np.errstate(invalid="ignore"):
        for t in range(n):
            before_peak = t < peak_idx
            optic = lswi[t] >= (ndvi[t] - 0.05)
            if t + 1 < n and np.isfinite(vh_thr):
                radar = np.isfinite(vh[t]) & (vh[t] <= vh_thr) & np.isfinite(vh[t + 1]) & (vh[t + 1] > vh[t])
            else:
                radar = np.zeros(mask_sawah.shape, dtype=bool)
            flooded |= before_peak & (optic | radar)
    return active & flooded, active & ~flooded


def classify_phase(ndvi, lswi, evi2, vh, rvi, rain, mask_padi, mask_non_padi) -> np.ndarray:
    """Module 2.1 `klasifikasikan_fase_tanam` (unchanged rules); 255 = unclassified."""
    def relative_position(vals):
        with np.errstate(invalid="ignore"), warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            vmin, vmax = np.nanmin(vals, axis=0), np.nanmax(vals, axis=0)
        span = np.where((vmax - vmin) > 1e-6, vmax - vmin, 1e-6)
        return (vals[-1] - vmin) / span, vmax

    pos_ndvi, ndvi_max = relative_position(ndvi)
    pos_evi2, _ = relative_position(evi2)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        pos = np.nanmean(np.stack([pos_ndvi, pos_evi2]), axis=0)
    ndvi_now, ndvi_prev = ndvi[-1], ndvi[-2]
    lswi_now, vh_now, rvi_now, rain_now = lswi[-1], vh[-1], rvi[-1], rain[-1]
    slope = ndvi_now - ndvi_prev
    with np.errstate(invalid="ignore"):
        valid = mask_padi & ~np.isnan(ndvi_now) & ~np.isnan(lswi_now)
        no_cycle = valid & (ndvi_max < 0.35)
        cycle = valid & ~no_cycle
        flood_optic = (lswi_now >= ndvi_now) & (pos <= 0.35)
        zero = np.zeros_like(flood_optic, dtype=bool)
        sel = mask_padi & np.isfinite(vh_now)
        flood_vh = (np.isfinite(vh_now) & (vh_now <= np.nanpercentile(vh_now[sel], 20)) & (pos <= 0.5)) if sel.any() else zero
        sel = mask_padi & np.isfinite(rvi_now)
        flood_rvi = (np.isfinite(rvi_now) & (rvi_now <= np.nanpercentile(rvi_now[sel], 25)) & (pos <= 0.5)) if sel.any() else zero
        flood_radar = flood_vh | flood_rvi
        flood_rain = (np.isfinite(rain_now) & (rain_now > 100.0) & (pos <= 0.35)) if np.isfinite(rain_now).any() else zero
        fallow_flat = no_cycle & (lswi_now < ndvi_now)
        flooded_flat = no_cycle & (lswi_now >= ndvi_now)
        fallow = cycle & (pos <= 0.25) & (lswi_now < ndvi_now) & ~flood_radar & ~flood_rain
        flooded = cycle & (flood_optic | flood_radar | flood_rain)
        generative = cycle & (pos >= 0.75) & ~flooded
        rest = cycle & ~fallow & ~flooded & ~generative
    phase = np.full(ndvi_now.shape, np.nan, dtype=np.float32)
    phase[fallow_flat | fallow] = 0
    phase[flooded_flat | flooded] = 1
    phase[rest & (slope >= 0)] = 2
    phase[generative] = 3
    phase[rest & (slope < 0)] = 4
    phase[mask_non_padi] = 5
    return phase


def smooth_curve(values: np.ndarray, points_per_month: int = 10):
    """Module 2.1 `haluskan_kurva`: PCHIP (shape-preserving), flat outside the data, linear if < 4 points."""
    n = len(values)
    x = np.arange(n)
    ok = ~np.isnan(values)
    xs = np.linspace(0, n - 1, n * points_per_month)
    if ok.sum() < 4:
        if ok.sum() < 2:
            return xs, np.full(xs.shape, np.nan)
        return xs, interp1d(x[ok], values[ok], kind="linear", fill_value="extrapolate")(xs)
    ys = PchipInterpolator(x[ok], values[ok], extrapolate=False)(xs)
    ys = np.where(xs < x[ok][0], values[ok][0], ys)
    return xs, np.where(xs > x[ok][-1], values[ok][-1], ys)


def _group_extrema(idx, y, gap, mode):
    if len(idx) < 2:
        return idx
    out = [idx[0]]
    for i in idx[1:]:
        if i - out[-1] < gap:
            if (y[i] > y[out[-1]]) if mode == "peak" else (y[i] < y[out[-1]]):
                out[-1] = i
        else:
            out.append(i)
    return np.array(out, dtype=int)


def _simple_extrema(y, gap):
    sign = np.sign(np.diff(y))
    for i in range(1, len(sign)):
        if sign[i] == 0:
            sign[i] = sign[i - 1]
    peaks = [i for i in range(1, len(sign)) if sign[i - 1] > 0 and sign[i] < 0]
    valleys = [i for i in range(1, len(sign)) if sign[i - 1] < 0 and sign[i] > 0]
    return (_group_extrema(np.array(peaks, dtype=int), y, gap, "peak"),
            _group_extrema(np.array(valleys, dtype=int), y, gap, "valley"))


def detect_peaks_valleys(xs, ys, active_ndvi=0.30, min_gap_days=60, amp_rel=0.10, amp_abs=0.05):
    """Module 2.1 `deteksi_puncak_lembah` (multi-season, local-amplitude rule + window-edge cases)."""
    amp_min = max((np.nanmax(ys) - np.nanmin(ys)) * amp_rel, amp_abs)
    per_day = (len(xs) - 1) / ((xs[-1] - xs[0]) * DAYS_PER_MONTH) if len(xs) > 1 else 1
    gap = max(int(min_gap_days * per_day), 1)
    cand_p, cand_v = _simple_extrema(ys, gap)
    seq = sorted([(int(i), "p") for i in cand_p] + [(int(i), "v") for i in cand_v])
    peaks, valleys = [], []
    for pos, (i, kind) in enumerate(seq):
        left = ys[seq[pos - 1][0]] if pos >= 1 else ys[0]
        right = ys[seq[pos + 1][0]] if pos + 1 < len(seq) else ys[-1]
        if kind == "p" and max(ys[i] - left, ys[i] - right) >= amp_min:
            peaks.append(i)
        if kind == "v" and max(left - ys[i], right - ys[i]) >= amp_min:
            valleys.append(i)
    peaks, valleys = np.array(sorted(peaks), dtype=int), np.array(sorted(valleys), dtype=int)
    peak_at_start = False
    if ys[0] >= active_ndvi and ys[0] > ys[1] and (len(peaks) == 0 or 0 not in peaks):
        peaks, peak_at_start = np.insert(peaks, 0, 0), True
    still_rising = bool(ys[-1] > ys[-2])
    if ys[0] <= np.nanmin(ys) + 1e-9 and (len(valleys) == 0 or 0 not in valleys):
        valleys = np.append(valleys, 0)
    if ys[-1] <= np.nanmin(ys) + 1e-9 and (len(valleys) == 0 or (len(ys) - 1) not in valleys):
        valleys = np.append(valleys, len(ys) - 1)
    return np.sort(peaks), np.sort(valleys), peak_at_start, still_rising


def _nearest(xs, idxs, ref, window_days):
    cand = [i for i in idxs if abs(xs[i] - ref) <= window_days / DAYS_PER_MONTH]
    return min(cand, key=lambda i: abs(xs[i] - ref)) if cand else None


def estimate_seasons(first_month: date, x_ndvi, x_vh, vh_valleys, ndvi_peaks, ndvi_valleys,
                     rain_days: list[date], rain_smooth: np.ndarray, peak_at_start=False, still_rising=False):
    """Module 2.1 `estimasi_tanggal_kunci`: planting / peak / harvest per season (MT-1, MT-2, ...)."""
    base = datetime(first_month.year, first_month.month, 1)
    to_date = lambda idx: base + timedelta(days=float(idx) * DAYS_PER_MONTH)  # noqa: E731
    to_idx = lambda d: (d - base).days / DAYS_PER_MONTH  # noqa: E731
    stages = lambda plant: {k: (plant + timedelta(days=v)).date().isoformat() for k, v in PHENO_DAS.items()}  # noqa: E731

    def rain_note(plant):
        if not rain_days:
            return "No rainfall data"
        lo, hi = (plant - timedelta(days=10)).date(), (plant + timedelta(days=10)).date()
        total = float(sum(r for d, r in zip(rain_days, rain_smooth) if lo <= d <= hi))
        return (f"Supported by rainfall (~{total:.0f} mm around planting)" if total >= RAIN_SUPPORT_MM
                else f"No clear rainfall support (~{total:.0f} mm around planting)")

    seasons = []
    for n, ip in enumerate(ndvi_peaks):
        peak = to_date(x_ndvi[ip])
        edge = peak_at_start and ip == ndvi_peaks[0] and ip == 0
        plant_ref = peak - timedelta(days=DAS_PEAK)
        harvest_ref = peak + timedelta(days=DAS_HARVEST - DAS_PEAK)
        i_plant = _nearest(x_vh, list(vh_valleys), to_idx(plant_ref), WINDOW_PLANT_DAYS)
        if i_plant is not None and to_idx(plant_ref) >= 0:
            plant, plant_method = to_date(x_vh[i_plant]), "Radar VH (corrected)"
        else:
            plant = plant_ref
            plant_method = ("Back-projected (before imagery)" if to_idx(plant_ref) < 0
                            else "DAS fallback (no clear VH trough)")
        harvest_shifted = harvest_ref + (plant - plant_ref)
        i_harv = _nearest(x_ndvi, [v for v in ndvi_valleys if v > ip], to_idx(harvest_shifted), WINDOW_HARVEST_DAYS)
        if i_harv is not None:
            harvest, harvest_method = to_date(x_ndvi[i_harv]), "NDVI senescence (corrected)"
        else:
            harvest, harvest_method = harvest_shifted, "DAS fallback (no clear NDVI valley)"
        seasons.append({
            "label": f"MT-{n + 1}", "planting": plant.date().isoformat(), "peak": peak.date().isoformat(),
            "harvest": harvest.date().isoformat(), "planting_method": plant_method,
            "harvest_method": harvest_method, "rain": rain_note(plant), "stages": stages(plant),
            "status": "partial_before_window" if edge else "complete",
        })
    if still_rising:
        after = [v for v in ndvi_valleys if len(ndvi_peaks) == 0 or v > ndvi_peaks[-1]]
        if after:
            plant, method = to_date(x_ndvi[after[-1]]), "Last NDVI valley (current season start)"
        else:
            plant, method = to_date(x_ndvi[-1]) - timedelta(days=45), "Rough projection (no NDVI valley)"
        seasons.append({
            "label": f"MT-{len(seasons) + 1} (ongoing)", "planting": plant.date().isoformat(),
            "peak": (plant + timedelta(days=DAS_PEAK)).date().isoformat(),
            "harvest": (plant + timedelta(days=DAS_HARVEST)).date().isoformat(),
            "planting_method": method, "harvest_method": "Projected (beyond current imagery)",
            "rain": "Not evaluated (season ongoing)", "stages": stages(plant), "status": "ongoing_projected",
        })
    return seasons


def growth_phase(aoi_geojson: dict, date_from: str, date_to_exclusive: str, dest: Path) -> dict:
    """Growth phase + cropping index for the month of date_from, from the 13 months ending there."""
    init_ee()
    aoi = ee.Geometry(aoi_geojson)
    crs = aoi_crs(aoi)
    target = date.fromisoformat(date_from).replace(day=1)
    months = [add_months(target, i - (GP_MONTHS - 1)) for i in range(GP_MONTHS)]

    s1_pass = _s1_pass(aoi, months[0], add_months(target, 1))
    with ThreadPoolExecutor(max_workers=4) as pool:
        composites = list(pool.map(lambda m: _monthly_composite(aoi, m, s1_pass), months))
    valid = [(m, img, meta) for m, (img, meta) in zip(months, composites) if img is not None]
    if len(valid) < 3:
        raise ValueError(f"Hanya {len(valid)} bulan dengan citra Sentinel-2; butuh minimal 3")
    if valid[-1][0] != target:
        raise ValueError(f"Tidak ada citra Sentinel-2 untuk bulan {target:%Y-%m}")

    paddy = paddy_reference(aoi, add_months(target, 1).isoformat(), crs)
    jobs = [img.addBands(paddy.rename("PADDY")) if k == 0 else img for k, (_, img, _) in enumerate(valid)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        downloads = list(pool.map(lambda im: download_arrays(im, aoi, crs), jobs))
    profile = downloads[0][1]
    paddy_arr = downloads[0][0][len(GP_BANDS_IN)]
    stacks = {b: np.stack([d[0][i] for d in downloads]) for i, b in enumerate(GP_BANDS_IN)}
    mask_sawah = paddy_arr == 1

    mask_padi, mask_non_padi = identify_paddy(stacks["NDVI"], stacks["LSWI"], stacks["VH_db"], mask_sawah)
    phase = classify_phase(stacks["NDVI"], stacks["LSWI"], stacks["EVI2"], stacks["VH_db"], stacks["RVI"],
                           stacks["RAIN"], mask_padi, mask_non_padi)
    phase = majority_filter(phase)

    ndvi = stacks["NDVI"]
    with np.errstate(invalid="ignore"):
        is_peak = (ndvi[1:-1] > ndvi[:-2]) & (ndvi[1:-1] > ndvi[2:]) & (ndvi[1:-1] > 0.35)
    ip = np.full(mask_sawah.shape, np.nan, dtype=np.float32)
    ip[mask_sawah & mask_padi] = np.clip(np.sum(is_peak, axis=0), 0, 3)[mask_sawah & mask_padi]
    ip[mask_sawah & mask_non_padi] = 4
    ip = majority_filter(ip)

    # Export versions: non-paddy land in the field and paddy pixels without an active cycle get classes
    phase_out, ip_out = phase.copy(), ip.copy()
    phase_out[paddy_arr == 0], ip_out[paddy_arr == 0] = 6, 5
    phase_out[mask_sawah & np.isnan(phase)], ip_out[mask_sawah & np.isnan(ip)] = 7, 6
    save_cog([phase_out, ip_out], GROWTH_BANDS, profile, dest)

    # Field time series over paddy pixels + seasons, on the full 13-month grid: months without
    # imagery stay NaN so index i is always months[i] (the notebook shifted dates after a gap).
    slot = {m: i for i, m in enumerate(months)}
    def series_mean(stack):
        full = np.full(len(months), np.nan)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            full[[slot[m] for m, _, _ in valid]] = np.nanmean(np.where(mask_padi, stack, np.nan), axis=(1, 2))
        return full
    means = {b: series_mean(stacks[b]) for b in GP_BANDS_IN}
    rain = _daily_rain(aoi, months[0], add_months(target, 1))
    rain_days = [d for d, _ in rain]
    rain_smooth = _rolling_mean(np.array([r for _, r in rain])) if rain else np.array([])

    seasons = []
    if np.isfinite(means["NDVI"]).sum() >= 2:
        x_ndvi, y_ndvi = smooth_curve(means["NDVI"])
        x_vh, y_vh = smooth_curve(means["VH_db"])
        ndvi_peaks, ndvi_valleys, at_start, rising = detect_peaks_valleys(x_ndvi, y_ndvi)
        vh_valleys = detect_peaks_valleys(x_vh, y_vh)[1] if np.isfinite(y_vh).all() else []
        seasons = estimate_seasons(months[0], x_ndvi, x_vh, vh_valleys, ndvi_peaks, ndvi_valleys,
                                   rain_days, rain_smooth, at_start, rising)

    # Module 2.1 double-bounce indicator (VV rising, RVI low, LSWI high) for the chart
    rvi_thr, lswi_thr = np.nanmedian(means["RVI"]), np.nanmedian(means["LSWI"])
    double_bounce = [bool(i > 0 and means["VV_db"][i] > means["VV_db"][i - 1] and means["RVI"][i] <= rvi_thr
                          and means["LSWI"][i] >= lswi_thr) for i in range(len(months))]
    r = lambda v: round(float(v), 4) if np.isfinite(v) else None  # noqa: E731
    return {
        "model": "Growth phase (Module 2.1)",
        "bands": GROWTH_BANDS,
        "month": f"{target:%Y-%m}",
        "s1_pass": s1_pass,
        "paddy_ha": round(float(mask_padi.sum()) * PX_HA, 2),
        "non_paddy_crop_ha": round(float(mask_non_padi.sum()) * PX_HA, 2),
        "phase_ha": class_areas(phase_out, PHASE_CLASS),
        "ip_ha": class_areas(ip_out, IP_CLASS),
        "series": [{**meta, **{b.lower(): r(means[b][i]) for b in GP_BANDS_IN}, "double_bounce": double_bounce[i]}
                   for i, (_, meta) in enumerate(composites)],
        "rain_daily": [[d.isoformat(), round(float(v), 2)] for d, v in zip(rain_days, rain_smooth)],
        "seasons": seasons,
    }


RUNNERS = {"productivity": productivity, "vhi": vhi, "growth_phase": growth_phase}


if __name__ == "__main__":
    assert add_months(date(2026, 1, 15), -1) == date(2025, 12, 1)
    assert add_months(date(2026, 11, 1), 2) == date(2027, 1, 1)
    # majority filter keeps NaN and smooths a lone pixel
    a = np.zeros((7, 7), dtype=np.float32); a[3, 3] = 1; a[0, 0] = np.nan
    f = majority_filter(a)
    assert f[3, 3] == 0 and np.isnan(f[0, 0])
    # Mann-Kendall: clear upward trend -> positive slope, p < 0.05
    yrs = np.arange(2016, 2027, dtype=float)
    stk = (50 + 2 * (yrs - 2016))[:, None, None] + np.random.default_rng(0).normal(0, 1, (11, 2, 2))
    s, p, n = mann_kendall_sen(stk.astype(np.float32), yrs)
    assert (s > 1.5).all() and (p < 0.05).all() and (n == 11).all()
    # Season detection on a synthetic two-season NDVI curve
    t = np.arange(13)
    nd = 0.2 + 0.5 * np.clip(np.sin((t - 1) / 12 * 4 * np.pi), 0, None)
    xs, ys = smooth_curve(nd)
    pk, vl, _, _ = detect_peaks_valleys(xs, ys)
    assert len(pk) == 2, pk
    print("paddy_models OK")
