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
cat > "$RUN_SCRIPT" <<'EOF_RUNNER'
#!/bin/bash
set -euo pipefail

LOG_FILE="/var/log/clisapp-pipeline.log"
BACKEND_DIR="/opt/clisapp/CLISAPP/CLISApp-backend"
VENV_PYTHON="/opt/clisapp/venv/bin/python"
RUN_AS_USER="ubuntu"

log() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') $1"
}

mkdir -p "$(dirname "$LOG_FILE")"
touch "$LOG_FILE"
exec > >(tee -a "$LOG_FILE") 2> >(tee -a "$LOG_FILE" >&2)

log "✅ Pipeline started"
START_TS=$(date +%s)

if [ ! -x "$VENV_PYTHON" ]; then
  log "❌ Python runtime not found at $VENV_PYTHON"
  exit 1
fi

if [ ! -d "$BACKEND_DIR" ]; then
  log "❌ Backend directory not found at $BACKEND_DIR"
  exit 1
fi

RUN_CMD=$(cat <<'INNER'
cd /opt/clisapp/CLISAPP/CLISApp-backend
if [ -f .env ]; then
  set -a
  . ./.env
  set +a
fi
export PYTHONPATH=/opt/clisapp/CLISAPP/CLISApp-backend
export PIPELINE_TRIGGER=scheduled
exec /opt/clisapp/venv/bin/python -m data_pipeline.processing.openmeteo.process_all_layers
INNER
)

if sudo -u "$RUN_AS_USER" bash -lc "$RUN_CMD"; then
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
EOF_RUNNER

chmod +x "$RUN_SCRIPT"

step "Installing cron entry (every 4 hours)"
CRON_LINE="0 */4 * * * /opt/clisapp/run-pipeline.sh"
( crontab -l 2>/dev/null | grep -v "/opt/clisapp/run-pipeline.sh" || true; echo "$CRON_LINE" ) | crontab -

step "Cron installed"

step "Installing logrotate config for pipeline log"
cp "$SCRIPT_DIR/logrotate-clisapp-pipeline" /etc/logrotate.d/clisapp-pipeline
chmod 644 /etc/logrotate.d/clisapp-pipeline
step "Logrotate installed (rotate at 10MB, keep 4 compressed copies)"

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
