import { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { useColorScheme } from 'nativewind';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { themeColors, type ThemePreference, type ResolvedTheme } from '@/lib/theme';

const STORAGE_KEY = 'theme-preference';

interface ThemeContextValue {
  preference: ThemePreference;
  resolved: ResolvedTheme;
  colors: (typeof themeColors)[ResolvedTheme];
  setPreference: (pref: ThemePreference) => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const { colorScheme, setColorScheme } = useColorScheme();
  const [preference, setPreferenceState] = useState<ThemePreference>('system');
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    AsyncStorage.getItem(STORAGE_KEY).then((stored) => {
      if (stored === 'light' || stored === 'dark' || stored === 'system') {
        setPreferenceState(stored);
        setColorScheme(stored);
      }
      setLoaded(true);
    });
  }, []);

  const setPreference = useCallback((pref: ThemePreference) => {
    setPreferenceState(pref);
    setColorScheme(pref);
    AsyncStorage.setItem(STORAGE_KEY, pref);
  }, [setColorScheme]);

  const resolved: ResolvedTheme = colorScheme ?? 'light';
  const colors = themeColors[resolved];

  if (!loaded) return null;

  return (
    <ThemeContext.Provider value={{ preference, resolved, colors, setPreference }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider');
  return ctx;
}
