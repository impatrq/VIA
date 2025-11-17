import cv2
import numpy as np # Necesario para la manipulación de índices de NMS

# --- 1. CONFIGURACIÓN DE RUTAS Y LECTURA DE CLASES ---
model = './Deteccion-de-objetos-main/ssd_mobilenet_v3_large_coco_2020_01_14/frozen_inference_graph.pb'
config = './Deteccion-de-objetos-main/ssd_mobilenet_v3_large_coco_2020_01_14.pbtxt'
clases = './Deteccion-de-objetos-main/coco_labels.txt'

# Extraemos las etiquetas del archivo
with open(clases) as cl:
    # Usamos strip() para eliminar posibles espacios en blanco extra de cada línea
    labels = [line.strip() for line in cl.read().split("\n") if line.strip()] 
print(f"Clases cargadas: {len(labels)}") # Muestra la cantidad de clases cargadas

# Leemos el modelo con TensorFlow
net = cv2.dnn.readNetFromTensorflow(model, config)

# --- 2. FUNCIONES DE DETECCIÓN Y PROCESAMIENTO ---

def object_detect(net, img):
    """Preprocesa la imagen y realiza la inferencia en la red."""
    # Las dimensiones de 320x320 son estándar para este modelo (SSD MobileNet)
    size = 320 
    
    # Preprocesamos la imagen (Blob: Binary Large Object)
    # Estandarización de MobileNet: se normalizan los valores al rango [-1, 1] usando (pixel - 127.5) / 127.5
    blob = cv2.dnn.blobFromImage(
        img, 
        1/127.5, # Factor de escala
        size=(size, size), 
        mean=(127.5, 127.5, 127.5), # Valor medio para restar
        swapRB = True, # OpenCV usa BGR, el modelo espera RGB
        crop = False
    )

    # Pasamos la imagen preprocesada a la red
    net.setInput(blob)

    # Extraemos los objetos detectados (inferencia)
    objetos = net.forward()

    return objetos

def dibujar_objetos_con_nms(img, objects, labels, umbral=0.7, nms_umbral=0.3): #nms:0.4 por default
    """
    Dibuja los cuadros delimitadores después de aplicar Supresión No Máxima (NMS).
    umbral (float): Confianza mínima para considerar una detección. 0.6 es un valor razonable
    nms_umbral (float): Umbral para superposición (IoU) en NMS. 0.4 es el valor por default
    """
    filas, colum, _ = img.shape
    boxes = []
    class_ids = []
    confidences = []

    # Recolectar todas las detecciones que superan el umbral inicial
    for i in range(objects.shape[2]):
        clase_id = int(objects[0, 0, i, 1])
        puntaje = float(objects[0, 0, i, 2])

        if puntaje > umbral:
            # Coordenadas normalizadas a píxeles: [x1, y1, x2, y2]
            x1 = int(objects[0, 0, i, 3] * colum)
            y1 = int(objects[0, 0, i, 4] * filas)
            x2 = int(objects[0, 0, i, 5] * colum)
            y2 = int(objects[0, 0, i, 6] * filas)
            
            w = x2 - x1
            h = y2 - y1
            
            # NMSBoxes espera el formato: [x, y, w, h]
            boxes.append([x1, y1, w, h]) 
            class_ids.append(clase_id)
            confidences.append(puntaje)

    # --- APLICAR SUPRESIÓN NO MÁXIMA (NMS) ---
    # Elimina cuadros duplicados con alta superposición (IoU)
    indices = cv2.dnn.NMSBoxes(boxes, confidences, umbral, nms_umbral)

    # Dibujar solo los cuadros seleccionados por NMS
    for i in indices:
        # Extraer el índice real. El formato de cv2.dnn.NMSBoxes puede devolver un array
        i = i.item() 
        box = boxes[i]
        x, y, w, h = box[0], box[1], box[2], box[3]
        clase_id = class_ids[i]
        puntaje = confidences[i]
        
        # --- Lógica de Dibujado de Rectángulo y Texto (Simplificado) ---
        
        # 1. Dibujar el cuadro delimitador (Bounding Box)
        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
        
        # 2. Preparar el texto de la etiqueta
        etiqueta = f"{labels[clase_id].upper()}: {puntaje*100:.1f}%"
        
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.7
        thickness = 1
        color_texto = (0, 255, 0) # Verde
        color_fondo = (0, 0, 0) # Negro
        
        (text_w, text_h), baseline = cv2.getTextSize(etiqueta, font, font_scale, thickness)
        
        # 3. Dibujar el fondo del texto (rectángulo negro)
        # Posición para el fondo del texto: justo encima del BBox (y-5)
        cv2.rectangle(img, (x, y - text_h - baseline - 5), (x + text_w, y), color_fondo, cv2.FILLED)
        
        # 4. Dibujar el texto
        cv2.putText(img, etiqueta, (x, y - 5), font, font_scale, color_texto, thickness, cv2.LINE_AA)

# --- 3. BUCLE PRINCIPAL DE VIDEO ---

# Creamos la Video Captura
cap = cv2.VideoCapture(0)
# Configuraciones de cámara más estándar (640x480) para mejor compatibilidad/rendimiento
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# Configuramos los umbrales sugeridos
CONFIDENCE_THRESHOLD = 0.5 # Bajado ligeramente para detectar más
NMS_THRESHOLD = 0.4 # Estándar para eliminar solapamiento

while True:
    # Leemos los fotogramas
    ret, frame = cap.read()
    
    if not ret:
        print("Error al leer el frame. Saliendo...")
        break

    # Realizamos las detecciones
    detect = object_detect(net, frame)

    # Mostramos las detecciones usando la función con NMS
    dibujar_objetos_con_nms(frame, detect, labels, 
                            umbral=CONFIDENCE_THRESHOLD, 
                            nms_umbral=NMS_THRESHOLD)

    # Mostramos los Frames
    cv2.imshow("DETECCION DE OBJETOS EN TIEMPO REAL (SSD-MobileNet con NMS)", frame)

    # Cerramos con lectura de teclado (ESC)
    t = cv2.waitKey(1)
    if t == 27: # ASCII 27 es la tecla ESC
        break

# Liberamos la VideoCaptura
cap.release()
# Cerramos la ventana
cv2.destroyAllWindows()