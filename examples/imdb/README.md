# IMDb Example

This folder is the reusable example workspace for connecting the app to an IMDb-backed Postgres database.

Important:

- This workflow is for **non-commercial use only** with IMDb's official non-commercial datasets.
- IMDb data is not bundled in this repository.
- Review IMDb's official terms before use:
  - https://developer.imdb.com/non-commercial-datasets/
  - https://datasets.imdbws.com/

## What gets created here

- `docs/markdown/`: generated schema documentation for the allowlisted IMDb Postgres objects
- `.env.generated`: ready-to-copy environment values for the IMDb example
- `.env.gemma4`: ready-to-run Ollama example for the IMDb database
- `imdb_smoke_eval.json`: lightweight smoke dataset for validating the agent against IMDb

The default setup now targets `imdb_core` plus selected `imdb_raw` tables.

## Quick setup

1. Build the database using the sibling repo at `/Users/alfredo/text2sql_agent/imdb-postgres-dataset`.
2. From the project root, run:
   `python scripts/setup_imdb_postgres.py`
3. Copy the generated values from `examples/imdb/.env.generated` into your root `.env`.
4. Start the app with `./scripts/run_chainlit.sh`.

The generated profile uses the local Postgres connection that works in this environment:

- `postgresql+psycopg2://alfredo@localhost:5432/imdb`

## Smoke evaluation

```bash
cp examples/imdb/.env.generated .env
python scripts/evaluate_agent.py \
  --dataset examples/imdb/imdb_smoke_eval.json \
  --output-dir eval_results/imdb_smoke \
  --max-items 5
```

## Companion repo

The IMDb database build pipeline and licensing/compliance docs live in the separate sibling repo:

- local path: `/Users/alfredo/text2sql_agent/imdb-postgres-dataset`
- GitHub repo: `https://github.com/Qalfredo/imdb-postgres-dataset`
