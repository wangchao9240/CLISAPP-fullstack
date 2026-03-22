import React, { useRef } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { Swipeable } from 'react-native-gesture-handler';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import type { FavoriteLocation } from '../../store/favoritesStore';

interface FavoriteLocationCardProps {
  favorite: FavoriteLocation;
  onPress: () => void;
  onDelete: () => void;
}

const formatRelativeTime = (isoTimestamp: string): string => {
  const saved = new Date(isoTimestamp).getTime();
  const now = Date.now();
  const diffMs = now - saved;

  const minutes = Math.floor(diffMs / 60_000);
  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;

  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;

  return new Date(isoTimestamp).toLocaleDateString();
};

const renderRightActions = (onDelete: () => void, regionName: string) => (
  <Pressable
    onPress={onDelete}
    style={styles.deleteAction}
    accessibilityRole="button"
    accessibilityLabel={`Delete favorite ${regionName}`}
  >
    <Icon name="delete" size={24} color="#FFFFFF" />
    <Text style={styles.deleteText}>Delete</Text>
  </Pressable>
);

export const FavoriteLocationCard: React.FC<FavoriteLocationCardProps> = ({
  favorite,
  onPress,
  onDelete,
}) => {
  const swipeableRef = useRef<Swipeable>(null);

  const handleDelete = () => {
    swipeableRef.current?.close();
    onDelete();
  };

  return (
    <Swipeable
      ref={swipeableRef}
      renderRightActions={() => renderRightActions(handleDelete, favorite.regionName)}
      overshootRight={false}
      friction={2}
    >
      <Pressable
        onPress={onPress}
        style={styles.card}
        accessibilityRole="button"
        accessibilityLabel={`View ${favorite.regionName} on map`}
      >
        <View style={styles.leftContent}>
          <Text style={styles.regionName} numberOfLines={1}>
            {favorite.regionName}
          </Text>
          <View style={styles.metaRow}>
            <View style={styles.healthDot} />
            <Text style={styles.healthLabel}>Data pending</Text>
            <View style={styles.separatorDot} />
            <Text style={styles.metaText}>
              {formatRelativeTime(favorite.timestamp)}
            </Text>
          </View>
        </View>
        <View style={styles.rightContent}>
          <Icon name="chevron-right" size={16} color="#BDBDBD" />
        </View>
      </Pressable>
    </Swipeable>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    minHeight: 88,
    marginHorizontal: 16,
    marginVertical: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 3,
    elevation: 1,
    borderWidth: 1,
    borderColor: 'rgba(193, 198, 212, 0.3)',
  },
  leftContent: {
    flex: 1,
    flexDirection: 'column',
    gap: 8,
  },
  regionName: {
    fontSize: 16,
    fontWeight: '500',
    color: '#181C21',
    lineHeight: 20,
  },
  metaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  healthDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#BDBDBD',
  },
  healthLabel: {
    fontSize: 11,
    fontWeight: '500',
    color: '#717783',
  },
  separatorDot: {
    width: 4,
    height: 4,
    borderRadius: 2,
    backgroundColor: '#717783',
  },
  metaText: {
    fontSize: 14,
    color: '#414752',
  },
  rightContent: {
    flexDirection: 'column',
    alignItems: 'flex-end',
    justifyContent: 'center',
    paddingLeft: 8,
  },
  deleteAction: {
    backgroundColor: '#E57373',
    justifyContent: 'center',
    alignItems: 'center',
    width: 80,
    flexDirection: 'column',
    gap: 4,
    borderTopRightRadius: 12,
    borderBottomRightRadius: 12,
    marginVertical: 4,
  },
  deleteText: {
    fontSize: 14,
    fontWeight: '500',
    color: '#FFFFFF',
  },
});
