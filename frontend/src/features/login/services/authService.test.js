import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// Evita inicializar Firebase real en las pruebas: se reemplazan los módulos que lo tocan.
vi.mock("firebase/auth", () => ({
  GoogleAuthProvider: vi.fn(),
  onAuthStateChanged: vi.fn(),
  signInWithPopup: vi.fn(),
  signOut: vi.fn(),
}));
vi.mock("../../../shared/lib/firebase", () => ({ auth: { currentUser: null } }));

import { signInWithPopup, signOut as firebaseSignOut, onAuthStateChanged } from "firebase/auth";
import { auth } from "../../../shared/lib/firebase";
import { getAuthToken, setAuthTokenProvider } from "../../../shared/services/authToken";
import { authService, connectAuthToken } from "./authService";

function jsonResponse(status, body) {
  return new Response(body === undefined ? null : JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("authService.hasAdminAccess", () => {
  let fetchMock;

  beforeEach(() => {
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("devuelve true cuando la API responde correctamente", async () => {
    fetchMock.mockResolvedValue(jsonResponse(200, []));

    await expect(authService.hasAdminAccess()).resolves.toBe(true);
  });

  it("devuelve false cuando la API responde 403", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(403, { status: 403, error: "ForbiddenError", message: "No autorizado" }),
    );

    await expect(authService.hasAdminAccess()).resolves.toBe(false);
  });

  it("propaga otros errores, como un 503", async () => {
    fetchMock.mockResolvedValue(jsonResponse(503, { message: "Servicio no disponible" }));

    await expect(authService.hasAdminAccess()).rejects.toMatchObject({ status: 503 });
  });
});

describe("authService.signInWithGoogle", () => {
  let fetchMock;

  beforeEach(() => {
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it("devuelve el usuario cuando la cuenta es administradora", async () => {
    const user = { email: "admin@sentinel.local" };
    signInWithPopup.mockResolvedValue({ user });
    fetchMock.mockResolvedValue(jsonResponse(200, []));

    await expect(authService.signInWithGoogle()).resolves.toBe(user);
    expect(signInWithPopup).toHaveBeenCalledWith(auth, expect.anything());
    expect(firebaseSignOut).not.toHaveBeenCalled();
  });

  it("cierra la sesión y lanza error si la cuenta no es administradora", async () => {
    signInWithPopup.mockResolvedValue({ user: { email: "otro@gmail.com" } });
    fetchMock.mockResolvedValue(jsonResponse(403, { message: "No autorizado" }));

    await expect(authService.signInWithGoogle()).rejects.toThrow(
      "Tu cuenta no tiene permisos de administrador en el panel.",
    );
    expect(firebaseSignOut).toHaveBeenCalledWith(auth);
  });

  it("no consulta la API si el popup de Google falla", async () => {
    signInWithPopup.mockRejectedValue(new Error("auth/popup-closed-by-user"));

    await expect(authService.signInWithGoogle()).rejects.toThrow("auth/popup-closed-by-user");
    expect(fetchMock).not.toHaveBeenCalled();
    expect(firebaseSignOut).not.toHaveBeenCalled();
  });

  it("propaga un error de la API distinto de 403 sin cerrar la sesión", async () => {
    signInWithPopup.mockResolvedValue({ user: { email: "admin@sentinel.local" } });
    fetchMock.mockResolvedValue(jsonResponse(503, { message: "Servicio no disponible" }));

    await expect(authService.signInWithGoogle()).rejects.toMatchObject({ status: 503 });
    expect(firebaseSignOut).not.toHaveBeenCalled();
  });
});

describe("authService.signOut", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("cierra la sesión de Firebase", async () => {
    firebaseSignOut.mockResolvedValue(undefined);

    await authService.signOut();

    expect(firebaseSignOut).toHaveBeenCalledWith(auth);
  });
});

describe("authService.onSessionChange", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("suscribe el callback a los cambios de sesión y devuelve la cancelación", () => {
    const unsubscribe = vi.fn();
    onAuthStateChanged.mockReturnValue(unsubscribe);
    const callback = vi.fn();

    const result = authService.onSessionChange(callback);

    expect(onAuthStateChanged).toHaveBeenCalledWith(auth, callback);
    expect(result).toBe(unsubscribe);
  });
});

describe("authService.getAppUserByEmail", () => {
  let fetchMock;

  beforeEach(() => {
    fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, { user_id: 1 }));
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("codifica el correo en la ruta para no romper caracteres especiales", async () => {
    await authService.getAppUserByEmail("ana+test/x@sentinel.local");

    const calledUrl = String(fetchMock.mock.calls[0][0]);
    expect(calledUrl).toContain("/app-users/email/ana%2Btest%2Fx%40sentinel.local");
  });
});

describe("connectAuthToken", () => {
  afterEach(() => {
    setAuthTokenProvider(null);
    auth.currentUser = null;
  });

  it("entrega el ID token del usuario actual de Firebase", async () => {
    auth.currentUser = { getIdToken: vi.fn().mockResolvedValue("id-token-xyz") };

    connectAuthToken();

    await expect(getAuthToken()).resolves.toBe("id-token-xyz");
  });

  it("devuelve null cuando no hay usuario en sesión", async () => {
    auth.currentUser = null;

    connectAuthToken();

    await expect(getAuthToken()).resolves.toBeNull();
  });
});
