import React, { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Alert, Modal, Pressable } from 'react-native';
import { useMapStore } from '../../store/mapStore';
import { CLIMATE_LAYERS } from '../../constants/climateData';
import { ClimateLayer } from '../../types/climate.types';

export const LAYERS: Array<{ key: ClimateLayer; label: string; emoji: string; available: boolean }> = [
  { key: 'pm25', label: 'PM2.5', emoji: '💨', available: true },
  { key: 'precipitation', label: 'Precipitation', emoji: '🌧️', available: true },
  { key: 'uv', label: 'UV Index', emoji: '☀️', available: true },
  { key: 'humidity', label: 'Humidity', emoji: '💧', available: true },
  { key: 'temperature', label: 'Temperature', emoji: '🌡️', available: true },
];

export const LayerSelector: React.FC<{ style?: any; onSelected?: () => void }> = ({ style, onSelected }) => {
  const { activeLayer, setActiveLayer } = useMapStore();
  const [menuVisible, setMenuVisible] = useState(false);

  const currentLayer = LAYERS.find(l => l.key === activeLayer) || LAYERS[0];

  const onSelect = (key: ClimateLayer, available: boolean) => {
    if (!available) {
      Alert.alert('Notice', 'This data dimension is coming soon');
      return;
    }
    setActiveLayer(key as any);
    setMenuVisible(false);
    onSelected?.();
  };

  return (
    <View style={[styles.container, style]}>
      {/* Current Layer Button */}
      <TouchableOpacity 
        style={styles.layerButton}
        onPress={() => setMenuVisible(!menuVisible)}
      >
        <Text style={styles.emoji}>{currentLayer.emoji}</Text>
        <Text style={styles.dropdownIcon}>▼</Text>
      </TouchableOpacity>

      {/* Dropdown Menu */}
      {menuVisible && (
        <>
          <Pressable 
            style={styles.overlay} 
            onPress={() => setMenuVisible(false)}
          />
          <View style={styles.menu}>
            {LAYERS.map(item => (
              <TouchableOpacity 
                key={item.key} 
                onPress={() => onSelect(item.key, item.available)} 
                style={[
                  styles.menuItem,
                  item.key === activeLayer && styles.activeItem
                ]}
              >
                <Text style={styles.menuEmoji}>{item.emoji}</Text>
                <Text style={[styles.menuLabel, item.key === activeLayer && styles.activeLabel]}>
                  {item.label}
                </Text>
                {item.key === activeLayer && <Text style={styles.checkmark}>✓</Text>}
                {!item.available && <Text style={styles.comingSoon}>(soon)</Text>}
              </TouchableOpacity>
            ))}
          </View>
        </>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    position: 'relative',
    zIndex: 1000,
  },
  layerButton: {
    width: 72,
    height: 56,
    backgroundColor: 'rgba(255, 255, 255, 0.95)',
    borderRadius: 16,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    borderWidth: 1,
    borderColor: 'rgba(0, 0, 0, 0.05)',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 4,
    elevation: 2,
  },
  emoji: {
    fontSize: 16,
  },
  dropdownIcon: {
    fontSize: 10,
    color: '#0A0A0A',
    opacity: 0.6,
  },
  overlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    width: 1000,
    height: 1000,
    marginLeft: -500,
    marginTop: -500,
  },
  menu: {
    position: 'absolute',
    top: 64,
    right: 0,
    backgroundColor: 'rgba(255, 255, 255, 0.98)',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: 'rgba(0, 0, 0, 0.1)',
    minWidth: 180,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 8,
    elevation: 5,
    overflow: 'hidden',
  },
  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    paddingHorizontal: 16,
    gap: 12,
  },
  activeItem: {
    backgroundColor: 'rgba(0, 122, 255, 0.05)',
  },
  menuEmoji: {
    fontSize: 18,
  },
  menuLabel: {
    flex: 1,
    fontSize: 14,
    color: '#0A0A0A',
  },
  activeLabel: {
    fontWeight: '600',
    color: '#007AFF',
  },
  checkmark: {
    fontSize: 16,
    color: '#007AFF',
    fontWeight: 'bold',
  },
  comingSoon: {
    fontSize: 11,
    color: '#999',
  },
});
