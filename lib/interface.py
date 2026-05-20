"""
Utilities for the Roomba Open Interface.
"""

import struct
from typing import Sequence, cast

from serial import Serial

# Packets
UNSIGNED_1 = ">B"
SIGNED_1 = ">b"
UNSIGNED_2 = ">H"
SIGNED_2 = ">h"

# fmt: off
BUTTON_CLOCK    = 0b10000000
BUTTON_SCHEDULE = 0b01000000
BUTTON_DAY      = 0b00100000
BUTTON_HOUR     = 0b00010000
BUTTON_MINUTE   = 0b00001000
BUTTON_DOCK     = 0b00000100
BUTTON_SPOT     = 0b00000010
BUTTON_CLEAN    = 0b00000001

BWD_WHEEL_LEFT  = 0b00001000
BWD_WHEEL_RIGHT = 0b00000100
BWD_BUMP_LEFT   = 0b00000010
BWD_BUMP_RIGHT  = 0b00000001

MOTORS_SIDE_BRUSH  = 0b00000001
MOTORS_VACUUM      = 0b00000010
MOTORS_MAIN_BRUSH  = 0b00000100
MOTORS_SIDE_INVERT = 0b00001000
MOTORS_MAIN_INVERT = 0b00010000
# fmt: on

ID_BUMPS_AND_WHEEL_DROPS = 7
ID_DIRT_DETECT = 15
ID_INFRARED_CHARACTER = 17
ID_BUTTONS = 18
ID_CHARGING_STATE = 21
ID_VOLTAGE = 22
ID_CURRENT = 23
ID_TEMPERATURE = 24
ID_BATTERY_CHARGE = 25
ID_BATTERY_CAPACITY = 26
ID_CHARGING_SOURCES_AVAILABLE = 34
ID_OI_MODE = 35
ID_LEFT_ENCODER_COUNTS = 43
ID_RIGHT_ENCODER_COUNTS = 44
ID_LIGHT_BUMPER = 45
ID_LIGHT_BUMPER_LEFT_SIGNAL = 46
ID_LIGHT_BUMPER_FRONT_LEFT_SIGNAL = 47
ID_LIGHT_BUMPER_CENTER_LEFT_SIGNAL = 48
ID_LIGHT_BUMPER_CENTER_RIGHT_SIGNAL = 49
ID_LIGHT_BUMPER_FRONT_RIGHT_SIGNAL = 50
ID_LIGHT_BUMPER_RIGHT_SIGNAL = 51
ID_INFRARED_CHARACTER_LEFT = 52
ID_INFRARED_CHARACTER_RIGHT = 53
PACKETS = {
    ID_BUMPS_AND_WHEEL_DROPS: UNSIGNED_1,
    ID_DIRT_DETECT: UNSIGNED_1,
    ID_INFRARED_CHARACTER: UNSIGNED_1,
    ID_BUTTONS: UNSIGNED_1,
    ID_CHARGING_STATE: UNSIGNED_1,
    ID_VOLTAGE: UNSIGNED_2,
    ID_CURRENT: SIGNED_2,
    ID_TEMPERATURE: SIGNED_1,
    ID_BATTERY_CHARGE: UNSIGNED_2,
    ID_BATTERY_CAPACITY: UNSIGNED_2,
    ID_CHARGING_SOURCES_AVAILABLE: UNSIGNED_1,
    ID_OI_MODE: UNSIGNED_1,
    ID_LEFT_ENCODER_COUNTS: SIGNED_2,
    ID_RIGHT_ENCODER_COUNTS: SIGNED_2,
    ID_LIGHT_BUMPER: UNSIGNED_1,
    ID_LIGHT_BUMPER_LEFT_SIGNAL: UNSIGNED_2,
    ID_LIGHT_BUMPER_FRONT_LEFT_SIGNAL: UNSIGNED_2,
    ID_LIGHT_BUMPER_CENTER_LEFT_SIGNAL: UNSIGNED_2,
    ID_LIGHT_BUMPER_CENTER_RIGHT_SIGNAL: UNSIGNED_2,
    ID_LIGHT_BUMPER_FRONT_RIGHT_SIGNAL: UNSIGNED_2,
    ID_LIGHT_BUMPER_RIGHT_SIGNAL: UNSIGNED_2,
    ID_INFRARED_CHARACTER_LEFT: UNSIGNED_1,
    ID_INFRARED_CHARACTER_RIGHT: UNSIGNED_1,
}


