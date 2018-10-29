from basic_interpreter.modules.EventDrivenModule import EventDrivenModule

COMPOSED_SPECIAL = {'>=', '<='}


class Tokenizer(EventDrivenModule):
    def get_handlers(self):
        self.character_queue = []
        self.special = ''
        return {
            'ascii_character': self.ascii_character_handler,
            'ascii_digit': self.ascii_digit_handler,
            'ascii_delimiter': self.ascii_delimiter_handler,
            'ascii_ctrl': self.ascii_ctrl_handler,
            'ascii_special': self.ascii_special_handler,
        }

    def ascii_character_handler(self, event):
        self.end_of_special()
        assert not self.character_queue or self.character_queue[0].isalpha(), 'character found in a number'
        self.character_queue.append(event[0])

    def ascii_digit_handler(self, event):
        if self.special in {'+', '-'}:
            self.character_queue.append(self.special)
            self.special = ''
        else:
            self.end_of_special()
        self.character_queue.append(event[0])

    def end_of_identifier(self):
        if self.character_queue:
            if self.character_queue[0].isalpha():
                self.add_external_event(('token_identifier', ''.join(self.character_queue)))
            else:
                self.add_external_event(('token_number', int(''.join(self.character_queue))))
            self.character_queue = []

    def end_of_special(self, event=''):
        if self.special + event in COMPOSED_SPECIAL:
            self.add_external_event(('token_special', self.special + event))
            self.special = ''
        else:
            if self.special:
                self.add_external_event(('token_special', self.special))
            self.special = event

    def ascii_delimiter_handler(self, event):
        self.end_of_identifier()
        self.end_of_special()

    def ascii_ctrl_handler(self, event):
        self.end_of_identifier()
        self.end_of_special()
        self.add_external_event(('token_ctrl', event[0]))

    def ascii_special_handler(self, event):
        self.end_of_identifier()
        if self.special:
            self.end_of_special(event[0])
        else:
            self.special = event[0]
