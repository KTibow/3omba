import threading


class SensorBox:
    def __init__(self):
        self._value = None
        self._event = threading.Event()

    def put(self, value):
        self._value = value
        self._event.set()  # notify reader

    def get(self):
        self._event.wait()  # wait for notification
        self._event.clear()
        return self._value
