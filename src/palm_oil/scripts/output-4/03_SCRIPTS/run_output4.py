#!/usr/bin/env python
from pathlib import Path
import argparse
import json
import subprocess
import sys

def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def validate(cfg):
    required = [
        "aoi_id",
        "monitoring_year",
        "projected_crs",
        "grid_size_m",
        "inputs",
        "transfer_policy",
    ]
    missing = [k for k in required if k not in cfg]
    if missing:
        raise ValueError("Missing config keys: " + ", ".join(missing))

    print("CONFIG VALID")
    print("AOI:", cfg["aoi_id"])
    print("Monitoring year:", cfg["monitoring_year"])
    print("CRS:", cfg["projected_crs"])
    print("Grid:", cfg["grid_size_m"], "m")

def resolve_script(config_path, script_value):
    p = Path(script_value)
    if p.is_absolute():
        return p

    package_root = config_path.resolve().parent.parent

    candidates = [
        package_root / "03_SCRIPTS" / script_value,
        package_root / script_value,
        config_path.resolve().parent / script_value,
    ]

    for c in candidates:
        if c.exists():
            return c

    return candidates[0]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--run-stage")
    args = ap.parse_args()

    config_path = Path(args.config)
    cfg = load_config(config_path)

    if args.validate:
        validate(cfg)

    stage_map = cfg.get("stage_script_map", {})

    if args.list:
        if not stage_map:
            print("No explicit stage_script_map configured.")
        for key, value in stage_map.items():
            print(key, "->", value)

    if args.run_stage:
        if args.run_stage not in stage_map:
            raise KeyError(
                f"Stage {args.run_stage!r} is not explicitly mapped. "
                "Do not auto-guess a development script."
            )

        script = resolve_script(config_path, stage_map[args.run_stage])

        if not script.exists():
            raise FileNotFoundError(script)

        print("Running:", script)
        subprocess.run(
            [sys.executable, str(script)],
            cwd=str(script.parent),
            check=True,
        )

if __name__ == "__main__":
    main()
