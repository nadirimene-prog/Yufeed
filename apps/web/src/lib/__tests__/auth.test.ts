import { describe, it, expect, beforeEach } from "vitest";
import {
  clearAuthTokens,
  getAuthToken,
  getAuthUserProfile,
  setAuthTokens,
} from "../auth";

// Helper to create a valid JWT with tenant_id
function makeJwt(
  payload: Record<string, unknown>,
  expInSeconds = 3600,
): string {
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const body = btoa(
    JSON.stringify({
      exp: Math.floor(Date.now() / 1000) + expInSeconds,
      ...payload,
    }),
  );
  return `${header}.${body}.fakesig`;
}

describe("auth", () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
  });

  describe("setAuthTokens", () => {
    it("stores access_token in localStorage by default", () => {
      setAuthTokens({ access_token: "tok123" });
      expect(localStorage.getItem("access_token")).toBe("tok123");
    });

    it("stores in sessionStorage when specified", () => {
      setAuthTokens({ access_token: "tok456" }, "session");
      expect(sessionStorage.getItem("access_token")).toBe("tok456");
      expect(localStorage.getItem("access_token")).toBeNull();
    });

    it("stores refresh_token and token_type when provided", () => {
      setAuthTokens({
        access_token: "a",
        refresh_token: "r",
        token_type: "bearer",
      });
      expect(localStorage.getItem("refresh_token")).toBe("r");
      expect(localStorage.getItem("token_type")).toBe("bearer");
    });
  });

  describe("getAuthToken", () => {
    it("returns null when no token is stored", () => {
      expect(getAuthToken()).toBeNull();
    });

    it("returns a valid token from localStorage", () => {
      const jwt = makeJwt({ tenant_id: "acme" });
      localStorage.setItem("access_token", jwt);
      expect(getAuthToken()).toBe(jwt);
    });

    it("returns null for expired tokens and removes them", () => {
      const expired = makeJwt({ tenant_id: "acme" }, -100);
      localStorage.setItem("access_token", expired);
      expect(getAuthToken()).toBeNull();
      expect(localStorage.getItem("access_token")).toBeNull();
    });

    it("returns token for tokens without tenant_id", () => {
      const noTenant = makeJwt({ sub: "user1" });
      localStorage.setItem("access_token", noTenant);
      expect(getAuthToken()).toBe(noTenant);
    });

    it("falls back to legacy keys", () => {
      const jwt = makeJwt({ tenant_id: "acme" });
      localStorage.setItem("auth_token", jwt);
      expect(getAuthToken()).toBe(jwt);
    });
  });

  describe("clearAuthTokens", () => {
    it("removes all token keys from both storages", () => {
      const jwt = makeJwt({ tenant_id: "acme" });
      localStorage.setItem("access_token", jwt);
      localStorage.setItem("refresh_token", "ref");
      sessionStorage.setItem("jwt", jwt);

      clearAuthTokens();

      expect(localStorage.getItem("access_token")).toBeNull();
      expect(localStorage.getItem("refresh_token")).toBeNull();
      expect(sessionStorage.getItem("jwt")).toBeNull();
    });
  });

  describe("getAuthUserProfile", () => {
    it("returns null when no auth token exists", () => {
      expect(getAuthUserProfile()).toBeNull();
    });

    it("parses profile claims and computes initials", () => {
      const jwt = makeJwt({
        tenant_id: "acme",
        email: "jane.doe@yufeed.com",
        role: "compliance_officer",
        user_id: "user_123",
        name: "Jane Doe",
      });
      localStorage.setItem("access_token", jwt);

      expect(getAuthUserProfile()).toEqual(
        expect.objectContaining({
          userId: "user_123",
          tenantId: "acme",
          role: "compliance_officer",
          displayName: "Jane Doe",
          initials: "JD",
        }),
      );
    });
  });
});
