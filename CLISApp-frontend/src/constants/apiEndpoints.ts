// API endpoints and environment configuration
import { Platform } from 'react-native';
import Config from 'react-native-config';

const isDevelopment = __DEV__;

/**
 * Get the local development base URL based on platform
 * - iOS Simulator: localhost works fine
 * - Android Emulator: must use 10.0.2.2 to access host machine
 * - Physical devices: use your Mac's local network IP (e.g., 192.168.0.97)
 */
const getLocalBaseUrl = (): string => {
  if (Platform.OS === 'android') {
    // Android emulator special IP to access host
    return 'http://10.0.2.2:8080';
    
    // For physical Android device, uncomment and use your Mac's IP:
    // return 'http://192.168.0.97:8080';
  }
  
  // iOS simulator can use localhost
  return 'http://localhost:8080';
  
  // For physical iOS device, uncomment and use your Mac's IP:
  // return 'http://192.168.0.97:8080';
};

const getLocalTileServerUrl = (): string => {
  if (Platform.OS === 'android') {
    return 'http://10.0.2.2:8000/tiles';
    // For physical device: 'http://192.168.0.97:8000/tiles';
  }
  return 'http://localhost:8000/tiles';
  // For physical device: 'http://192.168.0.97:8000/tiles';
};

const normalizeBaseUrl = (url: string): string => url.replace(/\/+$/, '');

const resolveApiBaseUrl = (): string => {
  const envBase = Config.API_BASE_URL?.trim();
  if (envBase) {
    return normalizeBaseUrl(envBase);
  }
  const fallback = isDevelopment ? getLocalBaseUrl() : 'https://clisapp-api.qut.edu.au';
  return normalizeBaseUrl(fallback);
};

const resolveTileServerUrl = (): string => {
  const envBase = Config.TILE_SERVER_URL?.trim();
  if (envBase) {
    return normalizeBaseUrl(envBase);
  }
  const fallback = isDevelopment
    ? getLocalTileServerUrl()
    : 'https://clisapp-tiles.qut.edu.au/tiles';
  console.log('Using tile server URL:', normalizeBaseUrl(fallback));
  return normalizeBaseUrl(fallback);
};

export const API_CONFIG = {
  // Backend base URL
  BASE_URL: resolveApiBaseUrl(),
    
  // Tile server configuration (canonical tile base for mobile)
  TILE_SERVER_URL: resolveTileServerUrl(),
    
  // API timeouts
  TIMEOUT: isDevelopment ? 10000 : 15000,
  
  // Cache configuration  
  CACHE_ENABLED: true,
  MAX_CACHE_SIZE: isDevelopment ? 100 : 50, // MB
  
  // Logging
  LOG_LEVEL: isDevelopment ? 'debug' : 'error',
} as const;

// Google Maps API key (loaded from .env file via react-native-config)
export const GOOGLE_MAPS_API_KEY = Config.GOOGLE_MAPS_API_KEY || '';

// Backend API endpoints (Phase 1 - aligned with canonical API)
export const API_ENDPOINTS = {
  // Health check (Phase 1 canonical format)
  HEALTH: '/api/v1/health', // Canonical health endpoint
  HEALTH_DETAILED: '/api/v1/health/detailed', // Detailed health endpoint

  // Tile endpoints (Phase 1 canonical format)
  TILES: '/api/v1/tiles', // Canonical tile API base
  TILE_STATUS: '/api/v1/tiles/status', // Canonical tile status endpoint

  // Region endpoints
  REGIONS_SEARCH: '/api/v1/regions/search',
  REGIONS_INFO: '/api/v1/regions',
  REGIONS_CLIMATE: '/api/v1/regions/climate',
  REGIONS_NEARBY: '/api/v1/regions/nearby',
  REGIONS_BOUNDS: '/api/v1/regions/bounds',
  REGIONS_BY_COORDINATES: '/api/v1/regions/by-coordinates',
} as const;

// Helper function to build full API URLs
export const buildApiUrl = (endpoint: string): string => {
  return `${API_CONFIG.BASE_URL}${endpoint}`;
};
