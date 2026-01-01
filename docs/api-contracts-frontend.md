# API Contracts (Frontend Consumption)

This document describes how the mobile app calls backend services.

## Environment-Aware Base URLs

Defined in `CLISApp-frontend/src/constants/apiEndpoints.ts`.

### Development

- **API base URL**
  - iOS simulator: `http://localhost:8080`
  - Android emulator: `http://10.0.2.2:8080`

- **Tile server base URL**
  - iOS simulator: `http://localhost:8000/tiles`
  - Android emulator: `http://10.0.2.2:8000/tiles`

### Production

- API base: `API_BASE_URL` (e.g., `https://clisapp-api.qut.edu.au`)
- Tile base: `TILE_SERVER_URL` (e.g., `https://clisapp-tiles.qut.edu.au/tiles`)
  - The mobile app should point to the dedicated tile service for images.
  - Using the API `/api/v1/tiles/*` as a tile image base is deprecated (Phase 2 removal).

## API Calls Implemented

Implemented in `CLISApp-frontend/src/services/ApiService.ts`.

### Health

- `checkHealth()` → `GET {BASE_URL}/api/v1/health`

### Regions

- `searchRegions(q, type?, limit?)` → `GET {BASE_URL}/api/v1/regions/search?q=...&type=...&limit=...`
- `getRegionInfo(regionId, includeClimateData?)` → `GET {BASE_URL}/api/v1/regions/{regionId}?include_climate_data=...`
- `getRegionByCoordinates(lat, lng, includeClimateData?)` → `GET {BASE_URL}/api/v1/regions/by-coordinates?...`
- `getNearbyRegions(lat, lng, level?, radiusKm?)` → `GET {BASE_URL}/api/v1/regions/nearby?...`
- `getRegionClimateData(regionId, layers?)` → `GET {BASE_URL}/api/v1/regions/{regionId}/climate?layers=...`
- `getRegionBoundary(regionId)` → `GET {BASE_URL}/api/v1/regions/{regionId}/boundary`

### Tiles (Phase 1 - Aligned)

- `getTileStatus()` → `GET {BASE_URL}/api/v1/tiles/status`
- `getLayerMetadata(layer, level)` → `GET {BASE_URL}/api/v1/tiles/{layer}/{level}/metadata`

### Tile URL generation for map overlay

- `getTileUrl(layer, level, z, x, y, format?)` → `{TILE_SERVER_URL}/{layer}/{level}/{z}/{x}/{y}.{format}`
  - In development, `TILE_SERVER_URL` defaults to `http://localhost:8000/tiles`
  - The tile server (port 8000) supports both canonical and legacy formats:
    - **Canonical** (Phase 1): `/tiles/{layer}/{level}/{z}/{x}/{y}.png`
    - **Legacy** (Phase 0): `/tiles/{layer}/{z}/{x}/{y}.png` (deprecated)

## Phase 1 Compatibility Notes

- **Health endpoints**: Backend provides both `/health` (legacy, deprecated) and `/api/v1/health` (canonical). Frontend uses the canonical `/api/v1/health`.
- **Tile URLs**: The mobile app uses `TILE_SERVER_URL` for tile images in all environments.
- **Tile metadata**: Uses canonical API routes (`/api/v1/tiles/*`) for consistency.

All Phase 0 legacy endpoints are deprecated and will be removed in Phase 2.
