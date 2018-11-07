from basic_compiler.fsm import Fsm, State
from basic_compiler.modules.EventDrivenModule import EventDrivenModule

TRANSITION_TABLE = {
    'start': State(False, [
        ('ascii_character', 'identifier'),
        ('ascii_digit', 'number'),
        ('ascii_delimiter', 'start'),
        ('ascii_ctrl', 'end_of_line'),
        (('ascii_special', '>'), 'greater_than'),
        (('ascii_special', '<'), 'smaller_than'),
        ('ascii_special', 'special'),
    ]),

    'identifier': State(True, [
        ('ascii_character', 'identifier'),
        ('ascii_digit', 'identifier'),
    ]),

    'number': State(True, [
        (('ascii_character', 'E'), 'scientific_notation_number'),
        ('ascii_character', 'number'),
        ('ascii_digit', 'number'),
    ]),
    'scientific_notation_number': State(True, [
        (('ascii_character', '+'), 'number'),
        (('ascii_character', '-'), 'number'),
        ('ascii_digit', 'number'),
    ]),

    'end_of_line': State(True, []),

    # Multicharacter specials
    'greater_than': State(True, [
        (('ascii_special', '='), 'greater_or_equal_than'),
    ]),
    'greater_or_equal_than': State(True, []),
    'smaller_than': State(True, [
        (('ascii_special', '='), 'smaller_or_equal_than'),
        (('ascii_special', '>'), 'different'),
    ]),
    'smaller_or_equal_than': State(True, []),
    'different': State(True, []),
    'special': State(True, []),
}

# 'number': (True, [
#     (('ascii_character', 'E'), 'scientific_notation_number'),
#     ('ascii_character', None),
#     ('ascii_digit', 'number'),
# ]),
# 'scientific_notation_number': (False, [
#     (('ascii_character', '+'), 'scientific_notation_number_exponent_after_sign'),
#     (('ascii_character', '-'), 'scientific_notation_number_exponent_after_sign'),
#     ('ascii_digit', 'scientific_notation_number_exponent_value'),
# ]),
# 'scientific_notation_number_exponent_after_sign': (False, [
#     ('ascii_digit', 'scientific_notation_number_exponent_value'),
# ]),
# 'scientific_notation_number_exponent_value': (True, [
#     ('ascii_digit', 'scientific_notation_number_exponent_value'),
#     ('ascii_character', None),
# ]),


class Tokenizer(EventDrivenModule):
    def transition_on_event(event_name, event):
        next_token = self.fsm.transition(event_name, event[0]))
        if next_token:
            self.add_external_event(next_token)

    def get_handlers(self):
        self.fsm = Fsm(TRANSITION_TABLE)
        return {
            'ascii_character': lambda event: transition_on_event('ascii_character', event),
            'ascii_digit': lambda event: transition_on_event('ascii_digit', event),
            'ascii_delimiter': lambda event: transition_on_event('ascii_delimiter', event),
            'ascii_ctrl': lambda event: transition_on_event('ascii_ctrl', event),
            'ascii_special': lambda event: transition_on_event('ascii_special', event),
        }
