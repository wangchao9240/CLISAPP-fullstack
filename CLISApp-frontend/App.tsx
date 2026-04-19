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

const BANNER_DISMISSED_KEY = '@clisapp_welcome_banner_dismissed';

function App(): React.JSX.Element {
  const [bannerVisible, setBannerVisible] = useState(false);

  useEffect(() => {
    void AsyncStorage.getItem(BANNER_DISMISSED_KEY).then(value => {
      if (value === null) {
        setBannerVisible(true);
      }
    });
  }, []);

  const handleDismissBanner = () => {
    setBannerVisible(false);
    void AsyncStorage.setItem(BANNER_DISMISSED_KEY, 'true');
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
              visible={bannerVisible}
              actions={[{ label: 'Got it', onPress: handleDismissBanner }]}
            >
              Welcome to CLISApp. Explore Queensland climate data and health
              indicators across regions.
            </Banner>
            <AppNavigator />
            <HealthBottomSheet />
          </BottomSheetModalProvider>
        </PaperProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}

export default App;
