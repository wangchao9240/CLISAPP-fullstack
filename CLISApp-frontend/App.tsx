/**
 * CLISApp - Queensland Climate Information System App
 * Main entry point for the React Native application
 *
 * @format
 */

import React, { useEffect } from 'react';
import { Platform } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { PaperProvider } from 'react-native-paper';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { AppNavigator } from './src/navigation/AppNavigator';
import { theme } from './src/constants/theme';
import {
  initializeFCM,
  onTokenRefresh,
  setupForegroundHandler,
} from './src/services/notificationService';

function App(): React.JSX.Element {
  useEffect(() => {
    if (Platform.OS !== 'android') {
      return;
    }

    void initializeFCM();

    const unsubscribe = onTokenRefresh();
    const unsubscribeFromForegroundMessages = setupForegroundHandler();

    return () => {
      unsubscribe();
      unsubscribeFromForegroundMessages();
    };
  }, []);

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <PaperProvider theme={theme}>
          <AppNavigator />
        </PaperProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}

export default App;
