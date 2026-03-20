import struct
import threading
import time

from serial import Serial

from lib.interface import (
    OPCODE_DRIVE_DIRECT,
    OPCODE_SAFE,
    OPCODE_START,
    OPCODE_STOP,
    OPCODE_STREAM_SENSORS,
    read_stream,
)
from lib.sensorbox import SensorBox

roomba = Serial("/dev/ttyUSB0", 115200, timeout=0.1)
time.sleep(0.2)
roomba.write(OPCODE_START)
roomba.write(OPCODE_SAFE)
time.sleep(0.2)

sensor_data: SensorBox[list[int]] = SensorBox()


def control_thread():
    while True:
        sensor_data_fixed = sensor_data.get()
        left_wheel = 500 - sensor_data_fixed[3]
        right_wheel = 500 - sensor_data_fixed[0]
        print(left_wheel, right_wheel)
        roomba.write(
            OPCODE_DRIVE_DIRECT
            + struct.pack("<h", right_wheel)
            + struct.pack("<h", left_wheel)
        )
        time.sleep(0.05)


def main():
    PACKETS = (46, 48, 49, 51)
    roomba.write(OPCODE_STREAM_SENSORS + bytes((len(PACKETS),)) + bytes(PACKETS))
    roomba.read_all()

    thread = threading.Thread(target=control_thread, daemon=True)

    while True:
        readings = read_stream(roomba, PACKETS)
        sensor_data.put(readings)
        if not thread.is_alive():
            thread.start()


try:
    main()
finally:
    roomba.write(OPCODE_STOP)
    roomba.close()
