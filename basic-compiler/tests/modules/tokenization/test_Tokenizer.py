from pathlib import Path
from unittest.mock import call, MagicMock

import pytest

from basic_compiler.modules.tokenization.AsciiCategorizer import AsciiCategorizer
from basic_compiler.modules.tokenization.Tokenizer import Tokenizer


@pytest.mark.parametrize('source_line,tokens', [
    (('ascii_line', '1 IF S(P) = 0 THEN GOTO 3\n'), [
        call(('number', '1')),
        call(('identifier', 'IF')),
        call(('identifier', 'S')),
        call(('special', '(')),
        call(('identifier', 'P')),
        call(('special', ')')),
        call(('special', '=')),
        call(('number', '0')),
        call(('identifier', 'THEN')),
        call(('identifier', 'GOTO')),
        call(('number', '3')),
        call(('end_of_line', '\n')),
    ]),
    (('ascii_line', '1 IF S2(P) <= -5 THEN GOTO 3\n'), [
        call(('number', '1')),
        call(('identifier', 'IF')),
        call(('identifier', 'S2')),
        call(('special', '(')),
        call(('identifier', 'P')),
        call(('special', ')')),
        call(('special', '<=')),
        call(('special', '-')),
        call(('number', '5')),
        call(('identifier', 'THEN')),
        call(('identifier', 'GOTO')),
        call(('number', '3')),
        call(('end_of_line', '\n')),
    ]),
    (('ascii_line', '-1.23E-4\n'), [
        call(('special', '-')),
        call(('number', '1.23E-4')),
    ]),
    (('ascii_line', '-1.2.3E-4.5E6\n'), [
        call(('special', '-')),
        call(('number', '1.2.3E-4.5E6')),
    ]),
])
def test_filters_ascii_chars(source_line, tokens):
    add_external_event = MagicMock()
    tokenizer = Tokenizer(add_external_event)
    categorizer = AsciiCategorizer(tokenizer.handle_event)
    categorizer.handle_event(source_line)
    tokenizer.handle_event(('eof', None))
    for event in categorizer:
        categorizer.handle_event(event)
    add_external_event.assert_has_calls(tokens)
