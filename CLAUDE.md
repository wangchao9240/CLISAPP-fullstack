# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CLISAPP is a full-stack climate data visualization system for Queensland, Australia, consisting of:
- **Backend**: FastAPI services (Python) serving climate tiles and region data
- **Frontend**: React Native mobile application (iOS & Android)
- **Data Pipeline**: Climate data processing and tile generation
- **Infrastructure**: Docker Compose orchestration with Redis caching

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
make api-down      # Stop API service
make tiles-up      # Start tile server only (port 8000)
make tiles-down    # Stop tile server

# Data pipeline
make pipeline      # Run full pipeline (all 5 layers, single run)
make pipeline-manual # Run pipeline with explicit manual trigger type
make pipeline-ssc  # Compute per-SSC climate averages from latest GeoTIFFs
make update-data   # Fetch latest data only (no tile generation)
make pipeline-pm25 # Run PM2.5 layer only
make pipeline-precip # Run precipitation layer only
make pipeline-temp # Run temperature layer only
make pipeline-humidity # Run humidity layer only
make pipeline-uv   # Run UV layer only

# Stage-specific pipeline (requires LAYER=<layer>)
make pipeline-download LAYER=pm25   # Download stage only
make pipeline-process LAYER=pm25    # Process stage only
make pipeline-tiles LAYER=pm25      # Tile generation stage only

# Verification
make verify            # Run aggregated verification
make verify-backend    # Backend health + sample tiles
make verify-pipeline   # Pipeline smoke test
make verify-mobile     # Mobile regression checklist
make check-boundaries  # Check app/ vs data_pipeline/ separation

# Mobile builds
make android-keystore       # Generate Android release keystore (once)
make android-release        # Build Android release APK
make android-release-clean  # Clean and build Android release APK
```

**Important**: The Makefile is the canonical entry point. Backend-local scripts (`start.sh`, `start_all_services.py`) are deprecated and will be removed.

### Backend Testing

```bash
cd CLISApp-backend
python -m pytest                   # Run all backend tests
python -m pytest tests/test_health_endpoints.py  # Run specific test file
```

Backend tests are in `CLISApp-backend/tests/` and cover: health endpoints, region search, tile server routes, tile generation, SSC climate service, Redis caching, pipeline logger, boundary processing, and topology verification.

### Frontend (React Native)

```bash
cd CLISApp-frontend

# Start Metro bundler
npm start

# Run on iOS (requires Xcode and iOS Simulator)
npm run ios        # Launches on iPhone 16 Pro by default

# Run on Android (requires Android Studio and emulator)
npm run android

