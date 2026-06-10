/**
 * OncoLife Design System - Theme Foundation
 * 
 * UPDATED: Lovable-inspired warm, emotionally comforting design
 * 
 * Brand: HealthAI
 * Application: OncoLife
 * Patient: "OncoLife - Ruby: Compassionate Care, Intelligent Triage"
 * Doctor: "OncoLife"
 * 
 * Design Philosophy:
 * - Warm cream backgrounds (not clinical white)
 * - Serif headings for emotional warmth
 * - Blue primary accent (trustworthy, calm)
 * - Soft shadows and rounded corners
 * - Green/Amber/Red severity system
 */

import { createTheme, ThemeOptions, responsiveFontSizes, PaletteMode } from '@mui/material/styles';

// =============================================================================
// RESPONSIVE BREAKPOINTS
// =============================================================================

export const breakpoints = {
  values: {
    xs: 0,      // Mobile (portrait)
    sm: 600,    // Mobile (landscape) / Small tablet
    md: 900,    // Tablet
    lg: 1200,   // Desktop
    xl: 1536,   // Large desktop
  },
};

// =============================================================================
// TYPOGRAPHY - DM Sans (body) + Fraunces (headings)
// Lovable-inspired warm typography
// =============================================================================

const typography = {
  // Body font: DM Sans - clean, modern, friendly
  fontFamily: "'DM Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
  
  // Headings use Fraunces (serif) for emotional warmth
  h1: {
    fontFamily: "'Fraunces', Georgia, serif",
    fontSize: '2rem',
    fontWeight: 600,
    lineHeight: 1.2,
    letterSpacing: '-0.02em',
    '@media (min-width:600px)': {
      fontSize: '2.25rem',
    },
    '@media (min-width:900px)': {
      fontSize: '2.5rem',
    },
  },
  h2: {
    fontFamily: "'Fraunces', Georgia, serif",
    fontSize: '1.5rem',
    fontWeight: 600,
    lineHeight: 1.3,
    letterSpacing: '-0.01em',
    '@media (min-width:600px)': {
      fontSize: '1.75rem',
    },
    '@media (min-width:900px)': {
      fontSize: '2rem',
    },
  },
  h3: {
    fontFamily: "'Fraunces', Georgia, serif",
    fontSize: '1.25rem',
    fontWeight: 500,
    lineHeight: 1.4,
    '@media (min-width:900px)': {
      fontSize: '1.5rem',
    },
  },
  h4: {
    fontFamily: "'Fraunces', Georgia, serif",
    fontSize: '1.125rem',
    fontWeight: 500,
    lineHeight: 1.4,
  },
  h5: {
    fontFamily: "'DM Sans', sans-serif",
    fontSize: '1rem',
    fontWeight: 600,
    lineHeight: 1.5,
  },
  h6: {
    fontFamily: "'DM Sans', sans-serif",
    fontSize: '0.875rem',
    fontWeight: 600,
    lineHeight: 1.5,
  },
  body1: {
    fontFamily: "'DM Sans', sans-serif",
    fontSize: '1rem',
    lineHeight: 1.6,
  },
  body2: {
    fontFamily: "'DM Sans', sans-serif",
    fontSize: '0.875rem',
    lineHeight: 1.5,
  },
  button: {
    fontFamily: "'DM Sans', sans-serif",
    textTransform: 'none' as const,
    fontWeight: 600,
  },
  caption: {
    fontFamily: "'DM Sans', sans-serif",
    fontSize: '0.75rem',
    lineHeight: 1.5,
  },
};

// =============================================================================
// SHARED DESIGN TOKENS - Lovable-inspired
// =============================================================================

