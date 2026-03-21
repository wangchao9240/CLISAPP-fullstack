import React from 'react';
import { View, Text, TouchableOpacity, ScrollView, StyleSheet } from 'react-native';
import { useMapStore } from '../../store/mapStore';
import { ClimateLayer } from '../../types/climate.types';

const LAYERS: ReadonlyArray<{ key: ClimateLayer; label: string }> = [
  { key: 'pm25', label: 'PM2.5' },
  { key: 'uv', label: 'UV' },
  { key: 'temperature', label: 'Temp' },
  { key: 'humidity', label: 'Humidity' },
  { key: 'precipitation', label: 'Precip' },
] as const;

export const LayerBar: React.FC = () => {
  const { activeLayer, setActiveLayer } = useMapStore();

  return (
    <View style={styles.container}>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.scrollContent}
      >
        {LAYERS.map((layer) => {
          const isActive = activeLayer === layer.key;
          return (
            <TouchableOpacity
              key={layer.key}
              style={[styles.pill, isActive ? styles.pillActive : styles.pillInactive]}
              onPress={() => setActiveLayer(layer.key as any)}
              accessibilityRole="button"
              accessibilityState={{ selected: isActive }}
              accessibilityLabel={`${layer.label} layer`}
            >
              <Text style={[styles.pillText, isActive ? styles.pillTextActive : styles.pillTextInactive]}>
                {layer.label}
              </Text>
            </TouchableOpacity>
          );
        })}
      </ScrollView>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    height: 56,
    backgroundColor: 'rgba(0,0,0,0.7)',
    justifyContent: 'center',
  },
  scrollContent: {
    paddingHorizontal: 16,
    alignItems: 'center',
    gap: 8,
  },
  pill: {
    height: 32,
    paddingHorizontal: 16,
    borderRadius: 9999,
    justifyContent: 'center',
    alignItems: 'center',
  },
  pillActive: {
    backgroundColor: '#FFFFFF',
  },
  pillInactive: {
    backgroundColor: 'transparent',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.4)',
  },
  pillText: {
    fontSize: 14,
    fontWeight: '500',
    letterSpacing: 0.5,
  },
  pillTextActive: {
    color: '#1E293B', // slate-900
  },
  pillTextInactive: {
    color: '#FFFFFF',
  },
});
