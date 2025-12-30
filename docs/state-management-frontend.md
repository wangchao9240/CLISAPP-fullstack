# State Management (Frontend)

Frontend state management is implemented with **Zustand** and persisted to **AsyncStorage**.

## Stores

### `useMapStore` (`CLISApp-frontend/src/store/mapStore.ts`)

Responsibilities:

- Current map region (lat/lng + deltas)
- Active climate layer selection
- Map level (`lga` vs `suburb`) + toggle
- Selected region, boundary data, region info panel state
- Loading/progress/error flags

Persistence:

- Persists a subset (`activeLayer`, `selectedRegionId`) via `partialize`.

### `useSettingsStore` (`CLISApp-frontend/src/store/settingsStore.ts`)

Responsibilities:

- Dark mode, location services, caching settings
- Map provider + base tile provider selection
- Tile server URL and API timeout

Notes:

- Uses a versioned migration strategy; resets defaults when version changes.

### `favoritesStore` (`CLISApp-frontend/src/store/favoritesStore.ts`)

Responsibilities:

- Persists a list of user favorites (regions).

## Key Pattern

- UI components read from stores (selectors/hooks) and dispatch actions.
- Network calls are centralized in `ApiService`, while state updates happen in stores/screens.
