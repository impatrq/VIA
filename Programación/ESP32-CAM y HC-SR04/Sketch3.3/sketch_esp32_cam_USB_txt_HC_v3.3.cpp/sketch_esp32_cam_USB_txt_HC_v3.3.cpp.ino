#include "esp_camera.h"

// --- Pines de la cámara (AI Thinker ESP32-CAM) ---
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

// --- Pines del sensor ultrasónico HC-SR04 ---
#define TRIG_PIN  14
#define ECHO_PIN  15

// --- Timeout para comandos ---
#define CMD_TIMEOUT_MS 1000

// =========================================================
// Configuración inicial
// =========================================================
void setup() {
  Serial.begin(500000);   // 🔹 BAUDRATE sincronizado con Raspberry Pi
  Serial.setTimeout(50);
  Serial.println("ESP32-CAM listo, esperando comando IMG...");

  // Pines HC-SR04
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  // Configurar cámara
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
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
  config.frame_size = FRAMESIZE_VGA;  // 640x480
  config.jpeg_quality = 12;           // menor = mejor calidad
  config.fb_count = 1;

  if (esp_camera_init(&config) != ESP_OK) {
    Serial.println("❌ Error al inicializar la cámara");
    while (true) delay(1000);
  }

  Serial.println("✅ Cámara inicializada correctamente");
}

// =========================================================
// Función para medir distancia con HC-SR04
// =========================================================
float medirDistanciaCM() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  long duracion = pulseIn(ECHO_PIN, HIGH, 30000);  // 30ms = ~5m máx
  if (duracion == 0) return -1.0;
  return (duracion / 2.0) * 0.0343;
}

// =========================================================
// Esperar comando IMG
// =========================================================
bool esperarComandoIMG(unsigned long timeout_ms) {
  unsigned long start = millis();
  String cmd = "";
  while (millis() - start < timeout_ms) {
    while (Serial.available() > 0) {
      char c = (char)Serial.read();
      if (c == '\n') {
        cmd.trim();
        return (cmd == "IMG");
      } else {
        cmd += c;
      }
    }
    delay(1);
  }
  return false;
}

// =========================================================
// LOOP PRINCIPAL
// =========================================================
void loop() {
  // Esperar comando desde Raspberry Pi
  if (!esperarComandoIMG(CMD_TIMEOUT_MS)) {
    delay(10);
    return;
  }

  // Medir distancia
  float dist = medirDistanciaCM();
  if (dist < 0) dist = 0;
  uint16_t dist_int = (uint16_t)dist;

  // Capturar imagen
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("⚠️ Error capturando imagen");
    return;
  }

  // --- PROTOCOLO DE ENVÍO ---
  // 1️⃣ Cabecera fija
  Serial.write("IMGSTART", 8);

  // 2️⃣ Distancia (2 bytes big-endian)
  uint8_t dist_bytes[2];
  dist_bytes[0] = (dist_int >> 8) & 0xFF;
  dist_bytes[1] = dist_int & 0xFF;
  Serial.write(dist_bytes, 2);

  // 3️⃣ Tamaño de imagen (4 bytes big-endian)
  uint32_t len = fb->len;
  uint8_t len_bytes[4];
  len_bytes[0] = (len >> 24) & 0xFF;
  len_bytes[1] = (len >> 16) & 0xFF;
  len_bytes[2] = (len >> 8) & 0xFF;
  len_bytes[3] = len & 0xFF;
  Serial.write(len_bytes, 4);

  // 4️⃣ Imagen JPEG
  Serial.write(fb->buf, fb->len);
  Serial.flush();

  esp_camera_fb_return(fb);
  delay(50);  // evita saturar el bus
}
