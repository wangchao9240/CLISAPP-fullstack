import { useMapStore } from '../../store/mapStore';
import { useDebugStore } from '../debugStore';

export const applyComingSoonPlaceholder = (): void => {
  const debugStore = useDebugStore.getState();
  const mapStore = useMapStore.getState();

  debugStore.captureSnapshotIfNone(mapStore.regionInfo);
  mapStore.openRegionInfo({
    regionId: 'DEBUG-3110',
    regionName: 'Demo Suburb (Debug)',
    regionType: 'ssc',
    latitude: -27.47,
    longitude: 153.03,
    climate: null,
  });
  debugStore.setEmptyState(true);
};

export const clearCurrentRegion = (): void => {
  useMapStore.getState().clearRegionInfo();
};
