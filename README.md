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

**Status: Planned / WIP** - Run verification/health checks. See `make help` and `_bmad-output/implementation-artifacts/sprint-status.yaml` for current implementation status.

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
- Pipeline scripts: `CLISApp-backend/data_pipeline/pipeline_scripts/` - One-click scripts per layer

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

## Verification Evidence

Mobile verification evidence (screenshots, test results) should be stored in:

```
_bmad-output/verification-evidence/<date>/mobile/ios/
_bmad-output/verification-evidence/<date>/mobile/android/
```

This convention ensures consistent tracking of manual mobile verification across development cycles.

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
| `make pipeline` | Run data pipeline (WIP) |
| `make verify` | Run verification checks (planned) |
