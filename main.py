import sys, os, re, uuid, json, datetime, smtplib, base64, threading, webbrowser
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from openai import OpenAI
except ImportError:
    print("\n[ERROR] Run: pip install openai\n"); sys.exit(1)

# ══════════════════════════════════════════════════════════════
#   CONFIG  ← Fill these in. No .env file needed.
# ══════════════════════════════════════════════════════════════
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_MODEL = "meta/llama-3.3-70b-instruct"
FALLBACK_MODELS = [
    "meta/llama-3.1-70b-instruct",
    "meta/llama-3.1-8b-instruct",    # last resort
]

# SMTP_HOST      = "smtp.gmail.com"
# SMTP_PORT      = 587
# SMTP_USERNAME  = os.environ.get("SMTP_USERNAME", "chavdajay510@gmail.com")
# SMTP_PASSWORD  = os.environ.get("SMTP_PASSWORD", "sbkbiounwrpoaphd")
# FROM_EMAIL     = os.environ.get("FROM_EMAIL", "chavdajay510@gmail.com")
# #ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "info@saubhagyam.com")
# ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "chavdajay510@gmail.com")
# WHATSAPP_NO    = "+919998978397"
# SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "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")
SMTP_HOST        = "smtp.gmail.com"
SMTP_PORT        = 587
SMTP_USERNAME    = os.environ.get("SMTP_USERNAME", "chavdajay510@gmail.com")
SMTP_PASSWORD    = os.environ.get("SMTP_PASSWORD", "")
FROM_EMAIL       = os.environ.get("FROM_EMAIL", "chavdajay510@gmail.com")
ADMIN_EMAIL      = os.environ.get("ADMIN_EMAIL", "chavdajay510@gmail.com")
WHATSAPP_NO      = "+919998978397"
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")
# ══════════════════════════════════════════════════════════════
#   SYSTEM PROMPT
# ══════════════════════════════════════════════════════════════
BASE_SYSTEM_PROMPT = """
You are "Saubhagyam AI," the official digital ambassador for SAUBHAGYAM Web Pvt. Ltd.
Be polite, friendly, and professional like a real human support agent.

═══════════════════════════════════════════════════════
LANGUAGE RULES — CRITICAL, FOLLOW EXACTLY
═══════════════════════════════════════════════════════

DEFAULT LANGUAGE: ENGLISH. If you are unsure about the user's language, ALWAYS reply in English.

STEP 1 — Detect the language of the user's CURRENT message ONLY:

GUJARATI — ONLY if the message contains Gujarati-specific words like:
kem cho, su che, majama, kevu, saru, chhe, tamne, mane, aapne, janvu, karvu,
mangta, puchhvu, kahevu, pan, tame, amne, mare, karo, karo cho, joi, joiye,
hoy, hatu, thay, thase, badhu, bov, shu, ahi, tya, chhiye, banavvu, joi rahu

HINDI — ONLY if the message contains Hindi-specific words like:
namaste, kaise, kya, hai, hain, karo, karna, chahte, baare, mein, humein,
aapka, aapko, bataiye, dijiye, haan, nahi, bhai, yaar, achha, theek, zaroorat,
chahiye, kaisa, kaise ho, batao, samajh, ho, hum, aap, kar, kijiye, sakte

ENGLISH — If the message is in English or uses common greetings like "hi", "hello", "hey", "thanks", etc.

STEP 2 — Reply in ONLY that ONE language. NO mixing allowed:

If ENGLISH: Write your ENTIRE reply in pure English only.
  FORBIDDEN in English replies: Any Hindi or Gujarati words.

If GUJARATI: Write your ENTIRE reply in transliterated Gujarati (Gujarati words written in English script).
  FORBIDDEN in Gujarati replies: Hindi words such as hai, kya, mein, kar, karo, karna, hum, chahte, chahiye, baare, zaroorat, aapko, batao, dijiye, sakte.
  Use Gujarati equivalents: "chhe" (not "hai"), "shu" (not "kya"), "ma" (not "mein"), "karo" in Gujarati context, "ame" (not "hum"), "joiye chhe" (not "chahiye").

If HINDI: Write your ENTIRE reply in Hinglish (Hindi words in English script).
  FORBIDDEN in Hindi replies: Gujarati words such as chhe, cho, che, tamne, mane, janvu, karvu, mangta, joiye, thase, chhiye, banavvu.
  Use Hindi equivalents: "hai" (not "chhe"), "kya" (not "shu"), "mein" (not "ma"), "chahiye" (not "joiye chhe").

STEP 3 — SELF-CHECK before sending:
Read your reply word by word. If ANY word belongs to a different language than the detected one (except technical terms like AI, Blockchain, API, React, Node.js, Flutter, etc.), DELETE that word and replace it with the correct word in the detected language. If you cannot translate it, remove the sentence entirely.

EXAMPLES OF CORRECT REPLIES:
User: "kem cho" → "Kem cho! Hu majama chu. Tamne SAUBHAGYAM ni koi service vishe janvu che?"
User: "Tell me about your AI services" → "Hello! We offer a wide range of AI services including AI Development, Chatbot Development, and Machine Learning solutions. What specific area are you interested in?"
User: "namaste kya haal hai" → "Namaste! Main theek hoon. Aap SAUBHAGYAM ki kis service ke baare mein jaanna chahte hain?"
User: "I want to make mobile application" → "Hello! You want to make a mobile application, is that right? We can help you with that. We offer iOS, Android, React Native, Flutter, and Kotlin development. Which platform are you interested in?"

EXAMPLES OF WRONG REPLIES (NEVER DO THIS):
WRONG: "Kem cho! Hu majama chu. Tamne SAUBHAGYAM ni koi AI vishe janvu che? Hum AI development, AI chatbot development karte hain." (Mixed Gujarati + Hindi)
WRONG: "Namaste! Aapko e-commerce website banane ke liye kya zaroorat hai? Hum aapko Magento, Shopify, WooCommerce..." followed by English sentences. (Mixed Hindi + English)
WRONG: "Hello! You want to make a mobile application, is that right? Hum aapki madad kar sakte hain." (Mixed English + Hindi)

Keep technical/brand names (AI, Blockchain, API, Web Development, React, Flutter, etc.) in English in ALL languages.

RESPONSE STYLE:
- Reply naturally and conversationally, like a helpful human, NOT like a brochure.
- Keep replies SHORT (2-5 sentences) unless user explicitly asks for full details, a list, or "tell me more".
- Do NOT dump the entire service list unless the user asks "what services do you offer" or similar broad questions.
- If user asks something specific (e.g. "I want to make a mobile app"), give a brief, relevant, friendly response and ask a follow-up question to understand their needs better — don't list every sub-service.
- Use bullet points and bold headings ONLY when listing multiple items the user specifically asked for.
- Match the tone of the user's message — casual question gets casual short answer, detailed request gets detailed answer.

COMPANY:
Name  : SAUBHAGYAM Web Pvt. Ltd.
About : Global AI and software development company delivering enterprise apps,
        mobile, cloud platforms, and digital transformation solutions.
Stats : 320+ Clients | 750+ Projects | 21+ Industries | 37+ Countries
Support: 60-day FREE post-delivery support

India HQ: 503-504 Nobles Trade Center, Bhuyangdev Cross Road, Ahmedabad 380052
USA     : 181 W Weddell Dr, Sunnyvale, CA 94089
Phone   : +91 99989 78397 (Inquiry) | +91 78018 38391 (Career)
Email   : info@saubhagyam.com | Skype: saubhagyam | WhatsApp: +91 99989 78397

ARTIFICIAL INTELLIGENCE SERVICES:
AI Development, AI Agent Development, AI Chatbot Development, AI Co-pilot Dev,
Adaptive AI, Agentive AI, AI Assistant Development, NLP Development,
LLM Development, Machine Learning, Computer Vision, Generative AI Development,
Generative AI Consulting, AI Token Development, Hire AI Engineers,
Hire Gen-AI Developers

BLOCKCHAIN SERVICES:
Blockchain Development, Smart Contract Development, Solana Blockchain,
TON Blockchain, Custom Blockchain, White Label Blockchain, Enterprise Blockchain,
Blockchain Audit, Smart Contract Audit

CRYPTOCURRENCY SERVICES:
Cryptocurrency Development, Token Development (ERC-20/BEP-20/SPL),
P2P Exchange Development, Crypto Wallet Development,
Crypto Payment Development, AI Token Development

CYBERSECURITY SERVICES:
Cyber Security Solutions, Enterprise Security, Digital Forensics,
Zero Trust (ZTNA), Data Protection (GDPR/HIPAA), Cloud Security,
Application Security, Penetration Testing

ALGO TRADING:
Algo Trading Development, Forex Algo Development,
Algorithm Testing, Fintech Developers

MOBILE APP DEVELOPMENT:
iOS App Development, Android App Development, React Native,
Flutter, Kotlin Development, Mobile App Design

WEB DEVELOPMENT:
Laravel, Django, Flask, CodeIgniter, WordPress, Joomla, Drupal,
Magento, Shopify, WooCommerce, React, Angular, Vue.js, Node.js, Express.js,
UI/UX Design, Figma, Responsive Design

API INTEGRATION:
Payment (Stripe, PayPal, Razorpay), Auth (OAuth, JWT, SSO),
Shipping (FedEx, UPS, DHL), Social (Facebook, LinkedIn, Instagram),
SMS (Twilio, MSG91), Phone Verification OTP

CLOUD & DEVOPS: AWS, GCP, Azure, Docker, Jenkins, Terraform, Kubernetes

HIRE DEDICATED DEVELOPERS:
Full Stack, React, Angular, Node.js, Laravel, PHP, WordPress, Shopify,
Magento, iOS, Android, Flutter, AI/ML Engineer, Gen AI Developer,
AI Agent Developer, QA, DevOps, Blockchain Developers.
Features: No extra Project Lead charge | 175+ hrs/month | Daily Scrum | Senior only

IMAGE ANALYSIS:
If user sends an image, analyze it helpfully. If it is a website or app screenshot,
describe what you see and suggest how SAUBHAGYAM can help build or improve it.

LIVE AGENT HANDOFF:
If user asks to talk to a human or connect to support, reply:
"I understand! Let me connect you with one of our experts. Please click the
'Talk to Human' button, share your contact details, and our team will reach
out within 15 minutes via WhatsApp or Email."
Then append EXACTLY: [HANDOFF_REQUESTED]

APPOINTMENT BOOKING:
Available: Monday to Friday only
Slots    : 11:00 AM to 1:00 PM  OR  3:00 PM to 6:00 PM

BOOKING STEPS:
Step 1: Greet and offer to help book an appointment.
Step 2: Ask for full name.
Step 3: Ask for email and phone number.
Step 4: Ask which service they are interested in.
Step 5: Ask for preferred date and time. Validate:
  - Monday to Friday only, no weekends
  - Only 11AM-1PM or 3PM-6PM, no other times
  - No past dates
Step 6: Show summary and ask if correct:
  Name: [Name]
  Email: [Email]
  Phone: [Phone]
  Service: [Service]
  Date: [Date]
  Time: [Time]
Step 7: On Yes confirmation reply with thank you message ending with [SUBMIT_BOOKING]
CRITICAL: Always include [SUBMIT_BOOKING] at the very end of Step 7.

MANAGE EXISTING BOOKING:
If user wants to cancel or reschedule:
1. Ask for their booking email.
2. Output EXACTLY this and nothing more: [LOOKUP_BOOKING] Email: {their_email}
3. Present bookings clearly after system provides them.
4. Cancel   -> append at end: [CANCEL_BOOKING] ID: {booking_id}
5. Reschedule -> validate slot -> append:
   [RESCHEDULE_BOOKING] ID: {booking_id} Date: {new_date} Time: {new_time}

RULES:
- Language matching always
- Bold with **text**, bullets with bullet symbol
- Links as [text](url)
- Never confirm appointment directly, always say pending admin review
"""


