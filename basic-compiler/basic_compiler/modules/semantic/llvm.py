import os

from basic_compiler.modules.semantic.Exp import Exp
from basic_compiler.modules.semantic.For import For
from basic_compiler.modules.semantic.Print import Print
from basic_compiler.modules.semantic.functions import Function, LLVM_TAIL, Main, Program


class SemanticError(RuntimeError):
    pass


def is_block_terminator(instruction):
    if not isinstance(instruction, str):
        return False  # not known yet
    opcode = instruction.lstrip().split()[0]
    return opcode in (
        'ret', 'br', 'switch', 'indirectbr', 'invoke', 'resume', 'catchswitch', 'catchret', 'cleanupret', 'unreachable')


class SemanticState:
    def __init__(self, filename):
        self.filename = filename
        self.exp_result = None
        self.functions = []
        self.current_function = None
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
        self.loaded_variables = {}
        self.print_parameters = []
        self.if_left_exp = None
        self.if_cond = None
        self.if_cond_register = None
        self.for_context = []
        self.variable_dimensions = {}
        self.remark = []

    def uid(self):
        self.uid_count += 1
        return self.uid_count

    def append_instruction(self, instruction):
        self.current_function.append(instruction)


def to_int(identifier):
    try:
        return int(identifier)
    except ValueError:
        raise SemanticError('Not a valid int: {}'.format(identifier))


def dimensions_specifier(dimensions):
    if not len(dimensions):
        return 'double'
    return '[{} x {}]'.format(dimensions[0], dimensions_specifier(dimensions[1:]))


def get_multidimensional_ptr(state, variable, dims):
        variable_dimensions = state.variable_dimensions.get(variable, [])
        if len(variable_dimensions) != len(dims):
            raise SemanticError('Variable dimensions mismatch for {} (expected {}, got {})'.format(variable, len(variable_dimensions), len(dims)))
        if not variable_dimensions:
            return 'double* @{}, align 8'.format(variable)
        # Multidimensional, convert operands to int and call getelementptr
        ptr_index = []
        dims_is_constant_expression = True
        for d in dims:
            if isinstance(d, float):
                # Number literal
                ptr_index.append(int(d))
            else:
                # Convert expression result to int
                register = '%fptoui_{}'.format(state.uid())
                state.append_instruction('{} = fptoui double {} to i32'.format(register, d))
                ptr_index.append(register)
                dims_is_constant_expression = False
        ptr_index = ', '.join('i32 {}'.format(x) for x in ptr_index)
        getelementptr = 'getelementptr inbounds {dims}, {dims}* @{var}, i32 0, {index}'.format(
            dims=dimensions_specifier(variable_dimensions),
            var=variable,
            index=ptr_index)
        if dims_is_constant_expression:
            result = getelementptr
        else:
            result = '%ptr_{}'.format(state.uid())
            state.append_instruction('{} = {}'.format(result, getelementptr))
        return 'double* {}, align 16'.format(result)


def assign_to(state, lvalue):
    if ',' not in lvalue:
        # If lvalue is just a variable name, add other qualifiers to make it a pointer
        lvalue = 'double* @{}, align 8'.format(lvalue)
    state.append_instruction('store double {}, {}'.format(state.exp_result, lvalue))


