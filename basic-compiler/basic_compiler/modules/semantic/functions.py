from basic_compiler.modules.semantic import llvm


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
        if not llvm.is_block_terminator(instructions[-1]):
            # Add a terminator if the body doesn't end with one
            final_semantic_state.external_symbols.add('exit')
            instructions.append('tail call void @exit(i32 0) noreturn #0')
            instructions.append('unreachable')
        return '\n'.join((
            'define dso_local {} @{}({}) local_unnamed_addr {} {{'.format(self.return_type, self.name, self.arguments, self.attributes),
            '\n'.join((('  {}'.format(x) if x[-1] != ':' else x) for x in instructions)),
            '}',
        ))


class Main(Function):
    def __init__(self):
        super().__init__('main', return_type='i32', attributes='#1')
        self.append(lambda state:
            ('tail call void @program(i8* blockaddress(@program, %label_{})) #0'.format(state.entry_point) if state.entry_point else None))
        self.append('ret i32 0')


class Program(Function):
    def __init__(self):
        super().__init__('program', arguments='i8* %target_label', attributes='#0')

        def indirect_branch(state):
            if state.entry_point:
                gosub_targets = state.gosub_targets | {state.entry_point}
            else:
                gosub_targets = state.gosub_targets
            if not gosub_targets:
                return None
            call_label_list = ', '.join(('label %label_{}'.format(x) for x in gosub_targets))
            return 'indirectbr i8* %target_label, [ {} ]'.format(call_label_list)

        self.append(indirect_branch)

# Text common to all generated LLVM IR files
LLVM_TAIL = '''attributes #0 = { nounwind "correctly-rounded-divide-sqrt-fp-math"="false" "disable-tail-calls"="false" "less-precise-fpmad"="false" "no-frame-pointer-elim"="false" "no-infs-fp-math"="true" "no-jump-tables"="false" "no-nans-fp-math"="true" "no-signed-zeros-fp-math"="true" "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-cpu"="x86-64" "target-features"="+fxsr,+mmx,+sse,+sse2,+x87" "unsafe-fp-math"="true" "use-soft-float"="false" }
attributes #1 = { norecurse nounwind "correctly-rounded-divide-sqrt-fp-math"="false" "disable-tail-calls"="false" "less-precise-fpmad"="false" "no-frame-pointer-elim"="false" "no-infs-fp-math"="true" "no-jump-tables"="false" "no-nans-fp-math"="true" "no-signed-zeros-fp-math"="true" "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-cpu"="x86-64" "target-features"="+fxsr,+mmx,+sse,+sse2,+x87" "unsafe-fp-math"="true" "use-soft-float"="false" }

!llvm.ident = !{!0}
!0 = !{!"BASIC to LLVM IR compiler (https://github.com/tiagoshibata/pcs3866-compilers)"}
'''