# ══════════════════════════════════════════════════════════════
#   EMAIL HELPER
# ══════════════════════════════════════════════════════════════
def send_email(to_email: str, subject: str, body: str, is_html: bool = False):
    """Send email via Gmail SMTP (primary) or SendGrid API (if key is set)."""
    if not to_email or "@" not in to_email:
        print(f"[EMAIL SKIP] Invalid recipient: {to_email}")
        return

    # ── Use SendGrid if API key is available ──
    if SENDGRID_API_KEY:
        try:
            import urllib.request, urllib.error, ssl
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            data = json.dumps({
                "personalizations": [{"to": [{"email": to_email}]}],
                "from": {"email": FROM_EMAIL, "name": "Saubhagyam AI"},
                "subject": subject,
                "content": [{"type": "text/plain", "value": body}]
            }).encode("utf-8")
            req = urllib.request.Request(
                "https://api.sendgrid.com/v3/mail/send",
                data=data,
                headers={
                    "Authorization": f"Bearer {SENDGRID_API_KEY}",
                    "Content-Type": "application/json"
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=30, context=ctx) as response:
                print(f"[EMAIL OK SendGrid] {to_email} — Status: {response.status}")
                return
        except Exception as e:
            print(f"[SendGrid FAIL] {e} — Falling back to SMTP...")

    # ── Gmail SMTP (primary / fallback) ──
    try:
        msg = MIMEMultipart()
        msg["From"]    = f"Saubhagyam AI <{SMTP_USERNAME}>"
        msg["To"]      = to_email
        msg["Subject"] = subject
        content_type = "html" if is_html else "plain"
        msg.attach(MIMEText(body, content_type))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(SMTP_USERNAME, to_email, msg.as_string())
        print(f"[EMAIL OK SMTP] {to_email}")
    except Exception as e:
        print(f"[EMAIL FAIL SMTP] {e}")
# ══════════════════════════════════════════════════════════════
#   SAFETY SCANNER
# ══════════════════════════════════════════════════════════════
SAFETY_REFUSAL = ("I specialise in SAUBHAGYAM services. "
                  "I cannot assist with that request.\n"
                  "Contact: info@saubhagyam.com | +91 99989 78397")

_DANGER = re.compile(
    r"how to hack|crack password|sql injection|phishing tutorial|create.*malware|"
    r"write.*virus|ransomware|ddos attack|exploit vulnerability|bypass.*security|"
    r"keylogger|trojan|spyware|rootkit|reverse shell|botnet|"
    r"how to kill|make.*bomb|build.*weapon|how to.*suicide|self.?harm|"
    r"launder money|drug trafficking|human trafficking|child.*exploit|"
    r"create.*scam|ponzi.*scheme|identity.*theft|jailbreak|DAN mode|"
    r"ignore.*instructions|ignore.*system|forget.*rules|bypass.*guardrail|"
    r"reveal.*system.*prompt|generate.*porn|sexual.*explicit",
    re.IGNORECASE
)

def is_unsafe(text: str) -> bool:
    return bool(_DANGER.search(text))


# ══════════════════════════════════════════════════════════════
#   LANGUAGE DETECTION (Server-side, deterministic)
# ══════════════════════════════════════════════════════════════
_GUJARATI_WORDS = {
    "kem", "cho", "che", "chhe", "su", "shu", "majama", "kevu", "saru",
    "tamne", "mane", "aapne", "janvu", "karvu", "mangta", "puchhvu",
    "kahevu", "pan", "tame", "amne", "mare", "joi", "joiye", "hoy",
    "hatu", "thay", "thase", "badhu", "bov", "ahi", "tya", "chhiye",
    "banavvu", "nathi", "karo", "karso", "batavo", "kevi", "rite",
    "mate", "vishe", "ketlu", "kem cho", "maja ma", "tamaru", "amaru",
}

_HINDI_WORDS = {
    "namaste", "kaise", "kya", "hai", "hain", "karo", "karna", "chahte",
    "baare", "mein", "humein", "aapka", "aapko", "bataiye", "dijiye",
    "haan", "nahi", "bhai", "yaar", "achha", "theek", "zaroorat",
    "chahiye", "kaisa", "batao", "samajh", "hum", "aap", "kar",
    "kijiye", "sakte", "mujhe", "kuch", "bahut", "accha", "bolo",
    "suniye", "dekhiye", "karenge", "karein", "chaiye", "dost",
    "jaldi", "abhi", "yahan", "wahan", "kyun", "kaise ho",
}

def detect_language(text: str) -> str:
    """Detect language from user input using keyword matching."""
    words = set(re.findall(r'[a-zA-Z]+', text.lower()))
    
    guj_score = len(words & _GUJARATI_WORDS)
    hin_score = len(words & _HINDI_WORDS)
    
    # Check for multi-word Gujarati phrases
    text_lower = text.lower()
    if "kem cho" in text_lower or "maja ma" in text_lower:
        guj_score += 3
    if "kaise ho" in text_lower or "kya hai" in text_lower:
        hin_score += 3
    
    if guj_score > hin_score and guj_score >= 1:
        return "GUJARATI"
    elif hin_score > guj_score and hin_score >= 1:
        return "HINDI"
    else:
        return "ENGLISH"

_LANG_INSTRUCTIONS = {
    "ENGLISH": (
        "[LANGUAGE INSTRUCTION: The user is writing in ENGLISH. "
        "You MUST reply ONLY in English. Do NOT use any Hindi or Gujarati words. "
        "Do NOT add translations in brackets. Write a clean English-only response.]\n\n"
    ),
    "GUJARATI": (
        "[LANGUAGE INSTRUCTION: The user is writing in GUJARATI. "
        "You MUST reply ONLY in transliterated Gujarati (Gujarati words in English letters). "
        "Do NOT use Hindi words like hai, kya, mein, hum, chahiye, zaroorat, aapko. "
        "Do NOT add English translations in brackets. "
        "Use words like chhe, shu, tamne, ame, joiye chhe, karvu.]\n\n"
    ),
    "HINDI": (
        "[LANGUAGE INSTRUCTION: The user is writing in HINDI. "
        "You MUST reply ONLY in Hinglish (Hindi words in English letters). "
        "Do NOT use Gujarati words like chhe, cho, tamne, janvu, thase, joiye. "
        "Do NOT add English translations in brackets. "
        "Use words like hai, kya, mein, hum, chahiye, aapko.]\n\n"
    ),
}

# Pattern to strip bracket translations like "(Hello! How are you?)"
_BRACKET_TRANSLATION = re.compile(r'\s*\([A-Z][^)]{10,}\)')


# ══════════════════════════════════════════════════════════════
#   CHATBOT CLASS
# ══════════════════════════════════════════════════════════════
class SaubhagyamChatbot:
    def __init__(self, api_key: str, model: str):
        self.client = OpenAI(base_url=NVIDIA_BASE_URL, api_key=api_key)
        self.model  = model
        today = datetime.datetime.now().strftime("%A, %d %B %Y (%d/%m/%Y)")
        prompt = BASE_SYSTEM_PROMPT.replace(
            "Available: Monday to Friday only",
            f"Today's Date (for validation): {today}\nAvailable: Monday to Friday only"
        )
        self.history: list[dict] = [{"role": "system", "content": prompt}]

    def ask(self, user_input: str, image_b64: str = None) -> str:
        if is_unsafe(user_input):
            return SAFETY_REFUSAL

        # Detect language and prepend instruction
        lang = detect_language(user_input)
        lang_prefix = _LANG_INSTRUCTIONS[lang]

        if image_b64:
            content = [
                {"type": "text", "text": lang_prefix + user_input},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
            ]
        else:
            content = lang_prefix + user_input

        self.history.append({"role": "user", "content": content})

        # Try primary model, then fallback models if it fails
        models_to_try = [self.model] + FALLBACK_MODELS
        reply = None
        last_error = None

        for model_name in models_to_try:
            try:
                res = self.client.chat.completions.create(
                    model=model_name, messages=self.history,
                    temperature=0.3, max_tokens=1024
                )
                reply = res.choices[0].message.content
                if model_name != self.model:
                    print(f"[FALLBACK] Primary model failed, used: {model_name}")
                break
            except Exception as ex:
                last_error = ex
                print(f"[MODEL FAIL] {model_name}: {ex}")
                continue

        if reply is None:
            self.history.pop()
            return f"[AI Error: {last_error}]"

        # Post-process: strip bracket translations like "(Hello! How are you?)"
        reply = _BRACKET_TRANSLATION.sub('', reply)
        reply = reply.strip()

        self.history.append({"role": "assistant", "content": reply})
        return reply

    def ask_stream(self, user_input: str, image_b64: str = None):
        """Generator that yields tokens as they stream from the model."""
        if is_unsafe(user_input):
            yield SAFETY_REFUSAL
            return

        # Detect language and prepend instruction
        lang = detect_language(user_input)
        lang_prefix = _LANG_INSTRUCTIONS[lang]

        if image_b64:
            content = [
                {"type": "text", "text": lang_prefix + user_input},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
            ]
        else:
            content = lang_prefix + user_input

        self.history.append({"role": "user", "content": content})

        models_to_try = [self.model] + FALLBACK_MODELS
        full_reply = ""
        success = False

        for model_name in models_to_try:
            try:
                stream = self.client.chat.completions.create(
                    model=model_name, messages=self.history,
                    temperature=0.3, max_tokens=1024,
                    stream=True
                )
                if model_name != self.model:
                    print(f"[FALLBACK STREAM] Primary model failed, used: {model_name}")
                for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        token = chunk.choices[0].delta.content
                        full_reply += token
                        yield token
                success = True
                break
            except Exception as ex:
                print(f"[MODEL FAIL STREAM] {model_name}: {ex}")
                continue

        if not success:
            self.history.pop()
            yield "[AI Error: All models failed]"
            return

        # Post-process and save to history
        full_reply = _BRACKET_TRANSLATION.sub('', full_reply).strip()
        self.history.append({"role": "assistant", "content": full_reply})

    def inject(self, msg: str) -> str:
        self.history.append({"role": "user", "content": f"[SYSTEM]: {msg}"})
        try:
            res = self.client.chat.completions.create(
                model=self.model, messages=self.history,
                temperature=0.3, max_tokens=512
            )
            reply = res.choices[0].message.content
        except Exception as ex:
            self.history.pop()
            return f"[Error: {ex}]"
        self.history.append({"role": "assistant", "content": reply})
        return reply


# ══════════════════════════════════════════════════════════════
#   DATA MODELS
# ══════════════════════════════════════════════════════════════
class Booking(BaseModel):
    id              : str = Field(default_factory=lambda: str(uuid.uuid4()))
    name            : str
    email           : str
    phone           : str
    date            : str
    time            : str
    service_interest: str = "General Inquiry"
    status          : str = "Pending"
    submitted_at    : str = Field(default_factory=lambda: datetime.datetime.now().isoformat())
    admin_reason    : Optional[str] = None
    suggested_date  : Optional[str] = None
    suggested_time  : Optional[str] = None

class AdminActionRequest(BaseModel):
    booking_id : str
    action     : str
    reason     : Optional[str] = None
    new_date   : Optional[str] = None
    new_time   : Optional[str] = None

class HandoffRequest(BaseModel):
    name    : str
    contact : str
    message : Optional[str] = "User requested live agent"

class CancelReq(BaseModel):
    booking_id: str

class RescheduleReq(BaseModel):
    booking_id: str
    new_date  : str
    new_time  : str


# ══════════════════════════════════════════════════════════════
#   BOOKING STORE
# ══════════════════════════════════════════════════════════════
class BookingStore:
    def __init__(self, path="bookings.json"):
        self.path = path
        self.bookings: list[Booking] = []
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path) as f:
                    self.bookings = [Booking(**b) for b in json.load(f)]
            except Exception:
                self.bookings = []

    def save(self):
        with open(self.path, "w") as f:
            json.dump([b.model_dump() for b in self.bookings], f, indent=2)

    def add(self, b: Booking):
        self._load(); self.bookings.append(b); self.save()

    def get_all(self):
        self._load(); return self.bookings

    def get_by_id(self, bid: str) -> Optional[Booking]:
        self._load()
        for b in self.bookings:
            if b.id == bid: return b
        return None


