import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The dev server forwards /api to the FastAPI backend, so the app and API
// share one origin and no CORS setup is needed. Override with API_URL.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": process.env.API_URL ?? "http://127.0.0.1:8000",
    },
  },
});
