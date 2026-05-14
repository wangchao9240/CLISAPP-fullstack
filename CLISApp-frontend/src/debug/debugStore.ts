import AsyncStorage from '@react-native-async-storage/async-storage';
import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';
import type { RegionInfoPanelState } from '../types/region.types';

export type RiskKey = 'low' | 'moderate' | 'high' | 'extreme';

export interface TelemetryTailEntry {
  id: string;
  timestamp: string;
  payload: {
    device_id: string;
    event_date: string;
    time_of_day: string;
    lat: number | null;
    lon: number | null;
  };
  outcome: 'ok' | 'fail';
}

interface DebugState {
  fabPosition: { x: number; y: number };
  overrides: {
    risk: RiskKey | null;
    emptyState: boolean;
  };
  preOverrideSnapshot: RegionInfoPanelState | null;
  pushRotationIndex: number;
  telemetryTail: TelemetryTailEntry[];
  telemetryUnreadCount: number;
  setRiskOverride: (risk: RiskKey | null) => void;
  setEmptyState: (enabled: boolean) => void;
  captureSnapshotIfNone: (snapshot: RegionInfoPanelState) => void;
  clearSnapshot: () => void;
  bumpPushRotation: () => void;
  pushTelemetry: (entry: TelemetryTailEntry) => void;
  markTelemetryRead: () => void;
  setFabPosition: (position: { x: number; y: number }) => void;
  resetAll: () => void;
}

const INITIAL: Pick<
  DebugState,
  | 'overrides'
  | 'preOverrideSnapshot'
  | 'pushRotationIndex'
  | 'telemetryTail'
  | 'telemetryUnreadCount'
> = {
  overrides: { risk: null, emptyState: false },
  preOverrideSnapshot: null,
  pushRotationIndex: 0,
  telemetryTail: [],
  telemetryUnreadCount: 0,
};

export const useDebugStore = create<DebugState>()(
  persist(
    (set) => ({
      fabPosition: { x: -24, y: -120 },
      ...INITIAL,
      setRiskOverride: (risk) =>
        set((state) => ({ overrides: { ...state.overrides, risk } })),
      setEmptyState: (enabled) =>
        set((state) => ({
          overrides: { ...state.overrides, emptyState: enabled },
        })),
      captureSnapshotIfNone: (snapshot) =>
        set((state) =>
          state.preOverrideSnapshot ? {} : { preOverrideSnapshot: snapshot },
        ),
      clearSnapshot: () => set({ preOverrideSnapshot: null }),
      bumpPushRotation: () =>
        set((state) => ({
          pushRotationIndex: (state.pushRotationIndex + 1) % 3,
        })),
      pushTelemetry: (entry) =>
        set((state) => ({
          telemetryTail: [entry, ...state.telemetryTail].slice(0, 20),
          telemetryUnreadCount: state.telemetryUnreadCount + 1,
        })),
      markTelemetryRead: () => set({ telemetryUnreadCount: 0 }),
      setFabPosition: (fabPosition) => set({ fabPosition }),
      resetAll: () =>
        set((state) => ({
          ...INITIAL,
          telemetryTail: state.telemetryTail,
          telemetryUnreadCount: state.telemetryUnreadCount,
          fabPosition: state.fabPosition,
        })),
    }),
    {
      name: 'clisapp-debug',
      storage: createJSONStorage(() => AsyncStorage),
      partialize: (state) => ({ fabPosition: state.fabPosition }),
    },
  ),
);
