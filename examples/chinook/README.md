# Chinook Example

This folder is the reusable example workspace for the Chinook sample database.

## What gets created here

- `data/chinook.sqlite`: local SQLite database copied from the official Chinook repository
- `docs/markdown/`: generated schema documentation for the agent
- `.env.generated`: ready-to-copy environment values for this example
- `.env.gemma4`: ready-to-run local Ollama example using Gemma 4 E2B

## Quick setup

1. Clone the official Chinook repository somewhere on your machine:
   `git clone https://github.com/lerocha/chinook-database.git`
2. From the project root, run:
   `python scripts/setup_chinook_sqlite.py --chinook-repo-dir /absolute/path/to/chinook-database`
3. Copy the generated values from `examples/chinook/.env.generated` into your root `.env`.
4. Start the app with `./scripts/run_chainlit.sh`.

## Gemma 4 local example

If you want the Chinook demo to use Ollama locally:

1. Start Ollama with `ollama serve`
2. Pull the lightest Gemma 4 edge model with `ollama pull gemma4:e2b`
3. Copy `examples/chinook/.env.gemma4` into your root `.env`
4. Start the app with `./scripts/run_chainlit.sh`
