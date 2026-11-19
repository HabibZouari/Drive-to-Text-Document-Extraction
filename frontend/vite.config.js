import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In development the React app runs on :5173 and forwards /api calls to the
// FastAPI backend. In production FastAPI serves the built files itself.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": process.env.API_URL || "http://localhost:8000",
    },
  },
});
