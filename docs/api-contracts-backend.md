# API Contracts (Backend)

## Services

CLISApp backend exposes **two HTTP services** in local development:

1) **Main API (FastAPI)**
- Default: `http://localhost:8080`
- Routers are mounted under: `/api/v1`
- Swagger UI (debug): `/docs`

2) **Tile Server (FastAPI, Phase 0 prototype)**
- Default: `http://localhost:8000`
- Tile routes under: `/tiles/*`
- Swagger UI: `/docs`

> Note: There are **two different tile serving implementations**:
> - Main API provides `/api/v1/tiles/{layer}/{level}/...` (includes `level` = `lga|suburb`).
> - Tile server provides `/tiles/{layer}/{z}/{x}/{y}.png` (no `level`).

---

## Main API (Port 8080) — Prefix `/api/v1`

### Health

- `GET /api/v1/health`
  - Returns basic service status.

- `GET /api/v1/health/detailed`
  - Returns redis connectivity, data directory checks, and optional system metrics (psutil).

### Regions

- `GET /api/v1/regions/search`
  - Query params:
    - `q` (string, min length 2)
    - `type` (optional: `lga|suburb`)
    - `limit` (int, 1–50)

- `GET /api/v1/regions/by-coordinates`
  - Query params: `lat`, `lng`, `include_climate_data` (default true)

- `GET /api/v1/regions/{region_id}`
  - Query params: `include_climate_data` (default true)

- `GET /api/v1/regions/{region_id}/climate`
  - Query params: `layers` (repeatable)

- `GET /api/v1/regions/bounds/{level}`
  - Path param: `level` = `lga|suburb`
  - Query param: `state` (default `QLD`)

- `GET /api/v1/regions/nearby`
  - Query params: `lat`, `lng`, `level` (`lga|suburb`, default `lga`), `radius_km` (default 10)

- `GET /api/v1/regions/{region_id}/boundary`
  - Returns GeoJSON boundary feature.

### Tiles (Main API implementation)

- `GET /api/v1/tiles/{layer}/{level}/{z}/{x}/{y}.{format}`
  - `layer`: `pm25|precipitation|uv|humidity|temperature`
  - `level`: `lga|suburb`
  - `format`: `png|jpg|webp`
  - Behavior: if tile is missing, attempts on-demand generation via `TileService`.

- `GET /api/v1/tiles/{layer}/{level}/metadata`
  - Returns metadata for a layer+level.

- `POST /api/v1/tiles/{layer}/{level}/generate`
  - Optional query params: `min_zoom`, `max_zoom`

- `GET /api/v1/tiles/status`
  - Returns availability and size information.

---

## Tile Server (Port 8000) — Phase 0

### Health

- `GET /health`
  - Returns tile directory stats (tile count, size, supported zoom range).

### Tiles

- `GET /tiles/{layer}/{z}/{x}/{y}.png`
  - `layer` allowed: `pm25|humidity|uv|temperature|precipitation`
  - Returns transparent placeholder tiles when data is missing (to avoid seams).

### Layer Info

- `GET /tiles/pm25/info`
- `GET /tiles/precipitation/info`

### Diagnostics

- `GET /tiles/pm25/test`
- `GET /tiles/pm25/demo`

---

## Known Contract Mismatches (Worth Verifying)

- Frontend health endpoint is configured as `GET /health` on the **API base URL** (port 8080), but the main API defines health under `/api/v1/health`.
- Frontend tile URL generation expects `.../tiles/{layer}/{level}/...`, while the phase-0 tile server uses `.../tiles/{layer}/{z}/{x}/{y}.png`.

These may be legacy remnants or require alignment in config/routes.
