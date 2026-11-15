import re

PREFIX = 'APP_'
DELETE = object()
INT = re.compile(r'-?[0-9]+')
FLOAT = re.compile(r'-?[0-9]+\.[0-9]+')


def _copy(value):
    if isinstance(value, dict):
        return {k: _copy(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_copy(v) for v in value]
    return value


def _merge(base, layer):
    for key, value in layer.items():
        if key.endswith('+'):
            name = key[:-1]
            if not isinstance(value, list):
                raise ValueError(f'{key} needs a list')
            if name in base and not isinstance(base[name], list):
                raise ValueError(f'cannot append to non-list {name}')
            base[name] = base.get(name, []) + _copy(value)
        elif value is None:
            base.pop(key, None)
        elif isinstance(value, dict):
            current = base.get(key)
            base[key] = _merge(current if isinstance(current, dict) else {}, value)
        else:
            base[key] = _copy(value)
    return base


def _convert(raw):
    if len(raw) >= 2 and raw[0] == raw[-1] == '"':
        return raw[1:-1]
    if raw in ('true', 'false'):
        return raw == 'true'
    if raw == 'null':
        return DELETE
    if INT.fullmatch(raw):
        return int(raw)
    if FLOAT.fullmatch(raw):
        return float(raw)
    return raw


def resolve(layers, env):
    config = {}
    for layer in layers:
        _merge(config, layer)
    overrides = []
    for name, raw in env.items():
        if not name.startswith(PREFIX):
            continue
        path = [segment.lower() for segment in name[len(PREFIX):].split('__')]
        if '' not in path:
            overrides.append((len(path), name, path, _convert(raw)))
    for _, _, path, value in sorted(overrides, key=lambda o: o[:2]):
        node = config
        for segment in path[:-1]:
            if not isinstance(node.get(segment), dict):
                if value is DELETE:
                    break
                node[segment] = {}
            node = node[segment]
        else:
            if value is DELETE:
                node.pop(path[-1], None)
            else:
                node[path[-1]] = value
    return config
