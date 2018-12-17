'''Based on https://graphviz.gitlab.io/_pages/Gallery/directed/fsm.html'''
import argparse

from basic_compiler.modules.EventEngine import EventEngine
from basic_compiler.modules.syntax_recognizer.SyntaxRecognizer import SyntaxRecognizer
from basic_compiler.modules.tokenization import Tokenizer


def parse_args():
    parser = argparse.ArgumentParser(description='Plot automata to file.')
    return parser.parse_args()

TEMPLATE = '''digraph finite_state_machine {{
    rankdir=LR;
    size="8,5"
    node [shape = point]; starting_point;
    {states}
    node [shape = circle, label="\E"];
    starting_point -> start;
    {transitions}
}}'''


def main(args):
    states = []
    transitions = []
    for name, state in Tokenizer.TRANSITION_TABLE.items():
        if state.accept:
            states.append('node [shape = doublecircle, label="{name} (token class \\"{token}\\")"] {name};'.format(name=name, token=state.accept))
        else:
            states.append('node [shape = circle, label={name}] {name};'.format(name=name))
        if state.transitions:
            for transition in state.transitions:
                event = str(transition.event).replace('"', '\\"')
                transitions.append('{} -> {} [ label = "{}" ];'.format(name, transition.to, event))

    with open('tokenizer.gv', 'w') as f:
        f.write(TEMPLATE.format(
            states='\n'.join(states),
            transitions='\n'.join(transitions),
        ))

if __name__ == '__main__':
    main(parse_args())
