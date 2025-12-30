import type { LatLng } from 'react-native-maps';
import type { FeatureCollection, Feature, Position } from 'geojson';
import { suburbCollections } from './suburbManifest';

const LGA_COLLECTION = require('../../../assets/geo/boundaries/lga_boundaries.json') as FeatureCollection;

export interface PolygonShape {
  outline: LatLng[];
  holes?: LatLng[][];
}

export interface BoundaryFeature {
  id: string;
  name: string;
  geometry: Feature['geometry'];
  props: Record<string, any>;
  bbox: [number, number, number, number];
  polygons: PolygonShape[];
}

const convertRing = (coords: Position[]): LatLng[] =>
  coords.map(([lng, lat]) => ({ latitude: lat, longitude: lng }));

export const convertGeometryToShapes = (geometry: Feature['geometry']): PolygonShape[] => {
  if (!geometry) {
    return [];
  }

  if (geometry.type === 'Polygon') {
    const [outer, ...holes] = (geometry.coordinates as Position[][][]).map(convertRing);
    return [
      {
        outline: outer,
        holes: holes.length > 0 ? holes : undefined,
      },
    ];
  }

  if (geometry.type === 'MultiPolygon') {
    return (geometry.coordinates as Position[][][][]).map((polygon) => {
      const [outer, ...holes] = polygon.map(convertRing);
      return {
        outline: outer,
        holes: holes.length > 0 ? holes : undefined,
      };
    });
  }

  return [];
};

const calculateBbox = (geometry: Feature['geometry']): [number, number, number, number] => {
  let minLng = Number.POSITIVE_INFINITY;
  let minLat = Number.POSITIVE_INFINITY;
  let maxLng = Number.NEGATIVE_INFINITY;
  let maxLat = Number.NEGATIVE_INFINITY;

  const visit = (ring: Position[]) => {
    ring.forEach(([lng, lat]) => {
      minLng = Math.min(minLng, lng);
      minLat = Math.min(minLat, lat);
      maxLng = Math.max(maxLng, lng);
      maxLat = Math.max(maxLat, lat);
    });
  };

  if (geometry?.type === 'Polygon') {
    (geometry.coordinates as Position[][][]).forEach(visit);
  } else if (geometry?.type === 'MultiPolygon') {
    (geometry.coordinates as Position[][][][]).forEach((poly) => poly.forEach(visit));
  }

  return [minLng, minLat, maxLng, maxLat];
};

const toBoundaryFeature = (feature: Feature): BoundaryFeature => {
  const polygons = convertGeometryToShapes(feature.geometry);
  return {
    id: String(feature.id ?? feature.properties?.id ?? feature.properties?.NAME ?? 'unknown'),
    name: feature.properties?.name ?? feature.properties?.NAME ?? String(feature.id ?? 'unknown'),
    geometry: feature.geometry,
    props: feature.properties ?? {},
    bbox: calculateBbox(feature.geometry),
    polygons,
  };
};

const LGA_FEATURES: BoundaryFeature[] = (LGA_COLLECTION.features ?? []).map(toBoundaryFeature);
const SUBURB_CACHE: Record<string, BoundaryFeature[]> = {};

export const loadLgaBoundaries = (): BoundaryFeature[] => LGA_FEATURES;

export const loadSuburbsForLga = (lgaId: string): BoundaryFeature[] => {
  if (SUBURB_CACHE[lgaId]) {
    return SUBURB_CACHE[lgaId];
  }

  const collection = suburbCollections[lgaId];
  if (!collection) {
    SUBURB_CACHE[lgaId] = [];
    return [];
  }

  const features = (collection.features ?? []).map(toBoundaryFeature);
  SUBURB_CACHE[lgaId] = features;
  return features;
};
