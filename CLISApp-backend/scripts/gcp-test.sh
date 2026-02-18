#!/bin/bash
set -e

step() {
  echo "OK: $1"
}

fail() {
  echo "ERROR: $1" >&2
  exit 1
}

if [ "$(id -un)" != "ubuntu" ]; then
  fail "Please run as the ubuntu user."
fi

step "Checking API health"
api_resp=$(curl -fsS http://localhost:8080/api/v1/health) || fail "API health check failed"
echo "API response: $api_resp"

step "Checking tile server health"
tiles_resp=$(curl -fsS http://localhost:8000/health) || fail "Tile server health check failed"
echo "Tiles response: $tiles_resp"

echo "Stopping services to free RAM..."
sudo systemctl stop clisapp-api clisapp-tiles

step "Running OpenMeteo processing"
start_ts=$(date +"%Y-%m-%d %H:%M:%S")
echo "Processing start: $start_ts"
cd /opt/clisapp/CLISAPP/CLISApp-backend
/opt/clisapp/venv/bin/python -m data_pipeline.processing.openmeteo.process_all_layers
end_ts=$(date +"%Y-%m-%d %H:%M:%S")
echo "Processing end: $end_ts"

step "Inspecting tiles output"
du -sh tiles/
ls tiles/

step "Restarting services"
sudo systemctl start clisapp-api clisapp-tiles
sleep 5

step "Checking sample tile"
curl -I http://localhost:8000/tiles/pm25/6/59/37.png
sample_code=$(curl -s -o /dev/null -w "%{http_code}" -I http://localhost:8000/tiles/pm25/6/59/37.png)
if [ "$sample_code" -ne 200 ]; then
  fail "Sample tile check failed with HTTP $sample_code"
fi

EXTERNAL_IP="$(curl -s ifconfig.me || true)"
step "Test summary"
echo "External IP: ${EXTERNAL_IP:-unknown}"
echo "API health: http://${EXTERNAL_IP:-<external-ip>}:8080/api/v1/health"
echo "Tiles health: http://${EXTERNAL_IP:-<external-ip>}:8000/health"
echo "Sample tile: http://${EXTERNAL_IP:-<external-ip>}:8000/tiles/pm25/6/59/37.png"
