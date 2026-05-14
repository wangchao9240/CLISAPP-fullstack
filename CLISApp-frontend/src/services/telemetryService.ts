import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';
import DeviceInfo from 'react-native-device-info';
import Geolocation from 'react-native-geolocation-service';
import {
  check,
  PERMISSIONS,
  RESULTS,
  type Permission,
} from 'react-native-permissions';
import { API_CONFIG } from '../constants/apiEndpoints';

const DEVICE_ID_STORAGE_KEY = '@clisapp_device_id';

interface TelemetryLocation {
  lat: number;
  lon: number;
}

export interface TelemetryPayload {
  device_id: string;
  event_date: string;
  time_of_day: string;
  lat: number | null;
  lon: number | null;
}

type DebugTap = (payload: TelemetryPayload, outcome: 'ok' | 'fail') => void;

let debugTap: DebugTap | undefined;

export const __setDebugTap = (fn: DebugTap | undefined): void => {
  debugTap = fn;
};

const padTimeUnit = (value: number): string =>
  value.toString().padStart(2, '0');

const buildEventDate = (date: Date): string => {
  const year = date.getFullYear();
  const month = padTimeUnit(date.getMonth() + 1);
  const day = padTimeUnit(date.getDate());

  return `${year}-${month}-${day}`;
};

const buildTimeOfDay = (date: Date): string => {
  const hours = padTimeUnit(date.getHours());
  const minutes = padTimeUnit(date.getMinutes());
  const seconds = padTimeUnit(date.getSeconds());

  return `${hours}:${minutes}:${seconds}`;
};

const truncateGps = (value: number): number => Math.round(value * 100) / 100;

const generateFallbackUuid = (): string =>
  'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, character => {
    const random = Math.floor(Math.random() * 16);
    const value = character === 'x' ? random : (random & 0x3) | 0x8;

    return value.toString(16);
  });

const getStoredFallbackDeviceId = async (): Promise<string> => {
  const generatedId = generateFallbackUuid();

  try {
    const storedDeviceId = await AsyncStorage.getItem(DEVICE_ID_STORAGE_KEY);

    if (
      typeof storedDeviceId === 'string' &&
      storedDeviceId.trim().length > 0
    ) {
      return storedDeviceId;
    }

    await AsyncStorage.setItem(DEVICE_ID_STORAGE_KEY, generatedId);
  } catch {
    // Ignore storage errors and return an in-memory fallback identifier.
  }

  return generatedId;
};

const getLocationPermission = (): Permission | undefined =>
  Platform.select({
    ios: PERMISSIONS.IOS.LOCATION_WHEN_IN_USE,
    android: PERMISSIONS.ANDROID.ACCESS_FINE_LOCATION,
    default: undefined,
  });

const getCurrentPosition = (): Promise<TelemetryLocation> =>
  new Promise((resolve, reject) => {
    Geolocation.getCurrentPosition(
      position => {
        resolve({
          lat: truncateGps(position.coords.latitude),
          lon: truncateGps(position.coords.longitude),
        });
      },
      error => {
        reject(error);
      },
      {
        enableHighAccuracy: true,
        timeout: 5000,
        maximumAge: 10000,
      },
    );
  });

export const getDeviceId = async (): Promise<string> => {
  try {
    const uniqueId = await DeviceInfo.getUniqueId();

    if (typeof uniqueId === 'string' && uniqueId.trim().length > 0) {
      return uniqueId;
    }
  } catch {
    // Fall through to AsyncStorage-backed UUID fallback.
  }

  return getStoredFallbackDeviceId();
};

export const getLocationForTelemetry =
  async (): Promise<TelemetryLocation | null> => {
    try {
      const permission = getLocationPermission();

      if (!permission) {
        return null;
      }

      const permissionStatus = await check(permission);

      if (permissionStatus !== RESULTS.GRANTED) {
        return null;
      }

      return await getCurrentPosition();
    } catch {
      return null;
    }
  };

export const sendTelemetry = async (): Promise<void> => {
  let payload: TelemetryPayload | null = null;

  try {
    const [deviceId, location] = await Promise.all([
      getDeviceId(),
      getLocationForTelemetry(),
    ]);
    const now = new Date();
    payload = {
      device_id: deviceId,
      event_date: buildEventDate(now),
      time_of_day: buildTimeOfDay(now),
      lat: location?.lat ?? null,
      lon: location?.lon ?? null,
    };

    const response = await fetch(`${API_CONFIG.BASE_URL}/api/v1/telemetry`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`Telemetry POST failed with ${response.status}`);
    }

    debugTap?.(payload, 'ok');
  } catch {
    if (payload) {
      debugTap?.(payload, 'fail');
    }
    // Telemetry is fire-and-forget and must never affect app startup.
  }
};
