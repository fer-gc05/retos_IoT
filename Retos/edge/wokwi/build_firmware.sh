#!/usr/bin/env bash
# Compila el firmware ESP32. Crea .venv local si hace falta (evita PEP 668 en Debian/Ubuntu).
set -euo pipefail
cd "$(dirname "$0")"
# Datos de PlatformIO dentro del proyecto (no requiere ~/.platformio)
export PLATFORMIO_CORE_DIR="$(pwd)/.platformio"

PIO=".venv/bin/pio"
if [[ ! -x "$PIO" ]]; then
  echo "Creando entorno virtual y instalando PlatformIO (solo la primera vez)..."
  python3 -m venv .venv
  .venv/bin/pip install -U pip
  .venv/bin/pip install platformio
fi
exec "$PIO" run
