import serial, struct, time, numpy as np, cv2

def read_n_bytes(ser, n, timeout=2.0):
    data = bytearray()
    start = time.time()
    while len(data) < n:
        chunk = ser.read(n - len(data))
        if chunk:
            data.extend(chunk)
        elif time.time() - start > timeout:
            return None
    return bytes(data)

def leer_frame(ser):
    ser.write(b"IMG\n")
    dist = read_n_bytes(ser, 2)
    if not dist: return None
    header = read_n_bytes(ser, 4)
    if not header: return None
    size = struct.unpack('>I', header)[0]
    img_bytes = read_n_bytes(ser, size)
    if not img_bytes: return None
    np_arr = np.frombuffer(img_bytes, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    return frame

ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=2)

while True:
    frame = leer_frame(ser)
    if frame is not None:
        cv2.imshow("ESP32-CAM", frame)
    if cv2.waitKey(1) == 27:
        break
