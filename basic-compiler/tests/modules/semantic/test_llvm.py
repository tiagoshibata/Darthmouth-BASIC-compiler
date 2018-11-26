from basic_compiler.modules.semantic import llvm


def test_dimensions_specifier():
    assert llvm.dimensions_specifier([]) == 'double'
    assert llvm.dimensions_specifier([2]) == '[2 x double]'
    assert llvm.dimensions_specifier([2, 4]) == '[2 x [4 x double]]'
