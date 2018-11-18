from collections import namedtuple

State = namedtuple('State', ['token_type', 'transitions'], defaults=(None, []))
Transition = namedtuple('Transition', ['event', 'to', 'semantic_action'], defaults=([], None))


class FsmError(RuntimeError):
    pass


def find_transition(transition_list, event):
    if isinstance(event[1], str):
        event = (event[0], event[1].upper())  # make case insensitive comparisons
    transition = next((x for x in transition_list
                       if not x.event or isinstance(x.event, Fsm) or x.event == event or isinstance(x.event, str) and x.event == event[0]), None)
    if not transition:
        return None
    if transition.semantic_action:
        transition.semantic_action(event[1])
    return (transition.event, transition.to)


class Fsm:
    def __init__(self, states):
        self.states = states
        self.sub_fsm = None
        self.reset()

    def reset(self):
        self.current_state_name = 'start'
        self.current_token = []

    def copy(self):
        return Fsm(this.states)

    def transition(self, event):
        if self.sub_fsm:
            if self.sub_fsm.transition(event):
                # Sub FSM returned, go back to normal execution
                self.sub_fsm = None
        current_state = self.states[self.current_state_name]
        transition = find_transition(current_state.transitions, event)
        identified_token = None
        if transition is None:
            # Longest path found
            if not current_state.token_type:
                raise FsmError('No valid transition for {}'.format(event))
            # Return token class and value
            identified_token = (current_state.token_type, ''.join(self.current_token))
            self.reset()
            self.transition(event)
            return identified_token
        elif not transition[0]:
            # Empty transition, don't consume the token yet
            self.current_state_name = transition[1]
            return self.transition(event)
        elif isinstance(transition[0], Fsm):
            # Call a sub-FSM
            self.sub_fsm = transition[0].copy()
        self.current_token.append(event[1])
        self.current_state_name = transition[1]
