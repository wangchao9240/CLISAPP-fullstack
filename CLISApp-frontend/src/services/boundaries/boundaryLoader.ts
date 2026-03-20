import type { Feature } from 'geojson';
import { apiService } from '../ApiService';
import { convertGeometryToShapes, type PolygonShape } from './BoundaryStore';

export interface BoundaryLoadResult {
  regionId: string;
  polygons: PolygonShape[];
  properties?: Feature['properties'];
}

export const loadRegionBoundary = async (
  regionId: string
): Promise<BoundaryLoadResult | null> => {
  try {
    const response = await apiService.getRegionBoundary(regionId);
    if (!response.success || !response.data) {
      return null;
    }

    const polygons = convertGeometryToShapes(response.data.geometry);
    if (polygons.length === 0) {
      return null;
    }

    return {
      regionId,
      polygons,
      properties: response.data.properties,
    };
  } catch (error) {
    console.warn('Failed to load region boundary:', error);
    return null;
  }
};
