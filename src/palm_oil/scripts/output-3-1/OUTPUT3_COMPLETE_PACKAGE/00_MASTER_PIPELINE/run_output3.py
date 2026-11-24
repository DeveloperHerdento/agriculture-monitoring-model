#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Reusable Output 3 runner.

Current automation level:

Standardized persistent 30D/30E GEE assets
    ->
Frozen 30F parameters
    ->
30G integrated product
    ->
QA

This runner does NOT yet build 30A-30E from raw sources.
Upstream stage-builder packaging is handled separately.
"""

from pathlib import Path
import argparse
import json
import ssl

import certifi
import ee
import pandas as pd


EXPECTED_BANDS = [
    "CORE_CLASS",
    "CORE_RISK_SCORE_0_100",
    "CONTEXT_MODIFIER_SCORE",
    "CONTEXT_MODIFIER_COVERAGE",
    "INTEGRATED_SCORE_0_100",
    "INTEGRATED_CLASS",
    "CLASS_DELTA",
]


# ============================================================
# UTILITIES
# ============================================================

def load_json(path):

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


def locate_project_root():

    start = Path.cwd().resolve()

    for candidate in [
        start,
        *start.parents
    ]:

        if (
            candidate /
            "OUTPUT3_COMPLETE_PACKAGE"
        ).exists():

            return candidate

    raise FileNotFoundError(
        "Could not locate project root containing "
        "OUTPUT3_COMPLETE_PACKAGE."
    )


def resolve_project_path(
    project_root,
    value
):

    path = Path(value)

    if path.is_absolute():
        return path

    return (
        project_root /
        path
    )


def initialize_ee(
    project_id
):

    ssl._create_default_https_context = (
        lambda:
        ssl.create_default_context(
            cafile=certifi.where()
        )
    )

    try:

        ee.Initialize(
            project=project_id
        )

    except Exception:

        ee.Authenticate()

        ee.Initialize(
            project=project_id
        )


# ============================================================
# CONFIG VALIDATION
# ============================================================

def validate_config(
    cfg
):

    required_top = [
        "project_id",
        "aoi_id",
        "reference_year",
        "mode",
        "assets",
        "frozen_model",
        "execution",
    ]

    missing = [
        key
        for key in required_top
        if key not in cfg
    ]

    if missing:

        raise ValueError(
            f"Missing config fields: {missing}"
        )


    if cfg[
        "mode"
    ] not in {
        "REPRODUCE",
        "TRANSFER_TEST",
    }:

        raise ValueError(
            "mode must be REPRODUCE "
            "or TRANSFER_TEST."
        )


# ============================================================
# ASSET AUDIT
# ============================================================

def check_asset(
    asset_id
):

    if (
        asset_id is None
        or
        asset_id == "REQUIRED"
    ):

        return False

    try:

        ee.data.getAsset(
            asset_id
        )

        return True

    except Exception:

        return False


def audit_assets(
    cfg
):

    required = [

        "plantation_boundary",

        "core_30d",

        "age_30e01",

        "chirps_30e02a",

        "era5_30e02b",

        "etpet_30e02c",

        "terrain_30e03a",

        "hydrology_30e03b",

        "soil_30e04a",

        "soil_water_30e04b",
    ]


    results = {}


    for key in required:

        asset_id = (
            cfg[
                "assets"
            ]
            .get(key)
        )

        exists = check_asset(
            asset_id
        )

        results[
            key
        ] = {

            "asset_id":
                asset_id,

            "status":
                (
                    "PASS"
                    if exists
                    else
                    "MISSING_OR_NOT_CONFIGURED"
                )
        }


    return results


# ============================================================
# FROZEN PARAMETERS
# ============================================================

def load_frozen_parameters(
    cfg,
    project_root
):

    frozen = cfg[
        "frozen_model"
    ]


    calibration_path = (
        resolve_project_path(
            project_root,
            frozen[
                "calibration_csv"
            ]
        )
    )


    weights_path = (
        resolve_project_path(
            project_root,
            frozen[
                "family_weights_csv"
            ]
        )
    )


    if not calibration_path.exists():

        raise FileNotFoundError(
            calibration_path
        )


    if not weights_path.exists():

        raise FileNotFoundError(
            weights_path
        )


    calibration_df = pd.read_csv(
        calibration_path
    )


    family_weight_df = pd.read_csv(
        weights_path
    )


    if len(
        calibration_df
    ) != 8:

        raise RuntimeError(
            "Expected 8 frozen modifier features; "
            f"found {len(calibration_df)}."
        )


    if len(
        family_weight_df
    ) != 4:

        raise RuntimeError(
            "Expected 4 frozen context families; "
            f"found {len(family_weight_df)}."
        )


    return (
        calibration_df,
        family_weight_df
    )


# ============================================================
# 30G FROZEN INTEGRATION
# ============================================================

def build_integrated_product(
    cfg,
    project_root
):

    assets = cfg[
        "assets"
    ]

    frozen = cfg[
        "frozen_model"
    ]


    (
        calibration_df,
        family_weight_df
    ) = load_frozen_parameters(
        cfg,
        project_root
    )


    feature_source_registry = {

        "LOCAL_RELIEF_300M_M":
            assets[
                "terrain_30e03a"
            ],

        "SLOPE_DEG":
            assets[
                "terrain_30e03a"
            ],

        "HAND_M":
            assets[
                "hydrology_30e03b"
            ],

        "SILT_PCT_DEEP_100_200CM":
            assets[
                "soil_30e04a"
            ],

        "SOC_GKG_SURFACE_0_30CM":
            assets[
                "soil_30e04a"
            ],

        "WV1500_DEEP_100_200CM":
            assets[
                "soil_water_30e04b"
            ],

        "WV10_DEEP_100_200CM":
            assets[
                "soil_water_30e04b"
            ],

        "PAW_PROXY_SURFACE_0_30CM":
            assets[
                "soil_water_30e04b"
            ],
    }


    core_img = ee.Image(
        assets[
            "core_30d"
        ]
    )


    core_class = (
        core_img
        .select(
            "CONDITION_CLASS"
        )
        .round()
        .toInt16()
    )


    core_raw = (
        core_img
        .select(
            "CONDITION_CLASS_RAW"
        )
        .round()
        .toInt16()
    )


    core_risk = (
        core_img
        .select(
            "RISK_SCORE_0_100"
        )
        .toFloat()
    )


    valid_mask = (
        core_class
        .gte(1)
        .And(
            core_class.lte(4)
        )
    )


    # --------------------------------------------------------
    # DIRECTIONAL FEATURES
    # --------------------------------------------------------

    directional_images = {}


    for _, row in (
        calibration_df
        .iterrows()
    ):

        feature = row[
            "feature"
        ]


        if (
            feature
            not in
            feature_source_registry
        ):

            raise KeyError(
                "No source mapping for frozen feature: "
                f"{feature}"
            )


        source = (
            ee.Image(
                feature_source_registry[
                    feature
                ]
            )
            .select(
                feature
            )
            .toFloat()
            .updateMask(
                valid_mask
            )
        )


        p10 = float(
            row[
                "p10"
            ]
        )

        p90 = float(
            row[
                "p90"
            ]
        )

        direction = int(
            row[
                "association_direction"
            ]
        )


        if p90 <= p10:

            raise ValueError(
                f"Invalid calibration range "
                f"for {feature}: "
                f"P10={p10}, P90={p90}"
            )


        norm01 = (
            source
            .subtract(
                p10
            )
            .divide(
                p90 - p10
            )
            .clamp(
                0,
                1
            )
        )


        if direction < 0:

            norm01 = (
                ee.Image
                .constant(1)
                .subtract(
                    norm01
                )
            )


        directional_images[
            feature
        ] = (
            norm01
            .multiply(2)
            .subtract(1)
            .rename(
                f"DIR_{feature}"
            )
        )


    # --------------------------------------------------------
    # FAMILY COMPOSITES
    # --------------------------------------------------------

    family_score_images = {}


    for family in (
        family_weight_df[
            "family"
        ]
        .tolist()
    ):

        family_cal = (
            calibration_df[
                calibration_df[
                    "family"
                ] == family
            ]
        )


        weighted_sum = (
            ee.Image
            .constant(0)
            .toFloat()
        )


        available_weight = (
            ee.Image
            .constant(0)
            .toFloat()
        )


        for _, row in (
            family_cal
            .iterrows()
        ):

            feature = row[
                "feature"
            ]

            weight = float(
                row[
                    "within_family_weight"
                ]
            )

            img = (
                directional_images[
                    feature
                ]
            )


            valid = (
                img
                .mask()
                .reduce(
                    ee.Reducer.min()
                )
                .gt(0)
            )


            weighted_sum = (
                weighted_sum
                .add(
                    img
                    .unmask(0)
                    .multiply(
                        weight
                    )
                )
            )


            available_weight = (
                available_weight
                .add(
                    valid
                    .toFloat()
                    .multiply(
                        weight
                    )
                )
            )


        family_score_images[
            family
        ] = (
            weighted_sum
            .divide(
                available_weight
                .max(1e-6)
            )
            .updateMask(
                available_weight
                .gte(0.50)
            )
            .clamp(
                -1,
                1
            )
            .rename(
                f"FAMILY_SCORE_{family}"
            )
        )


    # --------------------------------------------------------
    # FAMILY-BALANCED CONTEXT MODIFIER
    # --------------------------------------------------------

    overall_sum = (
        ee.Image
        .constant(0)
        .toFloat()
    )


    overall_weight = (
        ee.Image
        .constant(0)
        .toFloat()
    )


    for _, row in (
        family_weight_df
        .iterrows()
    ):

        family = row[
            "family"
        ]

        family_weight = float(
            row[
                "family_weight"
            ]
        )


        img = (
            family_score_images[
                family
            ]
        )


        valid = (
            img
            .mask()
            .reduce(
                ee.Reducer.min()
            )
            .gt(0)
        )


        overall_sum = (
            overall_sum
            .add(
                img
                .unmask(0)
                .multiply(
                    family_weight
                )
            )
        )


        overall_weight = (
            overall_weight
            .add(
                valid
                .toFloat()
                .multiply(
                    family_weight
                )
            )
        )


    context_modifier = (
        overall_sum
        .divide(
            overall_weight
            .max(1e-6)
        )
        .updateMask(
            overall_weight
            .gte(0.75)
        )
        .clamp(
            -1,
            1
        )
        .rename(
            "CONTEXT_MODIFIER_SCORE"
        )
    )


    context_coverage = (
        overall_weight
        .rename(
            "CONTEXT_MODIFIER_COVERAGE"
        )
    )


    # --------------------------------------------------------
    # F05 SCORE
    # --------------------------------------------------------

    amplitude = float(
        frozen[
            "fusion_amplitude"
        ]
    )


    integrated_score = (
        core_risk
        .add(
            context_modifier
            .unmask(0)
            .multiply(
                amplitude
            )
        )
        .clamp(
            0,
            100
        )
        .rename(
            "INTEGRATED_SCORE_0_100"
        )
    )


    # --------------------------------------------------------
    # CORE EVIDENCE
    # --------------------------------------------------------

    optical_valid = (
        core_img
        .select(
            "OPTICAL_VALID_PERIOD_COUNT"
        )
    )


    alert_mask = (
        core_img
        .select(
            "ALERT_MASK"
        )
        .round()
    )


    max_period_class = (
        core_img
        .select(
            "MAX_PERIOD_CLASS"
        )
    )


    max_consecutive = (
        core_img
        .select(
            "MAX_CONSECUTIVE_ALERT"
        )
    )


    optical_alert_total = (
        core_img
        .select(
            "GREENNESS_ALERT_PERIODS"
        )
        .add(
            core_img
            .select(
                "RED_EDGE_ALERT_PERIODS"
            )
        )
        .add(
            core_img
            .select(
                "MOISTURE_ALERT_PERIODS"
            )
        )
    )


    has_optical_support = (
        optical_valid
        .gt(0)
        .And(
            optical_alert_total
            .gt(0)
        )
    )


    # Preserve 30D RAW -> FINAL decisions.

    unlocked = (
        core_raw
        .neq(
            core_class
        )
        .Not()
    )


    # --------------------------------------------------------
    # FROZEN THRESHOLDS
    # --------------------------------------------------------

    thresholds = (
        frozen[
            "thresholds"
        ]
    )


    T12 = float(
        thresholds[
            "T12"
        ]
    )

    T23 = float(
        thresholds[
            "T23"
        ]
    )

    T34 = float(
        thresholds[
            "T34"
        ]
    )


    modifier_available = (
        context_modifier
        .mask()
        .reduce(
            ee.Reducer.min()
        )
        .gt(0)
    )


    modifier_pos = (
        context_modifier
        .unmask(0)
        .gt(0)
    )


    modifier_neg = (
        context_modifier
        .unmask(0)
        .lt(0)
    )


    # --------------------------------------------------------
    # TRANSITION RULES
    # --------------------------------------------------------

    promote_1_2 = (
        core_class
        .eq(1)
        .And(
            unlocked
        )
        .And(
            modifier_available
        )
        .And(
            modifier_pos
        )
        .And(
            integrated_score
            .gte(T12)
        )
        .And(
            alert_mask
            .eq(1)
        )
    )


    promote_2_3 = (
        core_class
        .eq(2)
        .And(
            unlocked
        )
        .And(
            modifier_available
        )
        .And(
            modifier_pos
        )
        .And(
            integrated_score
            .gte(T23)
        )
        .And(
            has_optical_support
        )
        .And(
            max_period_class
            .gte(3)
        )
        .And(
            max_consecutive
            .gte(2)
        )
    )


    promote_3_4 = (
        core_class
        .eq(3)
        .And(
            unlocked
        )
        .And(
            modifier_available
        )
        .And(
            modifier_pos
        )
        .And(
            integrated_score
            .gte(T34)
        )
        .And(
            has_optical_support
        )
        .And(
            max_period_class
            .gte(3)
        )
        .And(
            max_consecutive
            .gte(3)
        )
    )


    demote_2_1 = (
        core_class
        .eq(2)
        .And(
            unlocked
        )
        .And(
            modifier_available
        )
        .And(
            modifier_neg
        )
        .And(
            integrated_score
            .lt(T12)
        )
        .And(
            alert_mask
            .eq(0)
        )
    )


    demote_3_2 = (
        core_class
        .eq(3)
        .And(
            unlocked
        )
        .And(
            modifier_available
        )
        .And(
            modifier_neg
        )
        .And(
            integrated_score
            .lt(T23)
        )
        .And(
            max_consecutive
            .lte(1)
        )
    )


    demote_4_3 = (
        core_class
        .eq(4)
        .And(
            unlocked
        )
        .And(
            modifier_available
        )
        .And(
            modifier_neg
        )
        .And(
            integrated_score
            .lt(T34)
        )
        .And(
            max_consecutive
            .lte(2)
        )
    )


    # --------------------------------------------------------
    # FINAL CLASS
    # --------------------------------------------------------

    integrated_class = (
        core_class
        .where(
            promote_1_2,
            2
        )
        .where(
            promote_2_3,
            3
        )
        .where(
            promote_3_4,
            4
        )
        .where(
            demote_2_1,
            1
        )
        .where(
            demote_3_2,
            2
        )
        .where(
            demote_4_3,
            3
        )
        .rename(
            "INTEGRATED_CLASS"
        )
        .toInt16()
    )


    class_delta = (
        integrated_class
        .subtract(
            core_class
        )
        .rename(
            "CLASS_DELTA"
        )
        .toInt16()
    )


    final_img = (
        core_class
        .rename(
            "CORE_CLASS"
        )
        .addBands(
            core_risk
            .rename(
                "CORE_RISK_SCORE_0_100"
            )
        )
        .addBands(
            context_modifier
        )
        .addBands(
            context_coverage
        )
        .addBands(
            integrated_score
        )
        .addBands(
            integrated_class
        )
        .addBands(
            class_delta
        )
        .updateMask(
            valid_mask
        )
    )


    return final_img


# ============================================================
# BASIC QA
# ============================================================

def basic_qa(
    img
):

    bands = (
        img
        .bandNames()
        .getInfo()
    )


    return {

        "band_names":
            bands,

        "seven_band_contract":
            bands
            ==
            EXPECTED_BANDS
    }


# ============================================================
# AOI01 CANONICAL COMPARISON
# ============================================================

def compare_to_canonical(
    img,
    canonical_asset
):

    if not canonical_asset:

        return {

            "performed":
                False,

            "reason":
                "canonical_final is not configured"
        }


    canonical = ee.Image(
        canonical_asset
    )


    projection = (
        canonical
        .select(
            "INTEGRATED_CLASS"
        )
        .projection()
        .getInfo()
    )


    crs = projection[
        "crs"
    ]

    transform = projection[
        "transform"
    ]


    rebuilt_class = (
        img
        .select(
            "INTEGRATED_CLASS"
        )
        .reproject(
            crs=crs,
            crsTransform=transform
        )
    )


    mismatch = (
        rebuilt_class
        .neq(
            canonical
            .select(
                "INTEGRATED_CLASS"
            )
        )
        .rename(
            "MISMATCH"
        )
    )


    mismatch_area = (
        ee.Image
        .pixelArea()
        .divide(
            10000
        )
        .rename(
            "AREA_HA"
        )
        .updateMask(
            mismatch
        )
        .reduceRegion(

            reducer=
                ee.Reducer.sum(),

            geometry=
                canonical.geometry(),

            crs=
                crs,

            crsTransform=
                transform,

            maxPixels=
                1e13,

            tileScale=
                4
        )
        .get(
            "AREA_HA"
        )
        .getInfo()
    )


    if mismatch_area is None:

        mismatch_area = 0.0


    mismatch_area = float(
        mismatch_area
    )


    return {

        "performed":
            True,

        "mismatch_area_ha":
            mismatch_area,

        "pass":
            mismatch_area == 0.0
    }


# ============================================================
# MAIN
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=
            "Reusable Output 3 analytical runner"
    )


    parser.add_argument(

        "--config",

        required=True,

        help=
            "Path to Output 3 AOI JSON config."
    )


    parser.add_argument(

        "--audit-only",

        action="store_true",

        help=
            "Validate configuration and assets only."
    )


    args = parser.parse_args()


    project_root = (
        locate_project_root()
    )


    config_path = (
        Path(
            args.config
        )
        .resolve()
    )


    cfg = load_json(
        config_path
    )


    validate_config(
        cfg
    )


    initialize_ee(
        cfg[
            "project_id"
        ]
    )


    print(
        "=" * 90
    )

    print(
        "OUTPUT 3 REUSABLE RUNNER"
    )

    print(
        "=" * 90
    )


    print(
        "AOI  :",
        cfg[
            "aoi_id"
        ]
    )

    print(
        "Mode :",
        cfg[
            "mode"
        ]
    )


    # --------------------------------------------------------
    # Asset audit
    # --------------------------------------------------------

    asset_audit = audit_assets(
        cfg
    )


    print(
        "\nASSET AUDIT"
    )


    for key, result in (
        asset_audit.items()
    ):

        print(
            f"{key:25s}: "
            f"{result['status']}"
        )


    asset_pass = all(

        item[
            "status"
        ] == "PASS"

        for item in
        asset_audit.values()
    )


    if not asset_pass:

        raise RuntimeError(
            "Required standardized upstream "
            "assets are missing or not configured."
        )


    if args.audit_only:

        print(
            "\nRUNNER RESULT: "
            "ASSET CONTRACT PASS"
        )

        print(
            "No analytical graph was built."
        )

        return


    # --------------------------------------------------------
    # Build frozen Output 3 graph
    # --------------------------------------------------------

    final_img = (
        build_integrated_product(
            cfg,
            project_root
        )
    )


    qa = basic_qa(
        final_img
    )


    print(
        "\nOUTPUT BANDS:"
    )

    print(
        qa[
            "band_names"
        ]
    )


    print(
        "Seven-band contract:",
        (
            "PASS"
            if qa[
                "seven_band_contract"
            ]
            else
            "FAIL"
        )
    )


    if not qa[
        "seven_band_contract"
    ]:

        raise RuntimeError(
            "Seven-band Output 3 contract failed."
        )


    # --------------------------------------------------------
    # Reproduction QA for AOI01
    # --------------------------------------------------------

    if cfg[
        "mode"
    ] == "REPRODUCE":

        comparison = (
            compare_to_canonical(

                final_img,

                cfg[
                    "assets"
                ]
                .get(
                    "canonical_final"
                )
            )
        )


        print(
            "\nCANONICAL COMPARISON:"
        )


        print(
            json.dumps(
                comparison,
                indent=2
            )
        )


        if (
            comparison.get(
                "performed"
            )
            and
            not comparison.get(
                "pass"
            )
        ):

            raise RuntimeError(
                "Reconstructed INTEGRATED_CLASS "
                "does not match canonical asset."
            )


    # --------------------------------------------------------
    # Transfer warning
    # --------------------------------------------------------

    if cfg[
        "mode"
    ] == "TRANSFER_TEST":

        print(
            "\nTRANSFER TEST WARNING:\n"
            "Frozen AOI01 parameters are being used.\n"
            "This demonstrates technical portability only.\n"
            "It does NOT demonstrate field accuracy or\n"
            "validated transferability for the new AOI."
        )


    # --------------------------------------------------------
    # Export policy
    # --------------------------------------------------------

    if not cfg[
        "execution"
    ][
        "start_exports"
    ]:

        print(
            "\nEXPORTS: NOT STARTED "
            "(intentional QA-first policy)."
        )


    print(
        "\nRUNNER RESULT: PASS"
    )


if __name__ == "__main__":

    main()
