#!/usr/bin/env python3
"""
Pipeline Prerequisites Validator

Validates required credentials and system dependencies before running pipeline commands.
Provides fail-fast behavior with actionable guidance.

Usage:
    python scripts/pipeline_prereqs.py --layer pm25 --stage download
    python scripts/pipeline_prereqs.py --layer temperature --stage full

Environment Variables:
    PIPELINE_TEST_MODE=1  - Skip all prerequisite checks (for testing)
    PIPELINE_STRICT=1     - Fail on any missing optional prerequisite
"""

import argparse
import os
import sys
from pathlib import Path


# Test mode flag
TEST_MODE = os.environ.get("PIPELINE_TEST_MODE") == "1"
STRICT_MODE = os.environ.get("PIPELINE_STRICT") == "1"

from pipeline_locations import LAYER_ALIASES, normalize_layer


# Prerequisite configurations per layer/stage (canonical layer keys)
PREREQUISITES = {
    "pm25": {
        "download": {
            "credentials": [
                {
                    "name": "Copernicus CDS API",
                    "check": lambda: Path.home() / ".cdsapirc",
                    "required": True,
                    "how_to_fix": [
                        "1. Register at https://cds.climate.copernicus.eu/",
                        "2. Create ~/.cdsapirc with your API key",
                        "3. See CLISApp-backend/README.md for details",
                    ],
                },
            ],
            "python_modules": ["cdsapi"],
        },
        "process": {
            "python_modules": ["cfgrib", "xarray", "rasterio"],
            "notes": ["Requires eccodes library (system dependency)"],
        },
        "tiles": {
            "python_modules": ["PIL", "rasterio"],
        },
    },
    "uv": {
        "download": {
            "credentials": [
                {
                    "name": "Copernicus CDS API",
                    "check": lambda: Path.home() / ".cdsapirc",
                    "required": True,
                    "how_to_fix": [
                        "1. Register at https://cds.climate.copernicus.eu/",
                        "2. Create ~/.cdsapirc with your API key",
                        "3. See CLISApp-backend/README.md for details",
                    ],
                },
            ],
            "python_modules": ["cdsapi"],
        },
        "process": {
            "python_modules": ["xarray", "rasterio"],
        },
        "tiles": {
            "python_modules": ["PIL", "rasterio"],
        },
    },
    "precipitation": {
        "download": {
            "credentials": [
                {
                    "name": "NASA Earthdata",
                    "check": lambda: Path.home() / ".netrc",
                    "required": False,  # May work without it in some cases
                    "how_to_fix": [
                        "1. Register at https://urs.earthdata.nasa.gov/",
                        "2. Create ~/.netrc with credentials for urs.earthdata.nasa.gov",
                        "3. See CLISApp-backend/README.md for details",
                    ],
                },
            ],
            "python_modules": ["requests"],
        },
        "process": {
            "python_modules": ["xarray", "rasterio"],
        },
        "tiles": {
            "python_modules": ["PIL", "rasterio"],
        },
    },
    "temperature": {
        "download": {
            "notes": ["Uses Open-Meteo API (no credentials required)"],
        },
        "process": {
            "python_modules": ["httpx", "numpy", "rasterio"],
            "notes": ["Download and process are combined for Open-Meteo"],
        },
        "tiles": {
            "python_modules": ["PIL", "rasterio"],
        },
    },
    "humidity": {
        "download": {
            "notes": ["Uses Open-Meteo API (no credentials required)"],
        },
        "process": {
            "python_modules": ["httpx", "numpy", "rasterio"],
            "notes": ["Download and process are combined for Open-Meteo"],
        },
        "tiles": {
            "python_modules": ["PIL", "rasterio"],
        },
    },
}


def check_credential(cred_config):
    """
    Check if a credential is configured.

    Returns: (is_present, message)
    """
    check_func = cred_config["check"]
    credential_path = check_func()

    if isinstance(credential_path, Path):
        exists = credential_path.exists()
        if exists:
            return True, f"✓ {cred_config['name']} configured"
        else:
            how_to_fix = "\n     ".join(cred_config.get("how_to_fix", []))
            return False, f"✗ {cred_config['name']} missing\n     {how_to_fix}"
    else:
        # Custom check function
        return credential_path, f"✓ {cred_config['name']}"


