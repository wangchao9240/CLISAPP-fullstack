/**
 * CLISApp - Queensland Climate Information System App
 * Main entry point for the React Native application
 *
 * @format
 */

import React, { useEffect, useState } from 'react';
import { Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { Banner, PaperProvider } from 'react-native-paper';
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

const PRIVACY_DISMISSED_KEY = '@clisapp_privacy_dismissed';

const DebugFAB = __DEV__ ? require('./src/debug').DebugFAB : null;

function App(): React.JSX.Element {
  const [privacyVisible, setPrivacyVisible] = useState(false);

  useEffect(() => {
    void AsyncStorage.getItem(PRIVACY_DISMISSED_KEY).then(value => {
      if (value === null) {
        setPrivacyVisible(true);
      }
    });
  }, []);

  const handleDismissPrivacy = () => {
    setPrivacyVisible(false);
    void AsyncStorage.setItem(PRIVACY_DISMISSED_KEY, 'true');
  };

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
            <Banner
              visible={privacyVisible}
              actions={[{label: 'I Understand', onPress: handleDismissPrivacy}]}
              icon="shield-check-outline"
            >
              CLISApp collects anonymous usage data (app opens, region views) to
              improve the service. No personal information, precise location, or
              identifying details are collected or stored.
            </Banner>
            <AppNavigator />
            <HealthBottomSheet />
            {DebugFAB ? <DebugFAB /> : null}
          </BottomSheetModalProvider>
        </PaperProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}

export default App;
