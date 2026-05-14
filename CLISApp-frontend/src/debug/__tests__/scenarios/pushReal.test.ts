import { Platform } from 'react-native';
import { firePushReal } from '../../scenarios/pushReal';
import { useDebugStore } from '../../debugStore';
import * as pushSimModule from '../../scenarios/pushSim';

jest.mock('@react-native-async-storage/async-storage', () => ({
  __esModule: true,
  default: {
    getItem: jest.fn(),
    setItem: jest.fn(),
    removeItem: jest.fn(),
  },
}));

describe('firePushReal', () => {
  beforeEach(() => {
    useDebugStore.getState().resetAll();
    useDebugStore.setState({ telemetryTail: [], telemetryUnreadCount: 0 });
    globalThis.fetch = jest.fn();
    (Platform as any).OS = 'android';
    jest.spyOn(pushSimModule, 'firePushSimulated').mockImplementation(() => {});
  });

  afterEach(() => {
    jest.resetAllMocks();
  });

  it('POSTs to /api/v1/debug/fcm-test on Android with heatwave template', async () => {
    (globalThis.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => ({}),
    });

    await firePushReal('http://localhost:8080');

    expect(globalThis.fetch).toHaveBeenCalledWith(
      'http://localhost:8080/api/v1/debug/fcm-test',
      expect.objectContaining({
        method: 'POST',
        body: expect.stringContaining('Extreme Heat Warning'),
      }),
    );
  });

  it('falls back to firePushSimulated on AbortError', async () => {
    (globalThis.fetch as jest.Mock).mockRejectedValue(
      Object.assign(new Error('abort'), { name: 'AbortError' }),
    );

    await firePushReal('http://localhost:8080');

    expect(pushSimModule.firePushSimulated).toHaveBeenCalled();
  });

  it('falls back to firePushSimulated when the backend returns an error response', async () => {
    (globalThis.fetch as jest.Mock).mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => ({ detail: 'Firebase unavailable' }),
    });

    await expect(firePushReal('http://localhost:8080')).resolves.toBeUndefined();

    expect(pushSimModule.firePushSimulated).toHaveBeenCalled();
  });

  it('bumps rotation only once when AbortError falls back to simulated push', async () => {
    jest.spyOn(pushSimModule, 'firePushSimulated').mockRestore();
    (globalThis.fetch as jest.Mock).mockRejectedValue(
      Object.assign(new Error('abort'), { name: 'AbortError' }),
    );

    await firePushReal('http://localhost:8080');

    expect(useDebugStore.getState().pushRotationIndex).toBe(1);
  });

  it('no-ops on iOS', async () => {
    (Platform as any).OS = 'ios';

    await firePushReal('http://localhost:8080');

    expect(globalThis.fetch).not.toHaveBeenCalled();
  });

  it('bumps rotation index even on Android success', async () => {
    (globalThis.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => ({}),
    });

    await firePushReal('http://localhost:8080');

    expect(useDebugStore.getState().pushRotationIndex).toBe(1);
  });
});
