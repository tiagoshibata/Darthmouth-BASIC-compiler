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

    def to_ll(self):
        if not self.instructions:
            # Function bodies with no basic blocks are invalid, so return nothing instead of an empty function
            return "; {} @{}({}) removed because it's empty".format(self.return_type, self.name, self.arguments)
        if self.instructions[-1].lstrip().split()[0] not in ('ret', 'undefined'):
            # Add a terminator if the body doesn't end with one
            self.instructions.append('musttail call void @exit(i32 0) noreturn nounwind')
            self.instructions.append('unreachable')
        return '\n'.join((
            'define dso_local {} @{}({}) local_unnamed_addr {} {{'.format(self.return_type, self.name, self.arguments, self.attributes),
            '\n'.join(('  {}'.format(x) for x in self.instructions)),
            '}\n',
        ))

# Text common to all generated LLVM IR files
LLVM_TAIL = '''declare void @exit(i32) local_unnamed_addr noreturn nounwind

attributes #0 = { nounwind "correctly-rounded-divide-sqrt-fp-math"="false" "disable-tail-calls"="false" "less-precise-fpmad"="false" "no-frame-pointer-elim"="false" "no-infs-fp-math"="true" "no-jump-tables"="false" "no-nans-fp-math"="true" "no-signed-zeros-fp-math"="true" "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-cpu"="x86-64" "target-features"="+fxsr,+mmx,+sse,+sse2,+x87" "unsafe-fp-math"="true" "use-soft-float"="false" }
attributes #1 = { norecurse nounwind "correctly-rounded-divide-sqrt-fp-math"="false" "disable-tail-calls"="false" "less-precise-fpmad"="false" "no-frame-pointer-elim"="false" "no-infs-fp-math"="true" "no-jump-tables"="false" "no-nans-fp-math"="true" "no-signed-zeros-fp-math"="true" "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-cpu"="x86-64" "target-features"="+fxsr,+mmx,+sse,+sse2,+x87" "unsafe-fp-math"="true" "use-soft-float"="false" }

!llvm.ident = !{!0}
!0 = !{!"BASIC to LLVM IR compiler (https://github.com/tiagoshibata/pcs3866-compilers)"}
'''


class LlvmIrGenerator:
    def __init__(self, filename):
        self.filename = os.path.basename(filename)

        program = Function('program', arguments='i8* %target_label', attributes='#0')
        main = Function('main', return_type='i32', attributes='#1')
        main.append('ret i32 0')
        self.functions = [program, main]

        self.referenced_functions = set()
        self.defined_labels = set()
        self.referenced_labels = set()
        self.call_targets = set()

    def label(self, identifier):
        try:
            identifier = int(identifier)
        except ValueError:
            raise SemanticError('Label is not valid: {}'.format(identifier))
        label = 'label_{}'.format(identifier)
        if not self.defined_labels:
            # First instruction is used as entry point
            self.call_targets.add(identifier)
            self.functions[1].instructions.insert(0, 'musttail call void @program(i8* blockaddress(@program, %{})) #0'.format(label))
        self.defined_labels.add(identifier)
        self.functions[0].append('{}:'.format(label))

    def goto(self, target):
        self.referenced_labels.add(target)
        self.functions[0].append('br label %label_{}'.format(target))

    def def_statement(self, potato):  # TODO
        pass

    def gosub(self, target):
        self.referenced_labels.add(target)
        self.call_targets.add(target)
        self.functions[0].append('tail call void %label_{}()'.format(target))

    def return_statement(self, token):
        self.functions[0].append('ret void')

    def remark(self, text):
        self.functions[0].append('; {}'.format(text))

    def end(self, event):
        self.functions[0].append('musttail call void @exit(i32 0) noreturn nounwind')
        self.functions[0].append('unreachable')

    def to_ll(self):
        defined_functions = {x.name for x in self.functions}
        undefined_functions = self.referenced_functions - defined_functions
        if undefined_functions:
            raise SemanticError('Undefined functions: {}'.format(undefined_functions))

        undefined_labels = self.referenced_labels - self.defined_labels
        if undefined_labels:
            raise SemanticError('Undefined labels: {}'.format(undefined_labels))

        if self.call_targets:
            call_label_list = ', '.join(('label %label_{}'.format(x) for x in self.call_targets))
            self.functions[0].instructions.insert(0, 'indirectbr i8* %target_label, [ {} ]'.format(call_label_list))

        return '\n'.join((
            'source_filename = "{}"\n'.format(self.filename),
            '\n'.join(x.to_ll() for x in self.functions),
            LLVM_TAIL,
        ))
