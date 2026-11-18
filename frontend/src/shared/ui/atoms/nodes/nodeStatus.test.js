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

  it("una alerta atendida deja de ser 'alert' o 'warning': pasa a 'attended' aunque siga abierta", () => {
    expect(
      deriveNodeStatus({ isConnected: true, openAlerts: [{ alert_type: "out_of_range", handled_by_user_id: 5 }] }),
    ).toBe("attended");
    expect(
      deriveNodeStatus({ isConnected: false, openAlerts: [{ alert_type: "technical", handled_by_user_id: 5 }] }),
    ).toBe("attended");
  });

  it("basta una alerta sin atender para seguir en 'alert'", () => {
    expect(
      deriveNodeStatus({
        isConnected: true,
        openAlerts: [
          { alert_type: "out_of_range", handled_by_user_id: 5 },
          { alert_type: "out_of_range", handled_by_user_id: null },
        ],
      }),
    ).toBe("alert");
  });

  it("cada estado derivable tiene una definición visual", () => {
    ["alert", "warning", "attended", "connected", "off"].forEach((status) => {
      expect(NODE_STATUS[status].label).toBeTruthy();
      expect(NODE_STATUS[status].icon).toBeTruthy();
    });
  });
});
