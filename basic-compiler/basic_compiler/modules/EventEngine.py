from collections import deque


class EventEngine:
    def __init__(self, modules):
        self.modules = modules
        for module in modules:
            module.set_external_event_handler(self.add_event)
        self.queue = deque()

    def add_event(self, event):
        for module in self.modules:
            if event[0] in module.handlers:
                module.handle_event(event)

    def handle_next_dependent_event(self):
        for module in self.modules:
            event = next(module, None)
            if event:
                module.handle_event(event)
                return True
        return False

    def start(self, event):
        self.add_event(event)
        while self.handle_next_dependent_event():
            pass
