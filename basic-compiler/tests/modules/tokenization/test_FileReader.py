from pathlib import Path

from unittest.mock import call, MagicMock

from basic_compiler.modules.tokenization.FileReader import FileReader

base_dir = Path(__file__).resolve().parent


def test_reads_file():
    with open(base_dir / 'source.bas') as f:
        expected_lines = f.readlines()
    add_external_event = MagicMock()
    module = FileReader(add_external_event)
    module.handle_event(('open', base_dir / 'source.bas'))
    for event in module:
        module.handle_event(event)
    add_external_event.assert_has_calls([
        *(call(('ascii_line', line)) for line in expected_lines),
        call(('eof', None)),
    ])
