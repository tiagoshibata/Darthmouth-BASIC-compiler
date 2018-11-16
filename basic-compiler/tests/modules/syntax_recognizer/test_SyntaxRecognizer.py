from contextlib import redirect_stdout
import io
from pathlib import Path
from unittest.mock import call, MagicMock

from basic_compiler.modules.syntax_recognizer.SyntaxRecognizer import SyntaxRecognizer
from basic_compiler.modules.semantic.llvm import LLVM_TAIL


def test_empty_program():
    syntax_recognizer = SyntaxRecognizer(None)
    with io.StringIO() as f:
        with redirect_stdout(f):
            syntax_recognizer.handle_event(('open', 'source.bas'))
            syntax_recognizer.handle_event(('eof', None))
        s = f.getvalue()
    assert s.replace('\n\n', '\n') ==  '''source_filename = "source.bas"
; void @program(i8* %target_label) removed because it's empty
define dso_local i32 @main() local_unnamed_addr #1 {
  ret i32 0
}
''' + LLVM_TAIL.replace('\n\n', '\n')



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
    assert s.replace('\n\n', '\n') ==  '''source_filename = "source.bas"
define dso_local void @program(i8* %target_label) local_unnamed_addr #0 {
  indirectbr i8* %target_label, [ label %label_100 ]
  label_100:
  ret void
}
define dso_local i32 @main() local_unnamed_addr #1 {
  musttail call void @program(i8* blockaddress(@program, %label_100)) #0
  ret i32 0
}
''' + LLVM_TAIL.replace('\n\n', '\n')
