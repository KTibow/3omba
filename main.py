"""
The 3omba alarm clock program.
"""

import struct
import threading
import time
from datetime import datetime

from serial import Serial

from lib.interface import (
    BUTTON_HOUR,
    BUTTON_MINUTE,
    BWD_BUMP_LEFT,
    BWD_BUMP_RIGHT,
    ID_BUMPS_AND_WHEEL_DROPS,
    ID_BUTTONS,
    ID_LIGHT_BUMPER_CENTER_LEFT_SIGNAL,
    ID_LIGHT_BUMPER_CENTER_RIGHT_SIGNAL,
    ID_LIGHT_BUMPER_FRONT_LEFT_SIGNAL,
    ID_LIGHT_BUMPER_FRONT_RIGHT_SIGNAL,
    ID_LIGHT_BUMPER_LEFT_SIGNAL,
    ID_LIGHT_BUMPER_RIGHT_SIGNAL,
    MOTORS_MAIN_BRUSH,
    MOTORS_VACUUM,
    OPCODE_DRIVE_DIRECT,
    OPCODE_MOTORS,
    OPCODE_PLAY_SONG,
    OPCODE_SAFE,
    OPCODE_SCHEDULE_DISPLAY_ASCII,
    OPCODE_SCHEDULE_LEDS,
    OPCODE_START,
    OPCODE_STOP,
    OPCODE_STORE_SONG,
    OPCODE_STREAM_SENSORS,
    SIGNED_2,
    read_stream,
)
from lib.sensorbox import SensorBox

roomba = Serial("/dev/ttyUSB0", 115200, timeout=0.1)
sensor_data: SensorBox[list[int]] = SensorBox()

# Alarm target
_target_hour = datetime.now().hour
_target_minute = (datetime.now().minute - 1) % 60
_last_target_hour = -1
_last_target_minute = -1

# Button state
_last_buttons = 0
_hour_pressed_for_total = 0
_hour_pressed_for_since_last = 0
_minute_pressed_for_total = 0
_minute_pressed_for_since_last = 0

# Alarm trigger state
_last_hour = -1
_last_minute = -1


def display_target_time_on_display():
    global _last_target_hour, _last_target_minute

    if _target_hour == _last_target_hour and _target_minute == _last_target_minute:
        return

    _last_target_hour = _target_hour
    _last_target_minute = _target_minute

    chars = f"{_target_hour:02d}{_target_minute:02d}".encode("ascii")
    roomba.write(OPCODE_SCHEDULE_DISPLAY_ASCII + chars)


def update_target_time(buttons: int):
    global \
        _last_buttons, \
        _target_hour, \
        _target_minute, \
        _hour_pressed_for_total, \
        _hour_pressed_for_since_last, \
        _minute_pressed_for_total, \
        _minute_pressed_for_since_last

    should_increment_hour = False
    should_increment_minute = False

    # Increment on 0→1 transition
    pressed = (buttons ^ _last_buttons) & buttons
    if pressed & BUTTON_HOUR:
        should_increment_hour = True
    if pressed & BUTTON_MINUTE:
        should_increment_minute = True

    if buttons & BUTTON_HOUR:
        _hour_pressed_for_total += 1
        _hour_pressed_for_since_last += 1
    else:
        _hour_pressed_for_total = 0
        _hour_pressed_for_since_last = 0
    # Increment if held down - start after 0.3s, increment every 0.15s
    if _hour_pressed_for_total >= 20 and _hour_pressed_for_since_last >= 10:
        should_increment_hour = True
        _hour_pressed_for_since_last = 0

    if buttons & BUTTON_MINUTE:
        _minute_pressed_for_total += 1
        _minute_pressed_for_since_last += 1
    else:
        _minute_pressed_for_total = 0
        _minute_pressed_for_since_last = 0
    # Same as previous incrementing logic
    if _minute_pressed_for_total >= 20 and _minute_pressed_for_since_last >= 10:
        should_increment_minute = True
        _minute_pressed_for_since_last = 0

    if should_increment_hour:
        _target_hour = (_target_hour + 1) % 24
    if should_increment_minute:
        _target_minute = (_target_minute + 1) % 60

    if should_increment_hour or should_increment_minute:
        print("now targeting", _target_hour, _target_minute)

    _last_buttons = buttons


