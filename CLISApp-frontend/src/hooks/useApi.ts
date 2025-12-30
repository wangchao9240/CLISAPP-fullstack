/**
 * Custom hooks for API interactions
 * React hooks for managing API calls and state
 */

import { useState, useEffect, useCallback } from 'react';
import { apiService, RegionSearchResult, RegionInfo, HealthStatus } from '../services/ApiService';
import { RegionClimateOverview, RegionClimateStat } from '../types/region.types';
import { CLIMATE_LAYERS } from '../constants/climateData';
import { ClimateLayer } from '../types/climate.types';

export interface ApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refresh: () => void;
}

/**
 * Hook for health check
 */
export const useHealthCheck = (): ApiState<HealthStatus> => {
  const [data, setData] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchHealth = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await apiService.checkHealth();
      
      if (response.success) {
        setData(response.data);
      } else {
        setError(response.error || 'Failed to check health');
      }
    } catch (err: any) {
      setError(err.message || 'Network error');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHealth();
  }, [fetchHealth]);

  return {
    data,
    loading,
    error,
    refresh: fetchHealth,
  };
};

/**
 * Hook for region search
 */
export const useRegionSearch = () => {
  const [data, setData] = useState<RegionSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const searchRegions = useCallback(async (
    query: string,
    type?: 'lga' | 'suburb' | 'postcode',
    limit: number = 10
  ) => {
    if (query.trim().length < 2) {
      setData([]);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await apiService.searchRegions(query, type, limit);
      
      if (response.success) {
        setData(response.data || []);
      } else {
        setError(response.error || 'Search failed');
        setData([]);
      }
    } catch (err: any) {
      setError(err.message || 'Search error');
      setData([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const clearResults = useCallback(() => {
    setData([]);
    setError(null);
  }, []);

  return {
    data,
    loading,
    error,
    searchRegions,
    clearResults,
  };
};

/**
 * Hook for region information
 */
export const useRegionInfo = (regionId: string | null): ApiState<RegionInfo> => {
  const [data, setData] = useState<RegionInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchRegionInfo = useCallback(async () => {
    if (!regionId) {
      setData(null);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await apiService.getRegionInfo(regionId, true);
      
      if (response.success) {
        setData(response.data);
      } else {
        setError(response.error || 'Failed to get region info');
      }
    } catch (err: any) {
      setError(err.message || 'Network error');
    } finally {
      setLoading(false);
    }
  }, [regionId]);

  useEffect(() => {
    fetchRegionInfo();
  }, [fetchRegionInfo]);

  return {
    data,
    loading,
    error,
    refresh: fetchRegionInfo,
  };
};

export const fetchRegionInfoByCoordinates = async (
  latitude: number,
  longitude: number,
  includeClimateData: boolean = true
): Promise<RegionInfo | null> => {
  const response = await apiService.getRegionByCoordinates(
    latitude,
    longitude,
    includeClimateData,
  );

  if (!response.success) {
    return null;
  }
  return response.data as RegionInfo;
};

export const formatClimateOverview = (
  currentClimate: RegionInfo['current_climate'],
  activeLayer: ClimateLayer,
): RegionClimateOverview => {
  if (!currentClimate) {
    return { primary: null, secondary: [] };
  }

  const entries: RegionClimateStat[] = Object.entries(currentClimate).flatMap(([layerKey, data]) => {
    if (!data) return [];
    const key = layerKey as ClimateLayer;
    const config = CLIMATE_LAYERS[key];

    return [{
      layer: key,
      name: config?.name ?? key.toUpperCase(),
      value: data.value,
      unit: data.unit,
      category: data.category ?? undefined,
      description: config?.description,
      lastUpdated: data.timestamp,
    }];
  });

  const primary = entries.find((entry) => entry.layer === activeLayer) ?? null;
  const secondary = entries
    .filter((entry) => entry.layer !== activeLayer)
    .sort((a, b) => a.name.localeCompare(b.name));

  return { primary, secondary };
};

/**
 * Hook for nearby regions
 */
export const useNearbyRegions = () => {
  const [data, setData] = useState<RegionSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const findNearbyRegions = useCallback(async (
    lat: number,
    lng: number,
    level: 'lga' | 'suburb' = 'lga',
    radiusKm: number = 10
  ) => {
    setLoading(true);
    setError(null);

    try {
      const response = await apiService.getNearbyRegions(lat, lng, level, radiusKm);
      
      if (response.success) {
        setData(response.data || []);
      } else {
        setError(response.error || 'Failed to find nearby regions');
        setData([]);
      }
    } catch (err: any) {
      setError(err.message || 'Network error');
      setData([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const clearResults = useCallback(() => {
    setData([]);
    setError(null);
  }, []);

  return {
    data,
    loading,
    error,
    findNearbyRegions,
    clearResults,
  };
};

/**
 * Hook for tile status
 */
export const useTileStatus = (): ApiState<any> => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchTileStatus = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await apiService.getTileStatus();
      
      if (response.success) {
        setData(response.data);
      } else {
        setError(response.error || 'Failed to get tile status');
      }
    } catch (err: any) {
      setError(err.message || 'Network error');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTileStatus();
  }, [fetchTileStatus]);

  return {
    data,
    loading,
    error,
    refresh: fetchTileStatus,
  };
};
