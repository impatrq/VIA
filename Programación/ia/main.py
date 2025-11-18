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