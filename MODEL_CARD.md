# Model Card — agriculture-monitoring-model v0.1.0

| Field | Value |
|---|---|
| Status | exploration (served by `agriculture-monitoring-web` per field AOI) |
| Owner | `@DeveloperHerdento` — TODO(owner): team |
| Model type | rule-based / index models on GEE composites; palm cover = GEE Random Forest (500 trees, seed 42) |
| Artifact location | none: models are code in `src/agriculture_monitoring_model/`; frozen inputs in `PALM_DATA_DIR` (not in git) |
| Training data | palm cover: `o1_training_aoi01.geojson` (SIAK_AOI01 2025 samples); paddy: Dynamic World V1 labels |

## Intended use
- Use for: field-level monitoring maps and summary numbers in the RATRA agriculture web app (paddy: extent, growth
  phase, VHI/drought, LUE productivity; palm oil: cover, age proxy, condition, nutrient, waterlogging, productivity).
- **Do NOT use for:** field-validated yield, diagnosis of disease or nutrient deficiency, legal boundaries.
  Palm condition = inspection priority, not diagnosis; palm productivity = modelled potential (no local FFB labels);
  palm thresholds are calibrated on SIAK_AOI01 only (not validated for other AOIs).

## Performance
| Metric | Baseline | This model | Eval set |
|---|---|---|---|
| TODO: no held-out metrics in this repo yet (Rule 11.9). Package QC stats: `data/palm_oil/processed/*/04_QC_STATS`, `07_QC`. | | | |

## Limitations & risks
- Cloud cover: S2 scenes are cloud-masked; cloudy periods give gaps or fewer valid pixels.
- Palm productivity covers only the frozen SIAK_AOI01 2025 package (`productivity_covers`).
- Large AOIs can hit GEE download/memory limits (see `gee.download_arrays` tiling).

## Operations
- Inference: on request, per field (web backend calls `RUNNERS[kind]`).
- Rollback: pin the previous tag in the web backend requirements (`...@vX.Y.Z`).
