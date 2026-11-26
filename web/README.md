# stashflow web app

Mobile-first React + Vite frontend for the budget API, built from the team's Figma frames
(Overview, Budgets, Insights, Goals) plus a Receipt screen in the same style.

## Run it

You need Node 20+ and the Python API.

1. Start the API from the repo root (with the venv active):

   ```powershell
   budget-ai-api
   ```

   It listens on `http://127.0.0.1:8000` and uses `DATABASE_PATH` from `.env`.

2. In another terminal, start the web app:

   ```powershell
   cd web
   npm install
   npm run dev
   ```

3. Open http://localhost:5173. The app is laid out for a phone; on a desktop browser use
   the device toolbar (F12, then Ctrl+Shift+M) to see it at phone size.

The Vite dev server forwards `/api` to the API, so no CORS setup is needed. To point at an
API somewhere else, set `API_URL` before `npm run dev` (for example
`$env:API_URL = "http://192.168.1.20:8000"`).

Scanning a receipt and the AI tip on Insights call the local model server from `.env`
(`OPENAI_BASE_URL`). A scan can take a couple of minutes on a local model.

## Layout

| Path | Contents |
|---|---|
| `src/api.ts` | Typed calls to every API endpoint the app uses |
| `src/categories.ts` | Friendly names, icons and colours for the backend's category keys (`housing` → Rent, `utilities` → Bills, `dining` → Dining out) |
| `src/hooks.ts` | Selected month (shared by every screen) and the `useApi` loading hook |
| `src/components/` | Header with month picker and notifications, bottom nav, shared UI pieces |
| `src/pages/` | One file per screen, plus `Activity.tsx` for "See all" |
| `src/styles.css` | All styles; colours at the top match the Figma frames |
