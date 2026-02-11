# NextGen Voice Agent

A multi-channel AI customer service platform with voice and chat capabilities, featuring a three-tier architecture with intelligent message processing and formatting.

![Status](https://img.shields.io/badge/status-production%20ready-brightgreen)
![Version](https://img.shields.io/badge/version-1.0.0-blue)

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- Google API Key (for Gemini AI)
- ElevenLabs API Key (for voice TTS)
- Supabase account (for authentication)

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd Next-Generation-Voice-Agent
```

2. **Setup Backend**
```bash
cd Backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Create `Backend/.env`:
```env
GOOGLE_API_KEY=your_google_api_key
GOOGLE_GENAI_MODEL=gemini-2.0-flash-exp
```

3. **Setup Interceptor**
```bash
cd Interceptor
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Create `Interceptor/.env`:
```env
INTERCEPTOR_PORT=8001
BACKEND_URL=http://127.0.0.1:8000
GOOGLE_API_KEY=your_google_api_key
GOOGLE_GENAI_MODEL=gemini-2.0-flash-exp
ELEVENLABS_API_KEY=your_elevenlabs_api_key
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM
```

4. **Setup Frontend**
```bash
cd Frontend
npm install
```

Create `Frontend/.env`:
```env
VITE_INTERCEPTOR_URL=http://localhost:8001
VITE_SUPABASE_URL=your_supabase_url
VITE_SUPABASE_ANON_KEY=your_supabase_key
```

### Running the Application

**Automated (Windows):**
```bash
start-all.bat
```

**Manual:**
```bash
# Terminal 1: Backend
cd Backend && venv\Scripts\activate && python main.py

# Terminal 2: Interceptor
cd Interceptor && venv\Scripts\activate && python main.py

# Terminal 3: Frontend
cd Frontend && npm run dev
```

**Access:**
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- Interceptor API: http://localhost:8001

---

## 🏗️ Architecture

```
Frontend (5173) → Interceptor (8001) → Backend (8000)
     ↓                   ↓                   ↓
  User UI         Channel Logic        AI Agent
  Chat/Voice      Formatting/TTS      Business Logic
```

### Components

**Frontend (React + Vite)**
- Chat interface with markdown rendering
- Voice interface with animated 3D Orb
- Web Speech API for STT
- Web Audio API for playback

**Interceptor (FastAPI + Python)**
- Channel-specific middleware
- Gemini AI formatting for chat
- ElevenLabs TTS integration for voice
- WebSocket server for real-time communication

**Backend (FastAPI + Google ADK)**
- Channel-agnostic AI agent
- Google Gemini powered
- Business logic tools (billing, knowledge, memory, support)
- Session management

---

## ✨ Features

### Chat Mode
- ✅ Real-time text messaging
- ✅ Markdown rendering (bold, bullets, tables)
- ✅ Message history
- ✅ Session management
- ✅ New conversation creation

### Voice Mode
- ✅ Real-time voice conversation
- ✅ Speech-to-text (Web Speech API)
- ✅ Text-to-speech (ElevenLabs)
- ✅ Animated 3D Orb visualization
- ✅ State indicators (listening/thinking/talking)
- ✅ Mute, interrupt, and end call controls

### Backend
- ✅ AI-powered responses (Google Gemini)
- ✅ Tool calling (billing, knowledge, memory, support)
- ✅ Context-aware conversations
- ✅ User personalization

---

## 📚 Documentation

- **[Setup Guide](SETUP_GUIDE.md)** - Detailed setup instructions
- **[Complete Documentation](PROJECT_COMPLETE_DOCUMENTATION.md)** - Comprehensive project documentation
- **[System Diagrams](SYSTEM_DIAGRAMS.md)** - Visual architecture diagrams
- **[Contributing](CONTRIBUTING.md)** - Contribution guidelines

---

## ⚠️ Known Limitations

1. **ElevenLabs Free Tier Disabled**
   - Voice TTS requires paid plan ($5-11/month)
   - Alternative: Use Google Cloud TTS or Azure Speech

2. **Browser Compatibility**
   - Voice STT only works in Chrome/Edge
   - Alternative: Implement Deepgram or Google Speech-to-Text

---

## 🛠️ Tech Stack

**Frontend:**
- React 18
- Vite
- TailwindCSS
- Three.js
- Web Speech API
- Web Audio API

**Interceptor:**
- FastAPI
- WebSockets
- Google Gemini AI
- ElevenLabs API
- Python 3.8+

**Backend:**
- FastAPI
- Google ADK
- Google Gemini
- Python 3.8+

**External Services:**
- Google Gemini AI
- ElevenLabs
- Supabase

---

## 📊 Project Statistics

- **Total Files:** 40+
- **Lines of Code:** ~5,300
- **Technologies:** 8+
- **Communication Channels:** 2 (Chat, Voice)
- **Architecture Tiers:** 3

---

## 🧪 Testing

### Manual Testing

**Chat:**
```bash
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello","user_id":"test@example.com","name":"Test","channel":"chat"}'
```

**Backend:**
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello","user_id":"test@example.com","name":"Test"}'
```

---

## 🚀 Deployment

### Production Checklist
- [ ] Set up production environment variables
- [ ] Configure HTTPS/SSL certificates
- [ ] Set up load balancers
- [ ] Configure CDN for frontend
- [ ] Set up monitoring and logging
- [ ] Configure rate limiting
- [ ] Upgrade to ElevenLabs paid plan
- [ ] Test in production environment

### Recommended Infrastructure
- **Frontend:** CDN (Cloudflare, AWS CloudFront) or Vercel/Netlify
- **Backend & Interceptor:** Docker containers on AWS/GCP/Azure
- **Database:** Supabase or PostgreSQL

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

---

## 📝 License

[Add your license here]

---

## 🙏 Acknowledgments

- Google Gemini AI for intelligent responses
- ElevenLabs for voice synthesis
- Supabase for authentication and database
- React and FastAPI communities

---

## 📞 Support

For issues and questions:
1. Check [PROJECT_COMPLETE_DOCUMENTATION.md](PROJECT_COMPLETE_DOCUMENTATION.md)
2. Review [SETUP_GUIDE.md](SETUP_GUIDE.md)
3. Open an issue on GitHub

---

**Status:** ✅ Production Ready (Voice TTS requires ElevenLabs paid plan)

**Last Updated:** February 11, 2026  
**Version:** 1.0.0
