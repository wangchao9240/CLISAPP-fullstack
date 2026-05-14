import React, { useEffect } from 'react';
import {
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { sendTelemetry } from '../services/telemetryService';
import { useDebugStore } from './debugStore';

interface Props {
  visible: boolean;
  onClose: () => void;
}

const last8 = (value: string): string =>
  value.length > 8 ? value.slice(-8) : value;

export const TelemetryTailScreen: React.FC<Props> = ({ visible, onClose }) => {
  const tail = useDebugStore((state) => state.telemetryTail);
  const telemetryUnreadCount = useDebugStore(
    (state) => state.telemetryUnreadCount,
  );
  const markTelemetryRead = useDebugStore((state) => state.markTelemetryRead);

  useEffect(() => {
    if (visible && telemetryUnreadCount > 0) {
      markTelemetryRead();
    }
  }, [markTelemetryRead, telemetryUnreadCount, visible]);

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <View style={styles.root}>
        <View style={styles.header}>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Close telemetry tail"
            hitSlop={12}
            onPress={onClose}
            testID="debug-telemetry-close"
          >
            <Text style={styles.headerButton}>Close</Text>
          </Pressable>
          <Text style={styles.headerTitle}>TELEMETRY LIVE TAIL</Text>
          <Pressable
            accessibilityRole="button"
            hitSlop={12}
            onPress={() =>
              useDebugStore.setState({
                telemetryTail: [],
                telemetryUnreadCount: 0,
              })
            }
            testID="debug-telemetry-clear"
          >
            <Text style={styles.headerButton}>Clear</Text>
          </Pressable>
        </View>

        <View style={styles.privacyBanner}>
          <Text style={styles.privacyTitle}>Privacy guarantees</Text>
          <Text style={styles.privacyLine}>Device ID is an opaque app identifier</Text>
          <Text style={styles.privacyLine}>Only the last 8 characters are shown here</Text>
          <Text style={styles.privacyLine}>lat/lon truncated to 2 dp</Text>
          <Text style={styles.privacyLine}>No name, email, IP, or precise location</Text>
        </View>

        <Pressable
          accessibilityRole="button"
          onPress={() => void sendTelemetry()}
          style={styles.primaryButton}
          testID="debug-telemetry-fire"
        >
          <Text style={styles.primaryButtonText}>Fire test telemetry</Text>
        </Pressable>

        <ScrollView contentContainerStyle={styles.list}>
          {tail.length === 0 ? (
            <Text style={styles.empty}>No events yet.</Text>
          ) : (
            tail.map((entry) => {
              const location =
                entry.payload.lat === null || entry.payload.lon === null
                  ? 'null, null'
                  : `${entry.payload.lat}, ${entry.payload.lon}`;

              return (
                <View key={entry.id} style={styles.row}>
                  <Text style={styles.rowTitle}>
                    {`${entry.payload.time_of_day}  ${entry.outcome}`}
                  </Text>
                  <Text style={styles.rowDetail}>{last8(entry.payload.device_id)}</Text>
                  <Text style={styles.rowDetail}>{location}</Text>
                </View>
              );
            })
          )}
        </ScrollView>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: '#F7F8FA',
    paddingTop: 48,
  },
  header: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingBottom: 12,
    paddingHorizontal: 16,
  },
  headerButton: {
    color: '#0B6E99',
    fontSize: 16,
    fontWeight: '700',
  },
  headerTitle: {
    color: '#3F4A55',
    fontSize: 12,
    fontWeight: '700',
  },
  privacyBanner: {
    backgroundColor: '#EAF2F5',
    borderRadius: 8,
    marginBottom: 12,
    marginHorizontal: 16,
    padding: 12,
  },
  privacyTitle: {
    color: '#1F4E5F',
    fontSize: 13,
    fontWeight: '700',
    marginBottom: 6,
  },
  privacyLine: {
    color: '#1F4E5F',
    fontSize: 12,
    lineHeight: 18,
  },
  primaryButton: {
    alignItems: 'center',
    backgroundColor: '#0B6E99',
    borderRadius: 8,
    marginBottom: 12,
    marginHorizontal: 16,
    paddingVertical: 10,
  },
  primaryButtonText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '700',
  },
  list: {
    paddingBottom: 32,
    paddingHorizontal: 16,
  },
  row: {
    borderBottomColor: '#D7DEE4',
    borderBottomWidth: StyleSheet.hairlineWidth,
    paddingVertical: 10,
  },
  rowTitle: {
    color: '#111827',
    fontSize: 14,
    fontWeight: '700',
  },
  rowDetail: {
    color: '#607080',
    fontFamily: 'Menlo',
    fontSize: 12,
    marginTop: 3,
  },
  empty: {
    color: '#8A96A3',
    fontSize: 13,
    marginTop: 32,
    textAlign: 'center',
  },
});
