from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from beta_simulator.gateway import expand_lora_payload
from beta_simulator.sensors import utc_now

from .backend_contract import telemetry_endpoint, validate_backend_ack
from .config import GATEWAY_UID
from .storage import SummaryStore


class ExternalReceiver:
    """Simulated receiver outside the building for LoRa fallback packets."""

    def __init__(
        self,
        data_dir: Path,
        backend_url: str | None = None,
        node_tokens: dict[str, str] | None = None,
    ) -> None:
        self.store = SummaryStore(data_dir / "external_receiver.db")
        self.backend_url = backend_url.rstrip("/") if backend_url else None
        self.node_tokens = node_tokens or {}
        self.network_up = True
        self.received = 0

    def receive_lora(self, compact: dict[str, Any]) -> bool:
        payload = expand_lora_payload(compact)
        payload["gateway_uid"] = GATEWAY_UID
        payload["transport"] = "lora"
        payload["delivery_status"] = "gateway_received"
        self.received += 1
        self.store.save_summary(payload, payload["bridges"][0]["node_code"])
        print(
            f"receiver | lora_received={self.received:04d} "
            f"node={payload['bridges'][0]['node_code']} uid={payload['message_uid']}"
        )
        self.forward_pending()
        return True

    def forward_pending(self) -> int:
        if not self.network_up or not self.backend_url:
            return 0
        sent = 0
        for item in self.store.pending_summaries():
            payload = dict(item["payload"])
            payload["transport"] = "rest"
            payload["delivery_status"] = "realtime"
            payload["sent_at"] = utc_now()
            request = urllib.request.Request(
                telemetry_endpoint(self.backend_url),
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "X-Node-Token": self.node_tokens.get(item["node_code"], ""),
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=10) as response:
                    body = response.read().decode("utf-8", errors="replace")[:2000]
                    accepted, detail = validate_backend_ack(
                        response.status,
                        body,
                        item["message_uid"],
                        len(payload["bridges"][0]["sensors"]),
                    )
                    if accepted:
                        self.store.mark_summary(item["message_uid"], "sent", str(response.status))
                        self.store.log_sync(item["message_uid"], item["node_code"], "rest", "accepted")
                        sent += 1
                        continue
                    self.store.mark_summary(item["message_uid"], "pending", detail)
            except (OSError, urllib.error.HTTPError, urllib.error.URLError) as exc:
                self.store.mark_summary(item["message_uid"], "pending", str(exc))
                self.store.log_sync(item["message_uid"], item["node_code"], "rest", "retry")
        return sent

    def status(self) -> dict[str, Any]:
        return {"gateway_uid": GATEWAY_UID, "network_up": self.network_up, **self.store.status()}

    def close(self) -> None:
        self.store.close()

