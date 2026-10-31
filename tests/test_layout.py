import pytest

import unicodeit


@pytest.mark.parametrize('latex, expected', [
    ('\\frac{a}{b}', 'a/b'),
    ('\\frac{a + b}{b}', '(a + b)/b'),
    ('\\frac{1}{x^2}', '1/x²'),
    ('\\frac{\\alpha}{2\\pi}', 'α/2π'),
    ('\\frac{f(x)}{-1}', 'f(x)/(−1)'),
    ('\\dfrac{a}{b} + \\tfrac{c}{d}', 'a/b + c/d'),
    ('\\frac{\\frac{a}{b}}{c}', '(a/b)/c'),
    ('\\frac{\\left(a + b\\right)}{2}', '(a + b)/2'),
    ('\\sfrac{1}{2}', '½'),
])
def test_fraction(latex, expected):
    assert unicodeit.replace(latex) == expected


@pytest.mark.parametrize('latex, expected', [
    ('\\left(1 + 2\\right)', '(1 + 2)'),
    ('\\left( 1 + 2 \\right)', '( 1 + 2 )'),
    ('\\left\\langle x \\right\\rangle', '⟨ x ⟩'),
    ('\\left\\{ x \\right.', '{ x '),
    ('\\left\\lvert x \\middle\\vert y \\right\\rvert', '| x | y |'),
    ('\\bigl( x \\Bigr]', '( x ]'),
    ('a \\leftarrow b \\rightarrow \\bigcup', 'a ← b → ⋃'),
])
def test_delimiter_sizing(latex, expected):
    assert unicodeit.replace(latex) == expected


@pytest.mark.parametrize('latex, expected', [
    ('{1 + 2}', '1 + 2'),
    ('{{a} + b}', 'a + b'),
    ('x^{\\#}', 'x^{#}'),
    ('\\{1 + 2\\}', '{1 + 2}'),
    ('\\lbrace a \\rbrace', '{ a }'),
    ('\\left\\{ {a} \\right\\}', '{ a }'),
    ('\\frac{\\{a\\}}{2}', '({a})/2'),
    ('\\foo{abc} {d}', '\\foo{abc} d'),
    ('\\breve{', '\\breve{'),
])
def test_grouping_braces(latex, expected):
    assert unicodeit.replace(latex) == expected


@pytest.mark.parametrize('latex, expected', [
    # a command name runs until the first non-letter, as in TeX
    ('\\intf(x)', '\\intf(x)'),
    ('\\int f(x)', '∫ f(x)'),
    ('\\alphax', '\\alphax'),
    ('\\alpha2 \\alpha_1', 'α2 α₁'),
    ('\\dot{x} \\dots{}', 'x\u0307 \\dots{}'),
    ('\\mathbb{R}^n', 'ℝⁿ'),
])
def test_whole_command_names(latex, expected):
    assert unicodeit.replace(latex) == expected


@pytest.mark.parametrize('latex, expected', [
    # arguments without braces are the next character or command, as in TeX
    ('\\dot x', 'x\u0307'),
    ('\\dot2', '2\u0307'),
    ('\\hat\\alpha', 'α\u0302'),
    ('\\vec v + \\vec{w}', 'v\u20d7 + w\u20d7'),
    ('\\sqrt2', '√2'),
    ('\\sqrt\\succ', '√≻'),
    ('\\sqrt[3]x', '∛x'),
    ('\\frac12', '1/2'),
    ('\\frac\\alpha{n+1}', 'α/(n+1)'),
    ('\\mathbb R^n', 'ℝⁿ'),
    ('\\dotx', '\\dotx'),
    ('\\bar{x}', 'x\u0305'),
])
def test_unbraced_arguments(latex, expected):
    assert unicodeit.replace(latex) == expected


@pytest.mark.parametrize('latex, expected', [
    ('\\frac{1}{2} + \\frac34 = \\tfrac{5}{4}', '½ + ¾ = 5/4'),
    ('\\frac{1}{10} \\frac{ 1 }{ 7 } \\frac{0}{3}', '⅒ ⅐ ↉'),
    ('\\frac{1}{x}', '1/x'),
])
def test_vulgar_fractions(latex, expected):
    assert unicodeit.replace(latex, vulgar_fractions=True) == expected


def test_vulgar_fractions_are_optional():
    assert unicodeit.replace('\\frac{1}{2}') == '1/2'
    # in display style too, instead of a stacked fraction
    assert unicodeit.replace('x = \\frac{1}{2}', math_spacing=True, display=True,
                             vulgar_fractions=True) == 'x = ½'


@pytest.mark.parametrize('latex, expected', [
    ('a + b % the sum', 'a + b '),
    ('50\\% of x', '50% of x'),
    ('a \\\\% comment', 'a \\\\'),
    ('a\n% a whole line\nb', 'a\nb'),
    ('\\begin{bmatrix} % entries\n1 & 2 \\end{bmatrix}', '[1 2]'),
])
def test_comments(latex, expected):
    assert unicodeit.replace(latex) == expected
