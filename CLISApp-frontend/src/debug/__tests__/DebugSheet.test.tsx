import React from 'react';
import { act, create } from 'react-test-renderer';
import { DebugSheet } from '../DebugSheet';
import { useDebugStore } from '../debugStore';
import { useMapStore } from '../../store/mapStore';
import { API_CONFIG } from '../../constants/apiEndpoints';
import * as riskCycle from '../scenarios/riskCycle';
import * as pushSim from '../scenarios/pushSim';
import * as pushReal from '../scenarios/pushReal';

const mockPresent = jest.fn();
const mockDismiss = jest.fn();

jest.mock('@react-native-async-storage/async-storage', () => ({
  __esModule: true,
  default: {
    getItem: jest.fn(),
    setItem: jest.fn(),
    removeItem: jest.fn(),
  },
}));

jest.mock('react-native-config', () => ({
  __esModule: true,
  default: {},
}));

jest.mock('../../services/telemetryService', () => ({
  __setDebugTap: jest.fn(),
  sendTelemetry: jest.fn().mockResolvedValue(undefined),
}));

jest.mock('react-native-paper', () => {
  const React = require('react');

  return {
    Snackbar: ({ visible, children, ...props }: any) =>
      visible ? React.createElement('Text', props, children) : null,
  };
});

jest.mock('@gorhom/bottom-sheet', () => {
  const React = require('react');

  return {
    BottomSheetModal: React.forwardRef(({ children, ...props }: any, ref: any) => {
      React.useImperativeHandle(ref, () => ({
        present: mockPresent,
        dismiss: mockDismiss,
      }));
      return React.createElement('BottomSheetModal', props, children);
    }),
    BottomSheetScrollView: ({ children, ...props }: any) =>
      React.createElement('BottomSheetScrollView', props, children),
    BottomSheetView: ({ children }: any) => <>{children}</>,
  };
});

const findText = (renderer: ReturnType<typeof create>, text: string) =>
  renderer.root.findAllByType('Text' as any).filter((node) => node.props.children === text);

describe('DebugSheet', () => {
  beforeEach(() => {
    jest.restoreAllMocks();
    mockPresent.mockClear();
    mockDismiss.mockClear();
  });

  it('renders all scenario groups', () => {
    const renderer = create(<DebugSheet />);

    expect(findText(renderer, 'RISK BADGES').length).toBe(1);
    expect(findText(renderer, 'EMPTY / FALLBACK').length).toBe(1);
    expect(findText(renderer, 'PUSH NOTIFICATION').length).toBe(1);
    expect(findText(renderer, 'TELEMETRY').length).toBe(1);
    expect(findText(renderer, 'Reset all overrides').length).toBe(1);
    renderer.unmount();
  });

  it('uses a bottom-sheet-aware scroll view so lower controls stay reachable', () => {
    const renderer = create(<DebugSheet />);

    expect(
      renderer.root.findAllByType('BottomSheetScrollView' as any).length,
    ).toBe(1);
    renderer.unmount();
  });

  it('uses a tall demo snap point so the full scenario list is reachable', () => {
    const renderer = create(<DebugSheet />);

    expect(
      renderer.root.findByType('BottomSheetModal' as any).props.snapPoints,
    ).toEqual(['85%']);
    renderer.unmount();
  });

  it('risk chip taps call applyRiskCycle', () => {
    const spy = jest.spyOn(riskCycle, 'applyRiskCycle').mockImplementation(() => {});
    const renderer = create(<DebugSheet />);

    act(() => {
      renderer.root.findByProps({ testID: 'debug-risk-high' }).props.onPress();
    });

    expect(spy).toHaveBeenCalledWith('high');
    renderer.unmount();
  });

  it('shows a Snackbar instead of throwing when a scenario fails', () => {
    jest.spyOn(console, 'error').mockImplementation(() => {});
    jest.spyOn(riskCycle, 'applyRiskCycle').mockImplementation(() => {
      throw new Error('fixture failed');
    });
    const renderer = create(<DebugSheet />);

    expect(() => {
      act(() => {
        renderer.root.findByProps({ testID: 'debug-risk-high' }).props.onPress();
      });
    }).not.toThrow();
    expect(findText(renderer, 'Scenario failed - see logs').length).toBe(1);
    renderer.unmount();
  });

  it('Fire simulated alert calls firePushSimulated', () => {
    const spy = jest.spyOn(pushSim, 'firePushSimulated').mockImplementation(() => {});
    const renderer = create(<DebugSheet />);

    act(() => {
      renderer.root.findByProps({ testID: 'debug-push-sim' }).props.onPress();
    });

    expect(spy).toHaveBeenCalled();
    renderer.unmount();
  });

  it('Fire real FCM calls firePushReal with the configured API base URL', () => {
    const spy = jest.spyOn(pushReal, 'firePushReal').mockResolvedValue(undefined);
    const renderer = create(<DebugSheet />);

    act(() => {
      renderer.root.findByProps({ testID: 'debug-push-real' }).props.onPress();
    });

    expect(spy).toHaveBeenCalledWith(API_CONFIG.BASE_URL);
    renderer.unmount();
  });

  it('telemetry opener shows the live tail modal', () => {
    const renderer = create(<DebugSheet />);

    expect(findText(renderer, 'TELEMETRY LIVE TAIL').length).toBe(0);
    act(() => {
      renderer.root.findByProps({ testID: 'debug-telemetry-open' }).props.onPress();
    });

    expect(findText(renderer, 'TELEMETRY LIVE TAIL').length).toBe(1);
    renderer.unmount();
  });

  it('Clear current region dismisses the debug sheet', () => {
    const renderer = create(<DebugSheet />);

    act(() => {
      renderer.root.findByProps({ testID: 'debug-empty-clear' }).props.onPress();
    });

    expect(useMapStore.getState().regionInfo.visible).toBe(false);
    expect(mockDismiss).toHaveBeenCalledTimes(1);
    renderer.unmount();
  });

  it('Reset all overrides restores the pre-override region snapshot', () => {
    useDebugStore.getState().captureSnapshotIfNone({
      visible: true,
      regionId: 'REAL-1',
      regionName: 'Real Region',
      regionType: 'ssc',
      latitude: -27.5,
      longitude: 153,
      climate: null,
      loading: false,
      error: null,
    });
    useDebugStore.getState().setRiskOverride('high');
    const renderer = create(<DebugSheet />);

    act(() => {
      renderer.root.findByProps({ testID: 'debug-reset' }).props.onPress();
    });

    expect(useMapStore.getState().regionInfo.regionId).toBe('REAL-1');
    expect(useDebugStore.getState().overrides.risk).toBeNull();
    renderer.unmount();
  });
});
