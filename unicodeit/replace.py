# Copyright (c) 2010 Sven Kreiss, Kyle Cranmer
import re
import unicodedata

from .data import REPLACEMENTS, COMBININGMARKS, SUBSUPERSCRIPTS, MATHCLASSES

# Parts of the input that are converted separately (text, operator names,
# matrices, ...) are set aside as placeholder characters, one per item, from
# U+F000 in the Private Use Area. See _Converter.protect.
PLACEHOLDER_BASE = 0xF000
PLACEHOLDER_RE = re.compile('[\uf000-\uf8ff]')

# Literal braces (from \{, \lbrace, ...) and "\ " spaces are held as
# placeholders until grouping braces and typed spaces have been removed.
BRACE_PLACEHOLDERS = {'{': '\ue000', '}': '\ue001'}
SPACE_PLACEHOLDER = '\ue002'

# Commands whose arguments may be written without braces, as in \dot x, \sqrt2, or
# \frac12: an argument is then the next character or command, as in TeX.
ONE_ARGUMENT = [c[0][1:] for c in COMBININGMARKS] + [
    'sqrt', 'mathbb', 'mathbf', 'mathbfit', 'mathbold', 'mathcal', 'mathds', 'mathfrak',
    'mathit', 'mathrm', 'mathsf', 'mathsfbf', 'mathsfbfit', 'mathsfit', 'mathtt']
ARGUMENT = r'\s*(\{[^{}]*\}|\\[A-Za-z]+|[^\s{}\\])'
ONE_ARGUMENT_RE = re.compile(r'\\(' + '|'.join(ONE_ARGUMENT) + r')(?![A-Za-z])(?!\s*[{\[])' + ARGUMENT)
FRACTION_ARGUMENTS_RE = re.compile(r'\\([dt]?frac)(?![A-Za-z])' + ARGUMENT + ARGUMENT)


def _braced(argument: str) -> str:
    return argument if argument.startswith('{') else '{' + argument + '}'


def _strip_comments(f: str) -> str:
    """Remove % comments (but not \\%), and lines that held only a comment.

    LaTeX also removes the line break after a comment, but lines are kept here.
    """
    lines = []
    for line in f.split('\n'):
        stripped = COMMENT_RE.sub(r'\1', line)
        if stripped == line or stripped.strip():
            lines.append(stripped)
    return '\n'.join(lines)


def _scripts(f: str, end: int):
    """The ^ and _ scripts (at most one of each) at f[end], and where they end."""
    scripts = {}
    while (s := SCRIPT_RE.match(f, end)) and s.group(1) not in scripts:
        group = _brace_group(f, s.end()) if s.group(2) is None else None
        if group:
            scripts[s.group(1)], end = group
        elif s.group(2):
            scripts[s.group(1)], end = s.group(2), s.end()
        else:
            break
    return scripts, end


def _brace_group(f: str, i: int):
    """The contents and end of the {...} group starting at f[i] (after spaces), or None."""
    while i < len(f) and f[i].isspace():
        i += 1
    if i >= len(f) or f[i] != '{':
        return None
    depth = 0
    for j in range(i, len(f)):
        depth += {'{': 1, '}': -1}.get(f[j], 0) if f[j - 1:j] != '\\' else 0
        if depth == 0:
            return f[i + 1:j], j + 1
    return None


# A % comment to the end of the line, after any \\ pairs (so \% is a percent sign).
COMMENT_RE = re.compile(r'(?<!\\)((?:\\\\)*)%.*')

