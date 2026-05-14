import React from 'react';
import { act, create } from 'react-test-renderer';
import { DebugFAB } from '../DebugFAB';
import * as tap from '../telemetryTap';

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

jest.mock('@gorhom/bottom-sheet', () => {
  const React = require('react');

  return {
    BottomSheetModal: React.forwardRef(({ children }: any, ref: any) => {
      React.useImperativeHandle(ref, () => ({
        present: mockPresent,
        dismiss: mockDismiss,
      }));
      return <>{children}</>;
    }),
    BottomSheetScrollView: ({ children }: any) => <>{children}</>,
    BottomSheetView: ({ children }: any) => <>{children}</>,
  };
});

jest.mock('react-native-paper', () => {
  const React = require('react');

  return {
    Snackbar: ({ visible, children, ...props }: any) =>
      visible ? React.createElement('Text', props, children) : null,
  };
});

describe('DebugFAB', () => {
  beforeEach(() => {
    jest.restoreAllMocks();
    mockPresent.mockClear();
    mockDismiss.mockClear();
  });

  it('registers and unregisters the telemetry tap', () => {
    const register = jest.spyOn(tap, 'registerTelemetryTap').mockImplementation(() => {});
    const unregister = jest
      .spyOn(tap, 'unregisterTelemetryTap')
      .mockImplementation(() => {});

    let renderer: ReturnType<typeof create>;
    act(() => {
      renderer = create(<DebugFAB />);
    });

    expect(register).toHaveBeenCalled();
    act(() => {
      renderer.unmount();
    });
    expect(unregister).toHaveBeenCalled();
  });

  it('renders a pressable with testID="debug-fab"', () => {
    const renderer = create(<DebugFAB />);

    expect(renderer.root.findByProps({ testID: 'debug-fab' })).toBeTruthy();
    renderer.unmount();
  });

  it('tapping the FAB presents the debug sheet', () => {
    const renderer = create(<DebugFAB />);

    act(() => {
      renderer.root.findByProps({ testID: 'debug-fab' }).props.onPress();
    });

    expect(mockPresent).toHaveBeenCalledTimes(1);
    renderer.unmount();
  });
});
