from basic_compiler.fsm import Fsm, State, Transition
from basic_compiler.modules.EventDrivenModule import EventDrivenModule
from basic_compiler.modules.semantic.llvm import LlvmIrGenerator


class SyntaxRecognizer(EventDrivenModule):
    def open_handler(self, event):
        self.ir_generator = LlvmIrGenerator(event[0])
        self.fsm = Fsm({
            'start': State(None, [
                Transition('number', 'statement', self.ir_generator.label),
                Transition('eof', 'eof', lambda _: print(self.ir_generator.to_ll())),
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
                Transition(('identifier', 'RETURN'), 'end', self.ir_generator.return_statement),
                Transition(('identifier', 'REMARK'), 'remark'),
                Transition(('identifier', 'END'), 'end', self.ir_generator.end),
            ]),

            'let': State(None, []),  # TODO
            'read': State(None, [
                Transition('variable', 'end_of_read', self.ir_generator.read_item),
            ]),
            'end_of_read': State(None, [
                Transition(('special', ','), 'read'),
                Transition('end_of_line', 'start'),
            ]),
            'data': State(None, [
                Transition(('special', '+'), '+data'),
                Transition(('special', '-'), '-data'),
                Transition('number', 'end_of_data', self.ir_generator.data_item),
            ]),
            '+data': State(None, [
                Transition('number', 'end_of_data', self.ir_generator.data_item),
            ]),
            '-data': State(None, [
                Transition('number', 'end_of_data', lambda x: self.ir_generator.data_item('-{}'.format(x))),
            ]),
            'end_of_data': State(None, [
                Transition(('special', ','), 'data'),
                Transition('end_of_line', 'start'),
            ]),
            'print': State(None, [

            ]),
            'go': State(None, [
                Transition(('identifier', 'TO'), 'goto'),
            ]),
            'goto': State(None, [
                Transition('number', 'end', self.ir_generator.goto),
            ]),
            'if': State(None, []),  # TODO
            'for': State(None, []),  # TODO
            'next': State(None, []),  # TODO
            'dim': State(None, []),  # TODO
            'def': State(None, []),  # TODO
            'gosub': State(None, [
                Transition('number', 'end', self.ir_generator.gosub),
            ]),
            'remark': State(None, [
                Transition('identifier', 'remark', self.ir_generator.remark),
                Transition('number', 'remark', self.ir_generator.remark),
                Transition('special', 'remark', self.ir_generator.remark),
                Transition('string', 'remark', self.ir_generator.remark),
                Transition('variable', 'remark', self.ir_generator.remark),
                Transition('end_of_line', 'start'),
            ]),
            'end': State(None, [
                Transition('end_of_line', 'start'),
            ]),
            'eof': State('eof')
        })

    def transition_on_event(self, event_name):
        return lambda event: self.fsm.transition((event_name, event[0]))

    def get_handlers(self):
        return {
            'open': self.open_handler,
            **{
                x: self.transition_on_event(x)
                for x in ('end_of_line', 'identifier', 'number', 'special', 'string', 'variable', 'eof')
            },
        }
