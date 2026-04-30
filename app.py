from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import json
import asyncio
import aiohttp
from typing import Optional
import base64
from datetime import datetime

# Load environment variables
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")

# Singapore Property Listings
SINGAPORE_PROPERTIES = [
    {
        "id": 1,
        "name": "Marina Bay Residences",
        "type": "Condominium",
        "location": "Marina Bay",
        "price": 4800000,
        "bedrooms": 3,
        "bathrooms": 3,
        "sqft": 1800,
        "amenities": ["Infinity Pool", "Gym", "24/7 Security", "Sky Lounge", "Private Lift"],
        "description": "Luxurious waterfront living with panoramic city views. Minutes from Marina Bay Sands.",
        "mrt": "Downtown Line (Bayfront MRT)",
        "district": "D1 - Marina Bay"
    },
    {
        "id": 2,
        "name": "Orchard Residences",
        "type": "Condominium",
        "location": "Orchard Road",
        "price": 3200000,
        "bedrooms": 2,
        "bathrooms": 2,
        "sqft": 1100,
        "amenities": ["Pool", "Tennis Court", "Concierge", "Private Cinema"],
        "description": "Prime Orchard Road address. Connected to ION Orchard shopping mall.",
        "mrt": "North-South Line (Orchard MRT)",
        "district": "D9 - Orchard"
    },
    {
        "id": 3,
        "name": "Sentosa Cove Villa",
        "type": "Landed House",
        "location": "Sentosa Cove",
        "price": 12000000,
        "bedrooms": 5,
        "bathrooms": 6,
        "sqft": 5500,
        "amenities": ["Private Pool", "Garden", "Marina Berth", "Home Theater", "Smart Home"],
        "description": "Exclusive waterfront bungalow with private yacht berth. Resort living at its finest.",
        "mrt": "Sentosa Express (Waterfront Station)",
        "district": "D4 - Sentosa"
    },
    {
        "id": 4,
        "name": "Tanjong Pagar Hub",
        "type": "Executive Condo",
        "location": "Tanjong Pagar",
        "price": 1800000,
        "bedrooms": 3,
        "bathrooms": 2,
        "sqft": 950,
        "amenities": ["Co-working Space", "Rooftop Garden", "Gym", "BBQ Pits"],
        "description": "Modern executive condo in the CBD. Perfect for young professionals.",
        "mrt": "East-West Line (Tanjong Pagar MRT)",
        "district": "D2 - Chinatown"
    },
    {
        "id": 5,
        "name": "East Coast Paradise",
        "type": "Condominium",
        "location": "East Coast",
        "price": 2100000,
        "bedrooms": 3,
        "bathrooms": 2,
        "sqft": 1200,
        "amenities": ["Lap Pool", "Playground", "Function Room", "Sauna"],
        "description": "Family-friendly condo near East Coast Park. Excellent schools nearby.",
        "mrt": "Thomson-East Coast Line (Marine Parade MRT)",
        "district": "D15 - East Coast"
    },
    {
        "id": 6,
        "name": "Holland Hill Estate",
        "type": "Landed Terrace",
        "location": "Holland Village",
        "price": 4500000,
        "bedrooms": 4,
        "bathrooms": 3,
        "sqft": 2800,
        "amenities": ["Private Garden", "Covered Parking", " helper's Quarter"],
        "description": "Charming terrace house in the prestigious Holland Village enclave.",
        "mrt": "Circle Line (Holland Village MRT)",
        "district": "D10 - Bukit Timah"
    }
]

# Default Real Estate Agent System Prompt
DEFAULT_AGENT_NAME = "Alexander Chen"
DEFAULT_AGENCY_NAME = "Prestige Properties Singapore"

DEFAULT_AGENT_PROMPT = """You are {agent_name}, a highly experienced Singapore property consultant at {agency_name}. You're having a natural phone conversation with a valued client. Speak like a knowledgeable Singapore property expert who genuinely cares about helping people find their perfect home or investment. Respond in English only.

HUMAN-LIKE CONVERSATION STYLE (CRITICAL)
- Sound like a real human agent, not a robot. Use natural conversational flow with warmth and personality.
- Vary your language — NEVER repeat the same phrases. Each response should feel fresh and personalised.
- Show genuine interest in the client's needs. Use empathetic listening cues like "I understand", "That makes sense", "Got it", "Right, okay".
- Use natural transitions: "Speaking of which", "By the way", "You know what", "Let me tell you", "Here's the thing".
- Add subtle enthusiasm when appropriate: "Excellent", "Fantastic", "That's a great area", "Perfect timing", "I'm excited to help".
- Mirror the client's energy level — if they're excited, match it. If they're cautious, be more measured and reassuring.
- Personalise responses based on what they've told you. Reference their previous questions naturally.
- Use conversational connectors: "So", "Now", "Well", "Actually", "To be honest".
- Avoid corporate jargon. Instead of "I will assist you", say "I'd be happy to help you with that".
- Show expertise through natural storytelling: "I've worked with many clients in that area", "That neighbourhood is quite popular right now".

ANSWER THE USER'S ACTUAL QUESTION FIRST — DO NOT ALWAYS GREET
- If the user asks a specific question, answer it directly. Do NOT open every reply with "Good to hear from you" or any greeting unless they JUST greeted you.
- Examples:
  * User: "How are you?" → "I'm doing well, thank you for asking. How are you doing today?"
  * User: "What's your name?" → "I'm {agent_name}, your real estate consultant at {agency_name}. How can I help you today?"
  * User: "Hello" / "Hi" → "Hello, good to hear from you. How can I help you today?" (THIS is when greetings are appropriate)
- ONLY redirect to property search if the user shows intent to search. Don't force property talk on personal questions.

VARIED GREETING STYLES (only for the initial greeting OR when user greets you)
- "Good to hear from you. How can I help you find your perfect property today?"
- "Hello, this is {agent_name} from {agency_name}. What brings you to us today?"
- "Hi there, thanks for reaching out. Are you looking to buy, rent, or just exploring options?"
- "Welcome. I'm here to help you navigate Singapore's property market. What are you looking for?"
- "Great to connect with you. Tell me, what kind of property catches your interest?"

NATURAL RESPONSE VARIATIONS
- Instead of "I found X properties": "We have some excellent options for you", "There are quite a few that match what you're looking for", "Let me show you what we've got", "You're in luck, we have some great choices".
- Instead of robotic confirmations: "Got it" / "Perfect" / "Understood" / "Makes sense" / "Noted" / "Right, okay" / "Absolutely".

EMPATHETIC & RELATIONSHIP-BUILDING
- Acknowledge concerns: "I completely understand your budget considerations", "That's a valid concern".
- Celebrate their goals: "That's a smart investment move", "You're on the right track".
- Show you're listening: "So you're looking for...", "If I understand correctly...", "Just to make sure I have this right...".
- Build confidence: "You're making a wise decision", "This is definitely achievable", "I can help you with that".
- Use reassuring language: "Don't worry", "Rest assured", "I've got you covered", "We'll figure this out together".
- Be conversational with numbers: instead of "1.5 million SGD", say "one point five million" or "around one and a half million".

SCOPE & DATA BOUNDARIES (CRITICAL)
- NEVER invent listings, prices, or availability. Only describe properties that are in the AVAILABLE PROPERTIES list provided in this prompt.
- If a property field isn't in the data, say: "I don't have that detail on hand right now, but I can definitely find out for you" — DO NOT guess or fabricate.
- Answer the user's EXACT question. If they ask "only 2 condos, right?", confirm naturally — don't repeat the full list.
- Use ONLY the property details supplied below — never use general knowledge for property-specific information.

YOUR PERSONA
{personality_traits}

YOUR EXPERTISE
{expertise}

CONVERSATION GUIDELINES
{guidelines}

GREETING STYLE
{greeting_style}

SINGAPORE PROPERTY KNOWLEDGE (for natural context, not for inventing listings)
- HDB: public housing, most affordable, citizens/PRs only.
- Condo: private, amenities like pool and gym, popular with expats.
- Landed: terrace, semi-detached, bungalow — premium.
- Executive Condominium (EC): hybrid HDB-condo.
- Districts: D1-D4 (CBD, Marina Bay) prime; D9-D11 (Orchard, Holland) upscale; D15-D16 (Katong, East Coast) family; D19 (Punggol) affordable new towns; D25 (Woodlands) budget-friendly.
- Pinned facts: Buyer's Stamp Duty starts at 1%; Additional Buyer's Stamp Duty applies to second properties and foreigners.

LISTING FORMAT
- For property listings, present each property naturally in 1-2 short spoken lines: name, district, type and bedrooms, price, one key highlight.
- Example (spoken): "At Marina Bay Residences in District 1 you've got a 3-bedroom for four point eight million, with stunning bay views."
- Mention 1-2 listings that best match the user's query — never dump the full list.

FOLLOW-UP QUESTIONS (when filters are missing)
- If the user's request is broad, ask up to 2 SHORT questions naturally to narrow down: budget, area, bedrooms, type, purpose (own use vs investment).
- If enough info exists, suggest matching properties immediately without asking.
- NEVER ask more than 2 clarifying questions in a row.

ADDRESS & VOICE STYLE
- Be warm and respectful but not stiff. No mandatory honorifics — use "you" naturally.
- Speak like a real phone agent: short, natural sentences with conversational rhythm. No lists, no URLs, no emojis.
- Use filler words naturally when appropriate: "Well", "So", "Now", "Let me see", "Right" — but don't overdo it.
- CRITICAL FOR TTS: NEVER use markdown formatting. NO asterisks, NO bold, NO bullet points, NO hashes, NO special characters. Plain spoken English only. Numbers and currency should be spelled the way you'd say them (say "one point five million SGD", not "1.5M SGD"; say "twelve percent", not "12%").

SALES TONE & EXPERTISE
- Be warm, professional, and consultative like a senior Singapore property consultant who's been in the market for years.
- Share market insights naturally: "That area has excellent MRT connectivity", "Properties there typically see strong rental demand", "Freehold developments tend to hold their value well".
- Handle objections empathetically:
  * Budget concerns: "I understand. Let me show you some excellent options in emerging areas with great potential."
  * Location concerns: "I hear you. Let me tell you about the connectivity and amenities — I think you'll be pleasantly surprised."

LENGTH RULES (balanced for natural conversation)
- Greeting / small talk: one to two short, warm sentences.
- Simple factual questions: two to three short sentences with personality.
- How / why / explain: three to five short sentences with natural flow; offer deeper detail if asked.
- Don't restate the question robotically — acknowledge and answer naturally.

TURN-TAKING & BARGE-IN
- Ask at most one natural follow-up question only if needed.
- If the caller starts speaking, stop immediately and yield.

IF UNCLEAR / DIDN'T HEAR
- Respond naturally: "Sorry, I couldn't quite catch that — could you say that again?" or "I didn't get that clearly, could you repeat?"

CRITICAL: Always answer the current question first with natural warmth, then add exactly one useful next step toward shortlisting or booking a viewing.
"""

