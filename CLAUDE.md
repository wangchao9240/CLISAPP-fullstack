# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CLISAPP is a full-stack climate data visualization system for Queensland, Australia, consisting of:
- **Backend**: FastAPI services (Python) serving climate tiles and region data
- **Frontend**: React Native mobile application (iOS & Android)
- **Data Pipeline**: Climate data processing and tile generation

## Development Commands

### Backend Services

```bash
# From repository root - use Makefile (recommended)
make help          # Show all available commands
make preflight     # Validate environment before starting
make up            # Start both API (8080) and Tile Server (8000)
make down          # Stop all services
make status        # Check service health
make logs          # View service logs

# Individual services
make api-up        # Start API service only (port 8080)
make tiles-up      # Start tile server only (port 8000)
```

**Important**: The Makefile is the canonical entry point. Backend-local scripts (`start.sh`, `start_all_services.py`) are deprecated.

### Data Pipeline

```bash
make pipeline          # Run full pipeline (all 5 layers, single run)
make pipeline-manual   # Run pipeline with explicit manual trigger type
make update-data       # Fetch latest data only (no tile generation)

# Per-layer
make pipeline-pm25     # Run PM2.5 layer only
make pipeline-precip   # Run precipitation layer only
make pipeline-temp     # Run temperature layer only
make pipeline-humidity # Run humidity layer only
make pipeline-uv       # Run UV layer only

# Per-stage (requires LAYER=<pm25|precipitation|uv|temperature|humidity>)
make pipeline-download LAYER=pm25   # Download stage only
make pipeline-process LAYER=pm25    # Process stage only
make pipeline-tiles LAYER=pm25      # Tile generation stage only

# Derived data
make pipeline-ssc       # Compute per-SSC climate averages from GeoTIFF rasters
make pipeline-baseline  # Process historical baseline CSV into frontend JSON asset
```

GeoTIFF-only mode (skip tile generation):
```bash
SKIP_TILES=1 python -m data_pipeline.processing.openmeteo.process_all_layers
# or
python -m data_pipeline.processing.openmeteo.process_all_layers --geotiff-only
```

### Frontend (React Native)

**Requires Node >= 20.**

```bash
cd CLISApp-frontend
npm start              # Start Metro bundler
npm run ios            # Launches on iPhone 16 Pro by default
npm run android        # Run on Android emulator
npm run lint           # Run ESLint
npm test               # Run Jest tests (preset: react-native)
```

Uses `patch-package` (runs automatically via `postinstall`) — check `patches/` for any patched dependencies after `npm install`.

### Backend Tests

```bash
# From repository root — runs root-level tests (tests/)
pytest                                  # Run all root tests
pytest tests/test_health_endpoints.py   # Run single test file
pytest -k "test_name"                   # Run specific test by name

# From backend directory — runs backend tests (CLISApp-backend/tests/)
cd CLISApp-backend && pytest
```

Both directories have their own `pytest.ini` with `testpaths = tests/`. The root `tests/` contains integration and pipeline tests; `CLISApp-backend/tests/` contains backend service unit tests. The backend `conftest.py` adds `CLISApp-backend/` to `sys.path` so tests can import `app.*` and `data_pipeline.*` directly.

### Verification & Quality

```bash
make verify            # Run aggregated verification (backend + pipeline + mobile)
make verify-backend    # Backend health + sample tiles
make verify-pipeline   # Pipeline smoke test with fixtures
make verify-mobile     # Mobile regression checklist
make check-boundaries  # Check architectural boundaries (app/ vs data_pipeline/)
```

### Android Release Builds

```bash
make android-keystore       # Generate release keystore (run once)
make android-release        # Build release APK
make android-release-clean  # Clean and build release APK
```

### Docker

```bash
cd CLISApp-backend
docker-compose up      # Start API (8080), Tile Server (8000), Redis (6379)
```

## Architecture

### Two-Service Backend Topology

Two **separate** FastAPI applications sharing configuration via `app/core/config.py`:

1. **API Service** (`app.main:app`, port 8080): Region search, climate data, telemetry, health checks
   - Routers: `app/api/v1/` — `health.py`, `regions.py`, `tiles.py`, `telemetry.py`
   - Business logic: `app/services/` — `region_service.py`, `tile_service.py`, `ssc_climate_service.py`

