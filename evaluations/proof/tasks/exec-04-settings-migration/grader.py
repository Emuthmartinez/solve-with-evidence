import atexit
import copy
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from gradelib import main, raises

# Hidden settings files go in the grader's own directory, one folder each, never in the work directory.
TMP = tempfile.mkdtemp(prefix='settings-grader-')
atexit.register(shutil.rmtree, TMP, True)
FOLDERS = []


def path_for(name='settings.json'):
    folder = os.path.join(TMP, str(len(FOLDERS)))
    os.mkdir(folder)
    FOLDERS.append(folder)
    return os.path.join(folder, name)


def write(data):
    """A str is written as it is, anything else as JSON."""
    path = path_for()
    with open(path, 'w', encoding='utf-8') as file:
        file.write(data if isinstance(data, str) else json.dumps(data))
    return path


def load(s, data):
    return s.load(write(data))


def rejected(s, data):
    return raises(s.SettingsError, s.load, write(data))


def defaults():
    return {'schema': 3, 'notifications': {'email': True, 'push': True}, 'timeout_ms': 10000,
            'appearance': {'theme': 'system', 'contrast': 'normal'}, 'locale': 'en-US', 'quiet_hours': None}


def notify(s):
    return all(load(s, {'notify': flag})['notifications'] == {'email': flag, 'push': flag} for flag in (False, True))


def seconds(s):
    return load(s, {'timeout': 45})['timeout_ms'] == 45000 and load(s, {'timeout': 600})['timeout_ms'] == 600000


def hyphenated(s):
    return (load(s, {'lang': 'pt_BR'})['locale'] == 'pt-BR' and load(s, {'lang': 'fil'})['locale'] == 'fil'
            and load(s, {'schema': 2, 'locale': 'de_DE'})['locale'] == 'de-DE')


def hyphen_in_schema_3(s):
    return rejected(s, {'schema': 3, 'locale': 'pt_BR'}) and load(s, {'schema': 3, 'locale': 'pt-BR'})['locale'] == 'pt-BR'


def timeout_default(s):
    return [load(s, data)['timeout_ms'] for data in ({'notify': True}, {'schema': 2}, {'schema': 3})] == [30000, 10000, 10000]


def theme_default(s):
    files = ({'notify': True}, {'schema': 2}, {'schema': 3})
    return [load(s, data)['appearance']['theme'] for data in files] == ['light', 'light', 'system']


def string_timeout(s):
    return load(s, {'timeout': '45'})['timeout_ms'] == 45000 and load(s, {'timeout': '120'})['timeout_ms'] == 120000


def other_timeout_strings(s):
    files = [{'schema': 2, 'timeout_ms': '45000'}, {'schema': 3, 'timeout_ms': '45000'}]
    files += [{'timeout': text} for text in ('45s', ' 45', '+45', '4_5', '4.5', '')]
    return all(rejected(s, data) for data in files)


def migrated_checked(s):
    files = [{'theme': 'blue'}, {'timeout': -5}, {'timeout': 0}, {'timeout': 601}, {'timeout': True}, {'timeout': 45.0},
             {'notify': 1}, {'notify': 'yes'}, {'lang': 'pt_br'}, {'schema': 2, 'timeout_ms': 500},
             {'schema': 2, 'notifications': {'email': 'no'}}, {'schema': 2, 'theme': 'blue'}]
    return all(rejected(s, data) for data in files)


def only_schema_3_values(s):
    files = [{'theme': 'system'}, {'schema': 2, 'theme': 'system'}, {'lang': 'en-GB'}, {'schema': 2, 'locale': 'en-GB'},
             {'schema': 2, 'quiet_hours': {'start': 1320, 'end': 420}}]
    return all(rejected(s, data) for data in files)


