import unicodeit


def test_check_combining():
    # https://github.com/svenkreiss/unicodeit/issues/48
    assert unicodeit.replace('\\check{z}') == 'z\u030C'
    assert unicodeit.replace('\\check{}') == 'ˇ'


def test_angle_brackets():
    # https://github.com/svenkreiss/unicodeit/issues/32
    assert unicodeit.replace('\\langle x \\rangle') == '⟨ x ⟩'
