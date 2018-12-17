'''Based on https://graphviz.gitlab.io/_pages/Gallery/directed/fsm.html'''
from basic_compiler.fsm import Fsm
from basic_compiler.modules.tokenization import Tokenizer
from basic_compiler.modules.syntax_recognizer.SyntaxRecognizer import SyntaxRecognizer

TEMPLATE = '''digraph finite_state_machine {{
    rankdir=LR;
    size="8,5"
    node [shape = point]; starting_point;
    {states}
    starting_point -> start;
    {transitions}
}}'''


def label(transition):
    if isinstance(transition, Fsm):
        return 'call(Exp)'
    return str(transition).replace('"', '\\"')


def accept_label(name, accept):
    if isinstance(accept, str):
        return '{} (token class \\"{}\\")'.format(name, accept)
    return name


def fsm_to_graphviz(fsm_dict):
    states = []
    transitions = []
    for name, state in fsm_dict.items():
        if state.accept:
            states.append('node [shape = doublecircle, label="{label}", fontsize=28] {name};'.format(label=accept_label(name, state.accept), name=name, token=state.accept))
        else:
            states.append('node [shape = circle, label="{name}", fontsize=28] "{name}";'.format(name=name))
        if state.transitions:
            for transition in state.transitions:
                transitions.append('"{}" -> "{}" [ label = "{}", fontsize=28 ];'.format(name, transition.to, label(transition.event)))

    return TEMPLATE.format(
            states='\n'.join(states),
            transitions='\n'.join(transitions),
        )

def main():
    tokenizer_graphviz = fsm_to_graphviz(Tokenizer.TRANSITION_TABLE)
    with open('tokenizer.gv', 'w') as f:
        f.write(tokenizer_graphviz)

    recognizer = SyntaxRecognizer()
    recognizer.open_handler([''])
    recognizer_graphviz = fsm_to_graphviz(recognizer.fsm.states)
    with open('recognizer.gv', 'w') as f:
        f.write(recognizer_graphviz)

    recognizer_graphviz = fsm_to_graphviz(recognizer.fsm.states['if'].transitions[0].event.states)
    with open('exp.gv', 'w') as f:
        f.write(recognizer_graphviz)

if __name__ == '__main__':
    main()
