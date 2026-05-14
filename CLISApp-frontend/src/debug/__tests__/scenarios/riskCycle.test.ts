import { applyRiskCycle } from '../../scenarios/riskCycle';
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

describe('applyRiskCycle', () => {
  beforeEach(() => {
    useDebugStore.getState().resetAll();
    useDebugStore.setState({ telemetryTail: [], telemetryUnreadCount: 0 });
    useMapStore.getState().clearRegionInfo();
  });

  it('opens region info with the fixture for high risk', () => {
    applyRiskCycle('high');

    const regionInfo = useMapStore.getState().regionInfo;
    expect(regionInfo.regionId).toBe('DEBUG-3110');
    expect(regionInfo.climate?.primary?.layer).toBe('pm25');
    expect(regionInfo.climate?.primary?.riskLevel).toBe('Unhealthy');
  });

  it('sets debugStore.overrides.risk', () => {
    applyRiskCycle('extreme');

    expect(useDebugStore.getState().overrides.risk).toBe('extreme');
  });

  it('is idempotent when called twice with the same level', () => {
    applyRiskCycle('low');
    const firstRegionInfo = useMapStore.getState().regionInfo;
    applyRiskCycle('low');

    expect(useMapStore.getState().regionInfo).toBe(firstRegionInfo);
  });

  it('captures snapshot on first transition only', () => {
    useMapStore.getState().openRegionInfo({
      regionId: 'REAL-1234',
      regionName: 'Real Region',
      regionType: 'ssc',
      latitude: -27.5,
      longitude: 153.0,
      climate: null,
    });

    applyRiskCycle('low');
    expect(useDebugStore.getState().preOverrideSnapshot?.regionId).toBe('REAL-1234');

    applyRiskCycle('high');
    expect(useDebugStore.getState().preOverrideSnapshot?.regionId).toBe('REAL-1234');
  });
});
