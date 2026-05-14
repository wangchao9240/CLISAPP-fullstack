import { __setDebugTap } from '../services/telemetryService';
import { useDebugStore } from './debugStore';

let counter = 0;

export const registerTelemetryTap = (): void => {
  __setDebugTap((payload, outcome) => {
    useDebugStore.getState().pushTelemetry({
      id: String((counter += 1)),
      timestamp: new Date().toISOString(),
      payload,
      outcome,
    });
  });
};

export const unregisterTelemetryTap = (): void => {
  __setDebugTap(undefined);
};