class LlvmIrGenerator:
    def __init__(self, filename):
        self.state = SemanticState(os.path.basename(filename))
        self.state.current_function = Program()
        self.state.functions.extend((self.state.current_function, Main()))
        self.exp = Exp(self.state)
        self.for_statement = For(self.state)
        self.print = Print(self.state)

    def label(self, identifier):
        identifier = to_int(identifier)
        if identifier in self.state.defined_labels:
            raise SemanticError('Duplicate label {}'.format(identifier))
        label = 'label_{}'.format(identifier)
        if not self.state.entry_point:
            # First label is the entry point
            self.state.entry_point = identifier
        if self.state.for_context and not self.state.for_context[-1].identifier:
            self.state.for_context[-1].identifier = identifier
        self.state.defined_labels.add(identifier)
        if not is_block_terminator(self.state.current_function.instructions[-1]):
            self.state.append_instruction(lambda state: ('br label %{}'.format(label) if identifier in state.goto_targets | state.gosub_targets else None))
        self.state.append_instruction(lambda state: ('{}:'.format(label) if identifier in state.goto_targets | state.gosub_targets | {state.entry_point} else None))

    def lvalue(self, variable):
        variable = variable.upper()
        self.state.variables.add(variable)
        self.lvalue_variable = variable
        self.lvalue_dimensions = []

    def lvalue_dimension(self, _):
        self.lvalue_dimensions.append(self.state.exp_result)

    def lvalue_end(self, _):
        self.lvalue_ptr = get_multidimensional_ptr(self.state, self.lvalue_variable, self.lvalue_dimensions)

    def let_rvalue(self, _):
        assign_to(self.state, self.lvalue_ptr)

    def read_item(self, _):
        self.state.has_read = True
        i = self.state.uid()
        self.state.append_instruction('%i_{} = load i32, i32* @data_index, align 4'.format(i))
        self.state.append_instruction(lambda state:
            '%tmp_{i} = getelementptr [{len} x double], [{len} x double]* @DATA, i32 0, i32 %i_{i}'.format(len=len(state.const_data), i=i))
        self.state.append_instruction('%data_value_{i} = load double, double* %tmp_{i}, align 16'.format(i=i))
        self.state.append_instruction('store double %data_value_{}, {}'.format(i, self.lvalue_ptr))
        self.state.append_instruction('%i_{i}_inc = add i32 %i_{i}, 1'.format(i=i))
        self.state.append_instruction('store i32 %i_{}_inc, i32* @data_index, align 4'.format(i))

    def data_item(self, value):
        try:
            self.state.const_data.append(float(value))
        except ValueError:
            raise SemanticError('{} is not a valid number'.format(value))

    def goto(self, target):
        target = to_int(target)
        self.state.goto_targets.add(target)
        self.state.append_instruction('br label %label_{}'.format(target))

    def if_left_exp(self, _):
        self.state.if_left_exp = self.state.exp_result

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
        self.state.if_cond_register = '%cond_{}'.format(self.state.uid())
        self.state.append_instruction('{} = fcmp {} double {}, {}'.format(self.state.if_cond_register, self.state.if_cond, self.state.if_left_exp, self.state.exp_result))

    def if_target(self, target):
        target = to_int(target)
        self.state.goto_targets.add(target)
        if_unequal = 'cond_false_{}'.format(self.state.uid())
        self.state.append_instruction('br i1 {}, label %label_{}, label %{}'.format(self.state.if_cond_register, target, if_unequal))
        self.state.append_instruction('{}:'.format(if_unequal))

    def dim_dimension(self, dimension):
        self.lvalue_dimensions.append(dimension)

    def dim_end(self, _):
        self.state.variables.add(self.lvalue_variable)
        self.state.variable_dimensions[self.lvalue_variable] = self.lvalue_dimensions

    def def_identifier(self, identifier):
        f = Function(identifier, return_type='double', arguments='double %arg')
        self.state.functions.append(f)
        self.state.current_function = f

    def def_parameter(self, variable):
        self.state.loaded_variables = {variable.upper(): '%arg'}

    def def_exp(self, exp):
        self.state.loaded_variables = {}
        self.state.append_instruction('ret double {}'.format(self.state.exp_result))
        self.state.current_function = self.state.functions[0]

    def gosub(self, target):
        target = to_int(target)
        self.state.gosub_targets.add(target)
        self.state.append_instruction('tail call void @program(i8* blockaddress(@program, %label_{})) #0'.format(target))

    def return_statement(self, token):
        self.state.append_instruction('ret void')

    def remark(self, text):
        self.state.append_instruction(';{}'.format(text[3:]))

    def end(self, event):
        self.state.external_symbols.add('exit')
        self.state.append_instruction('tail call void @exit(i32 0) noreturn #0')
        self.state.append_instruction('unreachable')

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
            'rand': 'declare i32 @rand() local_unnamed_addr #0',
            'llvm.pow.f64': 'declare double @llvm.pow.f64(double, double) local_unnamed_addr #0',
        }
        return [DECLARATIONS[x] for x in sorted(self.state.external_symbols)]

    def to_ll(self):
        defined_functions = {x.name for x in self.state.functions}
        undefined_functions = self.state.referenced_functions - defined_functions
        if undefined_functions:
            raise SemanticError('Undefined functions: {}'.format(undefined_functions))

        undefined_labels = (self.state.goto_targets | self.state.gosub_targets) - self.state.defined_labels
        if undefined_labels:
            raise SemanticError('Undefined labels: {}'.format(undefined_labels))

        if self.state.has_read and not self.state.const_data:
            raise SemanticError('Code has READ statements, but no DATA statement')

        if self.state.const_data:
            data_array = '[{}]'.format(', '.join('double {}'.format(float(x)) for x in self.state.const_data))
            self.state.private_globals.append('@data_index = internal global i32 0, align 4')
            self.state.private_globals.append('@DATA = private unnamed_addr constant [{} x double] {}, align 16'.format(len(self.state.const_data), data_array))

        def declare_variable(var):
            dimensions = self.state.variable_dimensions.get(var)
            if not dimensions:
                # Scalar
                return '@{} = internal global double 0., align 8'.format(var)

            return '@{} = internal global {} zeroinitializer, align 16'.format(var, dimensions_specifier(dimensions))

        header = [
            'source_filename = "{}"\ntarget triple = "x86_64-pc-linux-gnu"'.format(self.state.filename),
            '\n'.join((x for x in sorted(self.state.private_globals))),
            '\n'.join((declare_variable(x) for x in sorted(self.state.variables))),
        ]

        body = [x.to_ll(self.state) for x in self.state.functions]

        return '\n\n'.join((x for x in (
            *header,
            *body,
            '\n'.join(self.external_symbols_declarations()),
            LLVM_TAIL,
        ) if x))
