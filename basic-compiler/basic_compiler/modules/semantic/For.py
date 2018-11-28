from basic_compiler.modules.semantic import llvm


class ForContext:
    def __init__(self, variable):
        self.variable = variable
        self.end = None
        self.step = None
        self.identifier = None


class For:
    def __init__(self, state):
        self.state = state

    def variable(self, variable):
        variable = variable.upper()
        self.state.variables.add(variable)
        self.state.for_context.append(ForContext(variable))

    def left_exp(self):
        llvm.assign_to(self.state, self.state.for_context[-1].variable)

    def right_exp(self):
        if isinstance(self.state.exp_result, float):
            # Literal number
            end = self.state.exp_result
        else:
            right_exp_variable = 'for_{}_end_{}'.format(self.state.for_context[-1].variable, self.state.uid())
            self.state.private_globals.append('@{} = internal global double 0., align 8'.format(right_exp_variable))
            llvm.assign_to(self.state, right_exp_variable)
            end = right_exp_variable
        self.state.for_context[-1].end = end

    def step_value(self, value):
        if isinstance(value, float):
            # Implicit 1 step
            step = value
        elif isinstance(self.state.exp_result, float):
            # Literal number step
            step = self.state.exp_result
        else:
            variable = self.state.for_context[-1].variable
            step = 'for_{}_step_{}'.format(variable, self.state.uid())
            self.state.private_globals.append('@{} = internal global double 0., align 8'.format(step))
            llvm.assign_to(self.state, step)
        self.state.for_context[-1].step = step

    def next(self, variable):
        variable = variable.upper()
        if not self.state.for_context:
            raise llvm.SemanticError('NEXT has no matching FOR')
        for_context = self.state.for_context.pop()
        if variable != for_context.variable:
            raise llvm.SemanticError(
                'NEXT and matching FOR have different counter variables ({} and {})'.format(variable, for_context.variable))

        step = for_context.step
        identifier = for_context.identifier
        end = for_context.end
        self.state.goto_targets.add(identifier)
        label = 'label_{}'.format(identifier)
        old_value = '{}_{}'.format(variable, self.state.uid())
        self.state.append_instruction('%{} = load double, double* @{}, align 8'.format(old_value, variable))
        new_value = 'new_{}_{}'.format(variable, self.state.uid())
        if isinstance(step, float):
            step_value = step
        else:
            # Load step
            step_value = '%step_{}'.format(self.state.uid())
            self.state.append_instruction('{} = load double, double* @{}, align 8'.format(step_value, step))
        # Update variable by step
        self.state.append_instruction('%{} = fadd fast double %{}, {}'.format(new_value, old_value, step_value))
        self.state.append_instruction('store double %{}, double* @{}, align 8'.format(new_value, variable))
        # Load end value
        if isinstance(end, float):
            end_value = end
        else:
            end_value = '%end_{}_{}'.format(variable, self.state.uid())
            self.state.append_instruction('{} = load double, double* @{}, align 8'.format(end_value, end))
        will_jump = 'will_jump_{}'.format(self.state.uid())
        for_exit = 'for_exit_{}'.format(self.state.uid())
        if isinstance(step, float):
            # Step is a literal, so generate a different code path based on its sign
            if step > 0:
                # If new_value <= end, jump to loop, else continue execution
                self.state.append_instruction('%{} = fcmp ole double %{}, {}'.format(will_jump, new_value, end_value))
                self.state.append_instruction('br i1 %{}, label %{}, label %{}'.format(will_jump, label, for_exit))
            else:
                # If new_value >= end, jump to loop, else continue execution
                self.state.append_instruction('%{} = fcmp oge double %{}, {}'.format(will_jump, new_value, end_value))
                self.state.append_instruction('br i1 %{}, label %{}, label %{}'.format(will_jump, label, for_exit))
        else:
            # Step is an expression, generate code to check its sign
            sign = 'step_sign_{}'.format(self.state.uid())
            positive = 'positive_{}'.format(self.state.uid())
            negative = 'negative_{}'.format(self.state.uid())
            self.state.append_instruction('%{} = fcmp oge double {}, 0.'.format(sign, step_value))
            self.state.append_instruction('br i1 %{}, label %{}, label %{}'.format(sign, positive, negative))
            # If step >= 0
            self.state.append_instruction('{}:'.format(positive))
            # If new_value <= end, jump to loop, else continue execution
            self.state.append_instruction('%{} = fcmp ole double %{}, {}'.format(will_jump, new_value, end_value))
            self.state.append_instruction('br i1 %{}, label %{}, label %{}'.format(will_jump, label, for_exit))
            # step < 0
            self.state.append_instruction('{}:'.format(negative))
            # If new_value >= end, jump to loop, else continue execution
            will_jump_2 = 'will_jump_2_{}'.format(self.state.uid())
            self.state.append_instruction('%{} = fcmp oge double %{}, {}'.format(will_jump_2, new_value, end_value))
            self.state.append_instruction('br i1 %{}, label %{}, label %{}'.format(will_jump_2, label, for_exit))
        # Exit of for loop
        self.state.append_instruction('{}:'.format(for_exit))
