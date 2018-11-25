import os


class SemanticError(RuntimeError):
    pass


def is_block_terminator(instruction):
    if not isinstance(instruction, str):
        return False  # not known yet
    opcode = instruction.lstrip().split()[0]
    return opcode in (
        'ret', 'br', 'switch', 'indirectbr', 'invoke', 'resume', 'catchswitch', 'catchret', 'cleanupret', 'unreachable')


class Function:
    def __init__(self, name, return_type='void', arguments='', attributes='#0'):
        self.return_type = return_type
        self.name = name
        self.arguments = arguments
        self.attributes = attributes
        self.instructions = []

    def append(self, instruction):
        self.instructions.append(instruction)

    def to_ll(self, final_semantic_state):
        def evaluate(instruction):
            if isinstance(instruction, str):
                return instruction
            return instruction(final_semantic_state)

        instructions = [evaluate(x) for x in self.instructions]
        instructions = [x for x in instructions if x]  # remove instructions that became empty
        if not instructions:
            # Function bodies with no basic blocks are invalid, so return nothing instead of an empty function
            return "; {} @{}({}) omitted because it's empty".format(self.return_type, self.name, self.arguments)
        if not is_block_terminator(instructions[-1]):
            # Add a terminator if the body doesn't end with one
            final_semantic_state.external_symbols.add('exit')
            instructions.append('musttail call void @exit(i32 0) noreturn nounwind')
            instructions.append('unreachable')
        return '\n'.join((
            'define dso_local {} @{}({}) local_unnamed_addr {} {{'.format(self.return_type, self.name, self.arguments, self.attributes),
            '\n'.join(('  {}'.format(x) for x in instructions)),
            '}\n',
        ))

# Text common to all generated LLVM IR files
LLVM_TAIL = '''attributes #0 = { nounwind "correctly-rounded-divide-sqrt-fp-math"="false" "disable-tail-calls"="false" "less-precise-fpmad"="false" "no-frame-pointer-elim"="false" "no-infs-fp-math"="true" "no-jump-tables"="false" "no-nans-fp-math"="true" "no-signed-zeros-fp-math"="true" "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-cpu"="x86-64" "target-features"="+fxsr,+mmx,+sse,+sse2,+x87" "unsafe-fp-math"="true" "use-soft-float"="false" }
attributes #1 = { norecurse nounwind "correctly-rounded-divide-sqrt-fp-math"="false" "disable-tail-calls"="false" "less-precise-fpmad"="false" "no-frame-pointer-elim"="false" "no-infs-fp-math"="true" "no-jump-tables"="false" "no-nans-fp-math"="true" "no-signed-zeros-fp-math"="true" "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-cpu"="x86-64" "target-features"="+fxsr,+mmx,+sse,+sse2,+x87" "unsafe-fp-math"="true" "use-soft-float"="false" }

!llvm.ident = !{!0}
!0 = !{!"BASIC to LLVM IR compiler (https://github.com/tiagoshibata/pcs3866-compilers)"}
'''


class SemanticState:
    def __init__(self, filename):
        self.filename = filename
        self.functions = []
        self.referenced_functions = set()
        self.entry_point = None
        self.defined_labels = set()
        self.goto_targets = set()
        self.gosub_targets = set()
        self.const_data = []
        self.uid_count = -1
        self.has_read = False
        self.variables = set()
        self.private_globals = []
        self.external_symbols = set()
        self.expression_operator_queue = []
        self.expression_operand_queue = []
        self.let_lvalue = None
        self.print_parameters = []
        self.if_left_exp = None
        self.if_cond = None
        self.if_cond_register = None
        self.for_context = []

    def uid(self):
        self.uid_count += 1
        return self.uid_count


class Main(Function):
    def __init__(self):
        super().__init__('main', return_type='i32', attributes='#1')
        self.instructions.append(lambda state:
            ('musttail call void @program(i8* blockaddress(@program, %label_{})) #0'.format(state.entry_point) if state.entry_point else None))
        self.append('ret i32 0')