2. **Tile Server** (`data_pipeline.servers.tile_server:app`, port 8000): PNG tile delivery
   - Canonical URL: `/tiles/{layer}/{level}/{z}/{x}/{y}.png` (level = `suburb` or `lga`)
   - Legacy URL: `/tiles/{layer}/{z}/{x}/{y}.png` (deprecated, defaults to `suburb`)

Both use `uvicorn` and run as separate processes. Both must run from `CLISApp-backend/` working directory (the Makefile handles this).

### Phase System

The codebase follows a phased migration. Phase 0 was the prototype, Phase 1 is the current state. Several deprecated endpoints (legacy `/health`, legacy tile URLs without `{level}`) are marked for Phase 2 removal. When modifying API endpoints, check for deprecation comments before removing or changing behavior.

### Data Pipeline Flow

```
Open-Meteo API → Download → GeoTIFF processing → Tile generation (zoom 6-12)
                                                → SSC averages (per-region climate)
```

- **Source**: Open-Meteo API (free, no credentials)
- **Layers**: PM2.5, precipitation, temperature, humidity, UV
- **Coverage**: Queensland bounds (-10° to -29° lat, 138° to 154° lon)
- **Grid**: 50km resolution (~0.45°), configured in `data_pipeline/config/grid_config.py`
- **Canonical raster path**: `CLISApp-backend/data/processing/<layer>/<layer>_latest.tif`
- **Legacy path**: `data_pipeline/data/processed/` is NOT used by the API for climate sampling
- Higher zoom levels (10-12) are upsampled from zoom 9 base tiles
- **SSC averages**: Climate data aggregated per Statistical Subdivision Code (geographic region). Used by `ssc_climate_service.py` for the `/regions/by-coordinates` endpoint's `current_climate` field.
- **Processing modules**: `data_pipeline/processing/` organized by source — `openmeteo/` (main pipeline), `geo/` (SSC/baseline), plus legacy per-layer modules

When running pipeline modules directly, set `PYTHONPATH=CLISApp-backend`.

### Frontend Architecture

- **State Management**: Zustand stores with AsyncStorage persistence
  - `mapStore`: Region, active layer, selected region, UI state
  - `settingsStore`: API URLs, timeouts, map provider config
  - `favoritesStore`: Saved locations with coordinates

- **Map Abstraction**: `UniversalMap` wraps `OpenStreetMap` to allow future provider swaps (e.g., MapLibre). Both platforms use `react-native-maps`.

- **Platform-Aware Networking** (in `src/constants/apiEndpoints.ts`):
  - iOS Simulator: `localhost:8080` / `localhost:8000`
  - Android Emulator: `10.0.2.2:8080` / `10.0.2.2:8000`

- **Services**: `ApiService` (regions/climate), `telemetryService` (anonymous usage events per ADR-2/ADR-8), `notificationService` (Firebase push)

- **Custom Hooks**: `useApi`, `useBoundaryOverlays`, `useDynamicThreshold`

- **Navigation**: Stack navigator with two screens — `MapScreen` (main map view) and `FavoritesScreen` (saved locations)

- **UI Panels**: `HealthBottomSheet` (climate health indicator with per-layer readings), `LayerBar`/`LayerSelector` (climate layer switching), `RegionSearchBar`, `Legend`

## Critical Implementation Details

### Android UrlTile Layer Switching

**Problem**: Android's React Native Maps does not automatically refresh UrlTile when URL props change.

**Solution**: Force component remount by adding a `key` that includes the active layer:

```typescript
// OpenStreetMap.tsx
const climateTileKey = `${activeLayer}-${mapLevel}-${tileServerUrl}`;

<UrlTile
  key={climateTileKey}  // Critical for Android layer switching
  urlTemplate={tileUrlTemplate}
/>
```

Without this key, Android will show the same tiles regardless of layer selection.

### Store Persistence & Versioning

The `mapStore` uses versioned persistence to handle breaking changes:

```typescript
const MAP_STORE_VERSION = 3;  // Increment when storage schema changes
```

**Don't persist `activeLayer`** — it causes startup issues where users see unexpected layers. Always start with `DEFAULT_LAYER`.

### Environment Configuration

**Frontend** (`CLISApp-frontend/.env`):
```bash
GOOGLE_MAPS_API_KEY=...
# API_BASE_URL=...        # Don't set - breaks platform detection
# TILE_SERVER_URL=...     # Don't set - breaks platform detection
```

