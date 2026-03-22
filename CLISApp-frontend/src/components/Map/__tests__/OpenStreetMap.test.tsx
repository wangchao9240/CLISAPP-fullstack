import React from 'react';
import { act, create } from 'react-test-renderer';

let mockMapViewProps: any;
const mockPolygon = jest.fn((_props: any) => null);
const mockUrlTile = jest.fn((_props: any) => null);

jest.mock('../../../store/mapStore', () => ({
  useMapStore: jest.fn(),
}));

jest.mock('../../../store/settingsStore', () => ({
  useSettingsStore: jest.fn(),
}));

jest.mock('../../../hooks/useApi', () => ({
  fetchRegionInfoByCoordinates: jest.fn(),
  formatClimateOverview: jest.fn(),
}));

jest.mock('../../../hooks/useBoundaryOverlays', () => ({
  __esModule: true,
  default: jest.fn(),
}));

jest.mock('../../../services/ApiService', () => ({
  apiService: {
    getRegionBoundary: jest.fn(),
  },
}));

jest.mock('../../../services/boundaries/BoundaryStore', () => ({
  convertGeometryToShapes: jest.fn(),
}));

jest.mock('react-native-device-info', () => ({
  getVersion: jest.fn(() => '1.0.0'),
  getUniqueId: jest.fn(() => 'test-device-id'),
}));

jest.mock('../../../services/telemetryService', () => ({
  trackEvent: jest.fn(),
}));

jest.mock('react-native-maps', () => {
  const React = require('react');

  const MockMapView = React.forwardRef((props: any, _ref: any) => {
    mockMapViewProps = props;
    return <>{props.children}</>;
  });

  return {
    __esModule: true,
    default: MockMapView,
    UrlTile: (props: any) => mockUrlTile(props),
    Polygon: (props: any) => mockPolygon(props),
  };
});

const { OpenStreetMap } = require('../OpenStreetMap');
const { useMapStore } = require('../../../store/mapStore');
const { useSettingsStore } = require('../../../store/settingsStore');
const { fetchRegionInfoByCoordinates, formatClimateOverview } = require('../../../hooks/useApi');
const useBoundaryOverlays = require('../../../hooks/useBoundaryOverlays').default;
const { apiService } = require('../../../services/ApiService');
const { convertGeometryToShapes } = require('../../../services/boundaries/BoundaryStore');

const mockUseMapStore = useMapStore as jest.Mock;
const mockUseSettingsStore = useSettingsStore as jest.Mock;
const mockFetchRegionInfoByCoordinates = fetchRegionInfoByCoordinates as jest.Mock;
const mockFormatClimateOverview = formatClimateOverview as jest.Mock;
const mockUseBoundaryOverlays = useBoundaryOverlays as jest.Mock;
const mockGetRegionBoundary = apiService.getRegionBoundary as jest.Mock;
const mockConvertGeometryToShapes = convertGeometryToShapes as jest.Mock;

