# Contributing

Thanks for helping build this! This guide keeps a small group moving without stepping on each other.

## Setup

See the Quick start in [README.md](README.md). Install the pre-commit hooks (`pre-commit install`) so formatting issues are caught before CI.

## Workflow

1. Pick or create an issue and assign yourself.
2. Branch from an up-to-date `main`:
   ```powershell
   git checkout main; git pull
   git checkout -b feat/42-receipt-tax-parsing
   ```
   Branch names: `feat/`, `fix/`, `docs/`, `chore/` + issue number + short slug.
3. Commit small and often. Use [Conventional Commits](https://www.conventionalcommits.org/): `feat: parse tax line`, `fix: handle blank date`.
4. Push and open a **pull request** using the template. Link the issue (`Closes #42`).
5. Get **one approval**; CI (lint + tests) must be green.
6. **Squash-merge**. The branch is deleted automatically.

Never push directly to `main`.

## Code standards

- Python 3.11+, formatted and linted with `ruff` (`ruff format .` and `ruff check . --fix`).
- Type hints on public functions.
- Tests live in `tests/`. **Tests never call the real Anthropic API**; mock the client (see `tests/test_reasoning.py`).
- Keep the three components decoupled: they talk only through the schemas in `src/budget_ai/models.py`. Changing a schema affects everyone, so raise it in an issue first.

## Prompts

Prompts are code. Changes to the vision or reasoning system prompts go through PR review, and the PR should show before/after output on a synthetic example.

## Secrets and data

- Never commit `.env`, API keys, `.db` files, or real receipts.
- If you accidentally commit a secret, tell the team immediately and **rotate the key**. Deleting the commit isn't enough.

## Getting help

Use GitHub Discussions for questions and issues for work items.