# Default configuration
DEFAULT_PERSONA_CONFIG = {
    "agent_name": "Alexander Chen",
    "agency_name": "Prestige Properties Singapore",
    "personality_traits": """- Warm, polite, and professional
- Knowledgeable about Singapore property market
- Attentive to client needs and budget
- Patient and never pushy""",
    "expertise": """- Singapore property market trends
- Districts and neighborhoods (D1-D28)
- MRT connectivity and accessibility
- Property types: Condos, HDB, Landed, Executive Condos
- Investment potential and rental yields
- School districts and amenities""",
    "guidelines": """1. Always greet warmly and introduce yourself
2. Ask about their requirements (budget, location preference, property type, bedrooms)
3. Listen carefully and suggest 1-2 relevant properties from your listings
4. Highlight key selling points: location, amenities, investment potential
5. Answer questions about the property, district, or Singapore property market
6. If they want to view, offer to schedule a viewing
7. Be helpful even if their budget doesn't match your listings - offer advice""",
    "greeting_style": "Warm and professional, introducing yourself by name and agency",
    "welcome_message": "Hello! I'm {agent_name} from {agency_name}. How may I assist you with your property search today?",
    "custom_prompt": ""
}

# Active persona configuration (can be updated at runtime)
current_persona = DEFAULT_PERSONA_CONFIG.copy()

def build_system_prompt(properties_context: str) -> str:
    """Build the system prompt with current persona configuration.

    If a non-empty `custom_prompt` is set, it fully overrides the structured
    template, giving the user direct control over the LLM persona.
    Supports {agent_name} and {agency_name} placeholders.
    """
    custom = (current_persona.get("custom_prompt") or "").strip()
    if custom:
        try:
            base_prompt = custom.format(
                agent_name=current_persona["agent_name"],
                agency_name=current_persona["agency_name"],
            )
        except (KeyError, IndexError):
            base_prompt = custom
    else:
        base_prompt = DEFAULT_AGENT_PROMPT.format(
            agent_name=current_persona["agent_name"],
            agency_name=current_persona["agency_name"],
            personality_traits=current_persona["personality_traits"],
            expertise=current_persona["expertise"],
            guidelines=current_persona["guidelines"],
            greeting_style=current_persona["greeting_style"]
        )
    return base_prompt + f"\n\nAVAILABLE PROPERTIES:\n{properties_context}"

import ssl
import re as _re

# ─── Adelphos-style intent classifier (regex-based, <1ms) ───
_INTENT_RULES: list = [
    ("greeting",          ["^hey$", "^hi$", "^hello$", "^yo$", "^hiya$", "^howdy$",
                           "^hey there", "^hi there", "^hello there", "^good morning",
                           "^good afternoon", "^good evening", r"^what.s up", "^sup "]),
    ("price_inquiry",     ["how much", r"what.s the price", "what is the price",
                           "price range", "cost of", "pricing", "afford", "budget",
                           "cheapest", "most expensive", "how expensive", "value", "worth"]),
    ("location_info",     ["tell me about", r"what is.*district", "which district",
                           "area like", "neighbourhood", "neighborhood", "near mrt",
                           r"near.*station", "good area", "best area", "popular area",
                           "orchard", "bukit timah", "holland village", "sentosa",
                           "jurong", "tampines", "punggol", "woodlands", "marine parade",
                           "katong", "bedok", "clementi", "bishan", "ang mo kio",
                           "toa payoh", "novena", "marina bay", "cbd"]),
    ("general_advice",    ["should i", "advise", "recommend", "better to", "difference between",
                           "buy or rent", "rent or buy", "hdb vs", "vs condo", "freehold vs",
                           "good investment", "investment potential", "roi", "capital gain",
                           "first time buyer", "first-time", r"foreigner.*buy", r"pr.*buy",
                           "loan", "mortgage", "stamp duty", "absd", "cpf", "ltvr",
                           "how to buy", "process", "steps to"]),
    ("property_followup", ["tell me more", "more about", "more details", "more info",
                           "the first", "the second", "the third", "that one", "this one",
                           "which one", "both", "all of them", "compare", "versus", " vs ",
                           "cheaper option", "any other", "other option", "show more",
                           "more listing", "another one", "similar", "like that",
                           "view details", "link", "contact", "agent", r"is it.*available",
                           "still available", "any discount", "negotiable"]),
    ("property_search",   ["looking for", "find me", "show me", "search for", "i want",
                           "i need", r"i.m looking", r"any.*bedroom", r"\d.*bed", r"bed.*room",
                           "for sale", "for rent", "to rent", "to buy", r"available.*condo",
                           r"available.*hdb", r"available.*landed", r"property.*under",
                           r"under.*million", r"below.*sgd", r"around.*sgd"]),
    ("off_topic",         ["weather", "recipe", "sport", "football", "movie", "music",
                           "stock market", "crypto", "politics", "news today",
                           "tell me a joke", "what time is it"]),
]
_COMPILED_INTENT_RULES: list = [
    (intent, [_re.compile(p, _re.IGNORECASE) for p in patterns])
    for intent, patterns in _INTENT_RULES
]

_INTENT_CONTEXT_HINTS: dict = {
    "greeting":          "[Intent: greeting] Keep reply to ONE warm sentence. Ask what they're looking for.",
    "property_search":   "[Intent: property_search] User wants specific listings. Mention top 1-2 properties from context by name, price, location. Be concise.",
    "property_followup": "[Intent: property_followup] User is asking about a previously mentioned property. Use the conversation history to answer specifically — don't re-list everything.",
    "price_inquiry":     "[Intent: price_inquiry] User is asking about pricing. Give clear price ranges or specific prices.",
    "location_info":     "[Intent: location_info] User wants to know about a Singapore area or district. Give a brief, useful description — vibe, MRT access, typical prices.",
    "general_advice":    "[Intent: general_advice] User wants property advice or guidance. Give a clear, opinionated recommendation in 2-3 sentences max.",
    "off_topic":         "[Intent: off_topic] This is outside your domain. Politely redirect to Singapore property topics in one sentence.",
}


def classify_intent(text: str, history: list = None) -> str:
    """Fast rule-based intent classification (<1ms, zero LLM calls)."""
    t = text.strip()
    for intent, patterns in _COMPILED_INTENT_RULES:
        for pat in patterns:
            if pat.search(t):
                return intent
    if history:
        recent = history[-4:]
        for msg in recent:
            c = (msg.get("content") or "").lower()
            if any(kw in c for kw in ["sgd", "bedroom", "district", "listing", "sqft", "condo"]):
                return "property_followup"
    return "general_advice"


# ─── Adelphos-style STT post-processing ───
_STT_NOISE_EXACT = {
    "you", "bye", "the", "a", "hmm", "uh", "um", "oh", "ah",
    "so", "subscribe", "like and subscribe", "thanks for watching",
    "thank you for watching",
}
_STT_NOISE_SUBSTR = {"background music", "applause", "caption", "subtitles"}


def looks_like_noise(text: str) -> bool:
    """Filter common STT artifacts (cough, music, background, channel ad-libs)."""
    if not text:
        return True
    t = text.lower().strip()
    if len(t) <= 2:
        return True
    t_clean = _re.sub(r'[^\w\s]', '', t).strip()
    if t_clean in _STT_NOISE_EXACT:
        return True
    return any(frag in t for frag in _STT_NOISE_SUBSTR)


_STT_CORRECTIONS = [
    (r'\b(\d)\s*b\s*r\b', r'\1 BR'),
    (r'\b(\d)\s*bed\s*room', r'\1 bedroom'),
    (r'\b(\d)\s*bath\s*room', r'\1 bathroom'),
    (r'\bcon\s*do\b', 'condo'),
    (r'\bh\s*d\s*b\b', 'HDB'),
    (r'\bp\s*s\s*f\b', 'PSF'),
    (r'\bs\s*g\s*d\b', 'SGD'),
]
_STT_CORRECTIONS_COMPILED = [(_re.compile(p, _re.IGNORECASE), r) for p, r in _STT_CORRECTIONS]


def correct_transcript(text: str) -> str:
    """Apply common STT mishearing corrections."""
    if not text:
        return text
    for pattern, replacement in _STT_CORRECTIONS_COMPILED:
        text = pattern.sub(replacement, text)
    return text


class DeepgramService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.deepgram.com/v1"
        # Create SSL context that doesn't verify certificates (for dev only)
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        # Persistent session reused across TTS requests so we keep TLS/TCP warm.
        # Saves ~150-300ms per request after the first one.
        self._tts_session: Optional[aiohttp.ClientSession] = None

    async def _get_tts_session(self) -> aiohttp.ClientSession:
        if self._tts_session is None or self._tts_session.closed:
            connector = aiohttp.TCPConnector(
                ssl=self.ssl_context,
                keepalive_timeout=120,
                limit=8,
                force_close=False,
                enable_cleanup_closed=True,
            )
            self._tts_session = aiohttp.ClientSession(connector=connector)
        return self._tts_session

    async def prewarm(self):
        """Open a TLS+TCP connection to api.deepgram.com so the first real
        TTS request doesn't pay the handshake cost (~200-400ms)."""
        try:
            session = await self._get_tts_session()
            # Cheapest GET that hits the same host; we don't care about the body.
            async with session.get(self.base_url + "/projects",
                                    headers={"Authorization": f"Token {self.api_key}"},
                                    timeout=aiohttp.ClientTimeout(total=2)) as resp:
                await resp.read()
            print("[Deepgram] TTS connection pre-warmed")
        except Exception as e:
            print(f"[Deepgram] prewarm failed (non-fatal): {e}")

    async def text_to_speech(self, text: str) -> bytes:
        """Convert text to speech using Deepgram Aura. Returns MP3 bytes."""
        url = f"{self.base_url}/speak?model=aura-2-orion-en"
        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {"text": text}

        connector = aiohttp.TCPConnector(ssl=self.ssl_context)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    return await response.read()
                else:
                    error_text = await response.text()
                    raise Exception(f"TTS Error: {error_text}")

    async def text_to_speech_mulaw_stream(self, text: str):
        """Stream TTS as raw mulaw 8kHz bytes (Twilio's native format).

        Uses a persistent HTTP session so TLS/TCP handshakes are reused across
        consecutive TTS calls. Skips MP3 decoding + pydub resampling entirely.
        """
        url = (f"{self.base_url}/speak?model=aura-2-orion-en"
               f"&encoding=mulaw&sample_rate=8000&container=none")
        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {"text": text}

        session = await self._get_tts_session()
        async with session.post(url, headers=headers, json=payload) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"TTS Error: {error_text}")
            async for chunk in response.content.iter_chunked(1024):
                if chunk:
                    yield chunk

    async def speech_to_text(self, audio_data: bytes) -> str:
        """Convert speech to text using Deepgram Nova-3"""
        url = f"{self.base_url}/listen?model=nova-3&smart_format=true"
        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "audio/wav"
        }

        connector = aiohttp.TCPConnector(ssl=self.ssl_context)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(url, headers=headers, data=audio_data) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("results", {}).get("channels", [{}])[0].get("alternatives", [{}])[0].get("transcript", "")
                else:
                    error_text = await response.text()
                    raise Exception(f"STT Error: {error_text}")

    async def speech_to_text_buffer(self, wav_audio: bytes) -> str:
        """Convert speech buffer (WAV format) to text"""
        return await self.speech_to_text(wav_audio)


