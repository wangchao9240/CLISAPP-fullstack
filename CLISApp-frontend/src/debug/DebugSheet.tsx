import React, {
  forwardRef,
  useImperativeHandle,
  useRef,
  useState,
} from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import {
  BottomSheetModal,
  BottomSheetScrollView,
  BottomSheetView,
} from '@gorhom/bottom-sheet';
import { Snackbar } from 'react-native-paper';
import { API_CONFIG } from '../constants/apiEndpoints';
import { useMapStore } from '../store/mapStore';
import { useDebugStore, type RiskKey } from './debugStore';
import { TelemetryTailScreen } from './TelemetryTailScreen';
import { setBoundaryMode } from './scenarios/boundaries';
import {
  applyComingSoonPlaceholder,
  clearCurrentRegion,
} from './scenarios/emptyState';
import { firePushReal } from './scenarios/pushReal';
import { firePushSimulated } from './scenarios/pushSim';
import { applyRiskCycle } from './scenarios/riskCycle';

export interface DebugSheetHandle {
  present: () => void;
  dismiss: () => void;
}

const RISK_LEVELS: Array<{ key: RiskKey; label: string }> = [
  { key: 'low', label: 'Low' },
  { key: 'moderate', label: 'Mod' },
  { key: 'high', label: 'High' },
  { key: 'extreme', label: 'Extreme' },
];

export const DebugSheet = forwardRef<DebugSheetHandle>((_props, ref) => {
  const sheetRef = useRef<any>(null);
  const [isTailOpen, setIsTailOpen] = useState(false);
  const [scenarioErrorVisible, setScenarioErrorVisible] = useState(false);
  const overrides = useDebugStore((state) => state.overrides);
  const unread = useDebugStore((state) => state.telemetryUnreadCount);
  const resetAll = useDebugStore((state) => state.resetAll);

  useImperativeHandle(ref, () => ({
    present: () => sheetRef.current?.present(),
    dismiss: () => sheetRef.current?.dismiss(),
  }));

  const handleScenarioError = (error: unknown): void => {
    console.error('Debug scenario failed', error);
    setScenarioErrorVisible(true);
  };

  const runScenario = (action: () => void | Promise<void>): void => {
    try {
      const result = action();

      if (result && typeof result.catch === 'function') {
        void result.catch(handleScenarioError);
      }
    } catch (error) {
      handleScenarioError(error);
    }
  };

  const handleReset = (): void => {
    const snapshot = useDebugStore.getState().preOverrideSnapshot;

    if (
      snapshot?.visible &&
      snapshot.regionId &&
      snapshot.regionName &&
      snapshot.regionType &&
      snapshot.latitude !== null &&
      snapshot.longitude !== null
    ) {
      useMapStore.getState().openRegionInfo({
        regionId: snapshot.regionId,
        regionName: snapshot.regionName,
        regionType: snapshot.regionType,
        latitude: snapshot.latitude,
        longitude: snapshot.longitude,
        climate: snapshot.climate,
      });
    } else {
      useMapStore.getState().clearRegionInfo();
    }

    resetAll();
  };

  const handleClearCurrentRegion = (): void => {
    clearCurrentRegion();
    sheetRef.current?.dismiss();
  };

  return (
    <>
      <BottomSheetModal ref={sheetRef} snapPoints={['85%']}>
        <BottomSheetView style={styles.sheet}>
          <BottomSheetScrollView contentContainerStyle={styles.content}>
            <Text style={styles.title}>CLISAPP DEBUG MODE</Text>

            <Text style={styles.groupHeader}>RISK BADGES</Text>
            <View style={styles.row}>
              {RISK_LEVELS.map((risk) => (
                <Pressable
                  accessibilityRole="button"
                  key={risk.key}
                  onPress={() => runScenario(() => applyRiskCycle(risk.key))}
                  style={[
                    styles.chip,
                    overrides.risk === risk.key && styles.chipActive,
                  ]}
                  testID={`debug-risk-${risk.key}`}
                >
                  <Text
                    style={[
                      styles.chipText,
                      overrides.risk === risk.key && styles.chipTextActive,
                    ]}
                  >
                    {risk.label}
                  </Text>
                </Pressable>
              ))}
            </View>

            <Text style={styles.groupHeader}>EMPTY / FALLBACK</Text>
            <DebugButton
              label="Coming-soon placeholder"
              onPress={() => runScenario(applyComingSoonPlaceholder)}
              testID="debug-empty-coming-soon"
            />
            <DebugButton
              label="Clear current region"
              onPress={() => runScenario(handleClearCurrentRegion)}
              testID="debug-empty-clear"
            />

            <Text style={styles.groupHeader}>PUSH NOTIFICATION</Text>
            <DebugButton
              label="Fire simulated alert"
              onPress={() => runScenario(firePushSimulated)}
              testID="debug-push-sim"
            />
            <DebugButton
              label="Fire real FCM (Android)"
              onPress={() => runScenario(() => firePushReal(API_CONFIG.BASE_URL))}
              testID="debug-push-real"
            />

            <Text style={styles.groupHeader}>BOUNDARIES</Text>
            <View style={styles.row}>
              <Pressable
                accessibilityRole="button"
                onPress={() => runScenario(() => setBoundaryMode('ssc'))}
                style={styles.chip}
                testID="debug-boundary-ssc"
              >
                <Text style={styles.chipText}>SSC</Text>
              </Pressable>
              <Pressable
                accessibilityRole="button"
                onPress={() => runScenario(() => setBoundaryMode('lga'))}
                style={styles.chip}
                testID="debug-boundary-lga"
              >
                <Text style={styles.chipText}>LGA</Text>
              </Pressable>
            </View>

            <Text style={styles.groupHeader}>TELEMETRY</Text>
            <DebugButton
              label={`Open live event tail (${unread} new)`}
              onPress={() => setIsTailOpen(true)}
              testID="debug-telemetry-open"
            />

            <Pressable
              accessibilityRole="button"
              onPress={handleReset}
              style={[styles.button, styles.resetButton]}
              testID="debug-reset"
            >
              <Text style={[styles.buttonText, styles.resetButtonText]}>
                Reset all overrides
              </Text>
            </Pressable>
          </BottomSheetScrollView>
        </BottomSheetView>
      </BottomSheetModal>

      <TelemetryTailScreen
        visible={isTailOpen}
        onClose={() => setIsTailOpen(false)}
      />
      <Snackbar
        duration={3000}
        visible={scenarioErrorVisible}
        onDismiss={() => setScenarioErrorVisible(false)}
      >
        Scenario failed - see logs
      </Snackbar>
    </>
  );
});

