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
    roomba.write(OPCODE_STORE_SONG + bytes([0, 3]) + bytes([31, 32, 41, 32, 51, 32]))
    roomba.write(OPCODE_PLAY_SONG + bytes([0]))


try:
    main()
finally:
    roomba.write(OPCODE_STOP)
    roomba.close()