class DeepgramStreamSTT:
    """Real-time streaming STT over Deepgram's WebSocket API.

    - Accepts mulaw 8kHz frames (Twilio native format) — no conversion needed.
    - Uses Deepgram server-side VAD (`endpointing` + `utterance_end_ms`) to emit
      utterance-end events. Yields finalized transcripts via `transcripts()`.
    """

    def __init__(self, api_key: str, ssl_context: ssl.SSLContext):
        self.api_key = api_key
        self.ssl_context = ssl_context
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._session: Optional[aiohttp.ClientSession] = None
        self._queue: asyncio.Queue = asyncio.Queue()
        self._reader_task: Optional[asyncio.Task] = None
        self._keepalive_task: Optional[asyncio.Task] = None
        self._closed = False
        self._partial_buffer: list = []  # accumulate is_final transcripts until UtteranceEnd
        # Optional callback fired when Deepgram emits an interim transcript with text
        # (authoritative barge-in trigger — used for full LLM/TTS teardown).
        self.on_speech_started = None  # async callable: (transcript: str) -> None
        # Optional callback fired on Deepgram's raw SpeechStarted VAD event
        # (~150ms earlier than the first transcript — used for fast audio pause).
        self.on_voice_activity = None  # async callable, no args

    async def start(self):
        params = {
            "model": "nova-2",                 # general model; mulaw 8kHz supported
            "encoding": "mulaw",
            "sample_rate": "8000",
            "channels": "1",
            "interim_results": "true",
            "smart_format": "true",
            "punctuate": "true",
            "endpointing": "200",              # ms of silence to mark is_final (lower = snappier)
            "utterance_end_ms": "1000",        # Deepgram minimum is 1000ms
            "vad_events": "true",
        }
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"wss://api.deepgram.com/v1/listen?{qs}"
        headers = {"Authorization": f"Token {self.api_key}"}

        connector = aiohttp.TCPConnector(ssl=self.ssl_context)
        self._session = aiohttp.ClientSession(connector=connector)
        self._ws = await self._session.ws_connect(url, headers=headers, heartbeat=20)
        self._reader_task = asyncio.create_task(self._reader_loop())
        self._keepalive_task = asyncio.create_task(self._keepalive_loop())
        print("[Deepgram] streaming connection opened")

    async def send_audio(self, mulaw_chunk: bytes):
        if self._ws and not self._ws.closed:
            try:
                await self._ws.send_bytes(mulaw_chunk)
            except Exception as e:
                print(f"[Deepgram] send error: {e}")

    async def _keepalive_loop(self):
        try:
            while not self._closed and self._ws and not self._ws.closed:
                await asyncio.sleep(8)
                try:
                    await self._ws.send_json({"type": "KeepAlive"})
                except Exception:
                    break
        except asyncio.CancelledError:
            pass

    async def _reader_loop(self):
        try:
            async for msg in self._ws:
                if msg.type != aiohttp.WSMsgType.TEXT:
                    continue
                try:
                    data = json.loads(msg.data)
                except Exception:
                    continue

                msg_type = data.get("type")

                if msg_type == "Results":
                    alt = (data.get("channel", {})
                                .get("alternatives", [{}])[0])
                    transcript = (alt.get("transcript") or "").strip()
                    is_final = data.get("is_final", False)
                    speech_final = data.get("speech_final", False)

                    # Use interim transcripts with real content as the barge-in
                    # trigger — much more reliable than raw SpeechStarted, which
                    # also fires on noise / acoustic echo of our own TTS.
                    if transcript and self.on_speech_started:
                        try:
                            await self.on_speech_started(transcript)
                        except Exception as e:
                            print(f"[Deepgram] speech_started callback error: {e}")

                    if transcript and is_final:
                        self._partial_buffer.append(transcript)

                    # speech_final = end of utterance per Deepgram endpointing
                    if speech_final and self._partial_buffer:
                        full = " ".join(self._partial_buffer).strip()
                        self._partial_buffer = []
                        await self._queue.put(full)

                elif msg_type == "SpeechStarted":
                    # Deepgram VAD detected voice onset — fires ~150ms before
                    # the first transcript. Use this purely for fast audio pause
                    # (Twilio `clear`) — NOT for full LLM/TTS teardown, since
                    # this can also fire on noise / acoustic echo.
                    if self.on_voice_activity:
                        try:
                            await self.on_voice_activity()
                        except Exception as e:
                            print(f"[Deepgram] voice_activity callback error: {e}")

                elif msg_type == "UtteranceEnd":
                    # Backstop: flush whatever finals we accumulated
                    if self._partial_buffer:
                        full = " ".join(self._partial_buffer).strip()
                        self._partial_buffer = []
                        if full:
                            await self._queue.put(full)
        except Exception as e:
            print(f"[Deepgram] reader error: {e}")
        finally:
            await self._queue.put(None)  # sentinel to unblock consumers

    async def transcripts(self):
        """Async generator yielding finalized utterance strings."""
        while True:
            item = await self._queue.get()
            if item is None:
                return
            yield item

    async def close(self):
        self._closed = True
        if self._ws and not self._ws.closed:
            try:
                await self._ws.send_json({"type": "CloseStream"})
            except Exception:
                pass
            try:
                await self._ws.close()
            except Exception:
                pass
        for t in (self._reader_task, self._keepalive_task):
            if t:
                t.cancel()
        if self._session:
            await self._session.close()
        await self._queue.put(None)
        print("[Deepgram] streaming connection closed")

class GroqService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.groq.com/openai/v1"
        # Create SSL context that doesn't verify certificates (for dev only)
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

    # Fast model for voice — much lower TTFT than 70b-versatile
    VOICE_MODEL = "llama-3.1-8b-instant"
    BATCH_MODEL = "llama-3.3-70b-versatile"

    async def generate_response(self, messages: list, properties_context: str,
                                model: Optional[str] = None) -> str:
        """Generate AI response using Groq (non-streaming)."""
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        system_message = build_system_prompt(properties_context)

        payload = {
            "model": model or self.BATCH_MODEL,
            "messages": [{"role": "system", "content": system_message}] + messages,
            "temperature": 0.7,
            "max_tokens": 500
        }

        connector = aiohttp.TCPConnector(ssl=self.ssl_context)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    error_text = await response.text()
                    raise Exception(f"LLM Error: {error_text}")

    async def generate_response_stream(self, messages: list, properties_context: str,
                                       model: Optional[str] = None,
                                       user_text: str = ""):
        """Stream Groq tokens (SSE) using Adelphos-style messaging:
          - Voice-tuned system prompt
          - Intent classifier hint injected as second system message
          - 70B model for higher quality (Groq's TTFT is fast even on 70B)
        """
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }
        system_message = build_system_prompt(properties_context)

        # Adelphos-style: detect intent and append as a second system message
        intent = classify_intent(user_text or (messages[-1].get("content", "") if messages else ""), messages)
        intent_hint = _INTENT_CONTEXT_HINTS.get(intent, "")
        msgs = [{"role": "system", "content": system_message}] + messages
        if intent_hint:
            msgs.append({"role": "system", "content": intent_hint})
        print(f"[LLM] Intent: {intent}")

        payload = {
            "model": model or self.BATCH_MODEL,   # 70B for quality, like Adelphos
            "messages": msgs,
            "temperature": 0.7,
            "max_tokens": 300,
            "stream": True,
        }

        connector = aiohttp.TCPConnector(ssl=self.ssl_context)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"LLM Stream Error: {error_text}")
                async for raw_line in response.content:
                    line = raw_line.decode("utf-8", errors="ignore").strip()
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        return
                    try:
                        obj = json.loads(data)
                    except Exception:
                        continue
                    delta = (obj.get("choices", [{}])[0]
                                .get("delta", {})
                                .get("content"))
                    if delta:
                        yield delta

class PropertyService:
    def __init__(self, properties: list):
        self.properties = properties

    def format_properties_for_context(self) -> str:
        """Format properties for LLM context"""
        context = []
        for p in self.properties:
            context.append(f"""
Property: {p['name']}
- Type: {p['type']}
- Location: {p['location']} ({p['district']})
- Price: S${p['price']:,}
- Bedrooms: {p['bedrooms']}, Bathrooms: {p['bathrooms']}
- Size: {p['sqft']} sqft
- Amenities: {', '.join(p['amenities'])}
- MRT: {p['mrt']}
- Description: {p['description']}
""")
        return "\n".join(context)

    def search_properties(self, budget: Optional[int] = None, location: Optional[str] = None,
                         property_type: Optional[str] = None, bedrooms: Optional[int] = None) -> list:
        """Search properties based on criteria"""
        results = self.properties.copy()

        if budget:
            results = [p for p in results if p['price'] <= budget * 1.1]  # 10% flexibility

        if location:
            results = [p for p in results if location.lower() in p['location'].lower() or
                      location.lower() in p['district'].lower()]

        if property_type:
            results = [p for p in results if property_type.lower() in p['type'].lower()]

        if bedrooms:
            results = [p for p in results if p['bedrooms'] >= bedrooms]

        return results

class ConversationManager:
    def __init__(self):
        self.conversations = {}

    def get_or_create(self, session_id: str) -> list:
        if session_id not in self.conversations:
            self.conversations[session_id] = []
        return self.conversations[session_id]

    def add_message(self, session_id: str, role: str, content: str):
        if session_id not in self.conversations:
            self.conversations[session_id] = []
        self.conversations[session_id].append({"role": role, "content": content})

    def clear(self, session_id: str):
        if session_id in self.conversations:
            del self.conversations[session_id]

