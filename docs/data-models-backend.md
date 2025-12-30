# Data Models (Backend)

Backend models are primarily **Pydantic schemas** used for API responses.

## Climate Models (`CLISApp-backend/app/models/climate.py`)

- `ClimateLayer` (Enum): `pm25 | precipitation | uv | humidity | temperature`
- `MapLevel` (Enum): `lga | suburb`

- `ClimateDataPoint`
  - `layer: ClimateLayer`
  - `value: float`
  - `unit: str`
  - `timestamp: datetime`
  - `quality?: str`
  - `category?: str`

- `ClimateDataConfig`
  - `name`, `description`, `unit`
  - `color_scale: string[]`
  - `thresholds: number[]`
  - `min_value?`, `max_value?`
  - `data_source`, `update_frequency`

- `TileMetadata`
  - `layer: ClimateLayer`, `level: MapLevel`
  - `bounds: { north,south,east,west }`
  - `zoom_levels: { min,max }`
  - `tile_count: int`
  - timestamps (`last_updated?`, `data_date?`), `file_size_mb?`

## Region Models (`CLISApp-backend/app/models/region.py`)

- `Coordinate`
  - `latitude: float`
  - `longitude: float`

- `Bounds`
  - `northeast: Coordinate`
  - `southwest: Coordinate`

- `RegionSearchResult`
  - `id: string`, `name: string`
  - `type: lga|suburb`, `state: string`
  - `location: Coordinate`
  - optional: `population`, `area_km2`

- `RegionResponse`
  - identification: `id`, `name`, `type`, `state`
  - geo: `location`, `bounds`, `area_km2?`
  - admin: `parent_region?`, `postcode?`
  - demographics: `population?`, `population_density?`
  - climate: `current_climate?: Record<string, ClimateDataPoint>`
  - metadata: `last_updated?`, `data_sources?`

- `RegionClimateData`
  - `region_id`, `region_name`
  - `measurements: Record<string, ClimateDataPoint>`
  - `measurement_time`, `location`
  - `interpolation_method?`

- `RegionBoundary`
  - `region_id`, `name`, `type`
  - `geometry: GeoJSON (dict)`
  - `properties?`

## Persistence / Database

No database ORM models were identified in the main API layer; the system appears to rely on files and generated tile artifacts.
