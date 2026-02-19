#!/bin/bash
set -e

step() {
  echo "OK: $1"
}

fail() {
  echo "ERROR: $1" >&2
  exit 1
}

if [ "$(id -u)" -ne 0 ]; then
  fail "Please run as root (sudo)."
fi

REPO_URL="${1:-}"
if [ -z "$REPO_URL" ]; then
  fail "REPO_URL is required as the first argument."
fi

APP_ROOT="/opt/clisapp"
REPO_DIR="$APP_ROOT/CLISAPP"
BACKEND_DIR="$REPO_DIR/CLISApp-backend"
VENV_DIR="$APP_ROOT/venv"

step "Updating package index and installing system dependencies"
apt-get update -y
apt-get install -y \
  python3.11 python3.11-venv python3-pip git curl build-essential \
  gdal-bin libgdal-dev libgeos-dev libproj-dev libspatialindex-dev

step "Configuring swap (2G)"
if [ -f /swapfile ]; then
  step "Swapfile already exists, skipping creation"
else
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  if ! grep -q "^/swapfile " /etc/fstab; then
    echo "/swapfile none swap sw 0 0" >> /etc/fstab
  fi
  step "Swapfile created and enabled"
fi

step "Preparing application directory"
mkdir -p "$APP_ROOT"

if [ -d "$REPO_DIR/.git" ]; then
  step "Repository exists, pulling latest changes"
  git -C "$REPO_DIR" fetch --all --prune
  git -C "$REPO_DIR" pull
else
  step "Cloning repository"
  git clone "$REPO_URL" "$REPO_DIR"
fi

step "Checking out deployment branch feature/migrate-to-openmeteo"
git -C "$REPO_DIR" checkout feature/migrate-to-openmeteo
git -C "$REPO_DIR" pull

step "Creating Python virtual environment"
python3.11 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -r "$BACKEND_DIR/requirements.txt"

step "Ensuring data, tiles, and logs directories exist"
mkdir -p "$BACKEND_DIR/tiles" "$BACKEND_DIR/data/processing" "$BACKEND_DIR/logs"

step "Writing backend .env"
cat > "$BACKEND_DIR/.env" <<'ENVEOF'
DEBUG=False
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8080
DATA_ROOT=./data
TILES_PATH=./tiles
TILE_SIZE=256
MIN_ZOOM=6
MAX_ZOOM=13
ENVEOF

step "Installing systemd service files"
cp "$BACKEND_DIR/scripts/clisapp-api.service" /etc/systemd/system/clisapp-api.service
cp "$BACKEND_DIR/scripts/clisapp-tiles.service" /etc/systemd/system/clisapp-tiles.service

step "Enabling and starting services"
systemctl daemon-reload
systemctl enable --now clisapp-api clisapp-tiles

step "Waiting for services to initialize"
sleep 5

step "Running health checks"
curl -fsS http://localhost:8080/api/v1/health >/dev/null || fail "API health check failed"
curl -fsS http://localhost:8000/health >/dev/null || fail "Tile server health check failed"

EXTERNAL_IP="$(curl -s ifconfig.me || true)"
step "Deployment complete"
echo "External IP: ${EXTERNAL_IP:-unknown}"
echo "API health: http://${EXTERNAL_IP:-<external-ip>}:8080/api/v1/health"
echo "Tiles health: http://${EXTERNAL_IP:-<external-ip>}:8000/health"
echo "Sample tile: http://${EXTERNAL_IP:-<external-ip>}:8000/tiles/pm25/6/59/37.png"
