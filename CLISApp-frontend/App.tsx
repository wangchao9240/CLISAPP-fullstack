/**
 * CLISApp - Queensland Climate Information System App
 * Main entry point for the React Native application
 *
 * @format
 */

import React, { useEffect } from 'react';
import { Platform } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { MapScreen } from './src/screens/MapScreen';
import {
  initializeFCM,
  onTokenRefresh,
} from './src/services/notificationService';

function App(): React.JSX.Element {
  useEffect(() => {
    if (Platform.OS !== 'android') {
      return;
    }

    void initializeFCM();

    const unsubscribe = onTokenRefresh();
    return () => {
      unsubscribe();
    };
  }, []);

  return (
    <SafeAreaProvider>
      <MapScreen />
    </SafeAreaProvider>
  );
}

export default App;
