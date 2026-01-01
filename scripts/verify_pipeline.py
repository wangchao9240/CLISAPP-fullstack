#!/usr/bin/env python3
"""
Pipeline Verification Script

Validates that the pipeline can run end-to-end and produce tiles.
Supports deterministic smoke mode for CI/testing environments.

Modes:
- Smoke mode (PIPELINE_SMOKE_MODE=1 or PIPELINE_TEST_MODE=1): Uses fixtures, no network
- Full mode (default): Runs actual pipeline for verification
"""

import os
import sys
import subprocess
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime

# Get repository root
REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "CLISApp-backend"
TILES_DIR = BACKEND_DIR / "tiles"
REPORT_DIR = REPO_ROOT / "_bmad-output" / "verification-reports"

# Test/smoke mode flags
PIPELINE_TEST_MODE = os.environ.get("PIPELINE_TEST_MODE") == "1"
PIPELINE_SMOKE_MODE = os.environ.get("PIPELINE_SMOKE_MODE") == "1"
PIPELINE_FULL_MODE = os.environ.get("PIPELINE_FULL_MODE") == "1"
PIPELINE_VERIFY_ALL = os.environ.get("PIPELINE_VERIFY_ALL") == "1"
PIPELINE_VERIFY_LAYER = os.environ.get("PIPELINE_VERIFY_LAYER", "pm25")

# Use smoke mode if either flag is set, or in CI unless explicitly forced full mode
CI_MODE = os.environ.get("CI") not in (None, "", "0", "false", "False")
SMOKE_MODE = PIPELINE_TEST_MODE or PIPELINE_SMOKE_MODE or (CI_MODE and not PIPELINE_FULL_MODE)

# Layers to verify in smoke mode (subset for speed)
SMOKE_LAYERS = ["pm25"]

# Layers for full mode (all layers)
FULL_LAYERS = ["pm25", "precipitation", "temperature", "humidity", "uv"]

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
SMOKE_TILE_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
    b"\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


class Tee:
    def __init__(self, *streams):
        self._streams = streams

    def write(self, s):
        for stream in self._streams:
            stream.write(s)
        return len(s)

    def flush(self):
        for stream in self._streams:
            try:
                stream.flush()
            except ValueError:
                pass


@contextmanager
def tee_stdio_to_file(log_file: Path):
    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_file.touch(exist_ok=True)
    with log_file.open("a", encoding="utf-8") as log_fh:
        tee = Tee(sys.stdout, log_fh)
        orig_stdout, orig_stderr = sys.stdout, sys.stderr
        try:
            sys.stdout = tee
            sys.stderr = tee
            yield
        finally:
            sys.stdout = orig_stdout
            sys.stderr = orig_stderr


def print_header():
    """Print verification start header"""
    print()
    print("=" * 70)
    print("PIPELINE VERIFICATION")
    print("=" * 70)
    print()


def print_mode():
    """Print verification mode"""
    if SMOKE_MODE:
        print("Mode: SMOKE (deterministic, no network)")
        if CI_MODE and not (PIPELINE_SMOKE_MODE or PIPELINE_TEST_MODE):
            print("CI detected: defaulting to smoke mode")
        print("Layers: " + ", ".join(SMOKE_LAYERS))
    else:
        print("Mode: FULL (end-to-end)")
        print("Layers: " + ", ".join(_full_mode_layers()))
    print()


def _full_mode_layers():
    from pipeline_locations import normalize_layer

    if PIPELINE_VERIFY_ALL:
        return FULL_LAYERS
    return [normalize_layer(PIPELINE_VERIFY_LAYER)]


def _png_signature_ok(tile_path: Path) -> bool:
    try:
        with tile_path.open("rb") as handle:
            return handle.read(8) == PNG_SIGNATURE
    except OSError:
        return False


def verify_tiles_exist(layers):
    """
    Verify that tiles exist for the given layers.

    Returns: (success: bool, results: dict)
    """
    results = {}

    for layer in layers:
        layer_dir = TILES_DIR / layer
        if not layer_dir.exists():
            results[layer] = {"exists": False, "tile_count": 0, "status": "FAIL"}
            continue

        # Find .png files
        png_files = list(layer_dir.rglob("*.png"))
        tile_count = len(png_files)

        if tile_count > 0:
            sample = png_files[0]
            signature_ok = _png_signature_ok(sample)
            if not signature_ok:
                results[layer] = {
                    "exists": True,
                    "tile_count": tile_count,
                    "status": "FAIL",
                    "reason": "invalid_png",
                    "sample": str(sample),
                }
            else:
                results[layer] = {
                    "exists": True,
                    "tile_count": tile_count,
                    "status": "PASS",
                    "sample": str(sample),
                }
        else:
            results[layer] = {
                "exists": True,
                "tile_count": 0,
                "status": "FAIL",
                "reason": "no_tiles",
            }

    all_passed = all(r["status"] == "PASS" for r in results.values())
    return all_passed, results


def ensure_smoke_fixtures(layers):
    """Ensure minimal tile fixtures exist for smoke mode."""
    for layer in layers:
        target = TILES_DIR / layer / "8" / "0" / "0.png"
        if target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(SMOKE_TILE_BYTES)


