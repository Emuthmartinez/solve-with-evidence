import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from gradelib import main, raises

# Each expected value below was worked out by hand from the rules in prompt.md.
PARSES = {
    'example 1': ('a|b|c\nd|"e|f"|\n', [['a', 'b', 'c'], ['d', 'e|f', '']]),
    'example 2': ('x |"say ""hi""" \r\n\r\n"two\nlines"', [['x', 'say "hi"'], ['two\nlines']]),
    'empty text': ('', []),
    'only line breaks': ('\n\r\n\n', []),
    'single field without line break': ('a', [['a']]),
    'final LF starts no record': ('a\n', [['a']]),
    'empty line skipped': ('a\n\nb', [['a'], ['b']]),
    'leading empty lines skipped': ('\r\n\na|b', [['a', 'b']]),
    'trailing separator gives empty field': ('a|', [['a', '']]),
    'lone separator gives two fields': ('|', [['', '']]),
    'separators only': ('||\n', [['', '', '']]),
    'spaces-only line is a record': ('a\n  \nb', [['a'], [''], ['b']]),
    'tab-only line is a record': ('\t', [['']]),
    'empty quoted field is a record': ('""', [['']]),
    'unquoted trimmed, inner blanks kept': (' a  b \t|c', [['a  b', 'c']]),
    'lone CR kept at field end': ('a\r|b', [['a\r', 'b']]),
    'lone CR kept inside field': ('a\rb', [['a\rb']]),
    'CRLF records with trailing blanks': ('a  \r\nb\t\r\n', [['a'], ['b']]),
    'space before opening quote': (' "x|y" |z', [['x|y', 'z']]),
    'tab before opening quote': ('a|\t"q"', [['a', 'q']]),
    'escaped quote in middle': ('"a""b"', [['a"b']]),
    'only an escaped quote': ('""""', [['"']]),
    'escaped quote at end': ('"a"""', [['a"']]),
    'quote inside unquoted field is literal': ('ab"c"|d', [['ab"c"', 'd']]),
    'quoted CRLF kept': ('"m\r\nl"|x\r\ny', [['m\r\nl', 'x'], ['y']]),
    'blanks inside quotes kept': ('" a "|"\t"', [[' a ', '\t']]),
    'blanks after closing quote ignored': ('"a"  |b', [['a', 'b']]),
}

ERRORS = {
    'example 3: unterminated quote': '"open',
    'text after closing quote': '"a"b',
    'text after closing quote and space': '"a" b|c',
    'unterminated after escaped pair': '"a""',
    'unterminated across lines': 'x\n"abc\ndef',
    'lone CR after closing quote': '"a"\rb',
}

CHECKS = [(name, lambda s, t=text, want=want: s.parse(t) == want) for name, (text, want) in PARSES.items()]
CHECKS += [(name, lambda s, t=text: raises(ValueError, s.parse, t)) for name, text in ERRORS.items()]
CHECKS.append(('returns lists of str', lambda s: all(
    type(r) is list and all(type(f) is str for f in r) for r in s.parse('a|"b"\nc'))))

if __name__ == '__main__':
    main(CHECKS)
