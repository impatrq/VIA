import serial
import struct
import numpy as np
import cv2
import time
import threading
from flask import Flask, Response
from ultralytics import YOLO
import subprocess
import torch
import io

# ===============================
# CONFIGURACIÓN GENERAL
# ===============================
device = 'cpu'
print(f"🧠 Dispositivo en uso: {device}")

# Modelo más liviano posible
model = YOLO("yolov10n.pt")

# ===============================
# SERIAL (ESP32-CAM)
# ===============================
try:
    ser = serial.Serial('/dev/ttyUSB0', 500000, timeout=1)
    time.sleep(2)
    print("✅ Puerto serial abierto correctamente.")
except Exception as e:
    print("❌ Error abriendo puerto serial:", e)
    ser = None

# ===============================
# VARIABLES GLOBALES
# ===============================
ultimo_jpeg = None
frame_para_inferencia = None
objetos_detectados = []
objetos_para_leer = []
objetos_leidos = set()
ultima_deteccion = 0
ultima_distancia = 0
intervalo = 2.5  # segundos entre inferencias
salida_txt = "detecciones_yolov10n.txt"

# ===============================
# TTS (espeak)
# ===============================
ESPEAK_CMD = '/usr/bin/espeak'
def hablar(texto):
    """Usa eSpeak en modo asíncrono."""
    try:
        subprocess.Popen([ESPEAK_CMD, '-s', '140', '-v', 'es', texto],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print("Error al reproducir voz:", e)

# ===============================
# FLASK APP
# ===============================
app = Flask(__name__)

@app.route('/')
def index():
    return """<h1>Proyecto VIA - Raspberry Pi 5</h1>
              <h3>ESP32-CAM + HC-SR04 + YOLOv10n (CPU)</h3>
              <p><a href='/video'>Ver transmisión en vivo</a></p>"""

def generar_video():
    """Genera el stream MJPEG."""
    global ultimo_jpeg
    while True:
        if ultimo_jpeg:
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' +
                   ultimo_jpeg + b'\r\n')
        time.sleep(0.08)  # 12.5 fps aprox

@app.route('/video')
def video():
    return Response(generar_video(), mimetype='multipart/x-mixed-replace; boundary=frame')

# ===============================
# FUNCIONES AUXILIARES
# ===============================
def read_n_bytes(n, timeout=1.5):
    """Lee exactamente n bytes del puerto serial o None si timeout."""
    if not ser:
        return None
    data = bytearray()
    start = time.time()
    while len(data) < n:
        chunk = ser.read(n - len(data))
        if chunk:
            data.extend(chunk)
        elif time.time() - start > timeout:
            return None
    return bytes(data)

def leer_frame():
    """Lee un frame JPEG y distancia desde ESP32."""
    global ultima_distancia
    if not ser:
        return None
    try:
        ser.reset_input_buffer()
        ser.write(b"IMGSTART\n")

        # Leer distancia (2 bytes)
        dist_bytes = read_n_bytes(2, 1.0)
        if not dist_bytes:
            return None
        ultima_distancia = struct.unpack('>H', dist_bytes)[0]

        # Leer tamaño (4 bytes)
        header = read_n_bytes(4, 1.0)
        if not header:
            return None
        size = struct.unpack('>I', header)[0]
        if not (1000 < size < 600000):
            return None

        # Leer datos JPEG
        img_bytes = read_n_bytes(size, 2.0)
        if not img_bytes:
            return None

        if not (img_bytes.startswith(b'\xff\xd8') and img_bytes.endswith(b'\xff\xd9')):
            return None

        np_arr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        return frame

    except Exception as e:
        print("⚠️ Error lectura serial:", e)
        return None

# ===============================
# HILO CAPTURA
# ===============================
def hilo_captura():
    """Captura frames desde ESP32-CAM."""
    global ultimo_jpeg, frame_para_inferencia
    while True:
        frame = leer_frame()
        if frame is None:
            time.sleep(0.05)
            continue

        # Mostrar distancia
        cv2.putText(frame, f"Distancia: {ultima_distancia} cm",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

        # ROI central para YOLO (reduce carga)
        h, w = frame.shape[:2]
        roi = frame[int(h*0.25):int(h*0.75), int(w*0.25):int(w*0.75)]

        # JPEG comprimido para transmisión
        ok, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 65])
        if ok:
            ultimo_jpeg = jpeg.tobytes()

        frame_para_inferencia = roi
        time.sleep(0.12)  # ≈8 FPS, baja uso CPU

# ===============================
# HILO INFERENCIA
# ===============================
def hilo_inferencia():
    """Ejecuta detección YOLO periódicamente."""
    global frame_para_inferencia, ultima_deteccion, objetos_detectados, objetos_para_leer
    while True:
        if frame_para_inferencia is None or (time.time() - ultima_deteccion < intervalo):
            time.sleep(0.1)
            continue
        try:
            frame = frame_para_inferencia
            with torch.inference_mode():
                results = model.predict(
                    frame,
                    conf=0.55,
                    iou=0.45,
                    imgsz=224,
                    max_det=3,
                    verbose=False,
                    device=device
                )

            objetos = []
            for r in results:
                if hasattr(r, 'boxes') and r.boxes is not None:
                    for box in r.boxes:
                        cls = int(box.cls[0])
                        if 0 <= cls < len(model.names):
                            objetos.append(model.names[cls])

            objetos_detectados = list(set(objetos))
            nuevos = [o for o in objetos_detectados if o not in objetos_leidos]

            if nuevos:
                objetos_para_leer.extend(nuevos)

            if objetos_detectados:
                with open(salida_txt, "a") as f:
                    f.write(f"[{time.strftime('%H:%M:%S')}] "
                            f"{ultima_distancia} cm -> {', '.join(objetos_detectados)}\n")
                print(f"✅ Detectado ({ultima_distancia} cm): {', '.join(objetos_detectados)}")

            ultima_deteccion = time.time()

        except Exception as e:
            print("❌ Error en inferencia:", e)
            time.sleep(1)

# ===============================
# HILO TTS
# ===============================
def hilo_tts():
    """Lee los objetos nuevos por voz."""
    global objetos_para_leer
    while True:
        if objetos_para_leer:
            texto = ", ".join(objetos_para_leer)
            hablar(texto)
            objetos_para_leer.clear()
        time.sleep(0.25)

# ===============================
# MAIN
# ===============================
if __name__ == '__main__':
    print("📸 Iniciando hilos...")
    threading.Thread(target=hilo_captura, daemon=True).start()
    threading.Thread(target=hilo_inferencia, daemon=True).start()
    threading.Thread(target=hilo_tts, daemon=True).start()

    print("🌐 Servidor activo en: http://localhost:8080")
    print("👉 Accedé desde otra PC: http://<IP_Raspberry>:8080")
    app.run(host='0.0.0.0', port=8080, debug=False, threaded=True)
