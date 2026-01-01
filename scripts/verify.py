#!/usr/bin/env python3
"""
Aggregated Verification Script

Runs all verification checks in sequence:
- verify-backend (automated)
- verify-pipeline (automated)
- verify-mobile instructions (manual)

Creates a unified summary report for the entire verification suite.
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

# Get repository root
REPO_ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = REPO_ROOT / "_bmad-output" / "verification-reports"
EVIDENCE_DIR = REPO_ROOT / "_bmad-output" / "verification-evidence"


def print_header():
    """Print verification start header"""
    print()
    print("=" * 70)
    print("AGGREGATED VERIFICATION")
    print("=" * 70)
    print()


def run_verification_check(name, command):
    """
    Run a verification check and return results.

    Args:
        name: Name of the check (e.g., "Backend", "Pipeline")
        command: List of command arguments (e.g., ["make", "verify-backend"])

    Returns:
        (passed: bool, output: str, duration: float)
    """
    import time

    print(f"Running {name} Verification...")
    print("-" * 70)

    start_time = time.time()

    try:
        # Preserve environment variables for smoke/test modes
        env = os.environ.copy()

        result = subprocess.run(
            command,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=180,
            env=env,
        )

        duration = time.time() - start_time
        output = result.stdout + result.stderr

        passed = result.returncode == 0

        if passed:
            print(f"  ✓ {name} verification PASSED")
        else:
            print(f"  ✗ {name} verification FAILED (exit code: {result.returncode})")

        print()

        return passed, output, duration

    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        print(f"  ✗ {name} verification TIMEOUT")
        print()
        return False, "TIMEOUT", duration
    except Exception as e:
        duration = time.time() - start_time
        print(f"  ✗ {name} verification ERROR: {e}")
        print()
        return False, f"ERROR: {e}", duration


def _summarize_output(output, max_lines=8):
    if not output:
        return ["<no output>"]
    lines = [line.rstrip() for line in output.splitlines() if line.strip()]
    if not lines:
        return ["<no output>"]
    if len(lines) <= max_lines:
        return lines
    head = lines[:3]
    tail = lines[-3:]
    return head + ["..."] + tail


def create_report(results, overall_passed):
    """
    Create verification summary report.

    Args:
        results: List of (name, passed, output, duration) tuples
        overall_passed: Overall verification status

    Returns:
        Path to report file
    """
    # Create report directory
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    # Generate report filename
    today = datetime.now().strftime("%Y-%m-%d")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_file = REPORT_DIR / f"verify-{today}.md"

    # Build report content
    lines = []
    lines.append(f"# Verification Report")
    lines.append(f"")
    lines.append(f"**Date**: {timestamp}")
    lines.append(f"**Status**: {'✓ PASS' if overall_passed else '✗ FAIL'}")
    lines.append(f"")

    # Environment info
    lines.append(f"## Environment")
    lines.append(f"")
    lines.append(f"- Test Mode: {os.environ.get('PIPELINE_TEST_MODE', 'Not set')}")
    lines.append(f"- Smoke Mode: {os.environ.get('PIPELINE_SMOKE_MODE', 'Not set')}")
    lines.append(f"- API Port: {os.environ.get('API_PORT', '8080 (default)')}")
    lines.append(f"- Tiles Port: {os.environ.get('TILES_PORT', '8000 (default)')}")
    lines.append(f"")

    # Automated checks section
    lines.append(f"## Automated Verification Checks")
    lines.append(f"")

    for name, passed, output, duration in results:
        status_icon = "✓" if passed else "✗"
        status_text = "PASS" if passed else "FAIL"
        log_slug = name.lower().replace(" ", "-")
        log_file = REPORT_DIR / f"verify-{today}-{log_slug}.log"
        log_file.write_text(output or "")
        output_summary = _summarize_output(output)

        lines.append(f"### {name} Verification")
        lines.append(f"")
        lines.append(f"- **Status**: {status_icon} {status_text}")
        lines.append(f"- **Duration**: {duration:.2f}s")
        lines.append(f"- **Log**: `{log_file.relative_to(REPO_ROOT)}`")
        lines.append(f"- **Output Summary**:")
        lines.append(f"  ```")
        for line in output_summary:
            lines.append(f"  {line}")
        lines.append(f"  ```")
        lines.append(f"")

        if not passed:
            lines.append(f"**Issue**: Check failed. See logs for details.")
            lines.append(f"")

    # Log locations
    pipeline_report = REPORT_DIR / f"verify-pipeline-{today}.md"
    pipeline_log = REPORT_DIR / f"verify-pipeline-{today}.log"
    lines.append(f"## Logs and Output Locations")
    lines.append(f"")
    lines.append(f"- API logs: `CLISApp-backend/logs/api.log`")
    lines.append(f"- Tile server logs: `CLISApp-backend/logs/tiles.log`")
    lines.append(f"- Pipeline verify report: `{pipeline_report.relative_to(REPO_ROOT)}`")
    lines.append(f"- Pipeline verify log: `{pipeline_log.relative_to(REPO_ROOT)}`")
    lines.append(f"- Tiles output: `CLISApp-backend/tiles/<layer>/`")
    lines.append(f"")

    # Manual verification section
    lines.append(f"## Manual Verification Required")
    lines.append(f"")
    lines.append(f"⚠️  **Mobile app verification must be performed manually.**")
    lines.append(f"")
    lines.append(f"### Steps:")
    lines.append(f"")
    lines.append(f"1. Run the mobile verification checklist:")
    lines.append(f"   ```bash")
    lines.append(f"   make verify-mobile")
    lines.append(f"   ```")
    lines.append(f"")
    lines.append(f"2. Follow the step-by-step checklist for iOS and Android")
    lines.append(f"")
    lines.append(f"3. Capture evidence screenshots in the designated directories:")
    lines.append(f"   - iOS: `_bmad-output/verification-evidence/<date>/mobile/ios/`")
    lines.append(f"   - Android: `_bmad-output/verification-evidence/<date>/mobile/android/`")
    lines.append(f"")
    lines.append(f"4. Ensure all required screenshots are captured:")
    lines.append(f"   - launch.png")
    lines.append(f"   - map-loaded.png")
    lines.append(f"   - layer-pm25.png, layer-uv.png, layer-precipitation.png, layer-temperature.png, layer-humidity.png")
    lines.append(f"   - boundary-inside-qld.png, boundary-outside-qld.png")
    lines.append(f"")

    # Summary
    lines.append(f"## Summary")
    lines.append(f"")
    if overall_passed:
        lines.append(f"✓ All automated verification checks passed.")
        lines.append(f"")
        lines.append(f"**Next Steps:**")
        lines.append(f"- Run `make verify-mobile` and capture evidence")
        lines.append(f"- Verification is complete when mobile evidence is captured")
    else:
        lines.append(f"✗ One or more automated checks failed.")
        lines.append(f"")
        lines.append(f"**Next Actions:**")
        lines.append(f"- Review failed checks above")
        lines.append(f"- Check logs for details: `make logs`")
        lines.append(f"- Fix issues and re-run: `make verify`")

    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")
    lines.append(f"Generated by `make verify` at {timestamp}")
    lines.append(f"")

    # Write report
    report_file.write_text("\n".join(lines))

    return report_file


def print_summary(overall_passed, report_file):
    """Print final summary"""
    print("=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    print()

    if overall_passed:
        print("✓ All automated verification checks PASSED")
        print()
        print("Next Steps:")
        print("  → Run mobile verification: make verify-mobile")
        print("  → Capture evidence screenshots")
    else:
        print("✗ One or more automated checks FAILED")
        print()
        print("Next Actions:")
        print("  → Check logs: make logs")
        print("  → Fix issues and re-run: make verify")

    print()
    print(f"Report saved to: {report_file.relative_to(REPO_ROOT)}")
    print()
    print("=" * 70)
    print()


def main():
    """Main entry point"""
    print_header()

    # Run automated verification checks
    results = []

    # 1. Backend verification
    backend_passed, backend_output, backend_duration = run_verification_check(
        "Backend",
        ["make", "verify-backend"]
    )
    results.append(("Backend", backend_passed, backend_output, backend_duration))

    # 2. Pipeline verification
    pipeline_passed, pipeline_output, pipeline_duration = run_verification_check(
        "Pipeline",
        ["make", "verify-pipeline"]
    )
    results.append(("Pipeline", pipeline_passed, pipeline_output, pipeline_duration))

    # Determine overall status
    overall_passed = all(passed for _, passed, _, _ in results)

    # Create report
    report_file = create_report(results, overall_passed)

    # Print summary
    print_summary(overall_passed, report_file)

    # Exit with appropriate code
    return 0 if overall_passed else 1


if __name__ == "__main__":
    sys.exit(main())
