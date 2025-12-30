# Source Tree Analysis

This analysis highlights the main directories, entry points, and where to look for key concerns.

## Top-Level

```
CLISAPP/
├── CLISApp-backend/           # FastAPI API + tile server + data pipeline
├── CLISApp-frontend/          # React Native mobile app (iOS/Android)
├── docs/                      # Generated project documentation (this folder)
└── _bmad/                     # BMad workflow engine (methodology support)
```

## Backend (`CLISApp-backend/`)

Key structure:

```
CLISApp-backend/
├── app/                       # Main FastAPI application (API service)
│   ├── main.py                # Entry point (creates FastAPI app)
│   ├── api/v1/                # Routers: health, regions, tiles
│   ├── core/                  # Settings (pydantic-settings), logging
│   ├── models/                # Pydantic schemas (region, climate)
│   ├── services/              # Domain logic (tile generation, region logic)
│   └── utils/                 # Utilities/helpers
├── data_pipeline/             # Download/process/generate tiles + tile server
│   └── servers/tile_server.py # Phase-0 tile server (FastAPI) on port 8000
├── tests/                     # Pytest suites
├── docker-compose.yml         # API + tile server + redis
└── Dockerfile                 # Container build
```

Entry points:

- API service: `app/main.py` (uvicorn target: `app.main:app`)
- Tile server: `data_pipeline/servers/tile_server.py` (uvicorn target: `data_pipeline.servers.tile_server:app`)

## Frontend (`CLISApp-frontend/`)

Key structure:

```
CLISApp-frontend/
├── App.tsx                    # React Native app entry
├── src/
│   ├── screens/               # Screens (MapScreen)
│   ├── components/            # UI components (Map, panels, UI)
│   ├── services/              # ApiService + map providers + boundary store
│   ├── store/                 # Zustand stores
│   ├── constants/             # API endpoints, map config, climate constants
│   └── types/                 # TypeScript domain types
├── ios/                       # iOS native project
├── android/                   # Android native project
└── package.json               # Dependencies and scripts
```

Entry points:

- `App.tsx` → main navigation / screen composition
- `src/screens/MapScreen.tsx` → primary UI surface

## Critical Folders (Where to Look First)

- Backend API contracts: `CLISApp-backend/app/api/v1/`
- Backend tile generation and serving: `CLISApp-backend/app/services/` and `CLISApp-backend/data_pipeline/`
- Frontend endpoint configuration: `CLISApp-frontend/src/constants/apiEndpoints.ts`
- Frontend network layer: `CLISApp-frontend/src/services/ApiService.ts`
- Frontend map state: `CLISApp-frontend/src/store/mapStore.ts`
- Frontend map components: `CLISApp-frontend/src/components/Map/`
