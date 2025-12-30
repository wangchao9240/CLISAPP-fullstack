# Integration Architecture

## Overview

CLISApp is an integrated mobile + backend system:

- **Mobile app (React Native)** renders map UI.
- **Backend API (FastAPI)** provides region search/info and tile metadata.
- **Tile server (FastAPI, phase 0)** serves raster tile PNGs for climate layers.
- **Base map tiles** come from OpenStreetMap providers (public tile servers).

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

Tiles are requested as `{tile_base}/{layer}/{...}/{z}/{x}/{y}.png` depending on implementation.

### Frontend → OpenStreetMap

- Base tiles use public OSM tile servers (CartoDB light/dark, standard OSM, etc.).

## Compatibility Notes

The repository currently contains **two tile contract shapes**:

- Main API tile endpoint includes an extra `level` segment: `/api/v1/tiles/{layer}/{level}/...`
- Phase 0 tile server omits `level`: `/tiles/{layer}/{z}/{x}/{y}.png`

The frontend currently generates tile URLs including `level`, while also using some phase-0 endpoints for status (`/tiles/pm25/info`).

Before major feature development, it is recommended to align the dev/prod contract (single canonical tile endpoint shape).
