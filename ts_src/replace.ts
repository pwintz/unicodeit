// Copyright (c) 2010-2020 Sven Kreiss, Kyle Cranmer

import { combiningmarks, mathclasses, replacements, subsuperscripts } from './data';

export interface ReplaceOptions {
    // Treat the input as math: typed spaces are ignored, and space goes around
    // operators and relations and after punctuation, as in TeX. Spacing
    // commands like ~ and \quad, and line breaks, are kept.
    mathSpacing?: boolean;
    // Lay the output out like display math, over several lines: fractions are
    // stacked, matrices have tall brackets, and the limits of sums go above and
    // below. Otherwise all of these are written on one line.
    display?: boolean;
    // Write fractions that Unicode has as one character, like \frac{1}{2}, as that character (½).
    vulgarFractions?: boolean;
}

// Rows of text, with the row that lines up with the text around it (like a fraction bar).
type Block = [string[], number];
// Converted text set aside as a placeholder: text, math class, and the axis row
// if it is a block of rows joined by newlines.
type Protected = [string, string, number | null];

// Parts of the input that are converted separately (text, operator names,
// matrices, ...) are set aside as placeholder characters, one per item, from
// U+F000 in the Private Use Area. See Converter.protect.
const PLACEHOLDER_BASE = 0xF000;
const PLACEHOLDER_RE = /[\uF000-\uF8FF]/g;

// Literal braces (from \{, \lbrace, ...) and "\ " spaces are held as
// placeholders until grouping braces and typed spaces have been removed.
const BRACE_PLACEHOLDERS: Record<string, string> = { '{': '\uE000', '}': '\uE001' };
const SPACE_PLACEHOLDER = '\uE002';

// Commands whose arguments may be written without braces, as in \dot x, \sqrt2, or
// \frac12: an argument is then the next character or command, as in TeX.
const ONE_ARGUMENT = [...combiningmarks.map((c) => c[0].slice(1)),
    'sqrt', 'mathbb', 'mathbf', 'mathbfit', 'mathbold', 'mathcal', 'mathds', 'mathfrak',
    'mathit', 'mathrm', 'mathsf', 'mathsfbf', 'mathsfbfit', 'mathsfit', 'mathtt'];
const ARGUMENT = String.raw`\s*(\{[^{}]*\}|\\[A-Za-z]+|[^\s{}\\])`;
const ONE_ARGUMENT_RE = new RegExp(String.raw`\\(` + ONE_ARGUMENT.join('|') + String.raw`)(?![A-Za-z])(?!\s*[{\[])` + ARGUMENT, 'g');
const FRACTION_ARGUMENTS_RE = new RegExp(String.raw`\\([dt]?frac)(?![A-Za-z])` + ARGUMENT + ARGUMENT, 'g');

function braced(argument: string): string {
    return argument.startsWith('{') ? argument : '{' + argument + '}';
}

// Remove % comments (but not \%), and lines that held only a comment. LaTeX also removes the
// line break after a comment, but lines are kept here.
function stripComments(f: string): string {
    return f.split('\n').flatMap((line) => {
        const stripped = line.replace(COMMENT_RE, '$1');
        return stripped == line || stripped.trim() ? [stripped] : [];
    }).join('\n');
}

// The ^ and _ scripts (at most one of each) at f[end], and where they end.
function parseScripts(f: string, end: number): [Record<string, string>, number] {
    const scripts: Record<string, string> = {};
    for (;;) {
        SCRIPT_RE.lastIndex = end;
        const s = SCRIPT_RE.exec(f);
        if (!s || s[1] in scripts) break;
        const group = s[2] === undefined ? braceGroup(f, SCRIPT_RE.lastIndex) : null;
        if (group) [scripts[s[1]], end] = group;
        else if (s[2]) [scripts[s[1]], end] = [s[2], SCRIPT_RE.lastIndex];
        else break;
    }
    return [scripts, end];
}