URL resolution priority in `src/constants/apiEndpoints.ts` (checked at runtime via `react-native-config`):
1. `PRODUCTION_API_URL` / `PRODUCTION_TILE_URL` — if set, wins unconditionally
2. `API_BASE_URL` / `TILE_SERVER_URL` — overrides platform defaults
3. Platform-aware defaults (localhost for iOS, 10.0.2.2 for Android)

For local development, keep `PRODUCTION_*`, `API_BASE_URL`, and `TILE_SERVER_URL` **all commented out** in `.env` so platform detection works. Uncomment `PRODUCTION_*` only when pointing the app at the remote server.

**Backend** (`CLISApp-backend/.env`): No credentials required — all data from Open-Meteo API.

### Android Cleartext Traffic

Android 9+ blocks HTTP by default. `AndroidManifest.xml` must include `android:usesCleartextTraffic="true"` for emulator connections to local backend.

### iOS Production HTTP Access

`Info.plist` allows HTTP access to the production API host (`136.114.38.138`) so simulator/device can reach the deployed backend.

### FastAPI Interactive Docs

Swagger UI (`/docs`) and ReDoc (`/redoc`) are only available when `DEBUG=true` (the default for local dev). They are disabled in production.

### Telemetry

The API service initializes a local SQLite database on startup for anonymous usage telemetry (`telemetry_service.py` / `init_db()`). Telemetry endpoints are under `/api/v1/telemetry`.

## Service Health Checks

```bash
curl http://localhost:8080/api/v1/health
# → {"status":"healthy","service":"CLISApp Backend","version":"1.0.0"}

curl http://localhost:8000/health
# → {"status":"healthy","service":"CLISApp Phase 0 Tile Server","tiles_available":true}

curl -I http://localhost:8000/tiles/pm25/6/59/37.png
# → 200 OK, Content-Type: image/png
```

## Common Issues

| Issue | Fix |
|-------|-----|
| "iOS 26.2 is not installed" | `xcodebuild -downloadPlatform iOS` |
| "cocoapods" gem missing | `gem install cocoapods && cd CLISApp-frontend/ios && pod install` |
| Android tiles not switching | Verify `key={climateTileKey}` on UrlTile in `OpenStreetMap.tsx` |
| Stale CocoaPods paths after repo move | `cd CLISApp-frontend/ios && rm -rf Pods Podfile.lock && pod install` |
| Tile requests all show `pm25` | UrlTile key is missing or broken |

## Deployment

### GCloud Production Server

- **Instance**: `clisapp-server` (zone: `us-central1-a`, machine: `e2-micro`)
- **External IP**: `136.114.38.138`
- **Project path**: `/opt/clisapp/CLISAPP`
- **Venv**: `/opt/clisapp/venv`
- **Services**: `clisapp-api` + `clisapp-tiles` (systemd)

```bash
# SSH
gcloud compute ssh clisapp-server --zone=us-central1-a

# Deploy: pull and restart
gcloud compute ssh clisapp-server --zone=us-central1-a --command="cd /opt/clisapp/CLISAPP && sudo git pull origin main"
gcloud compute ssh clisapp-server --zone=us-central1-a --command="sudo systemctl restart clisapp-api clisapp-tiles"

# Run pipeline on server
gcloud compute ssh clisapp-server --zone=us-central1-a --command="cd /opt/clisapp/CLISAPP/CLISApp-backend && /opt/clisapp/venv/bin/python -m data_pipeline.processing.openmeteo.process_all_layers"
```

This is a development/prototype system. See `docs/deployment-guide.md` for production considerations.

## Documentation

- `docs/index.md` — Documentation starting point
- `docs/architecture-backend.md` / `docs/architecture-frontend.md` — Architecture details
- `docs/api-contracts-backend.md` — API endpoint contracts
- `docs/development-guide-backend.md` / `docs/development-guide-frontend.md` — Setup guides
- `docs/integration-architecture.md` — How frontend and backend connect
- `docs/state-management-frontend.md` — Zustand store patterns

Mobile verification evidence (screenshots, test results) goes in:
```
_bmad-output/verification-evidence/<date>/mobile/ios/
_bmad-output/verification-evidence/<date>/mobile/android/
```
