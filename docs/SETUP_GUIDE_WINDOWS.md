# Windows Setup Guide (PowerShell)

Beginner-friendly, step by step. Hinglish notes included where it helps.

## Prerequisites

1. **Python 3.11 or 3.12** — [python.org/downloads](https://python.org/downloads).
   Install karte waqt "Add Python to PATH" checkbox zaroor check karein.
2. **Node.js 20 LTS** — [nodejs.org](https://nodejs.org) (for the frontend).
3. **Git** (optional, for cloning/pushing to GitHub).
4. **VS Code** with the Python extension (optional but recommended).

Check installs:
```powershell
python --version
node --version
npm --version
```

## Step 1 — Unzip the project

Unzip `ProcureMind_Professional_Project.zip` somewhere easy, e.g. `C:\Projects\ProcureMind`.

## Step 2 — Backend setup

```powershell
cd C:\Projects\ProcureMind\backend

# Virtual environment banayein (isolated Python environment, taaki aapke
# system-wide Python packages se conflict na ho)
python -m venv venv

# Activate karein — har naye terminal mein yeh command chalani padti hai
venv\Scripts\activate

# Dependencies install karein (requirements.txt mein sab kuch listed hai)
pip install -r requirements.txt
```

If `pip install` is slow or fails on a package, try:
```powershell
pip install --upgrade pip
pip install -r requirements.txt --no-cache-dir
```

## Step 3 — Configure environment

```powershell
copy .env.example .env
```

Open `.env` in VS Code. Default settings use SQLite (no database server
needed) and run in deterministic mode (no LLM key needed to start). You
can add an API key later — see README.md's "Adding an LLM key later"
section.

## Step 4 — Database

No separate step needed for SQLite — tables are created automatically the
first time the backend starts. (If you want PostgreSQL instead, see
`DEPLOYMENT_GUIDE.md`.)

## Step 5 — Load demo data (optional but recommended)

```powershell
python seed_demo_data.py
```

Isse 3 synthetic (fake, demo-only) vendors aur ek sample procurement
request create hoti hai, poora multi-agent evaluation chalta hai, aur
terminal mein ranking print hoti hai. Yeh confirm karta hai ki sab kuch
sahi se kaam kar raha hai.

## Step 6 — Start the backend

```powershell
uvicorn app.main:app --reload
```

Backend ab `http://localhost:8000` par chal raha hai. API docs dekhne ke
liye browser mein `http://localhost:8000/docs` kholein (FastAPI auto-generates
this — Swagger UI).

## Step 7 — Frontend setup (new terminal)

```powershell
cd C:\Projects\ProcureMind\frontend
npm install
npm run dev
```

Frontend `http://localhost:5173` par available hoga. Browser mein kholein.

## Step 8 — Run tests

```powershell
cd C:\Projects\ProcureMind\backend
venv\Scripts\activate
python -m pytest tests/ -v
```

Expected: `46 passed`.

## Local URLs summary

| Service | URL |
|---|---|
| Backend API | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/docs |
| Frontend dashboard | http://localhost:5173 |

## Troubleshooting

- **"python is not recognized"** — Python PATH mein add nahi hua. Python
  installer phir se chalayein aur "Add to PATH" check karein.
- **`pip install` fails on a specific package** — usually a build-tools
  issue. Try `pip install --only-binary :all: -r requirements.txt`.
- **Port already in use** — kisi aur app ne port 8000 ya 5173 le liya hai.
  `uvicorn app.main:app --reload --port 8001` se alag port use karein
  (aur frontend's `.env` mein `VITE_API_URL` update karein).
- **CORS error in browser console** — backend's `.env` mein `CORS_ORIGINS`
  check karein, isme frontend ka URL included hona chahiye.
