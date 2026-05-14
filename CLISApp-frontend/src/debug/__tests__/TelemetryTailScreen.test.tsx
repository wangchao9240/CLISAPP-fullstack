import React from 'react';
import { act, create } from 'react-test-renderer';
import { TelemetryTailScreen } from '../TelemetryTailScreen';
import { useDebugStore } from '../debugStore';
import * as telemetryService from '../../services/telemetryService';

jest.mock('@react-native-async-storage/async-storage', () => ({
  __esModule: true,
  default: {
    getItem: jest.fn(),
    setItem: jest.fn(),
    removeItem: jest.fn(),
  },
}));

jest.mock('../../services/telemetryService', () => ({
  sendTelemetry: jest.fn().mockResolvedValue(undefined),
}));

const findText = (renderer: ReturnType<typeof create>, text: string) =>
  renderer.root.findAllByType('Text' as any).filter((node) => node.props.children === text);

const findTextMatching = (renderer: ReturnType<typeof create>, pattern: RegExp) =>
  renderer.root
    .findAllByType('Text' as any)
    .filter((node) => pattern.test(String(node.props.children)));

describe('TelemetryTailScreen', () => {
  beforeEach(() => {
    useDebugStore.setState({ telemetryTail: [], telemetryUnreadCount: 0 });
    jest.clearAllMocks();
  });

  it('renders the privacy banner', () => {
    const renderer = create(<TelemetryTailScreen visible onClose={() => {}} />);

    expect(findText(renderer, 'Privacy guarantees').length).toBe(1);
    expect(findText(renderer, 'Device ID is an opaque app identifier').length).toBe(1);
    expect(findText(renderer, 'Only the last 8 characters are shown here').length).toBe(1);
    expect(findText(renderer, 'lat/lon truncated to 2 dp').length).toBe(1);
    renderer.unmount();
  });

  it('renders one row per tail entry', () => {
    useDebugStore.setState({
      telemetryTail: [
        {
          id: '1',
          timestamp: '2026-05-15T07:42:13Z',
          payload: {
            device_id: 'abc12345xyz67890',
            event_date: '2026-05-15',
            time_of_day: '07:42:13',
            lat: -27.47,
            lon: 153.03,
          },
          outcome: 'ok',
        },
      ],
      telemetryUnreadCount: 0,
    });

    const renderer = create(<TelemetryTailScreen visible onClose={() => {}} />);

    expect(findText(renderer, '07:42:13  ok').length).toBe(1);
    expect(findTextMatching(renderer, /xyz67890$/).length).toBe(1);
    expect(findText(renderer, '-27.47, 153.03').length).toBe(1);
    renderer.unmount();
  });

  it('Clear button wipes the tail', () => {
    useDebugStore.setState({
      telemetryTail: [
        {
          id: '1',
          timestamp: 't',
          payload: {
            device_id: 'a',
            event_date: 'd',
            time_of_day: 't',
            lat: null,
            lon: null,
          },
          outcome: 'ok',
        },
      ],
      telemetryUnreadCount: 1,
    });

    const renderer = create(<TelemetryTailScreen visible onClose={() => {}} />);
    useDebugStore.setState({ telemetryUnreadCount: 1 });

    act(() => {
      renderer.root.findByProps({ testID: 'debug-telemetry-clear' }).props.onPress();
    });

    expect(useDebugStore.getState().telemetryTail).toEqual([]);
    expect(useDebugStore.getState().telemetryUnreadCount).toBe(0);
    renderer.unmount();
  });

  it('keeps unread count at zero when telemetry arrives while tail is visible', async () => {
    const renderer = create(<TelemetryTailScreen visible onClose={() => {}} />);

    await act(async () => {
      useDebugStore.getState().pushTelemetry({
        id: '1',
        timestamp: 't',
        payload: {
          device_id: 'a',
          event_date: 'd',
          time_of_day: 't',
          lat: null,
          lon: null,
        },
        outcome: 'ok',
      });
    });

    expect(useDebugStore.getState().telemetryUnreadCount).toBe(0);
    renderer.unmount();
  });

  it('Fire test telemetry calls sendTelemetry', () => {
    const renderer = create(<TelemetryTailScreen visible onClose={() => {}} />);

    act(() => {
      renderer.root.findByProps({ testID: 'debug-telemetry-fire' }).props.onPress();
    });

    expect(telemetryService.sendTelemetry).toHaveBeenCalled();
    renderer.unmount();
  });
});
