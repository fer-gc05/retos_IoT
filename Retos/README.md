# 🔥 Sistema IoT — Detección de Fuga de Gas

> **Arquitectura de Software · Reto 3 · Corporación Universitaria Remington**  
> Ingeniería de Sistemas · Docente: Sonia Isabel Huérfano Duarte

[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](https://docs.docker.com/compose/)
[![MQTT](https://img.shields.io/badge/MQTT-Mosquitto_2.x-660066?logo=eclipsemosquitto)](https://mosquitto.org)
[![Node-RED](https://img.shields.io/badge/Node--RED-3.1-8F0000?logo=nodered)](https://nodered.org)
[![InfluxDB](https://img.shields.io/badge/InfluxDB-2.7-22ADF6?logo=influxdb)](https://influxdata.com)
[![Grafana](https://img.shields.io/badge/Grafana-10.2-F46800?logo=grafana)](https://grafana.com)

---

## 📋 Descripción

Sistema IoT que monitorea en tiempo real la concentración de gas (PPM) en espacios residenciales o industriales. Cuando los niveles superan el umbral seguro (300 PPM), el sistema genera alertas automáticas, activa el buzzer local del dispositivo y notifica al usuario vía Telegram.

**Alineación con los retos del curso (PDF *Actividad por Retos*):**  
- **Reto 1:** drivers, escenarios de calidad, C4 contexto/contenedores, estilos (Pub-Sub, capas), demo MQTT.  
- **Reto 2:** patrones (Pub-Sub, *gateway* Node-RED, *circuit breaker* en firmware/simulador), C4 componentes, flujo sensor → MQTT → Node-RED → persistencia/visualización, *trade-offs*.  
- **Reto 3 (este repositorio):** vistas de arquitectura (módulos, C&C, despliegue), evaluación ATAM simplificada, **Docker Compose** con *health checks* y monitoreo básico, portafolio en GitHub.

**Stack tecnológico:** **ESP32 simulado en Wokwi** (`edge/wokwi/`) publicando MQTT igual que un MQ-2 real → Mosquitto → Node-RED → InfluxDB → Grafana. *Simulador Python opcional* (`tools/simulator/`). *TLS opcional en producción.*

### Arranque rápido (flujo principal con Wokwi)

1. **Backend (terminal):** desde esta carpeta `Retos/` ejecuta `docker compose up -d` (Mosquitto, Node-RED, InfluxDB, Grafana). No arranca el simulador Python por defecto.
2. **Firmware:** hace falta **PlatformIO** para generar `firmware.bin`. En Linux con Python “externally managed” (PEP 668) **no** uses `pip install --user` al sistema: usá el script del repo (crea `.venv` dentro de `edge/wokwi/`) o la extensión **PlatformIO IDE**.
3. **Abrir el proyecto en VS Code:** abre la carpeta **`Retos/`** (recomendado: `wokwi.toml` y `diagram.json` en la raíz). También podés abrir solo **`Retos/edge/wokwi/`**. Instalá **Wokwi** y el **Private IoT Gateway** (`F1` → *Enable Private IoT Gateway*).
4. **Compilar antes de simular (obligatorio):** desde la raíz del repo: `cd Retos/edge/wokwi` (**nota:** la carpeta se llama `Retos` con mayúscula). Luego:
   ```bash
   chmod +x build_firmware.sh
   ./build_firmware.sh
   ```
   Eso instala PlatformIO en `.venv` (solo la primera vez) y ejecuta `pio run`. Alternativa manual: `python3 -m venv .venv && .venv/bin/pip install platformio && .venv/bin/pio run`. En VS Code: **Run Build Task** si tenés `pio` en el PATH o la extensión PlatformIO. Si aparece **«firmware.bin not found»**, falta compilar o la carpeta abierta no coincide con `wokwi.toml`.
5. **Simular:** `F1` → *Wokwi: Start Simulator*. MQTT: `host.wokwi.internal:1883`, usuario `sensor` / `sensor123`. El **MQ-2** lleva **VCC→3V3, GND, AO→GPIO34**; subí “humo” desde el panel del sensor o el atributo `ppm` en `diagram.json`.
6. **Ver datos:** Grafana en http://localhost:3000 (`admin` / `admin123`) o Node-RED en http://localhost:1880.

**Simulador Python (alternativa):** `docker compose --profile python-sim up -d` (servicio `sensor_simulator`).

---

## 🏗️ Arquitectura

### C4 Nivel 1 — Contexto

```mermaid
graph TD
    usuario["👤 Usuario / Residente\nRecibe alertas en smartphone"]
    admin["👤 Administrador\nConfigura umbrales y revisa logs"]
    iotSystem["🔧 Sistema IoT de Detección de Gas\n[Sistema Principal]"]
    mqttCloud["⬜ HiveMQ Cloud\n[Sistema Externo - Respaldo]"]
    notif["⬜ Telegram / Email\n[Sistema Externo]"]

    usuario -->|"Consulta dashboard | HTTPS"| iotSystem
    admin -->|"Configura parámetros | HTTPS"| iotSystem
    iotSystem -->|"Replica mensajes | MQTT bridge"| mqttCloud
    iotSystem -->|"Envía alertas | HTTPS"| notif

    style iotSystem fill:#08427B,color:#fff
    style mqttCloud fill:#999,color:#fff
    style notif fill:#999,color:#fff
    style usuario fill:#1168BD,color:#fff
    style admin fill:#1168BD,color:#fff
```

### C4 Nivel 2 — Contenedores

```mermaid
graph TD
    subgraph boundary["Sistema IoT de Detección de Gas"]
        sensor["📡 Dispositivo IoT\n[ESP8266 + MQ-2]\nLee PPM c/5s"]
        broker["📨 Broker MQTT\n[Mosquitto 2.x]\nTLS + ACLs"]
        nodered["⚙️ Node-RED\nProcesamiento y reglas"]
        dashboard["📊 Grafana\nVisualización"]
        db[("🗄️ InfluxDB\nSerie temporal")]
        notifier["🔔 Telegram Node\nAlertas push"]
    end

    sensor -->|"MQTT/TLS :1883"| broker
    broker -->|"MQTT interno"| nodered
    nodered -->|"TCP"| db
    nodered -->|"WebSocket"| dashboard
    nodered -->|"PPM > 300"| notifier
    notifier -->|"HTTPS"| usuario["👤 Usuario"]

    style boundary fill:#f0f4f8,stroke:#08427B,stroke-width:2px
```

### C4 Nivel 3 — Componentes (Node-RED)

```mermaid
graph LR
    MS["MQTTSubscriber\ncasa/gas/#"] --> RE["RuleEngine\nPPM > 300?"]
    RE --> DR["DataRepository\nInfluxDB out"]
    RE -->|alerta| AN["AlertNotifier\nTelegram"]
    RE --> AG["APIGateway\nHTTP + WS"]
    AG --> GW["GaugeWidget\nPPM actual"]
    AG --> HC["HistoryChart\nHistórico"]
    AN --> AW["AlertWidget\nNotificación visual"]
```

---

## 📚 Reto 3 — Documentación de arquitectura (*Views & Beyond*)

### Vista de módulos

Descomposición lógica del sistema (responsabilidades principales).

| Módulo | Responsabilidad | Tecnología | Decisiones (ADR) |
|--------|-----------------|------------|-------------------|
| **Edge / sensor** | Muestreo periódico de PPM, QoS, resiliencia ante red | **Wokwi + ESP32** (`edge/wokwi/`) o `tools/simulator/sensor_sim.py` | ADR-001 MQTT, ADR-002 *circuit breaker* |
| **Mensajería** | Pub-Sub, autenticación, ACL mínimas | Mosquitto 2.x | ADR-001 |
| **Procesamiento** | Enrutar telemetría, formato Influx *line protocol* | Node-RED 3.1 | ADR-003 |
| **Serie temporal** | Almacenar lecturas y alertas | InfluxDB 2.7 | ADR-003 |
| **Visualización** | Dashboards operativos | Grafana 10.2 | ADR-003 |
| **Notificaciones** | Telegram / email (extensible) | Nodos o integraciones externas | Documentado en C4 contexto |

```mermaid
flowchart LR
  subgraph edge["Borde"]
    S[Sensor / simulador]
  end
  subgraph msg["Mensajería"]
    B[Broker MQTT]
  end
  subgraph proc["Procesamiento"]
    NR[Node-RED]
  end
  subgraph data["Datos"]
    I[(InfluxDB)]
  end
  subgraph viz["Visualización"]
    G[Grafana]
  end
  S --> B --> NR --> I
  I --> G
```

### Vista C&C (componentes y conectores)

Conectores dominantes: **MQTT pub-sub** entre borde y broker, **HTTP** (API de escritura Influx v2) entre Node-RED e InfluxDB, **HTTP** entre cliente y Grafana/Node-RED UI.

| Elemento | Tipo / conector | Interacción |
|----------|-----------------|-------------|
| `sensor_sim` → Mosquitto | MQTT publicar (`casa/gas/ppm`, `casa/gas/alerta`) | QoS 1 |
| Mosquitto → Node-RED | MQTT suscribir (`casa/gas/#`) | QoS 1 |
| Node-RED → InfluxDB | HTTP `POST /api/v2/write` | Token en flujo (solo laboratorio) |
| Grafana → InfluxDB | HTTP Flux (proxy Grafana) | Token en *provisioning* |

### Vista de despliegue (Docker + Wokwi en el host)

Los servicios de backend comparten la red bridge `iot_net`. El **borde** es el simulador Wokwi (ESP32) en VS Code; publica MQTT hacia el puerto **1883** del host (vía *Private IoT Gateway* y `host.wokwi.internal`). Opcionalmente, `sensor_simulator` (perfil `python-sim`) publica igual desde Docker.

```mermaid
flowchart TB
  subgraph vscode["VS Code — Wokwi"]
    W[ESP32 firmware edge/wokwi]
  end
  subgraph host["Docker"]
    MQ[mosquitto:1883]
    NR[nodered:1880]
    IF[influxdb:8086]
    GF[grafana:3000]
  end
  W -->|MQTT| MQ
  NR -->|MQTT| MQ
  NR -->|HTTP write| IF
  GF -->|Flux| IF
```

**Puertos en el host:** 1883 (MQTT), 1880 (Node-RED), 8086 (InfluxDB), 3000 (Grafana). El listener WebSocket de Mosquitto queda **solo dentro de la red Docker** (evita conflictos con otros servicios en 9001/9002).

---

## ✅ Reto 3 — Evaluación ATAM simplificada

Evaluación breve contra los *drivers* del Reto 1 descritos en los ADR y en la rúbrica.

| Driver / preocupación | ¿Cómo lo cubre la arquitectura? | Riesgo o punto sensible | Mitigación / *trade-off* |
|-----------------------|--------------------------------|-------------------------|---------------------------|
| Latencia sensor → backend | MQTT ligero, broker local | Colas en broker si muchos dispositivos | Limitar `max_connections`, QoS acorde |
| Disponibilidad / pérdida de datos | QoS 1, CB en borde (ADR-002) | Desbordamiento del buffer local | Tamaño máximo del buffer en simulador |
| Seguridad | Usuario/contraseña + ACL | Credenciales por defecto en repo | Rotar claves, TLS en producción, no exponer token Influx en flujos versionados |
| Evolución / tiempo de desarrollo | Node-RED + Compose | Menor tipado y pruebas automatizadas | Introducir CI y *secrets* externos |
| Observabilidad (Reto 3) | *Health checks*, logs rotados, script Python | No hay APM completo | `docker compose ps`, `monitor_health.py`, logs JSON |

### Tabla de *trade-offs* (Reto 2, mantenida en Reto 3)

| Decisión | Ganancia principal | Coste / deuda |
|----------|-------------------|---------------|
| Node-RED frente a microservicio a medida | Velocidad de integración MQTT + Influx | Menos control fino y pruebas unitarias clásicas |
| MQTT con autenticación simple (sin TLS en lab) | Simplicidad para el curso | No apto para producción expuesta |
| InfluxDB 2 OSS en un solo host | Consultas Flux y buckets claros | Escalado horizontal no abordado |
| Wokwi + ESP32 como borde principal | Demo guiada sin hardware; mismos tópicos que producción | Requiere compilar firmware y Private IoT Gateway para MQTT local |
| Simulador Python opcional (`python-sim`) | Útil si no usás Wokwi | No sustituye la demo embebida del curso |

---

## 📡 Monitoreo y métricas de disponibilidad (Reto 3)

- **Health checks:** definidos en `docker-compose.yml` para Mosquitto, Node-RED, InfluxDB y Grafana (`wget`/`mosquitto_sub`/`influx ping`).
- **Logs:** controladores `json-file` con rotación (`max-size`, `max-file`).
- **Script Python:** desde la carpeta `Retos/` (con dependencias):

```bash
pip install -r tools/scripts/requirements.txt
python3 tools/scripts/monitor_health.py
```

Salida JSON con comprobaciones HTTP (Node-RED, Influx, Grafana) y autenticación MQTT (`admin` por defecto; variables `MQTT_USER`, `MQTT_PASS`, `MQTT_HOST`).

Inspección manual del estado Docker:

```bash
docker compose ps
docker inspect --format '{{json .State.Health}}' iot_mosquitto | jq .
```

---

## 🧩 Proyecto Wokwi (`edge/wokwi/`)

Firmware **PlatformIO + Arduino** organizado así:

| Archivo | Rol |
|---------|-----|
| `src/config.h` | Pines GPIO, umbral PPM, intervalos de muestreo / MQTT |
| `src/main.cpp` | WiFi, MQTT, lectura MQ-2, **LED + buzzer** de alerta local |

**`diagram.json`:** ESP32 + **MQ-2** (VCC→3V3, GND, **AO→GPIO 34**) + **LED rojo** con resistencia 220 Ω en **GPIO 26** + **buzzer** (pin negativo a GND, positivo a **GPIO 27**). Si PPM &gt; 300: LED encendido y buzzer en pitidos; MQTT sin cambios de tópicos.

- **Hostname MQTT:** `host.wokwi.internal` y puerto **1883** (documentado por Wokwi para llegar a servicios en tu PC cuando el *Private IoT Gateway* está activo). No uses `127.0.0.1` dentro del simulador.
- **Credenciales MQTT:** `sensor` / `sensor123` (mismas que en `services/mosquitto/config/passwd`).
- **Tópicos:** `casa/gas/ppm` y `casa/gas/alerta` (JSON compatible con Node-RED).

Podés abrir **`Retos/`** (raíz con `wokwi.toml` + `diagram.json`) o solo **`edge/wokwi/`**; en ambos casos hay que **compilar** (`pio run` o la *Build Task*) antes de *Start Simulator*.

---

## 🚀 Instalación y ejecución

### Requisitos

- Docker >= 24.x
- Docker Compose >= 2.x
- Git
- **Simulación Wokwi:** VS Code, extensión [Wokwi](https://marketplace.visualstudio.com/items?itemName=wokwi.wokwi-vscode), [PlatformIO IDE](https://marketplace.visualstudio.com/items?itemName=platformio.platformio-ide) (compila el firmware ESP32).

### 1. Obtener el código y entrar al proyecto

```bash
cd Retos
```

### 2. Contraseñas Mosquitto (desarrollo)

El archivo `services/mosquitto/config/passwd` ya incluye usuarios de **laboratorio** (`admin` / `sensor` / `nodered`). Para regenerarlo (recomendado antes de exponer el broker a Internet):

```bash
docker run --rm eclipse-mosquitto:2.0 sh -c \
  "mosquitto_passwd -b -c /tmp/pw admin TU_CLAVE_ADMIN && \
   mosquitto_passwd -b /tmp/pw sensor TU_CLAVE_SENSOR && \
   mosquitto_passwd -b /tmp/pw nodered TU_CLAVE_NR && cat /tmp/pw" \
  > services/mosquitto/config/passwd
chmod 600 services/mosquitto/config/passwd
```

> **Node-RED:** el flujo usa el broker `mqtt://admin:admin123@mosquitto:1883` solo para **desarrollo local**. En producción use *secrets*, usuario dedicado y TLS.

### 3. Levantar los servicios

```bash
docker compose up -d
```

### 4. Verificar que todos los servicios están healthy

```bash
docker compose ps
# Todos deben mostrar (healthy) en STATUS
```

### 5. Acceder a las interfaces

| Servicio   | URL                        | Usuario  | Contraseña  |
|------------|----------------------------|----------|-------------|
| Node-RED   | http://localhost:1880       | —        | —           |
| InfluxDB   | http://localhost:8086       | admin    | admin123456 |
| Grafana    | http://localhost:3000       | admin    | admin123    |

**MQTT (Mosquitto, puerto 1883):** usuarios de ejemplo `admin` / `admin123`, `sensor` / `sensor123`, `nodered` / `nodered123` (ver `services/mosquitto/config/passwd`). Las ACL están en `services/mosquitto/config/acl.conf`.

**Grafana — dashboard:** tras el arranque, abre *Dashboards* → **Detección de gas — PPM** (provisioning en `services/grafana/provisioning/`).

---

## 📁 Estructura del proyecto

```
Retos/
├── docker-compose.yml
├── README.md
├── wokwi.toml                 # Si abres Retos/ como workspace (rutas → edge/wokwi/.pio/...)
├── diagram.json               # Copia del esquema (sincronizado con edge/wokwi/diagram.json)
├── edge/
│   └── wokwi/                 # Código PlatformIO + wokwi.toml alternativo si abres solo esta carpeta
│       ├── wokwi.toml
│       ├── diagram.json
│       ├── platformio.ini
│       └── src/
│           ├── config.h
│           └── main.cpp
├── services/
│   ├── mosquitto/config/      # Broker MQTT
│   ├── nodered/               # flows.json
│   └── grafana/provisioning/  # Datasources y dashboards
└── tools/
    ├── simulator/             # Simulador Python (perfil Docker python-sim)
    └── scripts/               # monitor_health.py, etc.
```

---

## 📐 Decisiones Arquitectónicas (ADR)

### ADR-001 — Uso de MQTT sobre HTTP para telemetría IoT

**Fecha:** Semana 1  
**Estado:** Aceptado

**Contexto:** El sistema requiere transmitir lecturas de gas cada 5 segundos desde un microcontrolador ESP8266 con recursos limitados (RAM: 80KB, CPU: 80MHz).

**Decisión:** Usar MQTT (Mosquitto 2.x) como protocolo de mensajería con QoS 1 y autenticación por usuario/contraseña.

**Consecuencias:**
- ✅ Latencia < 2s sensor → dashboard
- ✅ Bajo consumo de ancho de banda (headers MQTT mínimos vs HTTP)
- ✅ Soporte nativo de patron Pub-Sub
- ⚠️ Requiere configuración de broker propio (mayor complejidad operacional)

---

### ADR-002 — Circuit Breaker con almacenamiento local en SPIFFS

**Fecha:** Semana 2  
**Estado:** Aceptado

**Contexto:** El driver de disponibilidad 24/7 exige que no se pierdan lecturas críticas durante fallos de conectividad nocturna.

**Decisión:** Implementar Circuit Breaker en el firmware del ESP8266: tras 3 fallos MQTT consecutivos, almacenar lecturas en SPIFFS y reintentar cada 30 segundos.

**Consecuencias:**
- ✅ 0% de pérdida de lecturas en desconexiones < 10 minutos
- ✅ Ahorro de batería al no reintentar constantemente
- ⚠️ Ráfaga de mensajes al reconectar (mitigada con QoS 1 y buffer broker)

---

### ADR-003 — Node-RED como capa de procesamiento y gateway

**Fecha:** Semana 2  
**Estado:** Aceptado

**Contexto:** El equipo necesita implementar lógica de umbral, persistencia y notificaciones en un tiempo académico limitado.

**Decisión:** Usar Node-RED como motor de procesamiento, API Gateway y orquestador de notificaciones en lugar de un backend personalizado.

**Consecuencias:**
- ✅ Desarrollo visual sin recompilar código
- ✅ Integración nativa con MQTT, InfluxDB y Telegram
- ⚠️ Menor control técnico para lógica compleja
- ⚠️ Node-RED no es óptimo para alta concurrencia (>100 sensores simultáneos)

---

### ADR-004 — Despliegue local con Docker Compose (Reto 3)

**Fecha:** Semana 3  
**Estado:** Aceptado

**Contexto:** La rúbrica del Reto 3 exige contenerización, *health checks* y visibilidad operativa básica.

**Decisión:** Orquestar Mosquitto, Node-RED, InfluxDB y Grafana en una sola *compose stack* con red `iot_net`, volúmenes persistentes y comprobaciones de salud. El borde se simula con **Wokwi** (`edge/wokwi/`); el simulador Python queda en un **perfil** opcional (`python-sim`).

**Consecuencias:**
- ✅ Misma demo en cualquier máquina con Docker
- ✅ Reinicios automáticos (`restart: unless-stopped`)
- ⚠️ Credenciales por defecto en el repositorio (solo para laboratorio)

---

## 🔍 Monitoreo y health checks

```bash
# Ver logs en tiempo real de todos los servicios
docker compose logs -f

# Ver logs de un servicio específico
docker compose logs -f mosquitto
docker compose logs -f nodered

# Verificar estado de health checks
docker inspect iot_mosquitto | grep -A 10 '"Health"'
docker inspect iot_influxdb  | grep -A 10 '"Health"'

# Reiniciar un servicio sin bajar los demás
docker compose restart nodered
```

---

## 🧪 Demo MQTT (prueba rápida)

```bash
# Suscribirse a todos los tópicos de gas (en una terminal)
docker exec -it iot_mosquitto \
  mosquitto_sub -t "casa/gas/#" -u admin -P admin123 -v

# Publicar una lectura de prueba (en otra terminal)
docker exec -it iot_mosquitto \
  mosquitto_pub -t "casa/gas/ppm" \
  -m '{"ppm": 450, "sensor": "MQ-2"}' \
  -u admin -P admin123

# Publicar alerta crítica
docker exec -it iot_mosquitto \
  mosquitto_pub -t "casa/gas/alerta" \
  -m '{"ppm": 450, "level": "CRITICAL"}' \
  -u admin -P admin123
```

---

## 👥 Equipo

| Nombre | Rol |
|--------|-----|
| Tatiana Milena Arango Simanca | Arquitectura y documentación |
| Luisa Fernanda Urueta Valencia | Implementación e integración |

---

## 📚 Referencias

- Bass, L., Clements, P., & Kazman, R. (2022). *Software architecture in practice* (4.ª ed.). Addison-Wesley.
- Brown, S. (2022). *The C4 model for visualising software architecture*. https://c4model.com
- Eclipse Foundation. (2023). *Eclipse Mosquitto documentation*. https://mosquitto.org/documentation/
- OpenJS Foundation. (2023). *Node-RED documentation*. https://nodered.org/docs/
- OASIS. (2019). *MQTT version 5.0*. https://docs.oasis-open.org/mqtt/mqtt/v5.0/

---

> 📹 **Video demo:** [Enlace al video en YouTube/Drive]  
> 🏫 **Corporación Universitaria Remington** · Arquitectura de Software · 2026
