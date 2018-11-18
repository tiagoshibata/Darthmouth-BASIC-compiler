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

    def const_string(self, literal):
        # Create a constant null-terminated string, global to this module
        string_constant_identifier = '@.str{}'.format(len(self.state.private_globals))
        string_length = len(literal) + 1
        self.state.private_globals.append('{} = private unnamed_addr constant [{} x i8] c"{}\\00", align 1'.format(string_constant_identifier, string_length, literal))
        return string_constant_identifier, string_length

    def print(self, element):
        self.state.print_parameters.append(element)

    def print_end(self, _, suffix=''):
        self.state.external_symbols.add('printf')

        format_parameters = []
        va_args = []
        for element in self.state.print_parameters:
            if element.startswith('"'):
                # Unescape double quotes
                element = element[1:-1].replace('""', '\\"')
                format_parameters.append('%s')
                # Create a constant string
                str_id, str_len = const_string(element)
                va_args.append('i8* getelementptr inbounds ([{len} x i8], [{len} x i8]* {str_id}, i64 0, i64 0)'.format(len=str_len, str_id=str_id))
            else:
                self.state.variables.add(element)
                format_parameters.append('%f')
                load_tmp = '%{}{}'.format(element, self.state.uid())
                self.program.append('{} = load double, double* @{}, align 8'.format(load_tmp, element))
                va_args.append(load_tmp)

        format_string = '{}{}\\0A'.format(' '.join(format_parameters), suffix)
        format_string_id, length = const_string(format_string)
        self.program.append(
            'tail call i32 (i8*, ...) @printf(i8* getelementptr inbounds ([{len} x i8], [{len} x i8]* {identifier}, i64 0, i64 0), '
            '{va_args})'.format(
                len=length,
                identifier=format_string_id,
                va_args=', '.join(va_args),
            ))

    def print_end_with_newline(self):
        print_end(None, suffix='\n')

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
            'exit': 'declare void @exit(i32) local_unnamed_addr noreturn nounwind',
            'printf': 'declare i32 @printf(i8* nocapture readonly, ...) local_unnamed_addr #0',
            'putchar': 'declare i32 @putchar(i32) local_unnamed_addr #0',
        }
        return [DECLARATIONS[x] for x in sorted(self.state.external_symbols)]

    def to_ll(self):
        # defined_functions = {x.name for x in self.state.functions}
        # undefined_functions = self.state.referenced_functions - defined_functions
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
