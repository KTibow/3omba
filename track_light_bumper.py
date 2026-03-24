import threading
import time

from serial import Serial

from lib.interface import (
    OPCODE_LEDS,
    OPCODE_SAFE,
    OPCODE_SCHEDULE_LEDS,
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
    last_led_bytes = b""
    last_schedule_bytes = b""
    while True:
        sensor_data_fixed = sensor_data.get()
        bumper = sensor_data_fixed[0]
        print(bumper)
        bumper_low_range = min(bumper * 16, 255)
        bumper_high_range = (bumper * 16) // 256
        led_bytes = OPCODE_LEDS + bytes(
            [
                0,
                bumper_high_range,
                bumper_low_range,
            ]
        )
        schedule_data_1 = 0
        schedule_data_1 |= 0b00000001 if bumper > 0 else 0
        schedule_data_1 |= 0b00000010 if bumper > 1 else 0
        schedule_data_1 |= 0b00000100 if bumper > 8 else 0
        schedule_data_1 |= 0b00001000 if bumper > 10 else 0
        schedule_data_1 |= 0b00010000 if bumper > 50 else 0
        schedule_data_1 |= 0b00100000 if bumper > 100 else 0
        schedule_data_1 |= 0b01000000 if bumper > 400 else 0
        schedule_bytes = OPCODE_SCHEDULE_LEDS + bytes([schedule_data_1, 0])
        if led_bytes != last_led_bytes:
            roomba.write(led_bytes)
            last_led_bytes = led_bytes
        if schedule_bytes != last_schedule_bytes:
            roomba.write(schedule_bytes)
            last_schedule_bytes = schedule_bytes
        time.sleep(0.015)


def main():
    PACKETS = (48,)
    roomba.write(OPCODE_STREAM_SENSORS + bytes((len(PACKETS),)) + bytes(PACKETS))
    roomba.read_all()

    thread = threading.Thread(target=control_thread, daemon=True)

    while True:
        try:
            readings = read_stream(roomba, PACKETS)
            sensor_data.put(readings)
            if not thread.is_alive():
                thread.start()
        except Exception as e:
            print(e)
            continue


try:
    main()
finally:
    roomba.write(OPCODE_STOP)
    roomba.close()
