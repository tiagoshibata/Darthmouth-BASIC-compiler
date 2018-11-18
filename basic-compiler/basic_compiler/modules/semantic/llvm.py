import os


class SemanticError(RuntimeError):
    pass


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
        if instructions[-1].lstrip().split()[0] not in ('ret', 'undefined'):
            # Add a terminator if the body doesn't end with one
            instructions.append('musttail call void @exit(i32 0) noreturn nounwind')
            instructions.append('unreachable')
        return '\n'.join((
            'define dso_local {} @{}({}) local_unnamed_addr {} {{'.format(self.return_type, self.name, self.arguments, self.attributes),
            '\n'.join(('  {}'.format(x) for x in instructions)),
            '}\n',
        ))

# Text common to all generated LLVM IR files
LLVM_TAIL = '''declare void @llvm.donothing() nounwind readnone
declare void @exit(i32) local_unnamed_addr noreturn nounwind

attributes #0 = { nounwind "correctly-rounded-divide-sqrt-fp-math"="false" "disable-tail-calls"="false" "less-precise-fpmad"="false" "no-frame-pointer-elim"="false" "no-infs-fp-math"="true" "no-jump-tables"="false" "no-nans-fp-math"="true" "no-signed-zeros-fp-math"="true" "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-cpu"="x86-64" "target-features"="+fxsr,+mmx,+sse,+sse2,+x87" "unsafe-fp-math"="true" "use-soft-float"="false" }
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
        self.read_count = 0
        self.variables = set()


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


class LlvmIrGenerator:
    def __init__(self, filename):
        self.state = SemanticState(os.path.basename(filename))
        self.program = Program()
        self.state.functions.extend((self.program, Main()))

    def label(self, identifier):
        try:
            identifier = int(identifier)
        except ValueError:
            raise SemanticError('Label is not valid: {}'.format(identifier))
        if identifier in self.state.defined_labels:
            raise SemanticError('Duplicate label {}'.format(identifier))
        label = 'label_{}'.format(identifier)
        if not self.state.entry_point:
            # First label is the entry point
            self.state.entry_point = identifier
        self.state.defined_labels.add(identifier)
        self.program.append(lambda state: ('br label %{}'.format(label) if identifier in state.goto_targets | state.gosub_targets else None))
        self.program.append(lambda state: ('{}:'.format(label) if identifier in state.goto_targets | state.gosub_targets | {state.entry_point} else None))

    def read_item(self, variable):
        self.state.variables.add(variable)
        i = self.state.read_count  # named register with index of current read
        self.program.append('%i{} = load i32, i32* @data_index, align 4'.format(i))
        self.program.append(lambda state:
            '%tmp{i} = getelementptr [{len} x double], [{len} x double]* @DATA, i32 0, i32 %i{i}'.format(len=len(state.const_data), i=i))
        self.program.append('%data_value{i} = load double, double* %tmp{i}, align 8'.format(i=i))
        self.program.append('store double %data_value{}, double* @{}, align 8'.format(i, variable))
        self.program.append('%i{i}_inc = add i32 %i{i}, 1'.format(i=i))
        self.program.append('store i32 %i{}_inc, i32* @data_index, align 4'.format(i))
        self.state.read_count += 1

    def data_start(self, _):
        # TODO only add if necessary. Add block terminator if needed
        self.program.append('call void @llvm.donothing() nounwind readnone')

    def data_item(self, value):
        try:
            self.state.const_data.append(float(value))
        except ValueError:
            raise SemanticError('{} is not a valid number'.format(value))

    def goto(self, target):
        self.state.goto_targets.add(target)
        self.program.append('br label %label_{}'.format(target))

    def def_statement(self, potato):  # TODO
        pass

    def gosub(self, target):
        self.state.gosub_targets.add(target)
        self.program.append('tail call void %label_{}()'.format(target))

    def return_statement(self, token):
        self.program.append('ret void')

    def remark(self, text):
        self.program.append('; {}'.format(text))

    def end(self, event):
        self.program.append('musttail call void @exit(i32 0) noreturn nounwind')
        self.program.append('unreachable')

    def to_ll(self):
        # defined_functions = {x.name for x in self.state.functions}
        # undefined_functions = self.state.referenced_functions - defined_functions
        # if undefined_functions:
        #     raise SemanticError('Undefined functions: {}'.format(undefined_functions))

        undefined_labels = (self.state.goto_targets | self.state.gosub_targets) - self.state.defined_labels
        if undefined_labels:
            raise SemanticError('Undefined labels: {}'.format(undefined_labels))

        if self.state.read_count and not self.state.const_data:
            raise SemanticError('Code has READ statements, but no DATA statement')

        header = [
            'source_filename = "{}"\n'.format(self.state.filename),
        ]

        if self.state.const_data:
            data_array = '[{}]'.format(', '.join('double {}'.format(float(x)) for x in self.state.const_data))
            header.append(
                '@data_index = dso_local local_unnamed_addr global i32 0, align 4\n'
                '@DATA = dso_local local_unnamed_addr constant [{} x double] {}, align 8'.format(len(self.state.const_data), data_array)
            )

        header.extend([
            '@{} = dso_local local_unnamed_addr global double 0., align 8'.format(x) for x in sorted(self.state.variables)])

        return '\n'.join((
            *header,
            '\n'.join(x.to_ll(self.state) for x in self.state.functions),
            LLVM_TAIL,
        ))
