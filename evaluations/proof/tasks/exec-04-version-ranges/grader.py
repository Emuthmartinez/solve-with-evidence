import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from gradelib import main, raises

T, F = True, False

# Each expected value below was worked out by hand from the rules in prompt.md.
CASES = {
    'example 1': [('1.4.0', '^1.2.3 <1.5.0', T)],
    'example 2': [('1.2.4-beta.1', '>=1.2.4-alpha <1.3.0', T)],
    'example 3': [('1.3.0-beta', '^1.2.3', F)],
    'numeric prerelease ids compare as integers': [('1.0.0-beta.2', '<1.0.0-beta.11', T),
                                                   ('1.0.0-beta.11', '<1.0.0-beta.2', F)],
    'numeric id below non-numeric id': [('1.0.0-alpha.9', '<1.0.0-alpha.a', T),
                                        ('1.0.0-alpha.a', '<1.0.0-alpha.9', F)],
    'shorter prerelease is lower': [('1.0.0-alpha', '<1.0.0-alpha.0', T)],
    'release above its prereleases': [('1.0.0-rc.1', '<1.0.0 >=1.0.0-rc.1', T),
                                      ('1.0.0', '<1.0.0-rc.1 || >1.0.0-rc.1', T)],
    'core parts compare as integers': [('10.0.0', '>9.99.99', T), ('1.10.0', '>1.9.0', T), ('1.9.0', '>1.10.0', F)],
    'build ignored': [('1.2.3+build.5', '1.2.3', T), ('1.2.3', '=1.2.3+x', T), ('1.2.3+b', '>1.2.3+a', F)],
    'leading zeros allowed in build and non-numeric ids': [('1.2.3+001', '1.2.3', T), ('1.2.3-0a', '1.2.3-0a', T)],
    'caret 0.y.z': [('0.2.9', '^0.2.3', T), ('0.3.0', '^0.2.3', F), ('0.2.2', '^0.2.3', F)],
    'caret 0.0.z': [('0.0.3', '^0.0.3', T), ('0.0.4', '^0.0.3', F)],
    'caret on zero partials': [('0.0.9', '^0.0', T), ('0.1.0', '^0.0', F), ('0.9.9', '^0', T), ('1.0.0', '^0', F),
                               ('0.0.7', '^0.0.x', T), ('0.1.0', '^0.0.x', F), ('0.0.0', '^0.0.0', T),
                               ('0.0.1', '^0.0.0', F)],
    'caret major': [('1.9.0', '^1.x', T), ('2.0.0', '^1.x', F), ('1.2.3', '^1.2.3', T), ('1.2.2', '^1.2.3', F)],
    'tilde': [('1.2.9', '~1.2.3', T), ('1.3.0', '~1.2.3', F), ('1.2.2', '~1.2.3', F), ('1.9.9', '~1', T),
              ('2.0.0', '~1', F), ('0.0.5', '~0.0.1', T), ('0.1.0', '~0.0.1', F), ('1.2.0', '~1.2.x', T),
              ('1.3.0', '~1.2', F)],
    'greater-than partial uses ceiling': [('1.2.9', '>1.2', F), ('1.3.0', '>1.2', T), ('1.9.0', '>1', F),
                                          ('2.0.0', '>1', T)],
    'at-most partial uses ceiling': [('1.2.5', '<=1.2', T), ('1.3.0', '<=1.2', F), ('1.9.9', '<=1', T)],
    'at-least and less-than partials use floor': [('1.2.0', '>=1.2', T), ('1.1.9', '>=1.2', F),
                                                  ('1.1.99', '<1.2', T), ('1.2.0', '<1.2', F)],
    'bare and equals partials': [('1.2.7', '1.2', T), ('1.3.0', '1.2', F), ('1.0.0', '1.x', T),
                                 ('1.2.0', '1.2.x', T), ('2.0.0', '=1', F), ('1.5.5', '=1', T)],
    'full comparators': [('1.2.3', '>1.2.3', F), ('1.2.3', '<=1.2.3', T), ('1.2.4', '=1.2.3', F),
                         ('1.2.3', '1.2.3', T)],
    'wildcards match every release': [('0.0.0', '*', T), ('9.9.9', 'x', T), ('3.0.0', '=*', T), ('1.0.0', 'x.x', T)],
    'wildcard rejects prereleases': [('3.0.0-alpha', '*', F)],
    'hyphen range with full ends': [('2.3.4', '1.2.3 - 2.3.4', T), ('2.3.5', '1.2.3 - 2.3.4', F),
                                    ('1.2.2', '1.2.3 - 2.3.4', F), ('1.2.3', '1.2.3 - 2.3.4', T)],
    'hyphen range with partial ends': [('2.3.9', '1.2 - 2.3', T), ('2.4.0', '1.2 - 2.3', F),
                                       ('1.2.0', '1.2 - 2.3', T), ('1.1.9', '1.2 - 2.3', F)],
    'or of sets': [('1.5.0', '<1.0.0 || >=2.0.0', F), ('2.0.0', '<1.0.0 || >=2.0.0', T),
                   ('0.9.0', '<1.0.0 || >=2.0.0', T)],
    'extra spaces ignored': [('3.1.0', '  >=1.0.0   <2.0.0  ||  3.x ', T), ('1.5.0', '  >=1.0.0   <2.0.0  ||  3.x ', T)],
    'prerelease needs a same-core prerelease in the set': [
        ('1.2.3-alpha', '<1.2.3-beta', T), ('1.2.3-alpha', '<1.2.3', F), ('1.2.4-alpha', '>=1.2.3-beta', F),
        ('1.2.3-rc.1', '^1.2.3-beta.2', T), ('1.2.3-beta.1', '^1.2.3-beta.2', F)],
    'prerelease rule is per set': [('1.2.3-rc.1', '=1.2.3-beta || >=1.0.0', F),
                                   ('1.2.3-rc.1', '>=1.0.0 || >=1.2.3-beta <1.3.0', T)],
    'hyphen prerelease end counts for the prerelease rule': [('2.0.0-rc.1', '1.0.0 - 2.0.0-rc.2', T),
                                                             ('2.0.0-rc.3', '1.0.0 - 2.0.0-rc.2', F)],
}

