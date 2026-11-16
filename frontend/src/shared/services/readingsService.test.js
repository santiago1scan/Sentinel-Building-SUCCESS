import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("./httpClient", () => ({
  httpClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

import { httpClient } from "./httpClient";
import { readingsService, sensorsService, sensorTypesService } from "./readingsService";

describe("readingsService", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("list usa límite y offset por defecto", () => {
    readingsService.list();
    expect(httpClient.get).toHaveBeenCalledWith("/readings", {
      params: { limit: 100, offset: 0 },
    });
  });

  it("consultas por ID, sensor, nodo receptor y secuencia usan sus rutas", () => {
    readingsService.getById(1);
    readingsService.listBySensor(2);
    readingsService.listByReceivingNode(3);
    readingsService.listBySequence(4);
    expect(httpClient.get).toHaveBeenNthCalledWith(1, "/readings/1");
    expect(httpClient.get).toHaveBeenNthCalledWith(2, "/readings/sensor/2");
    expect(httpClient.get).toHaveBeenNthCalledWith(3, "/readings/receiving-node/3");
    expect(httpClient.get).toHaveBeenNthCalledWith(4, "/readings/sequence/4");
  });
});

describe("sensorsService", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("list, getById y getByCode usan sus rutas", () => {
    sensorsService.list();
    sensorsService.getById(5);
    sensorsService.getByCode("TEMP-01");
    expect(httpClient.get).toHaveBeenNthCalledWith(1, "/sensors", {
      params: { limit: 100, offset: 0 },
    });
    expect(httpClient.get).toHaveBeenNthCalledWith(2, "/sensors/5");
    expect(httpClient.get).toHaveBeenNthCalledWith(3, "/sensors/code/TEMP-01");
  });

  it("listByPrimaryNode y listBySensorType usan sus rutas", () => {
    sensorsService.listByPrimaryNode(1);
    sensorsService.listBySensorType(2);
    expect(httpClient.get).toHaveBeenNthCalledWith(1, "/sensors/primary-node/1");
    expect(httpClient.get).toHaveBeenNthCalledWith(2, "/sensors/sensor-type/2");
  });

  it("no expone métodos de escritura (el panel solo consulta)", () => {
    expect(sensorsService.update).toBeUndefined();
    expect(sensorsService.remove).toBeUndefined();
    expect(sensorsService.create).toBeUndefined();
  });
});

describe("sensorTypesService", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("list y getById usan sus rutas", () => {
    sensorTypesService.list();
    sensorTypesService.getById(1);
    expect(httpClient.get).toHaveBeenNthCalledWith(1, "/sensor-types", {
      params: { limit: 100, offset: 0 },
    });
    expect(httpClient.get).toHaveBeenNthCalledWith(2, "/sensor-types/1");
  });

  it("no expone métodos de escritura (el panel solo consulta)", () => {
    expect(sensorTypesService.update).toBeUndefined();
    expect(sensorTypesService.remove).toBeUndefined();
  });
});
