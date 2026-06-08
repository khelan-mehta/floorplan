# Run locally (native, no Docker)

The stack runs natively on Windows: a **portable MongoDB** + per-service Python venvs + the Vite web
app. (Docker/`pnpm dev` also works once Docker Desktop is running.)

## Demo login
- URL: **http://localhost:5173**
- Email: **demo@example.com**  ·  Password: **demo-password**
- A demo project ("Demo 2-Bed Apartment") is seeded with a 10×8 m outer geometry + a 2-bed area
  programme. Click **Generate** to get scored options; switch 2D⇆3D; edit room types / auto-furnish;
  use the **Export** menu for DWG/DXF, IFC (Revit), or CSV.

## Start everything (PowerShell, one command per server — keep each window open)

```powershell
$R = "C:\Users\NG\Desktop\floorplangenerator"
$MONGOD = "C:\Users\NG\mongodb\mongodb-win32-x86_64-windows-8.0.4\bin\mongod.exe"

# 1. MongoDB (portable)
& $MONGOD --dbpath "C:\Users\NG\mongodb\data" --port 27017 --bind_ip 127.0.0.1

# 2. domain services (each in its own terminal)
cd $R\services\generator; .\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8001
cd $R\services\codes;     .\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8002   # Phase 07 RAG
cd $R\services\validator; .\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8003   # code scoring
cd $R\services\export;    .\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8005
cd $R\services\geometry;  .\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8004   # optional

# 3. API gateway
cd $R\apps\api
$env:MONGODB_URI='mongodb://localhost:27017'; $env:MONGODB_DB='fpg'
$env:JWT_SECRET='dev-secret-key-at-least-32-bytes-long-1234'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000

# 4. web app
cd $R\apps\web
$env:VITE_API_BASE_URL='http://localhost:8000'
node node_modules/vite/bin/vite.js --host --port 5173
```

## First-time setup (already done on this machine)
- Python venvs per service: `cd <svc>; <python3.12> -m venv .venv; .\.venv\Scripts\python -m pip install -e ".[dev]"`
  (api also needs `motor`; geometry needs `mapbox-earcut`).
- Seed demo data (after Mongo is up):
  `cd apps\api; $env:MONGODB_URI='mongodb://localhost:27017'; $env:MONGODB_DB='fpg'; .\.venv\Scripts\python -m app.seed`

## Ports
api :8000 (`/docs`) · web :5173 · generator :8001 · codes :8002 · validator :8003 · geometry :8004 · export :8005 · mongod :27017

## Notes
- **Building codes (Phase 07) are wired.** The `codes` service (port 8002) ingests a seeded
  jurisdiction (`generic-ibc-2021`), serves "ask the code" semantic search with citations
  (`POST /codes/query`, proxied by the API), and extracts a published RuleSet. The demo project is
  seeded with that jurisdiction, so **Generate** now scores each plan against the code via the
  `validator` service; the Codes tab answers code questions and the workspace shows a compliance
  panel. Set `OPENAI_API_KEY` (in repo-root `.env`) to extract rules with the OpenAI API; otherwise a
  deterministic offline extractor is used. (Raw LLM-extracted rules stay in review/approve state
  before publish — retrieval and the seeded compliance ruleset are independent of the LLM.)
- Generation calls the generator service; if it's down the API falls back to a trivial single-room
  stub. If the validator/codes are down, plans fall back to the generator's layout score.
