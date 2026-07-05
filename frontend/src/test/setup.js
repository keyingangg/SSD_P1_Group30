import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

// Unmount rendered trees between tests (fires effect cleanups, e.g.
// clearInterval) since `globals: true` is not set in vite.config.js.
afterEach(() => {
  cleanup();
});