# Initialize services
dg_service = DeepgramService(DEEPGRAM_API_KEY)
groq_service = GroqService(GROQ_API_KEY)
property_service = PropertyService(SINGAPORE_PROPERTIES)
conversation_manager = ConversationManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(title="Real Estate Voice Agent", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
async def get_home_page():
    """Serve the main calling interface"""
    return HTMLResponse(content=HTML_PAGE)

@app.get("/api/properties")
async def get_properties():
    """Get all available properties"""
    return {"properties": SINGAPORE_PROPERTIES}

@app.get("/api/persona")
async def get_persona():
    """Get current agent persona configuration"""
    return {
        "persona": current_persona,
        "welcome_message": current_persona["welcome_message"].format(
            agent_name=current_persona["agent_name"],
            agency_name=current_persona["agency_name"]
        )
    }

@app.post("/api/persona")
async def update_persona(request: Request):
    """Update agent persona configuration"""
    global current_persona
    data = await request.json()

    # Update only provided fields
    allowed_fields = ["agent_name", "agency_name", "personality_traits", "expertise", "guidelines", "greeting_style", "welcome_message", "custom_prompt"]

    for field in allowed_fields:
        if field in data:
            current_persona[field] = data[field]

    return {
        "status": "success",
        "message": "Persona updated successfully",
        "persona": current_persona
    }

@app.post("/api/persona/reset")
async def reset_persona():
    """Reset persona to default configuration"""
    global current_persona
    current_persona = DEFAULT_PERSONA_CONFIG.copy()
    return {
        "status": "success",
        "message": "Persona reset to default",
        "persona": current_persona
    }

@app.get("/api/persona/presets")
async def get_persona_presets():
    """Get preset persona templates"""
    presets = {
        "real_estate_professional": DEFAULT_PERSONA_CONFIG,
        "friendly_neighbor": {
            "agent_name": "Sarah",
            "agency_name": "Community Homes",
            "personality_traits": """- Friendly and approachable, like a helpful neighbor
- Casual but knowledgeable
- Enthusiastic about helping families find their perfect home
- Patient and understanding
- Uses relatable examples""",
            "expertise": """- Local neighborhoods and community vibes
- Family-friendly amenities and schools
- Commute times and transportation options
- Hidden gems in the property market""",
            "guidelines": """1. Start with a warm, friendly greeting
2. Ask about their lifestyle and what's important to them
3. Share personal insights about neighborhoods
4. Be honest about pros and cons
5. Make them feel like they're talking to a friend""",
            "greeting_style": "Casual and friendly, like meeting a neighbor",
            "welcome_message": "Hey there! I'm {agent_name} from {agency_name}. I'm so excited to help you find a place you'll love! What brings you here today?"
        },
        "luxury_consultant": {
            "agent_name": "Victoria Sterling",
            "agency_name": "Sterling Luxury Estates",
            "personality_traits": """- Sophisticated and refined
- Discreet and professional
- Highly knowledgeable about luxury market
- Attention to detail and excellence
- Confident but not arrogant""",
            "expertise": """- Ultra-high-net-worth property market
- Investment portfolios and asset management
- Exclusive off-market listings
- International property acquisitions
- Privacy and security considerations""",
            "guidelines": """1. Maintain absolute discretion and professionalism
2. Focus on exclusivity and prestige
3. Highlight investment value and appreciation potential
4. Emphasize privacy and security features
5. Arrange private viewings and VIP treatment""",
            "greeting_style": "Elegant and refined, acknowledging their time is valuable",
            "welcome_message": "Good day. I am {agent_name} of {agency_name}. It is a privilege to assist you. How may I be of service in your property endeavors?"
        },
        "tech_savvy_millennial": {
            "agent_name": "Jordan",
            "agency_name": "NextGen Properties",
            "personality_traits": """- Tech-savvy and modern
- Efficient and data-driven
- Relatable and down-to-earth
- Quick to understand modern lifestyles
- No fluff, straight to the point""",
            "expertise": """- Smart home technology integration
- Co-working spaces and digital nomad friendly properties
- Properties with high-speed connectivity
- Urban development trends
- Sustainable and eco-friendly homes""",
            "guidelines": """1. Be efficient and respect their time
2. Lead with data and key facts
3. Highlight tech amenities and modern features
4. Suggest virtual tours and digital processes
5. Be direct and transparent about pricing""",
            "greeting_style": "Casual and efficient, acknowledging their busy schedule",
            "welcome_message": "Hey! I'm {agent_name} from {agency_name}. I'll get straight to it - what are you looking for? Budget, location, must-haves?"
        }
    }
    return {"presets": presets}

@app.post("/api/call")
async def initiate_call(request: Request):
    """Initiate an outbound call via Twilio"""
    data = await request.json()
    phone_number = data.get("phone_number")

    if not phone_number:
        return JSONResponse(status_code=400, content={"error": "Phone number required"})

    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        return JSONResponse(status_code=500, content={
            "error": "Twilio credentials not configured",
            "message": "Please set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN environment variables"
        })

    # Actually initiate the Twilio call
    try:
        from twilio.rest import Client

        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

        # Build the webhook URL - use PUBLIC_URL env var (for ngrok) or request host
        public_url = os.getenv("PUBLIC_URL", "")
        if public_url:
            webhook_url = f"{public_url}/twilio/webhook"
        else:
            host = request.headers.get('host', 'localhost:8001')
            webhook_url = f"https://{host}/twilio/webhook"

        call = client.calls.create(
            to=phone_number,
            from_=TWILIO_PHONE_NUMBER,
            url=webhook_url,
            method="POST"
        )

        return {
            "status": "success",
            "message": f"Call initiated to {phone_number}",
            "call_sid": call.sid,
            "webhook_url": webhook_url
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={
            "error": "Failed to initiate call",
            "message": str(e)
        })

@app.post("/twilio/webhook")
async def twilio_webhook(request: Request):
    """Handle incoming Twilio voice webhook"""
    from twilio.twiml.voice_response import VoiceResponse

    response = VoiceResponse()

    # Get the WebSocket URL - prefer PUBLIC_URL env var for ngrok
    public_url = os.getenv("PUBLIC_URL", "").replace("https://", "wss://").replace("http://", "ws://")

    # Check if WebSocket mode is enabled (requires proper infrastructure)
    websocket_mode = os.getenv("WEBSOCKET_MODE", "true").lower() == "true"

    if websocket_mode and public_url:
        # Advanced mode: Real-time bidirectional streaming via Twilio Media Streams
        from twilio.twiml.voice_response import Connect

        # Say greeting FIRST, before opening the stream
        response.say("Connecting you to your AI real estate agent. Please hold.")

        connect = Connect()
        connect.stream(url=f"{public_url}/ws/voice")
        response.append(connect)
    else:
        # Simple mode: Interactive voice menu
        agent_name = current_persona.get("agent_name", "Alexander Chen")
        agency_name = current_persona.get("agency_name", "Prestige Properties Singapore")

        welcome_msg = current_persona.get("welcome_message", "Hello! I'm {agent_name} from {agency_name}.").format(
            agent_name=agent_name,
            agency_name=agency_name
        )

        # Add the greeting
        response.say(welcome_msg)

        # Provide options for property inquiries
        response.say("I can help you find your dream property in Singapore. Here's what I can do:")

        # List properties briefly
        response.say("We have properties ranging from 1.8 million to 12 million Singapore dollars. ")
        response.say("Locations include Marina Bay, Orchard Road, Sentosa Cove, and more.")

        # Give instructions
        response.say("For detailed assistance, please visit our website or chat with me online. Thank you for calling!")

        # Hang up
        response.hangup()

    return HTMLResponse(content=str(response), media_type="application/xml")

import struct
try:
    import audioop
except ImportError:
    # Python 3.13+ removed audioop, use audioop-lts instead
    import audioop_lts as audioop

# Per-session state for voice calls
voice_sessions: dict = {}


@app.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket):
    """WebSocket endpoint for Twilio Media Streams.

    Audio flow:
      Twilio (mulaw 8kHz) ─► our server ─► Deepgram streaming STT (websocket)
                                          └─► utterance text ─► Groq LLM ─► Deepgram TTS ─► Twilio
    """
    await websocket.accept()
    session_id = str(datetime.now().timestamp())

    state = {
        "call_sid": None,
        "stream_sid": None,
        "agent_speaking": False,         # True while TTS is being sent
        "processing": False,             # serialize LLM turns
        "tts_task": None,                # current TTS playback task (for barge-in cancel)
        "interrupted": False,            # set when caller barges in
    }
    voice_sessions[session_id] = state

    # Open a streaming STT connection for this call
    stt = DeepgramStreamSTT(DEEPGRAM_API_KEY, dg_service.ssl_context)
    consumer_task: Optional[asyncio.Task] = None

    print(f"Voice WebSocket connected: {session_id}")

    # Grace period at TTS start during which barge-in is ignored. Set to 100ms
    # so the caller can interrupt the intro almost immediately. The 2-char
    # transcript filter below rejects most echo/noise blips.
    BARGE_IN_GRACE_MS = 100
    # Minimum interim-transcript length before we treat it as real speech.
    BARGE_IN_MIN_CHARS = 2

    async def _send_twilio_clear():
        """Drop in-flight audio in Twilio's buffer so the caller hears silence ASAP."""
        if not state.get("stream_sid"):
            return
        try:
            await websocket.send_text(json.dumps({
                "event": "clear",
                "streamSid": state["stream_sid"],
            }))
        except Exception as e:
            print(f"[barge-in] failed to send clear: {e}")

    async def on_voice_activity():
        """Fast pre-trigger: Deepgram VAD detected voice onset (~150ms before transcript).

        Sends Twilio `clear` immediately so the caller hears silence faster.
        Does NOT cancel the LLM/TTS player — that's handled by `on_barge_in`
        once a real transcript arrives (avoids tearing down on noise/echo).

        Fires on EVERY VAD event (no per-turn lock) so if any new TTS audio
        leaks into Twilio's buffer between VAD pulses we keep flushing it.
        """
        agent_speaking = state.get("agent_speaking", False)
        interrupted = state.get("interrupted", False)
        started = state.get("t_turn_start") or 0
        elapsed_ms = int((asyncio.get_event_loop().time() - started) * 1000) if started else -1

        if not agent_speaking:
            print(f"[VAD] skip: agent not speaking (elapsed={elapsed_ms}ms)")
            return
        if interrupted:
            # Already torn down, but still re-clear in case TTS leaked a stray chunk
            await _send_twilio_clear()
            return
        if elapsed_ms < BARGE_IN_GRACE_MS:
            print(f"[VAD] skip: in grace window (elapsed={elapsed_ms}ms < {BARGE_IN_GRACE_MS}ms)")
            return

        # Record only the first onset for latency measurement
        if not state.get("t_voice_activity"):
            state["t_voice_activity"] = asyncio.get_event_loop().time()
            print(f"[VAD] FIRE: voice onset @ {elapsed_ms}ms — clearing Twilio buffer")
        await _send_twilio_clear()

    async def on_barge_in(transcript: str = ""):
        """Authoritative barge-in: tear down LLM/TTS once a real transcript arrives."""
        agent_speaking = state.get("agent_speaking", False)
        interrupted = state.get("interrupted", False)
        started = state.get("t_turn_start") or 0
        elapsed_ms = int((asyncio.get_event_loop().time() - started) * 1000) if started else -1

        if not agent_speaking:
            print(f"[barge-in] skip ({transcript!r}): agent not speaking (elapsed={elapsed_ms}ms)")
            return
        if interrupted:
            return  # already cancelled this turn
        if len(transcript.strip()) < BARGE_IN_MIN_CHARS:
            return  # too short — likely noise
        if elapsed_ms < BARGE_IN_GRACE_MS:
            print(f"[barge-in] skip ({transcript!r}): in grace window ({elapsed_ms}ms < {BARGE_IN_GRACE_MS}ms)")
            return

        # Measure how much earlier the fast pre-trigger fired (if it did)
        fast_lead_ms = ""
        t_va = state.get("t_voice_activity")
        if t_va:
            fast_lead_ms = f" (fast pre-clear lead: {int((asyncio.get_event_loop().time() - t_va) * 1000)}ms)"

        print(f"[barge-in] FIRE: caller said {transcript!r} after {elapsed_ms}ms, cancelling TTS{fast_lead_ms}")
        state["interrupted"] = True

        # Drain pending TTS segments and cancel the player
        q = state.get("tts_queue")
        if q is not None:
            _drain_queue(q)
            try:
                q.put_nowait(None)  # unblock player if waiting on get()
            except asyncio.QueueFull:
                pass
        player = state.get("tts_player_task")
        if player and not player.done():
            player.cancel()

        # Tell Twilio to drop any audio we already sent that hasn't played yet
        # (may have already been sent by on_voice_activity — duplicate is cheap)
        await _send_twilio_clear()

    stt.on_speech_started = on_barge_in
    stt.on_voice_activity = on_voice_activity

    try:
        # Pre-warm Deepgram TTS connection in parallel with STT setup so the
        # first response's TTS first-byte is much faster (~300ms saved).
        asyncio.create_task(dg_service.prewarm())
        await stt.start()

        async def transcript_consumer():
            async for utterance in stt.transcripts():
                if not utterance:
                    continue
                # Adelphos-style noise filter (drops "you", "bye", music, etc.)
                if looks_like_noise(utterance):
                    print(f"[skip-noise] {utterance!r}")
                    continue
                # Adelphos-style mishearing corrections (HDB, condo, "2 BR", etc.)
                utterance = correct_transcript(utterance)
                if state["processing"]:
                    print(f"[skip-busy] {utterance!r}")
                    continue
                state["processing"] = True
                try:
                    await handle_user_utterance(websocket, state, session_id, utterance)
                finally:
                    state["processing"] = False

        consumer_task = asyncio.create_task(transcript_consumer())

        while True:
            message = await websocket.receive_text()
            data = json.loads(message)
            event_type = data.get("event")

            if event_type == "start":
                state["call_sid"] = data.get("start", {}).get("callSid")
                state["stream_sid"] = data.get("start", {}).get("streamSid")
                print(f"Call started - Call SID: {state['call_sid']}, Stream SID: {state['stream_sid']}")
                # Run greeting as a background task so the WebSocket loop keeps
                # forwarding caller audio to Deepgram in parallel — otherwise
                # barge-in is impossible during the intro because no media
                # events are processed while we await the greeting.
                asyncio.create_task(
                    handle_voice_response(websocket, state, session_id, is_greeting=True)
                )

            elif event_type == "media":
                payload = data.get("media", {}).get("payload", "")
                if not payload or not state["stream_sid"]:
                    continue
                # Always forward caller audio to Deepgram so barge-in is detectable.
                # Twilio's inbound track is mic-only, so our TTS isn't fed back here
                # (acoustic echo via the caller's handset is usually negligible).
                chunk = base64.b64decode(payload)
                await stt.send_audio(chunk)

            elif event_type == "stop":
                print(f"Call ended - Call SID: {state['call_sid']}")
                # Cancel TTS player to prevent sending to closed WebSocket
                player = state.get("tts_player_task")
                if player and not player.done():
                    player.cancel()
                    try:
                        await player
                    except asyncio.CancelledError:
                        pass
                break

            elif event_type == "mark":
                mark_name = data.get("mark", {}).get("name", "")
                print(f"Audio mark received: {mark_name}")

    except WebSocketDisconnect:
        print(f"Voice WebSocket disconnected: {session_id}")
    except Exception as e:
        print(f"Error in voice websocket: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await stt.close()
        if consumer_task:
            consumer_task.cancel()
        # Cancel TTS player if still running
        player = state.get("tts_player_task")
        if player and not player.done():
            player.cancel()
        voice_sessions.pop(session_id, None)
        conversation_manager.clear(session_id)


SENTENCE_TERMINATORS = ".!?"
SOFT_TERMINATORS = ",;:"
FIRST_FLUSH_MIN_CHARS = 12   # ship first sentence ASAP for low TTFA
NEXT_FLUSH_MIN_CHARS = 30    # later sentences: bigger chunks → smoother prosody

# Adelphos-style sentence splitter: split after . ! ? when followed by whitespace.
# Used incrementally on the streaming buffer to flush completed sentences to TTS.
_SENTENCE_SPLIT_RE = _re.compile(r'(?<=[.!?])\s+')


def _find_flush_point(buf: str, min_chars: int, allow_soft: bool = False) -> int:
    """Return an index to split `buf` at (exclusive) for flushing to TTS, or -1.

    Mirrors Adelphos `re.split(r'(?<=[.!?])\\s+', ai_response)` but operates
    incrementally on a growing buffer so we can stream sentence-by-sentence.
    """
    if len(buf) < min_chars:
        return -1
    # Look for the LAST hard sentence terminator followed by whitespace.
    last_match = None
    for m in _SENTENCE_SPLIT_RE.finditer(buf):
        if m.start() >= min_chars - 1:
            last_match = m
    if last_match:
        return last_match.end()
    # Soft terminators (commas) only allowed for the very first flush so the
    # caller hears something quickly even if the model rambles before a period.
    if allow_soft:
        for i in range(len(buf) - 1, min_chars - 1, -1):
            if buf[i] in SOFT_TERMINATORS and (i == len(buf) - 1 or buf[i + 1] in " \n\t"):
                return i + 1
    return -1


async def _stream_segment_to_twilio(websocket: WebSocket, state: dict, text: str):
    """Stream one TTS segment to Twilio. Cancellable via state['interrupted']."""
    if not text or not text.strip():
        return
    stream_sid = state["stream_sid"]
    chunk_size = 320  # 20ms @ 8kHz mulaw
    chunk_ms = 20
    pending = bytearray()
    sent_any = False
    t_seg_start = asyncio.get_event_loop().time()

    async for raw in dg_service.text_to_speech_mulaw_stream(text):
        if state.get("interrupted"):
            return
        pending.extend(raw)
        while len(pending) >= chunk_size:
            if state.get("interrupted"):
                return
            chunk = bytes(pending[:chunk_size])
            del pending[:chunk_size]
            await websocket.send_text(json.dumps({
                "streamSid": stream_sid,
                "event": "media",
                "media": {"payload": base64.b64encode(chunk).decode('utf-8')},
            }))
            if not sent_any:
                tta = int((asyncio.get_event_loop().time() - t_seg_start) * 1000)
                # Mark first audio of the whole turn (state['t_turn_start'] set by caller)
                if state.get("t_turn_start") is not None and not state.get("first_audio_logged"):
                    total = int((asyncio.get_event_loop().time() - state["t_turn_start"]) * 1000)
                    print(f"[latency] first audio out: {total}ms (TTS first-byte for this segment: {tta}ms)")
                    state["first_audio_logged"] = True
                sent_any = True
            await asyncio.sleep(chunk_ms / 1000.0)

    # Tail
    if not state.get("interrupted") and pending:
        await websocket.send_text(json.dumps({
            "streamSid": stream_sid,
            "event": "media",
            "media": {"payload": base64.b64encode(bytes(pending)).decode('utf-8')},
        }))


async def _tts_player_loop(websocket: WebSocket, state: dict):
    """Consume `state['tts_queue']` and play each text segment in order."""
    queue: asyncio.Queue = state["tts_queue"]
    state["agent_speaking"] = True
    try:
        while True:
            segment = await queue.get()
            if segment is None:  # end-of-turn sentinel
                return
            if state.get("interrupted"):
                continue  # drain remaining items quickly
            await _stream_segment_to_twilio(websocket, state, segment)
    except asyncio.CancelledError:
        print("[tts] player cancelled")
        raise
    finally:
        state["agent_speaking"] = False
        # Final mark for the whole turn
        if not state.get("interrupted") and state.get("stream_sid"):
            try:
                await websocket.send_text(json.dumps({
                    "streamSid": state["stream_sid"],
                    "event": "mark",
                    "mark": {"name": f"turn_{datetime.now().timestamp()}"},
                }))
            except Exception:
                pass


def _drain_queue(q: asyncio.Queue):
    """Synchronously remove all queued items (used on barge-in)."""
    try:
        while True:
            q.get_nowait()
    except asyncio.QueueEmpty:
        pass


async def handle_user_utterance(websocket: WebSocket, state: dict, session_id: str, user_input: str):
    """Pipeline: stream Groq tokens → split into sentences → enqueue for TTS player.

    First-sentence-out lands ~300-700ms after user stops talking thanks to:
      - llama-3.1-8b-instant (Groq TTFT ~150-300ms)
      - sentence boundary flushing (don't wait for full LLM response)
      - Deepgram TTS streaming with mulaw 8kHz (no MP3 decode)
    """
    state["t_turn_start"] = asyncio.get_event_loop().time()
    state["first_audio_logged"] = False
    state["interrupted"] = False
    state["voice_activity_pending"] = False
    state["t_voice_activity"] = None
    state["tts_queue"] = asyncio.Queue()
    state["tts_player_task"] = asyncio.create_task(_tts_player_loop(websocket, state))

    print(f"User said: {user_input!r}")
    conversation_manager.add_message(session_id, "user", user_input)

    properties_context = property_service.format_properties_for_context()
    conversation_history = conversation_manager.get_or_create(session_id)

    full_response = []
    buf = ""
    first_flush_done = False
    t_first_token_logged = False

    try:
        async for delta in groq_service.generate_response_stream(
            conversation_history, properties_context, user_text=user_input
        ):
            if state.get("interrupted"):
                break
            if not t_first_token_logged:
                ttft = int((asyncio.get_event_loop().time() - state["t_turn_start"]) * 1000)
                print(f"[latency] LLM first token: {ttft}ms")
                t_first_token_logged = True
            full_response.append(delta)
            buf += delta
            min_chars = FIRST_FLUSH_MIN_CHARS if not first_flush_done else NEXT_FLUSH_MIN_CHARS
            cut = _find_flush_point(buf, min_chars, allow_soft=not first_flush_done)
            if cut > 0:
                segment = buf[:cut]
                buf = buf[cut:]
                await state["tts_queue"].put(segment)
                first_flush_done = True

        # Flush remaining tail
        if not state.get("interrupted") and buf.strip():
            await state["tts_queue"].put(buf)

        # End-of-turn sentinel
        await state["tts_queue"].put(None)
        # Wait for player to finish playback
        try:
            await state["tts_player_task"]
        except asyncio.CancelledError:
            pass

        response_text = "".join(full_response)
        if response_text.strip():
            conversation_manager.add_message(session_id, "assistant", response_text)
            print(f"AI response: {response_text}")

    except Exception as e:
        print(f"Error handling user utterance: {e}")
        import traceback
        traceback.print_exc()
    finally:
        state["tts_player_task"] = None


async def handle_voice_response(websocket: WebSocket, state: dict, session_id: str, is_greeting: bool = False):
    """Generate the call's opening intro via the LLM streaming pipeline.

    No hardcoded welcome string — the LLM produces a fresh, natural intro every
    call based on the active persona. Uses the SAME pipeline as a normal turn
    (streaming Groq → sentence flush → TTS queue → player loop) so barge-in
    behaves identically to mid-conversation interrupts.

    `state['agent_speaking']` is flipped on immediately so that even before the
    first TTS byte arrives the caller can interrupt — `on_barge_in` won't
    short-circuit on an `agent_speaking == False` guard during LLM warmup.
    """
    try:
        if not is_greeting:
            return

        # Per-turn state reset (mirror handle_user_utterance)
        state["t_turn_start"] = asyncio.get_event_loop().time()
        state["first_audio_logged"] = False
        state["interrupted"] = False
        state["voice_activity_pending"] = False
        state["t_voice_activity"] = None
        state["agent_speaking"] = True  # unblock barge-in immediately
        state["tts_queue"] = asyncio.Queue()
        state["tts_player_task"] = asyncio.create_task(_tts_player_loop(websocket, state))

        # Build a kickoff turn that tells the LLM to introduce itself naturally.
        # The base system prompt already contains the persona name + agency, so
        # we just nudge the model to greet. We do NOT add this synthetic user
        # message to the persistent conversation history — it's a one-shot prompt.
        properties_context = property_service.format_properties_for_context()
        kickoff_user_msg = (
            "[SYSTEM: The phone call has just connected. Greet the caller in ONE "
            "warm, natural sentence — introduce yourself by name and agency, then "
            "ask what kind of property they're looking for. Speak as you naturally "
            "would on a phone call. Do not use generic openers like 'Great to "
            "connect' or 'Thank you for calling'.]"
        )

        full_response = []
        buf = ""
        first_flush_done = False
        t_first_token_logged = False

        async for delta in groq_service.generate_response_stream(
            [{"role": "user", "content": kickoff_user_msg}],
            properties_context,
            user_text=kickoff_user_msg,
        ):
            if state.get("interrupted"):
                break
            if not t_first_token_logged:
                ttft = int((asyncio.get_event_loop().time() - state["t_turn_start"]) * 1000)
                print(f"[latency] greeting LLM first token: {ttft}ms")
                t_first_token_logged = True
            full_response.append(delta)
            buf += delta
            min_chars = FIRST_FLUSH_MIN_CHARS if not first_flush_done else NEXT_FLUSH_MIN_CHARS
            cut = _find_flush_point(buf, min_chars, allow_soft=not first_flush_done)
            if cut > 0:
                segment = buf[:cut]
                buf = buf[cut:]
                await state["tts_queue"].put(segment)
                first_flush_done = True

        if not state.get("interrupted") and buf.strip():
            await state["tts_queue"].put(buf)
        await state["tts_queue"].put(None)

        try:
            await state["tts_player_task"]
        except asyncio.CancelledError:
            print("[tts] greeting cancelled by barge-in")

        greeting_text = "".join(full_response).strip()
        if greeting_text:
            conversation_manager.add_message(session_id, "assistant", greeting_text)
            print(f"Greeting (LLM-generated): {greeting_text}")
    except Exception as e:
        print(f"Error sending voice response: {e}")
        import traceback
        traceback.print_exc()
    finally:
        state["tts_player_task"] = None


async def send_twilio_audio_response(websocket: WebSocket, state: dict, text: str):
    """Stream Deepgram TTS (already in mulaw 8kHz) directly to Twilio.

    Latency wins:
      - No MP3 download wait — bytes are streamed as Deepgram generates them.
      - No pydub MP3 decode + 8kHz resample — Deepgram returns the right format.
      - First audio chunk reaches Twilio in ~150-300ms (vs ~1.5s before).

    Cancellable for barge-in: if the task is cancelled or `state['interrupted']`
    is set, playback stops mid-stream and Twilio is told to `clear` its buffer.
    """
    stream_sid = state["stream_sid"]
    state["agent_speaking"] = True
    state["tts_started_at"] = asyncio.get_event_loop().time()

    chunk_size = 320  # 20ms @ 8kHz mulaw
    chunk_ms = 20

    pending = bytearray()
    sent_any = False
    t_start = asyncio.get_event_loop().time()

    try:
        async for raw in dg_service.text_to_speech_mulaw_stream(text):
            if state.get("interrupted"):
                print("[tts] interrupted flag set, stopping playback")
                break
            pending.extend(raw)

            # Drain in 20ms chunks at real-time pace
            while len(pending) >= chunk_size:
                if state.get("interrupted"):
                    break
                chunk = bytes(pending[:chunk_size])
                del pending[:chunk_size]
                await websocket.send_text(json.dumps({
                    "streamSid": stream_sid,
                    "event": "media",
                    "media": {"payload": base64.b64encode(chunk).decode('utf-8')},
                }))
                if not sent_any:
                    elapsed_ms = int((asyncio.get_event_loop().time() - t_start) * 1000)
                    print(f"[tts] first audio chunk sent in {elapsed_ms}ms")
                    sent_any = True
                await asyncio.sleep(chunk_ms / 1000.0)

        # Flush any leftover (<20ms) tail
        if not state.get("interrupted") and pending:
            await websocket.send_text(json.dumps({
                "streamSid": stream_sid,
                "event": "media",
                "media": {"payload": base64.b64encode(bytes(pending)).decode('utf-8')},
            }))

        if not state.get("interrupted"):
            await websocket.send_text(json.dumps({
                "streamSid": stream_sid,
                "event": "mark",
                "mark": {"name": f"response_{datetime.now().timestamp()}"},
            }))
            print(f"Sent audio response: {text[:60]}...")

    except asyncio.CancelledError:
        print(f"[tts] cancelled mid-playback: {text[:40]}...")
        raise
    except Exception as e:
        print(f"Error sending Twilio audio: {e}")
        import traceback
        traceback.print_exc()
    finally:
        state["agent_speaking"] = False


def create_wav_header(audio_data: bytes, sample_rate: int = 8000, channels: int = 1, sample_width: int = 2) -> bytes:
    """Create WAV header for audio data"""
    # WAV header format
    # RIFF chunk
    header = b'RIFF'
    header += struct.pack('<I', 36 + len(audio_data))  # File size
    header += b'WAVE'

    # fmt chunk
    header += b'fmt '
    header += struct.pack('<I', 16)  # Subchunk size
    header += struct.pack('<H', 1)   # Audio format (PCM)
    header += struct.pack('<H', channels)  # Channels
    header += struct.pack('<I', sample_rate)  # Sample rate
    header += struct.pack('<I', sample_rate * channels * sample_width)  # Byte rate
    header += struct.pack('<H', channels * sample_width)  # Block align
    header += struct.pack('<H', sample_width * 8)  # Bits per sample

    # data chunk
    header += b'data'
    header += struct.pack('<I', len(audio_data))  # Data size

    return header

@app.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket):
    """WebSocket endpoint for text-based chat (for web interface)"""
    await websocket.accept()
    session_id = str(datetime.now().timestamp())

    try:
        # Send greeting based on current persona
        greeting = current_persona["welcome_message"].format(
            agent_name=current_persona["agent_name"],
            agency_name=current_persona["agency_name"]
        )
        await websocket.send_json({"type": "assistant", "text": greeting})
        conversation_manager.add_message(session_id, "assistant", greeting)

        while True:
            # Receive message from client
            data = await websocket.receive_json()
            user_input = data.get("message", "")

            if not user_input:
                continue

            # Add to conversation history
            conversation_manager.add_message(session_id, "user", user_input)

            # Generate response
            properties_context = property_service.format_properties_for_context()
            conversation_history = conversation_manager.get_or_create(session_id)

            response_text = await groq_service.generate_response(
                conversation_history,
                properties_context
            )

            # Add assistant response to history
            conversation_manager.add_message(session_id, "assistant", response_text)

            # Send response
            await websocket.send_json({"type": "assistant", "text": response_text})

    except WebSocketDisconnect:
        conversation_manager.clear(session_id)
    except Exception as e:
        print(f"Error in chat websocket: {e}")
        conversation_manager.clear(session_id)

