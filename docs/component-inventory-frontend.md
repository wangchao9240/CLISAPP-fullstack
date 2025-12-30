# Component Inventory (Frontend)

## Screens

- `CLISApp-frontend/src/screens/MapScreen.tsx`
  - Main screen for map UI and climate overlay controls.
  - Integrates location permission flow and “Locate me” behavior.

## Map Components

- `CLISApp-frontend/src/components/Map/UniversalMap.tsx`
  - Map container that selects the underlying provider and layers.

- `CLISApp-frontend/src/components/Map/OpenStreetMap.tsx`
  - OSM base layer integration.

## UI Components

- `CLISApp-frontend/src/components/UI/LayerSelector.tsx`
  - Climate layer selector.

- `CLISApp-frontend/src/components/UI/Legend.tsx`
  - Visual legend for current layer.

- `CLISApp-frontend/src/components/UI/RegionSearchBar.tsx`
  - Region search input and UX.

## Panels

- `CLISApp-frontend/src/components/panels/RegionInfoPanel.tsx`
  - Region details panel (name/type and climate overview).

## Assets Used by UI

- `CLISApp-frontend/src/assets/img/locate.png` (MapScreen locate icon)

## Notes

This inventory is based on current `src/components` and `src/screens` directories; additional UI may be implemented via the map provider layer and services.
