import { expect } from 'chai';
import { replace } from './replace';


describe('Symbols', () => {
  describe('replace alpha', () => {
    it('converts', done => {
      expect(replace('\\alpha')).to.equal('α');
      done();
    });
  });

  describe('combining mark', () => {
    it('adds dot to a', done => {
      expect(replace('\\dot{a}')).to.equal('ȧ');
      done();
    });
    it('adds dot to alpha', done => {
      expect(replace('\\dot{\\alpha}')).to.equal('α̇');
      done();
    });
    it('empty combining char', done => {
      expect(replace('\\breve{}')).to.equal('˘');
      done();
    });
    it('incomplete combining char', done => {
      expect(replace('\\breve{')).to.equal('\\breve{');
      done();
    });
  });

  describe('issue fixes', () => {
    it('combines check (#48)', done => {
      expect(replace('\\check{z}')).to.equal('z\u030C');
      expect(replace('\\check{}')).to.equal('ˇ');
      done();
    });
    it('uses mathematical angle brackets (#32)', done => {
      expect(replace('\\langle x \\rangle')).to.equal('⟨ x ⟩');
      done();
    });
    it('superscripts top as transpose (#49)', done => {
      expect(replace('M^\\top')).to.equal('Mᵀ');
      expect(replace('M^{\\top}')).to.equal('Mᵀ');
      expect(replace('M^\\intercal')).to.equal('Mᵀ');
      done();
    });
    it('superscripts primes (#81)', done => {
      expect(replace("x^'")).to.equal('x′');
      expect(replace('x^\\prime')).to.equal('x′');
      expect(replace("\\eta^{(')}")).to.equal('η⁽′⁾');
      done();
    });

  describe('script groups', () => {
    it('converts groups with spaces', done => {
      expect(replace('a^{\\int f(x) dx}')).to.equal('aᶴ ᶠ⁽ˣ⁾ ᵈˣ');
      expect(replace('a^{\\int f(x) dx}', { mathSpacing: true })).to.equal('aᶴᶠ⁽ˣ⁾ᵈˣ');
      done();
    });
    it('leaves groups with a character that has no script', done => {
      expect(replace('x_{i,j}')).to.equal('x_{i,j}');
      expect(replace('D^{-0.5}')).to.equal('D⁻⁰ᐧ⁵');
      done();
    });
  });

  describe('command names', () => {
    it('matches whole command names only', done => {
      expect(replace('\\intf(x)')).to.equal('\\intf(x)');
      expect(replace('\\int f(x)')).to.equal('∫ f(x)');
      expect(replace('\\alpha2 \\alpha_1')).to.equal('α2 α₁');
      expect(replace('\\dot{x} \\dots{}')).to.equal('x\u0307 \\dots{}');
      done();
    });
  });

  describe('arguments without braces', () => {
    it('takes the next character or command', done => {
      expect(replace('\\dot x')).to.equal('x\u0307');
      expect(replace('\\dot2')).to.equal('2\u0307');
      expect(replace('\\hat\\alpha')).to.equal('α\u0302');
      expect(replace('\\sqrt2')).to.equal('√2');
      expect(replace('\\frac12')).to.equal('1/2');
      expect(replace('\\mathbb R^n')).to.equal('ℝⁿ');
      expect(replace('\\dotx')).to.equal('\\dotx');
      done();
    });
  });

  describe('vulgar fractions', () => {
    it('writes fractions with one character as that character', done => {
      expect(replace('\\frac{1}{2} + \\frac34 = \\tfrac{5}{4}', { vulgarFractions: true })).to.equal('½ + ¾ = 5/4');
      expect(replace('x = \\frac{1}{2}', { mathSpacing: true, display: true, vulgarFractions: true })).to.equal('x = ½');
      expect(replace('\\frac{1}{2}')).to.equal('1/2');
      done();
    });
  });

  describe('comments', () => {
    it('removes % comments but not \\%', done => {
      expect(replace('a + b % the sum')).to.equal('a + b ');
      expect(replace('50\\% of x')).to.equal('50% of x');
      expect(replace('a\n% a whole line\nb')).to.equal('a\nb');
      done();
    });
  });

  describe('math spacing', () => {
    const math = (latex: string) => replace(latex, { mathSpacing: true });
    it('ignores typed spaces and spaces operators, relations, and punctuation', done => {
      expect(math('a+b=c')).to.equal('a + b = c');
      expect(math('a   +   b')).to.equal('a + b');
      expect(math('f(x,y)')).to.equal('f(x, y)');
      expect(math('-x+(-1)')).to.equal('−x + (−1)');
      expect(math('x^2+y_1')).to.equal('x² + y₁');
      done();
    });
    it('keeps explicit spacing and line breaks', done => {
      expect(math('a~b')).to.equal('a b');
      expect(math('a\\,b')).to.equal('a b');
      expect(math('a\\qquad b')).to.equal('a  b');
      expect(math('a\\!b')).to.equal('ab');
      expect(math('\\~{A}')).to.equal('Ã');
      expect(math('a\\\\b')).to.equal('a\nb');
      done();
    });
    it('handles text and operator names', done => {
      expect(math('\\text{if } x>0')).to.equal('if x > 0');
      expect(math('\\sin x+\\sin(x)')).to.equal('sin x + sin(x)');
      expect(math('\\operatorname{sgn} x')).to.equal('sgn x');
      expect(math('\\mathrm{d}x')).to.equal('dx');
      expect(math('\\foo x')).to.equal('\\foo x');
      expect(math('\\lim_{x\\to0} f(x)')).to.equal('lim_{x→0} f(x)');
      done();
    });
    it('is optional', done => {
      expect(replace('a+b  =c')).to.equal('a+b  =c');
      done();
    });
  });

  describe('roots and matrices', () => {
    it('wraps roots of more than one term', done => {
      expect(replace('\\sqrt{2}')).to.equal('√2');
      expect(replace('\\sqrt{1 + 2}')).to.equal('√(1 + 2)');
      expect(replace('\\sqrt[5]{x}')).to.equal('⁵√x');
      done();
    });
    it('writes matrices inline by default', done => {
      expect(replace('\\begin{bmatrix}1&2\\\\3&4\\end{bmatrix}', { mathSpacing: true })).to.equal('[1 2; 3 4]');
      done();
    });
  });

  describe('display style', () => {
    const display = (latex: string) => replace(latex, { mathSpacing: true, display: true });
    it('stacks fractions', done => {
      expect(display('\\frac{a+b}{c}=1')).to.equal(' a + b\n─────── = 1\n   c');
      done();
    });
    it('draws matrices with tall brackets', done => {
      expect(display('A=\\begin{bmatrix}1&-2\\\\\\alpha&4\\end{bmatrix}x'))
        .to.equal('A = ⎡1  −2⎤ x\n    ⎣α  4 ⎦');
      expect(display('|x|=\\begin{cases}x & x\\geq 0\\\\-x&\\text{otherwise}\\end{cases}'))
        .to.equal('|x| = ⎧x   x ≥ 0\n      ⎩−x  otherwise');
      done();
    });
    it('makes \\left and \\right delimiters tall', done => {
      expect(display('\\left(\\frac{1}{2}\\right)')).to.equal('⎛ 1 ⎞\n⎜───⎟\n⎝ 2 ⎠');
      expect(display('\\left(\\left(\\frac{1}{2}\\right)+1\\right)'))
        .to.equal('⎛⎛ 1 ⎞    ⎞\n⎜⎜───⎟ + 1⎟\n⎝⎝ 2 ⎠    ⎠');
      expect(display('\\left(x+1\\right) \\left. y \\right|')).to.equal('(x + 1)y|');
      done();
    });
    it('writes the parts of fractions and limits in inline style', done => {
      expect(display('\\frac{\\frac{1}{2}}{x}')).to.equal(' 1/2\n─────\n  x');
      expect(display('\\sum_{i=1}^{\\frac{n}{2}} x')).to.equal('n/2\n ∑  x\ni=1');
      done();
    });
    it('puts scripts after tall blocks on their top and bottom rows', done => {
      expect(display('\\begin{bmatrix} \n1 & 2 \\\\ 3 & 4 \n\\end{bmatrix}^\\top')).to.equal('⎡1  2⎤ᵀ\n⎣3  4⎦');
      expect(display('A = \\begin{pmatrix}a\\\\b\\end{pmatrix}^{-1}_{ij} x')).to.equal('A = ⎛a⎞⁻¹ x\n    ⎝b⎠ᵢⱼ');
      done();
    });
    it('keeps empty matrix rows', done => {
      expect(display('\\begin{bmatrix}\n1 & 2 & 3 & 5  \\\\ \\\\ \\\\\n\\end{bmatrix}'))
        .to.equal('⎡1  2  3  5⎤\n⎢          ⎥\n⎣          ⎦');
      expect(display('\\begin{bmatrix}1&2\\\\3&4\\\\\\end{bmatrix}')).to.equal('⎡1  2⎤\n⎣3  4⎦');
      done();
    });
    it('treats newlines inside environments as spaces', done => {
      expect(display('\\begin{bmatrix} \n1 & 2 & 3 & 5 \n\\end{bmatrix}')).to.equal('[1  2  3  5]');
      done();
    });
    it('puts limits above and below', done => {
      expect(display('\\sum_{i=1}^{n} a_i + \\lim_{x\\to0} f(x)'))
        .to.equal(' n\n ∑  aᵢ + lim f(x)\ni=1      x→0');
      done();
    });
  });

  describe('layout', () => {
    it('writes fractions inline', done => {
      expect(replace('\\frac{a}{b}')).to.equal('a/b');
      expect(replace('\\frac{a + b}{b}')).to.equal('(a + b)/b');
      expect(replace('\\frac{\\frac{a}{b}}{c}')).to.equal('(a/b)/c');
      expect(replace('\\sfrac{1}{2}')).to.equal('½');
      done();
    });
    it('removes delimiter sizing', done => {
      expect(replace('\\left(1 + 2\\right)')).to.equal('(1 + 2)');
      expect(replace('\\left\\{ x \\right.')).to.equal('{ x ');
      expect(replace('a \\leftarrow b \\rightarrow \\bigcup')).to.equal('a ← b → ⋃');
      done();
    });
    it('removes grouping braces', done => {
      expect(replace('{1 + 2}')).to.equal('1 + 2');
      expect(replace('\\{1 + 2\\}')).to.equal('{1 + 2}');
      expect(replace('\\foo{abc} {d}')).to.equal('\\foo{abc} d');
      expect(replace('\\breve{')).to.equal('\\breve{');
      done();
    });
  });
  });
});
