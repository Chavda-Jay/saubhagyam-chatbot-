import sys, os, re, uuid, json, datetime, smtplib, base64, threading, webbrowser
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
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
DEFAULT_MODEL = "meta/llama-3.1-8b-instruct"

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
SMTP_PASSWORD    = os.environ.get("SMTP_PASSWORD", "wyrkbnuxxroxawhj")
FROM_EMAIL       = os.environ.get("FROM_EMAIL", "chavdajay510@gmail.com")
ADMIN_EMAIL      = os.environ.get("ADMIN_EMAIL", "chavdajay510@gmail.com")
WHATSAPP_NO      = "+919998978397"
#SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "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")
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")
# ══════════════════════════════════════════════════════════════
#   SYSTEM PROMPT
# ══════════════════════════════════════════════════════════════
BASE_SYSTEM_PROMPT = """
You are "Saubhagyam AI," the official digital ambassador for SAUBHAGYAM Web Pvt. Ltd.
Be polite, friendly, and professional like a real human support agent.

LANGUAGE RULES:
1. GUJARATI (kem cho, su che, majama) -> reply in transliterated Gujarati
2. HINDI/HINGLISH (namaste, kaise ho) -> reply in Hinglish
3. ENGLISH -> reply in English
Keep technical terms (AI, Blockchain, API) in English always.

RESPONSE STYLE:
- Reply naturally and conversationally, like a helpful human, NOT like a brochure.
- Keep replies SHORT (2-5 sentences) unless user explicitly asks for full details, a list, or "tell me more".
- Do NOT dump the entire service list unless the user asks "what services do you offer" or similar broad questions.
- If user asks something specific (e.g. "I want to make a mobile app"), give a brief, relevant, friendly response and ask a follow-up question to understand their needs better - don't list every sub-service.
- Use bullet points and bold headings ONLY when listing multiple items the user specifically asked for.
- Match the tone of the user's message - casual question gets casual short answer, detailed request gets detailed answer.

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
        if image_b64:
            content = [
                {"type": "text", "text": user_input},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
            ]
        else:
            content = user_input
        self.history.append({"role": "user", "content": content})
        try:
            res = self.client.chat.completions.create(
                model=self.model, messages=self.history,
                temperature=0.5, max_tokens=1024
            )
            reply = res.choices[0].message.content
        except Exception as ex:
            self.history.pop()
            return f"[AI Error: {ex}]"
        self.history.append({"role": "assistant", "content": reply})
        return reply

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

    # ── MAIN CHAT ENDPOINT ───────────────────────────────────
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
