# LEAPs Screener Tool

A web-based tool for screening stocks and finding LEAPs (Long-term Equity AnticiPation Securities) opportunities, featuring AI-powered company analysis.

## Project Structure

- `backend/`: FastAPI Python application
- `frontend/`: React + Vite application

## Prerequisites

- Python 3.8+
- Node.js & npm
- A Google Cloud API Key for Gemini (AI descriptions)

## Getting Started

### 1. Backend Setup

The backend handles data fetching, calculation, and the AI integration.

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create and activate a virtual environment (optional but recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   Create a `.env` file in the `backend/` directory:
   ```bash
   touch .env
   ```
   Add your Gemini API Key to the `.env` file:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```

5. Start the server:
   ```bash
   python main.py
   # OR
   uvicorn main:app --reload
   ```
   The backend will be running at `http://localhost:8000`. API docs are available at `http://localhost:8000/docs`.

### 2. Frontend Setup

The frontend is a React application that provides the user interface.

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install Node dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```
   The frontend will be running at `http://localhost:5173` (typically).

## Usage

1. Open your browser and go to the frontend URL (e.g., `http://localhost:5173`).
2. The dashboard will load with default stock data.
3. Use the interface to screen for stocks and view details, including AI-generated descriptions.

## Notes

- The backend uses `yfinance` to fetch stock data.
- The AI descriptions are generated using Google's Gemini Pro via the `google-generativeai` library.
- **Version Control**: Use `jujutsu` (jj) instead of raw Git for version control operations in this repository.
