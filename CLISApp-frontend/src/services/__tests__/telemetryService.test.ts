import AsyncStorage from '@react-native-async-storage/async-storage';
import DeviceInfo from 'react-native-device-info';
import Geolocation from 'react-native-geolocation-service';
import { check, RESULTS } from 'react-native-permissions';
import { API_CONFIG } from '../../constants/apiEndpoints';
import {
  __setDebugTap,
  getDeviceId,
  getLocationForTelemetry,
  sendTelemetry,
} from '../telemetryService';

jest.mock('react-native-config', () => ({
  __esModule: true,
  default: {},
}));

jest.mock('react-native-device-info', () => ({
  __esModule: true,
  default: {
    getUniqueId: jest.fn(),
  },
}));

jest.mock('react-native-geolocation-service', () => ({
  __esModule: true,
  default: {
    getCurrentPosition: jest.fn(),
  },
}));

jest.mock('react-native-permissions', () => ({
  check: jest.fn(),
  PERMISSIONS: {
    ANDROID: {
      ACCESS_FINE_LOCATION: 'android.permission.ACCESS_FINE_LOCATION',
    },
    IOS: {
      LOCATION_WHEN_IN_USE: 'ios.permission.LOCATION_WHEN_IN_USE',
    },
  },
  RESULTS: {
    GRANTED: 'granted',
    DENIED: 'denied',
    BLOCKED: 'blocked',
    UNAVAILABLE: 'unavailable',
    LIMITED: 'limited',
  },
}));

jest.mock('@react-native-async-storage/async-storage', () => ({
  __esModule: true,
  default: {
    getItem: jest.fn(),
    setItem: jest.fn(),
  },
}));

const mockGetUniqueId = DeviceInfo.getUniqueId as jest.Mock;
const mockGetCurrentPosition = Geolocation.getCurrentPosition as jest.Mock;
const mockCheck = check as jest.Mock;
const mockAsyncStorageGetItem = AsyncStorage.getItem as jest.Mock;
const mockAsyncStorageSetItem = AsyncStorage.setItem as jest.Mock;
const mockFetch = jest.fn();