interface DebugButtonProps {
  label: string;
  onPress: () => void;
  testID: string;
}

const DebugButton: React.FC<DebugButtonProps> = ({ label, onPress, testID }) => (
  <Pressable
    accessibilityRole="button"
    onPress={onPress}
    style={styles.button}
    testID={testID}
  >
    <Text style={styles.buttonText}>{label}</Text>
  </Pressable>
);

const styles = StyleSheet.create({
  sheet: {
    flex: 1,
  },
  content: {
    padding: 16,
    paddingBottom: 32,
  },
  title: {
    color: '#4F5F6F',
    fontSize: 12,
    fontWeight: '700',
    marginBottom: 12,
  },
  groupHeader: {
    color: '#26323D',
    fontSize: 12,
    fontWeight: '700',
    marginBottom: 8,
    marginTop: 16,
  },
  row: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  chip: {
    backgroundColor: '#EEF2F4',
    borderRadius: 16,
    paddingHorizontal: 14,
    paddingVertical: 8,
  },
  chipActive: {
    backgroundColor: '#B84E2A',
  },
  chipText: {
    color: '#101820',
    fontSize: 13,
    fontWeight: '700',
  },
  chipTextActive: {
    color: '#FFFFFF',
  },
  button: {
    backgroundColor: '#EEF2F4',
    borderRadius: 8,
    marginBottom: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  buttonText: {
    color: '#101820',
    fontSize: 13,
    fontWeight: '700',
  },
  resetButton: {
    backgroundColor: '#FCEEEE',
    marginTop: 16,
  },
  resetButtonText: {
    color: '#A9362A',
  },
});
