// CLISApp-frontend/src/constants/designTokens.ts
//
// Stitch v2 canonical design tokens — Phase 0.
// These are the authoritative palette, type scale, radii, and utility tokens
// for the visual redesign. All Phase 1+ component restyling imports from here.
//
// Light mode only. Dark mode is out of scope for this release.

// ---------------------------------------------------------------------------
// Palette
// ---------------------------------------------------------------------------

export const PALETTE = {
  // Backgrounds & surfaces
  bg:       '#F2F4FB',
  surface:  '#FFFFFF',
  surface2: '#F8F9FE',
  surface3: '#EDF0F8',

  // Foreground & text
  fg:    '#0E1422',
  fg2:   '#2B3247',
  muted: '#6A7186',
  faint: '#A1A8BC',

  // Borders
  border:   '#E5E8F0',
  border2:  '#D7DCE7',
  hairline: 'rgba(15,20,34,0.08)',

  // Accent (interactive / brand blue)
  accent:     '#0B86C8',
  accentSoft: '#E2F1FB',
  accentDeep: '#07658F',

  // Semantic — Good (green)
  good:     '#168D45',
  goodSoft: '#E3F4E8',

  // Semantic — Moderate (amber)
  moderate:     '#B86A09',
  moderateSoft: '#FAEAD3',

  // Semantic — Hazard (red)
  hazard:     '#B83232',
  hazardSoft: '#FAE0E0',

  // Climate delta — Cool (temperature below baseline)
  cool:     '#2D85BC',
  coolSoft: '#E0EFF7',

  // Climate delta — Warm (temperature above baseline)
  warm:     '#B85727',
  warmSoft: '#F8E5D9',
} as const;

export type PaletteKey = keyof typeof PALETTE;

// ---------------------------------------------------------------------------
// Type scale
// ---------------------------------------------------------------------------
// Letter-spacing values are expressed as React Native points (not em).
// Conversion: em × fontSize = points. E.g. -0.025em × 32px = -0.8pt.

export const TYPE_SCALE = {
  title: {
    fontSize:      32,
    lineHeight:    34,
    fontWeight:    '700' as const,
    letterSpacing: -0.8,
  },
  h2: {
    fontSize:      22,
    lineHeight:    24,
    fontWeight:    '600' as const,
    letterSpacing: -0.44,
  },
  body: {
    fontSize:   15,
    lineHeight: 23,
    fontWeight: '500' as const,
  },
  kicker: {
    fontSize:      11,
    lineHeight:    13,
    fontWeight:    '600' as const,
    letterSpacing: 0.66,
    textTransform: 'uppercase' as const,
  },
} as const;

export type TypeScaleKey = keyof typeof TYPE_SCALE;

// ---------------------------------------------------------------------------
// Radii
// ---------------------------------------------------------------------------

export const RADII = {
  chip:    12,
  control: 14,
  card:    18,
  sheet:   24,
} as const;

export type RadiusKey = keyof typeof RADII;

// ---------------------------------------------------------------------------
// Tabular numerics
// ---------------------------------------------------------------------------
// Apply to Text components that display numeric values (deltas, temps,
// percentages, dates) so digits align consistently — Principle 3.

export const TABULAR_NUMS = {
  fontVariant: ['tabular-nums'] as const,
} as const;
