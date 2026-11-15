import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// `base: "./"` keeps every asset path relative, so the built site works from any sub-path
// (GitHub Pages, a folder inside another team's site) without reconfiguring.
export default defineConfig({
  plugins: [react()],
  base: "./",
  build: {
    // MapLibre is most of the bundle; keep it (and Recharts) in their own cacheable chunks.
    chunkSizeWarningLimit: 900,
    rollupOptions: {
      output: { manualChunks: { maplibre: ["maplibre-gl"], recharts: ["recharts"] } },
    },
  },
  server: {
    // In VITE_DATA_MODE=api, requests to /api go to the FastAPI dev server.
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
});
