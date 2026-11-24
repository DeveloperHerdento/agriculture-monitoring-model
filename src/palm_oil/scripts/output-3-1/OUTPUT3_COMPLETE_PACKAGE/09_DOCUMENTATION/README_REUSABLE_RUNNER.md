# Output 3 Reusable Runner

## Main files

- `run_output3.py`
- `SIAK_AOI01_OUTPUT3_RUN_CONFIG.json`
- `OUTPUT3_AOI_TEMPLATE.json`

## AOI01 reproducibility

Run:

python run_output3.py --config SIAK_AOI01_OUTPUT3_RUN_CONFIG.json

The runner reconstructs the frozen downstream Output 3
product and compares INTEGRATED_CLASS against the
canonical AOI01 Earth Engine asset.

## Audit only

Run:

python run_output3.py --config SIAK_AOI01_OUTPUT3_RUN_CONFIG.json --audit-only

This checks required persistent assets without building the
analytical graph.

## New AOI

Copy `OUTPUT3_AOI_TEMPLATE.json`, replace the required
asset IDs, and use mode:

TRANSFER_TEST

At this stage the reusable runner assumes standardized
30D and 30E assets already exist.

30J-D will package the upstream 30A-30E process/source
provenance needed for complete handover.

## Scientific guardrail

Successful execution means technical reproducibility.

It does not by itself demonstrate:

- independent field accuracy;
- disease diagnosis;
- nutrient diagnosis;
- validated transferability to another AOI.