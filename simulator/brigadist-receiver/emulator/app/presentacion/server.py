from __future__ import annotations

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from app.negocio.brigadist_service import BrigadistService


HTML = """<!doctype html><html lang='es'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width'>
<title>Sentinel · Brigadista</title><style>
:root{color-scheme:dark;font-family:Inter,system-ui;background:#07110d;color:#e7f5ec}body{margin:0;padding:24px;background:radial-gradient(circle at top,#173027,#07110d 60%)}
header{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #315344;padding-bottom:18px}.live{color:#70e7a0}.grid{display:grid;gap:14px;margin-top:24px}.card{border:1px solid #345644;background:#0c1b14;padding:18px;border-radius:12px}.critical{border-color:#d84a4a;box-shadow:0 0 28px #b9252538;animation:pulse 1.4s infinite}.meta{color:#9cb3a6;font:13px ui-monospace}.event{font-size:24px;font-weight:800;margin:8px 0}button{background:#b82f2f;color:white;border:0;border-radius:8px;padding:12px 18px;font-weight:700}button:disabled{background:#315344}@keyframes pulse{50%{background:#301414}}.empty{color:#9cb3a6;text-align:center;padding:64px}
</style></head><body><header><div><b>SENTINEL · EMULADOR DEL RECEPTOR</b><div class='meta'>Representa Heltec WiFi LoRa 32 · SX1262 durante la Beta</div></div><div class='live'>● RADIO LISTA</div></header><main id='app'></main>
<script>async function ack(id){await fetch('/api/alerts/'+id+'/ack',{method:'POST'});load()}function esc(v){return String(v).replace(/[&<>]/g,s=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[s]))}async function load(){let a=await(await fetch('/api/alerts')).json();document.getElementById('app').innerHTML=a.length?'<div class="grid">'+a.map(x=>`<section class="card ${x.human_status==='WAITING'?'critical':''}"><div class="meta">${esc(x.received_at)} · NODE ${x.node} · ${esc(x.sensor)}</div><div class="event">${esc(x.event)}</div><p>Trama HMAC válida. Batería del bridge: ${x.battery_mv} mV.</p><button ${x.human_status!=='WAITING'?'disabled':''} onclick="ack('${x.message_uid}')">${x.human_status==='WAITING'?'CONFIRMAR RECEPCIÓN':'CONFIRMADO'}</button></section>`).join('')+'</div>':'<div class="empty">Sin alertas. El monolito del brigadista permanece escuchando.</div>'}load();setInterval(load,1000)</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    service: BrigadistService

    def _send(self, status: int, body: bytes, kind: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if urlparse(self.path).path == "/api/alerts":
            self._send(200, json.dumps(self.service.snapshot()).encode(), "application/json")
        else:
            self._send(200, HTML.encode(), "text/html; charset=utf-8")

    def do_POST(self) -> None:  # noqa: N802
        parts = urlparse(self.path).path.strip("/").split("/")
        if len(parts) == 4 and parts[:2] == ["api", "alerts"] and parts[3] == "ack":
            ok = self.service.acknowledge(parts[2])
            self._send(200 if ok else 404, json.dumps({"ok": ok}).encode(), "application/json")
        else:
            self._send(404, b"{}", "application/json")

    def log_message(self, fmt: str, *args: object) -> None:
        return


def main() -> None:
    parser = argparse.ArgumentParser(description="Emulador del receptor Heltec del brigadista")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--web-port", type=int, default=8993)
    parser.add_argument("--radio-port", type=int, default=9200)
    parser.add_argument("--history", default="runtime/alerts.json")
    parser.add_argument("--shared-key", default=os.getenv("SENTINEL_LORA_KEY", "sentinel-simulator-shared-key"))
    args = parser.parse_args()
    Handler.service = BrigadistService(
        args.host, args.radio_port, args.shared_key.encode("utf-8"), Path(args.history)
    )
    server = ThreadingHTTPServer((args.host, args.web_port), Handler)
    print(f"Brigadist Receiver Emulator: http://{args.host}:{args.web_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        Handler.service.close()
        server.server_close()


if __name__ == "__main__":
    main()
