from basic_compiler.fsm import Fsm, State, Transition
from basic_compiler.modules.EventDrivenModule import EventDrivenModule


TRANSITION_TABLE = {
    'start': State(None, [
        Transition('number', 'statement', generate_label),
        Transition('eof', 'eof', eof),
    ]),

    'statement': State(None, [
        Transition(('identifier', 'LET'), 'let'),
        Transition(('identifier', 'READ'), 'read'),
        Transition(('identifier', 'DATA'), 'data'),
        Transition(('identifier', 'PRINT'), 'print'),
        Transition(('identifier', 'GO'), 'go'),
        Transition(('identifier', 'GOTO'), 'goto'),
        Transition(('identifier', 'IF'), 'if'),
        Transition(('identifier', 'FOR'), 'for'),
        Transition(('identifier', 'NEXT'), 'next'),
        Transition(('identifier', 'DIM'), 'dim'),
        Transition(('identifier', 'DEF'), 'def'),
        Transition(('identifier', 'GOSUB'), 'gosub'),
        Transition(('identifier', 'RETURN'), 'return'),
        Transition(('identifier', 'REMARK'), 'remark'),
        Transition(('identifier', 'END'), 'end', end_statement),
    ]),

    'let': State(None, []),  # TODO
    'read': State(None, [

    ]),
    'data': State(None, [

    ]),
    'print': State(None, [

    ]),
    'go': State(None, [
        Transition(('identifier', 'TO'), 'goto'),
    ]),
    'goto': State(None, [
        Transition('number', 'end', goto),  # TODO validate number (must be an integer)
    ]),
    'if': State(None, []),  # TODO
    'for': State(None, []),  # TODO
    'next': State(None, []),  # TODO
    'dim': State(None, []),  # TODO
    'def': State(None, []),  # TODO
    'gosub': State(None, [
        Transition('number', 'end', gosub),
    ]),  # TODO
    'return': State(None, []),  # TODO
    # ...
    'end': State(None, [
        Transition('end_of_line', 'start'),
    ]),
    'eof': State('eof')
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


class SyntaxRecognizer(EventDrivenModule):
    def transition_on_event(self, event_name):
        return lambda event: self.fsm.transition((event_name, event[0]))

    def get_handlers(self):
        self.fsm = Fsm(TRANSITION_TABLE)
        return {
            x: self.transition_on_event(x)
            for x in ('delimiter', 'end_of_line', 'identifier', 'number', 'special', 'string', 'variable', 'eof')
        }
