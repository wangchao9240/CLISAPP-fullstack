import { setBoundaryMode } from '../../scenarios/boundaries';
import { useMapStore } from '../../../store/mapStore';

jest.mock('@react-native-async-storage/async-storage', () => ({
  __esModule: true,
  default: {
    getItem: jest.fn(),
    setItem: jest.fn(),
    removeItem: jest.fn(),
  },
}));

describe('boundaries scenario', () => {
  beforeEach(() => {
    jest.restoreAllMocks();
  });

  it('SSC mode calls setMapLevel("ssc")', () => {
    const spy = jest.spyOn(useMapStore.getState(), 'setMapLevel');

    setBoundaryMode('ssc');

    expect(spy).toHaveBeenCalledWith('ssc');
  });

  it('LGA mode calls setMapLevel("coarse")', () => {
    const spy = jest.spyOn(useMapStore.getState(), 'setMapLevel');

    setBoundaryMode('lga');

    expect(spy).toHaveBeenCalledWith('coarse');
  });
});