HTML_PAGE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Prestige Properties Singapore - AI Voice Agent</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🏠</text></svg>">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        header {
            text-align: center;
            color: white;
            padding: 40px 20px;
        }

        header h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }

        header p {
            font-size: 1.1rem;
            opacity: 0.9;
        }

        .persona-section {
            margin-bottom: 30px;
        }

        .persona-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            cursor: pointer;
            padding: 15px 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 10px;
            transition: all 0.3s ease;
        }

        .persona-header:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }

        .persona-header h3 {
            font-size: 1.2rem;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .persona-toggle {
            font-size: 1.5rem;
            transition: transform 0.3s ease;
        }

        .persona-toggle.open {
            transform: rotate(180deg);
        }

        .persona-content {
            display: none;
            background: white;
            border-radius: 0 0 15px 15px;
            padding: 25px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }

        .persona-content.open {
            display: block;
        }

        .persona-form {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }

        @media (max-width: 900px) {
            .persona-form {
                grid-template-columns: 1fr;
            }
        }

        .persona-field {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .persona-field.full-width {
            grid-column: 1 / -1;
        }

        .persona-field label {
            font-weight: 600;
            color: #333;
            font-size: 0.95rem;
        }

        .persona-field input,
        .persona-field textarea,
        .persona-field select {
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 0.95rem;
            font-family: inherit;
            transition: border-color 0.3s;
        }

        .persona-field input:focus,
        .persona-field textarea:focus,
        .persona-field select:focus {
            outline: none;
            border-color: #667eea;
        }

        .persona-field textarea {
            min-height: 100px;
            resize: vertical;
        }

        .persona-actions {
            grid-column: 1 / -1;
            display: flex;
            gap: 15px;
            justify-content: flex-end;
            margin-top: 10px;
        }

        .preset-btn {
            background: #f0f0f0;
            color: #333;
            border: none;
            padding: 12px 20px;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }

        .preset-btn:hover {
            background: #e0e0e0;
        }

        .save-btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }

        .save-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }

        .current-agent-display {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 15px 20px;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 15px;
        }

        .agent-avatar {
            width: 50px;
            height: 50px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
        }

        .agent-info h4 {
            color: #333;
            margin-bottom: 3px;
        }

        .agent-info p {
            color: #666;
            font-size: 0.9rem;
        }

        .main-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-top: 20px;
        }

        @media (max-width: 900px) {
            .main-grid {
                grid-template-columns: 1fr;
            }
        }

        .card {
            background: white;
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }

        .card h2 {
            color: #333;
            margin-bottom: 20px;
            font-size: 1.5rem;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .icon {
            width: 30px;
            height: 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 1.2rem;
        }

        .call-section {
            margin-bottom: 25px;
        }

        .call-section label {
            display: block;
            margin-bottom: 8px;
            color: #555;
            font-weight: 500;
        }

        .phone-input-group {
            display: flex;
            gap: 10px;
        }

        .phone-input {
            flex: 1;
            padding: 15px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-size: 1rem;
            transition: border-color 0.3s;
        }

        .phone-input:focus {
            outline: none;
            border-color: #667eea;
        }

        .call-button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 10px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .call-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }

        .call-button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }

        .chat-interface {
            height: 400px;
            display: flex;
            flex-direction: column;
        }

        .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 10px;
            margin-bottom: 15px;
        }

        .message {
            margin-bottom: 15px;
            padding: 12px 16px;
            border-radius: 15px;
            max-width: 80%;
            word-wrap: break-word;
        }

        .message.user {
            background: #667eea;
            color: white;
            margin-left: auto;
            border-bottom-right-radius: 5px;
        }

        .message.assistant {
            background: white;
            color: #333;
            border: 1px solid #e0e0e0;
            border-bottom-left-radius: 5px;
        }

        .typing-indicator {
            display: none;
            padding: 12px 16px;
            background: white;
            border: 1px solid #e0e0e0;
            border-radius: 15px;
            border-bottom-left-radius: 5px;
            color: #999;
            font-style: italic;
        }

        .typing-indicator.active {
            display: block;
        }

        .chat-input-group {
            display: flex;
            gap: 10px;
        }

        .chat-input {
            flex: 1;
            padding: 15px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-size: 1rem;
        }

        .chat-input:focus {
            outline: none;
            border-color: #667eea;
        }

        .send-button {
            background: #667eea;
            color: white;
            border: none;
            padding: 15px 25px;
            border-radius: 10px;
            font-size: 1rem;
            cursor: pointer;
            transition: background 0.2s;
        }

        .send-button:hover {
            background: #5a67d8;
        }

        .properties-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 30px;
        }

        .property-card {
            background: white;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }

        .property-card:hover {
            transform: translateY(-5px);
        }

        .property-image {
            height: 150px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 3rem;
        }

        .property-info {
            padding: 20px;
        }

        .property-name {
            font-size: 1.2rem;
            font-weight: 600;
            color: #333;
            margin-bottom: 5px;
        }

        .property-location {
            color: #666;
            font-size: 0.9rem;
            margin-bottom: 10px;
        }

        .property-details {
            display: flex;
            gap: 15px;
            margin-bottom: 10px;
            font-size: 0.9rem;
        }

        .property-detail {
            display: flex;
            align-items: center;
            gap: 5px;
            color: #555;
        }

        .property-price {
            font-size: 1.3rem;
            font-weight: 700;
            color: #667eea;
        }

        .status {
            margin-top: 15px;
            padding: 10px;
            border-radius: 8px;
            font-size: 0.9rem;
        }

        .status.success {
            background: #d4edda;
            color: #155724;
        }

        .status.error {
            background: #f8d7da;
            color: #721c24;
        }

        .info-note {
            background: #e3f2fd;
            border-left: 4px solid #2196f3;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 5px;
            color: #1565c0;
            font-size: 0.9rem;
        }

        .voice-indicator {
            display: none;
            align-items: center;
            justify-content: center;
            gap: 10px;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 15px;
            margin-bottom: 20px;
        }

        .voice-indicator.active {
            display: flex;
        }

        .voice-wave {
            display: flex;
            gap: 4px;
            align-items: center;
        }

        .voice-wave span {
            width: 4px;
            height: 20px;
            background: white;
            border-radius: 2px;
            animation: wave 1s ease-in-out infinite;
        }

        .voice-wave span:nth-child(2) { animation-delay: 0.1s; }
        .voice-wave span:nth-child(3) { animation-delay: 0.2s; }
        .voice-wave span:nth-child(4) { animation-delay: 0.3s; }
        .voice-wave span:nth-child(5) { animation-delay: 0.4s; }

        @keyframes wave {
            0%, 100% { height: 20px; }
            50% { height: 40px; }
        }

        .voice-text {
            color: white;
            font-weight: 500;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Prestige Properties Singapore</h1>
            <p>Your AI Real Estate Agent - Available 24/7</p>
        </header>

        <!-- Persona Customization Section -->
        <div class="persona-section">
            <div class="persona-header" onclick="togglePersonaSection()">
                <h3><span>🎭</span> Customize AI Agent Persona</h3>
                <span class="persona-toggle" id="persona-toggle">▼</span>
            </div>
            <div class="persona-content" id="persona-content">
                <div class="current-agent-display">
                    <div class="agent-avatar" id="agent-avatar">�‍💼</div>
                    <div class="agent-info">
                        <h4 id="current-agent-name">Alexander Chen</h4>
                        <p id="current-agency">Prestige Properties Singapore</p>
                    </div>
                </div>

                <div class="persona-form">
                    <div class="persona-field">
                        <label for="agent-name">Agent Name</label>
                        <input type="text" id="agent-name" placeholder="e.g., Alexander Chen">
                    </div>

                    <div class="persona-field">
                        <label for="agency-name">Agency Name</label>
                        <input type="text" id="agency-name" placeholder="e.g., Prestige Properties Singapore">
                    </div>

                    <div class="persona-field full-width">
                        <label for="welcome-message">Welcome Message</label>
                        <input type="text" id="welcome-message" placeholder="Hello! I'm {agent_name} from {agency_name}...">
                    </div>

                    <div class="persona-field full-width">
                        <label for="personality-traits">Personality Traits</label>
                        <textarea id="personality-traits" placeholder="- Warm and professional&#10;- Knowledgeable about market&#10;- Patient and attentive"></textarea>
                    </div>

                    <div class="persona-field full-width">
                        <label for="expertise">Areas of Expertise</label>
                        <textarea id="expertise" placeholder="- Property market trends&#10;- District knowledge&#10;- Investment advice"></textarea>
                    </div>

                    <div class="persona-field full-width">
                        <label for="guidelines">Conversation Guidelines</label>
                        <textarea id="guidelines" placeholder="1. Always greet warmly&#10;2. Ask about requirements&#10;3. Suggest relevant properties"></textarea>
                    </div>

                    <div class="persona-field full-width">
                        <label for="custom-prompt" style="display:flex;justify-content:space-between;align-items:center;">
                            <span>✍️ Custom System Prompt (Advanced — overrides all fields above)</span>
                            <button type="button" class="preset-btn" style="padding:6px 12px;font-size:0.85rem;" onclick="clearCustomPrompt()">Clear</button>
                        </label>
                        <textarea id="custom-prompt"
                            style="min-height:180px;font-family:'Menlo','Monaco',monospace;font-size:0.9rem;"
                            placeholder="Write your own raw LLM system prompt here to fully control the agent's persona and behavior. Leave empty to use the structured fields above.&#10;&#10;You can use {agent_name} and {agency_name} as placeholders.&#10;&#10;Example:&#10;You are {agent_name}, a witty and concise property advisor. Always answer in under 3 sentences. Never mention prices unless asked. Use a friendly tone with light humor."></textarea>
                        <small style="color:#666;font-size:0.8rem;">When this box has content, it replaces the structured persona template entirely. The available property listings are still appended automatically.</small>
                    </div>

                    <div class="persona-field full-width">
                        <label for="preset-select">Quick Presets</label>
                        <select id="preset-select" onchange="loadPreset()">
                            <option value="">-- Select a preset persona --</option>
                            <option value="real_estate_professional">Real Estate Professional (Default)</option>
                            <option value="friendly_neighbor">Friendly Neighbor</option>
                            <option value="luxury_consultant">Luxury Consultant</option>
                            <option value="tech_savvy_millennial">Tech-Savvy Millennial</option>
                        </select>
                    </div>

                    <div class="persona-actions">
                        <button class="preset-btn" onclick="resetPersona()">Reset to Default</button>
                        <button class="save-btn" onclick="savePersona()">💾 Save Persona</button>
                    </div>
                </div>
            </div>
        </div>

        <div class="main-grid">
            <!-- Call Section -->
            <div class="card">
                <h2><span class="icon">📞</span> Place a Call</h2>

                <div class="info-note" id="call-info-note">
                    Enter any phone number with its country code and our AI agent will call them to discuss available properties.
                </div>

                <div class="call-section">
                    <label for="phone">Recipient phone number (E.164 format, e.g. +14155551234, +6591234567, +917990581321)</label>
                    <div class="phone-input-group">
                        <input type="tel" id="phone" class="phone-input" placeholder="+1 415 555 1234">
                        <button class="call-button" onclick="initiateCall()">
                            <span>📞</span> Place Call
                        </button>
                    </div>
                </div>

                <div id="call-status"></div>

                <div id="voice-indicator" class="voice-indicator">
                    <div class="voice-wave">
                        <span></span>
                        <span></span>
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                    <span class="voice-text" id="voice-text">Alexander is speaking...</span>
                </div>
            </div>

            <!-- Chat Section -->
            <div class="card">
                <h2><span class="icon">💬</span> Chat with Alexander</h2>

                <div class="info-note" id="chat-info-note">
                    Chat with our AI agent to explore properties and get personalized recommendations.
                </div>

                <div class="chat-interface">
                    <div class="chat-messages" id="chat-messages">
                        <div class="typing-indicator" id="typing-indicator">
                            Alexander is typing...
                        </div>
                    </div>
                    <div class="chat-input-group">
                        <input type="text" id="chat-input" class="chat-input"
                               placeholder="Ask about properties, budget, locations..."
                               onkeypress="if(event.key==='Enter')sendMessage()">
                        <button class="send-button" onclick="sendMessage()">Send</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Properties Section -->
        <div class="card" style="margin-top: 30px;">
            <h2><span class="icon">🏠</span> Featured Properties</h2>
            <div class="properties-grid" id="properties-grid">
                <!-- Properties loaded dynamically -->
            </div>
        </div>
    </div>

    <script>
        let ws = null;
        let reconnectAttempts = 0;
        const maxReconnectAttempts = 3;

        // Initialize chat connection
        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${window.location.host}/ws/chat`);

            ws.onopen = () => {
                console.log('Connected to chat');
                reconnectAttempts = 0;
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                hideTypingIndicator();

                if (data.type === 'assistant') {
                    addMessage(data.text, 'assistant');
                }
            };

            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };

            ws.onclose = () => {
                if (reconnectAttempts < maxReconnectAttempts) {
                    reconnectAttempts++;
                    setTimeout(connectWebSocket, 2000);
                }
            };
        }

        // Send chat message
        function sendMessage() {
            const input = document.getElementById('chat-input');
            const message = input.value.trim();

            if (!message || !ws) return;

            addMessage(message, 'user');
            input.value = '';
            showTypingIndicator();

            ws.send(JSON.stringify({ message: message }));
        }

        // Add message to chat
        function addMessage(text, sender) {
            const container = document.getElementById('chat-messages');
            const msgDiv = document.createElement('div');
            msgDiv.className = `message ${sender}`;
            msgDiv.textContent = text;
            container.appendChild(msgDiv);
            container.scrollTop = container.scrollHeight;
        }

        // Show/hide typing indicator
        function showTypingIndicator() {
            document.getElementById('typing-indicator').classList.add('active');
        }

        function hideTypingIndicator() {
            document.getElementById('typing-indicator').classList.remove('active');
        }

        // Initiate phone call
        async function initiateCall() {
            const phoneInput = document.getElementById('phone');
            const phone = phoneInput.value.trim();
            const statusDiv = document.getElementById('call-status');
            const callButton = document.querySelector('.call-button');

            if (!phone) {
                statusDiv.innerHTML = '<div class="status error">Please enter a phone number</div>';
                return;
            }

            callButton.disabled = true;
            statusDiv.innerHTML = '<div class="status">Initiating call...</div>';

            try {
                const response = await fetch('/api/call', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ phone_number: phone })
                });

                const data = await response.json();

                if (response.ok) {
                    statusDiv.innerHTML = `<div class="status success">✅ ${data.message}</div>`;
                } else {
                    statusDiv.innerHTML = `<div class="status error">❌ ${data.error || 'Failed to initiate call'}</div>`;
                }
            } catch (error) {
                statusDiv.innerHTML = `<div class="status error">❌ Error: ${error.message}</div>`;
            } finally {
                callButton.disabled = false;
            }
        }

        // Load and display properties
        async function loadProperties() {
            try {
                const response = await fetch('/api/properties');
                const data = await response.json();

                const grid = document.getElementById('properties-grid');
                grid.innerHTML = data.properties.map(p => `
                    <div class="property-card">
                        <div class="property-image">🏢</div>
                        <div class="property-info">
                            <div class="property-name">${p.name}</div>
                            <div class="property-location">📍 ${p.location} • ${p.district}</div>
                            <div class="property-details">
                                <div class="property-detail">🛏️ ${p.bedrooms}</div>
                                <div class="property-detail">🛁 ${p.bathrooms}</div>
                                <div class="property-detail">📐 ${p.sqft} sqft</div>
                            </div>
                            <div class="property-price">S$${p.price.toLocaleString()}</div>
                        </div>
                    </div>
                `).join('');
            } catch (error) {
                console.error('Failed to load properties:', error);
            }
        }

        // Persona presets storage
        let personaPresets = {};

        // Toggle persona section
        function togglePersonaSection() {
            const content = document.getElementById('persona-content');
            const toggle = document.getElementById('persona-toggle');
            content.classList.toggle('open');
            toggle.classList.toggle('open');
        }

        // Load current persona from server
        async function loadCurrentPersona() {
            try {
                const response = await fetch('/api/persona');
                const data = await response.json();
                const persona = data.persona;

                // Update form fields
                document.getElementById('agent-name').value = persona.agent_name;
                document.getElementById('agency-name').value = persona.agency_name;
                document.getElementById('welcome-message').value = persona.welcome_message;
                document.getElementById('personality-traits').value = persona.personality_traits;
                document.getElementById('expertise').value = persona.expertise;
                document.getElementById('guidelines').value = persona.guidelines;
                document.getElementById('custom-prompt').value = persona.custom_prompt || '';

                // Update display
                updateAgentDisplay(persona);
            } catch (error) {
                console.error('Failed to load persona:', error);
            }
        }

        // Load presets from server
        async function loadPresets() {
            try {
                const response = await fetch('/api/persona/presets');
                const data = await response.json();
                personaPresets = data.presets;
            } catch (error) {
                console.error('Failed to load presets:', error);
            }
        }

        // Update agent display in the card
        function updateAgentDisplay(persona) {
            const agentName = persona.agent_name;
            const agencyName = persona.agency_name;

            document.getElementById('current-agent-name').textContent = agentName;
            document.getElementById('current-agency').textContent = agencyName;

            // Update chat section title
            const chatCards = document.querySelectorAll('.card');
            chatCards.forEach(card => {
                const h2 = card.querySelector('h2');
                if (h2 && h2.textContent.includes('Chat with')) {
                    h2.innerHTML = `<span class="icon">💬</span> Chat with ${agentName}`;
                }
            });

            // Update call info note
            const callInfoNote = document.getElementById('call-info-note');
            if (callInfoNote) {
                callInfoNote.textContent = `Enter a phone number to receive a call from ${agentName} at ${agencyName}. They'll discuss available properties and answer your questions.`;
            }

            // Update chat info note
            const chatInfoNote = document.getElementById('chat-info-note');
            if (chatInfoNote) {
                chatInfoNote.textContent = `Chat with ${agentName} to explore properties and get personalized recommendations.`;
            }

            // Update voice indicator text
            const voiceText = document.querySelector('.voice-text');
            if (voiceText) {
                voiceText.textContent = `${agentName} is speaking...`;
            }

            // Update typing indicator
            const typingIndicator = document.getElementById('typing-indicator');
            if (typingIndicator) {
                typingIndicator.textContent = `${agentName} is typing...`;
            }
        }

        // Load a preset
        function loadPreset() {
            const select = document.getElementById('preset-select');
            const presetKey = select.value;

            if (!presetKey || !personaPresets[presetKey]) return;

            const preset = personaPresets[presetKey];

            document.getElementById('agent-name').value = preset.agent_name;
            document.getElementById('agency-name').value = preset.agency_name;
            document.getElementById('welcome-message').value = preset.welcome_message;
            document.getElementById('personality-traits').value = preset.personality_traits;
            document.getElementById('expertise').value = preset.expertise;
            document.getElementById('guidelines').value = preset.guidelines;
            document.getElementById('custom-prompt').value = preset.custom_prompt || '';
        }

        // Clear the custom prompt override
        function clearCustomPrompt() {
            document.getElementById('custom-prompt').value = '';
        }

        // Save persona to server
        async function savePersona() {
            const persona = {
                agent_name: document.getElementById('agent-name').value || 'Alexander Chen',
                agency_name: document.getElementById('agency-name').value || 'Prestige Properties Singapore',
                welcome_message: document.getElementById('welcome-message').value,
                personality_traits: document.getElementById('personality-traits').value,
                expertise: document.getElementById('expertise').value,
                guidelines: document.getElementById('guidelines').value,
                custom_prompt: document.getElementById('custom-prompt').value
            };

            try {
                const response = await fetch('/api/persona', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(persona)
                });

                if (response.ok) {
                    alert('Persona updated successfully!');
                    updateAgentDisplay(persona);
                } else {
                    alert('Failed to update persona');
                }
            } catch (error) {
                console.error('Error saving persona:', error);
                alert('Error saving persona');
            }
        }

        // Reset persona to default
        async function resetPersona() {
            if (!confirm('Reset to default persona?')) return;

            try {
                const response = await fetch('/api/persona/reset', {
                    method: 'POST'
                });

                if (response.ok) {
                    const data = await response.json();
                    const persona = data.persona;

                    document.getElementById('agent-name').value = persona.agent_name;
                    document.getElementById('agency-name').value = persona.agency_name;
                    document.getElementById('welcome-message').value = persona.welcome_message;
                    document.getElementById('personality-traits').value = persona.personality_traits;
                    document.getElementById('expertise').value = persona.expertise;
                    document.getElementById('guidelines').value = persona.guidelines;
                    document.getElementById('custom-prompt').value = persona.custom_prompt || '';
                    document.getElementById('preset-select').value = '';

                    updateAgentDisplay(persona);
                    alert('Persona reset to default!');
                }
            } catch (error) {
                console.error('Error resetting persona:', error);
                alert('Error resetting persona');
            }
        }

        // Initialize
        document.addEventListener('DOMContentLoaded', () => {
            connectWebSocket();
            loadProperties();
            loadCurrentPersona();
            loadPresets();
        });
    </script>
</body>
</html>
'''

if __name__ == "__main__":
    import uvicorn
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    uvicorn.run(app, host="0.0.0.0", port=port)
