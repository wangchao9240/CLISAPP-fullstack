# Deployment Guide

## Backend

### Docker Compose (Local/VM)

In `CLISApp-backend/`:

```bash
docker compose up --build
```

Services:

- `backend` (8080)
- `tile-server` (8000)
- `redis` (6379)

Volumes:

- `./tiles` and `./data` are mounted for persistence.

### Render.com (Two services)

`CLISApp-backend/render.yaml` defines:

- `clisapp-api`: `uvicorn app.main:app`
- `clisapp-tiles`: `uvicorn data_pipeline.servers.tile_server:app`

Environment variables:

- `LOG_LEVEL` and any required credentials (e.g., NASA Earthdata) must be set in the Render dashboard.

## Frontend

Frontend is a React Native app.

- For distribution, follow standard React Native release steps for iOS/Android.
- The app uses different base URLs for development vs production (see `src/constants/apiEndpoints.ts`).

## Configuration Alignment

Ensure deployed endpoints match the frontend configuration:

- API base URL
- Tile server base URL
- Route prefixes (`/api/v1` vs root)
