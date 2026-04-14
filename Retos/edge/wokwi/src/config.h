/**
 * Configuración del borde — pines y umbrales (ESP32 + MQ-2 + alertas locales).
 * Ajustá aquí GPIO si cambiás el cableado en diagram.json.
 */
#pragma once

#include <Arduino.h>

// Sensor MQ-2 (salida analógica → ADC1)
static const int PIN_MQ2_AO = 34;
static const int PIN_MQ2_DO = 35; // opcional, no usado en la lógica actual

// Alertas locales (coinciden con diagram.json)
static const int PIN_ALERT_LED = 13; // LED rojo + resistencia
static const int PIN_ALERT_BUZZER = 12;  // Buzzer: pin 1 GPIO, pin 2 GND

static const int PPM_ALERT_THRESHOLD = 300;
static const uint32_t MQTT_PUBLISH_MS = 4000;
static const uint32_t SENSOR_SAMPLE_MS = 500;
