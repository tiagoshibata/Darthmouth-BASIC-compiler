import argparse
from contextlib import redirect_stdout
import io
from pathlib import Path
import subprocess

from basic_compiler.modules.EventEngine import EventEngine
from basic_compiler.modules.syntax_recognizer.SyntaxRecognizer import SyntaxRecognizer
from basic_compiler.modules.tokenization.AsciiCategorizer import AsciiCategorizer
from basic_compiler.modules.tokenization.FileReader import FileReader
from basic_compiler.modules.tokenization.Tokenizer import Tokenizer


def parse_args():
    parser = argparse.ArgumentParser(description='BASIC to LLVM IR compiler.')
    parser.add_argument('--opt', action='store_true', help='call optimizer on generated code')
    parser.add_argument('--lli', action='store_true', help='run generated code with lli')
    parser.add_argument('--bin', help='call assembler and linker to output a binary')
    parser.add_argument('source', type=Path, help='source file')
    return parser.parse_args()


def to_ir(filename):
    engine = EventEngine([
        FileReader(),
        AsciiCategorizer(),
        Tokenizer(),
        SyntaxRecognizer(),
    ])
    engine.start(('open', filename))


def main(args):
    if not args.source.exists():
        raise RuntimeError('{} not found'.format(args.source))

    with io.StringIO() as f:
        with redirect_stdout(f):
            to_ir(args.source)
        s = f.getvalue()

    output = args.source.parent / '{}.ll'.format(args.source.stem)
    with open(output, 'w') as f:
        f.write(s)

    if args.opt:
        output_optimized = args.source.parent / '{}_Ofast.ll'.format(args.source.stem)
        subprocess.run(['clang', '-Ofast', '-S', '-emit-llvm', output, '-o', output_optimized], check=True)
        output = output_optimized

    if args.bin:
        subprocess.run(['clang', '-Ofast', output, '-o', args.bin, '-lm'], check=True)

    if args.lli:
        subprocess.run(['lli', output], check=True)

if __name__ == '__main__':
    main(parse_args())