# Matrix-like environments: (left, right) delimiters, as keys of DELIMITERS.
MATRICES = {
    'matrix': ('', ''), 'smallmatrix': ('', ''), 'pmatrix': ('(', ')'),
    'bmatrix': ('[', ']'), 'Bmatrix': ('{', '}'), 'vmatrix': ('|', '|'),
    'Vmatrix': ('‖', '‖'), 'cases': ('{', ''),
}
MATRIX_RE = re.compile(r'\\begin\{(' + '|'.join(MATRICES) + r')\}(.*?)\\end\{\1\}', re.S)
# Delimiter pieces in display style: (one row, top, middle, bottom, center of a brace).
DELIMITERS = {
    '(': ('(', '⎛', '⎜', '⎝', '⎜'), ')': (')', '⎞', '⎟', '⎠', '⎟'),
    '[': ('[', '⎡', '⎢', '⎣', '⎢'), ']': (']', '⎤', '⎥', '⎦', '⎥'),
    '{': ('{', '⎧', '⎪', '⎩', '⎨'), '}': ('}', '⎫', '⎪', '⎭', '⎬'),
    '|': ('|', '|', '|', '|', '|'), '‖': ('‖', '‖', '‖', '‖', '‖'),
    '⌈': ('⌈', '⎡', '⎢', '⎢', '⎢'), '⌉': ('⌉', '⎤', '⎥', '⎥', '⎥'),
    '⌊': ('⌊', '⎢', '⎢', '⎣', '⎢'), '⌋': ('⌋', '⎥', '⎥', '⎦', '⎥'),
}

# \left and \right with their delimiters, for delimiters as tall as their contents in display style.
DELIMITER = r'\\[A-Za-z]+|\\[{}|]|[^\sA-Za-z\\{}]'
LEFT_RIGHT_RE = re.compile(r'\\(left|right)(?![A-Za-z])\s*(' + DELIMITER + ')')
LEFT_RE = re.compile(r'\\left(?![A-Za-z])\s*(' + DELIMITER + ')')
# Delimiter commands, as keys of DELIMITERS where they have tall pieces.
DELIMITER_COMMANDS = {
    '\\{': '{', '\\}': '}', '\\lbrace': '{', '\\rbrace': '}', '\\|': '‖', '\\vert': '|',
    '\\lvert': '|', '\\rvert': '|', '\\Vert': '‖', '\\lVert': '‖', '\\rVert': '‖',
    '\\lceil': '⌈', '\\rceil': '⌉', '\\lfloor': '⌊', '\\rfloor': '⌋', '.': '',
}

# Big operators and operator names whose limits go above and below in display style.
LIMITS_RE = re.compile(
    r'\\(sum|prod|coprod|bigcup|bigcap|bigsqcup|bigoplus|bigotimes|bigodot|biguplus|'
    r'bigvee|bigwedge|lim|liminf|limsup|max|min|sup|inf)(?![A-Za-z])')
# A ^ or _, then a command or character as its script; a {...} group is read with _brace_group.
SCRIPT_RE = re.compile(r'\s*([_^])\s*(\\[A-Za-z]+|[^\s{}\\])?')
OPERATOR_NAMES = {'lim', 'liminf', 'limsup', 'max', 'min', 'sup', 'inf'}

# Text, kept as typed, and operator names, written upright as op atoms.
TEXT_RE = re.compile(r'\\(?:text|textrm|textnormal|textup|textit|textbf|textsf|texttt|mbox)'
                     r'\s*\{([^{}]*)\}')
OPERATORNAME_RE = re.compile(r'\\operatorname\*?\s*\{([^{}]*)\}')
OPERATOR_NAMES_RE = re.compile(
    r'\\(arccos|arcsin|arctan|arg|cos|cosh|cot|coth|csc|deg|det|dim|exp|gcd|hom|inf|ker|lg|'
    r'lim|liminf|limsup|ln|log|max|min|Pr|sec|sin|sinh|sup|tan|tanh)(?![A-Za-z])')
# Upright words like \mathrm{and}; single symbols like \mathrm{\alpha} are in REPLACEMENTS.
MATHRM_RE = re.compile(r'\\mathrm\s*\{([A-Za-z0-9 ]{2,})\}')

