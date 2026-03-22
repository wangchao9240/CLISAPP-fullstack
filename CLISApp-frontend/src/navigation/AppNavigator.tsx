import React, { useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { BottomNavigation } from 'react-native-paper';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { MapScreen } from '../screens/MapScreen';
import { FavoritesScreen } from '../screens/FavoritesScreen';

export const AppNavigator: React.FC = () => {
  const [index, setIndex] = useState(0);
  const [routes] = useState([
    { key: 'map', title: 'Map', focusedIcon: 'map', unfocusedIcon: 'map' },
    { key: 'favorites', title: 'Favorites', focusedIcon: 'favorite', unfocusedIcon: 'favorite-outline' },
  ]);

  const isMapTab = index === 0;

  const renderIcon = ({ route, focused, color }: { route: { key: string; focusedIcon: string; unfocusedIcon: string }; focused: boolean; color: string }) => {
    const iconName = focused ? route.focusedIcon : route.unfocusedIcon;
    return <Icon name={iconName} size={24} color={color} />;
  };

  return (
    <View style={styles.container}>
      {/* Keep both scenes mounted for state preservation */}
      <View style={[styles.sceneContainer, !isMapTab && styles.hidden]}>
        <MapScreen isActive={isMapTab} />
      </View>
      <View style={[styles.sceneContainer, isMapTab && styles.hidden]}>
        <FavoritesScreen onNavigateToMap={() => setIndex(0)} />
      </View>
      <BottomNavigation.Bar
        navigationState={{ index, routes }}
        onTabPress={({ route }) => {
          const newIndex = routes.findIndex(r => r.key === route.key);
          if (newIndex >= 0) { setIndex(newIndex); }
        }}
        renderIcon={renderIcon}
        activeColor="#1976D2"
        inactiveColor="#757575"
        activeIndicatorStyle={styles.activeIndicator}
        style={styles.bottomBar}
        labeled={true}
        getLabelText={({ route }) => route.title}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  sceneContainer: {
    flex: 1,
  },
  hidden: {
    display: 'none',
  },
  bottomBar: {
    height: 80,
    backgroundColor: '#FFFFFF',
    borderTopWidth: 1,
    borderTopColor: '#E0E0E0',
  },
  activeIndicator: {
    backgroundColor: '#E3F2FD',
  },
});
