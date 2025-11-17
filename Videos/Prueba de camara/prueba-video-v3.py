import serial
import struct
import numpy as np
import cv2
import time

# ============================================
# CONFIG
# ============================================
PORT = '/dev/ttyUSB0'
BAUD = 500000      # 🔹 Cambiado desde 921600 a 500000
TIMEOUT = 2.0

print(f"Conectando a {PORT} @ {BAUD}...")
ser = serial.Serial(PORT, BAUD, timeout=TIMEOUT)
time.sleep(2)
print("Conectado correctamente.\n")

# ============================================
# FUNCIONES AUXILIARES
# ============================================

def read_n_bytes(n, timeout=2.0):
    """Lee exactamente n bytes o None si no se completan en timeout."""
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

# ============================================
# LECTURA DE FRAME CON CABECERA IMGSTART
# ============================================

def leer_frame():
    """Pide una imagen al ESP32-CAM y la devuelve como frame OpenCV."""
    global ultima_distancia
    ser.write(b"IMG\n")  # comando al ESP32

    # Buscar cabecera "IMGSTART"
    header = bytearray()
    start_time = time.time()
    while b"IMGSTART" not in header:
        bch = ser.read(1)
        if bch:
            header += bch
            if len(header) > 100:
                header = header[-8:]  # mantener ventana deslizante
        else:
            if time.time() - start_time > 2.0:
                print("⏱ Timeout esperando cabecera IMGSTART")
                return None

    # Leer distancia (2 bytes)
    dist_bytes = read_n_bytes(2, timeout=1.0)
    if not dist_bytes or len(dist_bytes) != 2:
        print("⚠️ Error leyendo distancia")
        return None
    distancia = struct.unpack('>H', dist_bytes)[0]

    # Leer tamaño de imagen (4 bytes)
    len_bytes = read_n_bytes(4, timeout=1.0)
    if not len_bytes or len(len_bytes) != 4:
        print("⚠️ Error leyendo longitud")
        return None
    img_len = struct.unpack('>I', len_bytes)[0]

    # Validar tamaño
    if img_len <= 0 or img_len > 300000:
        print(f"⚠️ Tamaño inválido: {img_len}")
        return None

    # Leer los datos JPEG
    img_data = read_n_bytes(img_len, timeout=3.0)
    if not img_data or len(img_data) != img_len:
        print("⚠️ Error leyendo imagen completa")
        return None

    # Decodificar imagen
    np_arr = np.frombuffer(img_data, dtype=np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if frame is None:
        print("⚠️ Error decodificando imagen JPEG")
        return None

    return frame, distancia

# ============================================
# LOOP PRINCIPAL
# ============================================

try:
    idx = 0
    while True:
        print(f"\n[{idx}] Solicitando imagen al ESP32-CAM...")
        result = leer_frame()
        if result is None:
            print("❌ Falló lectura, reintentando...")
            time.sleep(0.5)
            continue

        frame, dist = result
        print(f"✅ Distancia: {dist} cm, mostrando frame ({frame.shape[1]}x{frame.shape[0]})")

        # Mostrar imagen en ventana
        cv2.putText(frame, f"{dist} cm", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
        cv2.imshow("ESP32-CAM Video", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        idx += 1

except KeyboardInterrupt:
    print("\nInterrumpido por el usuario.")
finally:
    ser.close()
    cv2.destroyAllWindows()
    print("Puerto cerrado.")
