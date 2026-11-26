# Architecture

```
                ┌──────────────┐   Receipt (pydantic)   ┌──────────┐
 receipt image ▶│ Vision Agent │──────────────────────▶ │ Database │
                └──────────────┘                         └────┬─────┘
                                                              │ aggregates + recent receipts (JSON)
                                                         ┌────▼────────────┐
                                           question ───▶ │ Reasoning Agent │──▶ advice
                                                         └─────────────────┘
```

## Components

### Vision agent (`src/budget_ai/vision/`)
Sends the image to a vision-capable model with a strict JSON-only prompt. Output is validated into a `Receipt`; invalid output raises instead of being stored silently.

### Database (`src/budget_ai/db/`)
SQLite with `receipts` and `line_items`. Swappable later (Postgres) behind the `Database` class.

### Reasoning agent (`src/budget_ai/reasoning/`)
Builds a JSON context from the database (category totals + recent receipts) and asks the model a question. Instructed to ground claims in the data and not to give licensed financial advice.

### Shared contract (`src/budget_ai/models.py`)
`Receipt` and `LineItem` are the only interface between components, so teammates can work in parallel.

## Design decisions

| Decision | Reason |
|----------|--------|
| Validate model output with Pydantic | LLMs return malformed data; fail loudly |
| SQLite | Zero setup for a team project |
| Agents take injected clients | Tests mock the API |
| Fixed category list | Consistent aggregation for the reasoning agent |

## Ideas / roadmap

- Budgets and savings goals table; reasoning agent compares spend vs. budget
- ~~Human review step when vision `confidence` is low~~
- Duplicate-receipt detection
- Web UI (Streamlit / FastAPI) and image upload
- Evaluation set of synthetic receipts with expected JSON to measure vision accuracy
- Reasoning agent tools (SQL queries) instead of a context dump
