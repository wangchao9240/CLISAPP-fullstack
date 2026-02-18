#!/bin/bash
set -e

if [ "$(id -u)" -ne 0 ]; then
  echo "❌ Please run as root (sudo)."
  exit 1
fi

APP_ROOT="/opt/clisapp"
BACKEND_DIR="$APP_ROOT/CLISAPP/CLISApp-backend"
RUN_SCRIPT="$APP_ROOT/run-pipeline.sh"
LOG_FILE="/var/log/clisapp-pipeline.log"
SCRIPT_DIR="$BACKEND_DIR/scripts"

step() {
  echo "✅ $1"
}

fail() {
  echo "❌ $1"
  exit 1
}

step "Creating pipeline runner script at $RUN_SCRIPT"
cat > "$RUN_SCRIPT" <<'EOF'
#!/bin/bash
set -e

LOG_FILE="/var/log/clisapp-pipeline.log"
BACKEND_DIR="/opt/clisapp/CLISAPP/CLISApp-backend"

log() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOG_FILE"
}

mkdir -p "$(dirname "$LOG_FILE")"
touch "$LOG_FILE"

log "✅ Pipeline started"
START_TS=$(date +%s)

if ! docker ps --format '{{.Names}}' | grep -q '^clisapp-backend$'; then
  log "❌ Backend container not running"
  exit 1
fi

cd "$BACKEND_DIR"
if docker exec clisapp-backend python -m data_pipeline.processing.openmeteo.process_all_layers; then
  STATUS=0
else
  STATUS=$?
fi

END_TS=$(date +%s)
DURATION=$((END_TS - START_TS))

if [ "$STATUS" -eq 0 ]; then
  log "✅ Pipeline finished in ${DURATION}s"
else
  log "❌ Pipeline failed (status ${STATUS}) after ${DURATION}s"
fi

exit "$STATUS"
EOF

chmod +x "$RUN_SCRIPT"

step "Installing cron entry (every 4 hours)"
CRON_LINE="0 */4 * * * /opt/clisapp/run-pipeline.sh >> /var/log/clisapp-pipeline.log 2>&1"
( crontab -l 2>/dev/null | grep -v "/opt/clisapp/run-pipeline.sh"; echo "$CRON_LINE" ) | crontab -

step "Cron installed"

if [ "${USE_SYSTEMD:-}" = "1" ]; then
  step "Installing systemd service and timer"
  if [ ! -f "$SCRIPT_DIR/clisapp-pipeline.service" ] || [ ! -f "$SCRIPT_DIR/clisapp-pipeline.timer" ]; then
    fail "Systemd unit files not found in $SCRIPT_DIR"
  fi
  cp "$SCRIPT_DIR/clisapp-pipeline.service" /etc/systemd/system/clisapp-pipeline.service
  cp "$SCRIPT_DIR/clisapp-pipeline.timer" /etc/systemd/system/clisapp-pipeline.timer
  systemctl daemon-reload
  systemctl enable --now clisapp-pipeline.timer
  step "Systemd timer enabled"
else
  step "Systemd optional install skipped (set USE_SYSTEMD=1 to enable)"
fi

step "Pipeline scheduling setup completed"
