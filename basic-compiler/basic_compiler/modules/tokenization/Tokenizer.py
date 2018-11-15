from basic_compiler.fsm import Fsm, State
from basic_compiler.modules.EventDrivenModule import EventDrivenModule

TRANSITION_TABLE = {
    'start': State(None, [
        ('ascii_character', 'variable'),
        ('ascii_digit', 'number'),
        ('ascii_delimiter', 'delimiter'),
        ('ascii_ctrl', 'end_of_line'),
        (('ascii_special', '>'), 'greater_than'),
        (('ascii_special', '<'), 'smaller_than'),
        ('ascii_special', 'special'),
    ]),

    'variable': State('variable', [
        ('ascii_character', 'identifier'),
        ('ascii_digit', 'variable_with_number'),
    ]),
    'variable_with_number': State('variable', [
        ('ascii_character', 'invalid'),
        ('ascii_digit', 'invalid'),
    ]),
    'identifier': State('identifier', [
        ('ascii_character', 'identifier'),
        ('ascii_digit', 'invalid'),
    ]),
    'invalid': State(None, []),

    'number': State('number', [
        (('ascii_character', 'E'), 'scientific_notation_number'),
        ('ascii_character', 'number'),
        ('ascii_digit', 'number'),
        (('ascii_special', '.'), 'number'),
    ]),
    'scientific_notation_number': State(None, [
        (('ascii_special', '+'), 'number'),
        (('ascii_special', '-'), 'number'),
        ('ascii_digit', 'number'),
    ]),

    'delimiter': State('delimiter', []),
    'end_of_line': State('end_of_line', []),

    # Multicharacter specials
    'greater_than': State('special', [
        (('ascii_special', '='), 'special'),
    ]),
    'smaller_than': State('special', [
        (('ascii_special', '='), 'special'),
        (('ascii_special', '>'), 'special'),
    ]),
    'special': State('special', []),
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
    def transition_on_event(self, event_name):
        def transition(event):
            next_token = self.fsm.transition((event_name, event[0]))
            if next_token and next_token[0] != 'delimiter':
                self.add_external_event(next_token)
        return transition

    def get_handlers(self):
        self.fsm = Fsm(TRANSITION_TABLE)
        return {
            x: self.transition_on_event(x)
            for x in ('ascii_character', 'ascii_digit', 'ascii_delimiter', 'ascii_ctrl', 'ascii_special', 'eof')
        }
