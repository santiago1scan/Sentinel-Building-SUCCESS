import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup, fireEvent } from "@testing-library/react";
import BasementQuestion from "./BasementQuestion";

describe("BasementQuestion", () => {
  afterEach(() => cleanup());

  it("con valor falso, 'No' está marcado", () => {
    render(<BasementQuestion value={false} onChange={() => {}} />);

    expect(screen.getByRole("button", { name: "No" }).getAttribute("aria-pressed")).toBe("true");
    expect(screen.getByRole("button", { name: "Sí" }).getAttribute("aria-pressed")).toBe("false");
  });

  it("avisa true al marcar Sí y false al marcar No", () => {
    const onChange = vi.fn();
    render(<BasementQuestion value={false} onChange={onChange} />);

    fireEvent.click(screen.getByRole("button", { name: "Sí" }));
    expect(onChange).toHaveBeenLastCalledWith(true);

    fireEvent.click(screen.getByRole("button", { name: "No" }));
    expect(onChange).toHaveBeenLastCalledWith(false);
  });

  it("deshabilitada no responde", () => {
    render(<BasementQuestion value={false} disabled onChange={() => {}} />);
    expect(screen.getByRole("button", { name: "Sí" }).disabled).toBe(true);
  });
});
