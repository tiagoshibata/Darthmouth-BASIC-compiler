from pathlib import Path

from unittest.mock import call, MagicMock

from basic_interpreter.modules.tokenization.AsciiCategorizer import AsciiCategorizer


def test_categorizes_ascii_chars():
    add_external_event = MagicMock()
    module = AsciiCategorizer(add_external_event)
    module.handle_event(('ascii_line', '1 IF S(P) = 0 THEN GOTO 3\n'))
    for event in module:
        module.handle_event(event)
    add_external_event.assert_has_calls([
        call(('ascii_digit', '1')),
        call(('ascii_delimiter', ' ')),
        call(('ascii_character', 'I')),
        call(('ascii_character', 'F')),
        call(('ascii_delimiter', ' ')),
        call(('ascii_character', 'S')),
        call(('ascii_special', '(')),
        call(('ascii_character', 'P')),
        call(('ascii_special', ')')),
        call(('ascii_delimiter', ' ')),
        call(('ascii_special', '=')),
        call(('ascii_delimiter', ' ')),
        call(('ascii_digit', '0')),
        call(('ascii_delimiter', ' ')),
        call(('ascii_character', 'T')),
        call(('ascii_character', 'H')),
        call(('ascii_character', 'E')),
        call(('ascii_character', 'N')),
        call(('ascii_delimiter', ' ')),
        call(('ascii_character', 'G')),
        call(('ascii_character', 'O')),
        call(('ascii_character', 'T')),
        call(('ascii_character', 'O')),
        call(('ascii_delimiter', ' ')),
        call(('ascii_digit', '3')),
        call(('ascii_ctrl', '\n')),
    ])
