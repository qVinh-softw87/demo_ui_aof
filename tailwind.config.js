/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      "colors": {
          "secondary-fixed": "#ffddb8",
          "on-primary-container": "#b4bcff",
          "on-secondary-fixed": "#2a1700",
          "on-secondary-container": "#684000",
          "secondary-container": "#fea619",
          "tertiary-fixed": "#dae2fd",
          "surface-container-high": "#dce9ff",
          "primary-fixed-dim": "#bbc3ff",
          "inverse-surface": "#213145",
          "surface": "#f8f9ff",
          "on-primary-fixed-variant": "#2438ae",
          "on-background": "#0b1c30",
          "on-tertiary-container": "#b8c0da",
          "surface-dim": "#cbdbf5",
          "surface-container-lowest": "#ffffff",
          "on-secondary-fixed-variant": "#653e00",
          "surface-variant": "#d3e4fe",
          "surface-tint": "#4052c7",
          "tertiary-container": "#464e64",
          "primary-fixed": "#dfe0ff",
          "tertiary-fixed-dim": "#bec6e0",
          "error-container": "#ffdad6",
          "on-secondary": "#ffffff",
          "surface-container-highest": "#d3e4fe",
          "on-primary-fixed": "#000e5f",
          "on-error-container": "#93000a",
          "tertiary": "#30374c",
          "secondary-fixed-dim": "#ffb95f",
          "surface-container-low": "#eff4ff",
          "on-error": "#ffffff",
          "on-tertiary-fixed-variant": "#3f465c",
          "primary-container": "#2e41b6",
          "inverse-primary": "#bbc3ff",
          "on-tertiary-fixed": "#131b2e",
          "outline-variant": "#c5c5d6",
          "on-tertiary": "#ffffff",
          "on-surface-variant": "#454653",
          "inverse-on-surface": "#eaf1ff",
          "surface-container": "#e5eeff",
          "background": "#f8f9ff",
          "secondary": "#855300",
          "outline": "#757685",
          "surface-bright": "#f8f9ff",
          "error": "#ba1a1a",
          "primary": "#0d259f",
          "on-surface": "#0b1c30",
          "on-primary": "#ffffff"
      },
      "borderRadius": {
          "DEFAULT": "0.25rem",
          "lg": "0.5rem",
          "xl": "0.75rem",
          "full": "9999px"
      },
      "spacing": {
          "stack-md": "16px",
          "margin-desktop": "40px",
          "stack-sm": "8px",
          "gutter": "24px",
          "unit": "4px",
          "stack-lg": "32px",
          "container-max": "1280px",
          "margin-mobile": "16px"
      },
      "fontFamily": {
          "body-lg": ["Inter", "sans-serif"],
          "caption": ["Inter", "sans-serif"],
          "body-md": ["Inter", "sans-serif"],
          "headline-md": ["Inter", "sans-serif"],
          "label-mono": ["JetBrains Mono", "monospace"],
          "display-lg": ["Inter", "sans-serif"]
      },
      "fontSize": {
          "body-lg": ["18px", {"lineHeight": "28px", "fontWeight": "400"}],
          "caption": ["12px", {"lineHeight": "16px", "fontWeight": "500"}],
          "body-md": ["16px", {"lineHeight": "24px", "fontWeight": "400"}],
          "headline-md": ["24px", {"lineHeight": "32px", "fontWeight": "600"}],
          "label-mono": ["14px", {"lineHeight": "20px", "letterSpacing": "0.05em", "fontWeight": "500"}],
          "display-lg": ["48px", {"lineHeight": "56px", "letterSpacing": "-0.02em", "fontWeight": "700"}]
      }
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/container-queries')
  ],
}

