# SQL Agent Template

Reusable Chainlit + Smolagents starter for natural-language-to-SQL workflows. The app keeps a guarded read-only SQL tool, limits access to an explicit table allowlist, and enriches schema context with structured docs plus optional Markdown reference files.

## What it includes
- Chainlit chat interface in [app.py](/Users/alfredo/text2sql_agent/text2sql-agent/app.py)
- Runtime and prompt assembly in [sql_agent/agent.py](/Users/alfredo/text2sql_agent/text2sql-agent/sql_agent/agent.py)
- Database access and SQL policy enforcement in [sql_agent/database.py](/Users/alfredo/text2sql_agent/text2sql-agent/sql_agent/database.py)
- Documentation ingestion from cached JSON, PDF files, Coda, and Markdown files in [sql_agent/docs_loader.py](/Users/alfredo/text2sql_agent/text2sql-agent/sql_agent/docs_loader.py)
- Reusable schema-to-Markdown export pipeline in [sql_agent/schema_markdown.py](/Users/alfredo/text2sql_agent/text2sql-agent/sql_agent/schema_markdown.py)

## Install
Use Python 3.11 or 3.12.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configure
Copy the example environment file and fill in your values:

```bash
cp .env.example .env
```

Required variables:
- `APP_DATABASE_URL` (preferred) or legacy `DATABASE_URL`, or the component variables `DATABASE_HOST`, `DATABASE_PORT`, `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_NAME`
- `ALLOWED_TABLES` as comma-separated table names or `schema.table` values
- `MODEL_PROVIDER` and the matching credentials such as `OPENAI_API_KEY` or `HF_TOKEN`

Optional database settings:
- `SQL_DIALECT` for SQLGlot parsing, for example `postgres`, `mysql`, `snowflake`, or `redshift`
- `DATABASE_LABEL` for UI and prompt wording
- Legacy `REDSHIFT_*` variables are still accepted for backward compatibility

Optional documentation settings:
- `PDF_DOC_PATHS` for one or more schema PDFs
- `PDF_DOCS_DIR` to auto-discover PDFs under a directory
- `MARKDOWN_DOCS_DIR` for one or more `.md` files that should be injected into the agent context
- `SCHEMA_DOCS_JSON_PATH` for cached extracted schema docs
- `CODA_API_TOKEN`, `CODA_DOC_ID`, `CODA_TABLE_ID_OR_NAME`, and the column mapping variables if you want to load structured docs from Coda

## Markdown docs
Place reusable database notes in [docs/markdown](/Users/alfredo/text2sql_agent/text2sql-agent/docs/markdown). Every `.md` file in that directory tree is loaded and appended to the agent context as additional documentation. This is additive, so Markdown works alongside cached JSON, PDF parsing, and Coda-based structured docs.

Recommended content for Markdown files:
- business metric definitions
- join caveats
- table ownership notes
- known filters or data quality warnings
- example query patterns

## Run the app
```bash
./scripts/run_chainlit.sh
```

Then open `http://localhost:8001` (or the local Chainlit URL shown in the terminal).


## Evaluate against a benchmark
Use the evaluator to run the implemented agent on a benchmark dataset and save machine-readable reports.

```bash
source .venv/bin/activate
python scripts/evaluate_agent.py \
  --dataset chinook_benchmark_v1.json.rtf \
  --output-dir eval_results
```

Outputs:
- JSON report with per-question details plus summary metrics
- CSV report for spreadsheet analysis

Useful option for a quick smoke test:
```bash
python scripts/evaluate_agent.py --max-items 3
```

## Refresh cached PDF docs
```bash
source .venv/bin/activate
python scripts/extract_pdf_docs.py
```

## Export schema docs from any database
The project now includes a generic Markdown exporter that can introspect a live database and emit `.md` files that the agent can load directly.

```bash
source .venv/bin/activate
python scripts/export_database_docs.py \
  --database-url "${APP_DATABASE_URL:-$DATABASE_URL}" \
  --output-dir docs/markdown/generated \
  --database-label "Production analytics database" \
  --allowed-tables "$ALLOWED_TABLES"
```

What this writes:
- `schema_overview.md`
- one Markdown file per table under `tables/`
- `allowed_tables.txt` with the discovered allowlist

For SQLite, the exporter works with Python's built-in `sqlite3`. For other databases, install the correct SQLAlchemy driver for your target system.

## Chinook example setup
Chinook is included as a documented example so you can stand the app up quickly against a known sample database while keeping the codebase generic.

Official source: [lerocha/chinook-database](https://github.com/lerocha/chinook-database)

### Option A: quickest path with the bundled SQLite asset
1. Clone the Chinook repository:
   ```bash
   git clone https://github.com/lerocha/chinook-database.git
   ```
2. From this project root, create the local example database and Markdown docs:
   ```bash
   python scripts/setup_chinook_sqlite.py --chinook-repo-dir /absolute/path/to/chinook-database
   ```
3. Open the generated file [examples/chinook/.env.generated](/Users/alfredo/text2sql_agent/text2sql-agent/examples/chinook/.env.generated) after the script runs.
4. Copy those values into your root `.env`.
5. Start the app:
   ```bash
   ./scripts/run_chainlit.sh
   ```

The setup script:
- copies `Chinook_Sqlite.sqlite` into `examples/chinook/data/chinook.sqlite`
- exports agent-ready Markdown docs into `examples/chinook/docs/markdown`
- generates an environment snippet with `APP_DATABASE_URL`, `SQL_DIALECT=sqlite`, `MARKDOWN_DOCS_DIR`, and `ALLOWED_TABLES`

### Option B: use another Chinook variant
If you want PostgreSQL, MySQL, SQL Server, or another supported engine from Chinook:
1. Use the official Chinook SQL script for your engine from the upstream repository.
2. Create the database with your usual database tool.
3. Set `APP_DATABASE_URL` (or `DATABASE_URL`), `SQL_DIALECT`, and `ALLOWED_TABLES`.
4. Run `python scripts/export_database_docs.py` against that database to generate the Markdown docs the agent will consume.
5. Point `MARKDOWN_DOCS_DIR` at the generated output directory.

## Assumptions and limitations
- The SQL guard allows only a single read-only `SELECT` or `WITH ... SELECT` statement.
- Allowed tables may be schema-qualified or schema-less, depending on the target database.
- Database connectivity depends on a working SQLAlchemy URL and driver for your target database.
- Markdown docs are injected as raw context, so concise, well-structured notes work best.
