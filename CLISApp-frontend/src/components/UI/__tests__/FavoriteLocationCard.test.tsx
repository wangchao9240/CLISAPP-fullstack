import React from 'react';
import { act, create } from 'react-test-renderer';

jest.mock('react-native-gesture-handler', () => {
  const { View } = require('react-native');
  return {
    Swipeable: ({ children, renderRightActions }: any) => (
      <View testID="swipeable">
        {children}
        {renderRightActions && (
          <View testID="right-actions">{renderRightActions()}</View>
        )}
      </View>
    ),
  };
});

jest.mock('react-native-vector-icons/MaterialCommunityIcons', () => {
  const { Text } = require('react-native');
  return ({ name, ...props }: any) => <Text {...props}>{name}</Text>;
});

const { FavoriteLocationCard } =
  require('../FavoriteLocationCard') as typeof import('../FavoriteLocationCard');

const makeFavorite = (overrides: Record<string, any> = {}) => ({
  regionId: 'ssc-123',
  regionName: 'Sunnybank Hills',
  regionType: 'ssc' as const,
  latitude: -27.6,
  longitude: 153.05,
  timestamp: new Date().toISOString(),
  ...overrides,
});

describe('FavoriteLocationCard', () => {
  const onPress = jest.fn();
  const onDelete = jest.fn();

  beforeEach(() => jest.clearAllMocks());

  it('renders region name', () => {
    const tree = create(
      <FavoriteLocationCard
        favorite={makeFavorite()}
        onPress={onPress}
        onDelete={onDelete}
      />,
    );
    const texts = tree.root.findAllByType('Text' as any);
    const nameText = texts.find((t: any) => {
      try {
        return t.props.children === 'Sunnybank Hills';
      } catch {
        return false;
      }
    });
    expect(nameText).toBeDefined();
  });

  it('renders placeholder health label', () => {
    const tree = create(
      <FavoriteLocationCard
        favorite={makeFavorite()}
        onPress={onPress}
        onDelete={onDelete}
      />,
    );
    const texts = tree.root.findAllByType('Text' as any);
    const badge = texts.find((t: any) => {
      try {
        return t.props.children === 'Data pending';
      } catch {
        return false;
      }
    });
    expect(badge).toBeDefined();
  });

  it('calls onPress when card is pressed', () => {
    const tree = create(
      <FavoriteLocationCard
        favorite={makeFavorite()}
        onPress={onPress}
        onDelete={onDelete}
      />,
    );
    const pressable = tree.root.findAllByProps({ accessibilityRole: 'button' })[0];
    act(() => {
      pressable.props.onPress();
    });
    expect(onPress).toHaveBeenCalledTimes(1);
  });

  it('renders delete action in swipeable', () => {
    const tree = create(
      <FavoriteLocationCard
        favorite={makeFavorite()}
        onPress={onPress}
        onDelete={onDelete}
      />,
    );
    const deleteButton = tree.root.findAllByProps({
      accessibilityLabel: 'Delete favorite Sunnybank Hills',
    });
    expect(deleteButton.length).toBeGreaterThan(0);
  });

  it('renders relative timestamp', () => {
    const twoHoursAgo = new Date(Date.now() - 2 * 60 * 60_000).toISOString();
    const tree = create(
      <FavoriteLocationCard
        favorite={makeFavorite({ timestamp: twoHoursAgo })}
        onPress={onPress}
        onDelete={onDelete}
      />,
    );
    const texts = tree.root.findAllByType('Text' as any);
    const timeText = texts.find((t: any) => {
      try {
        return typeof t.props.children === 'string' && t.props.children.includes('2h ago');
      } catch {
        return false;
      }
    });
    expect(timeText).toBeDefined();
  });
});
