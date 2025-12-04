#!/bin/bash

# Quick Start Script - Run both backend and frontend

echo "🏥 Starting AI Medical Interview Assistant..."
echo ""

# Check if .env exists
if [ ! -f backend/.env ]; then
    echo "⚠️  backend/.env not found!"
    echo "Please copy backend/.env.example to backend/.env and add your API keys"
    exit 1
fi

# Start backend in background
echo "🚀 Starting Flask backend on localhost:5000..."
cd backend
python app.py &
BACKEND_PID=$!
cd ..

sleep 2

# Start frontend
echo "🚀 Starting React frontend on localhost:3000..."
cd frontend
npm start &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ Both services are starting!"
echo ""
echo "📱 Open http://localhost:3000 in your browser"
echo ""
echo "Process IDs:"
echo "  Backend:  $BACKEND_PID"
echo "  Frontend: $FRONTEND_PID"
echo ""
echo "To stop: Press Ctrl+C"

wait $BACKEND_PID $FRONTEND_PID
