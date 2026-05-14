import {
  applyComingSoonPlaceholder,
  clearCurrentRegion,
} from '../../scenarios/emptyState';
import { useDebugStore } from '../../debugStore';
import { useMapStore } from '../../../store/mapStore';

jest.mock('@react-native-async-storage/async-storage', () => ({
  __esModule: true,
  default: {
    getItem: jest.fn(),
    setItem: jest.fn(),
    removeItem: jest.fn(),
  },
}));

describe('emptyState scenarios', () => {
  beforeEach(() => {
    jest.restoreAllMocks();
    useDebugStore.getState().resetAll();
    useMapStore.getState().clearRegionInfo();
  });

  it('applyComingSoonPlaceholder calls openRegionInfo with null climate', () => {
    const spy = jest.spyOn(useMapStore.getState(), 'openRegionInfo');

    applyComingSoonPlaceholder();

    expect(spy).toHaveBeenCalledWith(expect.objectContaining({ climate: null }));
    expect(useDebugStore.getState().overrides.emptyState).toBe(true);
  });

  it('clearCurrentRegion calls clearRegionInfo', () => {
    useMapStore.getState().openRegionInfo({
      regionId: 'X',
      regionName: 'X',
      regionType: 'ssc',
      latitude: 0,
      longitude: 0,
      climate: null,
    });

    clearCurrentRegion();

    expect(useMapStore.getState().regionInfo.visible).toBe(false);
  });
});
