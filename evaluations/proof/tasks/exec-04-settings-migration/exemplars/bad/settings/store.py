"""Read and write the settings file. docs/schema.md defines the format."""
import copy
import json
import re

SCHEMA = 3

DEFAULTS = {
    'notifications': {'email': True, 'push': True},
    'timeout_ms': 10000,
    'appearance': {'theme': 'system', 'contrast': 'normal'},
    'locale': 'en-US',
    'quiet_hours': None,
}

LOCALE = re.compile(r'[a-z]{2,3}(-[A-Z]{2})?\Z')


class SettingsError(Exception):
    """The settings file cannot be used."""


class UnsupportedVersion(SettingsError):
    """The file was written by a newer release than this one."""


def load(path):
    """Return the settings in the file at `path`, in the schema 3 shape."""
    data = read(path)
    version = data.get('schema', 1)
    if not is_int(version) or version < 1:
        raise SettingsError(f'bad schema number: {version!r}')
    if version > SCHEMA:
        raise UnsupportedVersion(f'schema {version} is newer than this release understands')
    data = dict(data, schema=SCHEMA)
    if 'notify' in data:
        notify = data.pop('notify')
        data['notifications'] = {'email': notify, 'push': notify}
    if 'timeout' in data:
        data['timeout_ms'] = int(data.pop('timeout')) * 1000
    if 'lang' in data:
        data['locale'] = data.pop('lang')
    if isinstance(data.get('locale'), str):
        data['locale'] = data['locale'].replace('_', '-')
    if 'theme' in data:
        data['appearance'] = {'theme': data.pop('theme'), 'contrast': 'high' if data.pop('high_contrast', False) else 'normal'}
    if isinstance(data.get('quiet_hours'), str):
        start, end = data['quiet_hours'].split('-')
        data['quiet_hours'] = {'start': minutes(start), 'end': minutes(end)}
    data.pop('legacy_sync', None)
    settings = current(data)
    if version < SCHEMA:
        save(path, settings)  # upgrade the file so the next start reads it directly
    return settings


def minutes(clock):
    hours, mins = clock.split(':')
    return int(hours) * 60 + int(mins)


def save(path, settings):
    """Check `settings` against schema 3 and write it to `path`."""
    data = current(settings)
    with open(path, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=2, sort_keys=True)
        file.write('\n')


def read(path):
    with open(path, encoding='utf-8') as file:
        text = file.read()
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise SettingsError(f'not valid JSON: {exc}') from None
    if not isinstance(data, dict):
        raise SettingsError('the settings file must hold a JSON object')
    return data


def current(data):
    """Check a dict against schema 3. Return a new dict with every schema 3 key and the unknown keys."""
    schema = data.get('schema', SCHEMA)
    if not is_int(schema) or schema != SCHEMA:
        raise SettingsError(f'bad schema number: {schema!r}')
    result = {key: copy.deepcopy(value) for key, value in data.items() if key != 'schema' and key not in DEFAULTS}
    result['schema'] = SCHEMA
    result['notifications'] = members(data, 'notifications', {'email': is_bool, 'push': is_bool})
    result['appearance'] = members(data, 'appearance', {'theme': one_of('light', 'dark', 'system'),
                                                        'contrast': one_of('normal', 'high')})
    result['timeout_ms'] = value(data, 'timeout_ms', lambda v: is_int(v) and 1000 <= v <= 600000)
    result['locale'] = value(data, 'locale', lambda v: isinstance(v, str) and LOCALE.match(v))
    result['quiet_hours'] = quiet_hours(data.get('quiet_hours'))
    return result


def members(data, key, rules):
    given = data.get(key, {})
    if not isinstance(given, dict) or set(given) - set(rules):
        raise SettingsError(f'bad {key}: {given!r}')
    result = dict(DEFAULTS[key])
    for name, valid in rules.items():
        if name in given:
            if not valid(given[name]):
                raise SettingsError(f'bad {key}.{name}: {given[name]!r}')
            result[name] = given[name]
    return result


def value(data, key, valid):
    if key not in data:
        return DEFAULTS[key]
    if not valid(data[key]):
        raise SettingsError(f'bad {key}: {data[key]!r}')
    return data[key]


def quiet_hours(hours):
    if hours is None:
        return None
    if (not isinstance(hours, dict) or set(hours) != {'start', 'end'}
            or not all(is_int(t) and 0 <= t <= 1439 for t in hours.values()) or hours['start'] == hours['end']):
        raise SettingsError(f'bad quiet_hours: {hours!r}')
    return {'start': hours['start'], 'end': hours['end']}


def is_int(v):
    return type(v) is int


def is_bool(v):
    return type(v) is bool


def one_of(*choices):
    return lambda v: isinstance(v, str) and v in choices
