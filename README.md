# LEAPs Screener Tool

A high-performance "Hybrid" stock screener.
- **Worker**: Runs daily on a home PC/Server to crunch numbers (Black-Scholes, Scoring).
- **Database**: Stores pre-calculated results (SQLite locally, PostgreSQL in prod).
- **Web App**: Fast, read-only interface served by FastAPI + React.

## Project Structure

- `backend/`: FastAPI application + Ingestion Engine (`ingest.py`)
- `frontend/`: React + Vite application

## Prerequisites

- Python 3.10+
- Node.js & npm
- A Google Cloud API Key for Gemini (AI descriptions)

## Getting Started

### 1. Environment Setup

Create `backend/.env`:
```ini
GEMINI_API_KEY=your_api_key_here
# DATABASE_URL=sqlite:///./screen.db  (Default, no need to change for local)
```

### 2. Ingest Data

Run the ingestion script to populate your database (takes ~10-15m for full S&P 1500):
```bash
./ingestion.sh
```

### 3. Start Servers

Start both the backend (API) and frontend (UI):
```bash
./start_server.sh
```
- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`

## Deployment (Production)

This app is designed to run in a Hybrid mode:
1.  **Database**: Supabase / Neon (Cloud Postgres).
2.  **Worker**: Your Home PC running `ingest.py` daily.
3.  **Web App**: Cloud Hosting (Render/Railway).

See [DEPLOY.md](DEPLOY.md) for full instructions.

## Notes

- **Version Control**: Use `jujutsu` (jj).
