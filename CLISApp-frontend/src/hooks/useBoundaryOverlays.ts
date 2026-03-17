import { useEffect, useMemo, useRef, useState, useCallback } from 'react';
import { Region } from '../types/map.types';
import { useMapStore } from '../store/mapStore';
import { BoundaryFeature, loadCoarseBoundaries, loadSscsForCoarse } from '../services/boundaries/BoundaryStore';
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

const COARSE_STROKE = 'rgba(96, 96, 96, 0.45)';
const SSC_STROKE = 'rgba(128, 128, 128, 0.55)';
const SSC_ZOOM_THRESHOLD = 9;
const COARSE_BASE_WIDTH = 1;
const COARSE_ACTIVE_WIDTH = 1.4;
const SSC_WIDTH = 0.8;

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
  const [coarseFeatures] = useState<BoundaryFeature[]>(() => loadCoarseBoundaries());
  const [overlays, setOverlays] = useState<MapPolygonOverlay[]>([]);
  const [activeCoarse, setActiveCoarse] = useState<BoundaryFeature | null>(null);
  const lastRegionKeyRef = useRef<string>('');
  const turfCacheRef = useRef<Record<string, any>>({});

  const updateOverlays = useCallback((targetRegion: Region) => {
    const zoom = getZoomLevel(targetRegion);

    if (zoom < SSC_ZOOM_THRESHOLD) {
      const coarseOverlays = coarseFeatures.flatMap((feature) =>
        buildPolygonOverlays(feature, COARSE_STROKE, COARSE_BASE_WIDTH, 2)
      );
      setActiveCoarse(null);
      setOverlays(coarseOverlays);
      return;
    }

    const center = point([targetRegion.longitude, targetRegion.latitude]);

    let containing: BoundaryFeature | null = null;
    for (const feature of coarseFeatures) {
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
      setActiveCoarse(null);
      setOverlays([]);
      return;
    }

    if (activeCoarse?.id === containing.id) {
      return;
    }

    const sscFeatures = loadSscsForCoarse(containing.id);
    const sscOverlays = sscFeatures.flatMap((ssc) =>
      buildPolygonOverlays(ssc, SSC_STROKE, SSC_WIDTH, 3)
    );

    const containingOverlays = buildPolygonOverlays(containing, COARSE_STROKE, COARSE_ACTIVE_WIDTH, 4);

    setActiveCoarse(containing);
    setOverlays([...containingOverlays, ...sscOverlays]);
  }, [activeCoarse, coarseFeatures]);

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
