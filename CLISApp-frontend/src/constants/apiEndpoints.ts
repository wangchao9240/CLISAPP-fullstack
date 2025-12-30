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

export const API_CONFIG = {
  // Backend base URL
  BASE_URL: isDevelopment 
    ? getLocalBaseUrl()
    : 'https://clisapp-api.qut.edu.au',
    
  // Tile server configuration (using Phase 0 tile server)
  TILE_SERVER_URL: isDevelopment 
    ? getLocalTileServerUrl()
    : 'https://clisapp-api.qut.edu.au/api/v1/tiles',
    
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

// Backend API endpoints (Phase 0 tile server)
export const API_ENDPOINTS = {
  // Health check (Phase 0 format)
  HEALTH: '/health',
  HEALTH_DETAILED: '/health', // Phase 0 only has basic health
  
  // Tile endpoints (Phase 0 format)
  TILES: '/tiles',
  TILE_STATUS: '/tiles/pm25/info', // Phase 0 tile info endpoint
  
  // Region endpoints (not available in Phase 0, for future use)
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
