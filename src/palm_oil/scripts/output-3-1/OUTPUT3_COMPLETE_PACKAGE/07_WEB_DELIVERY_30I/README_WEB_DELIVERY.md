# Output 3 Web Delivery

## Product

Plantation Condition & Inspection Priority

AOI: SIAK_AOI01
Monitoring year: 2025

## Primary raster files

### Class COG

`rasters/SIAK_AOI01_O3_CLASS_COG_2025.tif`

Bands:

1. CORE_CLASS
2. INTEGRATED_CLASS
3. CLASS_DELTA

Recommended resampling:

Nearest neighbour.

### Metrics COG

`rasters/SIAK_AOI01_O3_METRICS_COG_2025.tif`

Bands:

1. CORE_RISK_SCORE_0_100
2. CONTEXT_MODIFIER_SCORE
3. CONTEXT_MODIFIER_COVERAGE
4. INTEGRATED_SCORE_0_100

Recommended visualization resampling:

Bilinear.

## Vector files

`vectors/O3_PLANTATION_BOUNDARY.geojson`

`vectors/O3_INSPECTION_PRIORITY.geojson`

Inspection-priority polygons represent frozen final
classes 3 and 4.

Where available, the polygon file also includes dominant
core reason code and mean data-confidence evidence.

## Temporal / tabular data

`tables/O3_PERIOD_SUMMARY.csv`

`tables/O3_PERIOD_SUMMARY.json`

`tables/O3_TEMPORAL_SERIES.json`

These are AOI-level context / evidence summaries derived
from persistent 30C anomaly assets.

## Legend

`metadata/O3_LEGEND.json`

## Scientific interpretation

This product is designed for early warning and inspection
prioritization.

It is not a confirmed disease, nutrient-deficiency,
fertilizer-dose or causal weather/soil diagnosis.

The 10 m final display grid does not imply that coarse
weather, soil or hydrology sources contain 10 m information.

## Source of truth

Analytical cloud source of truth:

projects/palm-oil-503202/assets/SIAK_AOI01_O3_30G_INTEGRATED_V1_1_GRIDLOCKED_2025
