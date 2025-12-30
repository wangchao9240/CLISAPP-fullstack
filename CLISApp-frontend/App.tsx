/**
 * CLISApp - Queensland Climate Information System App
 * Main entry point for the React Native application
 *
 * @format
 */

import React from 'react';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { MapScreen } from './src/screens/MapScreen';

function App(): React.JSX.Element {
  return (
    <SafeAreaProvider>
      <MapScreen />
    </SafeAreaProvider>
  );
}

export default App;