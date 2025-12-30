/**
 * API Service for CLISApp Frontend
 * Handles all communication with the backend API
 */

import { API_CONFIG, API_ENDPOINTS, buildApiUrl } from '../constants/apiEndpoints';

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  status?: number;
}

export interface RegionSearchResult {
  id: string;
  name: string;
  type: 'lga' | 'suburb';
  state: string;
  location: {
    latitude: number;
    longitude: number;
  };
  population?: number;
  area_km2?: number;
}

export interface RegionInfo {
  id: string;
  name: string;
  type: 'lga' | 'suburb';
  state: string;
  location: {
    latitude: number;
    longitude: number;
  };
  bounds: {
    northeast: { latitude: number; longitude: number };
    southwest: { latitude: number; longitude: number };
  };
  area_km2?: number;
  population?: number;
  population_density?: number;
  current_climate?: Record<string, {
    layer: string;
    value: number;
    unit: string;
    timestamp: string;
    quality?: string;
    category?: string;
  }>;
  last_updated?: string;
}

export interface HealthStatus {
  status: string;
  timestamp: string;
  service: string;
  version: string;
}

export interface RegionBoundary {
  type: 'Feature';
  id: string;
  properties: {
    id: string;
    name: string;
    type: 'lga' | 'suburb';
    state: string;
    area_km2?: number;
    parent_region?: string;
    postcode?: string;
  };
  geometry: GeoJSON.Geometry;
}

class ApiService {
  public baseUrl: string;
  private timeout: number;

  constructor() {
    this.baseUrl = API_CONFIG.BASE_URL;
    this.timeout = API_CONFIG.TIMEOUT;
  }

  /**
   * Generic fetch method with error handling
   */
  public async fetchWithTimeout(url: string, options: RequestInit = {}): Promise<ApiResponse> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        return {
          success: false,
          error: `HTTP ${response.status}: ${response.statusText}`,
          status: response.status,
        };
      }

      const data = await response.json();
      return {
        success: true,
        data,
        status: response.status,
      };
    } catch (error: any) {
      clearTimeout(timeoutId);
      
      if (error.name === 'AbortError') {
        return {
          success: false,
          error: 'Request timeout',
          status: 408,
        };
      }

      return {
        success: false,
        error: error.message || 'Network error',
        status: 0,
      };
    }
  }

  /**
   * Health check
   */
  async checkHealth(): Promise<ApiResponse<HealthStatus>> {
    const url = buildApiUrl(API_ENDPOINTS.HEALTH);
    return this.fetchWithTimeout(url);
  }

  /**
   * Search for regions
   */
  async searchRegions(
    query: string,
    type?: 'lga' | 'suburb',
    limit: number = 10
  ): Promise<ApiResponse<RegionSearchResult[]>> {
    const params = new URLSearchParams({
      q: query,
      limit: limit.toString(),
    });

    if (type) {
      params.append('type', type);
    }

    const url = buildApiUrl(`${API_ENDPOINTS.REGIONS_SEARCH}?${params.toString()}`);
    return this.fetchWithTimeout(url);
  }

  /**
   * Get region information by ID
   */
  async getRegionInfo(
    regionId: string,
    includeClimateData: boolean = true
  ): Promise<ApiResponse<RegionInfo>> {
    const params = new URLSearchParams({
      include_climate_data: includeClimateData.toString(),
    });

    const url = buildApiUrl(`${API_ENDPOINTS.REGIONS_INFO}/${regionId}?${params.toString()}`);
    return this.fetchWithTimeout(url);
  }

  /**
   * Get nearby regions
   */
  async getNearbyRegions(
    lat: number,
    lng: number,
    level: 'lga' | 'suburb' = 'lga',
    radiusKm: number = 10
  ): Promise<ApiResponse<RegionSearchResult[]>> {
    const params = new URLSearchParams({
      lat: lat.toString(),
      lng: lng.toString(),
      level,
      radius_km: radiusKm.toString(),
    });

    const url = buildApiUrl(`${API_ENDPOINTS.REGIONS_NEARBY}?${params.toString()}`);
    return this.fetchWithTimeout(url);
  }

  /**
   * Get climate data for a region
   */
  async getRegionClimateData(
    regionId: string,
    layers?: string[]
  ): Promise<ApiResponse<any>> {
    const params = new URLSearchParams();
    
    if (layers && layers.length > 0) {
      layers.forEach(layer => params.append('layers', layer));
    }

    const url = buildApiUrl(`${API_ENDPOINTS.REGIONS_INFO}/${regionId}/climate?${params.toString()}`);
    return this.fetchWithTimeout(url);
  }

  async getRegionByCoordinates(
    lat: number,
    lng: number,
    includeClimateData: boolean = true
  ): Promise<ApiResponse<RegionInfo>> {
    const params = new URLSearchParams({
      lat: lat.toString(),
      lng: lng.toString(),
      include_climate_data: includeClimateData.toString(),
    });
    const url = buildApiUrl(`${API_ENDPOINTS.REGIONS_BY_COORDINATES}?${params.toString()}`);
    return this.fetchWithTimeout(url);
  }

  /**
   * Get region boundary (GeoJSON geometry)
   */
  async getRegionBoundary(regionId: string): Promise<ApiResponse<GeoJSON.Feature>> {
    const url = buildApiUrl(`${API_ENDPOINTS.REGIONS_INFO}/${regionId}/boundary`);
    return this.fetchWithTimeout(url);
  }

  /**
   * Get tile server status
   */
  async getTileStatus(): Promise<ApiResponse<any>> {
    const url = buildApiUrl(API_ENDPOINTS.TILE_STATUS);
    return this.fetchWithTimeout(url);
  }

  /**
   * Generate tile URL for map tiles
   */
  getTileUrl(
    layer: 'pm25' | 'precipitation' | 'uv' | 'humidity' | 'temperature',
    level: 'lga' | 'suburb',
    z: number,
    x: number,
    y: number,
    format: 'png' | 'jpg' | 'webp' = 'png'
  ): string {
    return `${API_CONFIG.TILE_SERVER_URL}/${layer}/${level}/${z}/${x}/${y}.${format}`;
  }

  /**
   * Get layer metadata
   */
  async getLayerMetadata(
    layer: 'pm25' | 'precipitation' | 'uv' | 'humidity' | 'temperature',
    level: 'lga' | 'suburb'
  ): Promise<ApiResponse<any>> {
    const url = buildApiUrl(`${API_ENDPOINTS.TILES}/${layer}/${level}/metadata`);
    return this.fetchWithTimeout(url);
  }
}

// Export singleton instance
export const apiService = new ApiService();
export default apiService;
