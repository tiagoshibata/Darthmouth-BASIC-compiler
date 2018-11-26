from contextlib import redirect_stdout
import io
from pathlib import Path
import subprocess
from unittest.mock import call, MagicMock

import pytest

from basic_compiler.modules.EventEngine import EventEngine
from basic_compiler.modules.syntax_recognizer.SyntaxRecognizer import SyntaxRecognizer
from basic_compiler.modules.tokenization.AsciiCategorizer import AsciiCategorizer
from basic_compiler.modules.tokenization.FileReader import FileReader
from basic_compiler.modules.tokenization.Tokenizer import Tokenizer

base_dir = Path(__file__).resolve().parent


def lli_version():
    try:
        return subprocess.run(['lli', '--version'], capture_output=True, text=True, check=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return

lli = pytest.mark.skipif(not lli_version(), reason="LLVM interpreter lli not found")


def lli_run(source):
    completed_process = subprocess.run(['lli'], input=source, capture_output=True, text=True)
    # Print formatted source (with numbered lines) if execution fails
    assert completed_process.returncode == 0, '{}\nInput program:\n{}'.format(
        completed_process.stderr,
        '\n'.join('{: <2}: {}'.format(n + 1, s) for n, s in enumerate(source.splitlines())))
    return completed_process.stdout


def create_event_engine():
    return EventEngine([
        FileReader(),
        AsciiCategorizer(),
        Tokenizer(),
        SyntaxRecognizer(),
    ])


def format_float(n):
    return '{0:.6f}\n'.format(n)


@lli
@pytest.mark.parametrize('source_filename,expected_output', [
    ('empty.bas', ''),
    ('minimal.bas', ''),
    ('data.bas', ''),
    ('read.bas', ''),
    ('jump_to_data.bas', ''),
    ('print.bas', '\ntest\ntest without a new line\n'),
    ('print_expression.bas', ''.join(format_float(x) for x in [1, 2, -2, 0, 0, -1, 17, -15])),
    ('fibonacci.bas', ''.join(format_float(x) for x in [0, 1, 1, 2, 3, 5, 8])),
    ('for.bas', ''.join(format_float(x) for x in range(11))),
    ('bubblesort.bas', ''.join(format_float(x) for x in range(20))),
])
def test_compiler_end_to_end(source_filename, expected_output):
    event_engine = create_event_engine()

    with io.StringIO() as f:
        with redirect_stdout(f):
            event_engine.start(('open', base_dir / source_filename))
        s = f.getvalue()
    assert s  # ensure code was generated
    assert lli_run(s) == expected_output


def test_rand_end_to_end():
    event_engine = create_event_engine()

    with io.StringIO() as f:
        with redirect_stdout(f):
            event_engine.start(('open', base_dir / 'rand.bas'))
        s = f.getvalue()
    assert s  # ensure code was generated
    output = lli_run(s)
    for l in output.splitlines():
        value = float(l.rstrip())
        assert 0 <= value <= 1
