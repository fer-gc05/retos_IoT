# Sistema IoT de Deteccion de Fuga de Gas

Proyecto academico del curso de Arquitectura de Software (3 retos), enfocado en una arquitectura IoT con adquisicion de datos de gas, procesamiento en tiempo real, persistencia historica y alertamiento.

## 1) Resumen del sistema

- **Objetivo:** detectar concentracion de gas y generar alertas tempranas para usuario residente y administrador.
- **Flujo principal:** Sensor MQ-2 (Wokwi/hardware o simulador) -> MQTT (Mosquitto) -> Node-RED -> InfluxDB -> Dashboard (Grafana/Node-RED UI) + Notificaciones.
- **Modalidad de despliegue:** contenedores Docker Compose para backend y herramientas de monitoreo basico.
- **Estado actual:** implementacion funcional de punta a punta con componentes de seguridad, tolerancia a fallos y observabilidad base.

## 2) Arquitectura y diagramas C4

Los diagramas del proyecto estan en `diagramas/`:

- `nivel 1 - c4.png` -> Contexto
- `nivel 2 - c4.png` -> Contenedores
- `nivel 3 - c4 .png` -> Componentes
- `nivel 4 - c4.png` -> Codigo/Implementacion
- `c4 - relacion entre niveles.puml` + `relacion - c4.png` -> Trazabilidad entre niveles C4

> Nota: el diagrama de relacion entre niveles muestra el zoom progresivo 1->2->3->4 sin mezclar todo en una sola vista.

### Vista directa de diagramas C4

**Relacion entre niveles C4 (zoom progresivo)**

![Relacion C4](<diagramas/relacion - c4.png>)

**Nivel 1 - Contexto**

![C4 Nivel 1](<diagramas/nivel 1 - c4.png>)

**Nivel 2 - Contenedores**

![C4 Nivel 2](<diagramas/nivel 2 - c4.png>)

**Nivel 3 - Componentes**

![C4 Nivel 3](<diagramas/nivel 3 - c4 .png>)

**Nivel 4 - Codigo**

![C4 Nivel 4](<diagramas/nivel 4 - c4.png>)

## 3) Estructura del repositorio

```text
.
├── Retos/
│   ├── docker-compose.yml
│   ├── edge/wokwi/
│   │   ├── src/main.cpp
│   │   └── src/config.h
│   ├── services/
│   │   ├── mosquitto/config/
│   │   ├── nodered/flows.json
│   │   └── grafana/provisioning/
│   └── tools/
│       ├── simulator/sensor_sim.py
│       └── scripts/monitor_health.py
├── diagramas/
└── docs/
    ├── reto1.docx
    ├── reto2.docx
    ├── reto3.docx
    └── adr/
```

## 4) Drivers arquitectonicos (sintesis)

- **D1 - Seguridad de comunicaciones:** autenticacion MQTT + ACL y control de acceso por topicos.
- **D2 - Disponibilidad:** health checks en Docker Compose y reconexion automatica en borde.
- **D3 - Escalabilidad funcional:** desacoplamiento por Pub-Sub y procesamiento orientado a flujos.
- **D4 - Trazabilidad y monitoreo:** persistencia temporal + script de verificacion de salud.
- **D5 - Respuesta ante riesgo:** deteccion de umbral y notificacion inmediata.
- **D6 - Flexibilidad de entorno:** soporte de simulacion y hardware (Wokwi/ESP32).

## 5) Patrones/estilos aplicados

- **Pub-Sub (MQTT):** desacopla productor (sensor/simulador) y consumidores (Node-RED, alertas).
- **Repository:** persistencia centralizada de lecturas/eventos hacia InfluxDB.
- **Circuit Breaker:** estrategia de resiliencia en simulador y reconexion en firmware.
- **Gateway (API Flow):** exposicion de datos consolidados hacia widgets/dashboard.
- **Arquitectura en capas (percepcion-red-procesamiento-aplicacion):** separacion de responsabilidades.

ADRs asociados:

- `docs/adr/ADR-001-pubsub-mqtt.md`
- `docs/adr/ADR-002-circuit-breaker.md`
- `docs/adr/ADR-003-repository-time-series.md`

## 6) Stack tecnologico

- **Broker MQTT:** Eclipse Mosquitto 2.x
- **Orquestacion de flujos:** Node-RED 3.1
- **Base de datos:** InfluxDB 2.7
- **Visualizacion:** Grafana 10.2
- **Edge:** ESP32 (Wokwi) + sensor MQ-2
- **Simulacion y scripts:** Python 3.11 + `paho-mqtt`
- **Despliegue:** Docker Compose

## 7) Instrucciones de instalacion y ejecucion

### 7.1 Prerrequisitos

- Docker + Docker Compose
- Python 3.10+ (opcional para monitor y simulador fuera de contenedor)

### 7.2 Levantar el backend IoT (reto 3)

```bash
cd Retos
docker compose up -d
docker compose ps
```

Servicios esperados:

- Mosquitto: `localhost:1883`
- Node-RED: `http://localhost:1880`
- InfluxDB: `http://localhost:8086`
- Grafana: `http://localhost:3000`

### 7.3 Cargar telemetria

**Firmware Wokwi/ESP32**

- Codigo en `Retos/edge/wokwi/src/main.cpp`.
- Publica en topicos:
  - `casa/gas/ppm`
  - `casa/gas/alerta`

## 8) Credenciales y configuracion base (entorno academico)

- **Mosquitto admin:** `admin / admin123`
- **Mosquitto sensor:** `sensor / sensor123`
- **Grafana:** `admin / admin123`
- **InfluxDB:** `admin / admin123456`
- **Token Influx inicial:** definido en `Retos/docker-compose.yml`

> Importante: para entorno productivo se deben rotar credenciales y mover secretos a variables/gestor seguro.

## 9) Evidencia funcional esperada (checklist)

- [ ] Publicacion MQTT de lecturas y alertas.
- [ ] Flujo Node-RED recibiendo y transformando payload.
- [ ] Escritura de puntos en InfluxDB.
- [ ] Dashboard mostrando valor en tiempo real e historico.
- [ ] Alertas emitidas cuando el umbral es superado.
- [ ] `monitor_health.py` reportando disponibilidad integral.

## 10) Trade-offs (resumen)

1. **Simplicidad vs seguridad fuerte:** se usa auth/ACL en MQTT, pero con credenciales de laboratorio para agilizar pruebas.
2. **Latencia baja vs robustez de buffer:** en simulador el buffer es en memoria (mas simple) y en firmware el control de reintentos es acotado.
3. **Entrega rapida vs complejidad operacional:** stack completo en Compose facilita la demo, pero agrega consumo y configuracion de multiples servicios.


