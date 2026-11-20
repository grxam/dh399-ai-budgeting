# Team workflow

## Suggested split

| Person | Owns |
|--------|------|
| A | Vision agent: prompts, accuracy, evaluation set |
| B | Database + pipeline: schema, queries, ingestion |
| C | Reasoning agent: prompts, advice quality, tools |
| D (optional) | UI / docs / testing |

Everyone can touch everything via PRs; owners review changes in their area (add them to `.github/CODEOWNERS`).

## Rhythm

- Track work in GitHub Issues; use a GitHub Project board (Backlog → In progress → In review → Done).
- Short weekly sync; post blockers in the issue with the `blocked` label.
- Keep PRs small (< ~300 lines) so reviews happen within a day.

## Review checklist

- Does CI pass? Are there tests?
- Are schema or prompt changes explained?
- Any secrets, real receipts, or `.db` files?
- Is the code understandable without the author present?

## Git cheatsheet

```powershell
git checkout main; git pull
git checkout -b feat/12-short-name
git add -A; git commit -m "feat: ..."
git push -u origin HEAD
# open a PR:
gh pr create --fill
# stay up to date:
git fetch origin; git rebase origin/main
```