describe('OpenStreetMap', () => {
  const baseRegion = {
    latitude: -27.47,
    longitude: 153.02,
    latitudeDelta: 0.2,
    longitudeDelta: 0.2,
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockMapViewProps = undefined;
    mockUseSettingsStore.mockReturnValue({
      tileServerUrl: 'https://tiles.example.com',
    });
    mockUseBoundaryOverlays.mockReturnValue([]);
    (mockUseMapStore as any).getState = jest.fn(() => ({
      activeLayer: 'temperature',
    }));
  });

  it('renders selected region polygons with holes and highlight styling', () => {
    const setRegion = jest.fn();
    const setLoading = jest.fn();

    const selectedPolygon = {
      outline: [
        { latitude: -27.5, longitude: 153.0 },
        { latitude: -27.4, longitude: 153.0 },
        { latitude: -27.4, longitude: 153.1 },
      ],
      holes: [[
        { latitude: -27.48, longitude: 153.02 },
        { latitude: -27.46, longitude: 153.02 },
        { latitude: -27.46, longitude: 153.04 },
      ]],
    };

    mockUseMapStore.mockReturnValue({
      region: baseRegion,
      activeLayer: 'temperature',
      mapLevel: 'coarse',
      regionBoundary: {
        regionId: 'region-1',
        polygons: [selectedPolygon],
      },
      setRegion,
      setLoading,
      openRegionInfo: jest.fn(),
      setRegionInfoLoading: jest.fn(),
      setRegionInfoError: jest.fn(),
      setSelectedRegion: jest.fn(),
      setRegionBoundary: jest.fn(),
    });

    create(<OpenStreetMap />);

    expect(mockPolygon).toHaveBeenCalledWith(expect.objectContaining({
      coordinates: selectedPolygon.outline,
      holes: selectedPolygon.holes,
      strokeColor: 'rgba(25, 118, 210, 0.9)',
      strokeWidth: 2.5,
      fillColor: 'rgba(25, 118, 210, 0.08)',
      zIndex: 5,
    }));
  });

  it('does not write unchanged region values back to the store on region change complete', () => {
    const setRegion = jest.fn();
    const setLoading = jest.fn();

    mockUseMapStore.mockReturnValue({
      region: baseRegion,
      activeLayer: 'temperature',
      mapLevel: 'coarse',
      regionBoundary: null,
      setRegion,
      setLoading,
      openRegionInfo: jest.fn(),
      setRegionInfoLoading: jest.fn(),
      setRegionInfoError: jest.fn(),
      setSelectedRegion: jest.fn(),
      setRegionBoundary: jest.fn(),
    });
    (mockUseMapStore as any).getState = jest.fn(() => ({
      region: baseRegion,
    }));

    create(<OpenStreetMap />);

    act(() => {
      mockMapViewProps.onRegionChangeComplete(baseRegion);
    });

    expect(setRegion).not.toHaveBeenCalled();
    expect(setLoading).toHaveBeenCalledWith(false);
  });

  it('clears and reloads the selected region boundary on long press', async () => {
    const setRegionBoundary = jest.fn();
    const setRegionInfoLoading = jest.fn();
    const setRegionInfoError = jest.fn();
    const openRegionInfo = jest.fn();
    const setSelectedRegion = jest.fn();

    const geometry = {
      type: 'Polygon',
      coordinates: [[
        [153, -27.5],
        [153, -27.4],
        [153.1, -27.4],
      ]],
    };
    const convertedPolygons = [
      {
        outline: [
          { latitude: -27.5, longitude: 153 },
          { latitude: -27.4, longitude: 153 },
          { latitude: -27.4, longitude: 153.1 },
        ],
      },
    ];

    mockUseMapStore.mockReturnValue({
      region: baseRegion,
      activeLayer: 'temperature',
      mapLevel: 'coarse',
      regionBoundary: null,
      setRegion: jest.fn(),
      setLoading: jest.fn(),
      openRegionInfo,
      setRegionInfoLoading,
      setRegionInfoError,
      setSelectedRegion,
      setRegionBoundary,
    });

    mockFetchRegionInfoByCoordinates.mockResolvedValue({
      id: 'region-2',
      name: 'Region Two',
      type: 'lga',
      location: {
        latitude: -27.47,
        longitude: 153.02,
      },
      current_climate: { temperature: 22 },
    });
    mockFormatClimateOverview.mockReturnValue({ summary: 'Warm' });
    mockGetRegionBoundary.mockResolvedValue({
      success: true,
      data: {
        geometry,
        properties: { source: 'test' },
      },
    });
    mockConvertGeometryToShapes.mockReturnValue(convertedPolygons);

    create(<OpenStreetMap />);

    await act(async () => {
      await mockMapViewProps.onLongPress({
        nativeEvent: {
          coordinate: {
            latitude: -27.47,
            longitude: 153.02,
          },
        },
      });
    });

    expect(setRegionBoundary).toHaveBeenNthCalledWith(1, null);
    expect(openRegionInfo).toHaveBeenCalledWith({
      regionId: 'region-2',
      regionName: 'Region Two',
      regionType: 'lga',
      climate: { summary: 'Warm' },
      latitude: -27.47,
      longitude: 153.02,
    });
    expect(mockGetRegionBoundary).toHaveBeenCalledWith('region-2');
    expect(mockConvertGeometryToShapes).toHaveBeenCalledWith(geometry);
    expect(setRegionBoundary).toHaveBeenLastCalledWith({
      regionId: 'region-2',
      polygons: convertedPolygons,
      properties: { source: 'test' },
    });
  });

  it('ignores stale boundary responses from earlier long presses', async () => {
    const setRegionBoundary = jest.fn();

    mockUseMapStore.mockReturnValue({
      region: baseRegion,
      activeLayer: 'temperature',
      mapLevel: 'coarse',
      regionBoundary: null,
      setRegion: jest.fn(),
      setLoading: jest.fn(),
      openRegionInfo: jest.fn(),
      setRegionInfoLoading: jest.fn(),
      setRegionInfoError: jest.fn(),
      setSelectedRegion: jest.fn(),
      setRegionBoundary,
    });

    const firstGeometry = {
      type: 'Polygon',
      coordinates: [[
        [153.0, -27.5],
        [153.0, -27.4],
        [153.1, -27.4],
      ]],
    };
    const secondGeometry = {
      type: 'Polygon',
      coordinates: [[
        [152.9, -27.6],
        [152.9, -27.5],
        [153.0, -27.5],
      ]],
    };
    const firstPolygons = [{ outline: [{ latitude: -27.5, longitude: 153.0 }] }];
    const secondPolygons = [{ outline: [{ latitude: -27.6, longitude: 152.9 }] }];

    let resolveFirstBoundary: (value: any) => void;
    let resolveSecondBoundary: (value: any) => void;
    const firstBoundaryPromise = new Promise((resolve) => {
      resolveFirstBoundary = resolve;
    });
    const secondBoundaryPromise = new Promise((resolve) => {
      resolveSecondBoundary = resolve;
    });

    mockFetchRegionInfoByCoordinates
      .mockResolvedValueOnce({
        id: 'region-older',
        name: 'Older Region',
        type: 'lga',
        location: {
          latitude: -27.47,
          longitude: 153.02,
        },
        current_climate: { temperature: 20 },
      })
      .mockResolvedValueOnce({
        id: 'region-newer',
        name: 'Newer Region',
        type: 'lga',
        location: {
          latitude: -27.57,
          longitude: 152.92,
        },
        current_climate: { temperature: 24 },
      });
    mockFormatClimateOverview.mockReturnValue({ summary: 'Test climate' });
    mockGetRegionBoundary
      .mockImplementationOnce(() => firstBoundaryPromise)
      .mockImplementationOnce(() => secondBoundaryPromise);
    mockConvertGeometryToShapes.mockImplementation((geometry: any) => {
      if (geometry === firstGeometry) {
        return firstPolygons;
      }
      if (geometry === secondGeometry) {
        return secondPolygons;
      }
      return [];
    });

    create(<OpenStreetMap />);

    let firstLongPress: Promise<void>;
    let secondLongPress: Promise<void>;

    await act(async () => {
      firstLongPress = mockMapViewProps.onLongPress({
        nativeEvent: {
          coordinate: {
            latitude: -27.47,
            longitude: 153.02,
          },
        },
      });
      secondLongPress = mockMapViewProps.onLongPress({
        nativeEvent: {
          coordinate: {
            latitude: -27.57,
            longitude: 152.92,
          },
        },
      });
      await Promise.resolve();
    });

    await act(async () => {
      resolveSecondBoundary!({
        success: true,
        data: {
          geometry: secondGeometry,
          properties: { source: 'newer' },
        },
      });
      await secondLongPress!;
    });

    await act(async () => {
      resolveFirstBoundary!({
        success: true,
        data: {
          geometry: firstGeometry,
          properties: { source: 'older' },
        },
      });
      await firstLongPress!;
    });

    expect(setRegionBoundary).toHaveBeenLastCalledWith({
      regionId: 'region-newer',
      polygons: secondPolygons,
      properties: { source: 'newer' },
    });
  });
});
