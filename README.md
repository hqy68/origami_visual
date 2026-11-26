# Origami Pattern Studio

Type an object or upload a photo. You get a crease pattern built from a traditional base, folding steps, and links to existing designs.

- `backend/`: Python (FastAPI) API, catalog scraper, crease-pattern generator
- `frontend/`: Next.js (TypeScript) website

## Run locally

Backend (port 8000):

```sh
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
echo "ANTHROPIC_API_KEY=sk-..." > .env   # optional: enables photo recognition
.venv/bin/uvicorn app.main:app --reload --port 8000
```

Frontend (port 3000):

```sh
cd frontend
npm install
npm run dev
```

Open http://localhost:3000. The Next.js server proxies `/api/*` to the backend; set `API_URL` if the backend runs somewhere else.

Refresh the catalog with `cd backend && .venv/bin/python -m scraper`.
