# Data Dictionary

All files are gzip-compressed CSV. Field identifiers preserve the original source workflow's Spanish names.

## acuerdos.csv.gz

| Column | Meaning |
|---|---|
| `id` | Exported local database row identifier |
| `circuito_id` | Circuit identifier |
| `organo_id` | Court-body identifier |
| `expediente` | Case-number string; not globally unique |
| `tipo` | Source record type |
| `quejoso` | Source party/applicant text |
| `autoridad` | Source authority text |
| `fecha` | Publication date |
| `fecha_busqueda` | Date queried/collected in the historical pipeline |
| `row_index` | Position in a court/date result set |
| `sintesis_corta` | Short agreement summary |
| `sintesis_completa` | Extracted full summary/agreement text when available |
| `detalle_url` | Captured source detail link |
| `scraped_at` | Local ingestion timestamp |

There is no `es_cliente` column in the released agreements CSV. Official party text may include personal information; it is different from a private user/client tracking table.

## organos.csv.gz

`id`: court-body identifier; `circuito_id`: circuit identifier; `circuito_nombre`: circuit name; `nombre`: court-body name; `fecha_inicio`: configured collection-start date where present.

## scraper_fechas.csv.gz

`organo_id`: court identifier; `fecha`: queried date; `completo`: historical completion flag; `sin_acuerdos`: historical no-records flag; `total_acuerdos`: recorded count; `scraped_at`: ingestion timestamp. Treat flags as pipeline state, not independent proof of source completeness.

## Standalone Collector Output

The standalone script emits `indice`, `numero`, `tipo`, `expediente`, `quejoso`, `autoridad`, `fecha`, `sintesis_corta`, `sintesis_completa`, `expediente_detalle`, `fecha_acuerdo_detalle`, and `detalle_url`. This output is not identical to the normalized PostgreSQL export schema. Do not merge the formats without an explicit mapping.