def check_python_module(module_name):
    """
    Check if a Python module can be imported.

    Returns: (is_present, message)
    """
    try:
        __import__(module_name)
        return True, f"✓ {module_name}"
    except ImportError:
        return False, f"✗ {module_name} not installed (pip install {module_name})"


def validate_prerequisites(layer, stage="full"):
    """
    Validate prerequisites for a specific layer and stage.

    Args:
        layer: Layer name (pm25, uv, precip, temperature, humidity)
        stage: Stage name (download, process, tiles, full)

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    print()
    print("=" * 70)
    print("PIPELINE PREREQUISITE VALIDATION")
    print("=" * 70)
    print()
    layer = normalize_layer(layer)
    print(f"Layer: {layer}")
    print(f"Stage: {stage}")
    print(f"Test Mode: {TEST_MODE}")
    print(f"Strict Mode: {STRICT_MODE}")
    print()

    if TEST_MODE:
        print("  ℹ️  Test mode enabled - prerequisite checks skipped")
        print("  ℹ️  In real mode, the following would be checked:")
        print()

    # Get prerequisites for this layer
    if layer not in PREREQUISITES:
        print(f"  ✗ Unknown layer: {layer}")
        print(f"  ℹ️  Supported layers: {', '.join(PREREQUISITES.keys())}")
        if LAYER_ALIASES:
            aliases = ", ".join(f"{k}→{v}" for k, v in sorted(LAYER_ALIASES.items()))
            print(f"  ℹ️  Aliases: {aliases}")
        return 1

    layer_prereqs = PREREQUISITES[layer]

    # Determine which stages to check
    stages_to_check = []
    if stage == "full":
        stages_to_check = ["download", "process", "tiles"]
    elif stage in ["download", "process", "tiles"]:
        stages_to_check = [stage]
    else:
        print(f"  ✗ Unknown stage: {stage}")
        return 1

    # Validate each stage
    all_passed = True
    for check_stage in stages_to_check:
        if check_stage not in layer_prereqs:
            continue

        stage_prereqs = layer_prereqs[check_stage]

        print(f"Stage: {check_stage}")
        print("-" * 70)

        # Check credentials
        if "credentials" in stage_prereqs:
            print("  Credentials:")
            for cred in stage_prereqs["credentials"]:
                if TEST_MODE:
                    print(f"    [SKIP] {cred['name']} (required: {cred['required']})")
                else:
                    is_present, message = check_credential(cred)
                    print(f"    {message}")
                    if not is_present and (cred["required"] or STRICT_MODE):
                        all_passed = False

        # Check Python modules
        if "python_modules" in stage_prereqs:
            print("  Python Modules:")
            for module in stage_prereqs["python_modules"]:
                if TEST_MODE:
                    print(f"    [SKIP] {module}")
                else:
                    is_present, message = check_python_module(module)
                    print(f"    {message}")
                    if not is_present:
                        # Python modules are typically required
                        all_passed = False

        # Print notes
        if "notes" in stage_prereqs:
            print("  Notes:")
            for note in stage_prereqs["notes"]:
                print(f"    ℹ️  {note}")

        print()

    # Summary
    if TEST_MODE:
        print("✓ Test mode - all checks skipped")
        return 0
    elif all_passed:
        print("✓ All prerequisites satisfied")
        return 0
    else:
        print("✗ Some prerequisites are missing")
        print()
        print("  See CLISApp-backend/README.md for setup instructions")
        return 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate pipeline prerequisites before running"
    )
    parser.add_argument(
        "--layer",
        required=True,
        choices=list(PREREQUISITES.keys()) + list(LAYER_ALIASES.keys()),
        help="Climate data layer",
    )
    parser.add_argument(
        "--stage",
        default="full",
        choices=["full", "download", "process", "tiles"],
        help="Pipeline stage (default: full)",
    )

    args = parser.parse_args()

    exit_code = validate_prerequisites(args.layer, args.stage)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
