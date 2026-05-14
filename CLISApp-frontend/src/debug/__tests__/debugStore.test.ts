import { useDebugStore } from '../debugStore';
import type { RegionInfoPanelState } from '../../types/region.types';

jest.mock('@react-native-async-storage/async-storage', () => ({
  __esModule: true,
  default: {
    getItem: jest.fn(),
    setItem: jest.fn(),
    removeItem: jest.fn(),
  },
}));

const resetStore = () => useDebugStore.getState().resetAll();

const sampleSnapshot: RegionInfoPanelState = {
  visible: true,
  regionId: '3110',
  regionName: 'Brisbane City',
  regionType: 'ssc',
  latitude: -27.47,
  longitude: 153.03,
  climate: null,
  loading: false,
  error: null,
};

describe('debugStore', () => {
  beforeEach(() => {
    resetStore();
    useDebugStore.setState({ telemetryTail: [], telemetryUnreadCount: 0 });
  });

  it('starts with all overrides null and zero rotation index', () => {
    const s = useDebugStore.getState();

    expect(s.overrides.risk).toBeNull();
    expect(s.overrides.emptyState).toBe(false);
    expect(s.preOverrideSnapshot).toBeNull();
    expect(s.pushRotationIndex).toBe(0);
    expect(s.telemetryTail).toEqual([]);
    expect(s.telemetryUnreadCount).toBe(0);
  });

  it('setRiskOverride records the value', () => {
    useDebugStore.getState().setRiskOverride('high');

    expect(useDebugStore.getState().overrides.risk).toBe('high');
  });

  it('captureSnapshotIfNone records only on first transition', () => {
    const store = useDebugStore.getState();
    store.captureSnapshotIfNone(sampleSnapshot);
    expect(useDebugStore.getState().preOverrideSnapshot).toEqual(sampleSnapshot);

    const second = { ...sampleSnapshot, regionId: 'OTHER' };
    store.captureSnapshotIfNone(second);

    expect(useDebugStore.getState().preOverrideSnapshot?.regionId).toBe('3110');
  });

  it('bumpPushRotation wraps modulo 3', () => {
    const store = useDebugStore.getState();

    store.bumpPushRotation();
    store.bumpPushRotation();
    store.bumpPushRotation();

    expect(useDebugStore.getState().pushRotationIndex).toBe(0);
  });

  it('pushTelemetry caps the buffer at 20 entries, newest first', () => {
    const store = useDebugStore.getState();
    for (let i = 0; i < 25; i += 1) {
      store.pushTelemetry({
        id: String(i),
        timestamp: new Date().toISOString(),
        payload: {
          device_id: 'abc',
          event_date: '2026-05-15',
          time_of_day: '12:00:00',
          lat: null,
          lon: null,
        },
        outcome: 'ok',
      });
    }

    const tail = useDebugStore.getState().telemetryTail;
    expect(tail).toHaveLength(20);
    expect(tail[0].id).toBe('24');
    expect(tail[19].id).toBe('5');
  });

  it('markTelemetryRead zeroes the unread count', () => {
    const store = useDebugStore.getState();
    store.pushTelemetry({
      id: '1',
      timestamp: 't',
      payload: {
        device_id: 'a',
        event_date: 'd',
        time_of_day: 't',
        lat: null,
        lon: null,
      },
      outcome: 'ok',
    });

    expect(useDebugStore.getState().telemetryUnreadCount).toBe(1);
    store.markTelemetryRead();
    expect(useDebugStore.getState().telemetryUnreadCount).toBe(0);
  });

  it('resetAll clears overrides and snapshot but preserves telemetry tail', () => {
    const store = useDebugStore.getState();
    store.setRiskOverride('high');
    store.captureSnapshotIfNone(sampleSnapshot);
    store.pushTelemetry({
      id: '1',
      timestamp: 't',
      payload: {
        device_id: 'a',
        event_date: 'd',
        time_of_day: 't',
        lat: null,
        lon: null,
      },
      outcome: 'ok',
    });

    store.resetAll();

    const s = useDebugStore.getState();
    expect(s.overrides.risk).toBeNull();
    expect(s.preOverrideSnapshot).toBeNull();
    expect(s.telemetryTail).toHaveLength(1);
  });
});
