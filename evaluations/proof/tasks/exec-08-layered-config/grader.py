import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from gradelib import main, raises


def same(a, b):
    """Equal, with bool kept distinct from int and int distinct from float."""
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return a == b


def containers(value, found):
    if isinstance(value, (dict, list)):
        found.add(id(value))
        for item in (value.values() if isinstance(value, dict) else value):
            containers(item, found)
    return found


def ownership(s):
    layers = [{'a': {'b': [1, [2]]}, 'c': [{'d': 1}]}, {'e+': [[3]], 'f': {'g': {'h': [4]}}}]
    env = {'APP_A__X': '1'}
    before_layers, before_env = copy.deepcopy(layers), copy.deepcopy(env)
    result = s.resolve(layers, env)
    if layers != before_layers or env != before_env:
        return False
    keep = [layers, env]  # holds the inputs alive so their ids stay unique
    shared = containers(result, set()) & containers(keep, set())
    return not shared


CASES = [
    ('example layers', [{'db': {'host': 'a', 'port': 1}, 'tags': ['x']}, {'db': {'port': None}, 'tags+': ['y']}], {},
     {'db': {'host': 'a'}, 'tags': ['x', 'y']}),
    ('example env', [{'db': {'host': 'a'}}], {'APP_DB__PORT': '5432', 'APP_DEBUG': 'true', 'HOME': '/root'},
     {'db': {'host': 'a', 'port': 5432}, 'debug': True}),
    ('example quoted', [{}], {'APP_VERSION': '"1.10"', 'APP_RATIO': '0.5'}, {'version': '1.10', 'ratio': 0.5}),
    ('no layers', [], {'APP_X': '1'}, {'x': 1}),
    ('lists replace', [{'a': [1, 2]}, {'a': [3]}], {}, {'a': [3]}),
    ('append to absent', [{'b': 1}, {'a+': [1]}], {}, {'b': 1, 'a': [1]}),
    ('append in first layer', [{'a+': [1, 2]}], {}, {'a': [1, 2]}),
    ('set then append in one layer', [{'a': [0]}, {'a': [1], 'a+': [2]}], {}, {'a': [1, 2]}),
    ('append then set in one layer', [{'a': [0]}, {'a+': [2], 'a': [1]}], {}, {'a': [1]}),
    ('delete absent key', [{'a': 1}, {'b': None}], {}, {'a': 1}),
    ('deep delete', [{'a': {'b': {'c': 1, 'd': 2}}}, {'a': {'b': {'c': None}}}], {}, {'a': {'b': {'d': 2}}}),
    ('dict over scalar', [{'a': 1}, {'a': {'b': 2}}], {}, {'a': {'b': 2}}),
    ('scalar over dict', [{'a': {'b': 2}}, {'a': 5}], {}, {'a': 5}),
    ('directives inside a new dict', [{}, {'a': {'x': None, 'y+': [1], 'z': {'w': None}}}], {},
     {'a': {'y': [1], 'z': {}}}),
    ('directives inside a dict replacing a scalar', [{'a': 1}, {'a': {'b+': [1], 'c': None}}], {}, {'a': {'b': [1]}}),
    ('list contents are opaque', [{'a': [{'x': None, 'y+': 1}, None]}], {}, {'a': [{'x': None, 'y+': 1}, None]}),
    ('env numbers', [{}], {'APP_A': '007', 'APP_B': '-12', 'APP_C': '1.50', 'APP_D': '-0.25', 'APP_E': 'false'},
     {'a': 7, 'b': -12, 'c': 1.5, 'd': -0.25, 'e': False}),
    ('env strings that look numeric', [{}],
     {'APP_A': '1e3', 'APP_B': '.5', 'APP_C': '5.', 'APP_D': 'inf', 'APP_E': 'nan'},
     {'a': '1e3', 'b': '.5', 'c': '5.', 'd': 'inf', 'e': 'nan'}),
    ('env strings with signs or spaces', [{}], {'APP_A': '+5', 'APP_B': ' 7', 'APP_C': '7 '},
     {'a': '+5', 'b': ' 7', 'c': '7 '}),
    ('env other strings', [{}], {'APP_A': 'True', 'APP_B': '', 'APP_C': 'NULL', 'APP_D': "'x'", 'APP_E': '"'},
     {'a': 'True', 'b': '', 'c': 'NULL', 'd': "'x'", 'e': '"'}),
    ('env quoted', [{}], {'APP_A': '"42"', 'APP_B': '"null"', 'APP_C': '""', 'APP_D': '"true"'},
     {'a': '42', 'b': 'null', 'c': '', 'd': 'true'}),
    ('env null deletes', [{'db': {'host': 'a', 'port': 1}}], {'APP_DB__PORT': 'null'}, {'db': {'host': 'a'}}),
    ('env null never creates', [{'x': 1}], {'APP_DB__PORT': 'null', 'APP_DB__A__B': 'null'}, {'x': 1}),
    ('env null under a scalar', [{'db': 5}], {'APP_DB__PORT': 'null'}, {'db': 5}),
    ('env replaces non-dict parents', [{'db': 'x', 'tags': [1]}], {'APP_DB__HOST': 'h', 'APP_TAGS__0': 'a'},
     {'db': {'host': 'h'}, 'tags': {'0': 'a'}}),
    ('env shorter path first', [{}], {'APP_DB__HOST': 'h', 'APP_DB': 'x'}, {'db': {'host': 'h'}}),
    ('env null parent then child', [{'db': {'host': 'a', 'port': 1}}], {'APP_DB__HOST': 'h', 'APP_DB': 'null'},
     {'db': {'host': 'h'}}),
    ('env name order breaks ties', [{}], {'APP_Port': '2', 'APP_PORT': '1'}, {'port': 2}),
    ('env names ignored', [{'k': 0}],
     {'app_x': '1', 'APPX': '1', 'X_APP_Y': '1', 'APP_': '1', 'APP_A__': '1', 'APP___B': '1', 'APP_C____D': '1'},
     {'k': 0}),
    ('env lower-cases and keeps plus', [{'tags': ['a']}], {'APP_LOG__Level': 'debug', 'APP_TAGS+': 'b'},
     {'log': {'level': 'debug'}, 'tags': ['a'], 'tags+': 'b'}),
]

CHECKS = [(name, lambda s, l=layers, e=env, x=expected: same(s.resolve(l, e), x)) for name, layers, env, expected in CASES]
CHECKS += [
    ('append to non-list raises', lambda s: raises(ValueError, s.resolve, [{'a': 1}, {'a+': [2]}], {})),
    ('append to dict raises', lambda s: raises(ValueError, s.resolve, [{'a': {'b': 1}}, {'a+': [2]}], {})),
    ('append non-list value raises', lambda s: raises(ValueError, s.resolve, [{'a+': 3}], {})),
    ('append None raises', lambda s: raises(ValueError, s.resolve, [{'a': [1]}, {'a+': None}], {})),
    ('inputs untouched and unshared', ownership),
]

if __name__ == '__main__':
    main(CHECKS)
