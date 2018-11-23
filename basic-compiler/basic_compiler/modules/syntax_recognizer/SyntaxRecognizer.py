from basic_compiler.fsm import Fsm, State, Transition
from basic_compiler.modules.EventDrivenModule import EventDrivenModule
from basic_compiler.modules.semantic.llvm import LlvmIrGenerator


class SyntaxRecognizer(EventDrivenModule):
    def open_handler(self, event):
        self.ir_generator = LlvmIrGenerator(event[0])
        exp_fsm = Fsm({})
        exp_fsm.states = {
            'start': State(None, [
                Transition(('special', '+'), 'start'),
                Transition(('special', '-'), 'start', self.ir_generator.negative_expression),
                Transition(None, 'start_expression'),
            ]),
            'start_expression': State(None, [
                Transition(('special', '('), 'nested_expression', self.ir_generator.operator),
                Transition('number', 'end_expression', self.ir_generator.number),
                Transition('variable', 'end_expression', self.ir_generator.variable),
                Transition('identifier', 'function_call', self.ir_generator.operator),
            ]),
            'nested_expression': State(None, [
                Transition(exp_fsm, 'end_of_nested_expression'),  # TODO
            ]),
            'end_of_nested_expression': State(None, [
                Transition(('special', ')'), 'end_expression', self.ir_generator.end_nested_expression),
            ]),
            'function_call': State(None, [
                Transition(('special', '('), 'nested_expression', self.ir_generator.operator),
            ]),
            'end_expression': State(None, [
                Transition(('special', '+'), 'start_expression', self.ir_generator.operator),
                Transition(('special', '-'), 'start_expression', self.ir_generator.operator),
                Transition(('special', '*'), 'start_expression', self.ir_generator.operator),
                Transition(('special', '/'), 'start_expression', self.ir_generator.operator),
                Transition(('special', '↑'), 'start_expression', self.ir_generator.operator),
                Transition(None, 'accept', self.ir_generator.end_expression),
            ]),
            'accept': State(True)
        }

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

            'let': State(None, [
                Transition('variable', 'let_assign', self.ir_generator.let_lvalue),
            ]),
            'let_assign': State(None, [
                Transition(('special', '='), 'let_rvalue'),
            ]),
            'let_rvalue': State(None, [
                Transition(exp_fsm, 'let_end'),
            ]),
            'let_end': State(None, [
                Transition('end_of_line', 'start', self.ir_generator.let_rvalue),
            ]),

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
                Transition('end_of_line', 'start', self.ir_generator.print_newline),
                Transition('string', 'print_string', self.ir_generator.print),
                Transition(exp_fsm, 'print_exp_result'),
            ]),
            'print_string': State(None, [
                Transition(('special', ','), 'print_after_comma'),
                Transition('end_of_line', 'start', self.ir_generator.print_end_with_newline),
                Transition(exp_fsm, 'print_exp_result'),
            ]),
            'print_after_comma': State(None, [
                Transition('end_of_line', 'start', self.ir_generator.print_end),
                Transition(exp_fsm, 'print_exp_result'),
            ]),
            'print_exp_result': State(None, [
                Transition(None, 'print_after_exp', self.ir_generator.print_expression_result),
            ]),
            'print_after_exp': State(None, [
                Transition(('special', ','), 'print_after_comma'),
                Transition('end_of_line', 'start', self.ir_generator.print_end_with_newline),
            ]),

            'go': State(None, [
                Transition(('identifier', 'TO'), 'goto'),
            ]),
            'goto': State(None, [
                Transition('number', 'end', self.ir_generator.goto),
            ]),
            'if': State(None),  # TODO
            'for': State(None),  # TODO
            'next': State(None),  # TODO
            'dim': State(None),  # TODO
            'def': State(None),  # TODO
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
