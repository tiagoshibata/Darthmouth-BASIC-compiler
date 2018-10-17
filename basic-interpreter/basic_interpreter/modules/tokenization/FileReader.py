from basic_interpreter.modules.EventDrivenModule import EventDrivenModule


class FileReader(EventDrivenModule):
    def get_handlers(self):
        return {
            'open': self.open_handler,
            'read': self.read_handler,
            'close': self.close_handler,
        }

    def open_handler(self, event):
        self.file = open(event[0])
        self.add_event(('read'))

    def read_handler(self, event):
        line = self.file.readline()
        if not line:
            self.add_event(('close'))
            return
        self.add_external_event(('ascii_line', line))
        self.add_event(('read'))

    def close_handler(self, event):
        self.file.close()
        self.file = None
        self.add_external_event(('eof'))
