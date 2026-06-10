/**
 * OncoLife Theme Context
 * Provides dark mode toggle functionality
 */

import React, { createContext, useContext, useState, useEffect, useMemo, ReactNode } from 'react';
import { ThemeProvider as MuiThemeProvider, PaletteMode } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { createPatientTheme, createDoctorTheme } from '../styles/theme';

interface ThemeContextType {
  mode: PaletteMode;
  toggleTheme: () => void;
  setMode: (mode: PaletteMode) => void;
  isDark: boolean;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

interface ThemeProviderProps {
  children: ReactNode;
  appType: 'patient' | 'doctor';
  defaultMode?: PaletteMode;
  storageKey?: string;
}

export const OncolifeThemeProvider: React.FC<ThemeProviderProps> = ({
  children,
  appType,
  defaultMode = 'light',
  storageKey = 'oncolife-theme-mode',
}) => {
  // Initialize from localStorage or default
  const [mode, setModeState] = useState<PaletteMode>(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem(storageKey);
      if (stored === 'dark' || stored === 'light') {
        return stored;
      }
      // Check system preference
      if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        return 'dark';
      }
    }
    return defaultMode;
  });

  // Listen for system theme changes
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleChange = (e: MediaQueryListEvent) => {
      const stored = localStorage.getItem(storageKey);
      // Only auto-switch if user hasn't manually set preference
      if (!stored) {
        setModeState(e.matches ? 'dark' : 'light');
      }
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, [storageKey]);

  // Persist to localStorage
  useEffect(() => {
    localStorage.setItem(storageKey, mode);
    // Update document attribute for CSS targeting
    document.documentElement.setAttribute('data-theme', mode);
  }, [mode, storageKey]);

  const toggleTheme = () => {
    setModeState((prev) => (prev === 'light' ? 'dark' : 'light'));
  };

  const setMode = (newMode: PaletteMode) => {
    setModeState(newMode);
  };

  // Create theme based on app type and mode
  const theme = useMemo(() => {
    return appType === 'patient' 
      ? createPatientTheme(mode) 
      : createDoctorTheme(mode);
  }, [appType, mode]);

  const contextValue = useMemo(() => ({
    mode,
    toggleTheme,
    setMode,
    isDark: mode === 'dark',
  }), [mode]);

  return (
    <ThemeContext.Provider value={contextValue}>
      <MuiThemeProvider theme={theme}>
        <CssBaseline />
        {children}
      </MuiThemeProvider>
    </ThemeContext.Provider>
  );
};

export const useThemeMode = (): ThemeContextType => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useThemeMode must be used within an OncolifeThemeProvider');
  }
  return context;
};

export default ThemeContext;



