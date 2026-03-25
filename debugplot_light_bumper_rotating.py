import struct
import time

import matplotlib.pyplot as plt
from serial import Serial

from lib.interface import (
    OPCODE_DRIVE_DIRECT,
    OPCODE_SAFE,
    OPCODE_START,
    OPCODE_STOP,
    OPCODE_STREAM_SENSORS,
    read_stream,
)

# 1. Setup Serial
roomba = Serial("/dev/ttyUSB0", 115200, timeout=0.1)
time.sleep(0.2)
roomba.write(OPCODE_START)
roomba.write(OPCODE_SAFE)
time.sleep(0.2)

# 2. Data containers
PACKETS = (46, 47, 48, 49, 50, 51)
labels = ["Left", "Front Left", "Center Left", "Center Right", "Front Right", "Right"]

# Initialize a dictionary of lists for the 6 sensors
acc_data = {label: [] for label in labels}
acc_times = []

try:
    # 3. Start Streaming and Initiate Movement
    roomba.write(OPCODE_STREAM_SENSORS + bytes((len(PACKETS),)) + bytes(PACKETS))
    roomba.read_all()  # Clear buffer

    # Pack rotation command: Right wheel 100, Left wheel -100
    roomba.write(OPCODE_DRIVE_DIRECT + struct.pack(">h", -100) + struct.pack(">h", 100))

    start_time = time.time()
    duration = 7.38

    print(f"Recording for {duration} seconds...")

    # 4. Main Collection Loop (Single Threaded)
    while True:
        elapsed = time.time() - start_time
        if elapsed > duration:
            break

        try:
            # read_stream should return a list/tuple of 6 values
            readings = read_stream(roomba, PACKETS)

            if readings:
                acc_times.append(elapsed)
                for i, label in enumerate(labels):
                    acc_data[label].append(readings[i])
        except Exception as e:
            print(f"Read error: {e}")

        # Small sleep to prevent CPU pegging, but keep high enough for sensor freq
        time.sleep(0.015)

    # 5. Stop Roomba immediately after loop
    roomba.write(OPCODE_DRIVE_DIRECT + struct.pack(">h", 0) + struct.pack(">h", 0))
    print("Recording finished. Closing Roomba connection and plotting...")

finally:
    # Always try to stop and close even if the loop crashes
    roomba.write(OPCODE_STOP)
    roomba.close()

# 6. Plotting (Boilerplate for 6 datasets)
plt.figure(figsize=(12, 6))

for label, values in acc_data.items():
    # We use acc_times[:len(values)] to ensure X and Y match exactly
    plt.plot(acc_times[: len(values)], values, label=label, linewidth=1.5)

plt.xlabel("Time (seconds)", fontsize=12)
plt.ylabel("Light Signal Intensity", fontsize=12)

# Move legend outside to the right so it doesn't cover the data
plt.legend(loc="upper left", bbox_to_anchor=(1, 1), title="Sensors")

plt.grid(True, linestyle="--", alpha=0.7)
plt.tight_layout()

# Save and Show
plt.savefig("debugplot_lb_rotating.png", dpi=300)
plt.show()