def quiet_minutes(s):
    cases = {'13:05-14:10': {'start': 785, 'end': 850}, '22:30-07:00': {'start': 1350, 'end': 420},
             '00:00-23:59': {'start': 0, 'end': 1439}}
    return (all(load(s, {'schema': 2, 'quiet_hours': text})['quiet_hours'] == want for text, want in cases.items())
            and load(s, {'schema': 2, 'quiet_hours': None})['quiet_hours'] is None
            and load(s, {'schema': 2})['quiet_hours'] is None)


def quiet_invalid(s):
    values = ('25:00-07:00', '22:00-07:60', '22:00', '7:00-08:00', '22:00-22:00', '22:00 - 07:00', 2200)
    return all(rejected(s, {'schema': 2, 'quiet_hours': value}) for value in values)


def contrast(s):
    files = ({'schema': 2, 'high_contrast': True}, {'schema': 2, 'high_contrast': False}, {'schema': 2})
    return ([load(s, data)['appearance']['contrast'] for data in files] == ['high', 'normal', 'normal']
            and load(s, {'schema': 2, 'theme': 'dark', 'high_contrast': True})['appearance'] == {'theme': 'dark', 'contrast': 'high'})


def legacy_dropped(s):
    return all('legacy_sync' not in load(s, data) for data in ({'legacy_sync': True}, {'schema': 2, 'legacy_sync': False}))


def legacy_kept(s):
    return load(s, {'schema': 3, 'legacy_sync': True}).get('legacy_sync') is True


def newer_key_in_schema_1(s):
    result = load(s, {'notify': False, 'high_contrast': True})
    return result.get('high_contrast') is True and result['appearance']['contrast'] == 'normal'


def older_keys_in_newer_files(s):
    two = load(s, {'schema': 2, 'notify': False, 'lang': 'pt_BR', 'timeout': 45, 'locale': 'de_DE'})
    three = load(s, {'schema': 3, 'theme': 'blue', 'notify': 'x', 'high_contrast': True})
    return (two.get('notify') is False and two.get('lang') == 'pt_BR' and two.get('timeout') == 45
            and two['notifications'] == {'email': True, 'push': True} and two['locale'] == 'de-DE'
            and three.get('theme') == 'blue' and three.get('notify') == 'x' and three.get('high_contrast') is True
            and three['appearance'] == {'theme': 'system', 'contrast': 'normal'})


def named_like_schema_3(s):
    result = load(s, {'notify': False, 'timeout': 20, 'notifications': {'email': True, 'push': True},
                      'quiet_hours': '22:00-07:00', 'timeout_ms': 5000})
    return (result['notifications'] == {'email': False, 'push': False} and result['quiet_hours'] is None
            and result['timeout_ms'] == 20000)


def unknown_kept(s):
    window = {'x': 120, 'y': 80, 'size': [1280, 800]}
    files = ({'notify': True, 'window': window, 'last_report': None}, {'schema': 2, 'window': window, 'last_report': None},
             {'schema': 3, 'window': window, 'last_report': None})
    results = [load(s, data) for data in files]
    return all(r.get('window') == window and 'last_report' in r and r['last_report'] is None for r in results)


def nested_defaults(s):
    three = load(s, {'schema': 3, 'notifications': {'email': False}, 'appearance': {'contrast': 'high'}})
    two = load(s, {'schema': 2, 'notifications': {'push': False}})
    return (three['notifications'] == {'email': False, 'push': True}
            and three['appearance'] == {'theme': 'system', 'contrast': 'high'}
            and two['notifications'] == {'email': True, 'push': False})


def no_write(s):
    for data in ({'notify': False, 'timeout': 45, 'lang': 'pt_BR', 'legacy_sync': True},
                 {'schema': 2, 'quiet_hours': '08:00-12:00', 'locale': 'pt_BR'}):
        path = write(data)
        before = Path(path).read_bytes()
        s.load(path)
        if Path(path).read_bytes() != before or os.listdir(os.path.dirname(path)) != ['settings.json']:
            return False
    return True


