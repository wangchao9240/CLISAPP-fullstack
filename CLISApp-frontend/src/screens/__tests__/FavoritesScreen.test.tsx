import React from 'react';
import { act, create, ReactTestRenderer } from 'react-test-renderer';

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

jest.mock('react-native-vector-icons/MaterialIcons', () => {
  const { Text } = require('react-native');
  return ({ name, ...props }: any) => <Text {...props}>{name}</Text>;
});

jest.mock('react-native-paper', () => {
  const { View, Text: RNText } = require('react-native');
  return {
    Snackbar: ({ visible, children, action, onDismiss }: any) =>
      visible ? (
        <View testID="snackbar">
          <RNText>{children}</RNText>
          {action && (
            <RNText testID="snackbar-action" onPress={action.onPress}>
              {action.label}
            </RNText>
          )}
        </View>
      ) : null,
  };
});

const mockRemoveFavorite = jest.fn();
const mockRestoreFavorite = jest.fn();
let mockFavorites: any[] = [];

jest.mock('../../store/favoritesStore', () => ({
  useFavoritesStore: (selector: any) =>
    selector({
      favorites: mockFavorites,
      removeFavorite: mockRemoveFavorite,
      restoreFavorite: mockRestoreFavorite,
    }),
}));

const mockSetRegion = jest.fn();
const mockSetSelectedRegion = jest.fn();
const mockSetRegionInfoLoading = jest.fn();
const mockSetRegionInfoError = jest.fn();
const mockOpenRegionInfo = jest.fn();
const mockSetRegionBoundary = jest.fn();

jest.mock('../../store/mapStore', () => ({
  useMapStore: {
    getState: () => ({
      setRegion: mockSetRegion,
      setSelectedRegion: mockSetSelectedRegion,
      setRegionInfoLoading: mockSetRegionInfoLoading,
      setRegionInfoError: mockSetRegionInfoError,
      openRegionInfo: mockOpenRegionInfo,
      setRegionBoundary: mockSetRegionBoundary,
      activeLayer: 'pm25',
    }),
  },
}));

jest.mock('../../services/ApiService', () => ({
  apiService: {
    getRegionInfo: jest.fn().mockResolvedValue({
      success: true,
      data: {
        id: 'ssc-123',
        name: 'Sunnybank Hills',
        type: 'ssc',
        location: { latitude: -27.6, longitude: 153.05 },
        current_climate: {},
      },
    }),
  },
}));

jest.mock('../../hooks/useApi', () => ({
  formatClimateOverview: jest.fn().mockReturnValue({ primary: null, secondary: [] }),
}));

jest.mock('../../services/boundaries/boundaryLoader', () => ({
  loadRegionBoundary: jest.fn().mockResolvedValue(null),
}));

const { apiService } =
  require('../../services/ApiService') as typeof import('../../services/ApiService');
const { formatClimateOverview } =
  require('../../hooks/useApi') as typeof import('../../hooks/useApi');
const { FavoritesScreen } = require('../FavoritesScreen');

const makeFavorite = (overrides: Record<string, any> = {}) => ({
  regionId: 'ssc-123',
  regionName: 'Sunnybank Hills',
  regionType: 'ssc',
  latitude: -27.6,
  longitude: 153.05,
  timestamp: new Date().toISOString(),
  ...overrides,
});

