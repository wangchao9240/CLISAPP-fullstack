// Settings and preferences state management
import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { API_CONFIG } from '../constants/apiEndpoints';

interface SettingsState {
  // User preferences
  isDarkMode: boolean;
  enableLocationServices: boolean;
  cacheEnabled: boolean;
  maxCacheSize: number; // in MB
  
  // Map provider configuration
  mapProvider: 'react-native-maps' | 'maplibre';
  baseTileProvider: 'openstreetmap' | 'google' | 'satellite';
  
  // API configuration
  tileServerUrl: string;
  apiTimeout: number;
  
  // Actions
  setDarkMode: (enabled: boolean) => void;
  setLocationServices: (enabled: boolean) => void;
  setCacheEnabled: (enabled: boolean) => void;
  setMaxCacheSize: (size: number) => void;
  setMapProvider: (provider: 'react-native-maps' | 'maplibre') => void;
  setBaseTileProvider: (provider: 'openstreetmap' | 'google' | 'satellite') => void;
  setTileServerUrl: (url: string) => void;
  setApiTimeout: (timeout: number) => void;
  resetSettings: () => void;
}

const SETTINGS_VERSION = 3; // Increment to force reset incompatible settings

const defaultSettings = {
  _version: SETTINGS_VERSION,
  isDarkMode: false,
  enableLocationServices: true,
  cacheEnabled: true,
  maxCacheSize: 100, // 100MB
  mapProvider: 'react-native-maps' as const,
  baseTileProvider: 'openstreetmap' as const,
  tileServerUrl: API_CONFIG.TILE_SERVER_URL,
  apiTimeout: 10000, // 10 seconds
};

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      ...defaultSettings,

      setDarkMode: (_enabled) => set({ isDarkMode: false }),
      setLocationServices: (enabled) => set({ enableLocationServices: enabled }),
      setCacheEnabled: (enabled) => set({ cacheEnabled: enabled }),
      setMaxCacheSize: (size) => set({ maxCacheSize: size }),
      setMapProvider: (provider) => set({ mapProvider: provider }),
      setBaseTileProvider: (provider) => set({ baseTileProvider: provider }),
      setTileServerUrl: (url) => set({ tileServerUrl: url }),
      setApiTimeout: (timeout) => set({ apiTimeout: timeout }),
      resetSettings: () => set(defaultSettings),
    }),
    {
      name: 'clisapp-settings',
      storage: createJSONStorage(() => AsyncStorage),
      version: SETTINGS_VERSION,
      migrate: (persistedState: any, _version: number) => {
        // If stored version is older than current, reset to defaults
        if (!persistedState || persistedState._version < SETTINGS_VERSION) {
          console.log('Settings version outdated, resetting to defaults');
          return defaultSettings;
        }
        return persistedState;
      },
    }
  )
);
