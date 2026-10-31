import pytest

import unicodeit


def test_superscript_12():
    assert unicodeit.replace('a^{12}') == 'a¹²'


def test_superscript_minus1():
    assert unicodeit.replace('cm^{-1}') == 'cm⁻¹'


def test_subscript_12():
    assert unicodeit.replace('a_{12}') == 'a₁₂'


def test_subscript_minus1():
    assert unicodeit.replace('cm_{-1}') == 'cm₋₁'


def test_superscript_top():
    assert unicodeit.replace('M^\\top') == 'Mᵀ'
    assert unicodeit.replace('M^{\\top}') == 'Mᵀ'
    assert unicodeit.replace('M^\\intercal') == 'Mᵀ'


def test_superscript_prime():
    assert unicodeit.replace("x^'") == 'x′'
    assert unicodeit.replace('x^\\prime') == 'x′'
    assert unicodeit.replace("\\eta^{(')}") == 'η⁽′⁾'


@pytest.mark.parametrize('latex, expected', [
    # spaces in a group don't stop it from being converted
    ('a^{\\int f(x) dx}', 'aᶴ ᶠ⁽ˣ⁾ ᵈˣ'),
    ('a^{x + y}', 'aˣ ⁺ ʸ'),
    # but a character without a script does
    ('x_{i,j}', 'x_{i,j}'),
    ('a^{x/2}', 'a^{x/2}'),
    # '.' has a superscript, for exponents like -0.5
    ('D^{-0.5}', 'D⁻⁰ᐧ⁵'),
    ('a_{ij}', 'aᵢⱼ'),
])
def test_script_groups(latex, expected):
    assert unicodeit.replace(latex) == expected


def test_script_groups_in_math():
    # TeX doesn't space operators in scripts, and typed spaces are ignored
    assert unicodeit.replace('a^{\\int f(x) dx}', math_spacing=True) == 'aᶴᶠ⁽ˣ⁾ᵈˣ'
    assert unicodeit.replace('a^{x + y}', math_spacing=True) == 'aˣ⁺ʸ'
