import React from 'react';
import { act, create } from 'react-test-renderer';

jest.mock('../../../hooks/useApi', () => ({
  useRegionSearch: jest.fn(),
  formatClimateOverview: jest.fn(),
}));

jest.mock('../../../store/mapStore', () => ({
  useMapStore: jest.fn(),
}));

jest.mock('../../../services/ApiService', () => ({
  apiService: {
    getRegionInfo: jest.fn(),
    getRegionBoundary: jest.fn(),
  },
}));

jest.mock('../../../services/boundaries/BoundaryStore', () => ({
  convertGeometryToShapes: jest.fn(),
}));

const { RegionSearchBar } = require('../RegionSearchBar');
const { useRegionSearch, formatClimateOverview } = require('../../../hooks/useApi');
const { useMapStore } = require('../../../store/mapStore');
const { apiService } = require('../../../services/ApiService');
const { convertGeometryToShapes } = require('../../../services/boundaries/BoundaryStore');

const mockUseRegionSearch = useRegionSearch as jest.Mock;
const mockFormatClimateOverview = formatClimateOverview as jest.Mock;
const mockUseMapStore = useMapStore as jest.Mock;
const mockGetRegionInfo = apiService.getRegionInfo as jest.Mock;
const mockGetRegionBoundary = apiService.getRegionBoundary as jest.Mock;
const mockConvertGeometryToShapes = convertGeometryToShapes as jest.Mock;

describe('RegionSearchBar', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (mockUseMapStore as any).getState = jest.fn(() => ({
      activeLayer: 'temperature',
    }));
  });

  it('ignores stale boundary responses from earlier search selections', async () => {
    const openRegionInfo = jest.fn();
    const setRegionBoundary = jest.fn();

    mockUseMapStore.mockReturnValue({
      setRegion: jest.fn(),
      setMapLevel: jest.fn(),
      setSelectedRegion: jest.fn(),
      setLoading: jest.fn(),
      openRegionInfo,
      setRegionInfoLoading: jest.fn(),
      setRegionInfoError: jest.fn(),
      closeRegionInfo: jest.fn(),
      setRegionBoundary,
    });

    const searchResults = [
      {
        id: 'region-older',
        name: 'Older Region',
        type: 'lga',
        state: 'QLD',
        population: 1000,
        location: { latitude: -27.47, longitude: 153.02 },
      },
      {
        id: 'region-newer',
        name: 'Newer Region',
        type: 'lga',
        state: 'QLD',
        population: 2000,
        location: { latitude: -27.57, longitude: 152.92 },
      },
    ];

    mockUseRegionSearch.mockReturnValue({
      data: searchResults,
      loading: false,
      error: null,
      searchRegions: jest.fn(),
      clearResults: jest.fn(),
    });

    mockGetRegionInfo.mockResolvedValue({
      success: true,
      data: {
        id: 'region-info',
        name: 'Region Info',
        type: 'lga',
        location: {
          latitude: -27.47,
          longitude: 153.02,
        },
        current_climate: { temperature: { value: 23, unit: 'C' } },
      },
    });
    mockFormatClimateOverview.mockReturnValue({ summary: 'Test climate' });

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

    const renderer = create(<RegionSearchBar />);
    const olderResult = renderer.root.find(
      (node) => typeof node.props.onPress === 'function' && node.props.item?.id === 'region-older'
    );
    const newerResult = renderer.root.find(
      (node) => typeof node.props.onPress === 'function' && node.props.item?.id === 'region-newer'
    );

    await act(async () => {
      olderResult.props.onPress(olderResult.props.item);
      newerResult.props.onPress(newerResult.props.item);
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
      await Promise.resolve();
    });

    await act(async () => {
      resolveFirstBoundary!({
        success: true,
        data: {
          geometry: firstGeometry,
          properties: { source: 'older' },
        },
      });
      await Promise.resolve();
    });

    expect(setRegionBoundary).toHaveBeenLastCalledWith({
      regionId: 'region-newer',
      polygons: secondPolygons,
      properties: { source: 'newer' },
    });
    expect(openRegionInfo).toHaveBeenCalledWith({
      regionId: 'region-info',
      regionName: 'Region Info',
      regionType: 'lga',
      climate: { summary: 'Test climate' },
      latitude: -27.47,
      longitude: 153.02,
    });
  });
});
