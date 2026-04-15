// CLISApp-frontend/src/constants/healthDesignTokens.ts

// Colour tokens used by the Stitch-authored HealthBottomSheet redesign.
// Other components should keep using their existing palettes — do not
// re-export these from a global theme.

export const HEALTH_SHEET_COLORS = {
  surface: '#FFFFFF',
  surfaceContainerLow: '#F2F3FC',
  outline: '#717783',
  outlineVariant: '#C1C6D4',
  onSurface: '#181C21',
  onSurfaceVariant: '#414752',
  primary: '#005DAC',
} as const;

export const RISK_TEXT_COLORS = {
  Good: '#43A047',
  Moderate: '#F9A825',
  Unhealthy: '#FF7043',
  Hazardous: '#E57373',
  Unknown: '#717783',
} as const;

export const DELTA_COLORS = {
  warm: '#FF7043',
  cool: '#64B5F6',
  neutral: '#78909C',
} as const;

export const IMPACT_COLORS = {
  elevated: '#E65100',
} as const;

export type RiskKey = keyof typeof RISK_TEXT_COLORS;
