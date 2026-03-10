#!/bin/bash
set -euo pipefail

# Manual pipeline trigger — calls run-pipeline.sh directly (NOT via systemctl)
# so that PIPELINE_TRIGGER defaults to "manual" instead of inheriting the
# systemd service unit's Environment=PIPELINE_TRIGGER=scheduled.

if [ "$(id -u)" -ne 0 ]; then
  echo "❌ Please run as root (sudo)."
  exit 1
fi

RUN_SCRIPT="/opt/clisapp/run-pipeline.sh"
LOCK_FILE="/var/lock/clisapp-pipeline.lock"

if [ ! -x "$RUN_SCRIPT" ]; then
  echo "❌ Pipeline runner not found at $RUN_SCRIPT"
  echo "   Run setup-cron.sh first to generate it."
  exit 1
fi

# Pre-flight: check if pipeline is already running via flock
# (run-pipeline.sh has its own flock guard, but this gives an early warning)
if [ -f "$LOCK_FILE" ]; then
  exec 9>"$LOCK_FILE"
  if ! flock -n 9; then
    echo "⚠️ Pipeline execution already in progress (lock busy: $LOCK_FILE)"
    exit 75
  fi
  flock -u 9
fi

echo "▶ Starting pipeline manually (trigger_type=manual)"
if "$RUN_SCRIPT"; then
  STATUS=0
else
  STATUS=$?
fi

echo
if [ "$STATUS" -eq 0 ]; then
  echo "✅ Pipeline completed successfully"
else
  echo "❌ Pipeline failed (exit status: $STATUS)"
fi

echo
echo "Recent log output:"
tail -20 /var/log/clisapp-pipeline.log 2>/dev/null || echo "(no log file found)"

exit "$STATUS"
