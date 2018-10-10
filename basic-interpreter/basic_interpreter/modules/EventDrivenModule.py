from collections import deque


class EventDrivenModule:
    def __init__(self, add_external_event):
        self.add_external_event = add_external_event
        self.handlers = self.get_handlers()
        self.queue = deque()

    def get_handlers(self):
        raise NotImplementedError()

    def add_event(self, event):
        self.queue.append(event)

    def handle_event(self, event):
        handler = self.handlers.get(event[0])
        assert handler, 'No handler defined for {}'.format(event[0])
        handler(event[1:])

    def __iter__(self):
        return self

    def __next__(self):
        try:
            return self.queue.popleft()
        except IndexError:
            raise StopIteration()
