Write `solution.py` with one function:

```python
def resolve(layers: list[dict], env: dict[str, str]) -> dict:
```

It builds one configuration from layers (defaults first, overrides later), then applies overrides from environment variables.

Values inside layers are dicts, lists, strings, ints, floats, booleans or `None`. Every dict key is a string, and no key is exactly `+`.

Merging layers:

1. Start from an empty dict and merge each layer into it, left to right. Within one layer, keys are applied in the dict's iteration order.
2. A key whose value is `None` deletes that key from the current dict. If the key is absent, nothing happens.
3. A key ending in `+`, such as `tags+`, appends to the list stored under the name without the `+` (`tags`). Its value must be a list; otherwise raise `ValueError`. If the name is absent, the value becomes a new list under the name. If the name holds a value that is not a list, raise `ValueError`. A key ending in `+` never appears in the result.
4. A dict value is merged recursively into the existing value when the existing value is a dict. When the existing value is absent or is not a dict, the dict value is merged into a new empty dict, so rules 2 to 5 apply inside it at every depth. For example, merging `{"a": {"x": None, "y+": [1]}}` into `{}` gives `{"a": {"y": [1]}}`.
5. Any other value (a list, string, int, float or boolean) replaces the existing value. Lists are never merged, and nothing inside a list has a special meaning: a `None` or a key ending in `+` inside a list is kept as it is.

Environment overrides, applied after all layers:

6. Only variable names that start with `APP_` (case-sensitive) are used. All other names are ignored.
7. The rest of the name is split on `__` (two underscores), left to right without overlap, exactly as Python's `str.split("__")` splits it. Each segment is lower-cased. The segments form a path of keys from the top of the configuration. If any segment is empty (for example `APP_`, `APP_DB__` or `APP_A____B`), the variable is ignored.
8. The value string is converted by the first rule that applies:
   - at least 2 characters long and starts and ends with `"`: the text between the two quotes, as a string, with no further conversion (`"true"` written with its quotes becomes the string `true`);
   - exactly `true` or `false`: that boolean;
   - exactly `null`: a deletion (rule 10);
   - an optional `-` followed by one or more ASCII digits, and nothing else: an int (`007` becomes 7);
   - an optional `-`, one or more ASCII digits, a `.`, one or more ASCII digits, and nothing else: a float;
   - anything else: the exact string, unchanged. So `1e3`, `.5`, `5.`, `inf`, `nan`, `+5`, ` 7` (with a space), `True` and the empty string all stay strings.
9. Setting a value: walk the path from the top. For every segment except the last, if the key is missing or its value is not a dict, first set it to a new empty dict. Then store the value under the last segment, replacing whatever was there.
10. Deleting: if every segment except the last leads to an existing dict, remove the last key when it is present. Otherwise nothing changes. A deletion never creates a key.
11. Overrides are applied in order of path length, fewer segments first, and for equal lengths in ascending order of the original variable name (plain Python string comparison). When two overrides touch the same key, the one applied later wins. Overrides only set or delete: a `+` at the end of a segment is an ordinary character.

Ownership:

12. Do not modify `layers`, `env`, or any dict or list inside them. The result must not share any dict or list object with the inputs, so changing the result can never change an input.

Examples:

```python
resolve([{"db": {"host": "a", "port": 1}, "tags": ["x"]},
         {"db": {"port": None}, "tags+": ["y"]}], {})
# {"db": {"host": "a"}, "tags": ["x", "y"]}

resolve([{"db": {"host": "a"}}], {"APP_DB__PORT": "5432", "APP_DEBUG": "true", "HOME": "/root"})
# {"db": {"host": "a", "port": 5432}, "debug": True}

resolve([{}], {"APP_VERSION": '"1.10"', "APP_RATIO": "0.5"})
# {"version": "1.10", "ratio": 0.5}
```

Use the Python standard library only.
