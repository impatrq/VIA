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

# ===============================
# CONFIGURACIÓN GENERAL
# ===============================
device = 'cpu'
print(f"🧠 Dispositivo en uso: {device}")

model = YOLO("yolov10n.pt")

# ===============================
# SERIAL (ESP32-CAM)
# ===============================
SERIAL_PORT = '/dev/ttyUSB0'
BAUDRATE = 500000
try:
    ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=1)
    time.sleep(1.0)
    print(f"✅ Puerto serial {SERIAL_PORT} abierto a {BAUDRATE} bps.")
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
ultima_deteccion = 0
ultima_distancia = 0
intervalo = 3.0
salida_txt = "detecciones_yolov10n.txt"
DISTANCIA_MAX_RANGO = 100  # cm — límite para determinar "fuera de rango"

# crear/limpiar log
with open(salida_txt, "w") as f:
    f.write("Registro de detecciones (YOLOv10-N)\n=========================\n\n")

# ===============================
# TTS (espeak)
# ===============================
ESPEAK_CMD = '/usr/bin/espeak'
def hablar(texto):
    """Usa espeak para decir texto sin bloquear."""
    try:
        subprocess.Popen([ESPEAK_CMD, '-s', '140', '-v', 'es-la', texto],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print("Error al reproducir voz:", e)

# ===============================
# FLASK STREAMING
# ===============================
app = Flask(__name__)

@app.route('/')
def index():
    return """<h1>Proyecto VIA - Raspberry Pi 5</h1>
              <h3>ESP32-CAM + HC-SR04 + YOLOv10n</h3>
              <p><a href='/video'>Ver transmisión en vivo</a></p>"""

def generar_video():
    global ultimo_jpeg
    while True:
        if ultimo_jpeg:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + ultimo_jpeg + b'\r\n')
        time.sleep(0.08)

@app.route('/video')
def video():
    return Response(generar_video(), mimetype='multipart/x-mixed-replace; boundary=frame')

# ===============================
# FUNCIONES AUXILIARES
# ===============================
def read_n_bytes(n, timeout=2.0):
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
    """Lee un frame y la distancia del ESP32."""
    global ultima_distancia
    if not ser:
        return None
    try:
        ser.reset_input_buffer()
        ser.write(b"IMGSTART\n")

        dist_bytes = read_n_bytes(2, timeout=1.0)
        if not dist_bytes:
            return None
        ultima_distancia = struct.unpack('>H', dist_bytes)[0]

        size_bytes = read_n_bytes(4, timeout=1.0)
        if not size_bytes:
            return None
        img_size = struct.unpack('>I', size_bytes)[0]
        if not (1000 <= img_size <= 600000):
            return None

        img_bytes = read_n_bytes(img_size, timeout=3.0)
        if not img_bytes or len(img_bytes) != img_size:
            return None

        if not (img_bytes.startswith(b'\xff\xd8') and img_bytes.endswith(b'\xff\xd9')):
            return None

        np_arr = np.frombuffer(img_bytes, dtype=np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        return frame

    except Exception as e:
        print("⚠️ Error lectura serial:", e)
        return None

# ===============================
# HILO CAPTURA
# ===============================
def hilo_captura():
    global ultimo_jpeg, frame_para_inferencia
    while True:
        frame = leer_frame()
        if frame is None:
            time.sleep(0.05)
            continue

        cv2.putText(frame, f"Distancia: {ultima_distancia} cm", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)

        h, w = frame.shape[:2]
        roi = frame[int(h*0.25):int(h*0.75), int(w*0.25):int(w*0.75)]

        ok, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 65])
        if ok:
            ultimo_jpeg = jpeg.tobytes()

        frame_para_inferencia = roi
        time.sleep(0.12)

# ===============================
# HILO INFERENCIA
# ===============================
def hilo_inferencia():
    global frame_para_inferencia, ultima_deteccion, objetos_detectados, objetos_para_leer
    while True:
        if frame_para_inferencia is None or (time.time() - ultima_deteccion < intervalo):
            time.sleep(0.1)
            continue

        frame = frame_para_inferencia
        try:
            with torch.inference_mode():
                results = model.predict(
                    frame,
                    conf=0.45,
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
                        cls = int(box.cls[0]) if hasattr(box, 'cls') else int(box.cls)
                        if 0 <= cls < len(model.names):
                            objetos.append(model.names[cls])

            if objetos:
                objetos_detectados = list(set(objetos))
                objetos_para_leer.extend(objetos_detectados)

                estado = "FUERA DE RANGO" if ultima_distancia > DISTANCIA_MAX_RANGO else "EN RANGO"
                linea = f"[{time.strftime('%H:%M:%S')}] {ultima_distancia} cm ({estado}) -> {', '.join(objetos_detectados)}"
                print(linea)
                with open(salida_txt, "a") as f:
                    f.write(linea + "\n")

            ultima_deteccion = time.time()

        except Exception as e:
            print("❌ Error en inferencia:", e)
            time.sleep(1)

# ===============================
# HILO TTS (con control de rango)
# ===============================
def hilo_tts():
    global objetos_para_leer, ultima_distancia
    while True:
        if objetos_para_leer:
            objs = objetos_para_leer.copy()
            objetos_para_leer.clear()

            if ultima_distancia > DISTANCIA_MAX_RANGO:
                # fuera de rango
                if len(objs) == 1:
                    texto = f"{objs[0]} fuera de rango"
                else:
                    texto_obj = ", ".join(objs[:-1]) + f" y {objs[-1]}"
                    texto = f"{texto_obj} fuera de rango"
            else:
                # dentro del rango
                if len(objs) == 1:
                    texto = f"{objs[0]} detectado a {ultima_distancia} centímetros"
                else:
                    texto_obj = ", ".join(objs[:-1]) + f" y {objs[-1]}"
                    texto = f"{texto_obj} detectados a {ultima_distancia} centímetros"

            hablar(texto)

        time.sleep(0.3)

# ===============================
# MAIN
# ===============================
if __name__ == "__main__":
    threading.Thread(target=hilo_captura, daemon=True).start()
    threading.Thread(target=hilo_inferencia, daemon=True).start()
    threading.Thread(target=hilo_tts, daemon=True).start()

    print("🌐 Servidor activo en: http://0.0.0.0:8080")
    app.run(host="0.0.0.0", port=8080, debug=False, threaded=True)