def start_wakeup_at_target_time():
    global _last_hour, _last_minute

    now = datetime.now()
    if _last_hour != now.hour or _last_minute != now.minute:
        _last_hour = now.hour
        _last_minute = now.minute

        if _last_hour == _target_hour and _last_minute == _target_minute:
            threading.Thread(target=wakeup_thread, daemon=True).start()


def wakeup_thread():
    """
    This is the active loop. See comments below.
    """

    # Generate a wakeup song made of incrementing tones
    notes = []
    notes_payload = []
    for n in range(31, 107, 10):  # maps to 49 Hz to 3951 Hz
        notes.append(n)
        notes_payload.append(n)
        notes_payload.append(32)

    # Play wakeup song
    SONG_NUMBER = 0
    roomba.write(
        OPCODE_STORE_SONG + bytes([SONG_NUMBER, len(notes)]) + bytes(notes_payload)
    )
    roomba.write(OPCODE_PLAY_SONG + bytes([SONG_NUMBER]))
    time.sleep(len(notes) * 32 / 64)

    # Pulse the vacuum and brush on and off
    ACTIVATE_MOTORS = MOTORS_VACUUM | MOTORS_MAIN_BRUSH
    roomba.write(OPCODE_MOTORS + bytes([ACTIVATE_MOTORS]))
    time.sleep(0.2)
    roomba.write(OPCODE_MOTORS + bytes([0]))
    time.sleep(0.2)
    roomba.write(OPCODE_MOTORS + bytes([ACTIVATE_MOTORS]))
    time.sleep(0.2)
    roomba.write(OPCODE_MOTORS + bytes([0]))
    time.sleep(0.4)
    # Turn on the vacuum and brushes
    roomba.write(OPCODE_MOTORS + bytes([ACTIVATE_MOTORS]))

    # Evasion mode
    while True:
        readings = sensor_data.get()

        buttons = readings[0]
        if buttons:  # is *any* button pressed? then stop
            roomba.write(OPCODE_MOTORS + bytes([0]))
            roomba.write(OPCODE_DRIVE_DIRECT + bytes([0, 0, 0, 0]))
            break

        left_light_bumper = readings[2] + readings[3] + readings[4]
        right_light_bumper = readings[5] + readings[6] + readings[7]
        left_bumper = readings[1] & BWD_BUMP_LEFT
        right_bumper = readings[1] & BWD_BUMP_RIGHT

        # If no obstacles detected, go at max speed (equivalent to 1.1 mph)
        left_wheel = 500
        right_wheel = 450
        # If walls detected, slow down and turn away for better evasion (and cleaning)
        left_wheel -= 5 * right_light_bumper
        right_wheel -= 5 * left_light_bumper
        if right_bumper:
            left_wheel -= 500
        if left_bumper:
            right_wheel -= 500
        roomba.write(
            OPCODE_DRIVE_DIRECT
            + struct.pack(SIGNED_2, right_wheel)
            + struct.pack(SIGNED_2, left_wheel)
        )
        time.sleep(0.015)


def main():
    """
    This is the passive loop. See comments below.
    """
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
    roomba.write(OPCODE_STREAM_SENSORS + bytes([len(PACKETS)]) + bytes(PACKETS))
    roomba.read_all()  # flush buffers

    # Infinitely loop simple, synchronous operations
    while True:
        try:
            readings = read_stream(roomba, PACKETS)
            sensor_data.put(readings)
            update_target_time(readings[0])
            start_wakeup_at_target_time()
            display_target_time_on_display()
        except Exception as e:
            print(e)


# Setup
time.sleep(0.2)
roomba.write(OPCODE_START)
roomba.write(OPCODE_SAFE)
time.sleep(0.2)
roomba.write(OPCODE_SCHEDULE_LEDS + b"\x00\x01")
display_target_time_on_display()

try:
    main()
finally:
    # Teardown
    roomba.write(OPCODE_STOP)
    roomba.close()
