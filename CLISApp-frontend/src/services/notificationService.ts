import { Alert, PermissionsAndroid, Platform } from 'react-native';
import {
  getMessaging,
  getToken,
  subscribeToTopic,
  onMessage,
  onTokenRefresh,
} from '@react-native-firebase/messaging';
import type { RemoteMessage } from '@react-native-firebase/messaging';

export type TokenRefreshUnsubscribe = () => void;
export type ForegroundMessageUnsubscribe = () => void;

const messaging = getMessaging();
const HEALTH_ALERTS_TOPIC = 'qld-health-alerts';
const DEFAULT_ALERT_TITLE = 'Climate Health Alert';
const DEFAULT_ALERT_BODY = 'A new climate health alert is available.';

export const requestNotificationPermission = async (): Promise<boolean> => {
  if (Platform.OS !== 'android') {
    return false;
  }

  if (typeof Platform.Version === 'number' && Platform.Version < 33) {
    return true;
  }

  try {
    const result = await PermissionsAndroid.request(
      PermissionsAndroid.PERMISSIONS.POST_NOTIFICATIONS,
    );

    if (result !== PermissionsAndroid.RESULTS.GRANTED) {
      console.warn('Notification permission not granted:', result);
      return false;
    }

    console.log('Notification permission granted');
    return true;
  } catch (error) {
    console.error('Failed to request notification permission:', error);
    return false;
  }
};

export const subscribeToHealthAlerts = async (): Promise<boolean> => {
  if (Platform.OS !== 'android') {
    return false;
  }

  try {
    await subscribeToTopic(messaging, HEALTH_ALERTS_TOPIC);
    console.log('Subscribed to FCM topic:', HEALTH_ALERTS_TOPIC);
    return true;
  } catch (error) {
    console.error('Failed to subscribe to FCM topic:', error);
    return false;
  }
};

export const setupForegroundHandler = (): ForegroundMessageUnsubscribe => {
  if (Platform.OS !== 'android') {
    return () => undefined;
  }

  try {
    return onMessage(messaging, (remoteMessage: RemoteMessage) => {
      const title = remoteMessage.notification?.title ?? DEFAULT_ALERT_TITLE;
      const body = remoteMessage.notification?.body ?? DEFAULT_ALERT_BODY;

      Alert.alert(title, body);
    });
  } catch (error) {
    console.error('Failed to set up foreground FCM handler:', error);
    return () => undefined;
  }
};

export const initializeFCM = async (): Promise<string | null> => {
  if (Platform.OS !== 'android') {
    return null;
  }

  try {
    const hasNotificationPermission = await requestNotificationPermission();

    if (!hasNotificationPermission) {
      console.warn(
        'Notification permission denied. FCM setup will continue without guaranteed notification delivery.',
      );
    }

    const token = await getToken(messaging);
    console.log('FCM device token:', token);

    await subscribeToHealthAlerts();

    return token;
  } catch (error) {
    console.error('Failed to initialize FCM:', error);
    return null;
  }
};

export const listenToTokenRefresh = (): TokenRefreshUnsubscribe => {
  if (Platform.OS !== 'android') {
    return () => undefined;
  }

  try {
    return onTokenRefresh(messaging, (token: string) => {
      console.log('FCM token refreshed:', token);
    });
  } catch (error) {
    console.error('Failed to subscribe to FCM token refresh events:', error);
    return () => undefined;
  }
};
