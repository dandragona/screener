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
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Start Backend
echo "Starting Backend..."
cd backend
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
