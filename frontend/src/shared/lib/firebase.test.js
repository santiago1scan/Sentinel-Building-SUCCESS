import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

const initializeApp = vi.fn(() => ({ name: "app-test" }));
const getAuth = vi.fn(() => ({ name: "auth-test" }));

vi.mock("firebase/app", () => ({ initializeApp: (...args) => initializeApp(...args) }));
vi.mock("firebase/auth", () => ({ getAuth: (...args) => getAuth(...args) }));

const VALID_ENV = {
  VITE_FIREBASE_API_KEY: "api-key",
  VITE_FIREBASE_AUTH_DOMAIN: "proyecto.firebaseapp.com",
  VITE_FIREBASE_PROJECT_ID: "proyecto",
  VITE_FIREBASE_STORAGE_BUCKET: "proyecto.firebasestorage.app",
  VITE_FIREBASE_MESSAGING_SENDER_ID: "123",
  VITE_FIREBASE_APP_ID: "1:123:web:abc",
};

function setEnv(overrides = {}) {
  for (const [key, value] of Object.entries({ ...VALID_ENV, ...overrides })) {
    vi.stubEnv(key, value);
  }
}

describe("shared/lib/firebase", () => {
  beforeEach(() => {
    vi.resetModules();
    initializeApp.mockClear();
    getAuth.mockClear();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("inicializa la app con la configuración de las variables de entorno", async () => {
    setEnv();

    const mod = await import("./firebase");

    expect(initializeApp).toHaveBeenCalledWith({
      apiKey: "api-key",
      authDomain: "proyecto.firebaseapp.com",
      projectId: "proyecto",
      storageBucket: "proyecto.firebasestorage.app",
      messagingSenderId: "123",
      appId: "1:123:web:abc",
    });
    expect(getAuth).toHaveBeenCalledWith(mod.firebaseApp);
    expect(mod.auth).toEqual({ name: "auth-test" });
  });

  it("lanza un error que lista las variables faltantes", async () => {
    setEnv({ VITE_FIREBASE_API_KEY: "", VITE_FIREBASE_APP_ID: "" });

    await expect(import("./firebase")).rejects.toThrow(
      /VITE_FIREBASE_API_KEY|apiKey/,
    );
    await expect(import("./firebase")).rejects.toThrow(/appId/);
    expect(initializeApp).not.toHaveBeenCalled();
  });
});
