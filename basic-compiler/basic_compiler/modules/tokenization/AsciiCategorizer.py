from basic_compiler.modules.EventDrivenModule import EventDrivenModule


class AsciiCategorizer(EventDrivenModule):
    def get_handlers(self):
        return {
            'ascii_line': self.ascii_line_handler,
        }

    def ascii_line_handler(self, event):
        self.line = event[0]
        for self.position, c in enumerate(self.line):
            if c.isalpha():
                self.add_external_event(('ascii_character', c))
            elif c.isnumeric():
                self.add_external_event(('ascii_digit', c))
            elif c == ' ':
                self.add_external_event(('ascii_delimiter', c))
            elif c == '\n':
                self.add_external_event(('ascii_ctrl', c))
            else:
                self.add_external_event(('ascii_special', c))

    def report(self):
        return '{}{}'.format(self.line, '{}^'.format(' ' * (18 + self.position)))
