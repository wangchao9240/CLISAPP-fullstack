/**
 * Type definitions for react-native-config
 * This allows TypeScript to understand the Config object from .env file
 */

declare module 'react-native-config' {
  export interface NativeConfig {
    GOOGLE_MAPS_API_KEY?: string;
    API_BASE_URL?: string;
    TILE_SERVER_URL?: string;
    API_TIMEOUT?: string;
    CACHE_ENABLED?: string;
    LOG_LEVEL?: string;
  }

  export const Config: NativeConfig;
  export default Config;
}

