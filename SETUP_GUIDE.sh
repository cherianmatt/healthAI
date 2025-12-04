#!/bin/bash

# AI Medical Interview Assistant - Quick Setup Guide
# This script helps you get started quickly

echo "🏥 AI Medical Interview Assistant - Setup Guide"
echo "================================================"
echo ""

# Get the project directory (where this script is located)
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$PROJECT_DIR/.venv/bin"

# Check if virtual environment exists
if [ ! -f "$VENV/python" ]; then
    echo "❌ Virtual environment not found"
    echo "Run: python3 -m venv .venv"
    exit 1
fi

echo "✓ Virtual environment found"
echo ""

# Step 1: API Keys
echo "📋 STEP 1: Get Your API Keys"
echo "───────────────────────────────"
echo ""
echo "You need TWO free API keys:"
echo ""
echo "1️⃣  OpenAI Whisper API (for speech-to-text)"
echo "   → Go to: https://platform.openai.com/api-keys"
echo "   → Click 'Create new secret key'"
echo "   → Copy the key (starts with 'sk-')"
echo ""
echo "2️⃣  Google Gemini API (for question generation)"
echo "   → Go to: https://aistudio.google.com/app/apikey"
echo "   → Click 'Create API key'"
echo "   → Copy the key (starts with 'AIza')"
echo ""
echo "Both have free tiers! 🎉"
echo ""

# Step 2: Add keys to .env
echo "⚙️  STEP 2: Configure API Keys"
echo "───────────────────────────────"
echo ""
echo "Edit: $PROJECT_DIR/backend/.env"
echo ""
echo "Replace:"
echo "  OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
echo "  GEMINI_API_KEY=AIzaSyxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
echo ""
echo "With your actual keys:"
echo "  OPENAI_API_KEY=sk-proj-Qq-52YEY..."
echo "  GEMINI_API_KEY=AIzaSyAVcs2lc..."
echo ""

# Step 3: Run backend
echo "🚀 STEP 3: Run Backend"
echo "───────────────────────────────"
echo ""
echo "In Terminal 1, run:"
echo "  cd backend"
echo "  source ../.venv/bin/activate"
echo "  python app.py"
echo ""
echo "You should see:"
echo "  ✓ spaCy model loaded (or ⚠ using keyword matching)"
echo "  * Running on http://127.0.0.1:3001"
echo ""

# Step 4: Run frontend
echo "💻 STEP 4: Run Frontend"
echo "───────────────────────────────"
echo ""
echo "In Terminal 2, run:"
echo "  cd frontend"
echo "  npm start"
echo ""
echo "Your browser should open http://localhost:3000"
echo ""

# Step 5: Test
echo "🎤 STEP 5: Test the Application"
echo "───────────────────────────────"
echo ""
echo "1. Click 'Start Recording' button"
echo "2. Say: 'I have a severe headache and I feel nauseous'"
echo "3. Click 'Stop Recording'"
echo "4. Wait 2-3 seconds for results"
echo ""
echo "You should see:"
echo "  ✓ Transcript of what you said"
echo "  ✓ Detected symptoms (headache, nausea)"
echo "  ✓ 3-5 AI-generated follow-up questions"
echo ""

# Verification
echo "✅ STEP 6: Verify Installation"
echo "───────────────────────────────"
echo ""
echo "Test backend imports:"
source $VENV/activate
python -c "import flask; import google.generativeai; import assemblyai; print('✓ All imports working')" && echo "" || { echo "❌ Import failed"; exit 1; }

echo ""
echo "Backend API test:"
echo "  curl http://127.0.0.1:3001/health"
echo ""

echo "🎉 Ready to demo!"
echo ""
echo "Need help? Check:"
echo "  • README.md - Full documentation"
echo "  • IMPLEMENTATION_GUIDE.md - Technical details"
echo "  • backend/app.py - Backend code"
echo "  • frontend/src/App.js - Frontend code"
