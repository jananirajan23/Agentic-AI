# Reviewer-Lens — Frontend

React + Vite + TypeScript single-page app for the Reviewer-Lens pre-review tool.

## Setup

```bash
cd frontend
npm install
npm run dev
```

The dev server runs at `http://localhost:5173`.

## Talking to the backend

`vite.config.ts` proxies any request to `/api/*` to `http://localhost:8000` (the
FastAPI backend), so the frontend code just calls relative paths like
`fetch('/api/review')` — no CORS configuration or base URL needed in dev. Make
sure the backend is running first (`cd ../backend && uvicorn app:app --reload`).

For a production build, either serve the built `dist/` files behind the same
reverse proxy as the API, or point `src/api.ts` at an absolute backend URL.

## Structure

- `src/api.ts` — fetch wrappers for the three backend endpoints (`start review`,
  `poll status`, `health`) plus the report download URL helper.
- `src/App.tsx` — the four-state flow: Upload → Processing → Results → Error.
- `src/components/` — `UploadPanel`, `ProcessingView`, `ScoreDashboard`,
  `FlagsList`, `SuggestionsList`.

## Styling

Tailwind CSS (v3, classic `tailwind.config.js` + `postcss.config.js`) with a
custom type scale and a restrained slate/teal palette defined in
`tailwind.config.js` — intentionally not the default indigo/purple look.
Charts use Recharts. Fonts are Inter (UI) and Source Serif 4 (headings),
loaded from Google Fonts in `index.html`.
