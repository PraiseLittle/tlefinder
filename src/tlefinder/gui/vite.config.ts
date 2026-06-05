import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "src") },
  },
  server: {
    port: 2627,
    proxy: {
      // Forward API calls to the FastAPI app during dev.
      // Override with VITE_API_BASE_URL in .env.local if your API runs elsewhere.
      "/api": {
        target: "http://127.0.0.1:2626",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: true,
  },
});
