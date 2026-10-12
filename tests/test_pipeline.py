import json
from pathlib import Path
import tempfile
import unittest
from contextlib import closing
from pipeline import canonical_url, connect, ingest, normalize, number

URL = 'https://www.olx.pl/d/oferta/test-IDabc.html'
RAW = dict(price='699 988 zł', tags='Powierzchnia: 46,70 m²\nLiczba pokoi: 3 pokoje',
           offer_title="Mieszkanie O'Connor", location='Warszawa, Wola', active='No')


class PipelineTests(unittest.TestCase):
    def test_polish_values_and_unknown(self):
        row = normalize(URL, RAW)
        self.assertEqual(row['price_grosz'], 69998800)
        self.assertEqual(row['area_m2'], 46.7)
        self.assertEqual(row['rooms'], 3)
        self.assertEqual(row['active'], 0)
        for value in ['Unknown', 'Zapytaj', '-4', 'NaN', '1 000 EUR', 0]:
            self.assertIsNone(number(value))

    def test_otodom_tags(self):
        row = normalize(URL, dict(price='1\u00a0200\u00a0000,50 zł', tags='Powierzchnia\n65,73 m²\nLiczba pokoi\n2'))
        self.assertEqual(row['price_grosz'], 120000050)
        self.assertEqual(row['area_m2'], 65.73)

    def test_canonicalization_and_domain(self):
        self.assertEqual(canonical_url(URL + '?tracking=1#x'), URL)
        with self.assertRaises(ValueError):
            canonical_url('https://olx.pl.evil.example/test')

    def test_idempotence_older_import_and_sql_quotes(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / 'db.sqlite3'
            for _ in range(2):
                ingest({URL: RAW}, 'archive', '2022-11-16', db)
            ingest({URL: dict(RAW, price='5 zł')}, 'archive', '2022-11-15', db)
            with closing(connect(db)) as conn:
                self.assertEqual(conn.execute('SELECT count(*) FROM offers').fetchone()[0], 1)
                row = conn.execute('SELECT * FROM offers').fetchone()
                self.assertEqual(row['title'], "Mieszkanie O'Connor")
                self.assertEqual(row['price_grosz'], 69998800)
                self.assertEqual(conn.execute('SELECT count(*) FROM runs').fetchone()[0], 3)

    def test_reject_and_keep_missing_quality(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / 'db.sqlite3'
            summary = ingest({URL: {'price': 'Unknown'}, 'bad': RAW}, 'test', '2022-11-16', db)
            self.assertEqual(summary, dict(accepted=1, rejected=1, valid=0))
            with closing(connect(db)) as conn:
                self.assertEqual(conn.execute('SELECT count(*) FROM analysis_offers').fetchone()[0], 0)
                self.assertEqual(conn.execute('SELECT count(*) FROM rejected').fetchone()[0], 1)


if __name__ == '__main__':
    unittest.main()