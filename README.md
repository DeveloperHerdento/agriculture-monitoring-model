# agriculture-monitoring-model

> Python / Google Earth Engine models for agriculture monitoring in Indonesia (RATRA agriculture):
> **paddy** (padi) and **palm oil** (kelapa sawit). Also an installable library used by
> `agriculture-monitoring-web`.

**Owner:** `@DeveloperHerdento` (TODO(owner): team) · **Type:** `-model` · **Status:** exploration
(paddy notebooks + delivered palm-oil packages) · library `v0.1.0` used by the web backend

- **For whom:** the RATRA agriculture web app (field-level analyses) and analysts who rerun the notebooks.
- **What:** paddy field extraction, growth phase, vegetation health / drought (VHI), productivity (LUE + WOFOST);
  palm-oil plantation boundary, tree age, condition, nutrient, productivity / management priority, waterlogging.
- Paddy and palm oil are independent pipelines that happen to live in one repo; they share only `src/.../gee.py`.

## Setup

You need Python 3.12 (same as the web backend) and Git.

```bash
git clone https://github.com/DeveloperHerdento/agriculture-monitoring-model.git && cd agriculture-monitoring-model
py -3.12 -m venv .venv && .venv\Scripts\activate          # macOS/Linux: python3.12 -m venv .venv && source .venv/bin/activate
python -m pip install -r requirements.txt -r requirements-dev.txt -e .
earthengine authenticate                                   # once per machine, or set GEE_KEY_FILE
pytest -q
```

Copy `.env.example` to `.env` and fill it in. In VS Code pick `.venv` as interpreter and notebook kernel.

## Environment

| Variable | Read by | Meaning |
|---|---|---|
| `GEE_PROJECT` | `gee.init_ee()` | Earth Engine / Cloud project ID (empty = default project of the credentials) |
| `GEE_KEY_FILE` | `gee.init_ee()` | path to a service-account JSON; empty = `earthengine authenticate` user credentials |
| `PALM_DATA_DIR` | `palm` | folder with `plantation_boundary.geojson`, `o1_training_aoi01.geojson`, `output4_management_priority.geojson` |

All three are read **at call time**, not at import. The notebooks do not read them yet (they hardcode the GEE
project ID; see open items in `CHANGELOG.md`).

## Use as a library

```bash
pip install -e ../agriculture-monitoring-model                       # local, next to the web repo
pip install "agriculture-monitoring-model @ git+https://github.com/DeveloperHerdento/agriculture-monitoring-model.git@v0.1.0"   # deploy
```

```python
from agriculture_monitoring_model import palm, paddy   # same API as the web app's app.services.palm_models / paddy_models

paddy.RUNNERS["vhi"](aoi_geojson, "2025-07-01", "2025-08-01", Path("out/vhi.tif"))   # returns summary dict, writes a COG
```

Contract with `agriculture-monitoring-web`:

- `palm` and `paddy` keep the public names and behaviour of the web snapshot (`RUNNERS`, `palm_*`, `productivity`,
  `vhi`, `growth_phase`, `add_months`, `PRODUCTIVITY_YEAR`, `VHI_FIRST_YEAR`, `productivity_covers`, ...).
- Earth Engine is initialised lazily, once per process, by `gee.init_ee()` inside every runner, from
  `GEE_KEY_FILE` / `GEE_PROJECT`. The web backend exports these from its settings.
- `palm` reads its frozen geojson files from `PALM_DATA_DIR` (web: `backend/data/geojson/palm_oil`) and raises a
  clear `RuntimeError` when it is unset. `paddy` reads no data files.
- Each runner writes one float32 COG (nodata -9999, named bands) to the `dest` path you pass.
- Release: bump `version` in `pyproject.toml` and `__init__.py`, add a `CHANGELOG.md` entry, tag `vX.Y.Z`.

## Structure

Two domains, same spelling everywhere: `paddy` and `palm_oil`.

