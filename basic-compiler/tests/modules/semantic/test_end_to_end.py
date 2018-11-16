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
    completed_process = subprocess.run(['lli'], input=source, capture_output=True, text=True, check=True)
    assert completed_process.returncode == 0, 'lli returned non-zero status'
    return completed_process.stdout


def create_event_engine():
    return EventEngine([
        FileReader(),
        AsciiCategorizer(),
        Tokenizer(),
    ])


@lli
@pytest.mark.parametrize('source_filename,expected_output', [
    ('empty.bas', ''),
    ('minimal.bas', ''),
])
def test_compiler_end_to_end(source_filename, expected_output):
    event_engine = EventEngine([
        FileReader(),
        AsciiCategorizer(),
        Tokenizer(),
        SyntaxRecognizer(),
    ])

    with io.StringIO() as f:
        with redirect_stdout(f):
            event_engine.start(('open', base_dir / source_filename))
        s = f.getvalue()
    assert s  # ensure code was generated
    assert lli_run(s) == expected_output
