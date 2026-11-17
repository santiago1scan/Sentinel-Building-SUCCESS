import { describe, it, expect } from "vitest";
import { summarizeConnectivity, formatDuration } from "./nodeMetrics";

describe("summarizeConnectivity", () => {
  it("suma el tiempo conectado y detecta la sesión abierta", () => {
    const now = new Date("2026-11-16T12:00:00Z").getTime();
    const summary = summarizeConnectivity(
      [
        { started_at: "2026-11-16T08:00:00Z", ended_at: "2026-11-16T09:00:00Z" },
        { started_at: "2026-11-16T11:00:00Z", ended_at: null },
      ],
      now,
    );
    expect(summary.sessions).toBe(2);
    expect(summary.connected).toBe(true);
    expect(summary.connectedMs).toBe(2 * 3600 * 1000);
  });
});

describe("formatDuration", () => {
  it("formatea segundos, minutos, horas y días", () => {
    expect(formatDuration(40_000)).toBe("40 s");
    expect(formatDuration(15 * 60_000)).toBe("15 min");
    expect(formatDuration(125 * 60_000)).toBe("2 h 05 min");
    expect(formatDuration(50 * 3600_000)).toBe("2 d 2 h");
  });
});
