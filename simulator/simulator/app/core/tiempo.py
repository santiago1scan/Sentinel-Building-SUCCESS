from datetime import datetime, timezone


def now_utc() -> str:
    """Hora UTC con milisegundos, para los eventos."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def utc_ahora() -> str:
    """Hora UTC con segundos, para el registro que ve el panel."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