// The contents and end of the {...} group starting at f[i] (after spaces), or null.
function braceGroup(f: string, i: number): [string, number] | null {
    while (i < f.length && /\s/.test(f[i])) i++;
    if (f[i] != '{') return null;
    let depth = 0;
    for (let j = i; j < f.length; j++) {
        if (f[j - 1] != '\\') depth += f[j] == '{' ? 1 : f[j] == '}' ? -1 : 0;
        if (depth == 0) return [f.slice(i + 1, j), j + 1];
    }
    return null;
}

// A % comment to the end of the line, after any \\ pairs (so \% is a percent sign).
const COMMENT_RE = /(?<!\\)((?:\\\\)*)%.*/;

// Matrix-like environments: [left, right] delimiters, as keys of DELIMITERS.
const MATRICES: Record<string, [string, string]> = {
    'matrix': ['', ''], 'smallmatrix': ['', ''], 'pmatrix': ['(', ')'],
    'bmatrix': ['[', ']'], 'Bmatrix': ['{', '}'], 'vmatrix': ['|', '|'],
    'Vmatrix': ['‖', '‖'], 'cases': ['{', ''],
};
const MATRIX_RE = new RegExp('\\\\begin\\{(' + Object.keys(MATRICES).join('|') + ')\\}([\\s\\S]*?)\\\\end\\{\\1\\}', 'g');
// Delimiter pieces in display style: [one row, top, middle, bottom, center of a brace].
const DELIMITERS: Record<string, string[]> = {
    '(': ['(', '⎛', '⎜', '⎝', '⎜'], ')': [')', '⎞', '⎟', '⎠', '⎟'],
    '[': ['[', '⎡', '⎢', '⎣', '⎢'], ']': [']', '⎤', '⎥', '⎦', '⎥'],
    '{': ['{', '⎧', '⎪', '⎩', '⎨'], '}': ['}', '⎫', '⎪', '⎭', '⎬'],
    '|': ['|', '|', '|', '|', '|'], '‖': ['‖', '‖', '‖', '‖', '‖'],
    '⌈': ['⌈', '⎡', '⎢', '⎢', '⎢'], '⌉': ['⌉', '⎤', '⎥', '⎥', '⎥'],
    '⌊': ['⌊', '⎢', '⎢', '⎣', '⎢'], '⌋': ['⌋', '⎥', '⎥', '⎦', '⎥'],
};

// \left and \right with their delimiters, for delimiters as tall as their contents in display style.
const DELIMITER = String.raw`\\[A-Za-z]+|\\[{}|]|[^\sA-Za-z\\{}]`;
const LEFT_RIGHT_RE = new RegExp(String.raw`\\(left|right)(?![A-Za-z])\s*(` + DELIMITER + ')', 'g');
const LEFT_RE = new RegExp(String.raw`\\left(?![A-Za-z])\s*(` + DELIMITER + ')', 'g');
// Delimiter commands, as keys of DELIMITERS where they have tall pieces.
const DELIMITER_COMMANDS: Record<string, string> = {
    '\\{': '{', '\\}': '}', '\\lbrace': '{', '\\rbrace': '}', '\\|': '‖', '\\vert': '|',
    '\\lvert': '|', '\\rvert': '|', '\\Vert': '‖', '\\lVert': '‖', '\\rVert': '‖',
    '\\lceil': '⌈', '\\rceil': '⌉', '\\lfloor': '⌊', '\\rfloor': '⌋', '.': '',
};

// Big operators and operator names whose limits go above and below in display style.
const LIMITS_RE = /\\(sum|prod|coprod|bigcup|bigcap|bigsqcup|bigoplus|bigotimes|bigodot|biguplus|bigvee|bigwedge|lim|liminf|limsup|max|min|sup|inf)(?![A-Za-z])/g;
// A ^ or _, then a command or character as its script; a {...} group is read with braceGroup.
const SCRIPT_RE = /\s*([_^])\s*(\\[A-Za-z]+|[^\s{}\\])?/y;
const OPERATOR_NAMES = new Set(['lim', 'liminf', 'limsup', 'max', 'min', 'sup', 'inf']);

