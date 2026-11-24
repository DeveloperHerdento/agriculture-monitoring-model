OUTPUT 4 FINAL PACKAGE — SIAK_AOI01
================================

Product:
Productivity Potential & Management Priority

AOI:
SIAK_AOI01

Monitoring year:
2025

ASU:
Regular 500 x 500 m framework clipped to exact palm geometry.

Frozen domain:
820 ASUs
13867.10 ha exact palm area

PACKAGE
-------
01_WEB
    PASS 40J01 deployable web subset.

02_NOTEBOOK
    OUTPUT 4.ipynb working snapshot when found.
    MASTER_PIPELINE_OUTPUT4.ipynb canonical reproducibility/AOI-transfer notebook.

03_SCRIPTS
    Archived Output-4 scripts + reusable run_output4.py.

04_CONFIG
    Siak AOI config + reusable OUTPUT4_AOI_TEMPLATE.json + transfer guide.

05_MODEL_ARTIFACTS
    Selected PALMSIM/APSIM/process-model artifacts.

06_QA_METADATA
    QC/freeze/summary/manifest assets + environment + checksums.

07_PREVIEW
    Interactive presentation/QC HTML when available.

SCIENTIFIC CLAIM
----------------
Not a locally validated actual FFB yield prediction product.
Productivity = modelled/indicative potential.

PALMSIM = primary experimental process model.
APSIM OilPalm = representative process/scenario benchmark.
Class 4 = Replanting Evaluation Priority, not automatic replanting.

AOI TRANSFER
------------
Logic/schema/web contract are reusable.
AOI-specific inputs, CRS, area/count, climate mapping and model inputs must be rebuilt.
Siak numerical thresholds/calibration are only transfer-test V0 until new-AOI QA passes.

REPRODUCIBILITY SCOPE
---------------------
This archive provides the full delivery/reproducibility framework and validated
prepared-output/web packaging chain.

It does NOT claim a validated raw-source zero-to-final one-click 40A–40J run.
Use explicit canonical stage mappings instead of guessing among development versions.
