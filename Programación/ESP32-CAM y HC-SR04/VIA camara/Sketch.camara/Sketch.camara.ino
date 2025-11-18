#include "esp32_cam.h"
#include "FS.h"
#include "SD.h"
#include "SPI.h"


#define PWDN_GPIO_NUM     -1
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM     0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27

#define Y2_GPIO_NUM       5
#define Y3_GPIO_NUM       18
#define Y4_GPIO_NUM       19
#define Y5_GPIO_NUM       21
#define Y6_GPIO_NUM       36
#define Y7_GPIO_NUM       39
#define Y8_GPIO_NUM       34
#define Y9_GPIO_NUM       35
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22


#define SD_CS 13   
#define SD_MOSI 15
#define SD_MISO 2
#define SD_SCK 14

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("Inicializando cámara...");

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
  
  config.frame_size = FRAMESIZE_VGA; 
  config.jpeg_quality = 10;
  config.fb_count = 1;

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Error al inicializar la cámara: 0x%x\n", err);
    return;
  }
  Serial.println("Cámara inicializada.");

  
  Serial.println("Inicializando SD...");
  if(!SD.begin(SD_CS, SPI, 40000000)) {
    Serial.println("Error inicializando SD");
    return;
  }
  Serial.println("SD inicializada.");

  Serial.println("Tomando foto...");
  camera_fb_t * fb = esp_camera_fb_get();
  if(!fb) {
    Serial.println("Error al capturar foto");
    return;
  }


  File file = SD.open("/photo.jpg", FILE_WRITE);
  if(!file){
    Serial.println("Error al abrir archivo en SD");
  } else {
    file.write(fb->buf, fb->len);
    Serial.println("Foto guardada en SD como photo.jpg");
    file.close();
  }
  
  esp_camera_fb_return(fb);
}

void loop() {
 
}