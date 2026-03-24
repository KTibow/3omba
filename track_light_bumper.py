import threading
import time

from serial import Serial

from lib.interface import (
    OPCODE_LEDS,
    OPCODE_SAFE,
    OPCODE_SCHEDULE_DISPLAY_ASCII,
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
    last_digit_bytes = b""
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
        digit_bytes = OPCODE_SCHEDULE_DISPLAY_ASCII + str(bumper).encode("utf-8")
        if led_bytes != last_led_bytes:
            roomba.write(led_bytes)
            last_led_bytes = led_bytes
        if digit_bytes != last_digit_bytes:
            roomba.write(digit_bytes)
            last_digit_bytes = digit_bytes
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
