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
        self.print_parameters = []

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
        raise SemanticError('Double is not valid: {}'.format(identifier))


def operator_priority(operator):
    # Functions have lowest priority ("(" must be evaluated first)
    if len(operator) == 3:
        return 0
    # 'n' represents the negative sign leading an expression (unary -)
    PRIORITY = [('n',), ('+', '-'), ('*', '/'), ('↑',), ('(',)]
    priority = next((i for i, x in enumerate(PRIORITY) if operator in x), None)
    if not priority:
        raise SemanticError('Operator not implemented: {}'.format(operator))
    return priority


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
        self.state.defined_labels.add(identifier)
        if not is_block_terminator(self.program.instructions[-1]):
            self.program.append(lambda state: ('br label %{}'.format(label) if identifier in state.goto_targets | state.gosub_targets else None))
        self.program.append(lambda state: ('{}:'.format(label) if identifier in state.goto_targets | state.gosub_targets | {state.entry_point} else None))

    def negative_expression(self, _):
        if self.state.expression_operator_queue[-1] == 'n':
            self.state.expression_operator_queue.pop()
        else:
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

    def negate(register):
        negated = '{}_neg'.format(register)
        self.program.append('%{} = fneg fast double %{}'.format(negated, register))
        return negated

    def variable(self, variable):
        self.state.variables.add(variable)
        register = '{}{}'.format(variable, self.state.uid())
        self.program.append('%{} = load double, double* @{}, align 8'.format(register, variable))
        # Negate the result if a unary negative precedes it
        if self.is_unary_negative():
            self.state.expression_operand_queue.append(negate(register))
        else:
            self.state.expression_operand_queue.append(register)

    def evaluate_expression(self):
        operation = self.state.expression_operator_queue.pop()
        a, b = self.state.expression_operand_queue.pop(), self.state.expression_operand_queue.pop()
        if operation == '+':
            register = 'add_{}_{}_{}'.format(a, b, self.state.uid())
            self.program.append('%{} = fadd fast double %{}, %{}'.format(register, a, b))
        elif operation == '-':
            register = 'sub_{}_{}_{}'.format(a, b, self.state.uid())
            self.program.append('%{} = fsub fast double %{}, %{}'.format(register, a, b))
        elif operation == '*':
            register = 'mul_{}_{}_{}'.format(a, b, self.state.uid())
            self.program.append('%{} = fmul fast double %{}, %{}'.format(register, a, b))
        elif operation == '/':
            register = 'div_{}_{}_{}'.format(a, b, self.state.uid())
            self.program.append('%{} = fdiv fast double %{}, %{}'.format(register, a, b))
        elif operation == '↑':
            self.state.referenced_functions.add('llvm.pow.f64')
            register = 'pow_{}_{}_{}'.format(a, b, self.state.uid())
            self.program.append('%{} = call fast double @llvm.pow.f64(double %{}, double %{}) #0'.format(register, a, b))
        else:
            raise NotImplementedError()
        self.state.expression_operand_queue.append(register)

    def evaluate_scope(self):
        # Evaluate until start of scope ("(")
        while self.state.expression_operator_queue and self.state.expression_operator_queue[-1] != '(':
            self.evaluate_expression()

    def end_nested_expression(self, _):
        # Pop operators until '(' is found
        self.evaluate_scope()
        # Check if expression was the argument of a function call
        if self.state.expression_operator_queue and len(self.state.expression_operator_queue[-1]) > 1:
            function = self.state.expression_operator_queue.pop()
            register = self.call_function(function)
        # Negate the result if a unary negative precedes it
        if self.is_unary_negative():
            self.state.expression_operand_queue.append(negate(register))

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
            raise SemanticError('Unknown function identifier: {}'.format())

        self.state.referenced_functions.add(implementation)
        register = '{}{}'.format(function, self.state.uid())
        operand = self.expression_operand_queue.pop()
        if function == 'RND':
            # Call rand, cast to double and divide by RAND_MAX (platform-specific, 2147483647 on Linux)
            self.program.append('%{}_int = call i32 @rand() #0'.format(register))
            self.program.append('%{r}_double = sitofp i32 %{r}_int to double'.format(r=register))
            self.program.append('%{r} = fdiv double %{r}_double, 2147483647.'.format(r=register))
        else:
            self.program.append('%{} = call fast double @{}(double %{}) #0'.format(register, implementation, operand))
        self.state.expression_operand_queue.append(register)

    def operator(self, operator):
        current_priority = operator_priority(operator)
        queue_top_priority = operator_priority(self.state.expression_operator_queue[-1])
        if current_priority <= queue_top_priority:
            # Can't stack, evaluate previous expression first
            self.evaluate_scope()
        self.state.expression_operator_queue.push(operator)

    def end_expression(self, _):
        # Pop all queued operations
        self.evaluate_scope()

    def read_item(self, variable):
        self.state.variables.add(variable)
        self.state.has_read = True
        i = self.state.uid()
        self.program.append('%i{} = load i32, i32* @data_index, align 4'.format(i))
        self.program.append(lambda state:
            '%tmp{i} = getelementptr [{len} x double], [{len} x double]* @DATA, i32 0, i32 %i{i}'.format(len=len(state.const_data), i=i))
        self.program.append('%data_value{i} = load double, double* %tmp{i}, align 8'.format(i=i))
        self.program.append('store double %data_value{}, double* @{}, align 8'.format(i, variable))
        self.program.append('%i{i}_inc = add i32 %i{i}, 1'.format(i=i))
        self.program.append('store i32 %i{}_inc, i32* @data_index, align 4'.format(i))

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
        self.state.print_parameters.append(self.state.expression_operand_queue.pop())
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
            else:
                # Load global variable
                self.state.variables.add(element)
                format_parameters.append('%f')
                load_tmp = '%{}{}'.format(element, self.state.uid())
                self.program.append('{} = load double, double* @{}, align 8'.format(load_tmp, element))
                va_args.append('double {}'.format(load_tmp))

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

    def def_statement(self, potato):  # TODO
        pass

    def gosub(self, target):
        target = label_to_int(target)
        self.state.gosub_targets.add(target)
        self.program.append('tail call void %label_{}()'.format(target))

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
            'source_filename = "{}"\n'.format(self.state.filename),
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
