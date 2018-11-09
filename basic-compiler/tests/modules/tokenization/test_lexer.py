from pathlib import Path

from unittest.mock import call, MagicMock

from basic_compiler.modules.EventEngine import EventEngine
from basic_compiler.modules.tokenization.AsciiCategorizer import AsciiCategorizer
from basic_compiler.modules.tokenization.FileReader import FileReader
from basic_compiler.modules.tokenization.Tokenizer import Tokenizer

base_dir = Path(__file__).resolve().parent


def test_lexer_end_to_end():
    tokenizer = Tokenizer()
    event_engine = EventEngine([
        FileReader(),
        AsciiCategorizer(),
        tokenizer,
    ])

    token_event = MagicMock()
    tokenizer.set_external_event_handler(token_event)

    event_engine.start(('open', base_dir / 'small_source.bas'))
    token_event.assert_has_calls([
        call(('number', '1')),
        call(('identifier', 'LET')),
        call(('identifier', 'L')),
        call(('special', '=')),
        call(('number', '2000')),
        call(('end_of_line', '\n')),

        call(('number', '10')),
        call(('identifier', 'DIM')),
        call(('identifier', 'S')),
        call(('special', '(')),
        call(('identifier', 'L')),
        call(('special', ')')),
        call(('end_of_line', '\n')),

        call(('number', '20')),
        call(('identifier', 'LET')),
        call(('identifier', 'P')),
        call(('special', '=')),
        call(('number', '2')),
        call(('end_of_line', '\n')),
    ])
