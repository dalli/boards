import { afterEach, describe, expect, it, vi } from "vitest";
import { apiFetch, getAccessToken, setAccessToken } from "./client";

afterEach(() => {
  setAccessToken(null);
  vi.restoreAllMocks();
});

describe("api client (S-01 in-memory token)", () => {
  it("stores and clears token in memory", () => {
    expect(getAccessToken()).toBeNull();
    setAccessToken("abc");
    expect(getAccessToken()).toBe("abc");
    setAccessToken(null);
    expect(getAccessToken()).toBeNull();
  });

  it("attaches Authorization header when token set", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("{}"));
    vi.stubGlobal("fetch", fetchMock);
    setAccessToken("tok123");
    await apiFetch("/auth/me");
    const headers = fetchMock.mock.calls[0][1].headers as Headers;
    expect(headers.get("Authorization")).toBe("Bearer tok123");
  });

  it("does not attach Authorization header when no token", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("{}"));
    vi.stubGlobal("fetch", fetchMock);
    await apiFetch("/health");
    const headers = fetchMock.mock.calls[0][1].headers as Headers;
    expect(headers.get("Authorization")).toBeNull();
  });
});
