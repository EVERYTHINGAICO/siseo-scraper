# SISEO CICE Dataset v0.1

Export generated from the local SISEO PostgreSQL database on 2026-09-26.

## Scope

This dataset contains judicial agreement records collected from the public CICE portal of the Poder Judicial de la Federacion de Mexico and normalized by SISEO.

## Tables

| File | Rows | Description |
|---|---:|---|
| `acuerdos.csv.gz` | 159,247 | Judicial agreement records collected from CICE |
| `organos.csv.gz` | 981 | Institutional organ catalog available in the local database |
| `scraper_fechas.csv.gz` | 2,224 | Scraper progress and date coverage metadata |

## Agreement Coverage

- Agreement rows: 159,247
- Distinct expedientes: 8,034
- Organs with collected agreements: 20
- Date range in `acuerdos.fecha`: 2016-01-29 to 2026-06-30

## Columns

### acuerdos.csv.gz

`id`, `circuito_id`, `organo_id`, `expediente`, `tipo`, `quejoso`, `autoridad`, `fecha`, `fecha_busqueda`, `row_index`, `sintesis_corta`, `sintesis_completa`, `detalle_url`, `scraped_at`

### organos.csv.gz

`id`, `circuito_id`, `circuito_nombre`, `nombre`, `fecha_inicio`

### scraper_fechas.csv.gz

`organo_id`, `fecha`, `completo`, `sin_acuerdos`, `total_acuerdos`, `scraped_at`

## Integrity

```text
fe4c27ef6256029ffa3a318a1153c885c8286f91b0c7aea0ee7fcafcc8bae63d  acuerdos.csv.gz
0bed65c18e3c32add7be3c012db69b68b12c215136fc4a2a90870d808a2bb46c  organos.csv.gz
9793681285d356935285b55930fa216fa03a4da9ef21351dddd18f7cc42dfe52  scraper_fechas.csv.gz
```

## Methodology

The dataset follows the SISEO institutional key:

```text
circuito_id -> organo_id -> expediente
```

Collection state is tracked in `scraper_fechas`, and agreement inserts are idempotent in the application database through the `(organo_id, fecha_busqueda, row_index)` uniqueness rule.

## Notes

- This release contains public judicial data collected from CICE plus scraper metadata.
- User account data, private tracked expediente tables, environment variables, browser profiles, local credentials and runtime artifacts are not included.
- The repository contains the code and technical methodology; this Release contains the dataset artifact.
