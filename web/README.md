# stashflow web app

Mobile-first React + Vite frontend for the budget API, built from the team's Figma frames
(Overview, Budgets, Insights, Goals) plus a Receipt screen in the same style.

## Run it

You need Node 20.19+ (or 22.12+) and the Python API.

1. Start the API from the repo root (the folder you cloned the repo into), with the venv active:

   ```powershell
   cd path\to\dh399-ai-budgeting
   .venv\Scripts\Activate.ps1
   budget-ai-api
   ```

   If PowerShell refuses to run `Activate.ps1`, allow local scripts once with
   `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

   It listens on `http://127.0.0.1:8000` and uses `DATABASE_PATH` from `.env`.

2. In another terminal, start the web app:

   ```powershell
   cd path\to\dh399-ai-budgeting\web
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

## Demo data

To show the app without your real spending, create a demo database that looks like the
Figma frames. Its dates follow the current day, so it always shows "this month":

```powershell
.venv\Scripts\Activate.ps1
budget-ai seed-demo
budget-ai-api --db data/demo.db
```

`seed-demo` writes to `data/demo.db` (never to `DATABASE_PATH`) and won't overwrite an
existing file; run it with `--force` to start fresh before a presentation.

## Demo away from home (Tailscale)

The model, API and web app all run on the home PC; a laptop or phone anywhere just opens
the app in a browser over [Tailscale](https://tailscale.com/download).

One-time setup:

1. Install Tailscale on the home PC, laptop and phone, signed in to the same account.
2. On the home PC, find its address with `tailscale ip -4` (it starts with `100.`).
3. On the home PC, in an admin PowerShell, allow the web app's port from Tailscale only:

   ```powershell
   New-NetFirewallRule -DisplayName "stashflow via Tailscale" -Direction Inbound -Protocol TCP -LocalPort 5173 -RemoteAddress 100.64.0.0/10 -Action Allow -Profile Any
   ```

Before the demo, on the home PC (set it to never sleep):

1. Open LM Studio, load the model and start its server.
2. From the repo root, activate the venv and start the API on fresh demo data:

   ```powershell
   .venv\Scripts\Activate.ps1
   budget-ai seed-demo --force
   budget-ai-api --db data/demo.db
   ```
3. In `web/`: `npx vite --host` (in PowerShell, `npm run dev -- --host` loses the `--host`)
4. Do one scan to warm the model up; the first scan after loading is much slower.

On the laptop or phone, with Tailscale connected, open `http://<home PC's 100.x address>:5173`.
Use the IP address rather than the device name: the Vite dev server rejects unknown host names.

## Layout

| Path | Contents |
|---|---|
| `src/api.ts` | Typed calls to every API endpoint the app uses |
| `src/categories.ts` | Friendly names, icons and colours for the backend's category keys (`housing` → Rent, `utilities` → Bills, `dining` → Dining out) |
| `src/hooks.ts` | Selected month (shared by every screen) and the `useApi` loading hook |
| `src/components/` | Header with month picker and notifications, bottom nav, shared UI pieces |
| `src/pages/` | One file per screen, plus `Activity.tsx` for "See all" |
| `src/styles.css` | All styles; colours at the top match the Figma frames |