export const sharedTokens = {
  // Severity Colors (consistent green/amber/red system)
  severity: {
    emergency: '#DC2626',    // Red - Call 911
    urgent: '#EA580C',       // Orange-Red - Severe
    severe: '#EA580C',       // Alias for urgent
    moderate: '#F59E0B',     // Amber - Moderate
    mild: '#22C55E',         // Green - Mild/OK
  },
  
  // Severity Badge Backgrounds (lighter versions)
  severityBg: {
    emergency: '#FEE2E2',    // Red background
    urgent: '#FFEDD5',       // Orange background
    severe: '#FFEDD5',       // Alias
    moderate: '#FEF3C7',     // Amber background
    mild: '#DCFCE7',         // Green background
  },
  
  // Status Colors
  status: {
    success: '#10B981',
    warning: '#F59E0B',
    error: '#EF4444',
    info: '#3B82F6',
  },
  
  // Warm Cream Gray Scale (Light Mode) - Lovable inspired
  warmLight: {
    50: '#FDFCFA',           // Warmest white
    100: '#FAF8F5',          // Cream background
    200: '#F5F3EE',          // Card hover
    300: '#E8E4DD',          // Borders
    400: '#B8B3A8',          // Muted text
    500: '#8A847A',          // Secondary text
    600: '#5C574F',          // Body text
    700: '#3D3A35',          // Headings
    800: '#2A2825',          // Dark text
    900: '#1A1917',          // Darkest
  },
  
  // Dark Mode Gray Scale
  warmDark: {
    50: '#1A1917',
    100: '#252320',
    200: '#2F2D2A',
    300: '#3D3A35',
    400: '#5C574F',
    500: '#8A847A',
    600: '#B8B3A8',
    700: '#E8E4DD',
    800: '#F5F3EE',
    900: '#FDFCFA',
  },
  
  // Soft Shadows (Lovable style)
  shadows: {
    soft: '0 4px 24px -8px rgba(0, 0, 0, 0.08)',
    warm: '0 8px 32px -12px rgba(139, 90, 43, 0.12)',
    card: '0 2px 12px -4px rgba(0, 0, 0, 0.06)',
    hover: '0 8px 24px -8px rgba(0, 0, 0, 0.12)',
    sm: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
    md: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
    lg: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
  },
  
  // Dark Mode Shadows
  shadowsDark: {
    soft: '0 4px 24px -8px rgba(0, 0, 0, 0.4)',
    warm: '0 8px 32px -12px rgba(0, 0, 0, 0.5)',
    card: '0 2px 12px -4px rgba(0, 0, 0, 0.3)',
    hover: '0 8px 24px -8px rgba(0, 0, 0, 0.5)',
    sm: '0 1px 2px 0 rgba(0, 0, 0, 0.3)',
    md: '0 4px 6px -1px rgba(0, 0, 0, 0.4), 0 2px 4px -1px rgba(0, 0, 0, 0.3)',
    lg: '0 10px 15px -3px rgba(0, 0, 0, 0.5), 0 4px 6px -2px rgba(0, 0, 0, 0.3)',
  },
  
  // Border Radius (larger for Lovable style)
  borderRadius: {
    xs: 4,
    sm: 8,
    md: 12,
    lg: 16,
    xl: 24,
    '2xl': 32,
    full: 9999,
  },
  
  // Spacing Scale
  spacing: 8,
  
  // Transitions
  transitions: {
    fast: '0.15s ease',
    normal: '0.25s ease',
    slow: '0.35s ease',
    pageEnter: '0.4s cubic-bezier(0.4, 0, 0.2, 1)',
    pageExit: '0.3s cubic-bezier(0.4, 0, 1, 1)',
  },
};

// =============================================================================
// PATIENT THEME COLORS - Warm, Healing Blue
// =============================================================================

export const patientColors = {
  light: {
    primary: {
      main: '#4F7CAC',        // Calming Blue (Lovable-inspired)
      light: '#7BA3C9',
      dark: '#3B5F8A',
      contrastText: '#FFFFFF',
    },
    secondary: {
      main: '#D4A574',        // Warm Terracotta accent
      light: '#E5C4A8',
      dark: '#B8875A',
      contrastText: '#FFFFFF',
    },
    background: {
      default: '#FAF8F5',     // Warm cream (Lovable)
      paper: '#FFFFFF',
    },
    text: {
      primary: '#3D3A35',     // Warm dark brown
      secondary: '#8A847A',   // Muted warm gray
      disabled: '#B8B3A8',
    },
    divider: '#E8E4DD',
  },
  dark: {
    primary: {
      main: '#7BA3C9',        // Lighter blue for dark mode
      light: '#A5C4DE',
      dark: '#4F7CAC',
      contrastText: '#1A1917',
    },
    secondary: {
      main: '#E5C4A8',
      light: '#F2DCC8',
      dark: '#D4A574',
      contrastText: '#1A1917',
    },
    background: {
      default: '#1A1917',     // Warm dark
      paper: '#252320',
    },
    text: {
      primary: '#F5F3EE',
      secondary: '#B8B3A8',
      disabled: '#5C574F',
    },
    divider: '#3D3A35',
  },
  // Ruby Chat Colors
  ruby: {
    primary: '#4F7CAC',
    light: '#7BA3C9',
    bubble: '#FAF8F5',
    bubbleDark: '#2F2D2A',
    border: '#E8E4DD',
  },
  // Patient Message Colors
  patient: {
    primary: '#4F7CAC',
    bubble: '#4F7CAC',
    bubbleDark: '#3B5F8A',
    text: '#FFFFFF',
  },
};

