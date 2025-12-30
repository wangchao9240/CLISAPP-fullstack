# Architecture (Frontend)

## Purpose

The frontend is a React Native mobile application that:

- Displays an interactive map
- Uses OpenStreetMap for base tiles
- Overlays climate raster tiles served by the backend
- Provides region search and a region info panel

## Entry Points

- App entry: `CLISApp-frontend/App.tsx`
- Primary screen: `CLISApp-frontend/src/screens/MapScreen.tsx`

## Key Modules

### Map Rendering

- `src/components/Map/UniversalMap.tsx` — chooses provider and composes layers
- `src/components/Map/OpenStreetMap.tsx` — OSM base layer

### Network / Backend Integration

- `src/constants/apiEndpoints.ts` — base URL selection (iOS vs Android emulator)
- `src/services/ApiService.ts` — typed API wrapper and timeout handling

### State

- Zustand stores under `src/store/`
  - map store, settings store, favorites

### UI

- `src/components/UI/` — LayerSelector, Legend, RegionSearchBar
- `src/components/panels/RegionInfoPanel.tsx` — region details panel

## Runtime Behavior (High-Level)

- On map screen load, app renders the base map.
- Layer selection controls which tile overlay is requested.
- Region search calls backend region endpoints and updates map state.
- Location permission flow enables “Locate me”.

## Build & Deploy

- iOS/Android native projects exist under `ios/` and `android/`.
- Build scripts are in `package.json`.
