from unittest.mock import call, MagicMock

from basic_compiler.modules.EventDrivenModule import EventDrivenModule


class EmptyModule(EventDrivenModule):
    def __init__(self):
        super().__init__(None)

    def get_handlers(self):
        return {}


class SimpleModule(EventDrivenModule):
    def get_handlers(self):
        return {
            'test_handler': self.test_handler,
        }

    def test_handler(self, event):
        self.add_external_event(event[0])


def test_event_queue_is_fifo():
    module = EmptyModule()
    events = [('event0',), ('event1',)]
    for event in events:
        module.add_event(event)
    for event, expected_event in zip(module, events):
        assert event == expected_event


def test_adds_external_event():
    add_external_event = MagicMock()
    module = SimpleModule(add_external_event)
    module.add_event(('test_handler', 'first'))
    module.add_event(('test_handler', 'second'))
    for event in module:
        module.handle_event(event)
    add_external_event.assert_has_calls([
        call('first'),
        call('second'),
    ])
