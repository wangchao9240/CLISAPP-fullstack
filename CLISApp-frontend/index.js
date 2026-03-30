/**
 * @format
 */

import { AppRegistry, Platform } from 'react-native';
import App from './App';
import { name as appName } from './app.json';

if (Platform.OS === 'android') {
  const { getMessaging, setBackgroundMessageHandler } = require('@react-native-firebase/messaging');

  setBackgroundMessageHandler(getMessaging(), async remoteMessage => {
    console.log('Received background FCM message:', remoteMessage);
  });
}

AppRegistry.registerComponent(appName, () => App);
