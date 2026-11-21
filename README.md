# AI Finance & Budgeting Assistant (DH399)

[![CI](https://github.com/grxam/dh399-ai-budgeting/actions/workflows/ci.yml/badge.svg)](https://github.com/grxam/dh399-ai-budgeting/actions/workflows/ci.yml)

A budgeting app built from two cooperating AI agents and a database:

1. **Vision agent** – reads a photo or screenshot of a receipt and extracts structured data (merchant, date, line items, totals, category).
2. **Database** – stores the extracted receipts and line items (SQLite by default).
3. **Reasoning agent** – reads the stored data and gives budgeting advice (spending patterns, overspending, savings suggestions).

```
 receipt image ──▶ Vision Agent ──▶ validated Receipt ──▶ Database ──▶ Reasoning Agent ──▶ advice
```

See [docs/architecture.md](docs/architecture.md) for details.

## Quick start

Requires Python 3.11+ and an Anthropic API key.

```powershell
git clone https://github.com/grxam/dh399-ai-budgeting.git
cd dh399-ai-budgeting
python -m venv .venv
.venv\Scripts\Activate.ps1          # macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
copy .env.example .env              # then add your ANTHROPIC_API_KEY
pre-commit install
```

Try it:

```powershell
budget-ai ingest data\samples\receipt.jpg   # vision agent -> database
budget-ai summary                           # spending by category
budget-ai advise "Where can I cut spending this month?"
```

Run the checks:

```powershell
pytest
ruff check .
ruff format --check .
```

## Repository layout

| Path | Purpose |
|------|---------|
| `src/budget_ai/vision/` | Vision agent (image → structured receipt) |
| `src/budget_ai/reasoning/` | Reasoning agent (data → advice) |
| `src/budget_ai/db/` | Database schema and queries |
| `src/budget_ai/models.py` | Shared Pydantic schemas – the contract between agents |
| `src/budget_ai/pipeline.py` | Wires the pieces together |
| `src/budget_ai/cli.py` | `budget-ai` command line |
| `tests/` | Unit tests (no network calls; agents are mocked) |
| `data/samples/` | Sample receipts (**synthetic only**, see data policy) |
| `docs/` | Architecture, setup, team workflow, data privacy |
| `.github/` | CI, issue/PR templates, Dependabot |

## Working as a team

Read [CONTRIBUTING.md](CONTRIBUTING.md) and [docs/team-workflow.md](docs/team-workflow.md). Short version: branch from `main`, open a PR, get one review, CI must pass, squash-merge.

## Data & privacy

Never commit real receipts, API keys, or databases. Use synthetic or redacted samples. See [docs/data-privacy.md](docs/data-privacy.md).

> The reasoning agent gives general budgeting suggestions, not licensed financial advice.

## License

[MIT](LICENSE)
