#!/bin/bash
# Build CLISApp Android Release APK
# Usage: bash scripts/build-android-release.sh [--clean]
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FRONTEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ANDROID_DIR="$FRONTEND_DIR/android"
APK_OUTPUT="$ANDROID_DIR/app/build/outputs/apk/release/app-release.apk"
KEYSTORE_PATH="$ANDROID_DIR/app/clisapp-release.keystore"
ENV_PRODUCTION="$FRONTEND_DIR/.env.production"

echo ""
echo "🔨 CLISApp Android Release Build"
echo "================================="

# --- Check: keystore exists ---
if [ ! -f "$KEYSTORE_PATH" ]; then
    echo ""
    echo "❌ Release keystore not found: $KEYSTORE_PATH"
    echo "   Run this first: bash scripts/generate-keystore.sh"
    exit 1
fi
echo "✅ Keystore found"

# --- Check: .env.production has real IP ---
if [ -f "$ENV_PRODUCTION" ] && grep -q "YOUR_SERVER_IP" "$ENV_PRODUCTION"; then
    echo ""
    echo "⚠️  WARNING: .env.production still contains 'YOUR_SERVER_IP' placeholder"
    echo "   Edit CLISApp-frontend/.env.production and set your real server IP before distributing."
    echo "   Continuing build anyway..."
fi

# --- Optional clean ---
if [ "$1" = "--clean" ]; then
    echo ""
    echo "🧹 Cleaning previous build..."
    cd "$ANDROID_DIR" && ./gradlew clean
    echo "✅ Clean complete"
fi

# --- Build ---
echo ""
echo "⚙️  Building release APK..."
cd "$ANDROID_DIR"
./gradlew assembleRelease

# --- Result ---
if [ -f "$APK_OUTPUT" ]; then
    SIZE=$(du -sh "$APK_OUTPUT" | cut -f1)
    echo ""
    echo "✅ Build successful!"
    echo ""
    echo "📦 APK location: $APK_OUTPUT"
    echo "📏 File size:    $SIZE"
    echo ""
    echo "📤 Distribution options:"
    echo "   1. Send APK directly via WeChat / email / cloud drive"
    echo "   2. Upload to GitHub Releases for a download link"
    echo "   3. Use 'qrcp $APK_OUTPUT' to generate a QR code for local Wi-Fi install"
    echo ""
    echo "⚠️  Recipients must enable: Settings → Security → Install unknown apps"
else
    echo ""
    echo "❌ Build failed - APK not found at expected path"
    exit 1
fi
