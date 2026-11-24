"""Google Earth Engine helpers used by `palm` and `paddy`.

Copied from the web backend's `app/services/gee_service.py` (only what the models import, plus
their private helpers). Behaviour is unchanged; the only difference is where `init_ee` reads its
settings: env vars GEE_KEY_FILE (service-account JSON; empty = `earthengine authenticate` user
credentials) and GEE_PROJECT, read at call time, instead of the web app's `settings`.
"""

import json
import math
import os
import threading
import time
from pathlib import Path

import ee
import numpy as np
import rasterio
import requests
from rasterio.shutil import copy as rio_copy

DW_COLLECTION = "GOOGLE/DYNAMICWORLD/V1"
PADDY_CLASSES = [3, 4]
PADDY_WINDOW_MONTHS = 12  # Module 1 RENTANG_BULAN
NODATA = 255
SCALE_M = 10
MAJORITY_RADIUS_PX = 1  # 3x3 window; 5x5 (50 m) turned small fields into blobs

S2_SR = "COPERNICUS/S2_SR_HARMONIZED"
INDEX_NODATA = -9999.0
_init_lock = threading.Lock()
_initialized = False


def init_ee() -> None:
    """Initialise Earth Engine once per process (service account if GEE_KEY_FILE is set)."""
    global _initialized
    with _init_lock:
        if _initialized:
            return
        key_file = os.environ.get("GEE_KEY_FILE")
        project = os.environ.get("GEE_PROJECT") or None
        if key_file:
            with open(key_file) as f:
                email = json.load(f)["client_email"]
            creds = ee.ServiceAccountCredentials(email, key_file)
            ee.Initialize(creds, project=project)
        else:
            ee.Initialize(project=project)
        _initialized = True


