import threading
import time
from datetime import datetime

from serial import Serial

from lib.interface import (
    BUTTON_HOUR,
    BUTTON_MINUTE,
    ID_BUMPS_AND_WHEEL_DROPS,
    ID_BUTTONS,
    ID_LIGHT_BUMPER_CENTER_LEFT_SIGNAL,
    ID_LIGHT_BUMPER_CENTER_RIGHT_SIGNAL,
    ID_LIGHT_BUMPER_FRONT_LEFT_SIGNAL,
    ID_LIGHT_BUMPER_FRONT_RIGHT_SIGNAL,
    ID_LIGHT_BUMPER_LEFT_SIGNAL,
    ID_LIGHT_BUMPER_RIGHT_SIGNAL,
    OPCODE_PLAY_SONG,
    OPCODE_SAFE,
    OPCODE_SCHEDULE_DISPLAY_ASCII,
    OPCODE_SCHEDULE_LEDS,
    OPCODE_START,
    OPCODE_STOP,
    OPCODE_STORE_SONG,
    OPCODE_STREAM_SENSORS,
    read_stream,
)
from lib.sensorbox import SensorBox

roomba = Serial("/dev/ttyUSB0", 115200, timeout=0.1)
sensor_data: SensorBox[list[int]] = SensorBox()

# Global state
_target_hour = 0
_target_minute = 0
_last_hour = -1
_last_minute = -1
_last_buttons = 0
_last_target_hour = -1
_last_target_minute = -1


def update_display():
    """
    Sync the target hour and minute to the Roomba display.
    """
    global _last_target_hour, _last_target_minute

    if _target_hour == _last_target_hour and _target_minute == _last_target_minute:
        return

    _last_target_hour = _target_hour
    _last_target_minute = _target_minute

    chars = f"{_target_hour:02d}{_target_minute:02d}".encode("ascii")
    roomba.write(OPCODE_SCHEDULE_DISPLAY_ASCII + chars)


def handle_buttons(readings: list[int]):
    """
    When the hour/minute buttons are pressed, increment the target hour/minute.
    """
    global _last_buttons, _target_hour, _target_minute

    buttons = readings[0]
    pressed = (buttons ^ _last_buttons) & buttons  # 0→1 transition only

    if pressed & BUTTON_HOUR:
        _target_hour = (_target_hour + 1) % 24

    if pressed & BUTTON_MINUTE:
        _target_minute = (_target_minute + 1) % 60

    _last_buttons = buttons


def watch_time():
    """
    Start the wakeup thread when the target time is hit.
    """
    global _last_hour, _last_minute

    now = datetime.now()
    if _last_hour != now.hour or _last_minute != now.minute:
        _last_hour = now.hour
        _last_minute = now.minute
        print(_last_hour, _last_minute, _target_hour, _target_minute)

        if _last_hour == _target_hour and _last_minute == _target_minute:
            threading.Thread(target=wakeup_thread, daemon=True).start()


def wakeup_thread():
    print("HI")
    # todo: play wakeup song
    # todo: pulse motors
    # todo: drive around
    notes = []
    notes_payload = []
    for n in range(31, 127, 10):
        notes.append(n)
        notes_payload.append(n)
        notes_payload.append(32)
    roomba.write(OPCODE_STORE_SONG + bytes([0, len(notes)]) + bytes(notes_payload))
    roomba.write(OPCODE_PLAY_SONG + bytes([0]))
    while True:
        readings = sensor_data.get()
        print("HI", readings)
        # todo: check for stop conditions
        time.sleep(0.015)


def main():
    PACKETS = (
        ID_BUTTONS,
        ID_BUMPS_AND_WHEEL_DROPS,
        ID_LIGHT_BUMPER_LEFT_SIGNAL,
        ID_LIGHT_BUMPER_FRONT_LEFT_SIGNAL,
        ID_LIGHT_BUMPER_CENTER_LEFT_SIGNAL,
        ID_LIGHT_BUMPER_CENTER_RIGHT_SIGNAL,
        ID_LIGHT_BUMPER_FRONT_RIGHT_SIGNAL,
        ID_LIGHT_BUMPER_RIGHT_SIGNAL,
    )
    roomba.write(
        OPCODE_STREAM_SENSORS + len(PACKETS).to_bytes(1, "big") + bytes(PACKETS)
    )
    roomba.read_all()  # flush buffers

    while True:
        try:
            readings = read_stream(roomba, PACKETS)
            sensor_data.put(readings)
            handle_buttons(readings)
            watch_time()
            update_display()
        except Exception as e:
            print(e)


# Setup
time.sleep(0.2)
roomba.write(OPCODE_START)
roomba.write(OPCODE_SAFE)
time.sleep(0.2)
roomba.write(OPCODE_SCHEDULE_LEDS + b"\x00\x01")
update_display()

try:
    main()
finally:
    # Teardown
    roomba.write(OPCODE_STOP)
    roomba.close()
