import tensorflow as tf
import tensorflow_hub as hub
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO

print("Cargando modelo TensorFlow Hub...")
detector = hub.load("https://tfhub.dev/tensorflow/ssd_mobilenet_v2/2")
print("Modelo cargado.")

# Sube tu imagen a Google Colab o proporciona una URL.
# Ejemplo de cómo subir un archivo desde tu máquina:
# from google.colab import files
# uploaded = files.upload()
# for filename in uploaded.keys():
#    image_path = filename
# print(f"Imagen subida: {image_path}")

# O especifica la ruta de una imagen existente en Colab o una URL
# Puedes buscar imágenes de ejemplo en internet y poner la URL directamente
image_path = 'https://ultralytics.com/images/bus.jpg' # Ejemplo con una imagen de prueba
# image_path = 'ruta/a/tu/imagen.jpg' # <<< ¡CAMBIA ESTO POR LA RUTA DE TU IMAGEN!

# Función para cargar y preprocesar la imagen
def load_image_from_path(image_path):
    if image_path.startswith('http'):
        response = requests.get(image_path)
        image = Image.open(BytesIO(response.content)).convert("RGB")
    else:
        image = Image.open(image_path).convert("RGB")

        
    # TensorFlow Hub models expect uint8 images and might resize internally
    # Convert to numpy array and add batch dimension
    image_np = np.array(image)
    return image, image_np

original_image_pil, image_np = load_image_from_path(image_path)

# Realizar la inferencia
# Los modelos de TF Hub esperan un tensor de imagen en formato [1, height, width, 3]
# y devuelven un diccionario con las detecciones.
print("Realizando inferencia...")
input_tensor = tf.convert_to_tensor(image_np, dtype=tf.uint8)
input_tensor = input_tensor[tf.newaxis, ...]

result = detector(input_tensor)

# Los resultados de un modelo de TF Hub suelen ser un diccionario.
# Las claves relevantes son 'detection_boxes', 'detection_scores', 'detection_classes'
# y 'detection_class_entities' o similar para los nombres de las clases.

# Convertir las clases numéricas a nombres legibles.
# Para el modelo 'ssd_mobilenet_v2', las clases son COCO dataset IDs.
# Aquí usaremos un mapeo simple o podemos cargar un diccionario de etiquetas.
# Para una lista completa de etiquetas de COCO, podrías cargar un archivo .pbtxt
# o usar un mapeo predefinido.

# Nota: Este modelo no devuelve 'detection_class_entities' directamente,
# sino 'detection_classes' (IDs). Para obtener nombres, necesitamos un mapeo.
# Para simplificar, asumiremos que conocemos algunos de los IDs de COCO.

# Diccionario de mapeo de clases (ejemplo parcial para COCO dataset)
# Puedes expandir este diccionario para más clases si es necesario.
# O, si el modelo proporciona un mapeo, usarlo.
COCO_INSTANCE_CATEGORY_NAMES = [
    '__background__', 'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus',
    'train', 'truck', 'boat', 'traffic light', 'fire hydrant', 'N/A', 'stop sign',
    'parking meter', 'bench', 'bird', 'cat', 'dog', 'horse', 'sheep', 'cow', 'elephant',
    'bear', 'zebra', 'giraffe', 'N/A', 'backpack', 'umbrella', 'N/A', 'N/A', 'handbag',
    'tie', 'suitcase', 'frisbee', 'skis', 'snowboard', 'sports ball', 'kite',
    'baseball bat', 'baseball glove', 'skateboard', 'surfboard', 'tennis racket',
    'bottle', 'N/A', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl', 'banana',
    'apple', 'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza', 'donut',
    'cake', 'chair', 'couch', 'potted plant', 'bed', 'N/A', 'dining table', 'N/A',
    'N/A', 'toilet', 'N/A', 'tv', 'laptop', 'mouse', 'remote', 'keyboard', 'cell phone',
    'microwave', 'oven', 'toaster', 'sink', 'refrigerator', 'N/A', 'book', 'clock',
    'vase', 'scissors', 'teddy bear', 'hair drier', 'toothbrush'
]
# Parámetros para filtrado
min_confidence_threshold = 0.25 # Similar al conf=0.25 en YOLO

# Extraer resultados
detection_boxes = result['detection_boxes'][0].numpy() # [ymin, xmin, ymax, xmax]
detection_scores = result['detection_scores'][0].numpy()
detection_classes = result['detection_classes'][0].numpy().astype(int)

# Crear una copia de la imagen PIL para dibujar
draw_image = original_image_pil.copy()
draw = ImageDraw.Draw(draw_image)
width, height = original_image_pil.size

print("\nAnálisis de las detecciones:\n")


detected_objects_count = 0
for i in range(len(detection_scores)):
    if detection_scores[i] >= min_confidence_threshold:
        detected_objects_count += 1
        ymin, xmin, ymax, xmax = detection_boxes[i]

        # Convertir coordenadas normalizadas a píxeles
        x1 = int(xmin * width)
        y1 = int(ymin * height)
        x2 = int(xmax * width)
        y2 = int(ymax * height)

        class_id = detection_classes[i]
        label = COCO_INSTANCE_CATEGORY_NAMES[class_id] if class_id < len(COCO_INSTANCE_CATEGORY_NAMES) else f"Unknown Class ({class_id})"
        confidence = detection_scores[i]

        # Dibujar el recuadro y la etiqueta
        draw.rectangle([(x1, y1), (x2, y2)], outline="red", width=3)

        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except IOError:
            font = ImageFont.load_default()

        draw.text((x1 + 5, y1 + 5), f"{label}: {confidence:.2f}", fill="red", font=font)

        print(f"  - Objeto: {label} (Confianza: {confidence:.2f}) en [x1:{x1}, y1:{y1}, x2:{x2}, y2:{y2}]")
