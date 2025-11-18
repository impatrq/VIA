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

# Modelo liviano para Raspberry Pi
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
ultimo_jpeg = None                 # jpeg listo para streaming
frame_para_inferencia = None      # ROI para inferencia
objetos_detectados = []           # últimos objetos detectados
objetos_para_leer = []            # cola TTS
objetos_leidos = set()            # evita repeticiones si querés
ultima_deteccion = 0
ultima_distancia = 0
intervalo = 3.0                   # segundos entre inferencias
salida_txt = "detecciones_yolov10n.txt"

# crear/limpiar archivo de salida al inicio
with open(salida_txt, "w") as f:
    f.write("Registro de detecciones (YOLOv10-N)\n=========================\n\n")

# ===============================
# TTS (espeak)
# ===============================
ESPEAK_CMD = '/usr/bin/espeak'
def hablar(texto):
    """Lanza espeak en background, sin bloquear ni mostrar salida."""
    try:
        subprocess.Popen([ESPEAK_CMD, '-s', '140', '-v', 'es', texto],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print("Error al reproducir voz:", e)

# ===============================
# FLASK para streaming
# ===============================
app = Flask(__name__)

@app.route('/')
def index():
    return """<h1>Proyecto VIA - Raspberry Pi 5</h1>
              <h3>ESP32-CAM + HC-SR04 + YOLOv10n</h3>
              <p>Ver transmisión: <a href='/video'>/video</a></p>"""

def generar_video():
    """Generador MJPEG estable."""
    global ultimo_jpeg
    while True:
        if ultimo_jpeg:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + ultimo_jpeg + b'\r\n')
        time.sleep(0.08)  # ~12 FPS máximo para no saturar CPU

@app.route('/video')
def video():
    return Response(generar_video(), mimetype='multipart/x-mixed-replace; boundary=frame')

# ===============================
# UTIL: lectura robusta de n bytes
# ===============================
def read_n_bytes(n, timeout=2.0):
    """Lee exactamente n bytes o devuelve None si timeout."""
    if not ser:
        return None
    data = bytearray()
    start = time.time()
    while len(data) < n:
        chunk = ser.read(n - len(data))
        if chunk:
            data.extend(chunk)
        else:
            if time.time() - start > timeout:
                return None
    return bytes(data)

# ===============================
# LEER FRAME DESDE ESP32 CON PROTOCOLO IMGSTART
# ===============================
def leer_frame():
    """Pide un frame al ESP32 y devuelve (frame_cv2) o None."""
    global ultima_distancia
    if not ser:
        return None
    try:
        # limpiar buffer de entrada para evitar datos basura residuales
        try:
            ser.reset_input_buffer()
        except Exception:
            pass

        # enviar comando que el ESP32 espera (coincide con firmware)
        ser.write(b"IMGSTART\n")

        # leer 2 bytes distancia (big-endian uint16)
        dist_bytes = read_n_bytes(2, timeout=1.0)
        if not dist_bytes or len(dist_bytes) != 2:
            # no llegó distancia
            return None
        ultima_distancia = struct.unpack('>H', dist_bytes)[0]

        # leer 4 bytes tamaño (big-endian uint32)
        size_bytes = read_n_bytes(4, timeout=1.0)
        if not size_bytes or len(size_bytes) != 4:
            return None
        img_size = struct.unpack('>I', size_bytes)[0]

        # validar tamaño razonable (evita bloqueos por valores corruptos)
        if not (1000 <= img_size <= 600000):
            # tamaño fuera de rango => descartar
            # opcional: leer y descartar img_size bytes si querés intentar resync
            return None

        # leer imagen completa
        img_bytes = read_n_bytes(img_size, timeout=3.0)
        if not img_bytes or len(img_bytes) != img_size:
            return None

        # validar cabeceras JPEG
        if not (img_bytes.startswith(b'\xff\xd8') and img_bytes.endswith(b'\xff\xd9')):
            return None

        # decodificar a frame OpenCV
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
    """Hilo que pide frames al ESP32, crea JPEG para streaming y actualiza ROI."""
    global ultimo_jpeg, frame_para_inferencia, ultima_distancia
    while True:
        frame = leer_frame()
        if frame is None:
            # si falla, esperar un poco y reintentar
            # opcional: imprimir contador de fallos para debug
            time.sleep(0.05)
            continue

        # overlay distancia
        cv2.putText(frame, f"Dist: {ultima_distancia} cm", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)

        # ROI central para inferencia (reduce trabajo)
        h, w = frame.shape[:2]
        roi = frame[int(h*0.25):int(h*0.75), int(w*0.25):int(w*0.75)]

        # preparar jpeg para streaming (solo si codifica correctamente)
        ok, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 65])
        if ok:
            ultimo_jpeg = jpeg.tobytes()

        # actualizar ROI para inferencia (no hacemos copia extra)
        frame_para_inferencia = roi

        # sleep pequeño para limitar FPS y uso CPU
        time.sleep(0.12)  # ~8 FPS de lectura, suficiente para RPi

# ===============================
# HILO INFERENCIA
# ===============================
def hilo_inferencia():
    """Hilo que ejecuta YOLO periódicamente en frame_para_inferencia."""
    global frame_para_inferencia, ultima_deteccion, objetos_detectados, objetos_para_leer, objetos_leidos
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

            objetos_detectados = list(set(objetos))

            # identificar nuevos para leer por TTS
            nuevos = [o for o in objetos_detectados if o not in objetos_leidos]
            if nuevos:
                objetos_para_leer.extend(nuevos)
                objetos_leidos.update(nuevos)

            # log y archivo
            if objetos_detectados:
                linea = f"[{time.strftime('%H:%M:%S')}] {ultima_distancia} cm -> {', '.join(objetos_detectados)}"
                print(linea)
                with open(salida_txt, "a") as f:
                    f.write(linea + "\n")

            ultima_deteccion = time.time()

        except Exception as e:
            print("❌ Error en inferencia:", e)
            time.sleep(1)

# ===============================
# HILO TTS (lee objetos + distancia)
# ===============================
def hilo_tts():
    """Lee por TTS los objetos en la cola junto con la distancia."""
    global objetos_para_leer, ultima_distancia
    while True:
        if objetos_para_leer:
            # construir frase
            objs = objetos_para_leer.copy()
            objetos_para_leer.clear()

            if len(objs) == 1:
                texto = f"{objs[0]} detectado a {ultima_distancia} centímetros"
            else:
                # separar con 'y' para la última palabra
                if len(objs) == 2:
                    texto_obj = f"{objs[0]} y {objs[1]}"
                else:
                    texto_obj = ", ".join(objs[:-1]) + f" y {objs[-1]}"
                texto = f"{texto_obj} detectados a {ultima_distancia} centímetros"

            hablar(texto)

        time.sleep(0.25)

# ===============================
# INICIO PRINCIPAL
# ===============================
if __name__ == "__main__":
    # lanzar hilos
    threading.Thread(target=hilo_captura, daemon=True).start()
    threading.Thread(target=hilo_inferencia, daemon=True).start()
    threading.Thread(target=hilo_tts, daemon=True).start()

    # arrancar servidor Flask
    print("🌐 Servidor activo en: http://0.0.0.0:8080")
    app.run(host="0.0.0.0", port=8080, debug=False, threaded=True)
