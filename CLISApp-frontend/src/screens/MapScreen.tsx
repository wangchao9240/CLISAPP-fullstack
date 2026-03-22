// Main map screen implementing FR-001 and FR-002
import React, { useState, useEffect, useCallback } from 'react';
import { StyleSheet, View, StatusBar, TouchableOpacity, Image, Alert, Platform, BackHandler } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { UniversalMap } from '../components/Map/UniversalMap';
import Geolocation from 'react-native-geolocation-service';
import { check, request, PERMISSIONS, RESULTS } from 'react-native-permissions';

import { Legend } from '../components/UI/Legend';
import { RegionSearchBar } from '../components/UI/RegionSearchBar';
import { LayerBar } from '../components/UI/LayerBar';
import { useMapStore } from '../store/mapStore';

interface MapScreenProps {
  isActive?: boolean;
}

export const MapScreen: React.FC<MapScreenProps> = ({ isActive = true }) => {
  const [legendVisible, setLegendVisible] = useState(false);
  const [locating, setLocating] = useState(false);
  const { setRegion, regionInfo, closeRegionInfo } = useMapStore();

  // Close sheet when tab becomes inactive (fixes sheet leak to other tabs)
  useEffect(() => {
    if (!isActive && regionInfo.visible) {
      closeRegionInfo();
    }
  }, [isActive, regionInfo.visible, closeRegionInfo]);

  // Android back button handling (AC #5, #6)
  const handleBackPress = useCallback(() => {
    if (!isActive) {
      return false; // Don't consume back press when tab is hidden
    }
    // If region info panel is open, close it first
    if (regionInfo.visible) {
      closeRegionInfo();
      return true;
    }
    // If legend popup is open, close it
    if (legendVisible) {
      setLegendVisible(false);
      return true;
    }
    // Nothing open, let system handle (exits app)
    return false;
  }, [isActive, regionInfo.visible, legendVisible, closeRegionInfo]);

  useEffect(() => {
    if (Platform.OS !== 'android' || !isActive) {
      return;
    }
    const subscription = BackHandler.addEventListener('hardwareBackPress', handleBackPress);
    return () => subscription.remove();
  }, [isActive, handleBackPress]);

  const requestLocationPermission = async () => {
    try {
      const permission = Platform.select({
        ios: PERMISSIONS.IOS.LOCATION_WHEN_IN_USE,
        android: PERMISSIONS.ANDROID.ACCESS_FINE_LOCATION,
      });

      if (!permission) {
        Alert.alert('Error', 'Platform not supported');
        return false;
      }

      const result = await check(permission);

      if (result === RESULTS.GRANTED) {
        return true;
      }

      if (result === RESULTS.DENIED) {
        const requestResult = await request(permission);
        return requestResult === RESULTS.GRANTED;
      }

      if (result === RESULTS.BLOCKED) {
        Alert.alert(
          'Location Permission',
          'Location permission is blocked. Please enable it in your device settings.',
          [{ text: 'OK' }]
        );
        return false;
      }

      return false;
    } catch (error) {
      console.error('Error requesting location permission:', error);
      return false;
    }
  };

  const handleLocateMe = async () => {
    if (locating) return;

    setLocating(true);

    try {
      const hasPermission = await requestLocationPermission();

      if (!hasPermission) {
        setLocating(false);
        return;
      }

      Geolocation.getCurrentPosition(
        (position) => {
          const { latitude, longitude } = position.coords;

          setRegion({
            latitude,
            longitude,
            latitudeDelta: 0.05,
            longitudeDelta: 0.05,
          });

          setLocating(false);
        },
        (error) => {
          console.error('Location error:', error);
          Alert.alert(
            'Location Error',
            'Unable to get your current location. Please make sure location services are enabled.',
            [{ text: 'OK' }]
          );
          setLocating(false);
        },
        {
          enableHighAccuracy: true,
          timeout: 15000,
          maximumAge: 10000,
        }
      );
    } catch (error) {
      console.error('Error getting location:', error);
      Alert.alert('Error', 'Failed to get your location');
      setLocating(false);
    }
  };

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <StatusBar barStyle="dark-content" backgroundColor="#fff" />

      <View style={styles.mapContainer}>
        <UniversalMap />

        {/* Map controls overlay */}
        <View style={styles.controlsOverlay}>
          {/* Top Bar: Full-width Search Bar */}
          <View style={styles.topBar}>
            <RegionSearchBar style={styles.searchBar} />
          </View>

          {/* Right side controls */}
          <View style={styles.rightControls}>
            {/* Locate Me Button */}
            <TouchableOpacity
              style={[styles.controlButton, locating && styles.controlButtonActive]}
              onPress={handleLocateMe}
              disabled={locating}
            >
              <Image
                source={require('../assets/img/locate.png')}
                style={[styles.controlIcon, locating && styles.controlIconActive]}
                resizeMode="contain"
              />
            </TouchableOpacity>
          </View>

          {/* Bottom Left: Legend Toggle */}
          <View style={styles.bottomLeftControls}>
            <View style={styles.legendContainer}>
              {legendVisible && (
                <View style={styles.legendPopup}>
                  <Legend layer={undefined as any} />
                </View>
              )}
              <TouchableOpacity
                style={styles.controlButton}
                onPress={() => setLegendVisible(!legendVisible)}
              >
                <View style={styles.plusIcon}>
                  <View style={styles.plusHorizontal} />
                  <View style={styles.plusVertical} />
                </View>
              </TouchableOpacity>
            </View>
          </View>
        </View>

        {/* Layer Bar - above bottom nav */}
        <LayerBar visible={isActive} />
      </View>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  mapContainer: {
    flex: 1,
    position: 'relative',
  },
  controlsOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    pointerEvents: 'box-none',
  },
  topBar: {
    position: 'absolute',
    top: 16,
    left: 16,
    right: 16,
    pointerEvents: 'box-none',
  },
  searchBar: {
    pointerEvents: 'auto',
  },
  rightControls: {
    position: 'absolute',
    right: 16,
    bottom: 16,
    alignItems: 'center',
    gap: 12,
    pointerEvents: 'box-none',
  },
  bottomLeftControls: {
    position: 'absolute',
    left: 16,
    bottom: 16,
    pointerEvents: 'box-none',
  },
  controlButton: {
    width: 40,
    height: 40,
    backgroundColor: 'rgba(255, 255, 255, 0.95)',
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
    pointerEvents: 'auto',
  },
  controlButtonActive: {
    backgroundColor: 'rgba(0, 122, 255, 0.1)',
  },
  controlIcon: {
    width: 20,
    height: 20,
    tintColor: '#333',
  },
  controlIconActive: {
    tintColor: '#007AFF',
    opacity: 0.7,
  },
  legendContainer: {
    position: 'relative',
    pointerEvents: 'box-none',
  },
  legendPopup: {
    position: 'absolute',
    bottom: 52,
    left: 0,
    backgroundColor: 'rgba(255, 255, 255, 0.95)',
    borderRadius: 16,
    borderWidth: 1,
    borderColor: 'rgba(0, 0, 0, 0.05)',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 5,
    minWidth: 200,
    pointerEvents: 'auto',
  },
  plusIcon: {
    width: 20,
    height: 20,
    justifyContent: 'center',
    alignItems: 'center',
  },
  plusHorizontal: {
    position: 'absolute',
    width: 12,
    height: 2,
    backgroundColor: '#333',
    borderRadius: 1,
  },
  plusVertical: {
    position: 'absolute',
    width: 2,
    height: 12,
    backgroundColor: '#333',
    borderRadius: 1,
  },
});
