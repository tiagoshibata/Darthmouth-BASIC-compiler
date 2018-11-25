from basic_compiler.fsm import Fsm, State, Transition
from basic_compiler.modules.EventDrivenModule import EventDrivenModule

TRANSITION_TABLE = {
    'start': State(None, [
        Transition('ascii_character', 'variable'),
        Transition('ascii_digit', 'number'),
        Transition('ascii_delimiter', 'delimiter'),
        Transition('ascii_ctrl', 'end_of_line'),
        Transition(('ascii_special', '.'), 'number'),
        Transition(('ascii_special', '"'), 'string'),
        Transition(('ascii_special', '>'), 'greater_than'),
        Transition(('ascii_special', '<'), 'smaller_than'),
        Transition('ascii_special', 'special'),
        Transition('eof', 'eof'),
    ]),

    'variable': State('variable', [
        Transition('ascii_character', 'identifier'),
        Transition('ascii_digit', 'variable_with_number'),
    ]),
    'variable_with_number': State('variable', [
        Transition('ascii_character', 'invalid'),
        Transition('ascii_digit', 'invalid'),
    ]),
    'identifier': State('identifier', [
        Transition('ascii_character', 'identifier'),
        Transition('ascii_digit', 'invalid'),
    ]),
    'invalid': State(),

    'number': State('number', [
        Transition(('ascii_character', 'E'), 'scientific_notation_number'),
        Transition('ascii_character', 'number'),
        Transition('ascii_digit', 'number'),
        Transition(('ascii_special', '.'), 'number'),
    ]),
    'scientific_notation_number': State(None, [
        Transition(('ascii_special', '+'), 'number'),
        Transition(('ascii_special', '-'), 'number'),
        Transition('ascii_digit', 'number'),
    ]),

    'delimiter': State('delimiter'),
    'end_of_line': State('end_of_line'),

    # String literals (in PRINT statements)
    'string': State(None, [
        Transition('ascii_character', 'string'),
        Transition('ascii_digit', 'string'),
        Transition('ascii_delimiter', 'string'),
        Transition('ascii_ctrl', 'invalid'),
        Transition(('ascii_special', '"'), 'end_of_string'),
        Transition('ascii_special', 'string'),
    ]),
    'end_of_string': State('string', [
        Transition(('ascii_special', '"'), 'string'),  # escaped double quote
    ]),

    # Multicharacter specials
    'greater_than': State('special', [
        Transition(('ascii_special', '='), 'special'),
    ]),
    'smaller_than': State('special', [
        Transition(('ascii_special', '='), 'special'),
        Transition(('ascii_special', '>'), 'special'),
    ]),
    'special': State('special'),

    'eof': State(None),
}


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
