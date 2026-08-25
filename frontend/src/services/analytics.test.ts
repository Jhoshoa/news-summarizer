import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { __resetAnalyticsForTests, flush, trackEvent } from "./analytics";

describe("analytics client", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    window.sessionStorage.clear();
    __resetAnalyticsForTests();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: true, status: 202 }),
    );
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("does not call fetch immediately when an event is tracked", () => {
    trackEvent("brief_opened", { category: "economia" });

    expect(fetch).not.toHaveBeenCalled();
  });

  it("flushes the queued batch to /api/analytics/events after the debounce delay", async () => {
    trackEvent("brief_opened", { category: "economia" });
    trackEvent("story_opened", { storyId: "abc123" });

    await vi.advanceTimersByTimeAsync(2000);

    expect(fetch).toHaveBeenCalledTimes(1);
    const [url, options] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toContain("/api/analytics/events");
    const body = JSON.parse(options.body as string);
    expect(body.events).toHaveLength(2);
    expect(body.events[0].event_name).toBe("brief_opened");
    expect(body.events[0].category).toBe("economia");
    expect(body.events[1].story_id).toBe("abc123");
  });

  it("reuses the same session id across events in the same session", async () => {
    trackEvent("brief_opened");
    trackEvent("story_opened");
    await vi.advanceTimersByTimeAsync(2000);

    const body = JSON.parse(
      (fetch as ReturnType<typeof vi.fn>).mock.calls[0][1].body as string,
    );
    expect(body.events[0].session_id).toBe(body.events[1].session_id);
    expect(body.events[0].session_id).toBeTruthy();
  });

  it("flushes immediately once the batch reaches the size cap", () => {
    for (let i = 0; i < 20; i += 1) {
      trackEvent("story_opened", { storyId: `story-${i}` });
    }

    expect(fetch).toHaveBeenCalledTimes(1);
    const body = JSON.parse(
      (fetch as ReturnType<typeof vi.fn>).mock.calls[0][1].body as string,
    );
    expect(body.events).toHaveLength(20);
  });

  it("never throws when the network request fails", async () => {
    (fetch as ReturnType<typeof vi.fn>).mockRejectedValue(new Error("network down"));

    expect(() => trackEvent("brief_opened")).not.toThrow();
    await vi.advanceTimersByTimeAsync(2000);
    await vi.waitFor(() => {});
  });

  it("flush(true) uses sendBeacon when available and does not call fetch", () => {
    const sendBeacon = vi.fn().mockReturnValue(true);
    vi.stubGlobal("navigator", { ...navigator, sendBeacon, userAgent: navigator.userAgent });

    trackEvent("brief_opened");
    flush(true);

    expect(sendBeacon).toHaveBeenCalledTimes(1);
    expect(fetch).not.toHaveBeenCalled();
  });

  it("does nothing when flushed with an empty queue", () => {
    flush();
    expect(fetch).not.toHaveBeenCalled();
  });
});