BAD_VERSIONS = {
    'invalid version core raises': ['1.2', '01.2.3', '1.02.3', 'v1.2.3', ' 1.2.3', '1.2.3 ', '1.2.x'],
    'invalid version prerelease raises': ['1.2.3-01', '1.2.3-', '1.2.3-a..b', '1.2.3-a_b'],
    'invalid version build raises': ['1.2.3+', '1.2.3+a..b'],
}

BAD_SPECS = {
    'invalid spec raises': ['', '   ', '>=1.2.3 ||', '|| 1.2.3', '>= 1.2.3', '~>1.2', '1.x.3', '1.2-beta',
                            '01.2.3', '1.2.3 | 2.0.0', 'abc'],
    'operator with no numeric part raises': ['>=*', '^x', '~*', '>X', '<*', '<=x.x', '1.2.3 - *', '* - 1.2.3'],
    'misplaced hyphen raises': ['1.2.3 -', '- 1.2.3', '1.2.3 - >2.0.0', '>1.0.0 - 2.0.0', '1.0.0 - 2.0.0 - 3.0.0',
                                '1.2.3 -2.0.0'],
    'invalid term raises even after a matching set': ['1.0.0 || >>2', '* || 1.x.3'],
}

CHAIN = ['1.0.0-alpha', '1.0.0-alpha.1', '1.0.0-alpha.beta', '1.0.0-beta', '1.0.0-beta.2', '1.0.0-beta.11',
         '1.0.0-rc.1', '1.0.0']


def chain_ordered(s):
    for i, low in enumerate(CHAIN):
        for high in CHAIN[i + 1:]:
            if s.satisfies(low, f'<{high} >=1.0.0-alpha') is not True:
                return False
            if s.satisfies(high, f'<{low} >=1.0.0-alpha') is not False:
                return False
    return True


CHECKS = [(name, lambda s, cases=cases: all(s.satisfies(v, spec) is want for v, spec, want in cases))
          for name, cases in CASES.items()]
CHECKS += [(name, lambda s, vs=vs: all(raises(ValueError, s.satisfies, v, '*') for v in vs))
           for name, vs in BAD_VERSIONS.items()]
CHECKS += [(name, lambda s, specs=specs: all(raises(ValueError, s.satisfies, '1.0.0', spec) for spec in specs))
           for name, specs in BAD_SPECS.items()]
CHECKS.append(('precedence chain', chain_ordered))

if __name__ == '__main__':
    main(CHECKS)