def read_stream(roomba: Serial, packets: Sequence[int]):
    """
    Get the next reading for specific packets from a currently streaming iRobot Create 2.
    """
    length = 1 + 1 + sum(1 + struct.calcsize(PACKETS[pid]) for pid in packets) + 1
    data = roomba.read(length)
    if len(data) < length:
        raise ValueError(f"Need {length}b, got {len(data)}b")

    header = data[0]
    n_bytes = data[1]
    remaining_data = list(data[2:-1])
    checksum = data[-1]
    if header != 19:
        roomba.reset_input_buffer()
        raise ValueError(f"Need 19, got {header}")
    assert n_bytes == len(remaining_data)
    assert (header + n_bytes + sum(remaining_data) + checksum) & 0xFF == 0

    readings: list[int] = []
    for packet_id in packets:
        fmt = PACKETS[packet_id]
        size = struct.calcsize(fmt)

        returned_packet_id = remaining_data.pop(0)
        if returned_packet_id != packet_id:
            raise ValueError(f"Need {packet_id}, got {returned_packet_id}")
        if len(remaining_data) < size:
            raise ValueError(f"Need {size}b, got {len(remaining_data)}b")

        returned_data = [remaining_data.pop(0) for _ in range(size)]
        value = cast(int, struct.unpack(fmt, bytes(returned_data))[0])
        readings.append(value)
    return readings


OPCODE_START: bytes = (128).to_bytes(1, "big")
"""
Start the OI. Send it before any other commands.
If the robot's currently in another mode, sets it to Passive mode.

Format: [128]
Available: Always available.
Mode change: Sets mode to Passive, and the robot will beep.
"""
OPCODE_RESET: bytes = (7).to_bytes(1, "big")
"""
Reset the robot. Equivalent to removing and reinserting the battery.

Format: [7]
Available: Always available.
Mode change: Exits the OI, and the robot will make a tune when it's done.
"""
OPCODE_STOP: bytes = (173).to_bytes(1, "big")
"""
Stop the OI. Streams will stop, and commands won't work.

Format: [173]
Available: if the OI is connected.
Mode change: Exits the OI, and the robot will beep.
"""
OPCODE_BAUD: bytes = (129).to_bytes(1, "big")
"""
Set the baud rate in bits per second (bps).
The default baud rate is 115200 bps, but [it can be changed](https://cdn-shop.adafruit.com/datasheets/create_2_Open_Interface_Spec.pdf#page=4) to 19200 bps.
The baud rate is held unless the robot has to be restarted.
Wait 100ms after sending this command before sending more commands at the new baud rate.

Format: [129, [baud rate](https://cdn-shop.adafruit.com/datasheets/create_2_Open_Interface_Spec.pdf#page=8)]
Available: if the OI is connected.
Mode change: Doesn't change mode.
"""


OPCODE_SAFE: bytes = (131).to_bytes(1, "big")
"""
Put the robot in safe mode.
This allows you to control the robot, but it will exit if any problem is detected.
All LEDs will be turned off.

Format: [131]
Available: if the OI is connected.
Mode change: Changes mode to Safe.
"""
OPCODE_FULL: bytes = (132).to_bytes(1, "big")
"""
Put the robot in full mode.
This allows you to control the robot with safety features turned off.

Format: [132]
Available: if the OI is connected.
Mode change: Changes mode to Full.
"""


