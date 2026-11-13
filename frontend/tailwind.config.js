/** Token màu lấy từ bộ biến Figma (Phòng Ơi · cam ấm). Giá trị thật nằm ở CSS variables trong index.css,
 *  nên giao diện sáng/tối đổi chỉ bằng class "dark" trên <html>. */
const v = (name) => `rgb(var(--${name}) / <alpha-value>)`;

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: { sans: ['"Be Vietnam Pro"', "system-ui", "sans-serif"] },
      colors: {
        canvas: v("bg-canvas"),
        surface: v("bg-surface"),
        muted: v("bg-muted"),
        line: v("border"),
        "line-strong": v("border-strong"),
        ink: v("text"),
        "ink-2": v("text-2"),
        "ink-3": v("text-3"),
        "on-primary": v("on-primary"),
        primary: { DEFAULT: v("primary"), 700: v("primary-700"), 100: v("primary-100"), 50: v("primary-50") },
        accent: { DEFAULT: v("accent"), 50: v("accent-50"), 800: v("accent-800") },
        violet: { DEFAULT: v("violet"), 50: v("violet-50") },
        success: { DEFAULT: v("success"), 50: v("success-50") },
        warning: { DEFAULT: v("warning"), 50: v("warning-50") },
        danger: { DEFAULT: v("danger"), 50: v("danger-50") },
      },
      borderRadius: { sm: "8px", md: "12px", lg: "16px", xl: "24px", "2xl": "32px" },
      fontSize: {
        "display-l": ["48px", { lineHeight: "1.15", fontWeight: "800", letterSpacing: "-0.02em" }],
        "display-xl": ["64px", { lineHeight: "1.1", fontWeight: "800", letterSpacing: "-0.02em" }],
        h1: ["36px", { lineHeight: "1.2", fontWeight: "700", letterSpacing: "-0.01em" }],
        h2: ["28px", { lineHeight: "1.25", fontWeight: "700" }],
        h3: ["22px", { lineHeight: "1.3", fontWeight: "700" }],
        h4: ["18px", { lineHeight: "1.35", fontWeight: "600" }],
      },
      boxShadow: {
        sm: "0 1px 2px rgb(15 23 42 / 0.06), 0 1px 3px rgb(15 23 42 / 0.04)",
        md: "0 4px 12px rgb(15 23 42 / 0.08)",
        lg: "0 12px 32px rgb(15 23 42 / 0.12)",
        glow: "0 8px 28px rgb(234 88 12 / 0.35)",
      },
      keyframes: {
        drift: { "0%,100%": { transform: "translate(0,0) scale(1)" }, "50%": { transform: "translate(-40px,24px) scale(1.06)" } },
        float: { "0%,100%": { transform: "translateY(0)" }, "50%": { transform: "translateY(-8px)" } },
        shimmer: { "0%": { backgroundPosition: "-400px 0" }, "100%": { backgroundPosition: "400px 0" } },
      },
      animation: {
        drift: "drift 18s ease-in-out infinite",
        float: "float 6s ease-in-out infinite",
        shimmer: "shimmer 1.2s linear infinite",
      },
    },
  },
  plugins: [],
};
