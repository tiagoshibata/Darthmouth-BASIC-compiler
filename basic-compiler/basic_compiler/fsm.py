from collections import namedtuple

State = namedtuple('State', ['is_final', 'transitions'])


def find_transition(transition_list, transition):
    return next((target for condition, target in transition_list
                 if condition == transition or isinstance(condition, tuple) and condition[0] == transition), None)


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
        if next_state is None:
            if not current_state.is_final:
                raise RuntimeError('Lexer failed: No valid transition for {}'.format(event[1]))
            token_class = self.current_state_name
            token = ''.join(self.current_token)
            self.reset()
            self.current_state_name = find_transition(self.states['start'].transitions, event)
            return (token_class, token)
        self.current_state_name = next_state
        self.current_token.append(event[1])
