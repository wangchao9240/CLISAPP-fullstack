import React from 'react';
import type { RegionClimateOverview } from '../../../types/region.types';
import { act, create } from 'react-test-renderer';

let mockMapState: any;

jest.mock('../../../store/mapStore', () => ({
  useMapStore: jest.fn(() => mockMapState),
}));

jest.mock('../../../store/favoritesStore', () => ({
  useFavoritesStore: jest.fn(),
}));

jest.mock('@gorhom/bottom-sheet', () => {
  const React = require('react');

  const BottomSheetModal = React.forwardRef((props: any, ref: any) => {
    React.useImperativeHandle(ref, () => ({
      present: jest.fn(),
      dismiss: jest.fn(),
    }));

    return <>{props.children}</>;
  });

  return {
    BottomSheetModal,
    BottomSheetScrollView: ({ children }: any) => <>{children}</>,
    BottomSheetBackdrop: () => null,
  };
});

jest.mock('react-native-paper', () => {
  const React = require('react');

  return {
    ActivityIndicator: (props: any) => React.createElement('ActivityIndicator', props),
    Snackbar: (props: any) => React.createElement('Snackbar', props, props.children),
  };
});

jest.mock('react-native-vector-icons/MaterialCommunityIcons', () => {
  const { Text } = require('react-native');
  return ({ name, ...props }: any) => <Text {...props}>{name}</Text>;
});

jest.mock('../../UI/ClimateChangeIndicator', () => ({
  ClimateChangeIndicator: () => null,
}));

const { useMapStore } = require('../../../store/mapStore') as typeof import('../../../store/mapStore');
const { useFavoritesStore } =
  require('../../../store/favoritesStore') as typeof import('../../../store/favoritesStore');
const { HealthBottomSheet } =
  require('../HealthBottomSheet') as typeof import('../HealthBottomSheet');

const mockUseMapStore = useMapStore as jest.Mock;
const mockUseFavoritesStore = useFavoritesStore as jest.Mock;

const makeClimate = (): RegionClimateOverview => ({
  primary: {
    layer: 'pm25',
    name: 'PM2.5 Concentration',
    value: 35,
    unit: 'µg/m³',
    category: 'Moderate',
    riskLevel: 'Unhealthy',
    advice: 'Everyone should reduce outdoor activity.',
    lastUpdated: '2026-03-17T12:00:00Z',
  },
  secondary: [
    {
      layer: 'uv',
      name: 'UV Index',
      value: 2,
      unit: 'UVI',
      category: 'Low',
      riskLevel: 'Good',
      advice: 'Enjoy outdoor activity as usual.',
      lastUpdated: '2026-03-17T12:00:00Z',
    },
  ],
});

const getTextNode = (renderer: ReturnType<typeof create>, expectedText: string) =>
  renderer.root.findAllByType('Text' as any).find((node) => node.props.children === expectedText);

const getBadgeNode = (renderer: ReturnType<typeof create>) =>
  renderer.root.find(
    (node) => node.props.testID === 'health-risk-badge' && Array.isArray(node.props.style),
  );

describe('HealthBottomSheet', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
    mockUseMapStore.mockImplementation(() => mockMapState);
    (mockUseMapStore as any).getState = jest.fn(() => mockMapState);
    mockUseFavoritesStore.mockReturnValue({
      isFavorite: jest.fn(() => false),
      addFavorite: jest.fn(),
      removeFavorite: jest.fn(),
      restoreFavorite: jest.fn(),
      getFavorite: jest.fn(),
    });
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });

  it('renders the health risk badge and advice for an Unhealthy PM2.5 reading', () => {
    mockMapState = {
      regionInfo: {
        visible: true,
        regionId: 'ssc_10001',
        regionName: 'Alpha Plains',
        regionType: 'ssc',
        latitude: -27.5,
        longitude: 153.0,
        climate: makeClimate(),
        loading: false,
        error: null,
      },
      activeLayer: 'pm25',
      closeRegionInfo: jest.fn(),
      clearRegionInfo: jest.fn(),
    };

    const renderer = create(<HealthBottomSheet />);

    expect(getTextNode(renderer, 'Unhealthy')).toBeDefined();
    expect(getTextNode(renderer, 'Everyone should reduce outdoor activity.')).toBeDefined();
    expect(getBadgeNode(renderer).props.accessibilityLabel).toBe(
      'Unhealthy air/health risk. Everyone should reduce outdoor activity.',
    );

    renderer.unmount();
  });

  it('updates the badge and advice when the active layer changes', () => {
    mockMapState = {
      regionInfo: {
        visible: true,
        regionId: 'ssc_10001',
        regionName: 'Alpha Plains',
        regionType: 'ssc',
        latitude: -27.5,
        longitude: 153.0,
        climate: makeClimate(),
        loading: false,
        error: null,
      },
      activeLayer: 'pm25',
      closeRegionInfo: jest.fn(),
      clearRegionInfo: jest.fn(),
    };

    const renderer = create(<HealthBottomSheet />);

    mockMapState = {
      ...mockMapState,
      activeLayer: 'uv',
    };

    act(() => {
      renderer.update(<HealthBottomSheet />);
    });

    expect(getTextNode(renderer, 'Good')).toBeDefined();
    expect(getTextNode(renderer, 'Enjoy outdoor activity as usual.')).toBeDefined();
    expect(getBadgeNode(renderer).props.accessibilityLabel).toBe(
      'Good air/health risk. Enjoy outdoor activity as usual.',
    );

    renderer.unmount();
  });

  it('renders the loading fallback without throwing when climate data is unavailable', () => {
    mockMapState = {
      regionInfo: {
        visible: true,
        regionId: 'ssc_10001',
        regionName: 'Alpha Plains',
        regionType: 'ssc',
        latitude: -27.5,
        longitude: 153.0,
        climate: null,
        loading: true,
        error: null,
      },
      activeLayer: 'pm25',
      closeRegionInfo: jest.fn(),
      clearRegionInfo: jest.fn(),
    };

    const renderer = create(<HealthBottomSheet />);

    expect(getTextNode(renderer, 'Unknown')).toBeDefined();
    expect(renderer.root.findByProps({ testID: 'health-risk-advice-loading' })).toBeDefined();

    renderer.unmount();
  });
});
