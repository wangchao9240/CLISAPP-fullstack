import { useEffect, useMemo, useRef, useState, useCallback } from 'react';
import { Region } from '../types/map.types';
import { useMapStore } from '../store/mapStore';
import { BoundaryFeature, loadCoarseBoundaries, loadSscsForCoarse } from '../services/boundaries/BoundaryStore';
import { point, polygon, multiPolygon } from '@turf/helpers';
import booleanPointInPolygon from '@turf/boolean-point-in-polygon';
import { BOUNDARY_COLORS, BOUNDARY_WIDTHS, BOUNDARY_Z_INDEX } from '../constants/boundaryStyles';

export interface MapPolygonOverlay {
  id: string;
  coordinates: { latitude: number; longitude: number }[];
  holes?: { latitude: number; longitude: number }[][];
  strokeColor: string;
  strokeWidth: number;
  fillColor?: string;
  zIndex: number;
}

const SSC_ZOOM_THRESHOLD = 9;

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
  fillColor: string = BOUNDARY_COLORS.UNSELECTED_FILL,
): MapPolygonOverlay[] =>
  feature.polygons.map((poly, index) => ({
    id: `${feature.id}-${index}`,
    coordinates: poly.outline,
    holes: poly.holes,
    strokeColor,
    strokeWidth,
    fillColor,
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
        buildPolygonOverlays(
          feature,
          BOUNDARY_COLORS.UNSELECTED_STROKE,
          BOUNDARY_WIDTHS.UNSELECTED,
          BOUNDARY_Z_INDEX.COARSE
        )
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
      buildPolygonOverlays(
        ssc,
        BOUNDARY_COLORS.UNSELECTED_STROKE,
        BOUNDARY_WIDTHS.SSC_DETAIL,
        BOUNDARY_Z_INDEX.SSC
      )
    );

    const containingOverlays = buildPolygonOverlays(
      containing,
      BOUNDARY_COLORS.SELECTED_STROKE,
      BOUNDARY_WIDTHS.SELECTED,
      BOUNDARY_Z_INDEX.ACTIVE_COARSE
    );

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
