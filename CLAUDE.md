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
make api-down      # Stop API service
make tiles-up      # Start tile server only (port 8000)
make tiles-down    # Stop tile server

# Data pipeline
make pipeline      # Run full pipeline (all 5 layers, single run)
make update-data   # Fetch latest data only (no tile generation)
make pipeline-pm25 # Run PM2.5 layer only
make pipeline-precip # Run precipitation layer only
make pipeline-temp # Run temperature layer only
make pipeline-humidity # Run humidity layer only
make pipeline-uv   # Run UV layer only

# Verification
make verify        # Run aggregated verification
make verify-backend # Backend health + sample tiles
make verify-pipeline # Pipeline smoke test
make verify-mobile # Mobile regression checklist
```

**Important**: The Makefile is the canonical entry point. Backend-local scripts (`start.sh`, `start_all_services.py`) are deprecated and will be removed.

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

**Platform-specific networking**:
- iOS Simulator: Uses `localhost:8080` (API) and `localhost:8000` (tiles)
- Android Emulator: Uses `10.0.2.2:8080` and `10.0.2.2:8000`
- This is handled automatically by `src/constants/apiEndpoints.ts`

## Architecture

### Backend Structure

```
CLISApp-backend/
├── app/
│   ├── api/v1/              # FastAPI routers (endpoints)
│   ├── core/                # Configuration & logging
│   ├── models/              # Pydantic schemas
│   ├── services/            # Business logic (tiles, regions)
│   └── main.py              # API application entry
├── data_pipeline/
│   ├── servers/             # Tile server (separate FastAPI app)
│   └── pipeline_scripts/    # Data processing scripts
├── data/                    # Generated tiles and downloads
└── logs/                    # Service logs
```

**Two separate FastAPI applications**:
1. **API Service** (`app.main:app`, port 8080): Region search, health checks
2. **Tile Server** (`data_pipeline.servers.tile_server:app`, port 8000): PNG tile delivery

Both use `uvicorn` and run as separate processes. They share configuration via `app/core/config.py`.

### Frontend Structure

```
CLISApp-frontend/src/
├── components/
│   ├── Map/
│   │   ├── UniversalMap.tsx        # Abstraction layer for map providers
│   │   └── OpenStreetMap.tsx       # React Native Maps implementation
│   ├── UI/                         # LayerSelector, Legend, SearchBar
│   └── panels/                     # RegionInfoPanel
├── screens/
│   └── MapScreen.tsx               # Main screen
├── store/
│   ├── mapStore.ts                 # Zustand state (region, layer, UI)
│   └── settingsStore.ts            # App settings & config
├── services/
│   └── MapProvider.ts              # Map abstraction interface
├── constants/
│   ├── apiEndpoints.ts             # Platform-aware API URLs
│   ├── mapConfig.ts                # Default regions & zoom
│   └── climateData.ts              # Layer definitions
└── types/                          # TypeScript types
```

**Key architectural decisions**:

1. **Map Abstraction**: `UniversalMap` wraps `OpenStreetMap` to allow future provider swaps (e.g., MapLibre). Currently, both iOS and Android use `react-native-maps`.

2. **State Management**: Zustand stores with AsyncStorage persistence
   - `mapStore`: Region, active layer, selected region, UI state
   - `settingsStore`: API URLs, timeouts, map provider config

3. **Platform Differences**: Handled via `Platform.OS` checks:
   - Network URLs (localhost vs 10.0.2.2)
   - React Native Maps behaves differently on Android vs iOS for UrlTile updates

## Critical Implementation Details

### Android UrlTile Layer Switching

**Problem**: Android's React Native Maps does not automatically refresh UrlTile when URL props change.

**Solution**: Force component remount by adding a `key` that includes the active layer:

```typescript
// OpenStreetMap.tsx
const climateTileKey = `${activeLayer}-${mapLevel}-${tileServerUrl}`;

<UrlTile
  key={climateTileKey}  // ⚡ Critical for Android layer switching
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
    // Clear old activeLayer persistence to fix startup issues
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
# API_BASE_URL=...        # ❌ Don't set - breaks platform detection
# TILE_SERVER_URL=...     # ❌ Don't set - breaks platform detection
```

If `API_BASE_URL` or `TILE_SERVER_URL` are set in `.env`, they override the platform-aware logic in `apiEndpoints.ts`. Keep them commented out for development.

Backend uses `.env` in `CLISApp-backend/`:

```bash
# No credentials required - all data from Open-Meteo API (free, no auth)

# Paths (defaults usually work)
DATA_DIR=data
TILES_DIR=tiles
```

## Testing Strategy

### Manual Testing with Simulators

Use `ios-simulator-skill` for automated iOS testing:

```bash
cd ~/.claude/skills/ios-simulator-skill

# Take screenshot
python scripts/screenshot.py --output ~/test.png

# Map screen elements
python scripts/screen_mapper.py

# Find and tap elements
python scripts/navigator.py --find-text "Search" --tap

# Enter text in search
python scripts/navigator.py --find-type TextField --enter-text "Sunnybank"
```

For Android, use `adb`:

```bash
# Screenshot
adb exec-out screencap -p > ~/test.png

# UI hierarchy
adb shell uiautomator dump
adb pull /sdcard/window_dump.xml

# Tap coordinates
adb shell input tap x y

# Enter text
adb shell input text "Sunnybank"

# View logs
adb logcat ReactNativeJS:V *:S
```

### Verifying Tile Rendering

Check backend logs to confirm tiles are requested:

```bash
tail -f CLISApp-backend/logs/tiles/tiles-*.log

# Expected when switching layers:
# GET /tiles/pm25/6/59/37.png 200
# GET /tiles/uv/6/59/37.png 200
# GET /tiles/precipitation/6/59/37.png 200
```

If all requests show `pm25` regardless of layer selection, the UrlTile key is missing or broken.

### Android Cleartext Traffic

Android 9+ blocks HTTP by default. `AndroidManifest.xml` must include `android:usesCleartextTraffic="true"` on the `<application>` tag for the emulator to connect to local backend services over HTTP.

### Tile Zoom Levels

Default tile generation zoom levels are 6-11 (configured in `data_pipeline/processing/common/generate_tiles.py`). Higher zoom levels are upsampled from zoom 9 base tiles.

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

## Deployment

### GCloud Production Server

- **Instance**: `clisapp-server` (zone: `us-central1-a`, machine: `e2-micro`)
- **External IP**: `136.114.38.138`
- **Project path**: `/opt/clisapp/CLISAPP`
- **Venv**: `/opt/clisapp/venv`
- **Services**: `clisapp-api` + `clisapp-tiles` (systemd)
- **Setup script**: `/home/ubuntu/gcp-setup.sh`

### Deployment Notes

This is a development/prototype system. Before production:
1. Replace mock region data with real Queensland LGA/suburb data
2. Implement proper authentication/authorization
3. Add rate limiting and caching
4. Configure CORS policies
5. Use production-grade tile storage (CDN)
6. Add monitoring and error tracking
