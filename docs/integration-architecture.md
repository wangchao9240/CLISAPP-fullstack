# Integration Architecture

## Overview

CLISApp is an integrated mobile + backend system with a two-service topology:

- **Mobile app (React Native)** renders map UI.
- **Backend API (FastAPI, port 8080)** provides region search/info, tile metadata/status, and health endpoints.
- **Tile server (FastAPI, port 8000, Phase 1)** serves raster tile PNGs for climate layers with level-aware routing.
- **Base map tiles** come from OpenStreetMap providers (public tile servers).

### Canonical Topology (Phase 1)

**Development:**
- API service on `:8080` for JSON endpoints (`/api/v1/*`)
- Tile server on `:8000` for tile images (`/tiles/*`) and tile-server health (`/health`)

**Production (Render):**
- `clisapp-api` service provides `/api/v1/*` endpoints
- `clisapp-tiles` service provides `/tiles/*` tile images (canonical Phase 1 shape)

**Deprecated:** Static tile mount on `:8080/tiles/*` (disabled by default in Phase 1, removed in Phase 2)

## Data Flow

1) User opens map screen (`MapScreen.tsx`).
2) App displays base map (OSM) and requests climate tiles as an overlay.
3) App calls backend to:
   - check connectivity/health
   - search regions / fetch region details
   - fetch region boundary geometry for overlays
   - fetch tile metadata/status (depending on the current mode)

## Integration Points

### Frontend → Backend API

- Base URL is derived by platform:
  - iOS simulator: `http://localhost:8080`
  - Android emulator: `http://10.0.2.2:8080`

Calls include region endpoints under `/api/v1/regions/*`.

### Frontend → Tile Server

- Base URL is derived by platform:
  - iOS simulator: `http://localhost:8000/tiles`
  - Android emulator: `http://10.0.2.2:8000/tiles`

Tiles are requested as `{tile_base}/{layer}/{level}/{z}/{x}/{y}.png` using the canonical Phase 1 format.

### Frontend → OpenStreetMap

- Base tiles use public OSM tile servers (CartoDB light/dark, standard OSM, etc.).

## Phase 1 Contract Alignment

All tile contracts have been aligned in Phase 1:

### Canonical Tile URL Format

**`/tiles/{layer}/{level}/{z}/{x}/{y}.png`**

- `layer`: Climate layer (`pm25`, `precipitation`, `uv`, `humidity`, `temperature`)
- `level`: Aggregation level (`lga` or `suburb`)
- `z`, `x`, `y`: Tile coordinates

### Supported by All Services

- ✅ **Tile Server** (port 8000): `/tiles/{layer}/{level}/{z}/{x}/{y}.png`
- ✅ **Main API** (port 8080): `/api/v1/tiles/*` metadata/status/on-demand generation (not the mobile tile base)
- ✅ **Frontend**: Generates level-aware URLs for all tile requests

### Tile Metadata Endpoints

- Frontend uses canonical API routes:
  - `GET /api/v1/tiles/status` - Overall tile status
  - `GET /api/v1/tiles/{layer}/{level}/metadata` - Layer-specific metadata

### Backward Compatibility

Phase 0 legacy endpoints are preserved for transition but deprecated:
- `/tiles/{layer}/{z}/{x}/{y}.png` (tile server, no level)
- All legacy endpoints log deprecation warnings
- **Planned removal**: Phase 2
