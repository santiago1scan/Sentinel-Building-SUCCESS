import { describe, it, expect, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import NodeAlerts from "./NodeAlerts";

const group = (extra) => ({
  key: "1:temperature", category: "temperature", title: "Alerta de temperatura", label: "Temperatura",
  severity: "alert", gravity: null, live: true, attended: false, alerts: [], unhandled: [], sensors: [], ...extra,
});

describe("NodeAlerts · gravedad", () => {
  afterEach(() => cleanup());

  it("muestra «Emergencia» o «Leve» junto al título", () => {
    render(<NodeAlerts groups={[group({ gravity: "emergencia" }), group({ key: "1:air", gravity: "leve" })]} />);
    expect(screen.getByText("Emergencia")).toBeTruthy();
    expect(screen.getByText("Leve")).toBeTruthy();
  });

  it("sin gravedad no muestra etiqueta", () => {
    render(<NodeAlerts groups={[group()]} />);
    expect(screen.queryByText("Emergencia")).toBeNull();
    expect(screen.queryByText("Leve")).toBeNull();
  });
});