// =============================================================================
// DOCTOR THEME COLORS - Professional, Clinical
// =============================================================================

export const doctorColors = {
  light: {
    primary: {
      main: '#1E3A5F',        // Clinical Navy
      light: '#2E5077',
      dark: '#0F2942',
      contrastText: '#FFFFFF',
    },
    secondary: {
      main: '#4F7CAC',        // Same calming blue as patient
      light: '#7BA3C9',
      dark: '#3B5F8A',
      contrastText: '#FFFFFF',
    },
    background: {
      default: '#FAF8F5',     // Warm cream (consistent)
      paper: '#FFFFFF',
    },
    text: {
      primary: '#1E293B',
      secondary: '#64748B',
      disabled: '#94A3B8',
    },
    divider: '#E8E4DD',
  },
  dark: {
    primary: {
      main: '#3B82F6',
      light: '#60A5FA',
      dark: '#2563EB',
      contrastText: '#1A1917',
    },
    secondary: {
      main: '#7BA3C9',
      light: '#A5C4DE',
      dark: '#4F7CAC',
      contrastText: '#1A1917',
    },
    background: {
      default: '#1A1917',
      paper: '#252320',
    },
    text: {
      primary: '#F1F5F9',
      secondary: '#94A3B8',
      disabled: '#64748B',
    },
    divider: '#3D3A35',
  },
  accent: {
    teal: '#0D9488',
    indigo: '#4F46E5',
    amber: '#D97706',
  },
};

// =============================================================================
// LEFT BORDER CARD COLORS (Lovable pattern)
// =============================================================================

export const cardBorderColors = {
  primary: '#4F7CAC',
  shared: '#4F7CAC',       // For doctor-shared items
  severe: '#DC2626',
  moderate: '#F59E0B',
  mild: '#22C55E',
  new: '#8B5CF6',          // Purple for "New" items
};

// =============================================================================
// THEME FACTORY FUNCTIONS
// =============================================================================

const createPatientThemeOptions = (mode: PaletteMode): ThemeOptions => {
  const colors = mode === 'dark' ? patientColors.dark : patientColors.light;
  const warm = mode === 'dark' ? sharedTokens.warmDark : sharedTokens.warmLight;
  const shadows = mode === 'dark' ? sharedTokens.shadowsDark : sharedTokens.shadows;
  
  return {
    breakpoints,
    typography,
    palette: {
      mode,
      primary: colors.primary,
      secondary: colors.secondary,
      background: colors.background,
      text: colors.text,
      divider: colors.divider,
      success: { main: sharedTokens.severity.mild, light: sharedTokens.severityBg.mild },
      warning: { main: sharedTokens.severity.moderate, light: sharedTokens.severityBg.moderate },
      error: { main: sharedTokens.severity.emergency, light: sharedTokens.severityBg.emergency },
      info: { main: sharedTokens.status.info },
      grey: warm,
    },
    shape: {
      borderRadius: sharedTokens.borderRadius.md,
    },
    spacing: sharedTokens.spacing,
    components: {
      MuiCssBaseline: {
        styleOverrides: {
          body: {
            backgroundColor: colors.background.default,
            transition: 'background-color 0.3s ease, color 0.3s ease',
          },
        },
      },
      MuiButton: {
        styleOverrides: {
          root: {
            borderRadius: sharedTokens.borderRadius.lg,
            padding: '10px 24px',
            fontWeight: 600,
            minHeight: 44,
            transition: `all ${sharedTokens.transitions.normal}`,
            '@media (max-width:600px)': {
              minHeight: 48,
              padding: '12px 24px',
            },
          },
          contained: {
            boxShadow: shadows.soft,
            '&:hover': {
              boxShadow: shadows.hover,
              transform: 'translateY(-1px)',
            },
          },
        },
      },
      MuiCard: {
        styleOverrides: {
          root: {
            borderRadius: sharedTokens.borderRadius.xl,
            boxShadow: shadows.soft,
            border: `1px solid ${colors.divider}`,
            transition: `all ${sharedTokens.transitions.normal}`,
            '&:hover': {
              boxShadow: shadows.hover,
            },
          },
        },
      },
      MuiPaper: {
        styleOverrides: {
          root: {
            borderRadius: sharedTokens.borderRadius.xl,
          },
        },
      },
      MuiTextField: {
        styleOverrides: {
          root: {
            '& .MuiOutlinedInput-root': {
              borderRadius: sharedTokens.borderRadius.md,
              transition: `all ${sharedTokens.transitions.fast}`,
              '&:hover .MuiOutlinedInput-notchedOutline': {
                borderColor: colors.primary.light,
              },
            },
          },
        },
      },
      MuiChip: {
        styleOverrides: {
          root: {
            borderRadius: sharedTokens.borderRadius.lg,
            fontWeight: 500,
          },
        },
      },
      MuiDrawer: {
        styleOverrides: {
          paper: {
            borderRadius: 0,
            backgroundColor: colors.background.paper,
          },
        },
      },
      MuiBadge: {
        styleOverrides: {
          badge: {
            fontWeight: 600,
            fontSize: '0.75rem',
          },
        },
      },
    },
  };
};

