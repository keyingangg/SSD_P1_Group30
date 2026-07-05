import { describe, it, expect, beforeEach } from "vitest";

import axiosClient from "./axiosClient.js";

function clearCookies() {
  document.cookie.split(";").forEach((c) => {
    const name = c.split("=")[0].trim();
    // Include Secure so this expiry write is also accepted for __Host- cookies
    // — tough-cookie (jsdom's cookie jar) rejects overwrites of a __Host-
    // cookie that don't themselves satisfy the prefix's own requirements.
    if (name) document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/; Secure`;
  });
}

// AxiosHeaders (axios >=1.x) may normalise header storage, so read via .get()
// when available rather than assuming a plain object.
function getHeader(config, name) {
  if (config.headers && typeof config.headers.get === "function") {
    return config.headers.get(name);
  }
  return config.headers?.[name];
}

// Swap in a fake adapter that captures the outgoing request config instead of
// making a real network call, then restore nothing needed since each test
// overwrites it fresh.
async function captureRequestConfig(path = "/test/") {
  let captured;
  axiosClient.defaults.adapter = async (config) => {
    captured = config;
    return { data: {}, status: 200, statusText: "OK", headers: {}, config };
  };
  await axiosClient.get(path);
  return captured;
}

describe("axiosClient CSRF header handling", () => {
  beforeEach(() => {
    clearCookies();
  });

  it("attaches __Host-csrftoken as the X-CSRFToken header when present", async () => {
    // The __Host- prefix requires the Secure attribute (and a secure origin,
    // configured via environmentOptions.jsdom.url in vite.config.js) — this
    // mirrors the real constraint the cookie carries in production.
    document.cookie = "__Host-csrftoken=secure-token-value; Secure";
    const config = await captureRequestConfig();
    expect(getHeader(config, "X-CSRFToken")).toBe("secure-token-value");
  });

  it("falls back to the plain csrftoken cookie when __Host- is absent", async () => {
    document.cookie = "csrftoken=dev-token-value";
    const config = await captureRequestConfig();
    expect(getHeader(config, "X-CSRFToken")).toBe("dev-token-value");
  });

  it("prefers __Host-csrftoken over csrftoken when both are present", async () => {
    document.cookie = "csrftoken=dev-token-value";
    document.cookie = "__Host-csrftoken=secure-token-value; Secure";
    const config = await captureRequestConfig();
    expect(getHeader(config, "X-CSRFToken")).toBe("secure-token-value");
  });

  it("sends no CSRF header when neither cookie is present", async () => {
    const config = await captureRequestConfig();
    expect(getHeader(config, "X-CSRFToken")).toBeFalsy();
  });

  it("includes credentials on every request so the session cookie is sent", async () => {
    const config = await captureRequestConfig();
    expect(config.withCredentials).toBe(true);
  });
});
