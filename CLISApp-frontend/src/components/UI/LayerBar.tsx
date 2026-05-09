import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Platform } from 'react-native';
import { useMapStore } from '../../store/mapStore';
import { ClimateLayer } from '../../types/climate.types';
import { PALETTE, RADII } from '../../constants/designTokens';

const LAYERS: ReadonlyArray<{ key: ClimateLayer; label: string }> = [
  { key: 'pm25', label: 'PM2.5' },
  { key: 'uv', label: 'UV' },
  { key: 'temperature', label: 'Temp' },
  { key: 'humidity', label: 'Humidity' },
  { key: 'precipitation', label: 'Precip' },
] as const;

interface LayerBarProps {
  visible?: boolean;
}

export const LayerBar: React.FC<LayerBarProps> = ({ visible = true }) => {
  const { activeLayer, setActiveLayer } = useMapStore();

  if (!visible) {
    return null;
  }

  return (
    <View style={styles.container}>
      <View style={styles.card}>
        {LAYERS.map((layer) => {
          const isActive = activeLayer === layer.key;
          return (
            <TouchableOpacity
              key={layer.key}
              style={[styles.chip, isActive ? styles.chipActive : styles.chipInactive]}
              onPress={() => setActiveLayer(layer.key as any)}
              accessibilityRole="button"
              accessibilityState={{ selected: isActive }}
              accessibilityLabel={`${layer.label} layer`}
            >
              <Text style={[styles.chipText, isActive ? styles.chipTextActive : styles.chipTextInactive]}>
                {layer.label}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    bottom: 12,
    left: 0,
    right: 0,
    alignItems: 'center',
    paddingHorizontal: 16,
    zIndex: 1000,
    elevation: 1000,
    pointerEvents: 'box-none',
  },
  card: {
    flexDirection: 'row',
    backgroundColor: PALETTE.surface,
    borderRadius: RADII.card,
    padding: 7,
    borderWidth: 1,
    borderColor: PALETTE.border,
    gap: 4,
    ...Platform.select({
      ios: {
        shadowColor: '#0D1220',
        shadowOpacity: 0.10,
        shadowOffset: { width: 0, height: 12 },
        shadowRadius: 16,
      },
      android: {
        elevation: 2,
      },
    }),
    pointerEvents: 'auto',
  },
  chip: {
    flex: 1,
    borderRadius: RADII.chip,
    paddingVertical: 9,
    paddingHorizontal: 6,
    justifyContent: 'center',
    alignItems: 'center',
  },
  chipActive: {
    backgroundColor: PALETTE.fg,
  },
  chipInactive: {
    backgroundColor: 'transparent',
  },
  chipText: {
    fontSize: 12.5,
    fontWeight: '500',
    letterSpacing: -0.0625,
  },
  chipTextActive: {
    color: '#FFFFFF',
    fontWeight: '600',
  },
  chipTextInactive: {
    color: PALETTE.muted,
  },
});
