# Architecture Patterns

## High-Level

CLISApp follows a **client/server** model with a mobile application consuming an API and raster tile endpoints.

- **Frontend (React Native):** renders a map UI and overlays climate raster tiles.
- **Backend (FastAPI):** provides region search/info endpoints and a separate tile server for climate layers.

## Backend Patterns

### Two FastAPI applications

1) **Main API service** (`CLISApp-backend/app/main.py`)

- Routers are mounted under `/api/v1` (health, tiles, regions).
- Uses `pydantic-settings` for configuration.
- Organizes code into routers → services → models.

2) **Tile server** (`CLISApp-backend/data_pipeline/servers/tile_server.py`)

- Serves PNG raster tiles via `/tiles/{layer}/{z}/{x}/{y}.png`.
- Provides health + info endpoints for layers.
- Uses transparent placeholder tiles for missing data to avoid seams in the UI.

### Data pipeline separation

- `data_pipeline/` contains scripts and servers for downloading/processing climate data and generating tile artifacts.
- `tiles/` and `data/` are mounted into containers for persistence.

## Frontend Patterns

### State management

- Uses **Zustand** stores with persistence via `AsyncStorage`.
- Stores include: map state, settings, favorites.

### Environment-aware endpoints

- Development base URLs are platform-aware:
  - Android emulator uses `10.0.2.2` for host access.
  - iOS simulator uses `localhost`.

### Map composition

- Base map: OpenStreetMap tile servers.
- Overlay: climate tiles from backend tile server.
- Users can switch map style/provider in settings.

## Integration Contracts

- Frontend calls backend health and tile endpoints for connectivity and raster overlays.
- Region APIs provide region boundaries and metadata for map interaction.
