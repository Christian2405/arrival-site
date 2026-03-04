export const Colors = {
  // Arrival brand — warm off-white background
  background: '#FFFFF5',
  backgroundDark: '#1C1C1E',
  backgroundWarm: '#F3F0EB',
  card: '#FFFFFF',
  cardDark: '#2C2C2E',

  // Text
  text: '#1A1A1A',
  textDark: '#2A2622',
  textSecondary: '#8E8E93',
  textMuted: '#A09A93',
  textLight: '#AEAEB2',
  textFaint: '#C7C2BC',
  textOnDark: '#FFFFFF',

  // Accent — warm orange
  accent: '#D4842A',
  accentLight: '#E8A84C',
  accentMuted: 'rgba(212, 132, 42, 0.12)',

  // Borders & Dividers
  border: '#E5E5EA',
  borderLight: '#F2F2F7',
  borderWarm: '#EBE7E2',
  separator: '#C6C6C8',
  switchTrack: '#DDD9D5',

  // Status
  success: '#34C759',
  error: '#FF3B30',
  errorMuted: '#C75450',
  warning: '#FF9500',
  recording: '#FF3B30',

  // Confidence
  confidenceHigh: '#34C759',
  confidenceMedium: '#FF9500',
  confidenceLow: '#FF3B30',

  // Trades
  tradeHvac: '#4A90D9',
  tradeElectrical: '#E8A84C',
  tradePlumbing: '#5B9BD5',
  tradeGeneral: '#7C736A',

  // Plans
  planBusiness: '#4A90D9',
  planFree: '#7C736A',

  // Button
  buttonDark: '#2A2622',

  // Camera overlay
  overlayLight: 'rgba(0, 0, 0, 0.10)',
  overlayMedium: 'rgba(0, 0, 0, 0.40)',
  overlayDark: 'rgba(0, 0, 0, 0.60)',
  glassBg: 'rgba(255, 255, 255, 0.92)',
  glassLight: 'rgba(255, 255, 255, 0.15)',
  glassDark: 'rgba(0, 0, 0, 0.45)',
};

// ── Design Tokens ──────────────────────────────────────────────
// Constrained scales to keep the whole app visually consistent.

export const Spacing = { xs: 4, sm: 8, md: 12, base: 16, lg: 24, xl: 32 } as const;

export const Radius = { sm: 8, md: 12, lg: 16, full: 24 } as const;

export const FontSize = { xs: 12, sm: 14, base: 16, lg: 18, xl: 24 } as const;

export const IconSize = { sm: 16, md: 20, lg: 24 } as const;

export const Shadow = {
  subtle: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 4,
    elevation: 1,
  },
  medium: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 8,
    elevation: 3,
  },
} as const;