def utm_epsg(lon: float, lat: float) -> int:
    """UTM zone EPSG for a WGS84 point (326xx north, 327xx south)."""
    zone = min(int((lon + 180) // 6) + 1, 60)
    return (32600 if lat >= 0 else 32700) + zone


def aoi_crs(aoi: ee.Geometry) -> str:
    lon, lat = aoi.centroid(1).coordinates().getInfo()
    return f"EPSG:{utm_epsg(lon, lat)}"


def _get(url: str, retries: int = 5) -> requests.Response:
    """GET a GEE download URL; 429 (concurrency / quota limit) is retried with backoff 2, 4, 8, 16 s."""
    for attempt in range(retries):
        resp = requests.get(url, timeout=600)
        if resp.status_code != 429 or attempt == retries - 1:
            break
        time.sleep(2 ** (attempt + 1))
    _raise_for_gee(resp)
    return resp


def _raise_for_gee(resp: requests.Response) -> None:
    """Like raise_for_status, but keeps GEE's error message (computation errors arrive as HTTP 400 JSON)."""
    if not resp.ok:
        try:
            msg = resp.json()["error"]["message"]
        except (ValueError, KeyError, TypeError):
            msg = resp.text[:500]
        if "memory limit" in msg or "request size" in msg.lower() or "must be less than or equal to" in msg:
            msg += " — lahan terlalu besar atau periode terlalu panjang untuk analisis langsung; perkecil lahan."
        raise RuntimeError(f"GEE {resp.status_code}: {msg}")


def download_cog(img: ee.Image, aoi: ee.Geometry, crs: str, dest: Path, nodata: float,
                 band_names: list[str] | None = None, overview_resampling: str = "nearest",
                 scale: int = SCALE_M) -> None:
    """getDownloadURL (UTM, 10 m by default) -> local DEFLATE COG with nodata + band names; atomic replace."""
    # ponytail: getDownloadURL caps at ~48 MB (uint8 ~450k ha; 8-band float32 ~15k ha). Bigger -> Export to GCS.
    url = img.getDownloadURL({"scale": scale, "crs": crs, "region": aoi.bounds(1), "format": "GEO_TIFF"})
    resp = _get(url)

    dest.parent.mkdir(parents=True, exist_ok=True)
    raw = dest.with_suffix(".raw.tif")
    tmp = dest.with_suffix(".tmp.tif")
    try:
        raw.write_bytes(resp.content)
        with rasterio.open(raw, "r+") as ds:
            ds.nodata = nodata
            for i, name in enumerate(band_names or [], start=1):
                ds.set_band_description(i, name)
        rio_copy(raw, tmp, driver="COG", compress="DEFLATE", predictor="YES", overview_resampling=overview_resampling)
        os.replace(tmp, dest)  # atomic: tile server never sees a half-written file
    finally:
        raw.unlink(missing_ok=True)
        tmp.unlink(missing_ok=True)


def _download_region(safe: ee.Image, region: ee.Geometry, crs: str, scale: int) -> tuple[np.ndarray, dict]:
    url = safe.getDownloadURL({"scale": scale, "crs": crs, "region": region, "format": "GEO_TIFF"})
    resp = _get(url)
    with rasterio.MemoryFile(resp.content) as mem, mem.open() as ds:
        return ds.read().astype("float32"), ds.profile


def download_arrays(img: ee.Image, aoi: ee.Geometry, crs: str, scale: int = SCALE_M,
                    tile_px: int | None = None) -> tuple[np.ndarray, dict]:
    """Download a float image as a (bands, rows, cols) array; masked / outside-AOI pixels -> NaN.

    Used where a notebook's numpy rules run locally (VHI classes, growth phase). Returns the
    array and a rasterio profile to write results back on the same grid with save_cog().

    tile_px: for compute-heavy images (multi-year composites), split the AOI into tile_px x tile_px
    windows, one request each, so no single request hits GEE's interactive memory limit. Windows are
    snapped to the scale grid, so they line up pixel for pixel when mosaicked.
    """
    safe = img.toFloat().unmask(INDEX_NODATA).clip(aoi).unmask(INDEX_NODATA, False)
    w = h = 0
    if tile_px:
        xs, ys = zip(*aoi.bounds(1, crs).coordinates().get(0).getInfo())
        x0, y0 = math.floor(min(xs) / scale) * scale, math.floor(min(ys) / scale) * scale
        x1, y1 = math.ceil(max(xs) / scale) * scale, math.ceil(max(ys) / scale) * scale
        w, h = round((x1 - x0) / scale), round((y1 - y0) / scale)
    if not tile_px or (w <= tile_px and h <= tile_px):
        arr, profile = _download_region(safe, aoi.bounds(1), crs, scale)
    else:
        step = tile_px * scale
        windows = [(tx, ty) for ty in range(int(y1), int(y0), -step) for tx in range(int(x0), int(x1), step)]
        arr, profile = None, None
        for tx, ty in windows:  # sequential: callers already run a few of these in parallel
            rect = ee.Geometry.Rectangle([tx, max(ty - step, y0), min(tx + step, x1), ty], crs, False)
            part, p = _download_region(safe, rect, crs, scale)
            if arr is None:
                arr = np.full((part.shape[0], h, w), INDEX_NODATA, dtype="float32")
                profile = {**p, "width": w, "height": h,
                           "transform": rasterio.Affine(scale, 0, x0, 0, -scale, y1)}
            c, r = round((p["transform"].c - x0) / scale), round((y1 - p["transform"].f) / scale)
            rh, rw = min(part.shape[1], h - r), min(part.shape[2], w - c)
            arr[:, r:r + rh, c:c + rw] = part[:, :rh, :rw]
    arr[arr == INDEX_NODATA] = np.nan
    return arr, profile


def save_cog(arrays: list[np.ndarray], band_names: list[str], profile: dict, dest: Path,
             nodata: float = INDEX_NODATA) -> None:
    """Write same-grid float arrays (NaN = nodata) as one multi-band DEFLATE COG; atomic replace."""
    stack = np.stack([np.where(np.isnan(a), nodata, a) for a in arrays]).astype("float32")
    write_cog(stack, band_names, {**profile, "nodata": nodata}, dest)


def write_cog(stack: np.ndarray, band_names, profile: dict, dest: Path, overview_resampling: str = "nearest") -> None:
    """(bands, rows, cols) array -> DEFLATE COG with the profile's grid/nodata and the stack's dtype; atomic replace."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    raw = dest.with_suffix(".raw.tif")
    tmp = dest.with_suffix(".tmp.tif")
    meta = {**profile, "driver": "GTiff", "count": stack.shape[0], "dtype": stack.dtype.name}
    try:
        with rasterio.open(raw, "w", **meta) as ds:
            ds.write(stack)
            for i, name in enumerate(band_names or [], start=1):
                if name:
                    ds.set_band_description(i, name)
        rio_copy(raw, tmp, driver="COG", compress="DEFLATE", predictor="YES", overview_resampling=overview_resampling)
        os.replace(tmp, dest)
    finally:
        raw.unlink(missing_ok=True)
        tmp.unlink(missing_ok=True)


def paddy_image(aoi: ee.Geometry, date_to_exclusive: str, crs: str) -> tuple[ee.Image, ee.ImageCollection]:
    """uint8 image: 1 = paddy, 0 = non-paddy, 255 = nodata / outside AOI.

    Always the Module 1 mode over the PADDY_WINDOW_MONTHS before date_to_exclusive. A single Dynamic World
    date can't tell paddy: the same field reads Water at transplanting, Crops mid-season, Bare/Grass after
    harvest, so a one-day label flips paddy <-> non-paddy from scene to scene.
    """
    end = ee.Date(date_to_exclusive)
    col = ee.ImageCollection(DW_COLLECTION).filterBounds(aoi).filterDate(end.advance(-PADDY_WINDOW_MONTHS, "month"), end)
    paddy = (col.select("label").mode()
             .remap(PADDY_CLASSES, [1] * len(PADDY_CLASSES), 0)
             .reproject(ee.Projection(crs).atScale(SCALE_M)))  # neighbourhood below is in 10 m pixels
    # Mean of valid 0/1 neighbours; masked (nodata) pixels are skipped, like the notebook's filter.
    share = paddy.reduceNeighborhood(ee.Reducer.mean(), ee.Kernel.square(MAJORITY_RADIUS_PX, "pixels"))
    smoothed = share.gte(0.5).updateMask(paddy.mask()).rename("paddy")
    out = smoothed.unmask(NODATA).clip(aoi).unmask(NODATA, False).toByte()
    return out, col
