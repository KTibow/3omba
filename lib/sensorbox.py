import threading
from typing import Generic, TypeVar

T = TypeVar("T")


class SensorBox(Generic[T]):
    """
    Holds a value so it can be safely used across threads.
    """

    def __init__(self):
        self._value: T = None  # type: ignore
        self._event = threading.Event()

    def put(self, value: T):
        self._value = value
        self._event.set()

    def get(self):
        self._event.wait()
        self._event.clear()
        return self._value
