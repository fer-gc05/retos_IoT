#!/usr/bin/env python3
"""
Comprobación de disponibilidad (Reto 3: monitoreo básico + métricas simples).
Consulta HTTP health de servicios y hace un ping MQTT (subscribe corto).
Ejecutar desde el host con el stack levantado:  python3 scripts/monitor_health.py
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import List

try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None  # type: ignore


@dataclass
class Check:
    name: str
    ok: bool
    detail: str
    latency_ms: float


def http_check(name: str, url: str, timeout: float = 3.0) -> Check:
    t0 = time.perf_counter()
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = getattr(resp, "status", 200)
            _ = resp.read()
        ms = (time.perf_counter() - t0) * 1000
        return Check(name, True, f"HTTP {status}", ms)
    except urllib.error.HTTPError as e:
        ms = (time.perf_counter() - t0) * 1000
        return Check(name, False, str(e), ms)
    except Exception as e:  # noqa: BLE001
        ms = (time.perf_counter() - t0) * 1000
        return Check(name, False, repr(e), ms)


def mqtt_auth_subscribe(
    host: str,
    port: int,
    user: str,
    password: str,
    topic: str,
    timeout: float = 5.0,
) -> Check:
    """Conecta al broker, autentica y confirma suscripción (sin exigir telemetría)."""
    if mqtt is None:
        return Check("mqtt", False, "instala paho-mqtt: pip install 'paho-mqtt>=1.6,<2'", 0.0)
    t0 = time.perf_counter()
    err: List[str] = []
    suback = threading.Event()

    def on_connect(c: mqtt.Client, _u, _f, rc: int) -> None:
        if rc == 0:
            c.subscribe(topic, qos=0)
        else:
            err.append(f"rc={rc}")

    def on_subscribe(_c, _u, _mid, _granted_qos) -> None:
        suback.set()

    client = mqtt.Client(client_id="healthcheck_monitor")
    client.username_pw_set(user, password)
    client.on_connect = on_connect
    client.on_subscribe = on_subscribe
    try:
        client.connect(host, port, keepalive=10)
        client.loop_start()
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if err:
                break
            if suback.is_set():
                break
            time.sleep(0.05)
        client.loop_stop()
        client.disconnect()
        ms = (time.perf_counter() - t0) * 1000
        if err:
            return Check("mqtt_auth", False, err[0], ms)
        if not suback.is_set():
            return Check("mqtt_auth", False, "timeout sin SUBACK", ms)
        return Check("mqtt_auth", True, f"conectado y suscrito a {topic!r}", ms)
    except Exception as e:  # noqa: BLE001
        ms = (time.perf_counter() - t0) * 1000
        try:
            client.loop_stop()
            client.disconnect()
        except Exception:
            pass
        return Check("mqtt_auth", False, repr(e), ms)


def main() -> int:
    base = os.getenv("MONITOR_BASE", "http://127.0.0.1")
    nr = os.getenv("NODERED_URL", f"{base}:1880/")
    influx = os.getenv("INFLUX_HEALTH", f"{base}:8086/health")
    grafana = os.getenv("GRAFANA_HEALTH", f"{base}:3000/api/health")

    checks: List[Check] = [
        http_check("node-red", nr),
        http_check("influxdb", influx),
        http_check("grafana", grafana),
    ]

    mhost = os.getenv("MQTT_HOST", "127.0.0.1")
    mport = int(os.getenv("MQTT_PORT", "1883"))
    muser = os.getenv("MQTT_USER", "admin")
    mpass = os.getenv("MQTT_PASS", "admin123")
    topic = os.getenv("MQTT_TEST_TOPIC", "casa/gas/#")
    checks.append(mqtt_auth_subscribe(mhost, mport, muser, mpass, topic))

    ok_n = sum(1 for c in checks if c.ok)
    print(json.dumps({"summary": {"ok": ok_n, "total": len(checks)}, "checks": [c.__dict__ for c in checks]}, indent=2))
    return 0 if ok_n == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
