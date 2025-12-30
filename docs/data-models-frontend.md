# Data Models (Frontend)

The frontend uses TypeScript interfaces/types in `src/types` and also defines API response interfaces in `src/services/ApiService.ts`.

## Domain Types

### Climate (`CLISApp-frontend/src/types/climate.types.ts`)

Defines `ClimateLayer`, `MapLevel`, and supporting UI domain types for climate overlays.

### Map (`CLISApp-frontend/src/types/map.types.ts`)

Defines map region and related types used by `react-native-maps` and screen logic.

### Region UI (`CLISApp-frontend/src/types/region.types.ts`)

- `RegionClimateStat`
- `RegionClimateOverview`
- `RegionInfoPanelState`

## API Types (`CLISApp-frontend/src/services/ApiService.ts`)

- `ApiResponse<T>`
  - `success: boolean`
  - `data?: T`
  - `error?: string`
  - `status?: number`

- `RegionSearchResult`
- `RegionInfo`
- `HealthStatus`
- `RegionBoundary` (GeoJSON feature wrapper)

## Storage Shapes

Zustand stores persist selected fields to AsyncStorage (see `src/store/*Store.ts`).
