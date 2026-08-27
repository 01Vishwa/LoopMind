import type { Config } from "tailwindcss";

/** Wrap a `--vera-*-rgb` channel token so opacity utilities work. */
const channel = (name: string) => `rgb(var(--vera-${name}-rgb) / <alpha-value>)`;

const config: Config = {
  // Dark is the default (bare `:root`); `.light` opts out. This makes
  // `dark:` variants resolve to "not light" so they track the real theme.
  darkMode: ["selector", ":root:not(.light)"],
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "Menlo", "monospace"],
      },
      colors: {
        vera: {
          ink: channel("ink"),
          paper: channel("paper"),
          surface: channel("surface"),
          "surface-2": channel("surface-2"),
          muted: channel("muted"),
          subtle: channel("subtle"),
          border: channel("border"),
          "border-subtle": channel("border-subtle"),
          "border-strong": channel("border-strong"),
          accent: channel("accent"),
          "accent-hover": channel("accent-hover"),
          "accent-muted": channel("accent-muted"),
          "accent-glow": "rgb(var(--vera-accent-rgb) / 0.15)",
          verified: channel("verified"),
          "verified-muted": channel("verified-muted"),
          insufficient: channel("insufficient"),
          "insufficient-muted": channel("insufficient-muted"),
          backtrack: channel("backtrack"),
          "backtrack-muted": channel("backtrack-muted"),
          warning: channel("warning"),
          "warning-muted": channel("warning-muted"),
          "code-bg": channel("code-bg"),
          "code-bg-2": channel("code-bg-2"),
          "code-fg": channel("code-fg"),
          "code-border": channel("code-border"),
        },
      },
      borderRadius: {
        card: "6px",
        input: "4px",
        badge: "2px",
      },
      animation: {
        "step-pulse": "stepPulse 2s ease-in-out infinite",
        "shimmer": "shimmer 1.5s ease-in-out infinite",
        "slide-up": "slideUp 200ms ease-out",
        "slide-in-left": "slideInLeft 150ms ease-out",
      },
      keyframes: {
        stepPulse: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.5" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        slideUp: {
          from: { transform: "translateY(24px)", opacity: "0" },
          to: { transform: "translateY(0)", opacity: "1" },
        },
        slideInLeft: {
          from: { transform: "translateX(-12px)", opacity: "0" },
          to: { transform: "translateX(0)", opacity: "1" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
