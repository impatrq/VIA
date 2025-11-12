#include "esp_camera.h"

// ===============================
// CONFIGURACIÓN DE LA CÁMARA (AI Thinker ESP32-CAM)
// ===============================
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27

#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

// ===============================
// SENSOR ULTRASÓNICO HC-SR04
// ===============================
#define TRIG_PIN  14
#define ECHO_PIN  15

// ===============================
// CONFIGURACIÓN SERIAL
// ===============================
#define BAUDRATE 500000
#define CMD_TIMEOUT_MS 1000

// ===============================
// FUNCIONES AUXILIARES
// ===============================

// Espera el comando “IMGSTART” con timeout
bool esperarComandoIMG(unsigned long timeout_ms) {
  unsigned long start = millis();
  String cmd = "";
  while (millis() - start < timeout_ms) {
    while (Serial.available() > 0) {
      char c = (char)Serial.read();
      if (c == '\n') {
        cmd.trim();
        if (cmd == "IMGSTART") return true;
        cmd = "";
      } else {
        cmd += c;
      }
    }
    delay(1);
  }
  return false;
}

// Mide distancia con el sensor ultrasónico (en cm)
float medirDistanciaCM() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  long duration = pulseIn(ECHO_PIN, HIGH, 30000); // 30 ms → máx ≈5 m
  if (duration == 0) return -1.0; // sin eco
  float distance = (duration / 2.0) * 0.0343;
  return distance;
}

// ===============================
// CONFIGURACIÓN PRINCIPAL
// ===============================
void setup() {
  Serial.begin(BAUDRATE);
  Serial.setTimeout(100);
  Serial.println("\nESP32-CAM lista. Esperando comando IMGSTART...");

  // Inicializa pines del sensor ultrasónico
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  // Configuración de la cámara
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer   = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = FRAMESIZE_VGA;   // 640×480  fluido
  config.jpeg_quality = 12;            // menor → más calidad
  config.fb_count = 1;

  if (esp_camera_init(&config) != ESP_OK) {
    Serial.println("❌ Error al inicializar la cámara");
    while (true) delay(1000);
  }

  Serial.println("✅ Cámara inicializada correctamente");
}

// ===============================
// LOOP PRINCIPAL
// ===============================
void loop() {
  // Esperar comando IMGSTART\n desde Raspberry
  if (!esperarComandoIMG(CMD_TIMEOUT_MS)) {
    delay(5);
    return;
  }

  // Medir distancia
  float distancia = medirDistanciaCM();
  if (distancia < 0) distancia = 0;

  // Capturar imagen
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("⚠️ Error al capturar imagen");
    uint16_t dist_int_err = 0;
    uint8_t dist_bytes_err[2] = { (uint8_t)(dist_int_err >> 8), (uint8_t)(dist_int_err & 0xFF) };
    Serial.write(dist_bytes_err, 2);
    uint8_t header_err[4] = {0,0,0,0};
    Serial.write(header_err, 4);
    delay(50);
    return;
  }

  // Enviar distancia (2 bytes big-endian)
  uint16_t dist_int = (uint16_t)distancia;
  uint8_t dist_bytes[2] = {
    (uint8_t)((dist_int >> 8) & 0xFF),
    (uint8_t)(dist_int & 0xFF)
  };
  Serial.write(dist_bytes, 2);

  // Enviar tamaño de imagen (4 bytes big-endian)
  uint32_t len = fb->len;
  uint8_t header[4] = {
    (uint8_t)((len >> 24) & 0xFF),
    (uint8_t)((len >> 16) & 0xFF),
    (uint8_t)((len >> 8) & 0xFF),
    (uint8_t)(len & 0xFF)
  };
  Serial.write(header, 4);

  // Enviar datos JPEG
  Serial.write(fb->buf, fb->len);
  Serial.flush();

  // Liberar frame buffer
  esp_camera_fb_return(fb);

  // Pequeña pausa entre capturas
  delay(50);
}
