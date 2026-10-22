# Validation and Limitations

## Artifact Checks

The release files were downloaded from the existing SISEO dataset release, decompressed, and checked against their SHA256 hashes. The review recomputed headers, row counts, distinct case-number strings, court coverage, and minimum/maximum publication dates. Results are recorded in `dataset-metadata.json`.

`python scripts/verify_dataset.py data` repeats those checks using only the standard library. It fails if required files, hashes, headers, row counts, or recorded coverage disagree.

## Software Checks

Offline tests validate full-column/fallback row parsing, source-text cleanup, misleading detail-page rejection, Unicode CSV/JSON export, and command-line input handling. CLI help works without browser dependencies; running collection requires them.

These checks do not establish that the external portal currently accepts the selectors or that every detail link can be extracted. A fresh live scrape was not run for this publication. CAPTCHA completion remains manual. Dependency ranges are not an exact historical lockfile.

## Publication Boundaries

Only selected standalone code, synthetic examples, documentation, and the prepared snapshot artifacts are published here. This repository starts with a clean history and does not copy the application repository's history, authentication settings, client lists, frontend, backend, browser profiles, or diagnostic captures.

Source records can contain names and judicial text. Integrity verification is not legal clearance, anonymization, proof of complete coverage, or a guarantee of record accuracy. The repository's ownership notice does not grant rights over official source material.