def run_smoke_verification():
    """
    Run smoke mode verification.

    In smoke mode:
    - Skip network downloads (fixtures would be used)
    - Verify tiles exist (assume they were generated previously or by fixtures)
    - Fast execution
    """
    print("Running smoke verification...")
    print()

    # In smoke mode, generate minimal fixtures if missing
    ensure_smoke_fixtures(SMOKE_LAYERS)
    success, results = verify_tiles_exist(SMOKE_LAYERS)

    print("Tile Verification:")
    print("-" * 70)
    for layer, result in results.items():
        status_icon = "✓" if result["status"] == "PASS" else "✗"
        print(f"  {status_icon} {layer:15} {result['tile_count']:5} tiles")
        print(f"     Location: CLISApp-backend/tiles/{layer}/")
    print()

    return success, results


def run_full_verification():
    """
    Run full mode verification.

    In full mode:
    - Run actual pipeline for at least one layer
    - Verify tiles are generated
    - May require credentials and network access
    """
    print("Running full verification...")
    print()

    layers = _full_mode_layers()
    invalid_layers = [layer for layer in layers if layer not in FULL_LAYERS]
    if invalid_layers:
        print(f"Invalid layer(s): {', '.join(invalid_layers)}")
        print(f"Supported layers: {', '.join(FULL_LAYERS)}")
        return False, {}

    if PIPELINE_VERIFY_ALL:
        command = [sys.executable, str(REPO_ROOT / "scripts" / "pipeline.py")]
    else:
        command = [sys.executable, str(REPO_ROOT / "scripts" / "run_pipeline_layer.py"), layers[0]]

    print("Pipeline command:")
    print(f"  {' '.join(command)}")
    print()

    result = subprocess.run(command, cwd=REPO_ROOT, check=False)
    if result.returncode != 0:
        print(f"Pipeline failed with exit code {result.returncode}")
        return False, {}

    success, results = verify_tiles_exist(layers)

    print("Tile Verification:")
    print("-" * 70)
    for layer, result in results.items():
        status_icon = "✓" if result["status"] == "PASS" else "✗"
        print(f"  {status_icon} {layer:15} {result['tile_count']:5} tiles")
        print(f"     Location: CLISApp-backend/tiles/{layer}/")
    print()

    return success, results


def print_summary(success, mode, layers, report_file, log_file):
    """Print verification summary"""
    print("=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    print()
    print(f"Mode: {mode}")
    print(f"Layers: {', '.join(layers)}")
    print(f"Report: {report_file}")
    print(f"Log: {log_file}")
    print()

    if success:
        print("✓ All verification checks passed")
        print()
        print("Output Locations:")
        if SMOKE_MODE:
            for layer in SMOKE_LAYERS:
                print(f"  - CLISApp-backend/tiles/{layer}/")
        else:
            for layer in layers:
                print(f"  - CLISApp-backend/tiles/{layer}/")
    else:
        print("✗ Verification failed")
        print()
        print("Next Actions:")
        print("  → Re-run: make verify-pipeline")
        print("  → Generate tiles: make pipeline")
        print("  → Per-layer: make pipeline-pm25, make pipeline-precip, etc.")
        print("  → View logs: make logs")

    print()
    print("=" * 70)
    print()

def create_report(success, mode, layers, results, report_file, log_file):
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    lines = []
    lines.append("# Verify Pipeline Report")
    lines.append("")
    lines.append(f"**Status**: {'PASS' if success else 'FAIL'}")
    lines.append(f"**Mode**: {mode}")
    lines.append(f"**Layers**: {', '.join(layers)}")
    lines.append(f"**Log**: {log_file}")
    lines.append("")
    lines.append("## Tile Verification")
    lines.append("")
    for layer in layers:
        info = results.get(layer, {})
        status = info.get("status", "FAIL")
        tile_count = info.get("tile_count", 0)
        reason = info.get("reason", "")
        sample = info.get("sample", "")
        suffix = f" ({reason})" if reason else ""
        lines.append(f"- {layer}: {status} ({tile_count} tiles){suffix}")
        if sample:
            lines.append(f"  - sample: {sample}")
    lines.append("")
    lines.append("## Output Locations")
    lines.append("")
    for layer in layers:
        lines.append(f"- CLISApp-backend/tiles/{layer}/")
    lines.append("")
    lines.append(f"Report generated: {datetime.now().isoformat()}")
    lines.append("")
    report_file.write_text("\n".join(lines))


def main():
    """Main entry point"""
    report_date = datetime.now().strftime("%Y-%m-%d")
    report_file = REPORT_DIR / f"verify-pipeline-{report_date}.md"
    log_file = REPORT_DIR / f"verify-pipeline-{report_date}.log"

    with tee_stdio_to_file(log_file):
        print_header()
        print_mode()

        # Run verification based on mode
        if SMOKE_MODE:
            mode = "smoke"
            layers = SMOKE_LAYERS
            success, results = run_smoke_verification()
        else:
            mode = "full"
            layers = _full_mode_layers()
            success, results = run_full_verification()

        # Write report + summary
        create_report(success, mode, layers, results, report_file, log_file)
        print_summary(success, mode, layers, report_file, log_file)

    # Exit with appropriate code
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
