# Output 3 Complete Package

## Product
Plantation Condition & Inspection Priority

AOI: SIAK_AOI01
Reference year: 2025

## Architecture

Python/Jupyter is the master workflow and orchestration layer.

Google Earth Engine is used as the server-side geospatial
processing and persistent raster-asset backend.

Large intermediate rasters are not duplicated locally.

## Analytical status

FROZEN for AOI01.

Canonical Earth Engine asset:

projects/palm-oil-503202/assets/
SIAK_AOI01_O3_30G_INTEGRATED_V1_1_GRIDLOCKED_2025

## Scientific interpretation

This product supports inspection prioritization.

It is not an independent field-validated diagnosis of
plantation health, nutrient deficiency or disease.

## Package logic

00_MASTER_PIPELINE
    Complete reproducible 30A-30I notebook.

01_CONFIG
    AOI/configuration definitions.

02_ASSET_INVENTORY
    Persistent GEE and local-file inventories.

03_PROCESS_30A_30E
    Core processing and contextual enrichment provenance.

04_ANALYSIS_30F
    Screening, calibration, weights and sensitivity evidence.

05_INTEGRATION_30G
    Integrated product and transition logic.

06_FREEZE_30H
    Final analytical freeze and product summary.

07_WEB_DELIVERY_30I
    COG and web-development delivery files.

08_QA
    Technical, evidence and guardrail QA.

09_DOCUMENTATION
    Methodology, processing history and limitations.

10_ARCHIVE_MANIFEST
    Historical/legacy script inventory.

11_LOGS
    Task and execution status snapshots.

## Reuse

The final reusable pipeline will separate AOI-specific
configuration from processing logic.

A new AOI must first be treated as a reproducibility /
transferability test. Existing AOI01 weights and thresholds
must not automatically be interpreted as locally validated
for another AOI.
