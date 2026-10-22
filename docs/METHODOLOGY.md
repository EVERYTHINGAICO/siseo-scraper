# Methodology and Provenance

## Source and Collection

The collector's configured source is the SISE Internet judicial-agreement search page:

https://www.dgej.cjf.gob.mx/SiseInternet/consulta/busquedaacuerdos.aspx

Historical SISEO documentation refers to the source ecosystem as CICE. This repository preserves the exact configured URL rather than asserting that source branding or availability is unchanged.

The standalone script opens Chrome, connects Playwright over CDP, selects a circuit/court/date, waits for manual CAPTCHA completion, searches result tables, and attempts to retrieve full agreement text through detail links or popups. It saves JSON and CSV. Spanish source selectors and field names are retained for compatibility.

The released dataset was collected by the broader SISEO workflow and exported from local PostgreSQL on 2026-09-26, according to its manifest. It is not represented as the output of a newly executed standalone scrape. The exact historical collection/export environment is not fully reproduced here.

## Institutional Identity

Use `circuito_id -> organo_id -> expediente` when comparing cases. A case-number string may recur in different institutions. Court/date/row-index was the original database's import uniqueness key; this is different from a global judicial-document identifier.

`fecha` is a publication date; `fecha_busqueda` is the queried/collected date in the source pipeline; `scraped_at` records ingestion time. Do not treat these as interchangeable timestamps.

## Release Contents

The snapshot contains agreement records, a court catalog, and collection-progress rows. It excludes Supabase user tables, OAuth settings, application frontend/backend, browser profiles, and the separately maintained client tracking list. Agreement text can contain party names because those are fields from source records.

The initial release is distributed as gzip CSV with manifest and SHA256 hashes. A versioned metadata file and a standard-library verification script support repeatable checks. These checks establish artifact integrity and descriptive coverage, not correctness of every judicial record.

## Scope and Limitations

Coverage is uneven and historical: 20 court bodies have agreement records while the catalog contains 981 entries. A catalog entry is not evidence of collection coverage. Absence of a record is not evidence that a judicial event did not occur.

The publication includes normalized agreement text and source links, not original PDF documents. Some detail extraction can fail or return incomplete text. Current source availability, selector compatibility, CAPTCHA behavior, and live collection have not been independently validated in this release.

The snapshot is useful for exploring data engineering, text processing, institutional normalization, and reproducibility. It does not replace official judicial sources or establish complete national coverage.
