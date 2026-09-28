# ForecastGuard AI — Frontend (React + Vite + Tailwind + Lucide)

Government-style GIS dashboard for SIH 26079. Source lives here; the
**production build is emitted into `../dashboard/`** and served by the Python
backend (`python src/api/server.py` → http://127.0.0.1:8000/).

The previous vanilla-JS dashboard is backed up at `../dashboard-legacy/`.

## Develop

```bash
cd frontend
npm install
# Terminal 1 — backend (provides /api/v1/*)
python ../src/api/server.py
# Terminal 2 — frontend with hot reload + /api proxy to :8000
npm run dev   # → http://127.0.0.1:5173/
```

## Ship (rebuild the bundle the backend serves)

```bash
cd frontend
npm run build   # writes ../dashboard/index.html + ../dashboard/assets/*
```

## Layout & use-flow

`src/` — `App.jsx` (state + 5-step flow) · `api.js` (REST helpers) ·
`lib.js` (FCI tiers, colours, advisories) · `components/`:

| File | Step | What it does |
|---|---|---|
| `chrome.jsx` | always | Gov strip, header, KPI cards, 1→5 stepper, footer |
| `ControlPanel.jsx` | 1–3 | run picker → lead-time scrubber → layer cards + polygon toggle + region search |
| `MapView.jsx` | 4 | Leaflet map (Esri + OSM fallback), warning polygons, per-layer legend |
| `Inspector.jsx` | 4–5 | FCI gauge, metrics, SHAP drivers, advisory, print/GeoJSON/CSV export |

Icons: `lucide-react`. Maps: `leaflet` (plain API in a `useEffect`, no wrapper).
Styling: Tailwind v3 + `tailwind.config.js` (`navy` / `saffron` brand scale).
