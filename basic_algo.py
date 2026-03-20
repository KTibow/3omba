import time

from serial import Serial

from interface import (
    OPCODE_SAFE,
    OPCODE_START,
    OPCODE_STOP,
    OPCODE_STREAM_SENSORS,
    read_stream,
)

roomba = Serial("/dev/ttyUSB0", 115200, timeout=0.1)
time.sleep(0.2)
roomba.write(OPCODE_START)
roomba.write(OPCODE_SAFE)
time.sleep(0.2)


def main():
    PACKETS = (46, 48, 49, 51)
    roomba.write(OPCODE_STREAM_SENSORS + bytes((len(PACKETS),)) + bytes(PACKETS))
    roomba.read_all()
    while True:
        readings = read_stream(roomba, PACKETS)
        print(readings)


try:
    main()
finally:
    roomba.write(OPCODE_STOP)
    roomba.close()
