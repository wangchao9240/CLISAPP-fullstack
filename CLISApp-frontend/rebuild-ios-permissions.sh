#!/bin/bash

echo "🧹 Cleaning iOS build artifacts..."

# 1. Clean Xcode DerivedData
echo "Deleting DerivedData..."
rm -rf ~/Library/Developer/Xcode/DerivedData

# 2. Clean Pods
echo "Removing Pods and Podfile.lock..."
cd ios
rm -rf Pods
rm -f Podfile.lock

# 3. Reinstall Pods
echo "Installing Pods..."
pod install

echo "✅ Done! Now you can rebuild the app with:"
echo "   npm run ios"
echo ""
echo "Or open the workspace in Xcode:"
echo "   open ios/CLISApp.xcworkspace"

