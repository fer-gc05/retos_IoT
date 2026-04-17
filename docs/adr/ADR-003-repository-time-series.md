# ADR-003: Persistencia central en InfluxDB (Repository)

- **Estado:** Aprobado
- **Fecha:** 2026-04-16

## Contexto

Se requiere almacenar lecturas historicas de gas y eventos de alerta para analitica temporal, visualizacion y trazabilidad operativa.

## Decision

Adoptar un enfoque **Repository** para persistencia en series de tiempo:

- Node-RED transforma payload MQTT a line protocol.
- Nodo HTTP escribe en InfluxDB (`bucket: gas_readings`).
- El acceso a datos para dashboards se centraliza desde esa fuente.

## Consecuencias

### Positivas

- Fuente unica de verdad para historicos y tendencias.
- Integracion directa con Grafana para dashboards.
- Facilita auditoria de eventos y metricas.

### Negativas

- Dependencia operativa de InfluxDB.
- Requiere administrar token y configuracion de escritura.

