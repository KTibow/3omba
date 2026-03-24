import struct
import threading
import time

from serial import Serial

from lib.interface import (
    OPCODE_DRIVE_DIRECT,
    OPCODE_LEDS,
    OPCODE_MOTORS,
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
    running = False
    bias_metric = 0
    motors_enabled = True
    buttons_last_pressed = False

    last_drive_bytes = b""
    last_motor_bytes = b""
    last_led_bytes = b""
    while True:
        sensor_data_fixed = sensor_data.get()

        left_light_bumper = (
            sensor_data_fixed[0] + sensor_data_fixed[1] + sensor_data_fixed[2]
        )
        right_light_bumper = (
            sensor_data_fixed[3] + sensor_data_fixed[4] + sensor_data_fixed[5]
        )
        left_bumper = sensor_data_fixed[6] & 0b00000001
        right_bumper = sensor_data_fixed[6] & 0b00000010
        dirt_detect = sensor_data_fixed[7]
        buttons_pressed = sensor_data_fixed[8]

        if buttons_last_pressed and not buttons_pressed:
            motors_enabled = buttons_last_pressed & 0b00000001
            running = not running
        buttons_last_pressed = buttons_pressed

        bias_metric = (
            bias_metric * 0.99 + (right_light_bumper / 500 + right_bumper) * 0.01
        )
        print(bias_metric, right_light_bumper, right_bumper)

        left_wheel = 0
        right_wheel = 0
        if running:
            left_wheel = -200 if bias_metric > 0.2 else 200
            right_wheel = 200
            right_wheel -= 5 * left_light_bumper
            left_wheel -= 5 * right_light_bumper
            if right_bumper:
                left_wheel -= 400
            if left_bumper:
                right_wheel -= 400
        # print(sensor_data_fixed, left_wheel, right_wheel)
        drive_bytes = (
            OPCODE_DRIVE_DIRECT
            + struct.pack(">h", right_wheel)
            + struct.pack(">h", left_wheel)
        )
        motor_bytes = OPCODE_MOTORS + bytes(
            [0b00000110 if running and motors_enabled else 0]
        )
        led_bytes = OPCODE_LEDS + bytes(
            [
                (0b0000001 if dirt_detect else 0) | (0b00000010 if not running else 0),
                0,
                255 if not running else 16,
            ]
        )
        if drive_bytes != last_drive_bytes:
            roomba.write(drive_bytes)
            last_drive_bytes = drive_bytes
        if motor_bytes != last_motor_bytes:
            roomba.write(motor_bytes)
            last_motor_bytes = motor_bytes
        if led_bytes != last_led_bytes:
            roomba.write(led_bytes)
            last_led_bytes = led_bytes
        time.sleep(0.015)


def main():
    PACKETS = (46, 47, 48, 49, 50, 51, 7, 15, 18)
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
