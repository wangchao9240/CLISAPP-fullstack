import { useEffect, useMemo, useRef, useState, useCallback } from 'react';
import { Region } from '../types/map.types';
import { useMapStore } from '../store/mapStore';
import { BoundaryFeature, loadLgaBoundaries, loadSuburbsForLga } from '../services/boundaries/BoundaryStore';
import { point, polygon, multiPolygon } from '@turf/helpers';
import booleanPointInPolygon from '@turf/boolean-point-in-polygon';

export interface MapPolygonOverlay {
  id: string;
  coordinates: { latitude: number; longitude: number }[];
  holes?: { latitude: number; longitude: number }[][];
  strokeColor: string;
  strokeWidth: number;
  zIndex: number;
}

const LGA_STROKE = 'rgba(96, 96, 96, 0.45)';
const SUBURB_STROKE = 'rgba(128, 128, 128, 0.55)';
const SUBURB_ZOOM_THRESHOLD = 9;
const LGA_BASE_WIDTH = 1;
const LGA_ACTIVE_WIDTH = 1.4;
const SUBURB_WIDTH = 0.8;

const getZoomLevel = (region: Region): number => {
  const z = Math.log2(360 / region.latitudeDelta);
  return Number.isFinite(z) ? Math.round(z) : 0;
};

const regionKey = (region: Region): string =>
  [region.latitude.toFixed(4), region.longitude.toFixed(4), region.latitudeDelta.toFixed(6)].join(':');

const buildTurfGeometry = (feature: BoundaryFeature) => {
  if (feature.geometry?.type === 'Polygon') {
    return polygon(feature.geometry.coordinates as any);
  }
  if (feature.geometry?.type === 'MultiPolygon') {
    return multiPolygon(feature.geometry.coordinates as any);
  }
  return null;
};

const buildPolygonOverlays = (
  feature: BoundaryFeature,
  strokeColor: string,
  strokeWidth: number,
  zIndex: number,
): MapPolygonOverlay[] =>
  feature.polygons.map((poly, index) => ({
    id: `${feature.id}-${index}`,
    coordinates: poly.outline,
    holes: poly.holes,
    strokeColor,
    strokeWidth,
    zIndex,
  }));

const useBoundaryOverlays = () => {
  const region = useMapStore((state) => state.region);
  const [lgaFeatures] = useState<BoundaryFeature[]>(() => loadLgaBoundaries());
  const [overlays, setOverlays] = useState<MapPolygonOverlay[]>([]);
  const [activeLga, setActiveLga] = useState<BoundaryFeature | null>(null);
  const lastRegionKeyRef = useRef<string>('');
  const turfCacheRef = useRef<Record<string, any>>({});

  const updateOverlays = useCallback((targetRegion: Region) => {
    const zoom = getZoomLevel(targetRegion);

    if (zoom < SUBURB_ZOOM_THRESHOLD) {
      const lgaOverlays = lgaFeatures.flatMap((feature) =>
        buildPolygonOverlays(feature, LGA_STROKE, LGA_BASE_WIDTH, 2)
      );
      setActiveLga(null);
      setOverlays(lgaOverlays);
      return;
    }

    const center = point([targetRegion.longitude, targetRegion.latitude]);

    let containing: BoundaryFeature | null = null;
    for (const feature of lgaFeatures) {
      const [minLng, minLat, maxLng, maxLat] = feature.bbox;
      if (
        targetRegion.longitude < minLng ||
        targetRegion.longitude > maxLng ||
        targetRegion.latitude < minLat ||
        targetRegion.latitude > maxLat
      ) {
        continue;
      }
      const cacheKey = feature.id;
      if (!turfCacheRef.current[cacheKey]) {
        turfCacheRef.current[cacheKey] = buildTurfGeometry(feature);
      }
      const geometry = turfCacheRef.current[cacheKey];
      if (geometry && booleanPointInPolygon(center, geometry)) {
        containing = feature;
        break;
      }
    }

    if (!containing) {
      setActiveLga(null);
      setOverlays([]);
      return;
    }

    if (activeLga?.id === containing.id) {
      return;
    }

    const suburbFeatures = loadSuburbsForLga(containing.id);
    const suburbOverlays = suburbFeatures.flatMap((suburb) =>
      buildPolygonOverlays(suburb, SUBURB_STROKE, SUBURB_WIDTH, 3)
    );

    const containingOverlays = buildPolygonOverlays(containing, LGA_STROKE, LGA_ACTIVE_WIDTH, 4);

    setActiveLga(containing);
    setOverlays([...containingOverlays, ...suburbOverlays]);
  }, [activeLga, lgaFeatures]);

  useEffect(() => {
    const key = regionKey(region);
    if (key === lastRegionKeyRef.current) {
      return;
    }
    lastRegionKeyRef.current = key;

    const timer = setTimeout(() => updateOverlays(region), 150);
    return () => clearTimeout(timer);
  }, [region, updateOverlays]);

  return useMemo(() => overlays, [overlays]);
};

export default useBoundaryOverlays;

