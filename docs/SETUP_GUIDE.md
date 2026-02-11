# Setup Guide - NextGen Voice Agent

**Quick setup instructions for running the project**

---

## Prerequisites

- Python 3.8+ installed
- Node.js 16+ installed
- Git installed

---

## First Time Setup

### 1. Backend Setup

```bash
cd Backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Create `Backend/.env` file:
```env
GOOGLE_API_KEY=your_google_api_key
GOOGLE_GENAI_MODEL=gemini-2.0-flash-exp
```

### 2. Interceptor Setup

```bash
cd Interceptor
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Create `Interceptor/.env` file:
```env
INTERCEPTOR_PORT=8001
BACKEND_URL=http://127.0.0.1:8000
GOOGLE_API_KEY=your_google_api_key
GOOGLE_GENAI_MODEL=gemini-2.0-flash-exp
ELEVENLABS_API_KEY=your_elevenlabs_api_key
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM
```

### 3. Frontend Setup

```bash
cd Frontend
npm install
```

Create `Frontend/.env` file:
```env
VITE_INTERCEPTOR_URL=http://localhost:8001
VITE_SUPABASE_URL=your_supabase_url
VITE_SUPABASE_ANON_KEY=your_supabase_key
```

---

## Running the Application

### Option 1: Automated Start (Recommended)

Simply double-click or run:
```bash
start-all.bat
```

This will start all three services in separate windows:
- Backend on port 8000
- Interceptor on port 8001
- Frontend on port 5173

### Option 2: Manual Start

**Terminal 1 - Backend:**
```bash
cd Backend
venv\Scripts\activate
python main.py
```

**Terminal 2 - Interceptor:**
```bash
cd Interceptor
venv\Scripts\activate
python main.py
```

**Terminal 3 - Frontend:**
```bash
cd Frontend
npm run dev
```

---

## Accessing the Application

Once all services are running:

- **Frontend UI:** http://localhost:5173
- **Backend API:** http://localhost:8000
- **Interceptor API:** http://localhost:8001

---

## Virtual Environment Structure

The project uses separate virtual environments for isolation:

```
Next-Generation-Voice-Agent/
├── Backend/
│   ├── venv/              ← Backend's own virtual environment
│   ├── main.py
│   └── requirements.txt
├── Interceptor/
│   ├── venv/              ← Interceptor's own virtual environment
│   ├── main.py
│   └── requirements.txt
└── Frontend/
    ├── node_modules/      ← Frontend's dependencies
    └── package.json
```

**Why separate venvs?**
- Isolation: Each service has its own dependencies
- Flexibility: Can use different Python versions if needed
- Deployment: Easier to containerize each service separately

---

## Troubleshooting

### Backend won't start
- Check if port 8000 is available
- Verify GOOGLE_API_KEY is set in Backend/.env
- Ensure venv is activated

### Interceptor won't start
- Check if port 8001 is available
- Verify GOOGLE_API_KEY and ELEVENLABS_API_KEY are set
- Ensure venv is activated
- Check that Backend is running

### Frontend won't start
- Check if port 5173 is available
- Run `npm install` if node_modules is missing
- Verify VITE_INTERCEPTOR_URL is set

### Chat not working
- Verify all services are running
- Check browser console for errors
- Verify API keys are correct

### Voice not working
- Ensure you're using Chrome or Edge browser
- Allow microphone access when prompted
- Upgrade to ElevenLabs paid plan for TTS
- Check WebSocket connection in browser console

---

## Updating Dependencies

### Backend
```bash
cd Backend
venv\Scripts\activate
pip install -r requirements.txt --upgrade
```

### Interceptor
```bash
cd Interceptor
venv\Scripts\activate
pip install -r requirements.txt --upgrade
```

### Frontend
```bash
cd Frontend
npm update
```

---

## Clean Installation

If you encounter issues, try a clean installation:

### Backend
```bash
cd Backend
rmdir /s /q venv
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Interceptor
```bash
cd Interceptor
rmdir /s /q venv
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Frontend
```bash
cd Frontend
rmdir /s /q node_modules
npm install
```

---

## Next Steps

After setup:
1. Test chat functionality
2. Test voice functionality (requires ElevenLabs paid plan)
3. Review documentation in PROJECT_COMPLETE_DOCUMENTATION.md
4. Check FINAL_STATUS.md for current project state

---

**Need Help?**
- Check PROJECT_COMPLETE_DOCUMENTATION.md for detailed information
- Review SYSTEM_DIAGRAMS.md for architecture overview
- See BUG_FIX_SUMMARY.md for known issues and solutions