OPCODE_CLEAN: bytes = (135).to_bytes(1, "big")
"""
Start a normal cleaning cycle. Will pause current cycle if any.

Format: [135]
Available: if the OI is connected.
Mode change: Changes mode to Passive.
"""
OPCODE_SPOT: bytes = (134).to_bytes(1, "big")
"""
Start a spot cleaning cycle. Will pause current cycle if any.

Format: [134]
Available: if the OI is connected.
Mode change: Changes mode to Passive.
"""
OPCODE_DOCK: bytes = (143).to_bytes(1, "big")
"""
Tell the robot to go around until it sees the dock, then to drive onto it. Will pause current cycle if present.

Format: [143]
Available: if the OI is connected.
Mode change: Changes mode to Passive.
"""
OPCODE_POWER: bytes = (133).to_bytes(1, "big")
"""
Turn off the robot.

Format: [133]
Available: if the OI is connected.
Mode change: Exits the OI.
"""
OPCODE_SCHEDULE: bytes = (167).to_bytes(1, "big")
"""
Set the cleaning schedule.
If the robot is already in the schedule/clock UX, the command doesn't work.

Time format:
| Day | Code | Hour | Code | Minute | Code |
|-----|------|------|------|--------|------|
| Sun | 0    | 1AM  | 0    | 00     | 0    |
| Mon | 1    | 5AM  | 5    | 10     | 10   |
| Tue | 2    | 10AM | 10   | 20     | 20   |
| Wed | 3    | 12PM | 12   | 30     | 30   |
| Thu | 4    | 3PM  | 15   | 40     | 40   |
| Fri | 5    | 6PM  | 18   | 50     | 50   |
| Sat | 6    | 11PM | 23   | 00     | 60   |

Format: [167, [some kind of checksum](http://www.robotreviews.com/chat/viewtopic.php?f=1&t=12328), Sun hour, Sun minute, Mon hour, Mon minute, etc.]
Available: if the OI is connected.
Mode change: Doesn't change mode.
"""
OPCODE_CLOCK: bytes = (168).to_bytes(1, "big")
"""
Set the time.
If the robot is already in the schedule/clock UX, the command doesn't work.

Time format:
| Day | Code | Hour | Code | Minute | Code |
|-----|------|------|------|--------|------|
| Sun | 0    | 1AM  | 0    | 00     | 0    |
| Mon | 1    | 5AM  | 5    | 10     | 10   |
| Tue | 2    | 10AM | 10   | 20     | 20   |
| Wed | 3    | 12PM | 12   | 30     | 30   |
| Thu | 4    | 3PM  | 15   | 40     | 40   |
| Fri | 5    | 6PM  | 18   | 50     | 50   |
| Sat | 6    | 11PM | 23   | 00     | 60   |

Format: [168, day, hour, minute]
Available: if the OI is connected.
Mode change: Doesn't change mode.
"""


