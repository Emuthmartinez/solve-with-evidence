import json
import os
import tempfile
import unittest

from settings.store import SettingsError, UnsupportedVersion, load, save

FULL = {
    'schema': 3,
    'notifications': {'email': False, 'push': True},
    'timeout_ms': 20000,
    'appearance': {'theme': 'dark', 'contrast': 'high'},
    'locale': 'ja-JP',
    'quiet_hours': {'start': 1380, 'end': 360},
}


class Store(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = os.path.join(folder.name, 'settings.json')

    def write(self, data):
        with open(self.path, 'w', encoding='utf-8') as file:
            file.write(data if isinstance(data, str) else json.dumps(data))
        return self.path

    def test_a_full_file_loads_as_written(self):
        self.assertEqual(load(self.write(FULL)), FULL)

    def test_missing_keys_take_their_defaults(self):
        self.assertEqual(load(self.write({'schema': 3, 'locale': 'fr-FR'})), {
            'schema': 3,
            'notifications': {'email': True, 'push': True},
            'timeout_ms': 10000,
            'appearance': {'theme': 'system', 'contrast': 'normal'},
            'locale': 'fr-FR',
            'quiet_hours': None,
        })

    def test_unknown_keys_are_kept(self):
        self.assertEqual(load(self.write(dict(FULL, sidebar={'open': True})))['sidebar'], {'open': True})

    def test_a_bad_value_is_rejected(self):
        with self.assertRaises(SettingsError):
            load(self.write(dict(FULL, appearance={'theme': 'blue'})))

    def test_a_newer_schema_is_unsupported(self):
        with self.assertRaises(UnsupportedVersion):
            load(self.write({'schema': 4}))

    def test_not_json(self):
        with self.assertRaises(SettingsError):
            load(self.write('{"schema": 3'))

    def test_save_then_load(self):
        save(self.path, FULL)
        self.assertEqual(load(self.path), FULL)


if __name__ == '__main__':
    unittest.main()
