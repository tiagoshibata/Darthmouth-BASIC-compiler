from basic_compiler.modules.semantic import llvm
from basic_compiler.modules.syntax_recognizer import SyntaxRecognizer


def to_double(number):
    try:
        return float(number)
    except ValueError:
        raise SyntaxRecognizer.CompilerSyntaxError('Not a valid double: {}'.format(number))


def operator_priority(operator):
    # Functions have lower priority than "(", but higher than "n"
    if operator[0].isalpha():
        return 4
    # '-u' represents the negative sign leading an expression (unary -)
    PRIORITY = [('+', '-'), ('*', '/'), ('↑',), ('-u',), ('function',), ('(',)]
    return next((i for i, x in enumerate(PRIORITY) if operator in x))


class Exp:
    def __init__(self, state):
        self.state = state
        self.operator_queue = []
        self.operand_queue = []

    def is_unary_negative(self):
        if self.operator_queue and self.operator_queue[-1] == '-u':
            self.operator_queue.pop()
            return True
        return False

    def negative_expression(self):
        if not self.is_unary_negative():
            self.operator_queue.append('-u')

    def number(self, number):
        number = to_double(number)
        # Negate the result if a unary negative precedes it
        if self.is_unary_negative():
            number = -number
        self.operand_queue.append(number)

    def variable(self, variable):
        variable = variable.upper()
        self.state.variables.add(variable)
        self.operand_queue.append(variable)

    def variable_dimension(self):
        self.operator_queue.append(',')
        self.operand_queue.append(self.state.exp_result)

    def end_of_variable(self):
        dimensions = []
        while self.operator_queue and self.operator_queue[-1] == ',':
            self.operator_queue.pop()
            dimensions.insert(0, self.operand_queue.pop())
        variable = self.operand_queue.pop()
        register = self.state.loaded_variables.get(variable)
        if not register:
            register = '%{}_{}'.format(variable, self.state.uid())
            ptr = llvm.get_variable_ptr(self.state, variable, dimensions)
            self.state.append_instruction('{} = load double, {}'.format(register, ptr))
        self.operand_queue.append(register)

    def negate(self, register):
        negated = '{}_neg'.format(register)
        self.state.append_instruction('{} = fsub fast double 0., {}'.format(negated, register))
        return negated

    def evaluate_expression(self):
        if self.is_unary_negative():
            register = self.negate(self.operand_queue.pop())
        else:
            operator = self.operator_queue.pop()
            operand_2, operand = self.operand_queue.pop(), self.operand_queue.pop()
            if operator == '↑':
                self.state.external_symbols.add('llvm.pow.f64')
                register = '%pow_{}'.format(self.state.uid())
                self.state.append_instruction('{} = tail call fast double @llvm.pow.f64(double {}, double {}) #0'.format(register, operand, operand_2))
            else:
                operator_to_instruction = {
                    '+': 'fadd',
                    '-': 'fsub',
                    '*': 'fmul',
                    '/': 'fdiv',
                }
                instruction = operator_to_instruction[operator]
                register = '%{}_{}'.format(instruction, self.state.uid())
                self.state.append_instruction('{} = {} fast double {}, {}'.format(register, instruction, operand, operand_2))
        self.operand_queue.append(register)

    def evaluate_scope(self):
        # Evaluate until start of scope ("(" or start of expression)
        while self.operator_queue:
            if self.operator_queue[-1] == '(':
                return
            self.evaluate_expression()

    def operator(self, operator):
        if self.operator_queue:
            # If pending operators are stacked, first check if current operator can be stacked given its priority
            queue_top_priority = operator_priority(self.operator_queue[-1])
            if operator_priority(operator) <= queue_top_priority:
                # Can't stack, evaluate previous expression first
                self.evaluate_scope()
        self.operator_queue.append(operator.upper())

    def end_expression(self):
        # Pop queued operators until '(' or start of expression is found
        self.evaluate_scope()
        if self.operator_queue:
            self.operator_queue.pop()
        else:
            self.state.exp_result = self.operand_queue.pop()

    def call_function(self, function):
        register = '%{}_{}'.format(function, self.state.uid())
        operand = self.operand_queue.pop()
        if function.startswith('FN'):
            # Call user defined function
            self.state.referenced_functions.add(function)
            self.state.append_instruction('{} = tail call fast double @{}(double {}) #0'.format(register, function, operand))
        else:
            built_in_to_implementation = {
                'SIN': 'llvm.sin.f64',
                'COS': 'llvm.cos.f64',
                'TAN': 'tan',
                'ATN': 'atan',
                'EXP': 'llvm.exp.f64',
                'ABS': 'llvm.fabs.f64',
                'LOG': 'llvm.log.f64',
                'SQR': 'llvm.sqrt.f64',
                'INT': 'llvm.rint.f64',
                'RND': 'rand',
            }

            implementation = built_in_to_implementation.get(function)
            if not implementation:
                raise llvm.SemanticError('Unknown function identifier: {}'.format(function))

            self.state.external_symbols.add(implementation)
            if function == 'RND':
                # Call rand, cast to double and divide by RAND_MAX (platform-specific, 2147483647 on Linux)
                self.state.append_instruction('{}_int = call i32 @rand() #0'.format(register))
                self.state.append_instruction('{r}_double = sitofp i32 {r}_int to double'.format(r=register))
                self.state.append_instruction('{r} = fdiv double {r}_double, 2147483647.'.format(r=register))
            else:
                self.state.append_instruction('{} = tail call fast double @{}(double {}) #0'.format(register, implementation, operand))
        self.operand_queue.append(register)

    def end_nested_expression(self):
        # Check if expression was the argument of a function call
        if self.operator_queue and self.operator_queue[-1][0].isalpha():
            function = self.operator_queue.pop()
            self.call_function(function)
