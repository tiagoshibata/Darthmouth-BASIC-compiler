from collections import namedtuple

State = namedtuple('State', ['token_type', 'transitions'])


class FsmError(RuntimeError):
    pass


def find_transition(transition_list, transition):
    return next((target for condition, target in transition_list
                 if condition == transition or isinstance(condition, str) and condition == transition[0]), None)


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
