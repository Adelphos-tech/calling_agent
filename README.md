# Real Estate Voice Agent 🤖🏠

A complete voice-enabled AI real estate agent powered by:
- **Speech-to-Text**: Deepgram Nova-3
- **LLM**: Groq Llama 3.3 70B
- **Text-to-Speech**: Deepgram Aura
- **Calling**: Twilio (optional, for outbound calls)

## Agent Persona: Alexandra Chen

A polite, professional real estate agent from Prestige Properties Singapore. She's knowledgeable about:
- Singapore property market and districts (D1-D28)
- Property types: Condos, HDB, Landed, Executive Condos
- MRT connectivity and amenities
- Investment potential and rental yields

## Features

✅ **Voice Agent** - Real-time voice conversation with AI  
✅ **Chat Interface** - Text-based chat with the agent  
✅ **Outbound Calling** - Trigger calls via Twilio  
✅ **Property Search** - 6 curated Singapore listings  
✅ **Smart Recommendations** - Based on budget, location, preferences  

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Application

```bash
python app.py
```

Or with uvicorn directly:

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### 3. Open in Browser

Navigate to `http://localhost:8000`

## Web Interface

The home page provides:

1. **Outbound Call Section** - Enter a phone number to receive a call
2. **Chat Interface** - Text chat with Alexandra
3. **Property Showcase** - Browse available listings

### Chat Commands

You can ask Alexandra about:
- Properties within a specific budget (e.g., "Show me condos under 3 million")
- Locations (e.g., "What do you have in Orchard?")
- Property types (e.g., "Do you have any landed properties?")
- Specific properties (e.g., "Tell me about Marina Bay Residences")

## Twilio Integration (Optional)

To enable actual phone calls:

### 1. Set up Twilio Account
- Sign up at [twilio.com](https://www.twilio.com)
- Get a phone number
- Note your Account SID and Auth Token

### 2. Configure Environment Variables

```bash
export TWILIO_ACCOUNT_SID=your_account_sid
export TWILIO_AUTH_TOKEN=your_auth_token
export TWILIO_PHONE_NUMBER=+1234567890
```

Or create a `.env` file:

```bash
cp .env.example .env
# Edit .env with your credentials
```

### 3. Expose Local Server (for testing)

Using ngrok:

```bash
# Install ngrok
brew install ngrok

# Authenticate
ngrok config add-authtoken your_ngrok_token

# Expose port 8000
ngrok http 8000
```

Copy the HTTPS URL and update your Twilio webhook URL.

### 4. Configure Twilio Webhook

In your Twilio Console:
- Go to Phone Numbers → Manage → Active Numbers
- Click your number
- Set "A Call Comes In" webhook to: `https://your-ngrok-url.ngrok.io/twilio/webhook`
- Set method to POST

## Project Structure

```
.
├── app.py                 # Main FastAPI application
├── requirements.txt       # Python dependencies
├── .env.example          # Example environment variables
└── README.md             # This file
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main web interface |
| `/api/properties` | GET | Get all properties |
| `/api/call` | POST | Initiate outbound call |
| `/twilio/webhook` | POST | Twilio voice webhook |
| `/ws/voice` | WebSocket | Real-time voice stream |
| `/ws/chat` | WebSocket | Text chat stream |

## Property Listings

The demo includes 6 Singapore properties:

1. **Marina Bay Residences** - S$4.8M, 3BR Luxury Condo
2. **Orchard Residences** - S$3.2M, 2BR Prime Orchard
3. **Sentosa Cove Villa** - S$12M, 5BR Waterfront Bungalow
4. **Tanjong Pagar Hub** - S$1.8M, 3BR Executive Condo
5. **East Coast Paradise** - S$2.1M, 3BR Family Condo
6. **Holland Hill Estate** - S$4.5M, 4BR Landed Terrace

## Architecture

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   Browser    │◄───────►│  FastAPI     │◄───────►│  Deepgram    │
│   Client     │  WS/TTS │  Server      │  TTS    │  Aura        │
└──────────────┘         └──────────────┘         └──────────────┘
        ▲                        │
        │                        │
        │                 ┌──────┴──────┐         ┌──────────────┐
        │                 │   Groq      │◄───────►│   LLaMA      │
        │                 │   Llama 3.3 │         │   70B        │
        │                 └─────────────┘         └──────────────┘
        │                        │
        │                 ┌──────┴──────┐
        │                 │ Properties  │
        │                 │   Service   │
        │                 └─────────────┘
        │
        │                 ┌──────────────┐
        └────────────────►│  Deepgram    │
                          │  Nova-3 STT  │
                          └──────────────┘
```

## Troubleshooting

### WebSocket Connection Issues
- Check firewall settings
- Ensure port 8000 is open
- Try accessing via `http://localhost:8000` (not `127.0.0.1`)

### Twilio Call Fails
- Verify Twilio credentials are set
- Check ngrok is running if testing locally
- Ensure webhook URL is publicly accessible

### Audio Playback Issues
- Browser autoplay policies may block audio
- Click on the page first to enable audio
- Check browser console for errors

## Future Enhancements

- [ ] Add voice activity detection (VAD)
- [ ] Support for property booking/schedule viewings
- [ ] Integration with real MLS data
- [ ] Multi-language support
- [ ] Voice cloning for personalized agent voices

## License

MIT

## Credits

- Deepgram for STT/TTS APIs
- Groq for LLM inference
- Twilio for telephony
- FastAPI for web framework
