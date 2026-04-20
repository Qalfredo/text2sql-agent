# Text-to-SQL Agent

A reusable Chainlit + Smolagents starter for natural-language SQL workflows.

It ships with:
- a guarded read-only SQL execution tool,
- explicit table allowlisting,
- optional schema/context enrichment from Markdown,
- local Ollama support for Gemma 4,
- a notebook-friendly benchmarking library with resumable runs.

## Quickstart (Chinook SQLite)

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

3. Copy either example environment into the project root:

```bash
cp examples/chinook/.env.generated .env
```

For local Gemma 4 with Ollama instead:

```bash
cp examples/chinook/.env.gemma4 .env
ollama serve
ollama pull gemma4:e2b
```

4. Start the app:

```bash
./scripts/run_chainlit.sh
```

Open [http://localhost:8001](http://localhost:8001).

## IMDb Postgres Example

An IMDb-backed Postgres example now lives alongside the Chinook demo.

Important:
- This IMDb workflow is for **non-commercial use only** with IMDb's official non-commercial datasets.
- IMDb data is not bundled here.
- Review IMDb's official terms before using the dataset:
  - [IMDb Non-Commercial Datasets](https://developer.imdb.com/non-commercial-datasets/)
  - [IMDb Dataset Files](https://datasets.imdbws.com/)

The IMDb dataset build pipeline lives in the separate sibling repo at `/Users/alfredo/text2sql_agent/imdb-postgres-dataset` and is published at [Qalfredo/imdb-postgres-dataset](https://github.com/Qalfredo/imdb-postgres-dataset).

High-level flow:

```bash
cd /Users/alfredo/text2sql_agent/imdb-postgres-dataset
cp .env.example .env
python scripts/bootstrap.py

cd /Users/alfredo/text2sql_agent/text2sql-agent
python scripts/setup_imdb_postgres.py
cp examples/imdb/.env.generated .env
./scripts/run_chainlit.sh
```

The default IMDb profile uses:
- `APP_DATABASE_URL=postgresql+psycopg2://alfredo@localhost:5432/imdb`
- `SQL_DIALECT=postgres`
- generated markdown docs under `examples/imdb/docs/markdown`

The default IMDb allowlist includes:
- `imdb_core.title_genre`
- `imdb_core.title_director`
- `imdb_core.title_writer`
- `imdb_core.name_known_for_title`
- `imdb_core.name_primary_profession`
- `imdb_raw.title_basics`
- `imdb_raw.name_basics`
- `imdb_raw.title_ratings`
- `imdb_raw.title_principals`
- `imdb_raw.title_episode`

## Using Any Database

The runtime is database-agnostic. A database becomes usable by the agent when you provide a database profile with:

- a reachable `APP_DATABASE_URL`
- the matching `SQL_DIALECT`
- a human-readable `DATABASE_LABEL`
- an explicit `ALLOWED_TABLES` list
- generated schema docs in `MARKDOWN_DOCS_DIR`

The intended workflow is:

1. point the app at a real SQLAlchemy-compatible connection URL
2. choose a tight allowlist of queryable tables
3. export markdown schema docs with `scripts/export_database_docs.py` or a database-specific setup script
4. copy the generated `.env` snippet into `.env`
5. run the app

Chinook and IMDb are worked examples of the same pattern:
- Chinook shows a small SQLite profile
- IMDb shows a larger schema-qualified Postgres profile

## Configuration

Create your environment file:

```bash
cp .env.example .env
```

Minimum required settings:
- `APP_DATABASE_URL` or `DATABASE_URL`
- `ALLOWED_TABLES`
- `MODEL_PROVIDER`
- provider credentials/settings for the selected backend

Optional database settings:
- `SQL_DIALECT`
- `DATABASE_LABEL`
- `MARKDOWN_DOCS_DIR`

Supported model providers:
- `openai`
- `huggingface`
- `ollama`
- `google`

## Gemma 4 with Ollama

Ollama support is built in and validated at startup.

```bash
ollama serve
ollama pull gemma4:e2b
```

Then use:

```bash
MODEL_PROVIDER=ollama
MODEL_ID=gemma4:e2b
OLLAMA_BASE_URL=http://localhost:11434/v1
```

Notes:
- Ollama currently exposes the Gemma 4 edge tags `gemma4:e2b` and `gemma4:e4b`.
- The app also accepts `gemma4:2b` and `gemma4:4b` as friendly aliases and normalizes them to the real Ollama tags.
- If Ollama is unreachable or the model is missing, startup errors now include the exact `ollama pull ...` command to run.

## Google backend

For a hosted Google path, the agent supports `MODEL_PROVIDER=google` through Smolagents' `LiteLLMModel`.

```bash
MODEL_PROVIDER=google
MODEL_ID=gemini/gemini-2.5-flash-lite
GOOGLE_API_KEY=your-key
```

`MODEL_ID` stays fully configurable, so you can point it at any Google model exposed through your LiteLLM setup.

## Repository layout

Core runtime:
- `app.py`: Chainlit entrypoint
- `sql_agent/agent.py`: model + tool wiring
- `sql_agent/config.py`: environment loading and provider config
- `sql_agent/database.py`: SQL guard and DB execution
- `sql_agent/evaluation/`: reusable benchmark library

Scripts:
- `scripts/run_chainlit.sh`: local launcher
- `scripts/setup_chinook_sqlite.py`: Chinook SQLite bootstrap
- `scripts/setup_imdb_postgres.py`: IMDb Postgres example bootstrap
- `scripts/export_database_docs.py`: generic DB-to-Markdown exporter
- `scripts/evaluate_agent.py`: CLI wrapper over the evaluation library

Examples:
- `examples/chinook/.env.generated`: SQLite demo config
- `examples/chinook/.env.gemma4`: SQLite + Gemma 4 Ollama config
- `examples/imdb/.env.generated`: IMDb Postgres demo config
- `examples/imdb/.env.gemma4`: IMDb Postgres + Gemma 4 Ollama config
- `notebooks/01_single_agent_benchmark.ipynb`: single-config analysis
- `notebooks/02_compare_agents.ipynb`: side-by-side comparison workflow

## Benchmarking

The evaluation logic now lives in `sql_agent.evaluation` and can be used from Python, notebooks, or the CLI.

CLI:

```bash
python scripts/evaluate_agent.py \
  --dataset chinook_benchmark_v1.json.rtf \
  --output-dir eval_results
```

IMDb smoke evaluation:

```bash
cp examples/imdb/.env.generated .env
python scripts/evaluate_agent.py \
  --dataset examples/imdb/imdb_smoke_eval.json \
  --output-dir eval_results/imdb_smoke \
  --max-items 5
```

This smoke dataset checks that the agent can operate against the IMDb profile for joins, ratings, genres, principals, episodes, and known-for relationships.

Python:

```python
from sql_agent.config import load_settings
from sql_agent.evaluation import BenchmarkRunner

settings = load_settings()
runner = BenchmarkRunner(
    agent_config=settings,
    dataset="chinook_benchmark_v1.json.rtf",
    output_dir="eval_results",
    max_workers=1,
    timeout_per_question=60,
)
result = runner.run()
df = result.to_dataframe()
```

Comparison workflow:

```python
from sql_agent.config import Settings
from sql_agent.evaluation import ComparisonSuite

suite = ComparisonSuite(dataset="chinook_benchmark_v1.json.rtf")
suite.add_config("gemma4-local", Settings(...))
suite.add_config("qwen3-hf", Settings(...))
results = suite.run_all()
comparison_df = suite.compare(results)
```

What gets saved:
- resumable item-level JSON under `eval_results/<run_id>/items/`
- aggregate reports in `eval_results/<run_id>/`
- legacy top-level JSON and CSV files from `scripts/evaluate_agent.py`

Metrics include:
- exact match
- unordered row match
- scalar answer text match
- execution accuracy
- latency p50 / p95
- SQL validity rate

## Notebook extras

Install notebook dependencies only when you need them:

```bash
pip install -e ".[eval]"
```

## Markdown documentation workflow

Markdown files under `docs/markdown` or your configured `MARKDOWN_DOCS_DIR` are injected into agent context.

Good candidates:
- business definitions
- join caveats
- data quality notes
- filter caveats
- sample query guidance

## Export schema docs from any database

```bash
python scripts/export_database_docs.py \
  --database-url "${APP_DATABASE_URL:-$DATABASE_URL}" \
  --output-dir docs/markdown/generated \
  --database-label "Production analytics database" \
  --allowed-tables "$ALLOWED_TABLES"
```

Generated files:
- `schema_overview.md`
- `tables/*.md`
- `allowed_tables.txt`

## Known limitations

- The SQL tool still allows only a single read-only `SELECT` or `WITH ... SELECT` statement.
- Small local models like `gemma4:e2b` are convenient for setup and smoke tests, but they can trail larger hosted models on multi-join reasoning and strict instruction following.
- End-to-end benchmark speed and quality depend heavily on local hardware when using Ollama.
