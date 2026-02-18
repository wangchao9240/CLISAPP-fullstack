#!/bin/bash
set -e

if [ "$(id -u)" -ne 0 ]; then
  echo "❌ Please run as root (sudo)."
  exit 1
fi

APP_ROOT="/opt/clisapp"
REPO_DIR="$APP_ROOT/CLISAPP"
BACKEND_DIR="$REPO_DIR/CLISApp-backend"
ENV_FILE="$BACKEND_DIR/.env.production"

step() {
  echo "✅ $1"
}

fail() {
  echo "❌ $1"
  exit 1
}

step "Updating system packages"
apt-get update -y
apt-get install -y ca-certificates curl gnupg lsb-release

step "Installing Docker and Docker Compose"
install -m 0755 -d /etc/apt/keyrings
if [ ! -f /etc/apt/keyrings/docker.gpg ]; then
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
fi

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list
apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker

step "Configuring firewall (iptables) for ports 8080 and 8000"
iptables -C INPUT -p tcp --dport 8080 -j ACCEPT 2>/dev/null || iptables -I INPUT -p tcp --dport 8080 -j ACCEPT
iptables -C INPUT -p tcp --dport 8000 -j ACCEPT 2>/dev/null || iptables -I INPUT -p tcp --dport 8000 -j ACCEPT

step "Creating application directory"
mkdir -p "$APP_ROOT"

if [ ! -d "$REPO_DIR" ]; then
  echo "❌ Repository not found at $REPO_DIR"
  echo "✅ Placeholder: git clone <REPO_URL> $REPO_DIR"
  exit 1
fi

step "Creating data directories (tiles and processed data)"
mkdir -p "$BACKEND_DIR/tiles"
mkdir -p "$BACKEND_DIR/data/processed"

step "Configuring .env.production"
if [ ! -f "$ENV_FILE" ]; then
  cat > "$ENV_FILE" <<'EOF'
PRODUCTION_API_URL=http://YOUR_SERVER_IP:8080
PRODUCTION_TILE_URL=http://YOUR_SERVER_IP:8000
EOF
fi

if [ -n "${SERVER_IP:-}" ]; then
  sed -i "s/YOUR_SERVER_IP/${SERVER_IP}/g" "$ENV_FILE"
  step "Updated .env.production using SERVER_IP=${SERVER_IP}"
else
  step "SERVER_IP not set; leaving YOUR_SERVER_IP placeholder"
fi

step "Starting services via Docker Compose"
cd "$BACKEND_DIR"
docker compose up -d --build

step "Verifying API health"
curl -fsS http://localhost:8080/api/v1/health >/dev/null || fail "API health check failed"

step "Verifying Tile Server health"
curl -fsS http://localhost:8000/health >/dev/null || fail "Tile server health check failed"

step "Server setup completed successfully"
