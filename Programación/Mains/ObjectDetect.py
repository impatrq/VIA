import cv2
import numpy as np
import serial
import struct
import time

# --- CONFIGURACIÓN DE MODELO Y CLASES ---
model = './Deteccion-de-objetos-main/ssd_mobilenet_v3_large_coco_2020_01_14/frozen_inference_graph.pb'
config = './Deteccion-de-objetos-main/ssd_mobilenet_v3_large_coco_2020_01_14.pbtxt'
clases = './Deteccion-de-objetos-main/coco_labels.txt'

with open(clases) as cl:
    labels = [line.strip() for line in cl.read().split("\n") if line.strip()]
print(f"Clases cargadas: {len(labels)}")

net = cv2.dnn.readNetFromTensorflow(model, config)

# --- CONEXIÓN BLUETOOTH ---
# Ajustá el puerto según tu sistema (ej: /dev/rfcomm0 en Linux o COM7 en Windows)
BT_PORT = "COM7"
BAUD_RATE = 115200

print(f"Conectando a ESP32-CAM en {BT_PORT}...")
bt = serial.Serial(BT_PORT, BAUD_RATE, timeout=10)
time.sleep(2)
print("Conectado ok")

# --- FUNCIONES DE DETECCIÓN ---
def object_detect(net, img):
    size = 320
    blob = cv2.dnn.blobFromImage(img, 1/127.5, (size, size), (127.5, 127.5, 127.5), swapRB=True, crop=False)
    net.setInput(blob)
    return net.forward()

def dibujar_objetos_con_nms(img, objects, labels, umbral=0.5, nms_umbral=0.4):
    filas, colum, _ = img.shape
    boxes, class_ids, confidences = [], [], []

    for i in range(objects.shape[2]):
        clase_id = int(objects[0, 0, i, 1])
        puntaje = float(objects[0, 0, i, 2])
        if puntaje > umbral:
            x1 = int(objects[0, 0, i, 3] * colum)
            y1 = int(objects[0, 0, i, 4] * filas)
            x2 = int(objects[0, 0, i, 5] * colum)
            y2 = int(objects[0, 0, i, 6] * filas)
            boxes.append([x1, y1, x2 - x1, y2 - y1])
            class_ids.append(clase_id)
            confidences.append(puntaje)

    indices = cv2.dnn.NMSBoxes(boxes, confidences, umbral, nms_umbral)

    for i in indices:
        i = i.item()
        x, y, w, h = boxes[i]
        clase_id = class_ids[i]
        puntaje = confidences[i]
        etiqueta = f"{labels[clase_id].upper()}: {puntaje*100:.1f}%"
        cv2.rectangle(img, (x, y), (x+w, y+h), (0, 255, 0), 2)
        (text_w, text_h), baseline = cv2.getTextSize(etiqueta, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
        cv2.rectangle(img, (x, y - text_h - 5), (x + text_w, y), (0, 0, 0), cv2.FILLED)
        cv2.putText(img, etiqueta, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 1, cv2.LINE_AA)

# --- FUNCIÓN PARA RECIBIR UNA IMAGEN JPEG DESDE LA ESP32-CAM ---
def recibir_imagen(bt):
    # Pedimos imagen
    bt.write(b"IMG\n")
    
    # Leer los 4 bytes del tamaño
    header = bt.read(4)
    if len(header) < 4:
        print("No se recibio encabezado valido.")
        return None

    img_size = struct.unpack('>I', header)[0]  # Big-endian
    # Leer la imagen completa
    img_bytes = bytearray()
    while len(img_bytes) < img_size:
        chunk = bt.read(img_size - len(img_bytes))
        if not chunk:
            print("Tiempo de espera agotado al recibir imagen.")
            return None
        img_bytes.extend(chunk)

    # Decodificar JPEG a imagen OpenCV
    img_np = np.frombuffer(img_bytes, dtype=np.uint8)
    frame = cv2.imdecode(img_np, cv2.IMREAD_COLOR)
    return frame

# --- BUCLE PRINCIPAL ---
CONFIDENCE_THRESHOLD = 0.5
NMS_THRESHOLD = 0.4

print("Iniciando detección de objetos en tiempo real desde ESP32-CAM...")
while True:
    frame = recibir_imagen(bt)
    if frame is None:
        continue

    detecciones = object_detect(net, frame)
    dibujar_objetos_con_nms(frame, detecciones, labels, umbral=CONFIDENCE_THRESHOLD, nms_umbral=NMS_THRESHOLD)

    cv2.imshow("DETECCIÓN EN TIEMPO REAL - ESP32-CAM", frame)
    
    if cv2.waitKey(1) == 27:  # ESC para salir
        break

cv2.destroyAllWindows()
bt.close()