import { afterEach, describe, expect, it, vi } from "vitest";
import { getAccessToken, setAccessToken } from "./client";
import { login } from "./endpoints";

afterEach(() => {
  setAccessToken(null);
  vi.restoreAllMocks();
});

describe("login token hygiene (F-001)", () => {
  it("clears the token if the profile fetch fails after login", async () => {
    const fetchMock = vi
      .fn()
      // POST /auth/login → token
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ access_token: "tok", token_type: "bearer" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )
      // GET /auth/me → fails
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: "boom" }), {
          status: 500,
          headers: { "Content-Type": "application/json" },
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    await expect(login("a@example.com", "password123")).rejects.toThrow();
    // token must NOT linger after a failed /auth/me
    expect(getAccessToken()).toBeNull();
  });

  it("clears a pre-existing token if /auth/login itself fails (NF-001)", async () => {
    setAccessToken("stale-token-from-prior-session");
    const fetchMock = vi.fn().mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "Invalid email or password" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(login("a@example.com", "wrongpass")).rejects.toThrow();
    expect(getAccessToken()).toBeNull();
  });

  it("keeps the token and returns the user on success", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ access_token: "tok", token_type: "bearer" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ id: 1, email: "a@example.com", role: "USER", created_at: "x" }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      );
    vi.stubGlobal("fetch", fetchMock);

    const user = await login("a@example.com", "password123");
    expect(user.email).toBe("a@example.com");
    expect(getAccessToken()).toBe("tok");
  });
});
