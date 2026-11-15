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
OLD_LOCALE = re.compile(r'[a-z]{2,3}(_[A-Z]{2})?\Z')
DIGITS = re.compile(r'[0-9]+\Z')
QUIET = re.compile(r'([01][0-9]|2[0-3]):([0-5][0-9])-([01][0-9]|2[0-3]):([0-5][0-9])\Z')

# The keys each schema defines. CHANGELOG.md: 1.0.0 and 1.4.0 for schema 1; 2.0.0, 2.2.0 and 2.5.0 for schema 2.
KEYS = {
    1: {'notify', 'timeout', 'theme', 'lang', 'legacy_sync'},
    2: {'schema', 'notifications', 'timeout_ms', 'theme', 'locale', 'legacy_sync', 'quiet_hours', 'high_contrast'},
    3: {'schema'} | set(DEFAULTS),
}


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
    known = {key: value for key, value in data.items() if key in KEYS[version]}
    # Unknown keys skip migration. One named like a schema 3 key gives way to the migrated value.
    unknown = {key: value for key, value in data.items() if key not in KEYS[version] and key not in KEYS[3]}
    if version == 1:
        known = upgrade_1(known)
    if version <= 2:
        known = upgrade_2(known)
    known.update(unknown)
    return current(known)


def upgrade_1(old):
    """Schema 1 to schema 2 (CHANGELOG.md, 2.0.0 and 1.3.1)."""
    timeout = old.get('timeout', 30)
    if isinstance(timeout, str) and DIGITS.match(timeout):
        timeout = int(timeout)
    if not is_int(timeout):
        raise SettingsError(f'bad timeout: {timeout!r}')
    new = {'schema': 2, 'timeout_ms': timeout * 1000}
    if 'notify' in old:
        new['notifications'] = {'email': old['notify'], 'push': old['notify']}
    for before, after in (('theme', 'theme'), ('lang', 'locale'), ('legacy_sync', 'legacy_sync')):
        if before in old:
            new[after] = old[before]
    return new


def upgrade_2(old):
    """Check what schema 2 allows and schema 3 does not, then migrate to schema 3 (CHANGELOG.md, 3.0.0)."""
    theme = old.get('theme', 'light')
    locale = old.get('locale', 'en_US')
    hours = old.get('quiet_hours')
    if theme not in ('light', 'dark') or not isinstance(locale, str) or not OLD_LOCALE.match(locale):
        raise SettingsError(f'bad theme or locale: {theme!r}, {locale!r}')
    if any(key in old and not is_bool(old[key]) for key in ('legacy_sync', 'high_contrast')):
        raise SettingsError('legacy_sync and high_contrast are true or false')
    if hours is not None:
        match = QUIET.match(hours) if isinstance(hours, str) else None
        if not match:
            raise SettingsError(f'bad quiet_hours: {hours!r}')
        start_h, start_m, end_h, end_m = (int(part) for part in match.groups())
        hours = {'start': start_h * 60 + start_m, 'end': end_h * 60 + end_m}
    new = {key: old[key] for key in ('notifications', 'timeout_ms') if key in old}
    new.update(schema=3, locale=locale.replace('_', '-'), quiet_hours=hours,
               appearance={'theme': theme, 'contrast': 'high' if old.get('high_contrast') else 'normal'})
    return new


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
