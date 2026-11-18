import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import NodeInfo from "./NodeInfo";

const node = { node_id: 1, code: "N-01", name: "Piso 1", ip_address: null };

describe("NodeInfo", () => {
  afterEach(() => cleanup());

  it("sin alerta se ve como siempre, sin estado", () => {
    const { container } = render(<NodeInfo node={node} />);

    expect(screen.getByRole("heading", { name: "Piso 1" })).toBeTruthy();
    expect(container.querySelector("article").hasAttribute("data-status")).toBe(false);
    expect(screen.queryByText("Alerta")).toBeNull();
  });

  it("con alerta fuera de rango cambia a rojo y lo dice con texto", () => {
    const { container } = render(<NodeInfo node={node} status="alert" />);

    expect(container.querySelector("article").getAttribute("data-status")).toBe("alert");
    expect(screen.getByText("Alerta")).toBeTruthy();
  });

  it("con solo avisos técnicos usa el estado «Revisar»", () => {
    const { container } = render(<NodeInfo node={node} status="warning" />);

    expect(container.querySelector("article").getAttribute("data-status")).toBe("warning");
    expect(screen.getByText("Revisar")).toBeTruthy();
  });
});
