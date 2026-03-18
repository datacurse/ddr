import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  presets: [require("nativewind/preset")],
  theme: {
    extend: {
      colors: {
        surface: "var(--color-surface)",
        foreground: "var(--color-foreground)",
        stale: "var(--color-stale)",
        muted: "var(--color-muted)",
        subtle: "var(--color-subtle)",
        faint: "var(--color-faint)",
        disabled: "var(--color-disabled)",
        border: "var(--color-border)",
        "border-muted": "var(--color-border-muted)",
        overlay: "var(--color-overlay)",
        "overlay-subtle": "var(--color-overlay-subtle)",
        fill: "var(--color-fill)",
      },
      fontFamily: {
        'ibm-light': ['IBMPlexMono_300Light'],
        'ibm': ['IBMPlexMono_400Regular'],
        'ibm-medium': ['IBMPlexMono_500Medium'],
      },
    },
  },
  plugins: [],
};

export default config;
