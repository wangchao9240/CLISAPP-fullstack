# Architecture (Backend)

## Purpose

Backend provides:

- Region APIs (search, boundaries, climate data aggregation)
- Tile APIs and/or a tile server serving climate raster tiles
- Data pipeline to generate/refresh tile artifacts from external data sources

## Runtime Components

### 1) API Service (FastAPI)

- Entry point: `CLISApp-backend/app/main.py`
- Routers mounted under `/api/v1`:
  - `health`, `regions`, `tiles`

### 2) Tile Server (Phase 0)

- Entry point: `CLISApp-backend/data_pipeline/servers/tile_server.py`
- Serves pre-generated PNG tiles under `/tiles/*`

### 3) Redis (optional)

- Used for caching in some health checks and pipeline components.

## Code Organization

- `app/api/v1/` — request routing and parameter validation
- `app/services/` — domain logic (region lookup, tile generation/status)
- `app/models/` — Pydantic response schemas
- `app/core/` — configuration via pydantic-settings
- `data_pipeline/` — data acquisition + processing + tile generation

## Configuration

- `.env` / environment variables feed `app/core/config.py` (pydantic-settings)
- Docker Compose sets defaults for ports and paths:
  - tiles volume mounted at `./tiles`
  - data volume mounted at `./data`

## Data Sources (as documented)

- NASA Earthdata (MODIS LANCE)
- GPM IMERG
- CAMS (for PM2.5/UV in some contexts)
- Open-Meteo (realtime weather per implementation guide)

Exact pipeline source of truth is under `data_pipeline/` modules and should be referenced when changing data ingestion.

## Testing

- Test framework: `pytest`
- Tests live under `CLISApp-backend/tests/`

## Deployment

- Docker Compose for local/hosted deployment
- Render.com configuration in `render.yaml` (two python web services)