describe('FavoritesScreen', () => {
  const onNavigateToMap = jest.fn();
  const climateOverview = {
    primary: {
      layer: 'temperature',
      name: '2m Temperature',
      value: 24,
      unit: '°C',
      category: 'Moderate',
    },
    secondary: [],
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockFavorites = [];
    (apiService.getRegionInfo as jest.Mock).mockResolvedValue({
      success: true,
      data: {
        id: 'ssc-123',
        name: 'Sunnybank Hills',
        type: 'ssc',
        location: { latitude: -27.6, longitude: 153.05 },
        current_climate: {
          temperature: {
            layer: 'temperature',
            value: 24,
            unit: '°C',
            category: 'Moderate',
            timestamp: '2026-03-31T00:00:00Z',
          },
        },
      },
    });
    (formatClimateOverview as jest.Mock).mockReturnValue(climateOverview);
  });

  const flushClimateRequests = async () => {
    await Promise.resolve();
    await Promise.resolve();
  };

  const renderScreen = async () => {
    let tree: ReactTestRenderer;

    await act(async () => {
      tree = create(
        <FavoritesScreen onNavigateToMap={onNavigateToMap} />,
      );
      await flushClimateRequests();
    });

    return tree!;
  };

  it('renders empty state when no favorites', async () => {
    mockFavorites = [];
    const tree = await renderScreen();
    const texts = tree.root.findAllByType('Text' as any);
    const emptyTitle = texts.find((t: any) => {
      try {
        return t.props.children === 'No Favorites Yet';
      } catch {
        return false;
      }
    });
    expect(emptyTitle).toBeDefined();
  });

  it('renders empty state hint text', async () => {
    mockFavorites = [];
    const tree = await renderScreen();
    const texts = tree.root.findAllByType('Text' as any);
    const hint = texts.find((t: any) => {
      try {
        return (
          typeof t.props.children === 'string' &&
          t.props.children.includes('Tap the heart icon')
        );
      } catch {
        return false;
      }
    });
    expect(hint).toBeDefined();
  });

  it('renders Open Map button in empty state', async () => {
    mockFavorites = [];
    const tree = await renderScreen();
    const texts = tree.root.findAllByType('Text' as any);
    const openMap = texts.find((t: any) => {
      try {
        return t.props.children === 'Open Map';
      } catch {
        return false;
      }
    });
    expect(openMap).toBeDefined();
  });

  it('renders cards when favorites exist', async () => {
    mockFavorites = [
      makeFavorite({ regionId: 'ssc-1', regionName: 'Sunnybank' }),
      makeFavorite({ regionId: 'ssc-2', regionName: 'Brisbane CBD' }),
    ];
    const tree = await renderScreen();
    const texts = tree.root.findAllByType('Text' as any);
    const sunnybank = texts.find((t: any) => {
      try {
        return t.props.children === 'Sunnybank';
      } catch {
        return false;
      }
    });
    const brisbane = texts.find((t: any) => {
      try {
        return t.props.children === 'Brisbane CBD';
      } catch {
        return false;
      }
    });
    expect(sunnybank).toBeDefined();
    expect(brisbane).toBeDefined();
  });

  it('fetches climate data for favorites and renders it on the cards', async () => {
    mockFavorites = [makeFavorite()];
    const tree = await renderScreen();

    expect(apiService.getRegionInfo).toHaveBeenCalledWith('ssc-123', true);
    expect(formatClimateOverview).toHaveBeenCalledWith(
      {
        temperature: {
          layer: 'temperature',
          value: 24,
          unit: '°C',
          category: 'Moderate',
          timestamp: '2026-03-31T00:00:00Z',
        },
      },
      'temperature',
    );

    const texts = tree!.root.findAllByType('Text' as any);
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

  it('calls removeFavorite and shows Snackbar on delete', () => {
    const fav = makeFavorite();
    mockFavorites = [fav];
    let tree: ReactTestRenderer;
    return renderScreen().then((rendered) => {
      tree = rendered;
      const deleteButtons = tree.root.findAllByProps({
        accessibilityLabel: 'Delete favorite Sunnybank Hills',
      });
      expect(deleteButtons.length).toBeGreaterThan(0);
      act(() => {
        deleteButtons[0].props.onPress();
      });
      expect(mockRemoveFavorite).toHaveBeenCalledWith('ssc-123');
      const snackbar = tree.root.findAllByProps({ testID: 'snackbar' });
      expect(snackbar.length).toBeGreaterThan(0);
    });
  });

  it('restores favorite on Undo press', async () => {
    const fav = makeFavorite();
    mockFavorites = [fav];
    const tree = await renderScreen();
    const deleteButtons = tree.root.findAllByProps({
      accessibilityLabel: 'Delete favorite Sunnybank Hills',
    });
    act(() => {
      deleteButtons[0].props.onPress();
    });
    const undoButton = tree.root.findByProps({ testID: 'snackbar-action' });
    act(() => {
      undoButton.props.onPress();
    });
    expect(mockRestoreFavorite).toHaveBeenCalledWith(fav);
  });

  it('calls navigate to map on card press', async () => {
    const fav = makeFavorite();
    mockFavorites = [fav];
    const tree = await renderScreen();
    const cardButton = tree.root.findAllByProps({
      accessibilityLabel: 'View Sunnybank Hills on map',
    });
    expect(cardButton.length).toBeGreaterThan(0);
    await act(async () => {
      await cardButton[0].props.onPress();
    });
    expect(mockSetRegion).toHaveBeenCalled();
    expect(mockSetSelectedRegion).toHaveBeenCalledWith('ssc-123');
    expect(onNavigateToMap).toHaveBeenCalled();
  });

  it('does not navigate when favorite has no coordinates', async () => {
    const fav = makeFavorite({ latitude: undefined, longitude: undefined });
    mockFavorites = [fav];
    const tree = await renderScreen();
    const cardButton = tree.root.findAllByProps({
      accessibilityLabel: 'View Sunnybank Hills on map',
    });
    await act(async () => {
      await cardButton[0].props.onPress();
    });
    expect(mockSetRegion).not.toHaveBeenCalled();
    expect(onNavigateToMap).not.toHaveBeenCalled();
  });
});
