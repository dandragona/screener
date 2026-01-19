#!/bin/bash

# Function to kill background processes on exit
cleanup() {
    echo "Stopping servers..."
    kill $(jobs -p) 2>/dev/null
    wait
}

# Trap SIGINT (Ctrl+C) and SIGTERM
trap cleanup SIGINT SIGTERM

# Check if venv exists, if so activate it
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r backend/requirements.txt
else
    source venv/bin/activate
fi

# Check for flags
REFRESH_DB=false
if [[ "$*" == *"--refresh"* ]]; then
    REFRESH_DB=true
fi

# Database Setup
echo "Checking Database..."
cd backend
if [ ! -f "screen.db" ] || [ "$REFRESH_DB" = true ]; then
    echo "Initializing/Refreshing Database..."
    # Ensure tables exist
    alembic upgrade head
    
    if [ "$REFRESH_DB" = true ]; then
        echo "Refresh flag detected. Running ingestion..."
        python ingest.py
    elif [ ! -f "screen.db" ]; then
        echo "Database created. It is currently empty."
        read -p "Do you want to run the ingestion script now? (Takes ~10m) [y/N] " -n 1 -r
        echo 
        if [[ $REPLY =~ ^[Yy]$ ]]
        then
            python ingest.py
        else
            echo "Skipping ingestion. The UI will show empty results until you run 'python backend/ingest.py'."
        fi
    fi
else
    # Always run migrations to be safe
    alembic upgrade head
fi

# Start Backend
echo "Starting Backend..."
uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!
cd ..

# Start Frontend
echo "Starting Frontend..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo "Backend running on PID $BACKEND_PID"
echo "Frontend running on PID $FRONTEND_PID"
echo "Press Ctrl+C to stop both servers."

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
