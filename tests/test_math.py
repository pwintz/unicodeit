"""Math spacing, \\text and operator names, roots, matrices, and display style."""
import pytest

import unicodeit


def math(latex):
    return unicodeit.replace(latex, math_spacing=True)


def display(latex):
    return unicodeit.replace(latex, math_spacing=True, display=True)


@pytest.mark.parametrize('latex, expected', [
    # typed spaces are ignored; operators, relations, and punctuation are spaced
    ('a+b=c', 'a + b = c'),
    ('a   +   b', 'a + b'),
    ('f(x,y)', 'f(x, y)'),
    ('x\\in A', 'x ∈ A'),
    ('y \\to 0', 'y → 0'),
    ('n!=1', 'n! = 1'),
    ('a:=b', 'a := b'),
    # unary operators are not spaced
    ('-x+(-1)', '−x + (−1)'),
    ('a=-b', 'a = −b'),
    ('x, -y', 'x, −y'),
    # scripts, primes, and accents stay with their base
    ('x^2+y_1', 'x² + y₁'),
    ("f'(x) = \\hat{y}", "f'(x) = y\u0302"),
    # explicit spacing commands
    ('a~b', 'a\u00a0b'),
    ('a\\ b', 'a b'),
    ('a\\,b', 'a\u2009b'),
    ('a\\quad b', 'a\u2003b'),
    ('a\\qquad b', 'a\u2003\u2003b'),
    ('a\\!b', 'ab'),
    ('\\~{A}', 'Ã'),
    # line breaks
    ('a\\\\b', 'a\nb'),
    ('a\nb', 'a\nb'),
    # a space that ends an unknown command is kept
    ('\\foo x', '\\foo x'),
])
def test_math_spacing(latex, expected):
    assert math(latex) == expected


def test_math_spacing_is_optional():
    assert unicodeit.replace('a+b  =c') == 'a+b  =c'


@pytest.mark.parametrize('latex, expected', [
    ('\\text{if } x>0', 'if x > 0'),
    ('\\text{a  -b}', 'a  -b'),
    ('\\mbox{and}', 'and'),
    ('\\sin x+\\sin(x)', 'sin x + sin(x)'),
    ('\\log_2 n', 'log₂ n'),
    ('\\operatorname{sgn} x', 'sgn x'),
    ('\\mathrm{d}x + \\mathrm{and}', 'dx + and'),
    ('\\sinh x', 'sinh x'),
])
def test_text_and_operator_names(latex, expected):
    assert math(latex) == expected


@pytest.mark.parametrize('latex, expected', [
    ('\\sqrt{2}', '√2'),
    ('\\sqrt{1 + 2}', '√(1 + 2)'),
    ('\\sqrt[3]{x}', '∛x'),
    ('\\sqrt[5]{x}', '⁵√x'),
    ('\\frac{\\sqrt{2}}{2}', '√2/2'),
    ('\\frac{\\text{km}}{\\text{h}}', 'km/h'),
    ('\\frac{\\text{a b}}{c}', '(a b)/c'),
])
def test_roots_and_fraction_terms(latex, expected):
    assert unicodeit.replace(latex) == expected


@pytest.mark.parametrize('latex, expected', [
    ('\\begin{bmatrix}1&2\\\\3&4\\end{bmatrix}', '[1 2; 3 4]'),
    ('\\begin{pmatrix} a & b \\end{pmatrix}', '(a b)'),
    ('\\begin{vmatrix}a&b\\\\c&d\\end{vmatrix}', '|a b; c d|'),
    ('\\begin{matrix}1&0\\\\0&1\\\\\\end{matrix}', '1 0; 0 1'),
    ('\\begin{cases}x&x\\geq0\\\\-x&\\text{else}\\end{cases}', '{x, x ≥ 0; −x, else'),
])
def test_inline_matrices(latex, expected):
    assert math(latex) == expected


@pytest.mark.parametrize('latex, expected', [
    ('A=\\begin{bmatrix}1&-2\\\\\\alpha&4\\end{bmatrix}x',
     'A = ⎡1  −2⎤ x\n'
     '    ⎣α  4 ⎦'),
    ('\\begin{pmatrix}a&b\\end{pmatrix}', '(a  b)'),
    ('\\begin{Bmatrix}1\\\\2\\\\3\\end{Bmatrix}',
     '⎧1⎫\n'
     '⎨2⎬\n'
     '⎩3⎭'),
    ('|x|=\\begin{cases}x & x\\geq 0\\\\-x&\\text{otherwise}\\end{cases}',
     '|x| = ⎧x   x ≥ 0\n'
     '      ⎩−x  otherwise'),
    ('\\begin{bmatrix}\\frac{1}{2}&0\\\\0&1\\end{bmatrix}',
     '⎡ 1    ⎤\n'
     '⎢───  0⎥\n'
     '⎢ 2    ⎥\n'
     '⎣ 0   1⎦'),
])
def test_display_matrices(latex, expected):
    assert display(latex) == expected


