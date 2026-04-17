# ADR-002: Resiliencia de publicacion con Circuit Breaker

- **Estado:** Aprobado
- **Fecha:** 2026-04-16

## Contexto

La conectividad MQTT puede fallar de forma intermitente en pruebas de laboratorio (simulacion o hardware). Se necesita reducir perdida de datos y evitar reintentos agresivos.

## Decision

Aplicar una estrategia de **Circuit Breaker**:

- En simulador (`sensor_sim.py`): apertura temporal del circuito tras fallos consecutivos, buffer en memoria y reintento diferido.
- En firmware (`main.cpp`): reconexion automatica al broker y continuidad del loop de telemetria.

## Consecuencias

### Positivas

- Mayor continuidad operacional ante fallos transitorios.
- Menor cascada de errores por reconexion inmediata constante.
- Mejor estabilidad de demo y despliegue academico.

### Negativas

- Mayor complejidad del productor IoT.
- El buffer en memoria del simulador no persiste entre reinicios.