```
src/agriculture_monitoring_model/   library: palm.py, paddy.py, gee.py (GEE helpers)
src/palm_oil/scripts/output-3-1/    Output 3.1 package as delivered (OUTPUT3_COMPLETE_PACKAGE, layout kept)
src/palm_oil/scripts/output-4/      Output 4 code: 02_NOTEBOOK, 03_SCRIPTS, 04_CONFIG (layout kept)
tests/                              pytest (no Earth Engine calls)
notebooks/paddy/                    paddy pipeline, run in order (below)
notebooks/palm_oil/                 palm-oil Output 1 and 2 notebooks
configs/paddy.yaml, palm_oil.yaml   parameters (reference copy of the notebook / package values)
data/<domain>/{raw,interim,processed}/   not in git, see data/README.md
models/                             trained model files (not in git; none yet)
reports/figures/paddy/              paddy notebook figures (not in git)
reports/deliverables/               template for packages handed to others (Rule 11.8)
docs/                               ADRs; docs/notes/ = local working notes (not in git)
```

## Run order — paddy (`notebooks/paddy/`)

Open each notebook with `notebooks/paddy/` as working directory (Jupyter / VS Code default). They read
`../../data/paddy/raw/AOI_1.shp` and write to `../../data/paddy/processed/module_N/` and
`../../reports/figures/paddy/module_N/`.

```
01-field-extraction ──▶ data/paddy/processed/module_1/Klasifikasi_Sawah.tif (+ .geojson)  paddy mask, read by 02-04
        │
        ├──▶ 02-1-growth-phase   GEE monthly S2/S1/CHIRPS composites → growth phase + cropping index (IP)
        ├──▶ 03-health           vegetation indices, VHI + drought, VHI trend (Mann-Kendall / Sen)
        └──▶ 04-productivity     LUE constant productivity + WOFOST potential
```

1. `01-field-extraction.ipynb` — Dynamic World paddy mask + accuracy assessment
2. `02-1-growth-phase.ipynb` — growth phase from GEE time series
3. `03-health.ipynb` — vegetation indices, VHI, drought
4. `04-productivity.ipynb` — LUE and WOFOST productivity

Variants (kept because they differ):

- `01-field-extraction-road-river-revision.ipynb` — Module 1 revision (2026-09-22) that removes roads/rivers using
  `jaringan_jalan_sungai.geojson`. It still reads/writes **in its working directory** (`AOI_1.shp`,
  `jaringan_jalan_sungai.geojson`): copy those from `data/paddy/raw/` next to it, or align its paths with 01.
- `02-growth-phase-from-hotspot-repo.ipynb` — Lamongan growth-phase variant (Planetary Computer + GEE version),
  moved here from `hotspot-monitoring-model`. Reads `Klasifikasi_15x15_Sawah_Saja.tif` from its working directory.

## Palm oil

Packages delivered by the analyst for **SIAK_AOI01, 2025**. The web app ports them in `src/.../palm.py`.

| Output | Code | Delivered data (`data/palm_oil/processed/`) |
|---|---|---|
| 1 Plantation boundary | `notebooks/palm_oil/output-1-plantation-boundary.ipynb` | `output-1-plantation-boundary/` |
| 2 Tree age | `notebooks/palm_oil/output-2-tree-age.ipynb` | `output-2-tree-age/` |
| 3.1 Condition / inspection priority | `src/palm_oil/scripts/output-3-1/OUTPUT3_COMPLETE_PACKAGE/` (`README_START_HERE.md`) | inside the package |
| 3.2 Nutrient | — (not delivered) | `output-3-2-nutrient/` |
| 4 Productivity / management priority | `src/palm_oil/scripts/output-4/` (`README_OUTPUT4.txt`, `03_SCRIPTS/run_output4.py`) | `output-4/` |
| 5.2 Waterlogging | — (not delivered) | `output-5-2-waterlogging/` |

The Output 3.1 and 4 scripts contain the analyst's absolute Windows paths and GEE asset IDs; they are an archive of
how the products were made, not runnable as-is. From `src/palm_oil/scripts/output-4/`,
`python 03_SCRIPTS/run_output4.py --config 04_CONFIG/SIAK_AOI01_OUTPUT4_CONFIG.json --validate` works
(it looks for scripts in `<config>/../03_SCRIPTS`). They are not part of the installed library.

## Rules

1. Never commit data, rasters, zips or `.env` (`.gitignore` blocks them).
2. Never edit files in `data/<domain>/raw/`; derived output goes to `data/<domain>/processed/` or a new file name.
3. Logic used twice moves to `src/`; notebooks are for exploration.
4. Update `CHANGELOG.md` for every user-visible or structural change.
5. Notebook print/comment language: keep the language the notebook already uses (Indonesian) when editing it.

## Git

Default branch `main`; every change via pull request. `make lint` / `make test` (no make: copy the command from `Makefile`).
