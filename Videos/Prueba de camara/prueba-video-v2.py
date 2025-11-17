import serial
import struct
import time

ser = serial.Serial('/dev/ttyUSB0', 500000, timeout=1)
time.sleep(2)

for i in range(5):
    ser.write(b"IMG\n")
    print(f"[{i}] Enviado comando IMG...")
    dist_bytes = ser.read(2)
    if len(dist_bytes) < 2:
        print("❌ No se recibió distancia")
        continue

    dist = struct.unpack('>H', dist_bytes)[0]
    print(f"   Distancia recibida: {dist} cm")

    header = ser.read(4)
    if len(header) < 4:
        print("❌ No se recibió encabezado de longitud")
        continue

    img_size = struct.unpack('>I', header)[0]
    print(f"   Tamaño imagen: {img_size} bytes")

    # leer solo los primeros 100 bytes para prueba
    img_bytes = ser.read(min(img_size, 100))
    print(f"   Recibidos {len(img_bytes)} bytes de datos\n")

ser.close()
