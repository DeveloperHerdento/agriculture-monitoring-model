# Changelog

Notable changes per release, newest first. Versions follow `vMAJOR.MINOR.PATCH`.

## v0.1.0 — 2026-11-16

- feat: installable library `agriculture-monitoring-model` (`src/agriculture_monitoring_model/`: `palm`, `paddy`,
  `gee`), copied from the web backend's `palm_models.py` / `paddy_models.py` / `gee_service.py` with the same API.
  Earth Engine init reads `GEE_KEY_FILE` / `GEE_PROJECT`; palm reads its geojson from `PALM_DATA_DIR`.
- chore: restructure to the HGS-STD-11 layout, mirroring `ai-disaster-model` with domains `paddy` and `palm_oil`:
  `notebooks/<domain>/`, `configs/<domain>.yaml`, `data/<domain>/{raw,interim,processed}/` (ignored), `models/`,
  palm-oil package code in `src/palm_oil/scripts/` (internal layout kept), `reports/figures/paddy/` (ignored),
  `reports/deliverables/` template. Working notes live in ignored `docs/notes/`. Removed `paddy/`, `palm-oil/`,
  `new script/` and `CLAUDE.md` (facts moved to README).
- chore: base files from hgs-repo-kit (CI, CODEOWNERS, PR template, .editorconfig, .env.example, MODEL_CARD).

## Earlier (unreleased)

- Initial repo structure: `palm-oil/` and `paddy/` variants, each with
  `data/{raw,processed}`, `scripts/` (+ `scripts/notebook/`), and
  `results/{figures,tables}`. Added `README.md`, `CLAUDE.md`,
  `requirements.txt`, `.gitignore`.
- `paddy`: organized module outputs into per-module subfolders
  (`data/processed/module_{1,2,3,4}/`, `results/figures/module_{1,2,3,4}/`,
  `results/tables/module_{1,2,3,4}/`) and updated the four notebooks
  accordingly. Shared inputs produced by Module 1 (`Klasifikasi_Sawah.tif`
  / `.geojson`) stay flat in `data/processed/` since Modules 2-4 read them
  as a common dependency. Also fixed Module 2's
  `Grafik_TimeSeries_MultiMusim_CHIRPS.png` save path, which was writing
  to the notebook's working directory instead of `results/figures/`.