# Development
npm run lint       # Run ESLint
npm test          # Run Jest tests
```

Frontend tests are in `src/**/__tests__/` directories using Jest. Key test files cover: RegionSearchBar, FavoriteLocationCard, UniversalMap, OpenStreetMap, climateData constants, and FavoritesScreen.

**Platform-specific networking**:
- iOS Simulator: Uses `localhost:8080` (API) and `localhost:8000` (tiles)
- Android Emulator: Uses `10.0.2.2:8080` and `10.0.2.2:8000`
- This is handled automatically by `src/constants/apiEndpoints.ts`

### Docker

```bash
cd CLISApp-backend
docker compose up -d       # Start all services (API, tile server, Redis)
docker compose down        # Stop all services
docker compose logs -f     # Follow logs
```

Three services: `backend` (API, port 8080), `tile-server` (port 8000), `redis` (port 6379).

## Architecture

### Backend Structure

```
CLISApp-backend/
├── app/
│   ├── api/v1/                    # FastAPI routers
│   │   ├── health.py              # Health check endpoint
│   │   ├── regions.py             # Region search & lookup
│   │   ├── tiles.py               # Tile metadata/status
│   │   └── telemetry.py           # Analytics endpoint
│   ├── core/
│   │   └── config.py              # Configuration & settings
│   ├── models/                    # Pydantic schemas
│   │   ├── climate.py
│   │   ├── region.py
│   │   └── telemetry.py
│   ├── services/                  # Business logic
│   │   ├── climate_data_service.py    # Climate data sampling
│   │   ├── ssc_climate_service.py     # SSC-level climate averaging
│   │   ├── region_service.py          # Region search logic
│   │   ├── region_data_loader.py      # Region boundary data
│   │   ├── tile_service.py            # Tile metadata
│   │   ├── telemetry_service.py       # Analytics storage
│   │   └── notification_service.py    # Firebase notifications
│   ├── tasks/                     # Background tasks
│   └── utils/
├── data_pipeline/
│   ├── config/
│   │   └── grid_config.py         # Grid/tile configuration
│   ├── downloads/
│   │   └── openmeteo/
│   │       └── fetch_realtime.py  # Open-Meteo data fetcher
│   ├── processing/
│   │   ├── openmeteo/
│   │   │   └── process_all_layers.py  # Unified layer processor
│   │   ├── common/
│   │   │   ├── generate_tiles.py      # Tile generation (zoom 6-12)
│   │   │   └── upsample_zoom11_to_12.py
│   │   ├── geo/
│   │   │   ├── process_boundaries.py  # SSC boundary shapefile processing
│   │   │   └── compute_ssc_averages.py # Per-SSC climate averaging
│   │   └── {pm25,gpm,temp,humidity,uv}/ # Per-layer processors
│   ├── pipeline_scripts/          # Per-layer pipeline runners
│   ├── servers/
│   │   └── tile_server.py         # Tile delivery server (port 8000)
│   └── utils/
│       └── redis_cache.py         # Redis caching layer
├── data/                          # Generated tiles and downloads
├── shared/                        # Shared utilities
├── tests/                         # Backend tests (pytest)
├── Dockerfile                     # Production container (Python 3.11-slim)
├── docker-compose.yml             # Multi-service orchestration
└── requirements.txt               # Python dependencies
```

**Two separate FastAPI applications**:
1. **API Service** (`app.main:app`, port 8080): Region search, health checks, telemetry, SSC climate data
2. **Tile Server** (`data_pipeline.servers.tile_server:app`, port 8000): PNG tile delivery

Both use `uvicorn` and run as separate processes. They share configuration via `app/core/config.py`.

### Frontend Structure

```
CLISApp-frontend/src/
├── screens/
│   ├── MapScreen.tsx               # Main climate map interface
│   └── FavoritesScreen.tsx         # Saved favorite locations
├── components/
│   ├── Map/
│   │   ├── UniversalMap.tsx        # Abstraction layer for map providers
│   │   └── OpenStreetMap.tsx       # React Native Maps implementation
│   ├── UI/
│   │   ├── LayerSelector.tsx       # Climate layer picker
│   │   ├── LayerBar.tsx            # Layer controls bar
│   │   ├── Legend.tsx              # Color scale legend
│   │   ├── RegionSearchBar.tsx     # SSC region search
│   │   └── FavoriteLocationCard.tsx # Favorite location display
│   └── panels/
│       └── HealthBottomSheet.tsx   # Climate data display modal
├── store/                          # Zustand state management
│   ├── mapStore.ts                 # Map state: region, layer, UI
│   ├── settingsStore.ts            # App config & API URLs
│   └── favoritesStore.ts          # Favorite locations persistence
├── services/
│   ├── ApiService.ts               # HTTP client wrapper
│   ├── MapProvider.ts              # Map abstraction interface
│   ├── telemetryService.ts         # Analytics sending
│   ├── notificationService.ts      # Push notification handling
│   └── boundaries/
│       ├── BoundaryStore.ts        # Boundary feature caching
│       ├── boundaryLoader.ts       # Boundary file loading
│       └── sscManifest.ts          # SSC metadata
├── hooks/
│   ├── useApi.ts                   # API calls hook
│   ├── useBoundaryOverlays.ts      # Boundary rendering
│   └── useDynamicThreshold.ts      # Climate threshold logic
├── constants/
│   ├── apiEndpoints.ts             # Platform-aware URLs
│   ├── climateData.ts              # Layer definitions & metadata
│   ├── mapConfig.ts                # Default map settings
│   ├── theme.ts                    # Design tokens
│   └── boundaryStyles.ts           # Boundary styling
├── navigation/
│   └── AppNavigator.tsx            # Stack & tab navigation
├── types/                          # TypeScript definitions
├── assets/                         # Images and static assets
└── scripts/
    ├── generate-keystore.sh        # Android keystore generation
    └── build-android-release.sh    # Release APK building
