import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// The repository also carries historical, separately rooted research fixtures
// (github_overlay/ and integration_tests/). They are not tests of this app.
// Run only the active application's tests here; test the historical fixtures
// from their own roots in the research integration workflow.
export default defineConfig({
  plugins: [react()],
  test: {
    include: ["tests/**/*.test.ts", "tests/**/*.test.tsx"],
    // Heavy full-space research/innovation tests can exceed Vitest's 5s
    // default when CI shares CPU. This changes only the time limit, not checks.
    testTimeout: 20_000,
  },
});
