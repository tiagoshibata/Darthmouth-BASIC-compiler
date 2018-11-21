from collections import namedtuple

State = namedtuple('State', ['token_type', 'transitions'], defaults=(None, []))
Transition = namedtuple('Transition', ['event', 'to', 'semantic_action'], defaults=([], None))


class FsmError(RuntimeError):
    pass


def find_transition(transition_list, event):
    # Comparisons of the token value are case insensitive
    case_insensitive_event = (event[0], event[1].upper()) if isinstance(event[1], str) else None
    transition = next((x for x in transition_list
                       if not x.event or isinstance(x.event, Fsm) or x.event == case_insensitive_event or isinstance(x.event, str) and x.event == event[0]), None)
    if not transition:
        return None
    if transition.semantic_action:
        transition.semantic_action(event[1])
    return (transition.event, transition.to)


class Fsm:
    def __init__(self, states):
        self.states = states
        self.sub_fsm = None
        self.root_fsm = True
        self.reset()

    def reset(self):
        self.current_state_name = 'start'
        self.current_token = []

    def copy(self):
        return Fsm(self.states)

    def transition(self, event):
        if self.sub_fsm:
            result = self.sub_fsm.transition(event)
            if result:
                # Sub FSM returned, go back to normal execution
                self.sub_fsm = None
                self.transition(event)
            return result
        current_state = self.states[self.current_state_name]
        next_transition = find_transition(current_state.transitions, event)
        identified_token = None
        if next_transition is None:
            # Longest path found
            if not current_state.token_type:
                raise FsmError('No valid transition for {}'.format(event))
            # Return token class and value
            identified_token = (current_state.token_type, ''.join(self.current_token))
            if self.root_fsm:
                self.reset()
                self.transition(event)
            return identified_token
        self.current_state_name = next_transition[1]
        if not next_transition[0]:
            # Empty transition, don't consume the token yet
            return self.transition(event)
        if isinstance(next_transition[0], Fsm):
            # Call a sub-FSM
            self.sub_fsm = next_transition[0].copy()
            self.sub_fsm.root_fsm = False
            return self.transition(event)
        self.current_token.append(event[1])
