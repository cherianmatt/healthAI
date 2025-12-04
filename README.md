# AI Medical Interview Assistant - Setup & Run Guide

## Overview

A real-time AI-powered medical interview assistant that:
- Captures live patient speech via browser microphone
- Transcribes using **AssemblyAI** (free tier: 100 min/month)
- Extracts symptoms using keyword matching
- Generates follow-up questions using Google Gemini API
- Displays real-time guidance to clinicians
- **Persists session data** in browser (auto-clears on tab close)

## Prerequisites

- Python 3.13 (with `.venv` virtual environment)
- Node.js 16+
- AssemblyAI API key (free: 100 min/month, no billing required)
- Google Gemini API key (free tier available)

## Quick Start (5 minutes)

### 1. Get API Keys

**AssemblyAI (Speech-to-Text):**
- Go to https://www.assemblyai.com/dashboard/signup
- Sign up for free (100 min/month)
- Copy API key from dashboard

**Google Gemini API (Question Generation):**
- Go to https://aistudio.google.com/app/apikey
- Click "Create API key"
- Copy API key

### 2. Navigate to project

```bash
cd /Users/cherianmathew/Documents/Projects/HealthAI
```

### 3. Configure Environment

Edit `backend/.env`:
```env
ASSEMBLYAI_API_KEY=your_key_here
GEMINI_API_KEY=your_key_here
FLASK_ENV=development
FLASK_DEBUG=True
```

### 4. Install Dependencies

```bash
# Python
.venv/bin/pip install -r backend/requirements.txt

# Frontend
cd frontend
npm install
```

### 5. Run Backend (Terminal 1)

```bash
cd /Users/cherianmathew/Documents/Projects/HealthAI/backend
/Users/cherianmathew/Documents/Projects/HealthAI/.venv/bin/python app.py
```

Expected output:
```
⚠ spaCy not available - using keyword matching for symptom extraction
 * Running on http://127.0.0.1:3001
```

### 6. Run Frontend (Terminal 2)

```bash
cd /Users/cherianmathew/Documents/Projects/HealthAI/frontend
npm start
```

Automatic browser opens: http://localhost:3000

### 7. Use the Application

1. Click **"🎤 Start Recording"** button
2. Speak as a patient: *"I have a severe headache for 3 days and feel nauseous"*
3. Click **"⏹ Stop Recording"** when done
4. Wait 1-2 seconds for results
5. View:
   - **Current Transcript**: Latest recording
   - **Detected Symptoms**: AI-identified conditions
   - **Follow-up Questions**: AI-suggested questions for clinician
   - **Session Summary**: All symptoms from all recordings
   - **Transcript History**: Click past recordings to review

## Project Structure

```
HealthAI/
├── backend/
│   ├── app.py                          # Flask application
│   ├── requirements.txt                # Python dependencies
│   ├── .env.example                   # Environment template
│   └── knowledge_base/
│       └── symptoms.json              # Symptom-to-checklist mapping
├── frontend/
│   ├── public/
│   │   └── index.html
│   ├── src/
│   │   ├── App.js                     # Main React component
│   │   ├── App.css                    # Styling
│   │   ├── index.js                   # React entry point
│   │   └── index.css                  # Global styles
│   ├── package.json
│   └── README.md
├── setup.sh                            # Setup automation
└── README.md
```

## API Endpoints

### Backend (http://localhost:3001)

- **GET** `/` - Health check → `{"status": "healthy", "speech_service": "assemblyai"}`
- **POST** `/process-interview` - Full pipeline (main endpoint)
- **GET** `/symptoms` - List available symptoms
- **GET** `/conditions` - List medical conditions
- **GET** `/knowledge-base` - Full knowledge base
- **POST** `/generate-followup` - Generate new questions

## Supported Symptoms

The knowledge base currently includes:
- Headache
- Fever
- Cough
- Chest pain
- Sore throat
- Nausea
- Fatigue
- Shortness of breath

Each symptom has 5-10 required diagnostic checks.

## Session Management

### How It Works

- **Session Data Storage**: Browser `localStorage` (client-side only)
- **Auto-Cleanup**: All data deleted when browser tab closes
- **Manual Clear**: Click "🔄 New Session" button to clear
- **Session History**: Click past recordings to reload data
- **Accumulation**: All detected symptoms from all recordings shown

### What Gets Saved

- Transcript text from each recording
- Detected symptoms from each recording
- Timestamps for each recording
- All follow-up questions

### Privacy Note

- No data sent to server for storage
- All session data is temporary (local browser only)
- Data automatically cleared when you close the tab
- Ideal for demo/testing environments

## Troubleshooting

### "Backend connection refused"
- Verify Flask running on port 3001: `lsof -i :3001`
- Backend should show: `Running on http://127.0.0.1:3001`

### "Symptoms not detected"
- Check keyword matching against `backend/knowledge_base/symptoms.json`
- Try speaking symptom names clearly (e.g., "headache", "fever")
- Backend logs show extracted symptoms: look for "Detected symptoms: [...]"

### "API keys not configured"
Check `backend/.env`:
- AssemblyAI: https://www.assemblyai.com/dashboard (free signup)
- Gemini: https://aistudio.google.com/app/apikey

### "Microphone access denied"
Allow browser permission when prompted (usually top address bar)

### "AssemblyAI API calls failing"
- Check API key is correct in `.env`
- Verify free tier quota: https://www.assemblyai.com/dashboard (100 min/month)
- Check internet connection

### "Frontend won't connect to backend"
- Verify backend running on port 3001
- Check CORS headers in Flask (should be configured)
- Browser console may show CORS errors

## Performance & Limits

- **Audio Length**: 30-90 seconds ideal (AssemblyAI free tier limit)
- **Transcription**: ~1-2 seconds per 60 seconds audio
- **Question Generation**: 1-3 seconds (Gemini API latency)
- **Memory**: ~200MB total (Python + Node.js)
- **Storage**: localStorage limited to 5-10MB per domain (usually sufficient)

## Future Enhancements

- Extended symptom knowledge base
- Differential diagnosis suggestions
- Severity/confidence scoring
- Multi-language support
- Export session transcripts
- Real-time streaming transcription
- Server-side session storage (with privacy controls)

