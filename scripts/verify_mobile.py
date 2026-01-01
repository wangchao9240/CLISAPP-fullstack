#!/usr/bin/env python3
"""
Mobile Verification Checklist Generator

Generates a manual checklist for iOS and Android mobile app verification.
Creates evidence directories and guides consistent regression testing.

This is NOT automated testing - it's a manual checklist + evidence folder convention.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Get repository root
REPO_ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_BASE = REPO_ROOT / "_bmad-output" / "verification-evidence"


def create_evidence_directories():
    """
    Create canonical evidence directories for today's run.

    Returns: (ios_dir, android_dir)
    """
    today = datetime.now().strftime("%Y-%m-%d")
    mobile_base = EVIDENCE_BASE / today / "mobile"

    ios_dir = mobile_base / "ios"
    android_dir = mobile_base / "android"

    # Create directories
    ios_dir.mkdir(parents=True, exist_ok=True)
    android_dir.mkdir(parents=True, exist_ok=True)

    return ios_dir, android_dir


def print_header():
    """Print verification header"""
    print()
    print("=" * 70)
    print("MOBILE APP VERIFICATION CHECKLIST")
    print("=" * 70)
    print()
    print("This is a MANUAL verification checklist for iOS and Android.")
    print("Follow the steps below and capture evidence in the designated folders.")
    print()


def print_prerequisites():
    """Print prerequisites section"""
    print("Prerequisites")
    print("-" * 70)
    print("  1. Ensure backend services are running:")
    print("     → make status")
    print("     → If not running: make up")
    print()
    print("  2. Ensure tiles are generated:")
    print("     → make verify-backend")
    print("     → If tiles missing: make pipeline")
    print("     → Or per-layer: make pipeline-pm25, make pipeline-precip, etc.")
    print()


def print_checklist():
    """Print verification checklist for both platforms"""
    print("Verification Checklist")
    print("-" * 70)
    print()

    print("iOS Verification:")
    print("  [ ] 1. Launch app on iOS Simulator")
    print("       - Open CLISApp-iOS in Xcode")
    print("       - Build and run on simulator")
    print("       - Capture: launch.png")
    print()
    print("  [ ] 2. Verify map loads")
    print("       - Confirm map displays Queensland region")
    print("       - Capture: map-loaded.png")
    print()
    print("  [ ] 3. Test five-layer switching:")
    print("       - Switch to PM2.5 layer → Capture: layer-pm25.png")
    print("       - Switch to UV layer → Capture: layer-uv.png")
    print("       - Switch to Precipitation layer → Capture: layer-precipitation.png")
    print("       - Switch to Temperature layer → Capture: layer-temperature.png")
    print("       - Switch to Humidity layer → Capture: layer-humidity.png")
    print()
    print("  [ ] 4. Verify Queensland-only coverage (boundary check):")
    print("       - Navigate to a location INSIDE Queensland")
    print("         → Climate overlay should be visible")
    print("         → Capture: boundary-inside-qld.png")
    print("       - Navigate to a location OUTSIDE Queensland (e.g., NSW, NT)")
    print("         → Climate overlay should be ABSENT (no-data/transparent tiles)")
    print("         → Capture: boundary-outside-qld.png")
    print()

    print("Android Verification:")
    print("  [ ] 1. Launch app on Android Emulator")
    print("       - Open CLISApp-Android in Android Studio")
    print("       - Build and run on emulator")
    print("       - Capture: launch.png")
    print()
    print("  [ ] 2. Verify map loads")
    print("       - Confirm map displays Queensland region")
    print("       - Capture: map-loaded.png")
    print()
    print("  [ ] 3. Test five-layer switching:")
    print("       - Switch to PM2.5 layer → Capture: layer-pm25.png")
    print("       - Switch to UV layer → Capture: layer-uv.png")
    print("       - Switch to Precipitation layer → Capture: layer-precipitation.png")
    print("       - Switch to Temperature layer → Capture: layer-temperature.png")
    print("       - Switch to Humidity layer → Capture: layer-humidity.png")
    print()
    print("  [ ] 4. Verify Queensland-only coverage (boundary check):")
    print("       - Navigate to a location INSIDE Queensland")
    print("         → Climate overlay should be visible")
    print("         → Capture: boundary-inside-qld.png")
    print("       - Navigate to a location OUTSIDE Queensland (e.g., NSW, NT)")
    print("         → Climate overlay should be ABSENT (no-data/transparent tiles)")
    print("         → Capture: boundary-outside-qld.png")
    print()


def print_evidence_locations(ios_dir, android_dir):
    """Print evidence directory locations"""
    print("Evidence Locations")
    print("-" * 70)
    print(f"  iOS:     {ios_dir.relative_to(REPO_ROOT)}")
    print(f"  Android: {android_dir.relative_to(REPO_ROOT)}")
    print()
    print("Store all screenshots and optional notes.md in these directories.")
    print()


def print_additional_artifacts(ios_dir, android_dir):
    """Print guidance for additional artifacts (logs, notes)."""
    print("Additional Artifacts")
    print("-" * 70)
    print("Store any logs or notes alongside the screenshots for each platform:")
    print(f"  iOS logs/notes:     {ios_dir.relative_to(REPO_ROOT)}")
    print(f"  Android logs/notes: {android_dir.relative_to(REPO_ROOT)}")
    print("Suggested filenames:")
    print("  - notes.md (manual notes)")
    print("  - logs.txt (captured logs)")
    print()


def print_evidence_naming_guide():
    """Print evidence naming guidance"""
    print("Evidence Naming Guide")
    print("-" * 70)
    print("  Required screenshots:")
    print("    - launch.png")
    print("    - map-loaded.png")
    print("    - layer-pm25.png")
    print("    - layer-uv.png")
    print("    - layer-precipitation.png")
    print("    - layer-temperature.png")
    print("    - layer-humidity.png")
    print("    - boundary-inside-qld.png")
    print("    - boundary-outside-qld.png")
    print()
    print("  Optional:")
    print("    - notes.md (any observations or issues)")
    print("    - logs.txt (copied logs for debugging)")
    print()


def print_pass_criteria():
    """Print what PASS looks like"""
    print("Pass Criteria")
    print("-" * 70)
    print("  ✓ App launches without crashes")
    print("  ✓ Map loads and displays Queensland")
    print("  ✓ All five layers switch successfully with visible overlays")
    print("  ✓ Inside Queensland: climate overlay is visible")
    print("  ✓ Outside Queensland: climate overlay is ABSENT (transparent/no-data)")
    print()


def print_reminder():
    """Print evidence capture reminder"""
    print("=" * 70)
    print("REMINDER")
    print("=" * 70)
    print()
    print("  This verification is MANUAL - you must capture evidence screenshots")
    print("  and store them in the evidence directories above.")
    print()
    print("  Verification is only considered COMPLETE when:")
    print("    - All checklist items are checked")
    print("    - All required screenshots are captured")
    print("    - Evidence is stored in the correct directories")
    print()
    print("=" * 70)
    print()


def main():
    """Main entry point"""
    # Create evidence directories
    ios_dir, android_dir = create_evidence_directories()

    # Print checklist
    print_header()
    print_prerequisites()
    print_checklist()
    print_evidence_locations(ios_dir, android_dir)
    print_additional_artifacts(ios_dir, android_dir)
    print_evidence_naming_guide()
    print_pass_criteria()
    print_reminder()

    # Always exit 0 (manual checklist)
    return 0


if __name__ == "__main__":
    sys.exit(main())
