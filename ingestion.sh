#!/bin/bash

# Check if venv exists, if so activate it
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r backend/requirements.txt
else
    source venv/bin/activate
fi

# Database Setup - Ensure tables exist
echo "Checking Database Migrations..."
cd backend
alembic upgrade head

echo "Running Ingestion..."
python ingest.py "$@"
cd ..