@pytest.mark.parametrize('latex, expected', [
    ('\\frac{a+b}{c}=1',
     ' a + b\n'
     '─────── = 1\n'
     '   c'),
    # the parts of a fraction are in inline style
    ('\\frac{\\frac{1}{2}}{x}',
     ' 1/2\n'
     '─────\n'
     '  x'),
    ('\\frac{\\left(\\frac12\\right)^2}{\\sqrt{1+x}}',
     '  (1/2)²\n'
     '──────────\n'
     ' √(1 + x)'),
    ('\\sum_{i=1}^{\\frac{n}{2}} x',
     'n/2\n'
     ' ∑  x\n'
     'i=1'),
    ('\\sum_{i=1}^{n} a_i + \\lim_{x\\to0} f(x)',
     ' n\n'
     ' ∑  aᵢ + lim f(x)\n'
     'i=1      x→0'),
    ('\\int_0^1 f', '∫₀¹ f'),
])
def test_display_fractions_and_limits(latex, expected):
    assert display(latex) == expected


def test_inline_is_default():
    assert unicodeit.replace('\\frac{a}{b} \\sum_{i}', math_spacing=True) == 'a/b ∑ᵢ'


@pytest.mark.parametrize('latex, expected', [
    ('\\left(\\frac{1}{2}\\right)',
     '⎛ 1 ⎞\n'
     '⎜───⎟\n'
     '⎝ 2 ⎠'),
    ('\\left(\\left(\\frac{1}{2}\\right)+1\\right)',
     '⎛⎛ 1 ⎞    ⎞\n'
     '⎜⎜───⎟ + 1⎟\n'
     '⎝⎝ 2 ⎠    ⎠'),
    ('\\left\\{\\frac{1}{2}\\right.',
     '⎧ 1\n'
     '⎨───\n'
     '⎩ 2'),
    ('\\left\\lfloor\\frac{n}{2}\\right\\rfloor',
     '⎢ n ⎥\n'
     '⎢───⎥\n'
     '⎣ 2 ⎦'),
    # no tall pieces for angle brackets: they go on the middle row
    ('\\left\\langle\\frac{1}{2}\\right\\rangle',
     '  1\n'
     '⟨───⟩\n'
     '  2'),
    ('\\left(\\sum_{i=1}^n x_i\\right)^2',
     '⎛ n    ⎞²\n'
     '⎜ ∑  xᵢ⎟\n'
     '⎝i=1   ⎠'),
    # one row: plain delimiters, as in inline style
    ('\\left(x+1\\right) \\left. y \\right|', '(x + 1)y|'),
    ('a \\leftarrow \\left(1\\right)', 'a ← (1)'),
    ('\\left( 1 + 2', '(1 + 2'),
])
def test_display_delimiters(latex, expected):
    assert display(latex) == expected


def test_display_matrix_with_newlines():
    # newlines inside an environment are spaces, as in LaTeX
    latex = '\\begin{bmatrix} \n1 & 2 & 3 & 5 \n\\end{bmatrix}'
    assert display(latex) == '[1  2  3  5]'
    assert math(latex) == '[1 2 3 5]'
    assert display('\\begin{pmatrix}\na \\\\\nb\n\\end{pmatrix}') == '⎛a⎞\n⎝b⎠'


def test_empty_matrix_rows():
    # empty rows count, but a \\\\ that ends the last row doesn't add one
    latex = '\\begin{bmatrix}\n1 & 2 & 3 & 5  \\\\ \\\\ \\\\\n\\end{bmatrix}'
    assert display(latex) == ('⎡1  2  3  5⎤\n'
                              '⎢          ⎥\n'
                              '⎣          ⎦')
    assert math(latex) == '[1 2 3 5; ; ]'
    assert display('\\begin{bmatrix}1&2\\\\3&4\\\\\\end{bmatrix}') == '⎡1  2⎤\n⎣3  4⎦'


@pytest.mark.parametrize('latex, expected', [
    # scripts after a block of several rows go on its top and bottom rows
    ('\\begin{bmatrix} \n1 & 2 \\\\ 3 & 4 \n\\end{bmatrix}^\\top',
     '⎡1  2⎤ᵀ\n'
     '⎣3  4⎦'),
    ('\\left(\\frac12\\right)^2',
     '⎛ 1 ⎞²\n'
     '⎜───⎟\n'
     '⎝ 2 ⎠'),
    ('A = \\begin{pmatrix}a\\\\b\\end{pmatrix}^{-1}_{ij} x',
     'A = ⎛a⎞⁻¹ x\n'
     '    ⎝b⎠ᵢⱼ'),
    # what can't be raised stays as LaTeX
    ('\\left(\\frac12\\right)^{\\pi}',
     '⎛ 1 ⎞^{π}\n'
     '⎜───⎟\n'
     '⎝ 2 ⎠'),
    # one row: as usual
    ('\\begin{pmatrix}a&b\\end{pmatrix}^T', '(a  b)ᵀ'),
])
def test_display_block_scripts(latex, expected):
    assert display(latex) == expected


def test_display_matrix_cell_with_fraction():
    # a cell over several rows moves as one block, keeping the fraction's parts over its bar
    assert display('\\begin{bmatrix} 1 & 2 \\\\ x & \\frac{d}{dx} x^2 \\end{bmatrix}') == (
        '⎡1     2   ⎤\n'
        '⎢    d     ⎥\n'
        '⎢x  ──── x²⎥\n'
        '⎣    dx    ⎦')
