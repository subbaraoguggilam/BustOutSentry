from collections import deque
from threading import Lock


class LiveResults:

    def __init__(self, max_results=100):
        self.results = deque(maxlen=max_results)
        self.lock = Lock()

    def add(self, result):
        with self.lock:
            self.results.appendleft(result)

    def get_all(self):
        with self.lock:
            return list(self.results)

    def get_latest(self):
        with self.lock:
            if not self.results:
                return None

            return self.results[0]


live_results = LiveResults()