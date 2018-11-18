from basic_compiler.modules.EventDrivenModule import EventDrivenModule


class FileReader(EventDrivenModule):
    def get_handlers(self):
        return {
            'open': self.open_handler,
            'read': self.read_handler,
            'close': self.close_handler,
        }

    def open_handler(self, event):
        try:
            self.file = open(event[0])
        except FileNotFoundError as e:
            import sys
            print(e, file=sys.stderr)
            raise SystemExit(1)
        self.add_event(('read',))

    def read_handler(self, event):
        line = self.file.readline()
        if not line:
            self.add_event(('close',))
            return
        self.add_external_event(('ascii_line', line))
        self.add_event(('read',))

    def close_handler(self, event):
        self.file.close()
        self.file = None
        self.add_external_event(('eof', None))
