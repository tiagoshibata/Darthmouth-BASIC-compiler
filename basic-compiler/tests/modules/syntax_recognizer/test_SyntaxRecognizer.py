from contextlib import redirect_stdout
import io
from pathlib import Path
from unittest.mock import call, MagicMock

import pytest

from basic_compiler.modules.syntax_recognizer.SyntaxRecognizer import SyntaxRecognizer
from basic_compiler.modules.semantic.llvm import LLVM_TAIL, SemanticError


def assert_source_matches(source, desired):
    assert source.replace('\n\n', '\n') ==  desired + LLVM_TAIL.replace('\n\n', '\n')


def test_empty_program():
    syntax_recognizer = SyntaxRecognizer(None)
    with io.StringIO() as f:
        with redirect_stdout(f):
            syntax_recognizer.handle_event(('open', 'source.bas'))
            syntax_recognizer.handle_event(('eof', None))
        s = f.getvalue()
    assert_source_matches(s, '''source_filename = "source.bas"
; void @program(i8* %target_label) omitted because it's empty
define dso_local i32 @main() local_unnamed_addr #1 {
  ret i32 0
}
''')


def test_minimal_program():
    syntax_recognizer = SyntaxRecognizer(None)
    with io.StringIO() as f:
        with redirect_stdout(f):
            syntax_recognizer.handle_event(('open', 'source.bas'))
            syntax_recognizer.handle_event(('number', '100'))
            syntax_recognizer.handle_event(('identifier', 'return'))
            syntax_recognizer.handle_event(('end_of_line', '\n'))
            syntax_recognizer.handle_event(('eof', None))
        s = f.getvalue()
    assert_source_matches(s,  '''source_filename = "source.bas"
define dso_local void @program(i8* %target_label) local_unnamed_addr #0 {
  indirectbr i8* %target_label, [ label %label_100 ]
  label_100:
  ret void
}
define dso_local i32 @main() local_unnamed_addr #1 {
  tail call void @program(i8* blockaddress(@program, %label_100)) #0
  ret i32 0
}
''')


@pytest.mark.xfail(raises=SemanticError)
def test_undefined_label():
    syntax_recognizer = SyntaxRecognizer(None)
    syntax_recognizer.handle_event(('open', 'source.bas'))
    syntax_recognizer.handle_event(('number', '100'))
    syntax_recognizer.handle_event(('identifier', 'goto'))
    syntax_recognizer.handle_event(('number', '200'))
    syntax_recognizer.handle_event(('end_of_line', '\n'))
    syntax_recognizer.handle_event(('eof', None))


@pytest.mark.xfail(raises=SemanticError)
def test_undefined_label_at_gosub():
    syntax_recognizer = SyntaxRecognizer(None)
    syntax_recognizer.handle_event(('open', 'source.bas'))
    syntax_recognizer.handle_event(('number', '100'))
    syntax_recognizer.handle_event(('identifier', 'gosub'))
    syntax_recognizer.handle_event(('number', '200'))
    syntax_recognizer.handle_event(('end_of_line', '\n'))
    syntax_recognizer.handle_event(('eof', None))


@pytest.mark.xfail(raises=SemanticError)
def test_duplicate_label():
    syntax_recognizer = SyntaxRecognizer(None)
    syntax_recognizer.handle_event(('open', 'source.bas'))
    syntax_recognizer.handle_event(('number', '100'))
    syntax_recognizer.handle_event(('identifier', 'return'))
    syntax_recognizer.handle_event(('end_of_line', '\n'))
    syntax_recognizer.handle_event(('number', '100'))
    syntax_recognizer.handle_event(('identifier', 'return'))
    syntax_recognizer.handle_event(('end_of_line', '\n'))
    syntax_recognizer.handle_event(('eof', None))


@pytest.mark.xfail(raises=SemanticError)
def test_duplicate_label():
    syntax_recognizer = SyntaxRecognizer(None)
    syntax_recognizer.handle_event(('open', 'source.bas'))
    syntax_recognizer.handle_event(('number', '100'))
    syntax_recognizer.handle_event(('identifier', 'print'))
    syntax_recognizer.handle_event(('identifier', 'FNX'))
    syntax_recognizer.handle_event(('special', '('))
    syntax_recognizer.handle_event(('variable', 'x'))
    syntax_recognizer.handle_event(('special', ')'))
    syntax_recognizer.handle_event(('end_of_line', '\n'))
    syntax_recognizer.handle_event(('eof', None))


def test_data():
    syntax_recognizer = SyntaxRecognizer(None)
    with io.StringIO() as f:
        with redirect_stdout(f):
            syntax_recognizer.handle_event(('open', 'source.bas'))
            syntax_recognizer.handle_event(('number', '100'))
            syntax_recognizer.handle_event(('identifier', 'data'))
            syntax_recognizer.handle_event(('number', '10'))
            syntax_recognizer.handle_event(('special', ','))
            syntax_recognizer.handle_event(('special', '-'))
            syntax_recognizer.handle_event(('number', '20'))
            syntax_recognizer.handle_event(('special', ','))
            syntax_recognizer.handle_event(('special', '+'))
            syntax_recognizer.handle_event(('number', '30'))
            syntax_recognizer.handle_event(('special', ','))
            syntax_recognizer.handle_event(('number', '3.14e-0'))
            syntax_recognizer.handle_event(('special', ','))
            syntax_recognizer.handle_event(('number', '-.5'))
            syntax_recognizer.handle_event(('end_of_line', '\n'))
            syntax_recognizer.handle_event(('eof', None))
        s = f.getvalue()
    assert_source_matches(s,  '''source_filename = "source.bas"
@DATA = private unnamed_addr constant [5 x double] [double 10.0, double -20.0, double 30.0, double 3.14, double -0.5], align 16
@data_index = internal global i32 0, align 4
define dso_local void @program(i8* %target_label) local_unnamed_addr #0 {
  indirectbr i8* %target_label, [ label %label_100 ]
  label_100:
  tail call void @exit(i32 0) noreturn #0
  unreachable
}
define dso_local i32 @main() local_unnamed_addr #1 {
  tail call void @program(i8* blockaddress(@program, %label_100)) #0
  ret i32 0
}
declare void @exit(i32) local_unnamed_addr noreturn #0
''')
