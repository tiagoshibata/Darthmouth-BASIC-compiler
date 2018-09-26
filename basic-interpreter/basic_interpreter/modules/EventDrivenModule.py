from collections import deque


class EventDrivenModule:
    def __init__(self):
        self.queue = deque()

    def add_event(self, event):
        self.queue.append(event)