// Text, kept as typed, and operator names, written upright as op atoms.
const TEXT_RE = /\\(?:text|textrm|textnormal|textup|textit|textbf|textsf|texttt|mbox)\s*\{([^{}]*)\}/g;
const OPERATORNAME_RE = /\\operatorname\*?\s*\{([^{}]*)\}/g;
const OPERATOR_NAMES_RE = /\\(arccos|arcsin|arctan|arg|cos|cosh|cot|coth|csc|deg|det|dim|exp|gcd|hom|inf|ker|lg|lim|liminf|limsup|ln|log|max|min|Pr|sec|sin|sinh|sup|tan|tanh)(?![A-Za-z])/g;
// Upright words like \mathrm{and}; single symbols like \mathrm{\alpha} are in replacements.
const MATHRM_RE = /\\mathrm\s*\{([A-Za-z0-9 ]{2,})\}/g;

// Spacing commands that only apply to math, converted before anything else.
const MATH_SPACE_COMMANDS: [RegExp, string][] = [
    [/\\\\/g, '\n'],                      // \\ line break
    [/(?<!\\)~/g, '\u00A0'],              // ~ no-break space (not \~{a})
    [/\\ /g, SPACE_PLACEHOLDER],          // "\ " space
    [/\\>/g, '\u2004'],                   // same as \:
    [/\\!|\\neg(?:thin|med|thick)space(?![A-Za-z])/g, ''],
];
const MATH_CLASS = new Map<string, string>();
for (const [cls, first, last] of mathclasses) {
    for (let c = first; c <= last; c++) MATH_CLASS.set(String.fromCodePoint(c), cls);
}
const SCRIPT_CHARS = new Set(subsuperscripts.map((r) => r[1]).filter((u) => !/^[\x00-\x7F]*$/.test(u)));
// A command left unconverted (with its arguments), an unconverted script, a
// whitespace run, or one character.
const TOKEN_RE = /\\[A-Za-z]+(?:\{[^{}]*\})*|[_^]\s*(?:\{[^{}]*\}|\\[A-Za-z]+|.)|\\.|[ \t\r\f\v]+|./gu;
// Pairs of atom classes with space between them, as in TeX (thin, medium, and
// thick spaces all become one space).
const SPACED = new Set([
    'ord op', 'ord bin', 'ord rel', 'ord inner',
    'op ord', 'op op', 'op rel', 'op inner',
    'bin ord', 'bin op', 'bin open', 'bin inner',
    'rel ord', 'rel op', 'rel open', 'rel inner',
    'close op', 'close bin', 'close rel', 'close inner',
    'punct ord', 'punct op', 'punct rel', 'punct open',
    'punct close', 'punct punct', 'punct inner',
    'inner ord', 'inner op', 'inner bin', 'inner rel',
    'inner open', 'inner punct', 'inner inner',
]);
// In script style (limits), TeX keeps only the thin spaces next to operators.
const SCRIPT_SPACED = new Set(['ord op', 'op ord', 'op op', 'close op', 'inner op']);

// Symbols whose LaTeX ends in a letter match only whole command names, as in TeX,
// so \intf is an unknown command rather than \int followed by f.
const WHOLE_COMMANDS = replacements.map(([latex]) => /\\[A-Za-z]+$/.test(latex)
    ? new RegExp(latex.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '(?![A-Za-z])', 'g') : null);
// Characters with a superscript ('^') or subscript ('_'), and groups of them like ^{12}.
const SCRIPT_BASES: Record<string, Set<string>> = { '^': new Set(), '_': new Set() };
for (const [latex] of subsuperscripts) SCRIPT_BASES[latex[0]].add(latex.slice(1));
const SCRIPT_GROUP_RE = /([_^])\{([^{}]*)\}/g;

