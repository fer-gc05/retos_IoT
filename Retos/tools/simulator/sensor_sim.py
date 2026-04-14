#!/usr/bin/env python3
"""
Simulador MQ-2 (Reto 2: flujo a broker; Reto 3: despliegue / monitoreo).
- Publica telemetría cada N segundos (QoS 1), tópico configurable.
- Opcional: patrón Circuit Breaker (ADR-002): tras varios fallos, buffer en memoria
  y reintento espaciado (simplificación respecto a SPIFFS del firmware real).
- Wokwi: ejecuta este script en tu PC con MQTT_HOST=localhost cuando el broker
  está mapeado al host (puerto 1883) o usa la IP del túnel Wokwi.
"""
from __future__ import annotations

import json
import logging
import os
import random
import threading
import time
from collections import deque
from typing import Any, Deque, Dict, Optional

import paho.mqtt.client as mqtt

logging.basicConfig(level=logging.INFO, format="%(asctime)s [SENSOR] %(message)s")
log = logging.getLogger(__name__)

HOST = os.getenv("MQTT_HOST", "localhost")
PORT = int(os.getenv("MQTT_PORT", "1883"))
USER = os.getenv("MQTT_USER", "sensor")
PASS = os.getenv("MQTT_PASS", "sensor123")
TOPIC = os.getenv("MQTT_TOPIC", "casa/gas/ppm")
ALERT_TOPIC = os.getenv("ALERT_TOPIC", "casa/gas/alerta")
THRESHOLD = int(os.getenv("PPM_THRESHOLD", "300"))
INTERVAL = int(os.getenv("PUBLISH_INTERVAL", "5"))
CB_ENABLED = os.getenv("CIRCUIT_BREAKER", "1").lower() in ("1", "true", "yes")
CB_FAIL_THRESHOLD = int(os.getenv("CB_FAIL_THRESHOLD", "3"))
CB_BACKOFF_SEC = int(os.getenv("CB_BACKOFF_SEC", "30"))
BUFFER_MAX = int(os.getenv("CB_BUFFER_MAX", "120"))


def simulate_ppm() -> float:
    """Simula lectura: mayoría normal, ocasional pico por encima del umbral."""
    if random.random() < 0.2:
        return round(random.uniform(300, 600), 2)
    return round(random.uniform(50, 250), 2)


class CircuitBreakerPublisher:
    """Circuit breaker ligero en el simulador (eco del ADR-002 del ESP8266)."""

    def __init__(self, client: mqtt.Client) -> None:
        self._client = client
        self._failures = 0
        self._open_until: float = 0.0
        self._buffer: Deque[Dict[str, Any]] = deque(maxlen=BUFFER_MAX)
        self._lock = threading.Lock()

    def publish(self, topic: str, payload: str, qos: int = 1) -> bool:
        with self._lock:
            if time.monotonic() < self._open_until:
                self._buffer.append({"topic": topic, "payload": payload, "qos": qos})
                log.warning("Circuito ABIERTO: mensaje en buffer (%s)", len(self._buffer))
                return False
            info = self._client.publish(topic, payload, qos=qos)
            if info.rc != mqtt.MQTT_ERR_SUCCESS:
                self._on_fail()
                return False
            try:
                info.wait_for_publish(timeout=5.0)
            except (ValueError, OSError, RuntimeError) as e:
                log.debug("wait_for_publish: %s", e)
                self._on_fail()
                return False
            self._failures = 0
            return True

    def _on_fail(self) -> None:
        self._failures += 1
        log.error("Fallo MQTT consecutivo %s/%s", self._failures, CB_FAIL_THRESHOLD)
        if self._failures >= CB_FAIL_THRESHOLD:
            self._open_until = time.monotonic() + CB_BACKOFF_SEC
            self._failures = 0
            log.warning("Circuito abierto %ss; acumulando en buffer", CB_BACKOFF_SEC)

    def flush_buffer_if_closed(self) -> None:
        if time.monotonic() < self._open_until:
            return
        with self._lock:
            while self._buffer:
                item = self._buffer.popleft()
                info = self._client.publish(item["topic"], item["payload"], qos=item["qos"])
                if info.rc != mqtt.MQTT_ERR_SUCCESS:
                    self._buffer.appendleft(item)
                    self._on_fail()
                    break
                try:
                    info.wait_for_publish(timeout=5.0)
                except (ValueError, OSError, RuntimeError):
                    self._buffer.appendleft(item)
                    self._on_fail()
                    break


def main() -> None:
    connected = threading.Event()

    def on_connect(_c: mqtt.Client, _u: Any, _f: Any, rc: int) -> None:
        if rc == 0:
            log.info("Conectado a %s:%s", HOST, PORT)
            connected.set()
        else:
            log.error("Código de conexión MQTT: %s", rc)

    def on_disconnect(_c: mqtt.Client, _u: Any, rc: int) -> None:
        connected.clear()
        log.warning("Desconectado (rc=%s)", rc)

    client = mqtt.Client(client_id="sensor_mq2_sim")
    client.username_pw_set(USER, PASS)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect

    log.info("Conectando a %s:%s (usuario %s)...", HOST, PORT, USER)
    client.connect(HOST, PORT, keepalive=60)
    client.loop_start()
    if not connected.wait(timeout=15):
        log.error("Timeout esperando conexión MQTT")
        client.loop_stop()
        raise SystemExit(1)

    cb_pub: Optional[CircuitBreakerPublisher] = CircuitBreakerPublisher(client) if CB_ENABLED else None

    log.info(
        "Publicando en %r cada %ss (umbral %s PPM). CB=%s",
        TOPIC,
        INTERVAL,
        THRESHOLD,
        CB_ENABLED,
    )

    try:
        while True:
            if cb_pub:
                cb_pub.flush_buffer_if_closed()

            ppm = simulate_ppm()
            body: Dict[str, Any] = {
                "ppm": ppm,
                "timestamp": int(time.time()),
                "sensor": "MQ-2",
            }
            payload = json.dumps(body)

            if cb_pub:
                ok = cb_pub.publish(TOPIC, payload, qos=1)
            else:
                inf = client.publish(TOPIC, payload, qos=1)
                inf.wait_for_publish(timeout=5.0)
                ok = True

            if ok:
                log.info("Publicado %s | PPM=%s", TOPIC, ppm)

            if ppm > THRESHOLD:
                alert = json.dumps(
                    {
                        "ppm": ppm,
                        "level": "CRITICAL",
                        "timestamp": int(time.time()),
                        "sensor": "MQ-2",
                    }
                )
                if cb_pub:
                    cb_pub.publish(ALERT_TOPIC, alert, qos=1)
                else:
                    client.publish(ALERT_TOPIC, alert, qos=1).wait_for_publish(timeout=5.0)
                log.warning("Alerta → %s (PPM %s > %s)", ALERT_TOPIC, ppm, THRESHOLD)

            time.sleep(INTERVAL)
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
