// Map configuration constants
import { Region } from '../types/map.types';

export const QUEENSLAND_REGION: Region = {
  latitude: -27.4698,
  longitude: 153.0251,
  latitudeDelta: 10.0,
  longitudeDelta: 10.0,
};

export const BRISBANE_REGION: Region = {
  latitude: -27.4698,
  longitude: 153.0251,
  latitudeDelta: 0.5,
  longitudeDelta: 0.5,
};

export const MAP_ZOOM_LEVELS = {
  LGA: {
    min: 6,
    max: 8,
    default: 7,
  },
  SUBURB: {
    min: 9,
    max: 12,
    default: 10,
  },
} as const;

export const TILE_CONFIG = {
  maximumZ: 13,
  minimumZ: 6,
  // Optimized opacity for smoother gradient blending with base map
  // Lower opacity (0.5-0.6) creates softer, more natural appearance
  // Transparent tiles blend better with OSM base layer
  opacity: 0.55,
  cacheMaxAgeSec: 60 * 60 * 24 * 7, // 7 days
  cacheNamespace: 'clisapp_tile_cache',
} as const;

// Layer-specific opacity settings for better visualization
// Different climate layers may benefit from different opacity levels
export const LAYER_OPACITY = {
  pm25: 0.2,        // Higher opacity for air quality (more visible)
  precipitation: 0.2, // Medium opacity for precipitation
  uv: 0.2,         // Medium-high opacity for UV index
  humidity: 0.2,    // Medium opacity for humidity
  temperature: 0.2, // Medium-high opacity for temperature
} as const;

// OpenStreetMap tile server configuration
export const OSM_TILE_SERVERS = {
  // Standard OpenStreetMap tiles
  standard: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
  
  // Alternative OSM tile servers for load balancing
  cartodb_light: 'https://cartodb-basemaps-a.global.ssl.fastly.net/light_all/{z}/{x}/{y}.png',
  cartodb_dark: 'https://cartodb-basemaps-a.global.ssl.fastly.net/dark_all/{z}/{x}/{y}.png',
  
  // OpenTopoMap for topographic view
  topo: 'https://tile.opentopomap.org/{z}/{x}/{y}.png',
} as const;

export const DEFAULT_OSM_TILE_SERVER = OSM_TILE_SERVERS.cartodb_light;

// Australia bounds (approx)
export const AUSTRALIA_BOUNDS = {
  north: -10.0,
  south: -44.0,
  west: 112.0,
  east: 154.0,
} as const;

// Queensland bounds (used for clamping map interactions)
export const QUEENSLAND_BOUNDS = {
  north: -9.0,
  south: -29.0,
  west: 138.0,
  east: 154.0,
} as const;