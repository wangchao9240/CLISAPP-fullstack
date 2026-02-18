#!/bin/bash
# Generate CLISApp release keystore
# Usage: bash scripts/generate-keystore.sh
keytool -genkeypair -v \
  -storetype PKCS12 \
  -keystore android/app/clisapp-release.keystore \
  -alias clisapp \
  -keyalg RSA \
  -keysize 2048 \
  -validity 10000 \
  -dname "CN=CLISApp, OU=Development, O=QUT, L=Brisbane, ST=Queensland, C=AU" \
  -storepass clisapp2024 \
  -keypass clisapp2024

echo "Keystore generated: android/app/clisapp-release.keystore"
