import { useMapStore } from '../../store/mapStore';

export type BoundaryMode = 'ssc' | 'lga';

export const setBoundaryMode = (mode: BoundaryMode): void => {
  useMapStore.getState().setMapLevel(mode === 'ssc' ? 'ssc' : 'coarse');
};