describe('telemetryService', () => {
  beforeAll(() => {
    globalThis.fetch = mockFetch as unknown as typeof fetch;
  });

  beforeEach(() => {
    __setDebugTap(undefined);
    jest.useFakeTimers();
    jest.setSystemTime(new Date(2026, 2, 29, 9, 30, 45));

    jest.clearAllMocks();

    mockGetUniqueId.mockResolvedValue('device-123');
    mockCheck.mockResolvedValue(RESULTS.GRANTED);
    mockAsyncStorageGetItem.mockResolvedValue(null);
    mockAsyncStorageSetItem.mockResolvedValue(undefined);
    mockGetCurrentPosition.mockImplementation((success: any) => {
      success({
        coords: {
          latitude: -27.47056,
          longitude: 153.02678,
        },
      });
    });
    mockFetch.mockResolvedValue({
      ok: true,
      status: 201,
      json: async () => ({}),
    });
  });

  afterEach(() => {
    __setDebugTap(undefined);
    jest.useRealTimers();
  });

  it('returns a non-empty device identifier', async () => {
    await expect(getDeviceId()).resolves.toBe('device-123');
  });

  it('falls back to the stored AsyncStorage UUID when DeviceInfo fails', async () => {
    mockGetUniqueId.mockRejectedValue(new Error('device id unavailable'));
    mockAsyncStorageGetItem.mockResolvedValue('stored-uuid');

    await expect(getDeviceId()).resolves.toBe('stored-uuid');
    expect(mockAsyncStorageSetItem).not.toHaveBeenCalled();
  });

  it('generates and stores a fallback UUID when no device ID is available', async () => {
    mockGetUniqueId.mockRejectedValue(new Error('device id unavailable'));
    mockAsyncStorageGetItem.mockResolvedValue(null);

    const deviceId = await getDeviceId();

    expect(deviceId).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
    );
    expect(mockAsyncStorageSetItem).toHaveBeenCalledWith(
      '@clisapp_device_id',
      deviceId,
    );
  });

  it('truncates GPS coordinates to two decimal places', async () => {
    await expect(getLocationForTelemetry()).resolves.toEqual({
      lat: -27.47,
      lon: 153.03,
    });
  });

  it('returns null when location is unavailable', async () => {
    mockGetCurrentPosition.mockImplementation((_success: any, error: any) => {
      error({ code: 2, message: 'Location unavailable' });
    });

    await expect(getLocationForTelemetry()).resolves.toBeNull();
  });

  it('sends the ADR-8 payload shape to the telemetry endpoint', async () => {
    await sendTelemetry();

    expect(mockFetch).toHaveBeenCalledWith(
      `${API_CONFIG.BASE_URL}/api/v1/telemetry`,
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    const requestInit = mockFetch.mock.calls[0][1];
    const payload = JSON.parse(requestInit.body as string);

    expect(payload).toEqual({
      device_id: 'device-123',
      event_date: '2026-03-29',
      time_of_day: '09:30:45',
      lat: -27.47,
      lon: 153.03,
    });
  });

  it('sends null coordinates when location permission is not granted', async () => {
    mockCheck.mockResolvedValue(RESULTS.DENIED);

    await sendTelemetry();

    const requestInit = mockFetch.mock.calls[0][1];
    const payload = JSON.parse(requestInit.body as string);

    expect(payload.lat).toBeNull();
    expect(payload.lon).toBeNull();
    expect(mockGetCurrentPosition).not.toHaveBeenCalled();
  });

  it('silently swallows telemetry errors', async () => {
    mockFetch.mockRejectedValue(new Error('network down'));

    await expect(sendTelemetry()).resolves.toBeUndefined();
  });

  it('formats the event date and time using YYYY-MM-DD and HH:MM:SS', async () => {
    jest.setSystemTime(new Date(2026, 11, 1, 7, 8, 9));

    await sendTelemetry();

    const requestInit = mockFetch.mock.calls[0][1];
    const payload = JSON.parse(requestInit.body as string);

    expect(payload.event_date).toBe('2026-12-01');
    expect(payload.time_of_day).toBe('07:08:09');
    expect(payload.event_date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(payload.time_of_day).toMatch(/^\d{2}:\d{2}:\d{2}$/);
  });

  it('invokes the debug tap with payload and ok outcome on successful POST', async () => {
    const tap = jest.fn();
    __setDebugTap(tap);

    await sendTelemetry();

    expect(tap).toHaveBeenCalledTimes(1);
    expect(tap.mock.calls[0][1]).toBe('ok');
    expect(tap.mock.calls[0][0]).toMatchObject({
      device_id: 'device-123',
      event_date: '2026-03-29',
      time_of_day: '09:30:45',
      lat: -27.47,
      lon: 153.03,
    });
  });

  it('invokes the debug tap with fail outcome when fetch throws after payload creation', async () => {
    const tap = jest.fn();
    __setDebugTap(tap);
    mockFetch.mockRejectedValue(new Error('network'));

    await sendTelemetry();

    expect(tap).toHaveBeenCalledWith(
      expect.objectContaining({ device_id: 'device-123' }),
      'fail',
    );
  });

  it('invokes the debug tap with fail outcome when telemetry POST is not successful', async () => {
    const tap = jest.fn();
    __setDebugTap(tap);
    mockFetch.mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => ({}),
    });

    await sendTelemetry();

    expect(tap).toHaveBeenCalledWith(
      expect.objectContaining({ device_id: 'device-123' }),
      'fail',
    );
  });

  it('is a no-op when debug tap is undefined', async () => {
    await expect(sendTelemetry()).resolves.toBeUndefined();
  });
});
