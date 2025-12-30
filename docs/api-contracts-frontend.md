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

- API base: `https://clisapp-api.qut.edu.au`
- Tile base: `https://clisapp-api.qut.edu.au/api/v1/tiles`

## API Calls Implemented

Implemented in `CLISApp-frontend/src/services/ApiService.ts`.

### Health

- `checkHealth()` → `GET {BASE_URL}/health`

### Regions

- `searchRegions(q, type?, limit?)` → `GET {BASE_URL}/api/v1/regions/search?q=...&type=...&limit=...`
- `getRegionInfo(regionId, includeClimateData?)` → `GET {BASE_URL}/api/v1/regions/{regionId}?include_climate_data=...`
- `getRegionByCoordinates(lat, lng, includeClimateData?)` → `GET {BASE_URL}/api/v1/regions/by-coordinates?...`
- `getNearbyRegions(lat, lng, level?, radiusKm?)` → `GET {BASE_URL}/api/v1/regions/nearby?...`
- `getRegionClimateData(regionId, layers?)` → `GET {BASE_URL}/api/v1/regions/{regionId}/climate?layers=...`
- `getRegionBoundary(regionId)` → `GET {BASE_URL}/api/v1/regions/{regionId}/boundary`

### Tiles

- `getTileStatus()` → `GET {BASE_URL}/tiles/pm25/info`
- `getLayerMetadata(layer, level)` → `GET {BASE_URL}/tiles/{layer}/{level}/metadata`

### Tile URL generation for map overlay

- `getTileUrl(layer, level, z, x, y, format?)` → `{TILE_SERVER_URL}/{layer}/{level}/{z}/{x}/{y}.{format}`
  - In development, `TILE_SERVER_URL` defaults to `http://localhost:8000/tiles` (no `/api/v1`).

## Notes / Potential Mismatches

- Backend main API mounts health under `/api/v1/health`, but frontend health is configured as `/health`.
- Backend phase-0 tile server uses `/tiles/{layer}/{z}/{x}/{y}.png` (no `level`), while frontend generates `/tiles/{layer}/{level}/{z}/{x}/{y}.{format}`.

These differences should be validated and aligned to avoid dev/prod inconsistencies.
