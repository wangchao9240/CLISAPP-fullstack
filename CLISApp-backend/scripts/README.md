# CLISApp Deployment Scripts

## GCP Deployment (Recommended)

### Prerequisites
- GCP account with billing enabled
- `gcloud` CLI or Console access
- GitHub repo URL (SSH or HTTPS)

### VM creation (gcloud CLI)
```bash
gcloud compute instances create clisapp-backend \
  --zone=us-central1-a \
  --machine-type=e2-micro \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=30GB \
  --tags=clisapp-backend
```

### VM creation (Console)
1. Go to Compute Engine > VM instances > Create instance.
2. Choose Ubuntu 22.04 LTS, machine type `e2-micro` (free tier), 30GB boot disk.
3. Add network tag `clisapp-backend` to match firewall rules.

### Firewall rules
```bash
gcloud compute firewall-rules create clisapp-backend-allow \
  --allow tcp:8080,tcp:8000 \
  --target-tags clisapp-backend
```

### Copy scripts and SSH
```bash
gcloud compute scp CLISApp-backend/scripts/gcp-setup.sh CLISApp-backend/scripts/gcp-test.sh \
  ubuntu@clisapp-backend:~ --zone=us-central1-a

gcloud compute ssh ubuntu@clisapp-backend --zone=us-central1-a
```

### Run setup
```bash
sudo bash ~/gcp-setup.sh <REPO_URL>
```

### Run tests
```bash
bash ~/gcp-test.sh
```

### Service management
```bash
sudo systemctl status clisapp-api clisapp-tiles
sudo systemctl start clisapp-api clisapp-tiles
sudo systemctl stop clisapp-api clisapp-tiles
sudo systemctl restart clisapp-api clisapp-tiles
```

### Logs
```bash
tail -f /opt/clisapp/CLISAPP/CLISApp-backend/logs/api.log
tail -f /opt/clisapp/CLISAPP/CLISApp-backend/logs/tiles.log
```

### Swap
- Swap is automatically configured by `gcp-setup.sh` if `/swapfile` is missing.

## Usage Order

1. `server-setup.sh` — Oracle Cloud server initialization (Docker, firewall, data dirs, compose up)
2. `setup-cron.sh` — Install pipeline schedule (cron, optional systemd timer)
3. `generate-keystore.sh` — Android release signing (located at `CLISApp-frontend/scripts/generate-keystore.sh`)

## Scripts

- `server-setup.sh`
  - Updates OS packages, installs Docker/Compose, opens ports 8080/8000 with iptables
  - Creates `/opt/clisapp` and required data directories
  - Creates/updates `/opt/clisapp/CLISAPP/CLISApp-backend/.env.production`
  - Starts services with Docker Compose and runs health checks

- `setup-cron.sh`
  - Creates `/opt/clisapp/run-pipeline.sh`
  - Installs cron schedule to run every 4 hours
  - Optional systemd timer install when `USE_SYSTEMD=1`

- `clisapp-pipeline.service` / `clisapp-pipeline.timer`
  - Systemd units for running the pipeline every 4 hours
  - Install via `setup-cron.sh` with `USE_SYSTEMD=1`

## Notes

- Run scripts with sudo (they modify system packages and cron).
- For production IPs, export `SERVER_IP` before running `server-setup.sh`.
