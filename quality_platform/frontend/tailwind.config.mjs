/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          // Al-Mawadda (مركز المودة) teal identity. Key names kept for
          // backward-compat with existing className usages (brand-red*, etc.).
          redDark: "#1C5E58",   // darkest teal — headings
          red: "#2E9E95",       // teal
          redSoft: "#E3F3F1",   // soft teal — badges / backgrounds
          primary: "#2E9E95",   // main teal — buttons / accents
          secondary: "#217A72", // darker teal — hovers
          dark: "#1C5E58",      // darkest teal
        },
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-out forwards',
        'zoom-in': 'zoomIn 0.5s ease-out forwards',
        'slide-up': 'slideUp 0.5s ease-out forwards',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        zoomIn: {
          '0%': { opacity: '0', transform: 'scale(0.95)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-12px)' },
        }
      }
    },
  },
  plugins: [],
};