```

### Root-Level Scripts

The `scripts/` directory at the repo root contains Python helpers invoked by the Makefile:
- Service management: `api_service.py`, `tiles_service.py`, `status.py`, `logs.py`
- Pipeline: `pipeline.py`, `update_data.py`, `pipeline_stage.py`, `run_pipeline_layer.py`
- Verification: `verify.py`, `verify_backend.py`, `verify_pipeline.py`, `verify_mobile.py`
- Validation: `preflight.py`, `check_boundaries.py`

### Key Architectural Decisions

1. **Map Abstraction**: `UniversalMap` wraps `OpenStreetMap` to allow future provider swaps (e.g., MapLibre). Currently, both iOS and Android use `react-native-maps`.

2. **State Management**: Zustand stores with AsyncStorage persistence
   - `mapStore`: Region, active layer, selected region, UI state
   - `settingsStore`: API URLs, timeouts, map provider config
   - `favoritesStore`: Favorite locations with coordinates

3. **Platform Differences**: Handled via `Platform.OS` checks:
   - Network URLs (localhost vs 10.0.2.2)
   - React Native Maps behaves differently on Android vs iOS for UrlTile updates

4. **SSC Boundaries**: Statistical Small Areas (SSC) from ABS shapefiles provide region boundaries for Queensland. The pipeline processes these into GeoJSON for map overlays and per-region climate averaging.

5. **Redis Caching**: Optional Redis layer (`data_pipeline/utils/redis_cache.py`) for caching computed results. Used in Docker setup; local development works without it.

6. **Navigation**: React Navigation with stack and tab navigators (`AppNavigator.tsx`). Bottom tab navigation with Map and Favorites screens.

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
  // ...
/>
```

Without this key, Android will show the same tiles regardless of layer selection. iOS works without it, but the key doesn't harm iOS behavior.

### Store Persistence & Versioning

The `mapStore` uses versioned persistence to handle breaking changes:

```typescript
const MAP_STORE_VERSION = 2;  // Increment when storage schema changes

// Migration logic in persist middleware
version: MAP_STORE_VERSION,
migrate: (persistedState: any, version: number) => {
  if (version < 2) {
    delete persistedState.activeLayer;
  }
  return persistedState;
}
```

**Don't persist `activeLayer`** - it causes startup issues where users see unexpected layers. Always start with `DEFAULT_LAYER`.

### Environment Configuration

Frontend uses `react-native-config` to load `.env` files:

```bash
# CLISApp-frontend/.env
GOOGLE_MAPS_API_KEY=...
# API_BASE_URL=...        # Don't set - breaks platform detection
# TILE_SERVER_URL=...     # Don't set - breaks platform detection
```

If `API_BASE_URL` or `TILE_SERVER_URL` are set in `.env`, they override the platform-aware logic in `apiEndpoints.ts`. Keep them commented out for development.

Backend uses `.env` in `CLISApp-backend/`:

```bash
# No credentials required - all data from Open-Meteo API (free, no auth)
# Paths (defaults usually work)
DATA_DIR=data
TILES_DIR=tiles
```

### Tile Zoom Levels

Tile generation covers zoom levels 6-12 (configured in `data_pipeline/processing/common/generate_tiles.py` and `docker-compose.yml`). Base tiles are generated at zoom 6-9; higher levels (10-12) are upsampled.

## Conventions

### Commit Messages

This project uses conventional commit prefixes:
- `feat:` - New feature
- `fix:` - Bug fix
- `refactor:` - Code restructuring without behavior change
- `test:` - Adding or updating tests
- `docs:` - Documentation changes

### Code Organization

- **Backend boundary**: `app/` (API layer) and `data_pipeline/` (processing layer) are architecturally separated. Use `make check-boundaries` to verify no cross-boundary imports exist.
- **Frontend colocation**: Tests live in `__tests__/` directories adjacent to the code they test.
- **Patch-package**: Frontend uses `patch-package` via `postinstall` for dependency patches.

### Key Dependencies

**Backend** (Python): FastAPI, uvicorn, xarray, rasterio, geopandas, numpy, scipy, Pillow, redis

