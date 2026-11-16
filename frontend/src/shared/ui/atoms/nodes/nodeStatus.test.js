import { describe, it, expect } from "vitest";
import { deriveNodeStatus, NODE_STATUS } from "./nodeStatus";

describe("deriveNodeStatus", () => {
  it("una alerta fuera de rango abierta es 'alert', aunque haya conexión", () => {
    expect(
      deriveNodeStatus({ isConnected: true, openAlerts: [{ alert_type: "out_of_range" }] }),
    ).toBe("alert");
  });

  it("otra alerta abierta (técnica) es 'warning'", () => {
    expect(
      deriveNodeStatus({ isConnected: true, openAlerts: [{ alert_type: "technical" }] }),
    ).toBe("warning");
  });

  it("conectado y sin alertas es 'connected'", () => {
    expect(deriveNodeStatus({ isConnected: true, openAlerts: [] })).toBe("connected");
  });

  it("sin conexión activa y sin alertas es 'off'", () => {
    expect(deriveNodeStatus({ isConnected: false })).toBe("off");
  });

  it("cada estado derivable tiene una definición visual", () => {
    ["alert", "warning", "connected", "off"].forEach((status) => {
      expect(NODE_STATUS[status].label).toBeTruthy();
      expect(NODE_STATUS[status].icon).toBeTruthy();
    });
  });
});
