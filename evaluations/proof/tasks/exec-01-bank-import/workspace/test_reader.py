import os
import tempfile
import unittest
from datetime import date

from importer import FormatError, Transaction, load

HEADER = 'Booking date;Value date;Reference;Status;Amount;Currency;Memo'


class Load(unittest.TestCase):
    def export(self, *lines):
        folder = tempfile.mkdtemp()
        path = os.path.join(folder, 'export.csv')
        with open(path, 'w', encoding='utf-8', newline='') as file:
            file.write('\r\n'.join((HEADER,) + lines) + '\r\n')
        return path

    def test_booked_records(self):
        path = self.export('02.03.2026;02.03.2026;HB2603020001;B;12,50;EUR;Coffee beans',
                           '02.03.2026;03.03.2026;HB2603020002;B;3,00-;EUR;Card fee',
                           'T;2;9,50')
        self.assertEqual(load(path), [
            Transaction(date(2026, 3, 2), date(2026, 3, 2), 'HB2603020001', 'booked', 1250, 'EUR', 'Coffee beans'),
            Transaction(date(2026, 3, 2), date(2026, 3, 3), 'HB2603020002', 'booked', -300, 'EUR', 'Card fee'),
        ])

    def test_unknown_currency(self):
        path = self.export('02.03.2026;02.03.2026;HB2603020001;B;12,50;XXX;Coffee beans', 'T;1;12,50')
        with self.assertRaises(FormatError):
            load(path)


if __name__ == '__main__':
    unittest.main()
