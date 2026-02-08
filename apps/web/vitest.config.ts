import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
    globals: true,
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      // Stub @sentry/nextjs so Vite's import analysis does not fail when the
      // package is not installed. The module exports are mocked in individual
      // test files via vi.mock.
      "@sentry/nextjs": path.resolve(__dirname, "./src/types/__mocks__/sentry.ts"),
    },
  },
});
