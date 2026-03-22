import { Platform } from 'react-native';
import DeviceInfo from 'react-native-device-info';
import { API_CONFIG } from '../constants/apiEndpoints';

type EventType = 'app_start' | 'layer_change' | 'region_search' | 'region_select' | 'map_move';

interface TelemetryPayload {
  event_type: EventType;
  layer?: string;
  region_type?: string;
  zoom_level?: number;
  platform?: string;
  app_version?: string;
}

export const trackEvent = async (event_type: EventType, extras?: Omit<TelemetryPayload, 'event_type' | 'platform' | 'app_version'>): Promise<void> => {
  try {
    const payload: TelemetryPayload = {
      event_type,
      platform: Platform.OS,
      app_version: DeviceInfo.getVersion(),
      ...extras,
    };

    await fetch(`${API_CONFIG.BASE_URL}/api/v1/telemetry`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  } catch {
    // silently fail — telemetry should never break the app
  }
};
