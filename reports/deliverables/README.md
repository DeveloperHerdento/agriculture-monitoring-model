# Deliverables

A data product handed to another team or a client is a folder with this shape (HGS-STD Rule 11.8).
Copy `template/` to `data/<domain>/processed/<product>-<aoi>-<year>-v<version>/`, fill it, then zip it.
Only the template lives in git; real packages (rasters, geojson) stay in ignored `data/<domain>/processed/`.

```
<package>/
├── README.md              identity, version, CRS, resolution, QC status, limitations ("not for ...")
├── MANIFEST.json          what is in the package and its status
├── CHECKSUM_SHA256.csv    FILE,SHA256 for every file (paths relative to the package, forward slashes)
└── 01_.. 05_..            data folders, e.g. 01_INTERMEDIATE, 02_CLASSIFICATION, 03_FINAL_PRODUCT,
                           04_QC_STATS, 05_VISUALIZATION
```

Reference package: palm-oil Output 1, `data/palm_oil/processed/output-1-plantation-boundary/`
(received 2026-09, archive in `data/palm_oil/raw/source-drops/FINAL_OUTPUT_1.zip`).

Checksums (Git Bash):

```bash
cd <package> && echo "FILE,SHA256" > CHECKSUM_SHA256.csv && \
  find . -type f ! -name CHECKSUM_SHA256.csv | sort | while read f; do \
  echo "${f#./},$(sha256sum "$f" | cut -d' ' -f1)"; done >> CHECKSUM_SHA256.csv
```