// Innermost \frac{..}{..} (also \dfrac and \tfrac) and \sqrt{..} (already √).
const FRACTION_RE = /\\[dt]?frac\{([^{}]*)\}\{([^{}]*)\}/g;
const FRACTION_START_RE = /\\[dt]?frac(?![A-Za-z])/g;
// Fractions of whole numbers, and those with one character (like ½) as \sfrac{1}{2} in replacements.
const NUMBER_FRACTION_RE = /\\[dt]?frac\{\s*(\d+)\s*\}\{\s*(\d+)\s*\}/g;
const VULGAR_FRACTIONS = new Map(replacements.flatMap(([latex]) => {
    const m = latex.match(/^\\sfrac\{(\d+)\}\{(\d+)\}$/);
    return m ? [[m[1] + '/' + m[2], latex] as [string, string]] : [];
}));
const ROOT_RE = /([√∛∜])\{([^{}]*)\}/g;
// Innermost brace group, and what it may belong to: a command with arguments,
// or a ^ or _ whose group could not be converted.
const GROUP_RE = /\{([^{}]*)\}/g;
const COMMAND_ARGS_RE = /(?:\\[A-Za-z]+(?:\{[^{}]*\})*|[_^])$/;
// A single term: one character (with any combining marks), or letters, digits,
// combining marks, primes, '.' and '!', after an optional root sign, and
// optionally followed by one parenthesized group as in f(x) or (a + b).
const SINGLE_TERM_RE = /^[√∛∜]?(?:[^\p{M}]\p{M}*|[\p{L}\p{N}\p{M}.′'!]*(\([^()]*\))?)$/u;


// Columns that text takes in a monospaced font (combining marks take none).
function width(text: string): number {
    let n = 0;
    for (const c of text) if (!/\p{M}/u.test(c)) n++;
    return n;
}

function pad(text: string, w: number, align: 'center' | 'left' = 'center'): string {
    const extra = w - width(text);
    const left = align == 'center' ? Math.floor(extra / 2) : 0;
    return ' '.repeat(left) + text + ' '.repeat(extra - left);
}

// Stack blocks (lists of rows) vertically, padded to the same width.
function stack(blocks: string[][], align: 'center' | 'left' = 'center'): string[] {
    const w = Math.max(...blocks.flat().map(width));
    return blocks.flat().map((r) => pad(r, w, align));
}

// Join parts horizontally, lining up their axis rows.
function sideBySide(parts: Block[]): Block {
    const above = Math.max(...parts.map(([, axis]) => axis));
    const below = Math.max(...parts.map(([rows, axis]) => rows.length - axis - 1));
    const out: string[] = new Array(above + below + 1).fill('');
    for (const [rows, axis] of parts) {
        const w = Math.max(...rows.map(width));
        for (let i = 0; i < out.length; i++) {
            const j = i - (above - axis);
            out[i] += 0 <= j && j < rows.length ? pad(rows[j], w, 'left') : ' '.repeat(w);
        }
    }
    return [out, above];
}

// Rows of a delimiter for a given height, with a brace's center on the axis row. A
// delimiter without tall pieces in DELIMITERS (like ⟨) goes on the axis row alone.
function delimiter(name: string, height: number, axis = Math.floor((height - 1) / 2)): string[] {
    if (!(name in DELIMITERS)) {
        return [...new Array(height).keys()].map((i) => i == axis ? name : ' '.repeat(width(name)));
    }
    const [single, top, middle, bottom, center] = DELIMITERS[name];
    if (height == 1) return [single];
    const rows = [top, ...new Array(height - 2).fill(middle), bottom];
    if (height > 2) rows[Math.min(Math.max(axis, 1), height - 2)] = center;
    return rows;
}


class Converter {
    constructor(
        private mathSpacing: boolean,
        private display: boolean,
        private script = false,   // spaced as limits, more tightly
        // Converted text per placeholder, shared with nested converters so that
        // placeholders can be converted again inside them.
        private items: Protected[] = [],
        private vulgarFractions = false,
    ) {}

    // A placeholder for text that is already converted. Text with an axis is a
    // block of rows (joined by newlines) whose axis row lines up with the line
    // around it, like a fraction bar.
    protect(text: string, cls: string, axis: number | null = null): string {
        this.items.push([text, cls, axis]);
        return String.fromCharCode(PLACEHOLDER_BASE + this.items.length - 1);
    }

    item(char: string): Protected | undefined {
        const code = char.charCodeAt(0);
        return char.length == 1 && code >= PLACEHOLDER_BASE && code <= 0xF8FF
            ? this.items[code - PLACEHOLDER_BASE] : undefined;
    }

    restore(f: string): string {
        return f.replace(PLACEHOLDER_RE, (c) => this.item(c)![0]);
    }

    // Convert f on its own (a matrix cell, or a limit in script style).
    // A newline in f is a space, as in LaTeX; only the input's own lines stay lines.
    nested(f: string, script = false, display = this.display): Block {
        return new Converter(this.mathSpacing, display, script, this.items, this.vulgarFractions)
            .convert(f.replace(/\n/g, ' '));
    }

    // Wrap a fraction part or root argument in parentheses unless it is a single term.
    operand(part: string): string {
        part = part.trim();
        return SINGLE_TERM_RE.test(this.restore(part)) ? part : `(${part})`;
    }

    // A matrix environment, with each cell converted on its own.
    matrix(env: string, body: string): string {
        // Empty rows count, as in LaTeX, except after a \\ that ends the last row.
        const rows = body.split('\\\\');
        if (rows.length > 1 && !rows[rows.length - 1].trim()) rows.pop();
        let cells = rows.map((r) => r.split(/(?<!\\)&/).map((c) => this.nested(c)));
        if (!cells.length) return '';
        const [left, right] = MATRICES[env];
        const columns = Math.max(...cells.map((r) => r.length));
        cells = cells.map((r) => [...r, ...new Array(columns - r.length).fill([[''], 0])]);
        if (!this.display) {
            const separator = env == 'cases' ? ', ' : ' ';
            const text = cells.map((r) => r.map(([rows]) => rows.join('\n').trim()).join(separator).trim()).join('; ');
            return this.protect(left + text + right, 'inner');
        }

        const widths = [...new Array(columns).keys()].map(
            (j) => Math.max(...cells.flatMap((r) => r[j][0].map(width))));
        const align = env == 'cases' ? 'left' : 'center';
        let lines: string[] = [];
        for (const r of cells) {
            const joined: Block[] = [];
            r.forEach(([rows, axis], j) => {
                if (j > 0) joined.push([['  '], 0]);
                joined.push([rows.map((line) => pad(line, widths[j], align)), axis]);
            });
            lines = lines.concat(sideBySide(joined)[0]);
        }
        const l = delimiter(left, lines.length);
        const rr = delimiter(right, lines.length);
        lines = lines.map((line, i) => l[i] + line + rr[i]);
        return this.protect(lines.join('\n'), 'inner', Math.floor((lines.length - 1) / 2));
    }

    // In display style, lay out fractions, \left ... \right pairs, limits, and matrices over
    // several lines, outermost first, so each can set the style of what is inside it.
    displayLayout(f: string): string {
        let out = '';
        let position = 0;
        for (;;) {
            const starts = [FRACTION_START_RE, LEFT_RE, LIMITS_RE, MATRIX_RE].map((regex) => {
                regex.lastIndex = position;
                const m = regex.exec(f);
                return m && { regex, m };
            }).filter((s) => s !== null);
            if (!starts.length) return out + f.slice(position);
            const { regex, m } = starts.reduce((a, b) => b.m.index < a.m.index ? b : a);
            let laidOut =
                regex === FRACTION_START_RE ? this.stackedFraction(f, m)
                : regex === LEFT_RE ? this.leftRight(f, m)
                : regex === LIMITS_RE ? this.limits(f, m)
                : [this.matrix(m[1], m[2]), m.index + m[0].length] as [string, number];
            // not complete: keep the command as it is
            if (!laidOut) laidOut = [m[0], m.index + m[0].length];
            else if (regex !== LIMITS_RE) laidOut = this.blockScripts(f, ...laidOut);
            out += f.slice(position, m.index) + laidOut[0];
            position = laidOut[1];
        }
    }

    // A superscript after a block of several rows goes on its top row, and a subscript on its
    // bottom row, as TeX raises and lowers them. Returns the block and where it ends.
    blockScripts(f: string, text: string, end: number): [string, number] {
        const item = text.length == 1 ? this.item(text) : undefined;
        if (!item || item[2] === null || !item[0].includes('\n')) return [text, end];
        const [scripts, scriptsEnd] = parseScripts(f, end);
        if (!Object.keys(scripts).length) return [text, end];
        const rows = item[0].split('\n');
        const w = Math.max(...rows.map(width));
        // Converted like x^{...} without the x, so that what can't be raised stays as ^{...}.
        const [sup, sub] = ['^', '_'].map((kind) => kind in scripts
            ? this.nested(kind + '{' + scripts[kind] + '}', false, false)[0].join('\n') : '');
        const column = [sup, ...new Array(rows.length - 2).fill(''), sub];
        const joined = rows.map((r, i) => (pad(r, w, 'left') + column[i]).trimEnd());
        return [this.protect(joined.join('\n'), item[1], item[2]), scriptsEnd];
    }

    // A fraction over several lines, with its parts in inline style, and where it ends.
    stackedFraction(f: string, m: RegExpExecArray): [string, number] | null {
        const numerator = braceGroup(f, m.index + m[0].length);
        const denominator = numerator && braceGroup(f, numerator[1]);
        if (!numerator || !denominator) return null;
        const parts = [numerator[0], denominator[0]].map((part) => this.nested(part, false, false)[0]);
        const w = Math.max(...parts.flat().map(width)) + 2;
        const rows = [...parts[0].map((r) => pad(r, w)), '─'.repeat(w), ...parts[1].map((r) => pad(r, w))];
        return [this.protect(rows.join('\n'), 'inner', parts[0].length), denominator[1]];
    }

    // A \left ... \right pair with delimiters as tall as their contents, and where it ends.
    leftRight(f: string, opening: RegExpExecArray): [string, number] | null {
        let depth = 0;
        for (const m of f.slice(opening.index).matchAll(LEFT_RIGHT_RE)) {
            depth += m[1] == 'left' ? 1 : -1;
            if (depth == 0) {
                const start = opening.index + opening[0].length;
                const end = opening.index + m.index! + m[0].length;
                return [this.tallDelimiters(opening[1], f.slice(start, opening.index + m.index!), m[2]), end];
            }
        }
        return null;
    }

    // Delimiters as tall as the contents between them, which are converted on their own.
    tallDelimiters(left: string, contents: string, right: string): string {
        const [converted, axis] = this.nested(contents);
        // one row: plain delimiters, converted along with the rest of the line
        if (converted.length == 1) return '\\left' + left + contents + '\\right' + right;
        const w = Math.max(...converted.map(width));
        const rows = converted.map((r) => pad(r, w, 'left'));
        const [l, r] = [left, right].map((d) => {
            d = DELIMITER_COMMANDS[d] ?? d;
            return delimiter(d in DELIMITERS || !d.startsWith('\\') ? d : replace(d), rows.length, axis);
        });
        return this.protect(rows.map((row, i) => l[i] + row + r[i]).join('\n'), 'inner', axis);
    }

    // \sum, \lim, ... with their limits (in inline style) above and below, and where they end.
    limits(f: string, m: RegExpExecArray): [string, number] | null {
        const [scripts, end] = parseScripts(f, m.index + m[0].length);
        if (!Object.keys(scripts).length) return null;
        const name = m[1];
        const symbol = OPERATOR_NAMES.has(name) ? name : replace('\\' + name);
        const blocks: string[][] = [];
        if ('^' in scripts) blocks.push(this.nested(scripts['^'], true, false)[0]);
        blocks.push([symbol]);
        if ('_' in scripts) blocks.push(this.nested(scripts['_'], true, false)[0]);
        const axis = '^' in scripts ? blocks[0].length : 0;
        return [this.protect(stack(blocks).join('\n'), 'op', axis), end];
    }

    // Split a line into [text, class] atoms with TeX's math classes.
    atoms(line: string): [string, string][] {
        const atoms: [string, string][] = [];
        for (const [t] of line.matchAll(TOKEN_RE)) {
            if (' \t\r\f\v'.includes(t[0])) continue;   // spaces typed in math are ignored
            const last = atoms[atoms.length - 1];
            if (t[0] == '\\' && t.length > 1) {
                atoms.push([t, 'raw']);
            } else if ('_^'.includes(t[0]) && last && last[1] != 'space') {
                last[0] += t.replace(/\s+/g, '');   // an unconverted script stays on its base
            } else if (last && last[1] != 'space' && (
                MATH_CLASS.get(t) == 'attach' || SCRIPT_CHARS.has(t) || /^\p{M}$/u.test(t))) {
                last[0] += t;
            } else if (this.item(t)) {
                atoms.push([t, this.item(t)![1]]);
            } else {
                atoms.push([t, MATH_CLASS.get(t) ?? 'ord']);
            }
        }

        // A binary operator with nothing to combine on one side is ordinary, as in -x.
        let previous: [string, string] | null = null;
        for (const atom of atoms) {
            if (atom[1] == 'space') continue;
            if (atom[1] == 'bin' && (!previous || ['bin', 'op', 'rel', 'open', 'punct'].includes(previous[1]))) {
                atom[1] = 'ord';
            }
            if (['rel', 'close', 'punct'].includes(atom[1]) && previous && previous[1] == 'bin') {
                previous[1] = 'ord';
            }
            previous = atom;
        }
        if (previous && previous[1] == 'bin') previous[1] = 'ord';
        return atoms;
    }

    // Space a line of converted math the way TeX does, ignoring typed spaces.
    space(line: string): string {
        let out = '';
        let previous: [string, string] | null = null;
        for (const atom of this.atoms(line)) {
            if (previous && previous[1] != 'space' && atom[1] != 'space') {
                const left = previous[1] == 'raw' ? 'ord' : previous[1];
                const right = atom[1] == 'raw' ? 'ord' : atom[1];
                // An unconverted command keeps the space that ends it, as in \foo x.
                const endsCommand = previous[1] == 'raw' && /[A-Za-z]$/.test(previous[0])
                    && /^[A-Za-z0-9]/.test(atom[0]);
                if ((this.script ? SCRIPT_SPACED : SPACED).has(left + ' ' + right) || endsCommand) out += ' ';
            }
            out += atom[0];
            previous = atom;
        }
        return out;
    }

    // Restore the placeholders in a line, setting blocks side by side.
    layout(line: string): Block {
        const parts: Block[] = [];
        let text = '';
        for (const c of line) {
            const item = this.item(c);
            if (item && item[2] !== null) {
                parts.push([[text], 0], [item[0].split('\n'), item[2]]);
                text = '';
            } else {
                text += this.restore(c);
            }
        }
        if (!parts.length) return [[text], 0];
        const [rows, axis] = sideBySide([...parts, [[text], 0]]);
        return [rows.map((r) => r.trimEnd()), axis];
    }

    // Convert f, returning the rows of all its lines and the first line's axis.
    convert(f: string): Block {
        f = f.replace(ONE_ARGUMENT_RE, (_, name, arg) => '\\' + name + braced(arg));
        f = f.replace(FRACTION_ARGUMENTS_RE, (_, name, num, den) => '\\' + name + braced(num) + braced(den));
        if (this.vulgarFractions) {
            f = f.replace(NUMBER_FRACTION_RE, (whole, num, den) => VULGAR_FRACTIONS.get(num + '/' + den) ?? whole);
        }
        if (this.display) f = this.displayLayout(f);
        f = f.replace(MATRIX_RE, (_, env, body) => this.matrix(env, body));
        f = f.replace(TEXT_RE, (_, text) => this.protect(text, 'ord'));
        f = f.replace(OPERATORNAME_RE, (_, name) => this.protect(name.replace(/\s+/g, ''), 'op'));
        f = f.replace(OPERATOR_NAMES_RE, (_, name) => this.protect(name, 'op'));
        f = f.replace(MATHRM_RE, (_, text) => this.protect(text.replace(/\s+/g, ''), 'ord'));
        if (this.mathSpacing) {
            for (const [regex, space] of MATH_SPACE_COMMANDS) f = f.replace(regex, space);
        }
        // Roots with an index other than 3 or 4 (which are symbols): \sqrt[n] -> ⁿ√
        f = f.replace(/\\sqrt\s*\[([^\]]*)\]/g, (_, n) =>
            ['3', '4'].includes(n.trim()) ? '\\sqrt[' + n.trim() + ']' : '^{' + n.trim() + '}\\sqrt');

        // Catch cases like \not\subset and \not\in and convert them to
        // use the combining character slash as in \slash{\subset}
        f = f.replace(/\\not(\\[A-z]+)/g, '\\slash{$1}');
        // Remove delimiter sizing, which plain text can't show: \left( -> ( and
        // \bigl\{ -> \{. The null delimiters \left. and \right. disappear.
        f = f.replace(/\\(?:left|right)\s*\./g, '');
        f = f.replace(/\\(?:left|right|middle|[Bb]igg?[lrm]?)(?![A-Za-z])\s*/g, '');
        // escape combining marks with a space after the backslash
        for (const ic in combiningmarks) {
            const c = combiningmarks[ic];

            let i = -1;
            while (
                (i = f.indexOf(c[0] + '{', i+1)) > -1
                && f.indexOf("}", i+1) > i
            ) {
                f = f.slice(0, i+1) + ' ' + f.slice(i+1);
            }
        }

        // console.log(replacements);
        for (const ir in replacements) {
            const r = replacements[ir];
            const u = BRACE_PLACEHOLDERS[r[1]] ?? r[1];
            const wholeCommand = WHOLE_COMMANDS[ir];
            if (f.includes(r[0])) {
                // dirty way of a replaceAll():
                f = wholeCommand ? f.replace(wholeCommand, () => u) : f.split(r[0]).join(u);
            }

            if (r[0].slice(-2) == '{}') {
                f = f.split('\\ '+r[0].slice(1)).join(u);
            }
        }

        // expand groups of sub- and superscripts, _{01234} and ^{01234}, if every
        // character in them has one (spaces stay as they are)
        f = f.replace(SCRIPT_GROUP_RE, (group, kind, inner) => {
            const chars = [...inner];
            return inner.trim() && chars.every((c) => /\s/.test(c) || SCRIPT_BASES[kind].has(c))
                ? chars.map((c) => /\s/.test(c) ? c : kind + c).join('') : group;
        });

        // now replace subsuperscripts
        for (const ir in subsuperscripts) {
            const r = subsuperscripts[ir];
            // dirty way of a replaceAll():
            f = f.split(r[0]).join(r[1]);
        }

        // combining marks (unicode char modifies previous char)
        for (const ic in combiningmarks) {
            const c = combiningmarks[ic];

            let i = -1;
            while (
                (i = f.indexOf('\\ '+c[0].slice(1)+'{', i+1)) > -1
                && f.indexOf("}", i+1) > i
            ) {
                const newString = f[i+c[0].length+2] + c[1];
                f = f.slice(0,i)+newString+f.slice(i+1+c[0].length+3);
            }
        }

        // Fractions, \frac{a + b}{c} -> (a + b)/c or stacked in display style,
        // roots with parentheses unless single terms, √(1 + 2), and grouping
        // braces removed, {1 + 2} -> 1 + 2. Braces holding arguments of unknown
        // commands stay, as in \foo{abc}, and so do unconverted script groups,
        // as in x^{#}. Repeat for nested groups.
        let previous;
        do {
            previous = f;
            f = f.replace(FRACTION_RE, (_, num, den) => this.operand(num) + '/' + this.operand(den));
            f = f.replace(ROOT_RE, (_, root, arg) => root + this.operand(arg));
            f = f.replace(GROUP_RE, (group, inner, offset, whole) =>
                COMMAND_ARGS_RE.test(whole.slice(0, offset)) ? group : inner);
        } while (f !== previous);

        let rows: string[] = [];
        let axis = 0;
        for (let line of f.split('\n')) {
            if (this.mathSpacing) line = this.space(line);
            const [lineRows, lineAxis] = this.layout(line);
            if (!rows.length) axis = lineAxis;
            rows = rows.concat(lineRows);
        }
        for (const brace in BRACE_PLACEHOLDERS) {
            rows = rows.map((r) => r.split(BRACE_PLACEHOLDERS[brace]).join(brace));
        }
        return [rows.map((r) => r.split(SPACE_PLACEHOLDER).join(' ')), axis];
    }
}


export function replace(f: string, options: ReplaceOptions = {}): string {
    return new Converter(!!options.mathSpacing, !!options.display, false, [], !!options.vulgarFractions)
        .convert(stripComments(f))[0].join('\n');
}
