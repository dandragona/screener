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

### 1. Backend & Database Setup

1.  Navigate to the backend directory:
    ```bash
    cd backend
    ```

2.  Create and activate a virtual environment:
    ```bash
    python3 -m venv ../venv
    source ../venv/bin/activate
    ```

3.  Install Python dependencies:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Database Setup**:
    Initialize the local SQLite database:
    ```bash
    alembic upgrade head
    ```

5.  **Ingest Data**:
    Running the screener logic takes time. Run the ingestion script to populate your database:
    ```bash
    python ingest.py
    ```
    *(Note: This might take 10-15 minutes for the full S&P 1500)*

6.  Set up environment variables:
    Create `backend/.env`:
    ```ini
    GEMINI_API_KEY=your_api_key_here
    # DATABASE_URL=sqlite:///./screen.db  (Default, no need to change for local)
    ```

7.  Start the API server:
    ```bash
    uvicorn main:app --reload
    ```
    The backend will be running at `http://localhost:8000`.

### 2. Frontend Setup

1.  Navigate to the frontend directory:
    ```bash
    cd frontend
    ```

2.  Install & Start:
    ```bash
    npm install
    npm run dev
    ```
    The app will be running at `http://localhost:5173`.

## Deployment (Production)

This app is designed to run in a Hybrid mode:
1.  **Database**: Supabase / Neon (Cloud Postgres).
2.  **Worker**: Your Home PC running `ingest.py` daily.
3.  **Web App**: Cloud Hosting (Render/Railway).

See [DEPLOY.md](DEPLOY.md) for full instructions.

## Notes

- **Version Control**: Use `jujutsu` (jj).