**Frontend** (TypeScript): React Native 0.73.9, react-native-maps 1.10.3, zustand 4.5.7, @react-navigation/native, @gorhom/bottom-sheet, @react-native-firebase/app, react-native-config, @turf/*

## Testing Strategy

### Backend Tests (pytest)

```bash
cd CLISApp-backend
python -m pytest                    # All tests
python -m pytest tests/test_health_endpoints.py -v  # Specific file
```

Key test files:
- `test_health_endpoints.py` - API health checks
- `test_region_search_ssc.py` - SSC region search
- `test_ssc_climate_service.py` - Per-SSC climate averaging
- `test_tile_server_routes.py` - Tile server endpoints
- `test_generate_tiles_buffer.py` - Tile generation logic
- `test_redis_cache.py` - Redis caching layer
- `test_process_boundaries.py` - Boundary processing
- `test_topology_verification.py` - Topology checks

### Frontend Tests (Jest)

```bash
cd CLISApp-frontend
npm test                           # All tests
npm test -- RegionSearchBar        # Specific test
```

### Manual Testing with Simulators

Use `ios-simulator-skill` for automated iOS testing:

```bash
cd ~/.claude/skills/ios-simulator-skill
python scripts/screenshot.py --output ~/test.png
python scripts/screen_mapper.py
python scripts/navigator.py --find-text "Search" --tap
python scripts/navigator.py --find-type TextField --enter-text "Sunnybank"
```

For Android, use `adb`:

```bash
adb exec-out screencap -p > ~/test.png
adb shell uiautomator dump && adb pull /sdcard/window_dump.xml
adb shell input tap x y
adb shell input text "Sunnybank"
adb logcat ReactNativeJS:V *:S
```

### Verifying Tile Rendering

Check backend logs to confirm tiles are requested:

```bash
tail -f CLISApp-backend/logs/tiles/tiles-*.log

# Expected when switching layers:
# GET /tiles/pm25/6/59/37.png 200
# GET /tiles/uv/6/59/37.png 200
```

If all requests show `pm25` regardless of layer selection, the UrlTile key is missing or broken.

### Android Cleartext Traffic

Android 9+ blocks HTTP by default. `AndroidManifest.xml` must include `android:usesCleartextTraffic="true"` on the `<application>` tag for the emulator to connect to local backend services over HTTP.

## Common Issues

### "iOS 26.2 is not installed"
Run `xcodebuild -downloadPlatform iOS` to install the required platform runtime.

### "cocoapods" gem missing
Install: `gem install cocoapods`, then run `pod install` in `CLISApp-frontend/ios/`.

### Android tiles not switching
Verify `OpenStreetMap.tsx` has `key={climateTileKey}` on the UrlTile component.

### "no matches found" in Makefile commands
The Makefile uses simple Python scripts in `scripts/` - ensure Python 3 is installed.

### Stale CocoaPods paths
If you moved the repo, regenerate Pods:
```bash
cd CLISApp-frontend/ios
rm -rf Pods Podfile.lock
pod install
```

## Service Health Checks

```bash
# API health
curl http://localhost:8080/api/v1/health

# Tile server health
curl http://localhost:8000/health

# Test tile delivery
curl -I http://localhost:8000/tiles/pm25/6/59/37.png
```

Expected responses:
- API: `{"status":"healthy","service":"CLISApp Backend","version":"1.0.0"}`
- Tiles: `{"status":"healthy","service":"CLISApp Phase 0 Tile Server","tiles_available":true}`
- Tile PNG: `200 OK` with `Content-Type: image/png`

## Documentation

The `docs/` directory contains comprehensive project documentation:
- **Guides**: `development-guide-backend.md`, `development-guide-frontend.md`, `deployment-guide.md`, `contribution-guide.md`
- **Architecture**: `architecture-backend.md`, `architecture-frontend.md`, `architecture-patterns.md`, `integration-architecture.md`
- **API & Data**: `api-contracts-backend.md`, `api-contracts-frontend.md`, `data-models-backend.md`, `data-models-frontend.md`
- **Frontend**: `component-inventory-frontend.md`, `state-management-frontend.md`, `asset-inventory-frontend.md`

## Deployment

### GCloud Production Server

- **Instance**: `clisapp-server` (zone: `us-central1-a`, machine: `e2-micro`)
- **External IP**: `136.114.38.138`
- **Project path**: `/opt/clisapp/CLISAPP`
- **Venv**: `/opt/clisapp/venv`
- **Services**: `clisapp-api` + `clisapp-tiles` (systemd)
- **Setup script**: `/home/ubuntu/gcp-setup.sh`

### Docker Deployment

```bash
cd CLISApp-backend
docker compose up -d    # Starts API (8080), tile server (8000), Redis (6379)
```

The Dockerfile uses Python 3.11-slim with system dependencies for GDAL, GEOS, PROJ, and spatialindex.

### Deployment Notes

This is a development/prototype system. Before production:
1. Replace mock region data with real Queensland LGA/suburb data
2. Implement proper authentication/authorization
3. Add rate limiting and caching
4. Configure CORS policies
5. Use production-grade tile storage (CDN)
6. Add monitoring and error tracking
