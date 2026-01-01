# API Contracts (Backend)

## Services

CLISApp backend uses a **two-service topology** in all environments:

1) **Main API (FastAPI)**
- Default: `http://localhost:8080`
- Provides: `/api/v1/*` JSON endpoints (regions, health, tile metadata/status)
- Swagger UI (debug): `/docs`

2) **Tile Server (FastAPI, Phase 1)**
- Default: `http://localhost:8000`
- Provides: `/tiles/*` tile images and `/health` endpoint
- Swagger UI: `/docs`

### Canonical Tile Serving Contract

**Tile Images:**
- Served by dedicated **tile server** on port 8000
- Canonical format: `/tiles/{layer}/{level}/{z}/{x}/{y}.png`
- Legacy format (deprecated): `/tiles/{layer}/{z}/{x}/{y}.png`

**Tile Metadata/Status:**
- Served by **main API** on port 8080
- `/api/v1/tiles/status` - Overall tile availability
- `/api/v1/tiles/{layer}/{level}/metadata` - Layer-specific metadata

### Deprecated: Static Tile Mount

**Phase 0 Behavior:** Main API mounted `/tiles` as static files on `:8080/tiles/*`

**Phase 1 Deprecation:** Static mount is **disabled by default** to eliminate third tile-serving surface.
- Can be re-enabled with `ENABLE_LEGACY_STATIC_TILES=true` (NOT RECOMMENDED)
- Creates contract ambiguity and bypasses API tile logic

**Phase 2 Removal:** Static mount code will be completely removed.

**Migration Path:** Use dedicated tile server (`:8000/tiles/*`) for all tile image requests.

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

## Tile Server (Port 8000) — Phase 1

### Health

- `GET /health`
  - Returns tile directory stats (tile count, size, supported zoom range).

### Tiles (Level-Aware - Phase 1)

- **`GET /tiles/{layer}/{level}/{z}/{x}/{y}.png`** (Canonical - Phase 1)
  - `layer`: `pm25|humidity|uv|temperature|precipitation`
  - `level`: `lga|suburb`
  - Falls back to legacy tile layout if level-specific tiles don't exist.
  - Returns transparent placeholder tiles when data is missing (to avoid seams).

- **`GET /tiles/{layer}/{z}/{x}/{y}.png`** (Legacy - Phase 0, DEPRECATED)
  - Provided for backward compatibility only.
  - Defaults to `suburb` level aggregation.
  - Will be removed in Phase 2.
  - Logs deprecation warning when accessed.

### Layer Info

- `GET /tiles/pm25/info`
- `GET /tiles/precipitation/info`
  - Updated to document both canonical and legacy URL templates.

### Diagnostics

- `GET /tiles/pm25/test`
- `GET /tiles/pm25/demo`
- `GET /` (root) - Shows server info and supported endpoints

---

## Phase 1 Contract Alignment

All known contract mismatches from Phase 0 have been resolved:

- ✅ **Health endpoints**: Main API provides `/health` (legacy, deprecated) and `/api/v1/health` (canonical).
- ✅ **Tile URLs**: Tile server now supports level-aware format (`/tiles/{layer}/{level}/{z}/{x}/{y}.png`), matching frontend expectations.
- ✅ **Tile metadata**: Frontend uses canonical API routes (`/api/v1/tiles/status`, `/api/v1/tiles/{layer}/{level}/metadata`).
- ✅ **Backward compatibility**: Legacy endpoints preserved with deprecation warnings for Phase 1 transition.

All deprecated endpoints will be removed in Phase 2.
