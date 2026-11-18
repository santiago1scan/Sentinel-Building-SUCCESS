// Mantiene al día el componente estado_red (#red) con /api/conectividad. Sin #red no hace nada.
(() => {
  const red = document.getElementById("red");
  if (!red) return;
  const TITULOS = { en_linea: "En línea", parcial: "Conexión parcial", sin_conexion: "Sin conexión" };
  const NOMBRES = { rest: "REST", mqtt: "MQTT", lora: "LoRa" };
  const INTERVALO_MS = 10000;

  function pintar(estado, titulo, detalle) {
    red.dataset.estado = estado;
    document.getElementById("redTitulo").textContent = titulo;
    document.getElementById("redDetalle").textContent = detalle;
  }

  // Estado y texto de cada chip: uso (entregando ahora), activo (conectado), caido o respaldo (LoRa).
  function chip(canal, info) {
    if (info.en_uso) return ["uso", "en uso"];
    if (canal === "lora") return ["respaldo", "respaldo"];
    if (info.conectado === null) return ["desconocido", "sin configurar"];
    return info.conectado ? ["activo", "disponible"] : ["caido", "caído"];
  }

  function pintarCanales(canales) {
    for (const [canal, info] of Object.entries(canales)) {
      const li = red.querySelector(`[data-canal="${canal}"]`);
      if (!li) continue;
      const [estado, texto] = chip(canal, info);
      li.dataset.estado = estado;
      li.querySelector(".chip-estado").textContent = texto;
    }
  }

  function titulo(d) {
    if (d.en_uso) return "Enviando por " + NOMBRES[d.en_uso];
    return TITULOS[d.estado] || d.estado;
  }

  function detalleDe(d) {
    if (d.estado === "sin_conexion") return "Sin canal hacia el backend";
    return d.en_uso ? TITULOS[d.estado] : "Sin envíos recientes";
  }

  async function actualizar() {
    try {
      const r = await fetch("/api/conectividad", { cache: "no-store" });
      if (!r.ok) throw new Error(r.status);
      const d = await r.json();
      pintar(d.estado, titulo(d), detalleDe(d));
      pintarCanales(d.canales);
    } catch (e) {
      pintar("sin_conexion", "Sin conexión", "El bridge no responde");
      pintarCanales({ rest: { conectado: false }, mqtt: { conectado: false }, lora: {} });
    }
  }

  actualizar();
  setInterval(actualizar, INTERVALO_MS);
})();
