import React from 'react';
import { act, create } from 'react-test-renderer';
import type { RegionClimateOverview } from '../../../types/region.types';

jest.mock('react-native-gesture-handler', () => {
  const React = require('react');
  const { View } = require('react-native');
  const Swipeable = React.forwardRef(
    ({ children, renderRightActions }: any, ref: any) => {
      React.useImperativeHandle(ref, () => ({ close: () => {} }));

      return (
        <View testID="swipeable">
          {children}
          {renderRightActions && (
            <View testID="right-actions">{renderRightActions()}</View>
          )}
        </View>
      );
    },
  );

  Swipeable.displayName = 'Swipeable';

  return {
    Swipeable,
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

const makeClimate = (
  overrides: Partial<RegionClimateOverview> = {},
): RegionClimateOverview => ({
  primary: {
    layer: 'temperature',
    name: '2m Temperature',
    value: 24,
    unit: '°C',
    category: 'Moderate',
  },
  secondary: [],
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
        climate={null}
        isClimateLoading={false}
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

  it('shows no data when climate is unavailable', () => {
    const tree = create(
      <FavoriteLocationCard
        favorite={makeFavorite()}
        climate={null}
        isClimateLoading={false}
        onPress={onPress}
        onDelete={onDelete}
      />,
    );
    const texts = tree.root.findAllByType('Text' as any);
    const badge = texts.find((t: any) => {
      try {
        return t.props.children === 'No data';
      } catch {
        return false;
      }
    });
    expect(badge).toBeDefined();
  });

  it('shows loading state while climate data is fetching', () => {
    const tree = create(
      <FavoriteLocationCard
        favorite={makeFavorite()}
        climate={null}
        isClimateLoading={true}
        onPress={onPress}
        onDelete={onDelete}
      />,
    );
    const texts = tree.root.findAllByType('Text' as any);
    const loadingText = texts.find((t: any) => {
      try {
        return t.props.children === 'Loading...';
      } catch {
        return false;
      }
    });
    expect(loadingText).toBeDefined();
  });

  it('shows category and temperature when climate data is available', () => {
    const tree = create(
      <FavoriteLocationCard
        favorite={makeFavorite()}
        climate={makeClimate()}
        isClimateLoading={false}
        onPress={onPress}
        onDelete={onDelete}
      />,
    );
    const texts = tree.root.findAllByType('Text' as any);
    const categoryText = texts.find((t: any) => {
      try {
        return t.props.children === 'Moderate';
      } catch {
        return false;
      }
    });
    const temperatureText = texts.find((t: any) => {
      try {
        return t.props.children === '24 °C';
      } catch {
        return false;
      }
    });
    expect(categoryText).toBeDefined();
    expect(temperatureText).toBeDefined();
  });

  it('calls onPress when card is pressed', () => {
    const tree = create(
      <FavoriteLocationCard
        favorite={makeFavorite()}
        climate={null}
        isClimateLoading={false}
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
        climate={null}
        isClimateLoading={false}
        onPress={onPress}
        onDelete={onDelete}
      />,
    );
    const deleteButton = tree.root.findAllByProps({
      accessibilityLabel: 'Delete favorite Sunnybank Hills',
    });
    expect(deleteButton.length).toBeGreaterThan(0);
  });

  it('renders formatted date timestamp', () => {
    const knownDate = new Date('2026-03-31T10:00:00.000Z').toISOString();
    const tree = create(
      <FavoriteLocationCard
        favorite={makeFavorite({ timestamp: knownDate })}
        climate={null}
        isClimateLoading={false}
        onPress={onPress}
        onDelete={onDelete}
      />,
    );
    const texts = tree.root.findAllByType('Text' as any);
    // Date is rendered as "31 Mar 2026" (en-AU locale via toLocaleDateString).
    // The exact string may vary slightly by environment; check for the year.
    const dateText = texts.find((t: any) => {
      try {
        return typeof t.props.children === 'string' && t.props.children.includes('2026');
      } catch {
        return false;
      }
    });
    expect(dateText).toBeDefined();
  });
});
