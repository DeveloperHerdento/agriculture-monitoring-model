# Output 3 Methodology

## Product

Plantation Condition & Inspection Priority.

## Architecture

The production architecture is hybrid:

- Python / Jupyter is the orchestration, statistical,
  QA and reproducibility environment.
- Google Earth Engine is the persistent raster-data
  and server-side geospatial processing backend.

The hybrid route does not reprocess all raw satellite
imagery locally.

## 30A - Source and AOI contract

Defines AOI, upstream dependencies, asset naming,
spatial mask and source-data contract.

## 30B - Baseline and monitoring

Creates period-matched optical/radar baseline and
monitoring evidence.

The pilot uses monitoring year 2025 and matched
historical baseline periods rather than arbitrary
annual means.

## 30C - Temporal anomaly

Computes period-level differences between monitoring
and comparable baseline evidence.

## 30D - Core condition / inspection risk

Combines optical/radar anomaly, temporal persistence,
coverage and evidence rules.

30D04 Balanced Risk is the frozen upstream core used
by the final contextual integration.

## 30E - Context enrichment

Reusable contextual sources include:

- age / detected event context;
- CHIRPS rainfall;
- ERA5-Land atmospheric/moisture context;
- ET/PET;
- terrain;
- hydrology;
- soil;
- soil-water retention;
- GEDI as optional sparse structural support only.

Context data preserve their effective source resolution.

Resampling does not create new spatial information.

## 30F - Python analysis

30F performs feature screening and calibration.

The final contextual modifier uses eight frozen static
features grouped into four evidence families.

Feature selection, correlation, VIF and model comparison
are analytical evidence, not proof of causal relationships.

## 30G - Integrated Output 3

The frozen contextual modifier is applied conservatively
with F05 amplitude.

Final class movement is evidence-gated and limited to
a maximum of one class.

High-priority promotion requires optical evidence.

Radar-only evidence cannot create Class 3 or Class 4.

## 30H - Analytical freeze

AOI01 analytical product is frozen after technical and
evidence QA.

No further aesthetic retuning is permitted without new
independent validation evidence.

## 30I - Web delivery

The canonical Earth Engine asset remains the cloud
analytical source of truth.

COGs and accompanying metadata/tables are distribution
products for web development.
