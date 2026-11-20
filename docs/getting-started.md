# Getting started

1. Install Python 3.11+ and Git.
2. Get an Anthropic API key (console.anthropic.com) and keep it private.
3. Clone, create a venv, install:
   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -e ".[dev]"
   pre-commit install
   copy .env.example .env
   ```
4. Edit `.env` and set `ANTHROPIC_API_KEY`.
5. Verify: `pytest` (no key needed, API is mocked).
6. Run the CLI: `budget-ai --help`.

## Troubleshooting

- *Activate.ps1 blocked*: run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
- *`budget-ai` not found*: the venv isn't activated, or re-run `pip install -e ".[dev]"`.
- *Authentication error*: check `.env` is in the repo root and the key is valid.
