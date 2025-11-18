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

# Modelo más liviano posible
model = YOLO("yolov10n.pt")

# ===============================
# SERIAL (ESP32-CAM)
# ===============================
try:
    ser = serial.Serial('/dev/ttyUSB0', 500000, timeout=2)
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
intervalo = 3.0  # segundos entre inferencias
salida_txt = "detecciones_yolov10n.txt"

# ===============================
# TTS (espeak)
# ===============================
ESPEAK_CMD = '/usr/bin/espeak'
def hablar(texto):
    try:
        subprocess.Popen([ESPEAK_CMD, '-s', '140', '-v', 'es', texto])
    except Exception as e:
        print("Error al reproducir voz:", e)

# ===============================
# FLASK APP
# ===============================
app = Flask(__name__)

@app.route('/')
def index():
    return """<h1>Proyecto VIA - Raspberry Pi 5</h1>
              <h2>Monitoreo desde ESP32-CAM + YOLOv10n</h2>
              <p><a href='/video'>Ver transmisión en vivo</a></p>"""

def generar_video():
    global ultimo_jpeg
    while True:
        if ultimo_jpeg is not None:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + ultimo_jpeg + b'\r\n')
        time.sleep(0.1)

@app.route('/video')
def video():
    return Response(generar_video(), mimetype='multipart/x-mixed-replace; boundary=frame')

# ===============================
# FUNCIONES AUXILIARES
# ===============================
def read_n_bytes(n, timeout=2.0):
    """Lee exactamente n bytes o None si no llega a tiempo."""
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
        ser.write(b"IMG\n")

        # Leer 2 bytes distancia
        dist = read_n_bytes(2, 1.0)
        if not dist:
            return None
        ultima_distancia = struct.unpack('>H', dist)[0]

        # Leer 4 bytes tamaño
        header = read_n_bytes(4, 1.0)
        if not header:
            return None
        size = struct.unpack('>I', header)[0]
        if size <= 0 or size > 600000:
            return None

        # Leer imagen
        img_bytes = read_n_bytes(size, 2.0)
        if not img_bytes:
            return None
        if not (img_bytes.startswith(b'\xff\xd8') and img_bytes.endswith(b'\xff\xd9')):
            return None

        np_arr = np.frombuffer(img_bytes, dtype=np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        return frame

    except Exception as e:
        print("Error lectura serial:", e)
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

        # ROI central (más rápido)
        h, w = frame.shape[:2]
        roi = frame[int(h*0.25):int(h*0.75), int(w*0.25):int(w*0.75)]

        # Codificar JPEG para Flask
        ok, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 65])
        if ok:
            ultimo_jpeg = jpeg.tobytes()

        frame_para_inferencia = roi
        time.sleep(0.15)  # menor carga CPU

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
                    conf=0.5,
                    iou=0.45,
                    max_det=2,
                    imgsz=224,
                    verbose=False,
                    device=device
                )
            objetos = []
            for r in results:
                if hasattr(r, 'boxes') and r.boxes is not None:
                    for box in r.boxes:
                        cls = int(box.cls[0]) if hasattr(box, 'cls') else int(box.cls)
                        if cls < len(model.names):
                            objetos.append(model.names[cls])

            objetos_detectados = list(set(objetos))

            nuevos = [o for o in objetos_detectados if o not in objetos_leidos]
            if nuevos:
                objetos_para_leer.extend(nuevos)

            if objetos_detectados:
                with open(salida_txt, "a") as f:
                    f.write(f"[{time.strftime('%H:%M:%S')}] {ultima_distancia} cm -> {', '.join(objetos_detectados)}\n")
                print(f"✅ Detectado ({ultima_distancia} cm): {', '.join(objetos_detectados)}")

            ultima_deteccion = time.time()

        except Exception as e:
            print("Error en inferencia:", e)
            time.sleep(1)

# ===============================
# HILO TTS
# ===============================
def hilo_tts():
    global objetos_para_leer
    while True:
        if objetos_para_leer:
            texto = ", ".join(objetos_para_leer)
            hablar(f"{texto}")
            objetos_para_leer.clear()
        time.sleep(0.2)

# ===============================
# MAIN
# ===============================
if __name__ == '__main__':
    print("📸 Iniciando hilos...")
    threading.Thread(target=hilo_captura, daemon=True).start()
    threading.Thread(target=hilo_inferencia, daemon=True).start()
    threading.Thread(target=hilo_tts, daemon=True).start()

    print("🌐 Servidor activo en: http://localhost:8080")
    print("Usá http://<IP_Raspberry>:8080 desde otro dispositivo.")
    app.run(host='0.0.0.0', port=8080, debug=False, threaded=True)