# ══════════════════════════════════════════════════════════════
#   FASTAPI APP FACTORY
# ══════════════════════════════════════════════════════════════
def create_app(api_key: str, model: str) -> FastAPI:
    app     = FastAPI(title="Saubhagyam ChatBot v2")
    chatbot = SaubhagyamChatbot(api_key=api_key, model=model)
    store   = BookingStore()

    app.add_middleware(CORSMiddleware,
        allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    @app.get("/")
    async def index():
        return FileResponse("ui-chatbot/index.html")

    @app.get("/admin")
    async def admin():
        return FileResponse("ui-chatbot/admin.html")

    # ── STREAMING CHAT ENDPOINT (SSE) ────────────────────────
    @app.post("/chat/stream")
    async def chat_stream(message: str = Form(...), image: UploadFile = File(None)):
        image_b64 = None
        if image and image.filename:
            raw = await image.read()
            image_b64 = base64.b64encode(raw).decode("utf-8")

        def generate():
            for token in chatbot.ask_stream(message, image_b64):
                # SSE format: data: <token>\n\n
                yield f"data: {json.dumps({'token': token})}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(generate(), media_type="text/event-stream")

    # ── MAIN CHAT ENDPOINT (non-streaming, for bookings etc.) ─
    @app.post("/chat")
    async def chat(message: str = Form(...), image: UploadFile = File(None)):
        image_b64 = None
        if image and image.filename:
            raw = await image.read()
            image_b64 = base64.b64encode(raw).decode("utf-8")

        reply = chatbot.ask(message, image_b64)

        # Handle [LOOKUP_BOOKING]
        if "[LOOKUP_BOOKING]" in reply:
            try:
                m = re.search(
                    r"\[LOOKUP_BOOKING\]\s*Email:\s*([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})",
                    reply, re.IGNORECASE)
                if m:
                    email  = m.group(1).strip()
                    active = [b for b in store.get_all()
                              if b.email.lower() == email.lower()
                              and b.status in ("Pending", "Confirmed", "Rescheduled")]
                    if not active:
                        msg = f"No active bookings for {email}. Tell user politely."
                        nr  = chatbot.inject(msg)
                        reply = re.sub(r"\[LOOKUP_BOOKING\].*", "", reply).strip() + "\n\n" + nr
                    else:
                        data = [{"id": b.id, "date": b.date, "time": b.time, "status": b.status}
                                for b in active]
                        return {"action": "MANAGE_BOOKINGS", "bookings": data}
            except Exception as e:
                print(f"[LOOKUP ERR] {e}")

        # Handle [CANCEL_BOOKING]
        if "[CANCEL_BOOKING]" in reply:
            try:
                m = re.search(r"\[CANCEL_BOOKING\]\s*ID:\s*([^\s\]]+)", reply, re.IGNORECASE)
                if m:
                    b = store.get_by_id(m.group(1).strip())
                    if b:
                        b.status = "Cancelled"; store.save()
                        send_email(b.email, "Appointment Cancelled – SAUBHAGYAM",
                            f"Dear {b.name},\nYour appointment on {b.date} at {b.time} "
                            f"has been cancelled.\nTeam SAUBHAGYAM")
                reply = re.sub(r"\[CANCEL_BOOKING\].*", "", reply).strip()
            except Exception as e:
                print(f"[CANCEL ERR] {e}")

        # Handle [RESCHEDULE_BOOKING]
        if "[RESCHEDULE_BOOKING]" in reply:
            try:
                m = re.search(
                    r"\[RESCHEDULE_BOOKING\]\s*ID:\s*(\S+)\s*Date:\s*(\S+)\s*Time:\s*(.+?)(?=\n|$)",
                    reply, re.IGNORECASE)
                if m:
                    b = store.get_by_id(m.group(1).strip())
                    if b:
                        b.date = m.group(2).strip()
                        b.time = m.group(3).strip()
                        b.status = "Pending"; store.save()
                        send_email(b.email, "Reschedule Request – SAUBHAGYAM",
                            f"Dear {b.name},\nReschedule to {b.date} at {b.time} "
                            f"is under review.\nTeam SAUBHAGYAM")
                reply = re.sub(r"\[RESCHEDULE_BOOKING\].*", "", reply).strip()
            except Exception as e:
                print(f"[RESCHEDULE ERR] {e}")

        # Handle [SUBMIT_BOOKING]
        if "[SUBMIT_BOOKING]" in reply:
            try:
                def extract(pattern, text, fallback="N/A"):
                    m = re.search(pattern, text, re.IGNORECASE)
                    return m.group(1).strip().replace("*","").replace("\u2022","") if m else fallback

                name    = extract(r"Name\s*:\s*\**(.+?)\**(?=\n|Email|Phone|$)", reply)
                email_r = extract(r"Email\s*:\s*\[?(.+?)\]?(?:\(mailto:[^\)]+\))?(?=\n|Phone|Date|$)", reply)
                email_r = re.sub(r"[\[\]<>*]", "", email_r).split()[0]
                phone   = extract(r"Phone\s*:\s*\**(.+?)\**(?=\n|Date|Service|$)", reply).split()[0]
                service = extract(r"Service\s*:\s*\**(.+?)\**(?=\n|Date|Time|$)", reply, "General Inquiry")
                date    = extract(r"Date\s*:\s*\**(.+?)\**(?=\n|Time|$)", reply).split()[0]
                time_v  = extract(r"Time\s*:\s*\**(.+?)(?=\n|Thank|\[SUBMIT|$)", reply)

                booking = Booking(name=name, email=email_r, phone=phone,
                                  date=date, time=time_v, service_interest=service)
                store.add(booking)

                send_email(ADMIN_EMAIL, f"New Booking from {name}",
                    f"Name: {name}\nEmail: {email_r}\nPhone: {phone}\n"
                    f"Service: {service}\nDate: {date}\nTime: {time_v}")

                send_email(email_r, "Appointment Request Received – SAUBHAGYAM",
                    f"Dear {name},\nWe received your appointment request for "
                    f"{date} at {time_v}.\nOur team will confirm within 1 business day.\n"
                    f"Note: Not confirmed until you receive an approval email.\nTeam SAUBHAGYAM")

                reply = reply.replace("[SUBMIT_BOOKING]", "").strip()
            except Exception as e:
                print(f"[SUBMIT ERR] {e}")

        # Handle [HANDOFF_REQUESTED]
        if "[HANDOFF_REQUESTED]" in reply:
            reply = reply.replace("[HANDOFF_REQUESTED]", "").strip()

        return {"reply": reply}

    # ── LIVE AGENT HANDOFF ───────────────────────────────────
    @app.post("/api/handoff")
    async def handoff(req: HandoffRequest):
        send_email(ADMIN_EMAIL,
            f"LIVE AGENT REQUEST from {req.name}",
            f"Name   : {req.name}\nContact: {req.contact}\nMessage: {req.message}\n\n"
            f"Respond within 15 min via WhatsApp {WHATSAPP_NO} or email.")
        return {"success": True, "message": "Agent notified. Expect contact within 15 minutes."}

    # ── BOOKING CRUD ─────────────────────────────────────────
    @app.get("/api/bookings")
    async def get_bookings():
        return store.get_all()

    @app.post("/api/bookings/cancel")
    async def cancel_booking(req: CancelReq):
        b = store.get_by_id(req.booking_id)
        if not b: raise HTTPException(404, "Not found")
        b.status = "Cancelled"; store.save()
        send_email(b.email, "Appointment Cancelled – SAUBHAGYAM",
            f"Dear {b.name},\nAppointment on {b.date} at {b.time} cancelled.\nTeam SAUBHAGYAM")
        return {"success": True}

    @app.post("/api/bookings/reschedule")
    async def reschedule_booking(req: RescheduleReq):
        b = store.get_by_id(req.booking_id)
        if not b: raise HTTPException(404, "Not found")
        b.date = req.new_date; b.time = req.new_time; b.status = "Pending"
        store.save()
        send_email(b.email, "Reschedule Request – SAUBHAGYAM",
            f"Dear {b.name},\nReschedule to {req.new_date} at {req.new_time} under review.\nTeam SAUBHAGYAM")
        return {"success": True}

    @app.post("/api/admin/action")
    async def admin_action(req: AdminActionRequest):
        b = store.get_by_id(req.booking_id)
        if not b: raise HTTPException(404, "Not found")

        if req.action == "ACCEPT":
            b.status = "Confirmed"
            send_email(b.email, "Appointment CONFIRMED - SAUBHAGYAM",
                f"Dear {b.name},\n\nYour appointment is CONFIRMED!\n"
                f"Date: {b.date}\nTime: {b.time}\n\nTeam SAUBHAGYAM")

        elif req.action == "REJECT":
            b.status = "Rejected"
            b.admin_reason = req.reason or "Schedule conflict"
            send_email(b.email, "Appointment Update – SAUBHAGYAM",
                f"Dear {b.name},\n\nWe cannot confirm {b.date} at {b.time}.\n"
                f"Reason: {b.admin_reason}\n\nPlease rebook at saubhagyam.com\nTeam SAUBHAGYAM")

        elif req.action == "RESCHEDULE":
            b.status = "Rescheduled"
            b.suggested_date = req.new_date
            b.suggested_time = req.new_time
            send_email(b.email, "Reschedule Suggestion – SAUBHAGYAM",
                f"Dear {b.name},\n\nSuggested new slot:\n"
                f"Date: {req.new_date}\nTime: {req.new_time}\n"
                f"\nPlease reply to confirm.\nTeam SAUBHAGYAM")

        store.save()
        return {"status": "success"}

    app.mount("/", StaticFiles(directory="ui-chatbot"), name="static")
    return app


# ══════════════════════════════════════════════════════════════
#   ENTRY POINT
# ══════════════════════════════════════════════════════════════
def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--model",   default=DEFAULT_MODEL)
    parser.add_argument("--port",    type=int, default=5000)
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("NVIDIA_API_KEY", "")
    if not api_key:
        api_key = input("Enter NVIDIA API key: ").strip()

    port = int(os.environ.get("PORT", args.port))

    print(f"\n{'='*55}")
    print(f"  SAUBHAGYAM ChatBot v2  |  {args.model}")
    print(f"  Chat : http://127.0.0.1:{port}")
    print(f"  Admin: http://127.0.0.1:{port}/admin")
    print(f"{'='*55}\n")

    if os.environ.get("RENDER") is None:
        threading.Timer(1.5, lambda: webbrowser.open(f"http://127.0.0.1:{port}")).start()
    app = create_app(api_key, args.model)
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
