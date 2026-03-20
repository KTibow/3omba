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
        left_wheel = 200
        right_wheel = 200
        if (sensor_data_fixed[0] + sensor_data_fixed[1] + sensor_data_fixed[2]) > 100:
            right_wheel = -200
        if (sensor_data_fixed[3] + sensor_data_fixed[4] + sensor_data_fixed[5]) > 100:
            left_wheel = -200
        # left_wheel -= 3 * (
        #     sensor_data_fixed[3] + sensor_data_fixed[4] + sensor_data_fixed[5]
        # )
        # right_wheel -= 3 * (
        #     sensor_data_fixed[0] + sensor_data_fixed[1] + sensor_data_fixed[2]
        # )
        # if sensor_data_fixed[6] & 0b00000001:
        #     left_wheel -= 3 * 300
        # if sensor_data_fixed[6] & 0b00000010:
        #     right_wheel -= 3 * 300
        # print(sensor_data_fixed, left_wheel, right_wheel)
        roomba.write(
            OPCODE_DRIVE_DIRECT
            + struct.pack(">h", right_wheel)
            + struct.pack(">h", left_wheel)
        )
        time.sleep(0.1)


def main():
    PACKETS = (46, 47, 48, 49, 50, 51, 7)
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
