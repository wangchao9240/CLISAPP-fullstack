// Map state management using Zustand
import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Region } from '../types/map.types';
import { ClimateLayer, MapLevel } from '../types/climate.types';
import { QUEENSLAND_REGION } from '../constants/mapConfig';
import { DEFAULT_LAYER } from '../constants/climateData';
import { RegionInfoPanelState, RegionClimateOverview } from '../types/region.types';
import type { PolygonShape } from '../services/boundaries/BoundaryStore';

interface RegionBoundaryData {
  regionId: string;
  polygons: PolygonShape[];
  properties?: any;
}

export interface RecentRegion {
  id: string;
  name: string;
}

const MAX_RECENT_REGIONS = 5;

interface MapState {
  region: Region;
  activeLayer: ClimateLayer;
  mapLevel: MapLevel;
  selectedRegionId?: string;
  isLoading: boolean;
  tileLoadingProgress: number;
  error?: string;
  regionInfo: RegionInfoPanelState;
  regionBoundary: RegionBoundaryData | null;
  recentRegions: RecentRegion[];
  /** Ephemeral — current snap index of the bottom sheet (-1 = dismissed). Never persisted. */
  bottomSheetSnapIndex: number;
  setRegion: (region: Region) => void;
  setActiveLayer: (layer: ClimateLayer) => void;
  setMapLevel: (level: MapLevel) => void;
  toggleMapLevel: () => void;
  setSelectedRegion: (regionId?: string) => void;
  setLoading: (loading: boolean) => void;
  setTileLoadingProgress: (progress: number) => void;
  setError: (error?: string) => void;
  setBottomSheetSnapIndex: (index: number) => void;
  openRegionInfo: (payload: {
    regionId: string;
    regionName: string;
    regionType: string;
    latitude: number;
    longitude: number;
    climate: RegionClimateOverview | null;
  }) => void;
  closeRegionInfo: () => void;
  clearRegionInfo: () => void;
  setRegionInfoLoading: (loading: boolean) => void;
  setRegionInfoError: (error?: string) => void;
  setRegionBoundary: (boundary: RegionBoundaryData | null) => void;
  pushRecentRegion: (region: RecentRegion) => void;
  resetMapState: () => void;
}

const MAP_STORE_VERSION = 4;

export const useMapStore = create<MapState>()(
  persist(
    (set, get) => ({
      region: QUEENSLAND_REGION,
      activeLayer: DEFAULT_LAYER,
      mapLevel: 'coarse',
      selectedRegionId: undefined,
      isLoading: false,
      tileLoadingProgress: 0,
      error: undefined,
      regionBoundary: null,
      recentRegions: [],
      bottomSheetSnapIndex: -1,
      regionInfo: {
        visible: false,
        regionId: null,
        regionName: null,
        regionType: null,
        latitude: null,
        longitude: null,
        climate: null,
        loading: false,
        error: null,
      },

      setRegion: (region) => set({ region }),
      setActiveLayer: (layer) => set({ activeLayer: layer, isLoading: true }),
      setMapLevel: (level) => set({ mapLevel: level, isLoading: true }),
      toggleMapLevel: () => {
        const currentLevel = get().mapLevel;
        const newLevel = currentLevel === 'coarse' ? 'ssc' : 'coarse';
        set({ mapLevel: newLevel, isLoading: true });
      },
      setSelectedRegion: (selectedRegionId) => set({ selectedRegionId }),
      setLoading: (loading) => set({ isLoading: loading }),
      setTileLoadingProgress: (progress) => set({ tileLoadingProgress: progress }),
      setError: (error) => set({ error, isLoading: false }),
      openRegionInfo: ({ regionId, regionName, regionType, latitude, longitude, climate }) =>
        set({
          regionInfo: {
            visible: true,
            regionId,
            regionName,
            regionType,
            latitude,
            longitude,
            climate,
            loading: false,
            error: null,
          },
        }),
      closeRegionInfo: () =>
        set((state) => ({
          regionInfo: { ...state.regionInfo, visible: false, loading: false, error: null },
        })),
      clearRegionInfo: () =>
        set({
          regionInfo: {
            visible: false,
            regionId: null,
            regionName: null,
            regionType: null,
            latitude: null,
            longitude: null,
            climate: null,
            loading: false,
            error: null,
          },
        }),
      setRegionInfoLoading: (loading) =>
        set((state) => ({
          regionInfo: {
            ...state.regionInfo,
            loading,
            error: loading ? null : state.regionInfo.error,
          },
        })),
      setRegionInfoError: (error) =>
        set((state) => ({
          regionInfo: {
            ...state.regionInfo,
            error: error ?? null,
            loading: false,
          },
        })),
      setRegionBoundary: (boundary) => set({ regionBoundary: boundary }),
      setBottomSheetSnapIndex: (index) => set({ bottomSheetSnapIndex: index }),
      pushRecentRegion: (region) =>
        set((state) => {
          const filtered = state.recentRegions.filter((r) => r.id !== region.id);
          const updated = [region, ...filtered].slice(0, MAX_RECENT_REGIONS);
          return { recentRegions: updated };
        }),
      resetMapState: () =>
        set({
          region: QUEENSLAND_REGION,
          activeLayer: DEFAULT_LAYER,
          mapLevel: 'coarse',
          selectedRegionId: undefined,
          isLoading: false,
          tileLoadingProgress: 0,
          error: undefined,
          regionBoundary: null,
          recentRegions: [],
          bottomSheetSnapIndex: -1,
          regionInfo: {
            visible: false,
            regionId: null,
            regionName: null,
            regionType: null,
            latitude: null,
            longitude: null,
            climate: null,
            loading: false,
            error: null,
          },
        }),
    }),
    {
      name: 'clisapp-map',
      storage: createJSONStorage(() => AsyncStorage),
      version: MAP_STORE_VERSION,
      migrate: (persistedState: any, _version: number) => {
        if (!persistedState) {
          return persistedState;
        }

        const persistedMapLevel =
          typeof persistedState.mapLevel === 'string'
            ? persistedState.mapLevel === 'lga'
              ? 'coarse'
              : persistedState.mapLevel === 'suburb'
                ? 'ssc'
                : persistedState.mapLevel
            : undefined;

        // Ensure deterministic startup layer after config changes.
        return {
          ...persistedState,
          ...(persistedMapLevel ? { mapLevel: persistedMapLevel } : {}),
          activeLayer: DEFAULT_LAYER,
          recentRegions: persistedState.recentRegions ?? [],
        };
      },
      partialize: (state) => ({
        selectedRegionId: state.selectedRegionId,
        recentRegions: state.recentRegions,
      }),
    }
  )
);
