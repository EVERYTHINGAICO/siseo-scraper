import argparse
import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import scraper


class ScraperTests(unittest.TestCase):
    def test_full_row_retains_case_and_source_text(self):
        values = ['1', 'ACUERDO', '123/2026', 'Synthetic party', 'Synthetic authority', '01/05/2026', 'Synthetic summary']
        result = scraper.inferir_campos(values)
        self.assertEqual((result['expediente'], result['fecha'], result['sintesis_corta']), ('123/2026', '01/05/2026', 'Synthetic summary'))

    def test_short_row_finds_case_and_date_without_shifting_fields(self):
        result = scraper.inferir_campos(['123/2026', '01/05/2026', 'Synthetic summary'])
        self.assertEqual(result['expediente'], '123/2026')
        self.assertEqual(result['fecha'], '01/05/2026')
        self.assertEqual(result['quejoso'], '')

    def test_empty_row_is_supported(self):
        self.assertEqual(scraper.inferir_campos([])['expediente'], '')

    def test_text_cleanup_preserves_unicode_and_line_boundaries(self):
        self.assertEqual(scraper.limpiar_texto('  Síntesis\xa0 judicial\n\n texto  '), 'Síntesis  judicial\ntexto')

    def test_result_listing_is_not_mistaken_for_detail(self):
        self.assertTrue(scraper.parece_pagina_lista('Lista de acuerdos. Para ver la síntesis completa, abrir enlace.'))
        self.assertFalse(scraper.parece_pagina_lista('Synthetic agreement for 123/2026.'))

    def test_csv_and_json_export_preserve_quotes_newlines_and_unicode(self):
        with tempfile.TemporaryDirectory() as directory:
            previous = scraper.OUT_DIR
            scraper.OUT_DIR = Path(directory)
            record = {'indice': 0, 'expediente': '123/2026', 'sintesis_completa': 'Síntesis, "quoted"\nsecond line'}
            try:
                scraper.guardar_resultados([record], 'synthetic')
                saved = json.loads((Path(directory) / 'synthetic.json').read_text())
                with (Path(directory) / 'synthetic.csv').open(encoding='utf-8-sig', newline='') as stream:
                    rows = list(csv.DictReader(stream))
                self.assertEqual(saved[0]['sintesis_completa'], record['sintesis_completa'])
                self.assertEqual(rows[0]['sintesis_completa'], record['sintesis_completa'])
            finally:
                scraper.OUT_DIR = previous

    def test_invalid_date_and_negative_limits_rejected(self):
        for value in ['31/02/2026', '2026-01-01']:
            with self.assertRaises(argparse.ArgumentTypeError):
                scraper.valid_date(value)
        with self.assertRaises(argparse.ArgumentTypeError):
            scraper.nonnegative_int('-1')
        for value in ['-1', 'nan', 'inf']:
            with self.assertRaises(argparse.ArgumentTypeError):
                scraper.nonnegative_float(value)

    def test_help_is_available_without_browser_setup(self):
        result = subprocess.run([sys.executable, str(Path(scraper.__file__)), '--help'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn('--circuit', result.stdout)
        self.assertIn('--max-records', result.stdout)


if __name__ == '__main__':
    unittest.main()