# Spacing commands that only apply to math, converted before anything else.
MATH_SPACE_COMMANDS = [
    (re.compile(r'\\\\'), '\n'),                     # \\ line break
    (re.compile(r'(?<!\\)~'), '\u00a0'),             # ~ no-break space (not \~{a})
    (re.compile(r'\\ '), SPACE_PLACEHOLDER),         # "\ " space
    (re.compile(r'\\>'), '\u2004'),                  # same as \:
    (re.compile(r'\\!|\\neg(?:thin|med|thick)space(?![A-Za-z])'), ''),
]
MATH_CLASS = {chr(c): cls for cls, first, last in MATHCLASSES for c in range(first, last + 1)}
SCRIPT_CHARS = {u for _, u in SUBSUPERSCRIPTS if not u.isascii()}
# Symbols whose LaTeX ends in a letter match only whole command names, as in TeX,
# so \intf is an unknown command rather than \int followed by f.
WHOLE_COMMANDS = [re.compile(re.escape(l) + '(?![A-Za-z])') if re.search(r'\\[A-Za-z]+$', l) else None
                  for l, _ in REPLACEMENTS]
# Characters with a superscript ('^') or subscript ('_'), and groups of them like ^{12}.
SCRIPT_BASES = {kind: {l[1:] for l, _ in SUBSUPERSCRIPTS if l[0] == kind} for kind in '^_'}
SCRIPT_GROUP_RE = re.compile(r'([_^])\{([^{}]*)\}')
# A command left unconverted (with its arguments), an unconverted script, a
# whitespace run, or one character.
TOKEN_RE = re.compile(r'\\[A-Za-z]+(?:\{[^{}]*\})*|[_^]\s*(?:\{[^{}]*\}|\\[A-Za-z]+|.)|\\.|[ \t\r\f\v]+|.')
# Pairs of atom classes with space between them, as in TeX (thin, medium, and
# thick spaces all become one space).
SPACED = {
    ('ord', 'op'), ('ord', 'bin'), ('ord', 'rel'), ('ord', 'inner'),
    ('op', 'ord'), ('op', 'op'), ('op', 'rel'), ('op', 'inner'),
    ('bin', 'ord'), ('bin', 'op'), ('bin', 'open'), ('bin', 'inner'),
    ('rel', 'ord'), ('rel', 'op'), ('rel', 'open'), ('rel', 'inner'),
    ('close', 'op'), ('close', 'bin'), ('close', 'rel'), ('close', 'inner'),
    ('punct', 'ord'), ('punct', 'op'), ('punct', 'rel'), ('punct', 'open'),
    ('punct', 'close'), ('punct', 'punct'), ('punct', 'inner'),
    ('inner', 'ord'), ('inner', 'op'), ('inner', 'bin'), ('inner', 'rel'),
    ('inner', 'open'), ('inner', 'punct'), ('inner', 'inner'),
}
# In script style (limits), TeX keeps only the thin spaces next to operators.
SCRIPT_SPACED = {('ord', 'op'), ('op', 'ord'), ('op', 'op'), ('close', 'op'), ('inner', 'op')}

# Innermost \frac{..}{..} (also \dfrac and \tfrac) and \sqrt{..} (already √).
FRACTION_RE = re.compile(r'\\[dt]?frac\{([^{}]*)\}\{([^{}]*)\}')
FRACTION_START_RE = re.compile(r'\\[dt]?frac(?![A-Za-z])')
# Fractions of whole numbers, and those with one character (like ½) as \sfrac{1}{2} in REPLACEMENTS.
NUMBER_FRACTION_RE = re.compile(r'\\[dt]?frac\{\s*(\d+)\s*\}\{\s*(\d+)\s*\}')
VULGAR_FRACTIONS = {m.groups(): l for l, _ in REPLACEMENTS
                    if (m := re.fullmatch(r'\\sfrac\{(\d+)\}\{(\d+)\}', l))}
