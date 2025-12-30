import React, { useMemo } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { CLIMATE_LAYERS } from '../../constants/climateData';
import { useMapStore } from '../../store/mapStore';
import { useDynamicThreshold } from '../../hooks/useDynamicThreshold';

interface LegendProps {
  layer?: keyof typeof CLIMATE_LAYERS;
  style?: any;
}

export const Legend: React.FC<LegendProps> = ({ layer, style }) => {
  const { activeLayer } = useMapStore();
  const key = (layer ?? activeLayer) as keyof typeof CLIMATE_LAYERS;

  const config = CLIMATE_LAYERS[key];
  const dynamicThresholds = useDynamicThreshold(key === 'precipitation' ? 'precipitation' : 'pm25');
  const thresholds = useMemo(() => {
    if ((key === 'pm25' || key === 'precipitation') && dynamicThresholds.length === config.colorScale.length) {
      return dynamicThresholds;
    }
    return config.thresholds;
  }, [key, dynamicThresholds, config.thresholds, config.colorScale.length]);

  return (
    <View style={[styles.container, style]}> 
      <Text style={styles.title}>{config.name}</Text>
      <View style={styles.rows}>
        {thresholds.map((t: number, idx: number) => {
          const next = thresholds[idx + 1];
          const label = next !== undefined ? `${t}–${next} ${config.unit}` : `${t}+ ${config.unit}`;
          const color = config.colorScale[Math.min(idx, config.colorScale.length - 1)];
          return (
            <View key={`${key}-${idx}`} style={styles.row}>
              <View style={[styles.swatch, { backgroundColor: color }]} />
              <Text style={styles.label}>{label}</Text>
            </View>
          );
        })}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: 'rgba(255,255,255,0.95)',
    padding: 10,
    borderRadius: 8,
    minWidth: 160,
    maxWidth: 220,
  },
  title: {
    fontSize: 12,
    fontWeight: '600',
    marginBottom: 6,
    color: '#333',
  },
  rows: {
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    marginVertical: 2,
  },
  swatch: {
    width: 16,
    height: 10,
    borderRadius: 2,
    marginRight: 8,
  },
  label: {
    fontSize: 11,
    color: '#444',
  },
});
