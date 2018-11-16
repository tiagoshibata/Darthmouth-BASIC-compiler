from contextlib import redirect_stdout
import io
from pathlib import Path
from unittest.mock import call, MagicMock

from basic_compiler.modules.syntax_recognizer.SyntaxRecognizer import SyntaxRecognizer


def test_create_label():
    tokenizer = SyntaxRecognizer(None)
    with io.StringIO() as f:
        with redirect_stdout(f):
            tokenizer.handle_event(('number', '100'))
        assert f.getvalue() == 'label_100:\n'
