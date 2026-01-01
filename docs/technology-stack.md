# Technology Stack

## Repository Overview

CLISApp is a monorepo with two main parts:

- **Frontend (mobile):** `CLISApp-frontend/`
- **Backend (API + tile server):** `CLISApp-backend/`

## Frontend (Mobile)

- **Platform:** React Native (iOS + Android)
- **Language:** TypeScript
- **Runtime:** Node.js (package.json specifies `node >=20`)
- **Package managers:** npm / yarn (both lockfiles present)

### Key Libraries

- UI + runtime: `react`, `react-native`
- Navigation: `@react-navigation/native`, `@react-navigation/stack`
- Maps: `react-native-maps`
- State management: `zustand`
- Storage: `@react-native-async-storage/async-storage`
- Permissions / location: `react-native-permissions`, `react-native-geolocation-service`
- SVG: `react-native-svg`
- Geo helpers: `@turf/*`

### Tooling

- Lint: ESLint
- Test: Jest
- Formatting: Prettier

## Backend (API + Tile Server)

- **Language:** Python
- **Framework:** FastAPI
- **Web server:** Uvicorn
- **Core config:** Pydantic + pydantic-settings
- **Caching:** Redis

### Data / Geospatial

- Raster / array processing: numpy, scipy
- Geo stack: rasterio, geopandas, fiona, pyproj, shapely
- NetCDF / GRIB / HDF: netcdf4, h5netcdf, cfgrib, pyhdf, h5py
- Plotting / palettes: matplotlib, colorcet

### Tooling

- Test: pytest, pytest-asyncio
- Formatting: black, isort
- Typing: mypy
- Docs: mkdocs, mkdocs-material

### Runtime Topology (Local Dev)

CLISApp uses a **two-service architecture** for clear separation of concerns:

- **API service:** `http://localhost:8080`
  - JSON endpoints: `/api/v1/*` (regions, health, tile metadata/status)
  - Swagger documentation: `/docs` (debug mode only)

- **Tile service:** `http://localhost:8000`
  - Tile images: `/tiles/{layer}/{level}/{z}/{x}/{y}.png`
  - Tile server health: `/health`

**Note:** The legacy static tile mount on `:8080/tiles/*` is **disabled by default** in Phase 1 to avoid conflicting tile-serving surfaces. This will be completely removed in Phase 2.

**Production:** Tile images are served by the dedicated tile service; set `TILE_SERVER_URL` in the mobile app config to the tiles domain.

### Containerization

- Docker Compose defines services: `backend` (8080), `tile-server` (8000), `redis` (6379)
- Both services use the same Docker image with different startup commands
