import React, { useEffect, useRef } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { DebugSheet, type DebugSheetHandle } from './DebugSheet';
import {
  registerTelemetryTap,
  unregisterTelemetryTap,
} from './telemetryTap';

export const DebugFAB: React.FC = () => {
  const sheetRef = useRef<DebugSheetHandle>(null);

  useEffect(() => {
    if (!__DEV__) return undefined;

    registerTelemetryTap();
    return () => unregisterTelemetryTap();
  }, []);

  if (!__DEV__) {
    return null;
  }

  return (
    <>
      <Pressable
        accessibilityLabel="Open debug controls"
        accessibilityRole="button"
        onPress={() => sheetRef.current?.present()}
        style={styles.fab}
        testID="debug-fab"
      >
        <View style={styles.fabInner}>
          <Text style={styles.fabIcon}>DBG</Text>
          <Text style={styles.fabLabel}>DEV</Text>
        </View>
      </Pressable>
      <DebugSheet ref={sheetRef} />
    </>
  );
};

const styles = StyleSheet.create({
  fab: {
    alignItems: 'center',
    backgroundColor: 'rgba(184, 78, 42, 0.92)',
    borderRadius: 24,
    bottom: 120,
    elevation: 6,
    height: 48,
    justifyContent: 'center',
    position: 'absolute',
    right: 24,
    shadowColor: '#000000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 6,
    width: 48,
  },
  fabInner: {
    alignItems: 'center',
  },
  fabIcon: {
    color: '#FFFFFF',
    fontSize: 10,
    fontWeight: '800',
    lineHeight: 13,
  },
  fabLabel: {
    color: '#FFFFFF',
    fontSize: 8,
    fontWeight: '800',
  },
});
