'''Based on https://graphviz.gitlab.io/_pages/Gallery/directed/fsm.html'''
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


def fsm_to_graphviz(fsm_dict):
    states = []
    transitions = []
    for name, state in fsm_dict.items():
        if state.accept:
            states.append('node [shape = doublecircle, label="{name} (token class \\"{token}\\")", fontsize=28] {name};'.format(name=name, token=state.accept))
        else:
            states.append('node [shape = circle, label="{name}", fontsize=28] "{name}";'.format(name=name))
        if state.transitions:
            for transition in state.transitions:
                event = str(transition.event).replace('"', '\\"')
                transitions.append('"{}" -> "{}" [ label = "{}", fontsize=28 ];'.format(name, transition.to, event))

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

if __name__ == '__main__':
    main()
