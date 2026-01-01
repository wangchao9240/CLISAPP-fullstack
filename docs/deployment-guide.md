# Deployment Guide

## Backend

### Canonical Two-Service Topology

CLISApp backend uses a **two-service architecture** in all environments:

1. **Main API** (port 8080) - JSON endpoints for regions, health, tile metadata/status
2. **Tile Server** (port 8000) - Tile image serving and tile-server health

This topology ensures:
- Clear separation of concerns (JSON API vs tile images)
- No conflicting tile-serving surfaces
- Consistent behavior across dev/staging/production

### Docker Compose (Local/VM)

In `CLISApp-backend/`:

```bash
docker compose up --build
```

Services:

- `backend` (8080) - Main API service
- `tile-server` (8000) - Dedicated tile image server
- `redis` (6379) - Caching layer

Volumes:

- `./tiles` and `./data` are mounted for persistence.

**Note:** The static tile mount on `:8080/tiles/*` is **disabled by default** in Phase 1 to avoid a third tile-serving surface. Use the dedicated tile server on port 8000 for all tile image requests.

### Render.com (Two services)

`CLISApp-backend/render.yaml` defines:

- `clisapp-api`: `uvicorn app.main:app` - Main API endpoints
- `clisapp-tiles`: `uvicorn data_pipeline.servers.tile_server:app` - Tile image serving

Environment variables:

- `LOG_LEVEL` and any required credentials (e.g., NASA Earthdata) must be set in the Render dashboard.
- **Do NOT set `ENABLE_LEGACY_STATIC_TILES=true`** - this deprecated feature will be removed in Phase 2.

## Frontend

Frontend is a React Native app.

- For distribution, follow standard React Native release steps for iOS/Android.
- The app uses different base URLs for development vs production (see `src/constants/apiEndpoints.ts`).

## Configuration Alignment

Ensure deployed endpoints match the frontend configuration:

- API base URL
- Tile server base URL
- Route prefixes (`/api/v1` vs root)

**Canonical production base URLs (Phase 1):**

- `API_BASE_URL` → `clisapp-api` service (e.g., `https://clisapp-api.qut.edu.au`)
- `TILE_SERVER_URL` → `clisapp-tiles` service (e.g., `https://clisapp-tiles.qut.edu.au/tiles`)

The mobile app should use `TILE_SERVER_URL` for tile images in all environments.
