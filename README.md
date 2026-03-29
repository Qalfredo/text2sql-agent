# SQL Agent Template

Reusable Chainlit + Smolagents starter for natural-language-to-SQL workflows. The app keeps a guarded read-only SQL tool, limits access to an explicit table allowlist, and enriches schema context with structured docs plus optional Markdown reference files.

## What it includes
- Chainlit chat interface in [app.py](/Users/alfredo/text2sql_agent/sql_agent_template/app.py)
- Runtime and prompt assembly in [sql_agent/agent.py](/Users/alfredo/text2sql_agent/sql_agent_template/sql_agent/agent.py)
- Database access and SQL policy enforcement in [sql_agent/database.py](/Users/alfredo/text2sql_agent/sql_agent_template/sql_agent/database.py)
- Documentation ingestion from cached JSON, PDF files, Coda, and Markdown files in [sql_agent/docs_loader.py](/Users/alfredo/text2sql_agent/sql_agent_template/sql_agent/docs_loader.py)

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
- `DATABASE_URL` or the component variables `DATABASE_HOST`, `DATABASE_PORT`, `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_NAME`
- `ALLOWED_TABLES` as comma-separated `schema.table` values
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
Place reusable database notes in [docs/markdown](/Users/alfredo/text2sql_agent/sql_agent_template/docs/markdown). Every `.md` file in that directory tree is loaded and appended to the agent context as additional documentation. This is additive, so Markdown works alongside cached JSON, PDF parsing, and Coda-based structured docs.

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

Then open the local Chainlit URL shown in the terminal.

## Refresh cached PDF docs
```bash
source .venv/bin/activate
python scripts/extract_pdf_docs.py
```

## Assumptions and limitations
- The SQL guard allows only a single read-only `SELECT` or `WITH ... SELECT` statement.
- Allowed tables must be schema-qualified.
- Database connectivity depends on a working SQLAlchemy URL and driver for your target database.
- Markdown docs are injected as raw context, so concise, well-structured notes work best.
