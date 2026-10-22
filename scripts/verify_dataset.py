"""Verify a downloaded SISEO snapshot without third-party dependencies."""
import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path


def verify(directory):
    metadata = json.loads((Path(__file__).resolve().parents[1] / 'docs/dataset-metadata.json').read_text())
    cases, courts, dates = set(), set(), []
    for name, expected in metadata.items():
        if name == 'coverage':
            continue
        path = directory / name
        checksum = hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                checksum.update(chunk)
        if checksum.hexdigest() != expected['sha256']:
            raise ValueError(f'{name}: SHA256 mismatch')
        with gzip.open(path, 'rt', encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != expected['columns']:
                raise ValueError(f'{name}: column mismatch')
            count = 0
            for row in reader:
                if None in row or any(value is None for value in row.values()):
                    raise ValueError(f'{name}: malformed row {count + 1}')
                count += 1
                if name == 'acuerdos.csv.gz':
                    cases.add(row['expediente'])
                    courts.add(row['organo_id'])
                    if row['fecha']:
                        dates.append(row['fecha'])
        if count != expected['rows']:
            raise ValueError(f'{name}: expected {expected["rows"]} rows, got {count}')
        print(f'OK {name}: {count:,} rows; SHA256 and columns verified')
    observed = {
        'distinct_case_number_strings': len(cases),
        'court_bodies_with_agreements': len(courts),
        'publication_date_min': min(dates) if dates else None,
        'publication_date_max': max(dates) if dates else None,
    }
    if observed != metadata['coverage']:
        raise ValueError('Agreement coverage differs from recorded metadata')
    print('OK coverage:', json.dumps(observed))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path, help='Folder containing the three downloaded .csv.gz files')
    args = parser.parse_args()
    try:
        verify(args.directory)
    except (OSError, ValueError, csv.Error) as exc:
        parser.exit(1, f'Verification failed: {exc}\n')
