from collections import namedtuple

State = namedtuple('State', ['accept', 'transitions'], defaults=(None, []))
Transition = namedtuple('Transition', ['event', 'to', 'semantic_action'], defaults=([], None))


class FsmError(RuntimeError):
    pass


def find_transition(transition_list, event):
    # Comparisons of the token value are case insensitive
    case_insensitive_event = (event[0], event[1].upper()) if isinstance(event[1], str) else None
    return next((x for x in transition_list
                 if not x.event or isinstance(x.event, Fsm) or x.event == case_insensitive_event or isinstance(x.event, str) and x.event == event[0]), None)


def call_semantic_action(f, event):
    if not f:
        return
    try:
        f(event[1])
    except TypeError:
        f()


class Fsm:
    def __init__(self, states):
        self.states = states
        self.sub_fsm = None
        self.on_success = None
        self.reset()

    def reset(self):
        self.current_state_name = 'start'
        self.current_token = []

    def copy(self):
        return Fsm(self.states)

    def transition(self, event):
        if self.sub_fsm:
            result = self.sub_fsm.transition(event)
            if not result:
                return
            # Sub FSM succeeded, go back to normal execution
            self.sub_fsm = None
            return self.transition(event)
        current_state = self.states[self.current_state_name]
        next_transition = find_transition(current_state.transitions, event)
        identified_token = None
        if next_transition is None:
            # Longest path found
            if not current_state.accept:
                raise FsmError('No valid transition for {}'.format(event))
            # Return token class and value
            identified_token = (current_state.accept, ''.join(self.current_token))
            if self.on_success is None:
                self.reset()
                self.transition(event)
            else:
                call_semantic_action(self.on_success, event)
            return identified_token
        self.current_state_name = next_transition.to
        if isinstance(next_transition.event, Fsm):
            # Call a sub-FSM
            self.sub_fsm = next_transition.event.copy()
            self.sub_fsm.on_success = next_transition.semantic_action or False
            return self.transition(event)
        if next_transition.semantic_action:
            call_semantic_action(next_transition.semantic_action, event)
        if not next_transition.event:
            # Empty transition, don't consume the token yet
            return self.transition(event)
        self.current_token.append(event[1])
