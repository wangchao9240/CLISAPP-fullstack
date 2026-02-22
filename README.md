# CLISAPP - Climate Information System Application

A full-stack climate data visualization system with FastAPI backend and React Native mobile frontend.

## Getting Started

Follow this single path to get the system running:

### 1. Discover Available Commands

```bash
make help
```

Lists all available Make targets and their descriptions.

### 2. Validate Prerequisites

```bash
make preflight
```

Validates that all required dependencies and configuration are in place before starting services.

### 3. Start Services

```bash
make up
```

Starts both the API service and tile server together.

### 4. Verify Services Are Running

```bash
make status
```

Checks the health of running services and provides guidance if any are down.

### 5. View Service Logs

```bash
make logs
```

Shows where logs are stored and provides commands to view/tail API and tile server logs.

### 6. Run Verification

```bash
make verify
```

Runs aggregated verification (backend health, pipeline smoke test, mobile checklist).

## Repository Structure

### Module Boundaries

- **`CLISApp-backend/`** - Backend services and data pipeline
  - FastAPI API service (port 8080)
  - Tile server (port 8000)
  - Data pipeline for processing climate data layers

- **`CLISApp-frontend/`** - React Native mobile application
  - iOS and Android support
  - Connects to backend API and tile server

- **`docs/`** - Generated project documentation
  - Architecture and design decisions
  - API contracts and development guides

For more details, see:
- [`docs/index.md`](docs/index.md) - Documentation starting point
- [`docs/development-guide-backend.md`](docs/development-guide-backend.md) - Backend setup and development
- [`docs/development-guide-frontend.md`](docs/development-guide-frontend.md) - Frontend setup and development

### Canonical Entry Points

**Makefile Entry Surface:**
- Repository root [`Makefile`](Makefile) - All canonical developer commands

**API Service:**
- Entry point: `CLISApp-backend/app/main.py` (module: `app.main:app`)
- Health endpoint: `GET /api/v1/health`

**Tile Server:**
- Entry point: `CLISApp-backend/data_pipeline/servers/tile_server.py` (module: `data_pipeline.servers.tile_server:app`)
- Health endpoint: `GET /health`

**Data Pipeline:**
- Orchestrator: `scripts/pipeline.py` - Calls `process_all_layers` once for all 5 layers
- Module: `data_pipeline.processing.openmeteo.process_all_layers` - Fetches data, generates GeoTIFFs and tiles
- Per-layer runners in `data_pipeline/pipeline_scripts/` are kept for standalone use

## Climate Data Sources & Paths

**Production climate sampling path:**

```
CLISApp-backend/data/processing/<layer>/<layer>_latest.tif
```

Layers: `pm25`, `precipitation`, `uv`, `humidity`, `temperature`.

**Data source:** Open-Meteo (raw values; no UV transform applied).

**Legacy path note:** `data_pipeline/data/processed/` is not used by the API for climate sampling.

## API Behavior Notes

- `GET /api/v1/regions/by-coordinates` returns `current_climate` when the latest rasters exist.
- `data_sources` includes `Open-Meteo` for climate fields.

## Open-Meteo Pipeline Flags

To generate GeoTIFFs without tiles:

```bash
SKIP_TILES=1 python -m data_pipeline.processing.openmeteo.process_all_layers
# or
python -m data_pipeline.processing.openmeteo.process_all_layers --geotiff-only
```

## Platform-Specific Connectivity

When connecting the mobile app to backend services during development:

### iOS Simulator
Use `localhost`:
- API: `http://localhost:8080`
- Tiles: `http://localhost:8000/tiles`

### Android Emulator
Use `10.0.2.2` (special Android emulator IP that maps to host machine's localhost):
- API: `http://10.0.2.2:8080`
- Tiles: `http://10.0.2.2:8000/tiles`

**Note**: `AndroidManifest.xml` must include `android:usesCleartextTraffic="true"` for HTTP connections to work on Android 9+.

### iOS Production HTTP Access
The iOS app allows HTTP access to the production API host via `Info.plist` so the simulator/device can reach `http://136.114.38.138:8080`.

## Verification Evidence

Mobile verification evidence (screenshots, test results) should be stored in:

```
_bmad-output/verification-evidence/<date>/mobile/ios/
_bmad-output/verification-evidence/<date>/mobile/android/
```

This convention ensures consistent tracking of manual mobile verification across development cycles.

## GCloud Deployment

The backend is deployed on Google Cloud Compute Engine:

- **Instance**: `clisapp-server` (zone: `us-central1-a`, machine: `e2-micro`)
- **Project path**: `/opt/clisapp/CLISAPP`
- **Venv**: `/opt/clisapp/venv`
- **Services**: `clisapp-api` + `clisapp-tiles` (systemd, user: ubuntu)

```bash
# SSH into server
gcloud compute ssh clisapp-server --zone=us-central1-a

# Update code and restart
gcloud compute ssh clisapp-server --zone=us-central1-a --command="cd /opt/clisapp/CLISAPP && sudo git pull origin main"
gcloud compute ssh clisapp-server --zone=us-central1-a --command="sudo systemctl restart clisapp-api clisapp-tiles"

# Run pipeline on server
gcloud compute ssh clisapp-server --zone=us-central1-a --command="cd /opt/clisapp/CLISAPP/CLISApp-backend && /opt/clisapp/venv/bin/python -m data_pipeline.processing.openmeteo.process_all_layers"

# Health checks
curl http://136.114.38.138:8080/api/v1/health
curl http://136.114.38.138:8000/health
```

Setup script: `gcp-setup.sh` (on server at `/home/ubuntu/gcp-setup.sh`).

## Next Steps

1. Run `make preflight` to ensure your environment is ready
2. Run `make up` to start all services
3. Run `make status` to verify everything is healthy
4. Check the [documentation index](docs/index.md) for detailed guides

## Quick Reference

| Command | Purpose |
|---------|---------|
| `make help` | List all available targets |
| `make preflight` | Validate dependencies and configuration |
| `make up` | Start API + tile server |
| `make down` | Stop all services |
| `make status` | Check service health |
| `make logs` | View/tail service logs |
| `make api-up` | Start API service only |
| `make api-down` | Stop API service only |
| `make tiles-up` | Start tile server only |
| `make tiles-down` | Stop tile server only |
| `make pipeline` | Run full data pipeline (all 5 layers) |
| `make update-data` | Fetch latest data only (no tile generation) |
| `make pipeline-pm25` | Run PM2.5 layer pipeline |
| `make pipeline-precip` | Run precipitation layer pipeline |
| `make pipeline-temp` | Run temperature layer pipeline |
| `make pipeline-humidity` | Run humidity layer pipeline |
| `make pipeline-uv` | Run UV layer pipeline |
| `make verify` | Run aggregated verification |
| `make verify-backend` | Verify backend health + sample tiles |
| `make verify-pipeline` | Pipeline smoke test with fixtures |
| `make verify-mobile` | Mobile regression checklist |
| `make check-boundaries` | Check architectural boundaries |
| `make android-release` | Build Android release APK |