ROOT_RE = re.compile(r'([√∛∜])\{([^{}]*)\}')
# Innermost brace group, and what it may belong to: a command with arguments,
# or a ^ or _ whose group could not be converted.
GROUP_RE = re.compile(r'\{([^{}]*)\}')
COMMAND_ARGS_RE = re.compile(r'(?:\\[A-Za-z]+(?:\{[^{}]*\})*|[_^])$')


def _expand_script_group(m) -> str:
    """^{ab} -> ^a^b, unless a character in the group has no superscript (or subscript)."""
    kind, group = m.group(1), m.group(2)
    if group.strip() and all(c.isspace() or c in SCRIPT_BASES[kind] for c in group):
        return ''.join(c if c.isspace() else kind + c for c in group)
    return m.group(0)


def _width(text: str) -> int:
    """Columns that text takes in a monospaced font (combining marks take none)."""
    return sum(not unicodedata.category(c).startswith('M') for c in text)


def _pad(text: str, width: int, align: str = 'center') -> str:
    extra = width - _width(text)
    left = extra // 2 if align == 'center' else 0
    return ' ' * left + text + ' ' * (extra - left)


def _stack(blocks, align: str = 'center'):
    """Stack blocks (lists of rows) vertically, padded to the same width."""
    width = max(_width(r) for rows in blocks for r in rows)
    return [_pad(r, width, align) for rows in blocks for r in rows]


def _side_by_side(parts):
    """Join (rows, axis) parts horizontally, lining up their axis rows."""
    above = max(axis for _, axis in parts)
    below = max(len(rows) - axis - 1 for rows, axis in parts)
    out = [''] * (above + below + 1)
    for rows, axis in parts:
        width = max(_width(r) for r in rows)
        for i in range(len(out)):
            j = i - (above - axis)
            out[i] += _pad(rows[j], width, 'left') if 0 <= j < len(rows) else ' ' * width
    return out, above


def _delimiter(name: str, height: int, axis=None):
    """Rows of a delimiter for a given height, with a brace's center on the axis row.

    A delimiter without tall pieces in DELIMITERS (like ⟨) goes on the axis row alone.
    """
    if axis is None:
        axis = (height - 1) // 2
    if name not in DELIMITERS:
        return [name if i == axis else ' ' * _width(name) for i in range(height)]
    single, top, middle, bottom, center = DELIMITERS[name]
    if height == 1:
        return [single]
    rows = [top] + [middle] * (height - 2) + [bottom]
    if height > 2:
        rows[min(max(axis, 1), height - 2)] = center
    return rows