def newer_schema(s):
    return (raises(s.UnsupportedVersion, s.load, write({'schema': 4}))
            and raises(s.UnsupportedVersion, s.load, write({'schema': 17, 'hologram': True})))


def settings_error_only(s, data):
    try:
        s.load(write(data))
    except s.UnsupportedVersion:
        return False
    except s.SettingsError:
        return True
    except Exception:
        return False
    return False


def malformed_schema(s):
    return all(settings_error_only(s, {'schema': value}) for value in (0, -1, 3.0, 2.0, 4.0, '3', '2', True, False, None, [3]))


def not_an_object(s):
    return all(rejected(s, text) for text in ('', '{', 'dark mode', '[]', '[{"schema": 3}]', '"dark"', 'null', '3'))


def no_shared_state(s):
    before = copy.deepcopy(s.DEFAULTS)
    first = load(s, {'notify': False, 'theme': 'dark'})
    first['notifications']['push'] = 'changed'
    first['appearance']['theme'] = 'changed'
    second = load(s, {'schema': 2, 'high_contrast': True})
    second['notifications']['email'] = 'changed'
    second['appearance']['contrast'] = 'changed'
    third = load(s, {'schema': 3})
    return s.DEFAULTS == before and third == defaults()


def save_migrated(s):
    loaded = load(s, {'notify': False, 'timeout': 45, 'theme': 'dark', 'lang': 'pt_BR', 'legacy_sync': True,
                      'window': {'width': 900}})
    path = path_for()
    s.save(path, loaded)
    raw = json.loads(Path(path).read_text(encoding='utf-8'))
    return raw == loaded and raw['schema'] == 3 and 'notify' not in raw and s.load(path) == loaded


def save_keeps_argument(s):
    given = {'notifications': {'email': False}, 'locale': 'fr-FR', 'sidebar': {'open': True}}
    snapshot = copy.deepcopy(given)
    path = path_for()
    s.save(path, given)
    want = dict(defaults(), notifications={'email': False, 'push': True}, locale='fr-FR', sidebar={'open': True})
    return given == snapshot and s.load(path) == want


CHECKS = [
    ('schema 1 notify sets both notifications', notify),
    ('schema 1 timeout seconds become milliseconds', seconds),
    ('older locales become hyphenated', hyphenated),
    ('schema 3 locale must already be hyphenated', hyphen_in_schema_3),
    ('missing timeout takes the default of its release', timeout_default),
    ('missing theme takes the default of its release', theme_default),
    ('digit string timeout accepted in schema 1', string_timeout),
    ('other timeout strings rejected', other_timeout_strings),
    ('migrated values are checked against schema 3', migrated_checked),
    ('values only schema 3 allows are rejected in older files', only_schema_3_values),
    ('quiet hours become minutes after midnight', quiet_minutes),
    ('invalid quiet hours rejected', quiet_invalid),
    ('high_contrast becomes the contrast', contrast),
    ('legacy_sync dropped from older files', legacy_dropped),
    ('legacy_sync kept in a schema 3 file', legacy_kept),
    ('a schema 2 key stays unknown in a schema 1 file', newer_key_in_schema_1),
    ('older keys stay unknown in newer files', older_keys_in_newer_files),
    ('an unknown key named like a schema 3 key is replaced', named_like_schema_3),
    ('unknown keys survive migration', unknown_kept),
    ('partial nested objects take defaults', nested_defaults),
    ('load does not write the file', no_write),
    ('newer schema raises UnsupportedVersion', newer_schema),
    ('malformed schema number raises SettingsError', malformed_schema),
    ('not a JSON object raises SettingsError', not_an_object),
    ('results share no state', no_shared_state),
    ('save writes migrated settings as schema 3', save_migrated),
    ('save leaves its argument unchanged', save_keeps_argument),
]

if __name__ == '__main__':
    main(CHECKS, 'settings.store')
