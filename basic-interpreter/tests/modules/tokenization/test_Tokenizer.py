from pathlib import Path
from unittest.mock import call, MagicMock

import pytest

from basic_interpreter.modules.tokenization.AsciiCategorizer import AsciiCategorizer
from basic_interpreter.modules.tokenization.Tokenizer import Tokenizer


@pytest.mark.parametrize('source_line,tokens', [
    (('ascii_line', '1 IF S(P) = 0 THEN GOTO 3\n'), [
        call(('token_number', 1)),
        call(('token_identifier', 'IF')),
        call(('token_identifier', 'S')),
        call(('token_special', '(')),
        call(('token_identifier', 'P')),
        call(('token_special', ')')),
        call(('token_special', '=')),
        call(('token_number', 0)),
        call(('token_identifier', 'THEN')),
        call(('token_identifier', 'GOTO')),
        call(('token_number', 3)),
        call(('token_ctrl', '\n')),
    ]),
    (('ascii_line', '1 IF S2(P) <= -5 THEN GOTO 3\n'), [
        call(('token_number', 1)),
        call(('token_identifier', 'IF')),
        call(('token_identifier', 'S2')),
        call(('token_special', '(')),
        call(('token_identifier', 'P')),
        call(('token_special', ')')),
        call(('token_special', '<=')),
        call(('token_number', -5)),
        call(('token_identifier', 'THEN')),
        call(('token_identifier', 'GOTO')),
        call(('token_number', 3)),
        call(('token_ctrl', '\n')),
    ]),
    (('ascii_line', '-1.23e-4\n'), [
        call(('token_number', -1.23e-4)),
    ]),
])
def test_filters_ascii_chars(source_line, tokens):
    add_external_event = MagicMock()
    tokenizer = Tokenizer(add_external_event)
    categorizer = AsciiCategorizer(tokenizer.handle_event)
    categorizer.handle_event(source_line)
    for event in categorizer:
        categorizer.handle_event(event)
    add_external_event.assert_has_calls(tokens)
