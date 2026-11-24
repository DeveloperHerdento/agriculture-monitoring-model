# Output 3 Web Delivery
## Plantation Condition & Inspection Priority

AOI: SIAK_AOI01
Monitoring year: 2025
Analytical status: FROZEN
Technical QA: PASS
Field validation: NOT AVAILABLE

## Canonical Earth Engine asset

projects/palm-oil-503202/assets/SIAK_AOI01_O3_30G_INTEGRATED_V1_1_GRIDLOCKED_2025

## Primary web display

Band:
INTEGRATED_CLASS

Class schema:

1 = Stable / Expected Condition
2 = Watch
3 = Persistent Stress - Inspection Priority
4 = High Persistent Anomaly - High Priority

## Raster delivery

### SIAK_AOI01_O3_CLASS_COG_2025.tif

Bands:
1. CORE_CLASS
2. INTEGRATED_CLASS
3. CLASS_DELTA

Data type:
Int16

NoData:
-9999

Recommended display resampling:
Nearest neighbour.

### SIAK_AOI01_O3_METRICS_COG_2025.tif

Bands:
1. CORE_RISK_SCORE_0_100
2. CONTEXT_MODIFIER_SCORE
3. CONTEXT_MODIFIER_COVERAGE
4. INTEGRATED_SCORE_0_100

Data type:
Float32

NoData:
-9999

Recommended display resampling:
Bilinear for continuous visualization.

## Spatial reference

CRS:
EPSG:32647

Affine transform:
[10, 0, 804540, 0, -10, 87290]

Nominal resolution:
10 m

## Interpretation guardrail

This product is intended for inspection prioritization.

It must NOT be presented as:
- confirmed plantation health diagnosis;
- disease diagnosis;
- nutrient deficiency diagnosis;
- field-validated accuracy product.

Environmental context represents contextual association.
Coarse source datasets do not acquire 10 m information
simply because they are represented on the display grid.

## Files

metadata/
- Product summary
- Legend
- Band dictionary
- Freeze manifest
- GEE export task registry

tables/
- Final class area
- Final transition area

qa/
- Canonical area QA
- Transition QA
- Evidence guardrail QA

preview/
- Final analytical map preview

rasters/
- Place the two downloaded COG files here after
  Earth Engine export to Google Drive is complete.

## Reproducibility

The Jupyter notebook used to produce Output 3 should be
saved separately as:

MASTER_PIPELINE_OUTPUT3.ipynb

The notebook is the reproducible processing pipeline.
The COG/CSV/JSON files are delivery products.
The Earth Engine asset remains the cloud analytical
source of truth for this frozen AOI01 version.
