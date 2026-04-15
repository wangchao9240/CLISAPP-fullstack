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

// BaselinePill and ClimateMetricsGrid render climate data — stub them so this
// test focuses on the sheet's own assembly (region header, advice subtitle,
// impact section) without duplicating their test coverage.
jest.mock('../../UI/BaselinePill', () => ({
  BaselinePill: () => null,
}));

jest.mock('../../UI/ClimateMetricsGrid', () => ({
  ClimateMetricsGrid: () => null,
}));

const { useMapStore } = require('../../../store/mapStore') as typeof import('../../../store/mapStore');
const { useFavoritesStore } =
  require('../../../store/favoritesStore') as typeof import('../../../store/favoritesStore');
const { HealthBottomSheet } =
  require('../HealthBottomSheet') as typeof import('../HealthBottomSheet');

const mockUseMapStore = useMapStore as unknown as jest.Mock;
const mockUseFavoritesStore = useFavoritesStore as unknown as jest.Mock;

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

const findText = (renderer: ReturnType<typeof create>, text: string) =>
  renderer.root.findAllByType('Text' as any).filter((node) => node.props.children === text);

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

  it("uses the worst-risk layer's advice as the header subtitle", () => {
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

    // Worst-risk is PM2.5 ("Unhealthy") → its advice is shown.
    expect(findText(renderer, 'Everyone should reduce outdoor activity.').length).toBe(1);

    // No HealthRiskBadge testID should exist in the redesigned sheet.
    expect(renderer.root.findAllByProps({ testID: 'health-risk-badge' }).length).toBe(0);

    renderer.unmount();
  });

  it('falls back to the active layer advice when no layer is above Good', () => {
    mockMapState = {
      regionInfo: {
        visible: true,
        regionId: 'ssc_10001',
        regionName: 'Alpha Plains',
        regionType: 'ssc',
        latitude: -27.5,
        longitude: 153.0,
        climate: {
          primary: {
            layer: 'pm25',
            name: 'PM2.5',
            value: 5,
            unit: 'µg/m³',
            riskLevel: 'Good',
            advice: 'Air quality is great today.',
            lastUpdated: '2026-03-17T12:00:00Z',
          },
          secondary: [
            {
              layer: 'uv',
              name: 'UV',
              value: 2,
              unit: 'UVI',
              riskLevel: 'Good',
              advice: 'Enjoy the sunshine.',
            },
          ],
        },
        loading: false,
        error: null,
      },
      activeLayer: 'uv',
      closeRegionInfo: jest.fn(),
      clearRegionInfo: jest.fn(),
    };

    const renderer = create(<HealthBottomSheet />);

    expect(findText(renderer, 'Enjoy the sunshine.').length).toBe(1);
    renderer.unmount();
  });

  it('shows the generic fallback subtitle when no climate data is available', () => {
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

    expect(findText(renderer, 'Conditions are within expected ranges.').length).toBe(1);
    renderer.unmount();
  });

  it('updates the advice subtitle when the climate data changes', () => {
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
    expect(findText(renderer, 'Everyone should reduce outdoor activity.').length).toBe(1);

    mockMapState = {
      ...mockMapState,
      regionInfo: {
        ...mockMapState.regionInfo,
        climate: {
          primary: {
            layer: 'uv',
            name: 'UV',
            value: 9,
            unit: 'UVI',
            riskLevel: 'Hazardous',
            advice: 'Seek shade immediately.',
          },
          secondary: [],
        },
      },
    };

    act(() => {
      renderer.update(<HealthBottomSheet />);
    });

    expect(findText(renderer, 'Seek shade immediately.').length).toBe(1);
    renderer.unmount();
  });
});
