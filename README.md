# Text-to-SQL Agent

A reusable Chainlit + Smolagents starter for natural-language SQL workflows.

It ships with:
- a guarded read-only SQL execution tool,
- explicit table allowlisting,
- optional schema/context enrichment from Markdown,
- helper scripts for Chinook demo setup and benchmark evaluation.

## Quickstart (Chinook SQLite)
If you want the fastest path to a running demo, use the included Chinook setup.

1. Create and activate a virtual environment:
```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Clone Chinook and generate local assets:
```bash
git clone https://github.com/lerocha/chinook-database.git
python scripts/setup_chinook_sqlite.py --chinook-repo-dir /absolute/path/to/chinook-database
```

3. Copy settings from `examples/chinook/.env.generated` into your root `.env`.

4. Start the app:
```bash
./scripts/run_chainlit.sh
```

Open `http://localhost:8001`.

## Configuration
Create your environment file:
```bash
cp .env.example .env
```

Minimum required settings:
- `APP_DATABASE_URL` (preferred) or `DATABASE_URL` (legacy fallback)
- `ALLOWED_TABLES` (comma-separated table names or `schema.table`)
- `MODEL_PROVIDER` and provider credentials (`OPENAI_API_KEY` or `HF_TOKEN`)

Optional database settings:
- `SQL_DIALECT` (for SQLGlot parsing, e.g. `postgres`, `mysql`, `sqlite`)
- `DATABASE_LABEL`
- legacy `REDSHIFT_*` variables are still supported

Optional documentation settings:
- `MARKDOWN_DOCS_DIR`

## Repository layout
Core runtime:
- `app.py`: Chainlit entrypoint
- `sql_agent/agent.py`: model + tool wiring
- `sql_agent/database.py`: SQL guard and DB execution
- `sql_agent/docs_loader.py`: Markdown docs ingestion
- `sql_agent/schema_markdown.py`: schema introspection and Markdown export

Scripts:
- `scripts/run_chainlit.sh`: local launcher
- `scripts/setup_chinook_sqlite.py`: Chinook SQLite bootstrap
- `scripts/export_database_docs.py`: generic DB-to-Markdown exporter
- `scripts/evaluate_agent.py`: benchmark evaluator

## Markdown documentation workflow
Markdown files under `docs/markdown` (or your configured `MARKDOWN_DOCS_DIR`) are injected into agent context.

Good candidates for Markdown docs:
- business definitions
- join caveats
- data quality notes
- filter caveats
- sample query guidance

## Benchmark evaluation
Run the evaluator against the included benchmark dataset:

```bash
source .venv/bin/activate
python scripts/evaluate_agent.py \
  --dataset chinook_benchmark_v1.json.rtf \
  --output-dir eval_results
```

Outputs:
- JSON report with summary + per-question details
- CSV report for spreadsheet analysis

Quick smoke test:
```bash
python scripts/evaluate_agent.py --max-items 3
```

## Export schema docs from any database
Use the schema exporter to generate Markdown context from your own database:

```bash
source .venv/bin/activate
python scripts/export_database_docs.py \
  --database-url "${APP_DATABASE_URL:-$DATABASE_URL}" \
  --output-dir docs/markdown/generated \
  --database-label "Production analytics database" \
  --allowed-tables "$ALLOWED_TABLES"
```

Generated files:
- `schema_overview.md`
- `tables/*.md` (one file per table)
- `allowed_tables.txt`

## Chinook notes
The Chinook helper script writes:
- `examples/chinook/data/chinook.sqlite`
- `examples/chinook/docs/markdown/*`
- `examples/chinook/.env.generated`

If you prefer another engine (PostgreSQL/MySQL/SQL Server/etc.), create the DB from the official Chinook SQL scripts and run `scripts/export_database_docs.py` against it.

## Guardrails and limitations
- Only a single read-only `SELECT` or `WITH ... SELECT` statement is allowed.
- Queries against non-allowlisted tables are blocked.
- Connectivity depends on a valid SQLAlchemy URL and installed driver.
- Markdown context is injected as raw text, so concise, specific docs perform best.
