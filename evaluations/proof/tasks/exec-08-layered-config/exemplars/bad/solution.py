import copy

DELETE = object()


def _merge(base, layer):
    for key, value in layer.items():
        if key.endswith('+'):
            name = key[:-1]
            if not isinstance(value, list):
                raise ValueError(key)
            existing = base.get(name, [])
            if not isinstance(existing, list):
                raise ValueError(key)
            base[name] = existing + copy.deepcopy(value)
        elif value is None:
            base.pop(key, None)
        elif isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge(base[key], value)
        else:
            base[key] = copy.deepcopy(value)


def _convert(raw):
    if len(raw) >= 2 and raw[0] == raw[-1] == '"':
        return raw[1:-1]
    if raw in ('true', 'false'):
        return raw == 'true'
    if raw == 'null':
        return DELETE
    for kind in (int, float):
        try:
            return kind(raw)
        except ValueError:
            pass
    return raw


def resolve(layers, env):
    config = {}
    for layer in layers:
        _merge(config, layer)
    for name, raw in env.items():
        if not name.startswith('APP_'):
            continue
        path = [segment.lower() for segment in name[4:].split('__')]
        if '' in path:
            continue
        value = _convert(raw)
        node = config
        for segment in path[:-1]:
            if not isinstance(node.get(segment), dict):
                node[segment] = {}
            node = node[segment]
        if value is DELETE:
            node.pop(path[-1], None)
        else:
            node[path[-1]] = value
    return config
