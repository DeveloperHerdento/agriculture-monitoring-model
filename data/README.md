# Data

Data files are **never** stored in git (HGS-STD 11.1). Only this README and the empty `.gitkeep` files are versioned.

One set of folders per domain (`paddy`, `palm_oil`, same spelling as `configs/` and `notebooks/`):

```
data/<domain>/
├── raw/         inputs exactly as received. Never edit or overwrite.
├── interim/     temp / intermediate files
└── processed/   model outputs and delivered packages

data/paddy/raw/
  AOI_1.{shp,shx,dbf,prj,cpg}   paddy AOI, read by notebooks/paddy/01-field-extraction.ipynb
  Klasifikasi_Sawah.tif         paddy mask as received (reference copy)
  Landy_AOI_1.tiff              AOI raster as received (not read by the notebooks)
  jaringan_jalan_sungai.geojson road + river network, read by 01-field-extraction-road-river-revision.ipynb
  source-drops/                 paddy zips/rars as downloaded (notebooks drop 2026-09-29, Revisi_Jaringan, results)
data/paddy/interim/             temp_dw.tif from paddy Module 1
data/paddy/processed/
  module_1/ .. module_4/        paddy notebook outputs (01..04); module_1/Klasifikasi_Sawah.tif feeds 02-04
  module_1-road-river-revision/ outputs of the road/river revision of Module 1 (2026-09-22)
  cache_*/                      GEE download caches written by paddy 02 and 03
  Info_*.json, Keterangan_*.json  legend/index descriptions written by 03 and 04
data/palm_oil/raw/source-drops/ palm-oil packages as downloaded (Google Drive drop 2026-09-29)
data/palm_oil/processed/
  output-1-plantation-boundary/ delivered package (FINAL_OUTPUT, has MANIFEST + CHECKSUM)
  output-2-tree-age/            delivered web package
  output-3-2-nutrient/          delivered package + preview/guide
  output-4/                     01_WEB, 05_MODEL_ARTIFACTS, 06_QA_METADATA, 07_PREVIEW of Output 4
  output-5-2-waterlogging/      delivered package + viewer/guide
reports/figures/paddy/module_N/ paddy notebook figures (ignored)
```

The paddy notebooks resolve these paths relative to `notebooks/paddy/` (`../../data/paddy/...`), so keep the
layout. File names (`Klasifikasi_Sawah.tif`, `AOI_1.shp`) are kept because the notebooks read them by name.

The palm-oil Output 3.1 package keeps its data next to its code in
`src/palm_oil/scripts/output-3-1/OUTPUT3_COMPLETE_PACKAGE/` (its runner needs that layout); data files there
are ignored by `src/palm_oil/scripts/.gitignore`.

## Sources

| Source | What | Licence | Owner |
|---|---|---|---|
| Google Earth Engine (Dynamic World V1, Sentinel-1/2, Landsat 8/9, CHIRPS) | imagery, read live by the notebooks | per dataset terms | GEE project of the analyst |
| SDAI analyst packages (Google Drive) | palm-oil Outputs 1, 2, 3.1, 3.2, 4, 5.2 for SIAK_AOI01 2025 | internal | TODO(owner) |
| Paddy notebooks drop (Google Drive) | Modules 1-4 notebooks, AOI_1 | internal | TODO(owner) |

## Extraction log

Hash: `sha256sum <file>` (Git Bash) or `certutil -hashfile <file> SHA256` (Windows).

| File | Source | Extracted (UTC) | By | Rows | sha256 |
|---|---|---|---|---|---|
| paddy/raw/source-drops/drive-download-20260929T023404Z-1-001.zip | Google Drive (paddy notebooks) | 2026-09-29 | TODO(owner) | – | |
| palm_oil/raw/source-drops/drive-download-20260929T023507Z-1-001.zip | Google Drive (palm-oil outputs) | 2026-09-29 | TODO(owner) | – | |

## Columns

See each package's own README / data dictionary (e.g. `palm_oil/processed/output-5-2-waterlogging/05_METADATA/Waterlogging_Data_Dictionary.csv`).

## Personal data

None. Rasters and polygons of land cover; no person-level data.
