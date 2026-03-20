import time

from serial import Serial

from interface import (
    OPCODE_PLAY_SONG,
    OPCODE_SAFE,
    OPCODE_START,
    OPCODE_STOP,
    OPCODE_STORE_SONG,
)

roomba = Serial("/dev/ttyUSB0", 115200, timeout=0.1)
time.sleep(0.2)
roomba.write(OPCODE_START)
roomba.write(OPCODE_SAFE)
time.sleep(0.2)


def main():
    notes = []
    notes_payload = []
    for n in range(31, 127, 10):
        notes.append(n)
        notes_payload.append(n)
        notes_payload.append(32)
    roomba.write(OPCODE_STORE_SONG + bytes([0, len(notes)]) + bytes(notes_payload))
    roomba.write(OPCODE_PLAY_SONG + bytes([0]))
    time.sleep(1.5)


try:
    main()
finally:
    roomba.write(OPCODE_STOP)
    roomba.close()
