# ADR-001: Uso de Pub-Sub con MQTT

- **Estado:** Aprobado
- **Fecha:** 2026-04-16

## Contexto

El sistema requiere desacoplar productores de datos (ESP32/simulador) de consumidores (Node-RED, almacenamiento, alertas y dashboard), manteniendo baja latencia y soporte para eventos en tiempo real.

## Decision

Adoptar el patron **Publish-Subscribe** usando MQTT (Mosquitto) como backbone de mensajeria, con topicos:

- `casa/gas/ppm`
- `casa/gas/alerta`

## Consecuencias

### Positivas

- Desacoplamiento entre edge y procesamiento.
- Facilidad para agregar nuevos consumidores sin modificar productores.
- Soporte natural para telemetria continua/event-driven.

### Negativas

- Requiere gestionar autenticacion, ACL y disponibilidad del broker.
- Implica observabilidad especifica del canal de mensajeria.