class _Converter:
    def __init__(self, math_spacing: bool, display: bool, script: bool = False, protected=None,
                 vulgar_fractions: bool = False):
        self.math_spacing = math_spacing
        self.display = display
        self.script = script  # spaced as limits, more tightly
        self.vulgar_fractions = vulgar_fractions
        # (text, math class, axis row or None) per placeholder, shared with nested
        # converters so that placeholders can be converted again inside them
        self.protected = [] if protected is None else protected

    def protect(self, text: str, cls: str, axis=None) -> str:
        """A placeholder for text that is already converted.

        Text with an axis is a block of rows (joined by newlines) whose axis row
        lines up with the line around it, like a fraction bar.
        """
        self.protected.append((text, cls, axis))
        return chr(PLACEHOLDER_BASE + len(self.protected) - 1)

    def item(self, char: str):
        return self.protected[ord(char) - PLACEHOLDER_BASE] if PLACEHOLDER_RE.match(char) else None

    def restore(self, f: str) -> str:
        return PLACEHOLDER_RE.sub(lambda m: self.item(m.group(0))[0], f)

    def nested(self, f: str, script: bool = False, display=None):
        """Convert f on its own (a matrix cell, or a limit in script style) as (rows, axis).

        A newline in f is a space, as in LaTeX; only the input's own lines stay lines.
        """
        return _Converter(self.math_spacing, self.display if display is None else display,
                          script, self.protected, self.vulgar_fractions).convert(f.replace('\n', ' '))

    def operand(self, part: str) -> str:
        """Wrap a fraction part or root argument in parentheses unless it is a single term.

        A single term is one character (with any combining marks), or letters,
        digits, combining marks, primes, '.' and '!', after an optional root
        sign, and optionally followed by one parenthesized group as in f(x) or
        (a + b).
        """
        part = part.strip()
        head = re.sub(r'\([^()]*\)$', '', self.restore(part)).lstrip('√∛∜')
        if sum(not unicodedata.category(c).startswith('M') for c in head) <= 1 or all(
                c.isalnum() or unicodedata.category(c).startswith('M') or c in ".′'!" for c in head):
            return part
        return f'({part})'

    def display_layout(self, f: str) -> str:
        """In display style, lay out fractions, \\left ... \\right pairs, limits, and
        matrices over several lines, outermost first, so each can set the style of
        what is inside it."""
        out = ''
        position = 0
        while True:
            starts = [m for m in (regex.search(f, position) for regex in (
                FRACTION_START_RE, LEFT_RE, LIMITS_RE, MATRIX_RE)) if m]
            if not starts:
                return out + f[position:]
            m = min(starts, key=lambda m: m.start())
            if m.re is FRACTION_START_RE:
                laid_out = self.stacked_fraction(f, m)
            elif m.re is LEFT_RE:
                laid_out = self.left_right(f, m)
            elif m.re is LIMITS_RE:
                laid_out = self.limits(f, m)
            else:
                laid_out = self.matrix(m.group(1), m.group(2)), m.end()
            if laid_out is None:  # not complete: keep the command as it is
                laid_out = m.group(0), m.end()
            elif m.re is not LIMITS_RE:
                laid_out = self.block_scripts(f, *laid_out)
            out += f[position:m.start()] + laid_out[0]
            position = laid_out[1]

    def block_scripts(self, f: str, text: str, end: int):
        """A superscript after a block of several rows goes on its top row, and a subscript on
        its bottom row, as TeX raises and lowers them. Returns the block and where it ends."""
        item = self.item(text) if len(text) == 1 else None
        if not item or item[2] is None or '\n' not in item[0]:
            return text, end
        scripts, scripts_end = _scripts(f, end)
        if not scripts:
            return text, end
        rows = item[0].split('\n')
        width = max(_width(r) for r in rows)
        # Converted like x^{...} without the x, so that what can't be raised stays as ^{...}.
        sup, sub = ('\n'.join(self.nested(kind + '{' + scripts[kind] + '}', display=False)[0])
                    if kind in scripts else '' for kind in '^_')
        column = [sup] + [''] * (len(rows) - 2) + [sub]
        rows = [_pad(r, width, 'left') + c for r, c in zip(rows, column)]
        return self.protect('\n'.join(r.rstrip() for r in rows), item[1], item[2]), scripts_end

    def stacked_fraction(self, f: str, m):
        """A fraction over several lines, with its parts in inline style, and where it ends."""
        numerator = _brace_group(f, m.end())
        denominator = numerator and _brace_group(f, numerator[1])
        if not denominator:
            return None
        return self.stacked(numerator[0], denominator[0]), denominator[1]

    def stacked(self, numerator: str, denominator: str) -> str:
        parts = [self.nested(part, display=False)[0] for part in (numerator, denominator)]
        width = max(_width(r) for rows in parts for r in rows) + 2
        rows = [_pad(r, width) for r in parts[0]] + ['─' * width] + [_pad(r, width) for r in parts[1]]
        return self.protect('\n'.join(rows), 'inner', len(parts[0]))

    def matrix(self, env: str, body: str) -> str:
        """A matrix environment, with each cell converted on its own."""
        # Empty rows count, as in LaTeX, except after a \\ that ends the last row.
        rows = re.split(r'\\\\', body)
        if len(rows) > 1 and not rows[-1].strip():
            rows.pop()
        cells = [[self.nested(c) for c in re.split(r'(?<!\\)&', r)] for r in rows]
        if not cells:
            return ''
        left, right = MATRICES[env]
        columns = max(len(r) for r in cells)
        cells = [r + [([''], 0)] * (columns - len(r)) for r in cells]
        if not self.display:
            separator = ', ' if env == 'cases' else ' '
            text = '; '.join(separator.join('\n'.join(rows).strip() for rows, _ in r).strip() for r in cells)
            return self.protect(left + text + right, 'inner')

        widths = [max(_width(line) for r in cells for line in r[j][0]) for j in range(columns)]
        align = 'left' if env == 'cases' else 'center'
        lines = []
        for r in cells:
            padded = [([_pad(line, w, align) for line in rows], axis) for (rows, axis), w in zip(r, widths)]
            joined = []
            for i, part in enumerate(padded):
                joined += [part] if i == 0 else [(['  '], 0), part]
            lines += _side_by_side(joined)[0]
        lines = [l + line + r for l, line, r in zip(
            _delimiter(left, len(lines)), lines, _delimiter(right, len(lines)))]
        return self.protect('\n'.join(lines), 'inner', (len(lines) - 1) // 2)

    def left_right(self, f: str, opening):
        """A \\left ... \\right pair with delimiters as tall as their contents, and where it ends."""
        depth = 0
        for m in LEFT_RIGHT_RE.finditer(f, opening.start()):
            depth += 1 if m.group(1) == 'left' else -1
            if depth == 0:
                return self.tall_delimiters(opening.group(1), f[opening.end():m.start()], m.group(2)), m.end()
        return None

    def tall_delimiters(self, left: str, contents: str, right: str) -> str:
        """Delimiters as tall as the contents between them, which are converted on their own."""
        rows, axis = self.nested(contents)
        if len(rows) == 1:
            # one row: plain delimiters, converted along with the rest of the line
            return '\\left' + left + contents + '\\right' + right
        width = max(_width(r) for r in rows)
        rows = [_pad(r, width, 'left') for r in rows]
        sides = []
        for d in (left, right):
            d = DELIMITER_COMMANDS.get(d, d)
            sides.append(_delimiter(d if d in DELIMITERS or not d.startswith('\\') else replace(d),
                                    len(rows), axis))
        return self.protect('\n'.join(l + r + rr for l, r, rr in zip(sides[0], rows, sides[1])),
                            'inner', axis)

    def limits(self, f: str, m):
        """\\sum, \\lim, ... with their limits (in inline style) above and below, and where they end."""
        scripts, end = _scripts(f, m.end())
        if not scripts:
            return None
        name = m.group(1)
        symbol = name if name in OPERATOR_NAMES else self.restore(replace('\\' + name))
        blocks = [self.nested(scripts['^'], script=True, display=False)[0]] if '^' in scripts else []
        blocks += [[symbol]]
        blocks += [self.nested(scripts['_'], script=True, display=False)[0]] if '_' in scripts else []
        axis = len(blocks[0]) if '^' in scripts else 0
        return self.protect('\n'.join(_stack(blocks)), 'op', axis), end

    def atoms(self, line: str):
        """Split a line into [text, class] atoms with TeX's math classes."""
        atoms = []
        for m in TOKEN_RE.finditer(line):
            t = m.group(0)
            if t[0] in ' \t\r\f\v':
                continue  # spaces typed in math are ignored
            if t[0] == '\\' and len(t) > 1:
                atoms.append([t, 'raw'])
            elif t[0] in '_^' and atoms and atoms[-1][1] != 'space':
                atoms[-1][0] += re.sub(r'\s+', '', t)  # an unconverted script stays on its base
            elif atoms and atoms[-1][1] != 'space' and (
                    MATH_CLASS.get(t) == 'attach' or t in SCRIPT_CHARS
                    or unicodedata.category(t).startswith('M')):
                atoms[-1][0] += t
            elif self.item(t):
                atoms.append([t, self.item(t)[1]])
            else:
                atoms.append([t, MATH_CLASS.get(t, 'ord')])

        # A binary operator with nothing to combine on one side is ordinary, as in -x.
        previous = None
        for atom in atoms:
            if atom[1] == 'space':
                continue
            if atom[1] == 'bin' and (previous is None
                                     or previous[1] in ('bin', 'op', 'rel', 'open', 'punct')):
                atom[1] = 'ord'
            if atom[1] in ('rel', 'close', 'punct') and previous is not None and previous[1] == 'bin':
                previous[1] = 'ord'
            previous = atom
        if previous is not None and previous[1] == 'bin':
            previous[1] = 'ord'
        return atoms

    def space(self, line: str) -> str:
        """Space a line of converted math the way TeX does, ignoring typed spaces."""
        out = ''
        previous = None
        for atom in self.atoms(line):
            if previous is not None and 'space' not in (previous[1], atom[1]):
                left = 'ord' if previous[1] == 'raw' else previous[1]
                right = 'ord' if atom[1] == 'raw' else atom[1]
                # An unconverted command keeps the space that ends it, as in \foo x.
                ends_command = (previous[1] == 'raw' and re.search('[A-Za-z]$', previous[0])
                                and re.match('[A-Za-z0-9]', atom[0]))
                if (left, right) in (SCRIPT_SPACED if self.script else SPACED) or ends_command:
                    out += ' '
            out += atom[0]
            previous = atom
        return out

    def layout(self, line: str):
        """Restore the placeholders in a line, setting blocks side by side, as (rows, axis)."""
        parts = []
        text = ''
        for c in line:
            item = self.item(c)
            if item and item[2] is not None:
                parts += [([text], 0), (item[0].split('\n'), item[2])]
                text = ''
            else:
                text += self.restore(c)
        if not parts:
            return [text], 0
        rows, axis = _side_by_side(parts + [([text], 0)])
        return [r.rstrip() for r in rows], axis

    def convert(self, f: str):
        """Convert f, returning (rows, axis) for all its lines."""
        f = ONE_ARGUMENT_RE.sub(lambda m: '\\' + m.group(1) + _braced(m.group(2)), f)
        f = FRACTION_ARGUMENTS_RE.sub(
            lambda m: '\\' + m.group(1) + _braced(m.group(2)) + _braced(m.group(3)), f)
        if self.vulgar_fractions:
            f = NUMBER_FRACTION_RE.sub(
                lambda m: VULGAR_FRACTIONS.get((m.group(1), m.group(2)), m.group(0)), f)
        if self.display:
            f = self.display_layout(f)
        f = MATRIX_RE.sub(lambda m: self.matrix(m.group(1), m.group(2)), f)
        f = TEXT_RE.sub(lambda m: self.protect(m.group(1), 'ord'), f)
        f = OPERATORNAME_RE.sub(lambda m: self.protect(re.sub(r'\s+', '', m.group(1)), 'op'), f)
        f = OPERATOR_NAMES_RE.sub(lambda m: self.protect(m.group(1), 'op'), f)
        f = MATHRM_RE.sub(lambda m: self.protect(re.sub(r'\s+', '', m.group(1)), 'ord'), f)
        if self.math_spacing:
            for regex, space in MATH_SPACE_COMMANDS:
                f = regex.sub(space, f)
        # Roots with an index other than 3 or 4 (which are symbols): \sqrt[n] -> ⁿ√
        f = re.sub(r'\\sqrt\s*\[([^\]]*)\]',
                   lambda m: '\\sqrt[' + m.group(1).strip() + ']' if m.group(1).strip() in ('3', '4')
                   else '^{' + m.group(1).strip() + '}\\sqrt', f)

        # Catch cases like \not\subset and \not\in and convert them to
        # use the combining character slash as in \slash{\subset}
        f = re.sub(r'\\not(\\[A-z]+)', r'\\slash{\1}', f)
        # Remove delimiter sizing, which plain text can't show: \left( -> ( and
        # \bigl\{ -> \{. The null delimiters \left. and \right. disappear.
        f = re.sub(r'\\(?:left|right)\s*\.', '', f)
        f = re.sub(r'\\(?:left|right|middle|[Bb]igg?[lrm]?)(?![A-Za-z])\s*', '', f)
        # escape combining marks with a space after the backslash
        for c in COMBININGMARKS:
            f = f.replace(c[0] + '{', '\\ ' + c[0][1:] + '{')

        # replace
        for r, whole_command in zip(REPLACEMENTS, WHOLE_COMMANDS):
            u = BRACE_PLACEHOLDERS.get(r[1], r[1])
            if r[0] in f:
                f = whole_command.sub(lambda _: u, f) if whole_command else f.replace(r[0], u)

            # check whether it was escaped for combining marks but has empty braces
            if r[0].endswith('{}'):
                f = f.replace('\\ ' + r[0][1:], u)

        # expand groups of sub- and superscripts, _{01234} and ^{01234}, if every
        # character in them has one (spaces stay as they are)
        f = SCRIPT_GROUP_RE.sub(_expand_script_group, f)

        # now replace subsuperscripts
        for r in SUBSUPERSCRIPTS:
            f = f.replace(r[0], r[1])

        # process combining marks first
        for c in COMBININGMARKS:
            escaped_latex = f'\\ {c[0][1:]}{{'
            while escaped_latex in f:
                i = f.index(escaped_latex)
                if len(f) <= i + len(escaped_latex):
                    # incomplete: unescape and continue
                    f = f[:i] + c[0] + '{'
                    continue

                combined_char = f[i + len(escaped_latex)]

                remainder = ''
                if len(f) >= i + len(escaped_latex) + 2:
                    remainder = f[i + len(escaped_latex) + 2:]

                f = f[:i] + combined_char + c[1] + remainder

        # Fractions, \frac{a + b}{c} -> (a + b)/c or stacked in display style,
        # roots with parentheses unless single terms, √(1 + 2), and grouping
        # braces removed, {1 + 2} -> 1 + 2. Braces holding arguments of unknown
        # commands stay, as in \foo{abc}, and so do unconverted script groups,
        # as in x^{#}. Repeat for nested groups.
        while True:
            previous = f
            f = FRACTION_RE.sub(lambda m: self.operand(m.group(1)) + '/' + self.operand(m.group(2)), f)
            f = ROOT_RE.sub(lambda m: m.group(1) + self.operand(m.group(2)), f)
            f = GROUP_RE.sub(
                lambda m: m.group(0) if COMMAND_ARGS_RE.search(m.string, 0, m.start()) else m.group(1), f)
            if f == previous:
                break

        rows = []
        axis = 0
        for line in f.split('\n'):
            if self.math_spacing:
                line = self.space(line)
            line_rows, line_axis = self.layout(line)
            if not rows:
                axis = line_axis
            rows += line_rows
        for brace, placeholder in BRACE_PLACEHOLDERS.items():
            rows = [r.replace(placeholder, brace) for r in rows]
        return [r.replace(SPACE_PLACEHOLDER, ' ') for r in rows], axis


def replace(f: str, math_spacing: bool = False, display: bool = False,
            vulgar_fractions: bool = False) -> str:
    """Convert LaTeX to Unicode.

    With math_spacing, f is treated as math: typed spaces are ignored, and space
    goes around operators and relations and after punctuation, as in TeX.
    Spacing commands like ~ and \\quad, and line breaks, are kept.

    With display, the output is laid out like display math, over several lines:
    fractions are stacked, matrices have tall brackets, and the limits of sums
    go above and below. Otherwise all of these are written on one line.

    With vulgar_fractions, fractions that Unicode has as one character, like
    \\frac{1}{2}, are written as that character (½).
    """
    return '\n'.join(_Converter(math_spacing, display,
                                vulgar_fractions=vulgar_fractions).convert(_strip_comments(f))[0])
