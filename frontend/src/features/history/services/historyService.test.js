import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../../../shared/services/httpClient", () => ({
  httpClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

import { httpClient } from "../../../shared/services/httpClient";
import { historyService } from "./historyService";

describe("historyService.getHalfHourHistory", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("mapea los campos de la UI a los nombres de query del backend", () => {
    historyService.getHalfHourHistory({
      sensorId: 4,
      metricCode: "temperature_c",
      from: "2026-11-16T08:00:00-05:00",
      to: "2026-11-16T10:00:00-05:00",
    });

    expect(httpClient.get).toHaveBeenCalledWith("/history", {
      params: {
        sensor_id: 4,
        metric_code: "temperature_c",
        from: "2026-11-16T08:00:00-05:00",
        to: "2026-11-16T10:00:00-05:00",
      },
    });
  });

  it("convierte objetos Date a ISO 8601", () => {
    const from = new Date("2026-11-16T13:00:00Z");
    const to = new Date("2026-11-16T15:00:00Z");

    historyService.getHalfHourHistory({
      sensorId: 1,
      metricCode: "humidity_pct",
      from,
      to,
    });

    const params = httpClient.get.mock.calls[0][1].params;
    expect(params.from).toBe("2026-11-16T13:00:00.000Z");
    expect(params.to).toBe("2026-11-16T15:00:00.000Z");
  });
});
