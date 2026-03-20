/**
 * Boundary styling constants - aligned with design mockup
 * Primary blue: #1976D2 (Material Design Blue 700)
 */

export const BOUNDARY_COLORS = {
  PRIMARY_BLUE: '#1976D2',

  // Unselected boundaries (default state)
  UNSELECTED_STROKE: 'rgba(25, 118, 210, 0.6)',
  UNSELECTED_FILL: 'rgba(0, 0, 0, 0)',

  // Selected/highlighted boundaries (user-selected region)
  SELECTED_STROKE: 'rgba(25, 118, 210, 0.9)',
  SELECTED_FILL: 'rgba(25, 118, 210, 0.08)',
} as const;

export const BOUNDARY_WIDTHS = {
  UNSELECTED: 1,
  SELECTED: 2.5,
  SSC_DETAIL: 1,
} as const;

export const BOUNDARY_Z_INDEX = {
  COARSE: 2,
  SSC: 3,
  ACTIVE_COARSE: 4,
  SELECTED_REGION: 5,
} as const;
