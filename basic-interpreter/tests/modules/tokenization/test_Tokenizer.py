from pathlib import Path

from unittest.mock import call, MagicMock

from basic_interpreter.modules.tokenization.AsciiCategorizer import AsciiCategorizer
from basic_interpreter.modules.tokenization.Tokenizer import Tokenizer


def test_filters_ascii_chars():
    add_external_event = MagicMock()
    tokenizer = Tokenizer(add_external_event)
    categorizer = AsciiCategorizer(tokenizer.handle_event)
    categorizer.handle_event(('ascii_line', '1 IF S(P) = 0 THEN GOTO 3\n'))
    for event in categorizer:
        categorizer.handle_event(event)
    for event in tokenizer:
        print(event)
        tokenizer.handle_event(event)
    # WIP
    # add_external_event.assert_has_calls([
    #     call()
    # ])
