# Scalable Data Integration System

A small, dependency-free, config-driven ETL framework that integrates data from
heterogeneous sources (CSV, JSON Lines, SQL databases) into one unified warehouse.

## Architecture

```
 Sources (connectors)        Transform (parallel)            Load
 +------------+            +----------------------+      +------------------+
 | CSV (CRM)  |--batches-->| schema mapping       |      | SQLite warehouse |
 | SQLite     |            | type casting/cleaning|----->| idempotent UPSERT|
 | JSON Lines |            | validation -> rejects|      | rejects table    |
 +------------+            +----------------------+      +------------------+
     streaming              thread/process pool            single writer
```

## Scalability features
- **Streaming batches** - constant memory regardless of source size.
- **Parallel transforms** - worker pool (`thread` or `process`) with a bounded in-flight window (back-pressure).
- **Pluggable connectors** - add a source by subclassing `Source` and registering it in `sdis/connectors/__init__.py`.
- **Config-driven schema mapping** - onboard a new source/dataset without code changes.
- **Entity merging** - records from different systems with the same key are merged (`COALESCE` upsert).
- **Idempotent loads** - re-running never duplicates data.
- **Dead-letter table** - invalid records go to `rejects` with the reason and raw payload.

## Quick start
```bash
python scripts/generate_sample_data.py          # optional: regenerate (args: customers orders)
python run_pipeline.py                          # run with config/pipeline.json
python run_pipeline.py --workers 8 --executor process --batch-size 2000
python -m unittest discover -s tests -v         # run tests
```

Inspect results:
```bash
sqlite3 output/warehouse.db "SELECT source_system, COUNT(*) FROM customers GROUP BY 1;"
sqlite3 output/warehouse.db "SELECT reason, COUNT(*) FROM rejects GROUP BY 1 ORDER BY 2 DESC LIMIT 5;"
```

## Project layout
```
sdis/connectors/   csv / json / sqlite sources + factory
sdis/transform.py  mapping, casting, validation
sdis/loader.py     upserts + rejects
sdis/pipeline.py   orchestration, parallelism, metrics
sdis/main.py       CLI
config/           pipeline.json (sources, mappings, targets)
scripts/          sample data generator
tests/            unit + end-to-end tests
```

## Mapping rule options
`from`, `type` (str|int|float|email|date), `required`, `default`, `case` (upper|lower|title), `min`.

## Ideas to extend
Add Postgres/REST/Kafka connectors, swap SQLite for Postgres/BigQuery in `loader.py`,
schedule with cron/Airflow, add metrics, add schema-evolution checks.
