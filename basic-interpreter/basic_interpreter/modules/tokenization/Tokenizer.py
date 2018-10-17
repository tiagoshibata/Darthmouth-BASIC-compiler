from basic_interpreter.modules.EventDrivenModule import EventDrivenModule


class Tokenizer(EventDrivenModule):
    def get_handlers(self):
        self.character_queue = []
        return {
            'ascii_character': self.ascii_character_handler,
            'ascii_digit': self.ascii_digit_handler,
            'ascii_delimiter': self.ascii_delimiter_or_ctrl_handler,
            'ascii_ctrl': self.ascii_delimiter_or_ctrl_handler,
            'ascii_special': self.ascii_special_handler,
        }

    def ascii_character_handler(self, event):
        assert not self.character_queue or self.character_queue[0].isalpha(), 'character found in a number'
        self.character_queue.append(event[0])

    def ascii_digit_handler(self, event):
        self.character_queue.append(event[0])

    def ascii_delimiter_or_ctrl_handler(self, event):
        if self.character_queue:
            self.add_external_event(('identifier', ''.join(self.character_queue)))
            self.character_queue = []

    def ascii_special_handler(self, event):
        self.ascii_delimiter_or_ctrl_handler(event)
        self.add_external_event(('special', event[0]))

    # TODO numbers
    # TODO multi-char special (e.g. :=)
