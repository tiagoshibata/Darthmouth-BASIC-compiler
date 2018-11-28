from basic_compiler.modules.semantic import llvm


class If:
    def __init__(self, state):
        self.state = state

    def left_exp(self):
        self.left = self.state.exp_result

    def operator(self, operator):
        operator_to_cond = {
            '=': 'oeq',
            '>': 'ogt',
            '>=': 'oge',
            '<': 'olt',
            '<=': 'ole',
            '<>': 'one',
        }
        cond = operator_to_cond.get(operator)
        if not cond:
            raise llvm.SemanticError('Unknown operator: {}'.format(operator))
        self.cond = cond

    def right_exp(self):
        self.cond_register = '%cond_{}'.format(self.state.uid())
        self.state.append_instruction(
            '{} = fcmp {} double {}, {}'.format(self.cond_register, self.cond, self.left, self.state.exp_result))

    def target(self, target):
        target = llvm.to_int(target)
        self.state.goto_targets.add(target)
        if_unequal = 'cond_false_{}'.format(self.state.uid())
        self.state.append_instruction('br i1 {}, label %label_{}, label %{}'.format(self.cond_register, target, if_unequal))
        self.state.append_instruction('{}:'.format(if_unequal))
