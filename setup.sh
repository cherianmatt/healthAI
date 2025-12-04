#!/bin/bash

# AI Medical Interview Assistant - Setup Script

echo "🏥 Setting up AI Medical Interview Assistant..."
echo ""

# Backend setup
echo "📦 Setting up backend..."
cd backend

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    cp .env.example .env
    echo "⚠️  Created .env file. Please add your API keys:"
    echo "   - OPENAI_API_KEY (from https://platform.openai.com/api-keys)"
    echo "   - GEMINI_API_KEY (from https://aistudio.google.com/app/apikey)"
fi

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Download spaCy model
echo "Downloading spaCy biomedical model (this may take a minute)..."
python -m spacy download en_core_sci_md

cd ..

# Frontend setup
echo ""
echo "📦 Setting up frontend..."
cd frontend

# Install Node dependencies
echo "Installing Node dependencies..."
npm install

cd ..

echo ""
echo "✅ Setup complete!"
echo ""
echo "🚀 To run the application:"
echo ""
echo "1. Terminal 1 - Start Flask backend:"
echo "   cd backend"
echo "   python app.py"
echo ""
echo "2. Terminal 2 - Start React frontend:"
echo "   cd frontend"
echo "   npm start"
echo ""
echo "Then open http://localhost:3000 in your browser"