const createDoctorThemeOptions = (mode: PaletteMode): ThemeOptions => {
  const colors = mode === 'dark' ? doctorColors.dark : doctorColors.light;
  const warm = mode === 'dark' ? sharedTokens.warmDark : sharedTokens.warmLight;
  const shadows = mode === 'dark' ? sharedTokens.shadowsDark : sharedTokens.shadows;
  
  return {
    breakpoints,
    typography,
    palette: {
      mode,
      primary: colors.primary,
      secondary: colors.secondary,
      background: colors.background,
      text: colors.text,
      divider: colors.divider,
      success: { main: sharedTokens.severity.mild, light: sharedTokens.severityBg.mild },
      warning: { main: sharedTokens.severity.moderate, light: sharedTokens.severityBg.moderate },
      error: { main: sharedTokens.severity.emergency, light: sharedTokens.severityBg.emergency },
      info: { main: sharedTokens.status.info },
      grey: warm,
    },
    shape: {
      borderRadius: sharedTokens.borderRadius.md,
    },
    spacing: sharedTokens.spacing,
    components: {
      MuiCssBaseline: {
        styleOverrides: {
          body: {
            backgroundColor: colors.background.default,
            transition: 'background-color 0.3s ease, color 0.3s ease',
          },
        },
      },
      MuiButton: {
        styleOverrides: {
          root: {
            borderRadius: sharedTokens.borderRadius.md,
            padding: '8px 20px',
            fontWeight: 600,
            minHeight: 40,
            transition: `all ${sharedTokens.transitions.normal}`,
            '@media (max-width:600px)': {
              minHeight: 44,
            },
          },
          contained: {
            boxShadow: 'none',
            '&:hover': {
              boxShadow: shadows.soft,
            },
          },
        },
      },
      MuiCard: {
        styleOverrides: {
          root: {
            borderRadius: sharedTokens.borderRadius.xl,
            boxShadow: shadows.soft,
            border: `1px solid ${colors.divider}`,
            transition: `all ${sharedTokens.transitions.normal}`,
          },
        },
      },
      MuiPaper: {
        styleOverrides: {
          root: {
            borderRadius: sharedTokens.borderRadius.lg,
          },
        },
      },
      MuiTableCell: {
        styleOverrides: {
          head: {
            fontWeight: 600,
            backgroundColor: mode === 'dark' ? warm[100] : warm[50],
          },
        },
      },
      MuiTableRow: {
        styleOverrides: {
          root: {
            transition: `background-color ${sharedTokens.transitions.fast}`,
            '&:hover': {
              backgroundColor: mode === 'dark' ? warm[100] : warm[100],
            },
          },
        },
      },
      MuiChip: {
        styleOverrides: {
          root: {
            borderRadius: sharedTokens.borderRadius.md,
            fontWeight: 600,
          },
        },
      },
      MuiDrawer: {
        styleOverrides: {
          paper: {
            backgroundColor: mode === 'dark' ? colors.background.paper : doctorColors.light.primary.main,
            color: mode === 'dark' ? colors.text.primary : '#FFFFFF',
          },
        },
      },
    },
  };
};

// =============================================================================
// THEME EXPORTS
// =============================================================================

export const patientTheme = responsiveFontSizes(createTheme(createPatientThemeOptions('light')));
export const doctorTheme = responsiveFontSizes(createTheme(createDoctorThemeOptions('light')));
export const patientDarkTheme = responsiveFontSizes(createTheme(createPatientThemeOptions('dark')));
export const doctorDarkTheme = responsiveFontSizes(createTheme(createDoctorThemeOptions('dark')));

