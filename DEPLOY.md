# Deployment Guide: Hybrid Screener Logic

This guide sets up your "Hybrid" architecture:
1.  **Cloud Database** (PostgreSQL) - Stores the data.
2.  **Home PC Worker** - Calculates data daily & updates DB.
3.  **Cloud Web App** - Serves the fast, pre-calculated results.

---

## Part 1: Cloud Database (Supabase)
1.  Go to [Supabase](https://supabase.com/) and create a Free Project.
2.  Go to **Project Settings > Database > Connection Strings**.
3.  Copy the **URI**. It looks like:
    `postgresql://postgres.xxxx:[YOUR-PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres`
    *Note: Use the "Transaction Mode" port (6543) if offered, or standard 5432.*

---

## Part 2: Home PC Worker Setup
1.  Open your `.env` file in `backend/.env`.
2.  Add/Update the `DATABASE_URL`:
    ```ini
    DATABASE_URL="postgresql://postgres.xxxx:[YOUR-PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
    ```
3.  **Run Migrations**: Create the tables in the Cloud DB.
    ```bash
    cd backend
    ../venv/bin/alembic upgrade head
    ```
4.  **Run Ingestion**: Fill the database with initial data.
    ```bash
    ../venv/bin/python3 ingest.py
    ```
    *(This will take 10-20 minutes for 1500 stocks).*

5.  **Schedule it**:
    -   **Linux**: Add to crontab (`crontab -e`). Run daily at 6 PM.
        ```bash
        0 18 * * * cd /path/to/screen/backend && ../venv/bin/python3 ingest.py >> /tmp/ingest.log 2>&1
        ```

---

## Part 3: Deploy API to Cloud (Render.com)
1.  Push your code to GitHub.
2.  Go to [Render.com](https://render.com) > **New +** > **Web Service**.
3.  Connect your GitHub Repo.
4.  **Settings**:
    -   **Runtime**: Python 3
    -   **Root Directory**: `backend`
    -   **Build Command**: `pip install -r requirements.txt`
    -   **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5.  **Environment Variables**:
    -   Add `DATABASE_URL` (Same Supabase URL).
    -   Add `GEMINI_API_KEY` (if you want AI analysis).

6.  **Deploy!**
    -   Your URL will be `https://screen-xyz.onrender.com/screen`.
    -   It will serve the data your Home PC uploaded.
