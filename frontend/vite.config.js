import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Proxy API and WebSocket traffic to the Django backend during development.
export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.js",
    // The __Host- cookie prefix is only settable on a secure (https) origin —
    // jsdom's cookie jar enforces this per spec, so tests exercising the
    // __Host-csrftoken cookie need an https:// test URL, matching production.
    environmentOptions: {
      jsdom: {
        url: "https://securebid.test",
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/images": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/ws": {
        target: "ws://localhost:8000",
        ws: true,
        changeOrigin: true,
      },
    },
  },
});
