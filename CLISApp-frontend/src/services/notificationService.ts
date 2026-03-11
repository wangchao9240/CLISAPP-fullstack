import { Platform } from 'react-native';
import messaging from '@react-native-firebase/messaging';

export type TokenRefreshUnsubscribe = () => void;

export const initializeFCM = async (): Promise<string | null> => {
  if (Platform.OS !== 'android') {
    return null;
  }

  try {
    const token = await messaging().getToken();
    console.log('FCM device token:', token);
    return token;
  } catch (error) {
    console.error('Failed to initialize FCM:', error);
    return null;
  }
};

export const onTokenRefresh = (): TokenRefreshUnsubscribe => {
  if (Platform.OS !== 'android') {
    return () => undefined;
  }

  try {
    return messaging().onTokenRefresh((token: string) => {
      console.log('FCM token refreshed:', token);
    });
  } catch (error) {
    console.error('Failed to subscribe to FCM token refresh events:', error);
    return () => undefined;
  }
};
