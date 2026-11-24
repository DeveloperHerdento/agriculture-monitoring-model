# New AOI Readiness

## Ready now

- AOI-specific JSON configuration.
- Persistent GEE asset audit.
- Frozen 30F calibration loading.
- Frozen 30G wall-to-wall reconstruction.
- Seven-band product QA.
- AOI01 canonical reproducibility comparison.
- Web-delivery/export orchestration.
- Full working-notebook development-history backup.

## Upstream source capture

{
  "30A": {
    "captured_code_cells": 7,
    "source_capture_exists": true
  },
  "30B": {
    "captured_code_cells": 1,
    "source_capture_exists": true
  },
  "30C": {
    "captured_code_cells": 0,
    "source_capture_exists": false
  },
  "30D": {
    "captured_code_cells": 0,
    "source_capture_exists": false
  },
  "30E": {
    "captured_code_cells": 1,
    "source_capture_exists": true
  }
}

## Current automation claim

Prepared standardized 30D/30E assets
→ final Output 3:

**READY**

AOI01 reproducibility:

**READY**

Raw external source
→ 30A → 30B → 30C → 30D → 30E
→ 30F → 30G → delivery:

**NOT YET CLAIMED AS ONE-CLICK**

This distinction is deliberate.

Captured notebook source may rely on development-state
variables and is therefore not automatically treated as a
standalone production module.

## Reuse rule

For a new AOI, the current safe workflow is:

1. Produce standardized upstream assets.
2. Fill OUTPUT3_AOI_TEMPLATE.json.
3. Run asset audit.
4. Run transfer-test mode.
5. Review QA.
6. Export only after QA passes.

Technical portability must not be described as validated
field accuracy.
