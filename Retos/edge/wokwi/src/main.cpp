/**
 * Borde IoT — MQ-2, MQTT y alertas locales (LED + buzzer) por alto indice de gas.
 */
#include "config.h"
#include <Arduino.h>
#include <ArduinoJson.h>
#include <PubSubClient.h>
#include <WiFi.h>

static const char *WIFI_SSID = "Wokwi-GUEST";
static const char *MQTT_USER = "sensor";
static const char *MQTT_PASS = "sensor123";
static const char *TOPIC_PPM = "casa/gas/ppm";
static const char *TOPIC_ALERT = "casa/gas/alerta";
static const char *SENSOR_ID = "MQ-2-WOKWI";

static const char *mqttHost = "host.wokwi.internal";
static const int mqttPort = 1883;

static WiFiClient wifiClient;
static PubSubClient mqtt(wifiClient);

static void setup_wifi() {
  Serial.print(F("WiFi "));
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, "", 6);
  while (WiFi.status() != WL_CONNECTED) {
    delay(100);
    Serial.print(F("."));
  }
  Serial.println(F(" OK"));
  Serial.println(WiFi.localIP());
}

static void reconnect_mqtt() {
  while (!mqtt.connected()) {
    Serial.print(F("MQTT "));
    if (mqtt.connect("wokwi-gas-esp32", MQTT_USER, MQTT_PASS)) {
      Serial.println(F("OK"));
    } else {
      Serial.print(F("err "));
      Serial.println(mqtt.state());
      delay(1500);
    }
  }
}

/** Convierte ADC (0..4095) a indice relativo de gas (0..100). */
static float raw_to_index(int raw) {
  return (raw / 4095.0f) * 100.0f;
}

static float ema_value(float v) {
  static bool initialized = false;
  static float value = 0.0f;
  const float alpha = 0.22f; // visual más estable
  if (!initialized) {
    value = v;
    initialized = true;
    return value;
  }
  value = (alpha * v) + ((1.0f - alpha) * value);
  return value;
}

/** LED encendido y pitidos periódicos mientras haya peligro.
 * En ESP32/Wokwi evitamos tone() para no depender de inicialización LEDC.
 */
static void update_local_alert(bool danger, uint32_t now) {
  static uint32_t lastToggle = 0;
  static bool buzzerOn = false;

  if (!danger) {
    digitalWrite(PIN_ALERT_LED, LOW);
    digitalWrite(PIN_ALERT_BUZZER, LOW);
    lastToggle = 0;
    buzzerOn = false;
    return;
  }

  digitalWrite(PIN_ALERT_LED, HIGH);

  // Pitido intermitente simple para buzzer activo: 200ms ON / 300ms OFF
  const uint32_t interval = buzzerOn ? 200 : 300;
  if (now - lastToggle >= interval) {
    buzzerOn = !buzzerOn;
    digitalWrite(PIN_ALERT_BUZZER, buzzerOn ? HIGH : LOW);
    lastToggle = now;
  }
}

static void publish_telemetry(float gasIndex, int raw, uint32_t now) {
  StaticJsonDocument<192> doc;
  doc["gas_index"] = gasIndex;
  doc["raw"] = raw;
  doc["timestamp"] = (int)(now / 1000);
  doc["sensor"] = SENSOR_ID;

  char payload[192];
  const size_t n = serializeJson(doc, payload, sizeof(payload));
  if (n == 0 || n >= sizeof(payload)) {
    Serial.println(F("JSON overflow"));
    return;
  }

  if (mqtt.publish(TOPIC_PPM, payload, false)) {
    Serial.printf("[MQTT] gas_index=%.2f raw=%d\n", gasIndex, raw);
  } else {
    Serial.println(F("[MQTT] publish fallo"));
  }

  if (gasIndex > 55.0f) {
    StaticJsonDocument<160> alert;
    alert["gas_index"] = gasIndex;
    alert["raw"] = raw;
    alert["level"] = "CRITICAL";
    alert["timestamp"] = (int)(now / 1000);
    alert["sensor"] = SENSOR_ID;
    char alertBuf[160];
    const size_t na = serializeJson(alert, alertBuf, sizeof(alertBuf));
    if (na > 0 && na < sizeof(alertBuf)) {
      mqtt.publish(TOPIC_ALERT, alertBuf, false);
    }
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_MQ2_AO, INPUT);
  pinMode(PIN_ALERT_LED, OUTPUT);
  pinMode(PIN_ALERT_BUZZER, OUTPUT);
  digitalWrite(PIN_ALERT_LED, LOW);

  setup_wifi();
  mqtt.setServer(mqttHost, mqttPort);
  reconnect_mqtt();
}

void loop() {
  if (!mqtt.connected()) {
    reconnect_mqtt();
  }
  mqtt.loop();

  const uint32_t now = millis();

  static uint32_t lastSample = 0;
  static int latestRaw = 0;
  static float latestInstantIndex = 0.0f;
  static float latestFilteredIndex = 0.0f;
  if (now - lastSample >= SENSOR_SAMPLE_MS) {
    lastSample = now;
    const int raw = analogRead(PIN_MQ2_AO);
    latestRaw = raw;
    const float gasIndex = raw_to_index(raw);
    latestInstantIndex = gasIndex;
    const float filteredIndex = ema_value(gasIndex);
    latestFilteredIndex = filteredIndex;
    const bool danger = filteredIndex > 55.0f;
    update_local_alert(danger, now);
    Serial.printf("raw=%d gas_index=%.1f filt=%.1f alerta_local=%s\n", raw, gasIndex, filteredIndex, danger ? "SI" : "no");
  }

  static uint32_t lastMqtt = 0;
  if (now - lastMqtt >= MQTT_PUBLISH_MS) {
    lastMqtt = now;
    // Telemetría usa valor instantáneo para que coincida con el slider en dashboard.
    publish_telemetry(latestInstantIndex, latestRaw, now);
  }
}
