from collections import namedtuple

State = namedtuple('State', ['token_type', 'transitions'], defaults=(None, []))
Transition = namedtuple('Transition', ['event', 'to', 'semantic_action'], defaults=([], None))


class FsmError(RuntimeError):
    pass


def find_transition(transition_list, event):
    if isinstance(event[1], str):
        event = (event[0], event[1].upper())  # make case insensitive comparisons
    transition = next((x for x in transition_list
                       if x.event == event or isinstance(x.event, str) and x.event == event[0]), None)
    if not transition:
        return None
    if transition.semantic_action:
        transition.semantic_action(event[1])
    return transition.to


class Fsm:
    def __init__(self, states):
        self.states = states
        self.reset()

    def reset(self):
        self.current_state_name = 'start'
        self.current_token = []

    def transition(self, event):
        current_state = self.states[self.current_state_name]
        next_state = find_transition(current_state.transitions, event)
        identified_token = None
        if next_state is None:
            # Longest path found
            if not current_state.token_type:
                raise FsmError('No valid transition for {}'.format(event))
            # Return token class and value
            identified_token = (current_state.token_type, ''.join(self.current_token))
            self.reset()
            next_state = find_transition(self.states['start'].transitions, event)
        self.current_state_name = next_state
        self.current_token.append(event[1])
        return identified_token