// Aliases for backward compatibility
export const patientThemeDark = patientDarkTheme;
export const doctorThemeDark = doctorDarkTheme;

export const createPatientTheme = (mode: PaletteMode) => 
  responsiveFontSizes(createTheme(createPatientThemeOptions(mode)));

export const createDoctorTheme = (mode: PaletteMode) => 
  responsiveFontSizes(createTheme(createDoctorThemeOptions(mode)));

// =============================================================================
// SEVERITY HELPERS (Lovable-style consistent system)
// =============================================================================

export const getSeverityColor = (level: 'emergency' | 'urgent' | 'severe' | 'moderate' | 'mild') => {
  return sharedTokens.severity[level] || sharedTokens.severity.mild;
};

export const getSeverityBgColor = (level: 'emergency' | 'urgent' | 'severe' | 'moderate' | 'mild') => {
  return sharedTokens.severityBg[level] || sharedTokens.severityBg.mild;
};

export const getSeverityLabel = (level: string) => {
  const labels: Record<string, string> = {
    emergency: 'Emergency',
    urgent: 'Urgent',
    severe: 'Severe',
    moderate: 'Moderate',
    mild: 'Mild',
  };
  return labels[level.toLowerCase()] || level;
};

// Natural language severity (Lovable style)
export const getSeverityDescription = (level: string) => {
  const descriptions: Record<string, string> = {
    emergency: 'requires immediate medical attention',
    urgent: 'rated as severe',
    severe: 'rated as severe',
    moderate: 'rated as moderate',
    mild: 'rated as mild',
  };
  return descriptions[level.toLowerCase()] || level;
};

// =============================================================================
// ANIMATIONS
// =============================================================================

export const animations = {
  fadeIn: `
    @keyframes fadeIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }
  `,
  fadeInUp: `
    @keyframes fadeInUp {
      from {
        opacity: 0;
        transform: translateY(20px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }
  `,
  slideInLeft: `
    @keyframes slideInLeft {
      from {
        opacity: 0;
        transform: translateX(-30px);
      }
      to {
        opacity: 1;
        transform: translateX(0);
      }
    }
  `,
  slideInRight: `
    @keyframes slideInRight {
      from {
        opacity: 0;
        transform: translateX(30px);
      }
      to {
        opacity: 1;
        transform: translateX(0);
      }
    }
  `,
  scaleIn: `
    @keyframes scaleIn {
      from {
        opacity: 0;
        transform: scale(0.95);
      }
      to {
        opacity: 1;
        transform: scale(1);
      }
    }
  `,
};

// CSS class-based animations for use with className prop
export const animationClasses = {
  fadeIn: 'animate-fade-in',
  fadeInUp: 'animate-fade-in-up',
  slideInLeft: 'animate-slide-in-left',
  slideInRight: 'animate-slide-in-right',
  scaleIn: 'animate-scale-in',
  staggered: 'animate-staggered',
};

// =============================================================================
// LEGACY EXPORTS (backward compatibility)
// =============================================================================

export const theme = {
  colors: {
    primary: patientColors.light.primary.main,
    secondary: sharedTokens.warmLight[500],
    success: sharedTokens.severity.mild,
    danger: sharedTokens.severity.emergency,
    warning: sharedTokens.severity.moderate,
    info: sharedTokens.status.info,
    light: sharedTokens.warmLight[100],
    dark: sharedTokens.warmLight[800],
    white: '#ffffff',
    cream: '#FAF8F5',
    gray: sharedTokens.warmLight,
  },
  fonts: {
    body: "'DM Sans', sans-serif",
    heading: "'Fraunces', Georgia, serif",
  },
  fontSizes: {
    xs: '0.75rem',
    sm: '0.875rem',
    base: '1rem',
    lg: '1.125rem',
    xl: '1.25rem',
    '2xl': '1.5rem',
    '3xl': '1.875rem',
    '4xl': '2.25rem',
  },
  spacing: {
    xs: '0.25rem',
    sm: '0.5rem',
    md: '1rem',
    lg: '1.5rem',
    xl: '2rem',
    '2xl': '3rem',
  },
  borderRadius: sharedTokens.borderRadius,
  transitions: sharedTokens.transitions,
  shadows: sharedTokens.shadows,
  severity: sharedTokens.severity,
  severityBg: sharedTokens.severityBg,
  cardBorderColors,
  animations,
};

export type Theme = typeof theme;
