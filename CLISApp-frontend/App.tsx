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
import { BottomSheetModalProvider } from '@gorhom/bottom-sheet';
import { AppNavigator } from './src/navigation/AppNavigator';
import { HealthBottomSheet } from './src/components/panels/HealthBottomSheet';
import { theme } from './src/constants/theme';
import {
  initializeFCM,
  listenToTokenRefresh,
  setupForegroundHandler,
} from './src/services/notificationService';
import { sendTelemetry } from './src/services/telemetryService';

function App(): React.JSX.Element {
  useEffect(() => {
    if (Platform.OS !== 'android') {
      return;
    }

    void sendTelemetry();
    void initializeFCM();

    const unsubscribe = listenToTokenRefresh();
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
          <BottomSheetModalProvider>
            <AppNavigator />
            <HealthBottomSheet />
          </BottomSheetModalProvider>
        </PaperProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}

export default App;
