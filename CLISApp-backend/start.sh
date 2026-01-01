#!/bin/bash

# DEPRECATED: This script is deprecated in Phase 1 and will be removed in Phase 2.
#
# Migration Path: Use the root Makefile instead
#   - For all services:  make up      (from repo root)
#   - For API only:      make api-up  (from repo root)
#   - For tiles only:    make tiles-up (from repo root)
#
# This wrapper delegates to the Makefile for backward compatibility.

echo "⚠️  DEPRECATED: start.sh is deprecated and will be removed in Phase 2."
echo "    Please use 'make up' from the repo root instead."
echo "    Delegating to Makefile for backward compatibility..."
echo ""

# Navigate to repo root (one level up from CLISApp-backend)
cd "$(dirname "$0")/.."

# Delegate to Makefile
make up

