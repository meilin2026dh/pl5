import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
export default defineConfig({
  plugins: [react()],
  base: "/",
  server: { proxy: { "/api": "http://127.0.0.1:3001" } },
  test: {
    // Keep the web-app test suite independent from the archived PL5 research sources.
    // Research Python/TypeScript integration tests have separate package-relative runners.
    include: ["tests/**/*.{test,spec}.{ts,tsx,js,jsx}"],
    testTimeout: 10000,
  },
});