class Program(Function):
    def __init__(self):
        super().__init__('program', arguments='i8* %target_label', attributes='#0')

        def indirect_branch(state):
            if state.defined_labels:
                # If the program is not empty, the entry point is called by main
                gosub_targets = state.gosub_targets | {state.entry_point}
            else:
                gosub_targets = state.gosub_targets
            if not gosub_targets:
                return None
            call_label_list = ', '.join(('label %label_{}'.format(x) for x in gosub_targets))
            return 'indirectbr i8* %target_label, [ {} ]'.format(call_label_list)

        self.append(indirect_branch)


def label_to_int(identifier):
    try:
        return int(identifier)
    except ValueError:
        raise SemanticError('Label is not valid: {}'.format(identifier))


def number_to_double(number):
    try:
        return float(number)
    except ValueError:
        raise SemanticError('Double is not valid: {}'.format(number))


def operator_priority(operator):
    # Functions have lower priority than "(", but higher than "n"
    if len(operator) == 3:
        return 4
    # 'n' represents the negative sign leading an expression (unary -)
    PRIORITY = [('+', '-'), ('*', '/'), ('↑',), ('n',), ('function',), ('(',)]
    priority = next((i for i, x in enumerate(PRIORITY) if operator in x), None)
    if priority is None:
        raise SemanticError('Operator not implemented: {}'.format(operator))
    return priority


class ForContext:
    def __init__(self, variable):
        self.variable = variable
        self.end = None
        self.step = None
        self.identifier = None


