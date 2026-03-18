export type ThemePreference = 'light' | 'dark' | 'system';
export type ResolvedTheme = 'light' | 'dark';

export const themeColors = {
  light: {
    muted: 'rgba(0,0,0,0.5)',
    track: 'rgba(0,0,0,0.12)',
    thumb: 'rgba(0,0,0,0.6)',
    canvas: {
      surface: '#f5f4f0',
      foreground: '#1a1a1a',
      subtle: 'rgba(0,0,0,0.35)',
      border: 'rgba(0,0,0,0.4)',
      borderMuted: 'rgba(0,0,0,0.08)',
      fill: 'rgba(0,0,0,0.1)',
      overlaySubtle: 'rgba(0,0,0,0.04)',
      routeLine: 'rgba(100,200,255,0.3)',
      robotAccent: 'rgba(100,200,255,0.6)',
      targetFill: 'rgba(0,0,0,0.1)',
    },
  },
  dark: {
    muted: 'rgba(255,255,255,0.45)',
    track: 'rgba(255,255,255,0.1)',
    thumb: 'rgba(255,255,255,0.55)',
    canvas: {
      surface: '#0a0a0a',
      foreground: 'rgba(255,255,255,0.87)',
      subtle: 'rgba(255,255,255,0.3)',
      border: 'rgba(255,255,255,0.4)',
      borderMuted: 'rgba(255,255,255,0.06)',
      fill: 'rgba(255,255,255,0.1)',
      overlaySubtle: 'rgba(255,255,255,0.04)',
      routeLine: 'rgba(100,200,255,0.3)',
      robotAccent: 'rgba(100,200,255,0.6)',
      targetFill: 'rgba(255,255,255,0.1)',
    },
  },
} as const;
