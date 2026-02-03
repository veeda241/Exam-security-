#!/bin/bash
# ExamGuard Pro - Startup Script

echo "🛡️  Starting ExamGuard Pro..."
echo ""

# Change to server directory
cd server

# Install dependencies if needed
echo "Checking dependencies..."
pip install -r requirements.txt --quiet

echo ""
echo "📦 Starting backend server..."
echo "API will be available at http://localhost:8000"
echo "Documentation at http://localhost:8000/docs"
echo ""

# Run the server
python -m uvicorn main:app --host 0.0.0.0 --port 8000