class LlvmIrGenerator:
    def __init__(self, filename):
        self.state = SemanticState(os.path.basename(filename))
        self.program = Program()
        self.state.functions.extend((self.program, Main()))

    def label(self, identifier):
        identifier = label_to_int(identifier)
        if identifier in self.state.defined_labels:
            raise SemanticError('Duplicate label {}'.format(identifier))
        label = 'label_{}'.format(identifier)
        if not self.state.entry_point:
            # First label is the entry point
            self.state.entry_point = identifier
        if self.state.for_context and not self.state.for_context[-1].identifier:
            self.state.for_context[-1].identifier = identifier
        self.state.defined_labels.add(identifier)
        if not is_block_terminator(self.program.instructions[-1]):
            self.program.append(lambda state: ('br label %{}'.format(label) if identifier in state.goto_targets | state.gosub_targets else None))
        self.program.append(lambda state: ('{}:'.format(label) if identifier in state.goto_targets | state.gosub_targets | {state.entry_point} else None))

    def negative_expression(self, _):
        if not self.is_unary_negative():
            self.state.expression_operator_queue.append('n')

    def is_unary_negative(self):
        if self.state.expression_operator_queue and self.state.expression_operator_queue[-1] == 'n':
            self.state.expression_operator_queue.pop()
            return True
        return False

    def number(self, number):
        number = number_to_double(number)
        # Negate the result if a unary negative precedes it
        if self.is_unary_negative():
            number = -number
        self.state.expression_operand_queue.append(number)

    def negate(self, register):
        negated = '{}_neg'.format(register)
        self.program.append('{} = fsub fast double 0., {}'.format(negated, register))
        return negated

    def variable(self, variable):
        self.state.variables.add(variable)
        register = '%{}_{}'.format(variable, self.state.uid())
        self.program.append('{} = load double, double* @{}, align 8'.format(register, variable))
        self.state.expression_operand_queue.append(register)

    def evaluate_expression(self):
        if self.is_unary_negative():
            register = self.negate(self.state.expression_operand_queue.pop())
        else:
            operator = self.state.expression_operator_queue.pop()
            operand, operand_2 = self.state.expression_operand_queue.pop(), self.state.expression_operand_queue.pop()
            if operator == '↑':
                self.state.external_symbols.add('llvm.pow.f64')
                register = '%pow_{}'.format(self.state.uid())
                self.program.append('{} = tail call fast double @llvm.pow.f64(double {}, double {}) #0'.format(register, operand, operand_2))
            else:
                operator_to_instruction = {
                    '+': 'fadd',
                    '-': 'fsub',
                    '*': 'fmul',
                    '/': 'fdiv',
                }
                instruction = operator_to_instruction[operator]
                register = '%{}_{}'.format(instruction, self.state.uid())
                self.program.append('{} = {} fast double {}, {}'.format(register, instruction, operand, operand_2))
        self.state.expression_operand_queue.append(register)

    def evaluate_scope(self):
        # Evaluate until start of scope ("(" or start of expression)
        while self.state.expression_operator_queue:
            if self.state.expression_operator_queue[-1] == '(':
                self.state.expression_operator_queue.pop()
                return
            self.evaluate_expression()

    def end_nested_expression(self, _):
        # Check if expression was the argument of a function call
        if self.state.expression_operator_queue and len(self.state.expression_operator_queue[-1]) > 1:
            function = self.state.expression_operator_queue.pop()
            self.call_function(function)

    def call_function(self, function):
        if function.startswith('FN'):
            # Call user defined function
            raise NotImplementedError()

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
            raise SemanticError('Unknown function identifier: {}'.format(function))

        self.state.external_symbols.add(implementation)
        register = '%{}_{}'.format(function, self.state.uid())
        operand = self.state.expression_operand_queue.pop()
        if function == 'RND':
            # Call rand, cast to double and divide by RAND_MAX (platform-specific, 2147483647 on Linux)
            self.program.append('{}_int = call i32 @rand() #0'.format(register))
            self.program.append('{r}_double = sitofp i32 {r}_int to double'.format(r=register))
            self.program.append('{r} = fdiv double {r}_double, 2147483647.'.format(r=register))
        else:
            self.program.append('{} = tail call fast double @{}(double {}) #0'.format(register, implementation, operand))
        self.state.expression_operand_queue.append(register)

    def operator(self, operator):
        if self.state.expression_operator_queue:
            # If pending operators are stacked, first check if current operator can be stacked given its priority
            queue_top_priority = operator_priority(self.state.expression_operator_queue[-1])
            if operator_priority(operator) <= queue_top_priority:
                # Can't stack, evaluate previous expression first
                self.evaluate_scope()
        self.state.expression_operator_queue.append(operator.upper())

    def end_expression(self, _):
        # Pop queued operators until '(' or start of expression is found
        self.evaluate_scope()

    def let_lvalue(self, variable):
        variable = variable.upper()
        self.state.variables.add(variable)
        self.state.let_lvalue = variable

    def assign_to(self, lvalue):
        result = self.state.expression_operand_queue.pop()
        assert not self.state.expression_operand_queue  # queue should be empty after evaluation
        self.program.append('store double {}, double* @{}, align 8'.format(result, lvalue))

    def let_rvalue(self, _):
        self.assign_to(self.state.let_lvalue)
        self.state.let_lvalue = None

    def read_item(self, variable):
        self.state.variables.add(variable)
        self.state.has_read = True
        i = self.state.uid()
        self.program.append('%i_{} = load i32, i32* @data_index, align 4'.format(i))
        self.program.append(lambda state:
            '%tmp_{i} = getelementptr [{len} x double], [{len} x double]* @DATA, i32 0, i32 %i_{i}'.format(len=len(state.const_data), i=i))
        self.program.append('%data_value_{i} = load double, double* %tmp_{i}, align 8'.format(i=i))
        self.program.append('store double %data_value_{}, double* @{}, align 8'.format(i, variable))
        self.program.append('%i_{i}_inc = add i32 %i_{i}, 1'.format(i=i))
        self.program.append('store i32 %i_{}_inc, i32* @data_index, align 4'.format(i))

    def data_item(self, value):
        try:
            self.state.const_data.append(float(value))
        except ValueError:
            raise SemanticError('{} is not a valid number'.format(value))

    def print_newline(self, _):
        self.state.external_symbols.add('putchar')
        self.program.append('tail call i32 @putchar(i32 10)')

    def const_string(self, literal, newline=False):
        # Create a constant null-terminated string, global to this module
        string_constant_identifier = '@.str{}'.format(len(self.state.private_globals))
        # Add one byte for the null-terminator and don't count escape sequences
        string_length = len(literal) + 1 - 2 * literal.count('\\')
        self.state.private_globals.append('{} = private unnamed_addr constant [{} x i8] c"{}\\00", align 1'.format(string_constant_identifier, string_length, literal))
        return string_constant_identifier, string_length

    def print(self, element):
        self.state.print_parameters.append(element)

    def print_expression_result(self, _):
        result = self.state.expression_operand_queue.pop()
        self.state.print_parameters.append(result)
        assert not self.state.expression_operand_queue  # queue should be empty after evaluation

    def print_end(self, _, suffix=''):
        self.state.external_symbols.add('printf')

        format_parameters = []
        va_args = []
        for element in self.state.print_parameters:
            if isinstance(element, float) or element.startswith('%'):
                # Print number literal or local register
                format_parameters.append('%f')
                va_args.append('double {}'.format(element))
            elif element.startswith('"'):
                # Print string literal
                # Unescape and encode double quotes, encode "\"
                element = element[1:-1].replace('""', '\\22').replace('\\', '\\5C')
                format_parameters.append('%s')
                # Create a constant string
                str_id, str_len = self.const_string(element)
                va_args.append('i8* getelementptr inbounds ([{len} x i8], [{len} x i8]* {str_id}, i64 0, i64 0)'.format(len=str_len, str_id=str_id))

        format_string_id, length = self.const_string(' '.join(format_parameters) + suffix)
        self.program.append(
            'tail call i32 (i8*, ...) @printf(i8* getelementptr inbounds ([{len} x i8], [{len} x i8]* {identifier}, i64 0, i64 0), '
            '{va_args})'.format(
                len=length,
                identifier=format_string_id,
                va_args=', '.join(va_args),
            ))
        self.state.print_parameters = []

    def print_end_with_newline(self, _):
        self.print_end(_, suffix='\\0A')

    def goto(self, target):
        target = label_to_int(target)
        self.state.goto_targets.add(target)
        self.program.append('br label %label_{}'.format(target))

    def if_left_exp(self, _):
        self.state.if_left_exp = self.state.expression_operand_queue.pop()
        assert not self.state.expression_operand_queue  # queue should be empty after evaluation

    def if_operator(self, operator):
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
            raise SemanticError('Unknown operator: {}'.format(operator))
        self.state.if_cond = cond

    def if_right_exp(self, _):
        if_right_exp = self.state.expression_operand_queue.pop()
        assert not self.state.expression_operand_queue  # queue should be empty after evaluation
        self.state.if_cond_register = '%cond_{}'.format(self.state.uid())
        self.program.append('{} = fcmp {} double {}, {}'.format(self.state.if_cond_register, self.state.if_cond, self.state.if_left_exp, if_right_exp))

    def if_target(self, target):
        target = label_to_int(target)
        self.state.goto_targets.add(target)
        if_unequal = 'cond_false_{}'.format(self.state.uid())
        self.program.append('br i1 {}, label %label_{}, label %{}'.format(self.state.if_cond_register, target, if_unequal))
        self.program.append('{}:'.format(if_unequal))

    def for_variable(self, variable):
        variable = variable.upper()
        self.state.variables.add(variable)
        self.state.for_context.append(ForContext(variable))

    def for_left_exp(self, _):
        self.assign_to(self.state.for_context[-1].variable)

    def for_right_exp(self, _):
        if isinstance(self.state.expression_operand_queue[-1], float):
            # Literal number
            end = self.state.expression_operand_queue.pop()
        else:
            right_exp_variable = 'for_{}_end_{}'.format(self.state.for_context[-1].variable, self.state.uid())
            self.state.private_globals.append('@{} = internal global double 0., align 8'.format(right_exp_variable))
            self.assign_to(right_exp_variable)
            end = right_exp_variable
        self.state.for_context[-1].end = end

    def for_step_value(self, value):
        self.state.expression_operand_queue
        if isinstance(value, float):
            # Implicit 1 step
            step = value
        elif isinstance(self.state.expression_operand_queue[-1], float):
            # Literal number step
            step = self.state.expression_operand_queue.pop()
        else:
            variable = self.state.for_context[-1].variable
            step = 'for_{}_step_{}'.format(variable, self.state.uid())
            self.state.private_globals.append('@{} = internal global double 0., align 8'.format(step))
            self.assign_to(step)
        self.state.for_context[-1].step = step

    def next(self, variable):
        variable = variable.upper()
        if not self.state.for_context:
            raise SemanticError('NEXT has no matching FOR')
        for_context = self.state.for_context.pop()
        if variable != for_context.variable:
            raise SemanticError('NEXT and matching FOR have different counter variables ({} and {})'.format(variable, for_context.variable))

        step = for_context.step
        identifier = for_context.identifier
        end = for_context.end
        self.state.goto_targets.add(identifier)
        label = 'label_{}'.format(identifier)
        old_value = '{}_{}'.format(variable, self.state.uid())
        self.program.append('%{} = load double, double* @{}, align 8'.format(old_value, variable))
        new_value = 'new_{}_{}'.format(variable, self.state.uid())
        if isinstance(step, float):
            step_value = step
        else:
            # Load step
            step_value = '%step_{}'.format(self.state.uid())
            self.program.append('{} = load double, double* @{}, align 8'.format(step_value, step))
        # Update variable by step
        self.program.append('%{} = fadd fast double %{}, {}'.format(new_value, old_value, step_value))
        self.program.append('store double %{}, double* @{}, align 8'.format(new_value, variable))
        # Load end value
        if isinstance(end, float):
            end_value = end
        else:
            end_value = '%end_{}_{}'.format(variable, self.state.uid())
            self.program.append('{} = load double, double* @{}, align 8'.format(end_value, end))
        will_jump = 'will_jump_{}'.format(self.state.uid())
        for_exit = 'for_exit_{}'.format(self.state.uid())
        if isinstance(step, float):
            # Step is a literal, so generate a different code path based on its sign
            if step > 0:
                # If new_value <= end, jump to loop, else continue execution
                self.program.append('%{} = fcmp ole double %{}, {}'.format(will_jump, new_value, end_value))
                self.program.append('br i1 %{}, label %{}, label %{}'.format(will_jump, label, for_exit))
            else:
                # If new_value >= end, jump to loop, else continue execution
                self.program.append('%{} = fcmp oge double %{}, {}'.format(will_jump, new_value, end_value))
                self.program.append('br i1 %{}, label %{}, label %{}'.format(will_jump, label, for_exit))
        else:
            # Step is an expression, generate code to check its sign
            sign = 'step_sign_{}'.format(self.state.uid())
            positive = 'positive_{}'.format(self.state.uid())
            negative = 'negative_{}'.format(self.state.uid())
            self.program.append('%{} = fcmp oge double {}, 0.'.format(sign, step_value))
            self.program.append('br i1 %{}, label %{}, label %{}'.format(sign, positive, negative))
            # If step >= 0
            self.program.append('{}:'.format(positive))
            # If new_value <= end, jump to loop, else continue execution
            self.program.append('%{} = fcmp ole double %{}, {}'.format(will_jump, new_value, end_value))
            self.program.append('br i1 %{}, label %{}, label %{}'.format(will_jump, label, for_exit))
            # step < 0
            self.program.append('{}:'.format(negative))
            # If new_value >= end, jump to loop, else continue execution
            self.program.append('%{} = fcmp oge double %{}, {}'.format(will_jump, new_value, end_value))
            self.program.append('br i1 %{}, label %{}, label %{}'.format(will_jump, label, for_exit))
        # Exit of for loop
        self.program.append('{}:'.format(for_exit))
        self.state.external_symbols.add('llvm.donothing')
        self.program.append('tail call void @llvm.donothing() nounwind readnone')

    def def_statement(self, potato):  # TODO
        pass

    def gosub(self, target):
        target = label_to_int(target)
        self.state.gosub_targets.add(target)
        self.program.append('tail call void @program(i8* blockaddress(@program, %label_{})) #0'.format(target))

    def return_statement(self, token):
        self.program.append('ret void')

    def remark(self, text):
        self.program.append('; {}'.format(text))

    def end(self, event):
        self.state.external_symbols.add('exit')
        self.program.append('musttail call void @exit(i32 0) noreturn nounwind')
        self.program.append('unreachable')

    def external_symbols_declarations(self):
        DECLARATIONS = {
            'exit': 'declare void @exit(i32) local_unnamed_addr noreturn #0',
            'printf': 'declare i32 @printf(i8* nocapture readonly, ...) local_unnamed_addr #0',
            'putchar': 'declare i32 @putchar(i32) local_unnamed_addr #0',
            'llvm.donothing': 'declare void @llvm.donothing() nounwind readnone',

            # Language built-ins
            'llvm.sin.f64': 'declare double @llvm.sin.f64(double) local_unnamed_addr #0',
            'llvm.cos.f64': 'declare double @llvm.cos.f64(double) local_unnamed_addr #0',
            'tan': 'declare double @tan(double) local_unnamed_addr #0',
            'atan': 'declare double @atan(double) local_unnamed_addr #0',
            'llvm.exp.f64': 'declare double @llvm.exp.f64(double) local_unnamed_addr #0',
            'llvm.abs.f64': 'declare double @llvm.abs.f64(double) local_unnamed_addr #0',
            'llvm.log.f64': 'declare double @llvm.log.f64(double) local_unnamed_addr #0',
            'llvm.sqrt.f64': 'declare double @llvm.sqrt.f64(double) local_unnamed_addr #0',
            'llvm.rint.f64': 'declare double @llvm.rint.f64(double) local_unnamed_addr #0',
            'rand': 'declare i32 rand() local_unnamed_addr #0',
            'llvm.pow.f64': 'declare double @llvm.rint.f64(double, double) local_unnamed_addr #0',
        }
        return [DECLARATIONS[x] for x in sorted(self.state.external_symbols)]

    def to_ll(self):
        # defined_functions = {x.name for x in self.state.functions}
        # undefined_functions = self.state.referenced_functions - defined_functions  # TODO remove symbols in external_symbols_declarations
        # if undefined_functions:
        #     raise SemanticError('Undefined functions: {}'.format(undefined_functions))

        undefined_labels = (self.state.goto_targets | self.state.gosub_targets) - self.state.defined_labels
        if undefined_labels:
            raise SemanticError('Undefined labels: {}'.format(undefined_labels))

        if self.state.has_read and not self.state.const_data:
            raise SemanticError('Code has READ statements, but no DATA statement')

        if self.state.const_data:
            data_array = '[{}]'.format(', '.join('double {}'.format(float(x)) for x in self.state.const_data))
            self.state.private_globals.append('@data_index = internal global i32 0, align 4')
            self.state.private_globals.append('@DATA = private unnamed_addr constant [{} x double] {}, align 8'.format(len(self.state.const_data), data_array))

        header = [
            'source_filename = "{}"'.format(self.state.filename),
            *(x for x in sorted(self.state.private_globals)),
            *('@{} = internal global double 0., align 8'.format(x) for x in sorted(self.state.variables)),
        ]

        body = [x.to_ll(self.state) for x in self.state.functions]

        return '\n'.join((
            *header,
            *body,
            *self.external_symbols_declarations(),
            LLVM_TAIL,
        ))
