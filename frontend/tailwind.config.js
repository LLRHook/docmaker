/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // Node type colors
        "node-class": "#3b82f6", // blue-500
        "node-interface": "#a855f7", // purple-500
        "node-endpoint": "#22c55e", // green-500
        "node-package": "#6b7280", // gray-500
        "node-file": "#f97316", // orange-500
        // Category colors
        "cat-backend": "#3b82f6", // blue-500
        "cat-frontend": "#22c55e", // green-500
        "cat-config": "#f59e0b", // amber-500
        "cat-test": "#6b7280", // gray-500
      },
    },
  },
  plugins: [],
};
