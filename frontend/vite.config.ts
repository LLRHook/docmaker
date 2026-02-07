import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  base: "./",
  build: {
    outDir: "dist",
    emptyOutDir: true,
    rollupOptions: {
      output: {
        manualChunks: {
          "vendor-react": ["react", "react-dom"],
          "vendor-graph": ["cytoscape", "cytoscape-fcose", "react-cytoscapejs"],
        },
      },
    },
  },
  server: {
    port: 5173,
    strictPort: true,
  },
});