OPCODE_DRIVE: bytes = (137).to_bytes(1, "big")
"""
Control the robot's drive wheels (with speed/turn amount).
This is a weird/proprietary command, so [check the official docs](https://cdn-shop.adafruit.com/datasheets/create_2_Open_Interface_Spec.pdf#page=12).
Basically, if it's negative, you subtract the value from 65535 (positive is normal).

Format: [137, speed (2 bits, big endian, -500-500), radius (2 bits, big endian, -2000-2000)]
Available: in Safe/Full mode.
Mode change: Doesn't change mode.
"""
OPCODE_DRIVE_DIRECT: bytes = (145).to_bytes(1, "big")
"""
Control the robot's drive wheels (with mm/s for each wheel).
This is a weird/proprietary command, so [check the official docs](https://cdn-shop.adafruit.com/datasheets/create_2_Open_Interface_Spec.pdf#page=13).
Basically, if it's negative, you subtract the value from 65535 (positive is normal).

Format: [145, right wheel (2 bytes, big endian, -500-500), left wheel (2 bytes, big endian, -500-500)]
Available: in Safe/Full mode.
Mode change: Doesn't change mode.
"""
OPCODE_DRIVE_PWM: bytes = (146).to_bytes(1, "big")
"""
Control the robot's drive wheels (with how much power to send to each wheel).
This is a weird/proprietary command, so [check the official docs](https://cdn-shop.adafruit.com/datasheets/create_2_Open_Interface_Spec.pdf#page=13).
Basically, if it's negative, you subtract the value from 65535 (positive is normal).

Format: [146, left wheel (2 bits, big endian, -255-255), right wheel (2 bits, big endian, -255-255)]
Available: in Safe/Full mode.
Mode change: Doesn't change mode.
"""
OPCODE_MOTORS: bytes = (138).to_bytes(1, "big")
"""
Toggle the brushes and vacuum.
The byte sent is a [combination of multiple bits](https://cdn-shop.adafruit.com/datasheets/create_2_Open_Interface_Spec.pdf#page=14).

Format: [138, byte]
Available: in Safe/Full mode.
Mode change: Doesn't change mode.
"""
OPCODE_MOTORS_PWM: bytes = (144).to_bytes(1, "big")
"""
Set the power of the brushes and vacuum.
Basically, if it's negative, you subtract the value from 255 (positive is normal).

Format: [144, main brush (-127-127), side brush (-127-127), vacuum (0-127)]
Available: in Safe/Full mode.
Mode change: Doesn't change mode.
"""
OPCODE_LEDS: bytes = (139).to_bytes(1, "big")
"""
Set the LEDs.
The first data byte sent is a [combination of multiple bits](https://cdn-shop.adafruit.com/datasheets/create_2_Open_Interface_Spec.pdf#page=15).

Format: [139, byte, Clean led hue, Clean led brightness]
Available: in Safe/Full mode.
Mode change: Doesn't change mode.
"""
OPCODE_SCHEDULE_LEDS: bytes = (162).to_bytes(1, "big")
"""
Set the LEDs surrounding the display for the scheduling system.
The data bytes are a [combination of multiple bits](https://cdn-shop.adafruit.com/datasheets/create_2_Open_Interface_Spec.pdf#page=15).

Format: [162, byte, byte]
Available: in Safe/Full mode.
Mode change: Doesn't change mode.
"""
OPCODE_SCHEDULE_DISPLAY: bytes = (163).to_bytes(1, "big")
"""
Set the display for the scheduling system.
The data bytes are a [combination of multiple bits](https://cdn-shop.adafruit.com/datasheets/create_2_Open_Interface_Spec.pdf#page=16).

Format: [163, bytes for display from left to right x4]
Available: in Safe/Full mode.
Mode change: Doesn't change mode.
"""
OPCODE_EMULATE_BUTTONS: bytes = (165).to_bytes(1, "big")
"""
Push buttons on the robot for 1/6th of a second.
The data byte is a [combination of multiple bits](https://cdn-shop.adafruit.com/datasheets/create_2_Open_Interface_Spec.pdf#page=16).

Format: [165, byte]
Available: if the OI is connected.
Mode change: Doesn't change mode.
"""
OPCODE_SCHEDULE_DISPLAY_ASCII: bytes = (164).to_bytes(1, "big")
"""
Set the display for the scheduling system with ASCII characters.

Format: [164, characters for display from left to right x4]
Available: in Safe/Full mode.
Mode change: Doesn't change mode.
"""
OPCODE_STORE_SONG: bytes = (140).to_bytes(1, "big")
"""
Store a song (up to 4 at a time).
View the [official note list](https://cdn-shop.adafruit.com/datasheets/create_2_Open_Interface_Spec.pdf#page=18).

Among Us: `roomba.write(OPCODE_STORE_SONG + b"\x00\x0b\x40\x16\x43\x16\x46\x16\x49\x16\x46\x16\x43\x16\x40\x16\x00\x32\x40\x0c\x43\x0c\x40\x0c")`

Format: [140, song number (0-3), song note count (1-16), note 1 tone, note 1 length, etc.]
Available: if the OI is connected.
Mode change: Doesn't change mode.
"""
OPCODE_PLAY_SONG: bytes = (141).to_bytes(1, "big")
"""
Play a song.

Format: [141, song number (0-3)]
Available: if the OI is connected.
Mode change: Doesn't change mode.
"""


OPCODE_SEND_SENSOR: bytes = (142).to_bytes(1, "big")
"""
Request a sensor packet (check [the sensor packet docs](https://cdn-shop.adafruit.com/datasheets/create_2_Open_Interface_Spec.pdf#page=22)).

Format: [142, sensor packet ID]
Available: if the OI is connected.
Mode change: Doesn't change mode.
"""
OPCODE_SEND_SENSORS: bytes = (149).to_bytes(1, "big")
"""
Request multiple sensor packets (check [the sensor packet docs](https://cdn-shop.adafruit.com/datasheets/create_2_Open_Interface_Spec.pdf#page=22)).

Format: [149, sensor packet count, sensor packet ID 1, sensor packet ID 2, etc.]
Available: if the OI is connected.
Mode change: Doesn't change mode.
"""
OPCODE_STREAM_SENSORS: bytes = (148).to_bytes(1, "big")
"""
Request sensor packets every 15ms (check [the sensor packet docs](https://cdn-shop.adafruit.com/datasheets/create_2_Open_Interface_Spec.pdf#page=22)).
Check the [format of the returned data](https://cdn-shop.adafruit.com/datasheets/create_2_Open_Interface_Spec.pdf#page=21).

Format: [148, sensor packet count, sensor packet ID 1, sensor packet ID 2, etc.]
Available: if the OI is connected.
Mode change: Doesn't change mode.
"""
OPCODE_CHANGE_STREAM_STATUS: bytes = (150).to_bytes(1, "big")
"""
Toggle the stream of sensor packets.

Format: [150, operation (0-off, 1-on)]
Available: if the OI is connected.
Mode change: Doesn't change mode.
"""
