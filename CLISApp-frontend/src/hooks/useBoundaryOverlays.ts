import { useEffect, useMemo, useRef, useState, useCallback } from 'react';
import { Platform } from 'react-native';
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

/**
 * Produce a dedup key that captures both centre position AND zoom.
 * Including longitudeDelta ensures pure pinch-zoom (no pan) still
 * generates a distinct key so overlays are re-evaluated.
 */
const regionKey = (region: Region): string =>
  [
    region.latitude.toFixed(4),
    region.longitude.toFixed(4),
    region.latitudeDelta.toFixed(6),
    region.longitudeDelta.toFixed(6),
  ].join(':');

const buildTurfGeometry = (feature: BoundaryFeature) => {
  if (feature.geometry?.type === 'Polygon') {
    return polygon(feature.geometry.coordinates as any);
  }
  if (feature.geometry?.type === 'MultiPolygon') {
    return multiPolygon(feature.geometry.coordinates as any);
  }
  return null;
};

/**
 * Build Polygon overlays for a boundary feature.
 * `generation` is a monotonically increasing counter that is embedded into
 * each overlay id.  On Android, react-native-maps does not reliably reconcile
 * Polygon children when the array changes but some keys overlap.  Embedding
 * the generation guarantees every key is unique across overlay set switches,
 * forcing Android to unmount old polygons and mount new ones.
 */
const buildPolygonOverlays = (
  feature: BoundaryFeature,
  strokeColor: string,
  strokeWidth: number,
  zIndex: number,
  fillColor: string = BOUNDARY_COLORS.UNSELECTED_FILL,
  generation: number = 0,
): MapPolygonOverlay[] =>
  feature.polygons.map((poly, index) => ({
    id: `${feature.id}-${index}-g${generation}`,
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
  const lastRegionKeyRef = useRef<string>('');
  const turfCacheRef = useRef<Record<string, any>>({});

  // Use a ref for activeCoarse to avoid stale closures in updateOverlays.
  // Previously activeCoarse was state AND a useCallback dependency, meaning
  // the callback captured a stale value and the dependency change re-created
  // the callback (triggering the useEffect again with possible race conditions).
  const activeCoarseRef = useRef<BoundaryFeature | null>(null);

  // Generation counter: incremented every time the overlay set changes.
  // Embedded into overlay IDs so Android's react-native-maps treats each
  // overlay set as entirely new components, forcing proper unmount/mount.
  const generationRef = useRef(0);

  const updateOverlays = useCallback((targetRegion: Region) => {
    const zoom = getZoomLevel(targetRegion);

    if (zoom < SSC_ZOOM_THRESHOLD) {
      // Only regenerate coarse overlays if we were previously showing SSC
      // detail (activeCoarseRef was set) OR if overlays are empty (initial).
      // This avoids rebuilding the identical coarse overlay array on every
      // pan at low zoom.
      if (activeCoarseRef.current !== null) {
        generationRef.current += 1;
      }
      const gen = generationRef.current;
      const coarseOverlays = coarseFeatures.flatMap((feature) =>
        buildPolygonOverlays(
          feature,
          BOUNDARY_COLORS.UNSELECTED_STROKE,
          BOUNDARY_WIDTHS.UNSELECTED,
          BOUNDARY_Z_INDEX.COARSE,
          BOUNDARY_COLORS.UNSELECTED_FILL,
          gen,
        )
      );
      activeCoarseRef.current = null;
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
      if (activeCoarseRef.current !== null) {
        generationRef.current += 1;
      }
      activeCoarseRef.current = null;
      setOverlays([]);
      return;
    }

    // Skip rebuild if the active coarse region hasn't changed
    if (activeCoarseRef.current?.id === containing.id) {
      return;
    }

    generationRef.current += 1;
    const gen = generationRef.current;

    const sscFeatures = loadSscsForCoarse(containing.id);
    const sscOverlays = sscFeatures.flatMap((ssc) =>
      buildPolygonOverlays(
        ssc,
        BOUNDARY_COLORS.UNSELECTED_STROKE,
        BOUNDARY_WIDTHS.SSC_DETAIL,
        BOUNDARY_Z_INDEX.SSC,
        BOUNDARY_COLORS.UNSELECTED_FILL,
        gen,
      )
    );

    const containingOverlays = buildPolygonOverlays(
      containing,
      BOUNDARY_COLORS.SELECTED_STROKE,
      BOUNDARY_WIDTHS.SELECTED,
      BOUNDARY_Z_INDEX.ACTIVE_COARSE,
      BOUNDARY_COLORS.UNSELECTED_FILL,
      gen,
    );

    activeCoarseRef.current = containing;
    setOverlays([...containingOverlays, ...sscOverlays]);
  }, [coarseFeatures]);

  useEffect(() => {
    const key = regionKey(region);
    if (key === lastRegionKeyRef.current) {
      return;
    }
    lastRegionKeyRef.current = key;

    // Use a shorter debounce on Android where region change events fire less
    // frequently, ensuring boundary updates feel responsive.
    const debounceMs = Platform.OS === 'android' ? 80 : 150;
    const timer = setTimeout(() => updateOverlays(region), debounceMs);
    return () => clearTimeout(timer);
  }, [region, updateOverlays]);

  return useMemo(() => overlays, [overlays]);
};

export default useBoundaryOverlays;
