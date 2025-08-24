import os, json, random
from dotenv import load_dotenv
import google.generativeai as genai

# ========== Setup ==========
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise SystemExit("Missing GEMINI_API_KEY in .env")
genai.configure(api_key=API_KEY)

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

PROFILES   = load_json("data/profiles.json")
ACTIVITIES = load_json("data/activities.json")
    
# Pick a random profile every run
profile_key = random.choice(list(PROFILES.keys()))
profile = PROFILES[profile_key]

# ========== Crisis ==========
CRISIS_MES = """I’m really sorry you’re going through this. You’re not alone.
**If you’re in the US and in immediate danger, call 911.**
You can also call or text **988** (Suicide & Crisis Lifeline) to talk to someone now.
If you’d like, we can try a brief grounding exercise or identify a trusted person to reach out to.
"""

CRISIS_KW = {
    "suicide", "self-harm", "self harm", "kill myself", "end my life",
    "can't go on", "cant go on", "hurt myself", "harm myself"
}

def is_crisis(profile, text):
    """Return True if profile or message suggests a crisis"""
    t = (text or "").lower()
    kw_hit = any(k in t for k in CRISIS_KW)
    severe_scores = profile['phq9'] >= 20 or profile['mood_score'] <= 2
    return kw_hit or severe_scores

# ========== Reminders / Appointments ==========
REMINDERS = []
APPOINTMENTS = []

def parse_intents(text):
    """Naive keyword matching for demo"""
    t = text.lower()
    return {
        'reminder': any(k in t for k in ['remind me', 'set reminder', 'reminder']),
        'appointment': any(k in t for k in ['appointment', 'book', 'schedule']),
    }

def simulate_actions(intents, text):
    outputs = []
    if intents['reminder']:
        REMINDERS.append(text)
        outputs.append('Reminder set (demo).')
    if intents['appointment']:
        APPOINTMENTS.append(text)
        outputs.append('Appointment scheduled (demo).')
    return outputs

# ========== Suggestions ==========
def pick_activities(profile):
    ms = profile.get("mood_score", 5)
    if ms <= 4:
        # low mood users: calming, reflective
        return [activity for activity in ACTIVITIES if "low_mood" in activity['tags'] or "anxiety" in activity['tags']][:2]
    elif ms >= 8:
        # very positive: activation / growth
        return [activity for activity in ACTIVITIES if "balanced" in activity['tags'] or "learning" in activity['tags']][:2]
    else:
        # mid-range: balanced / activation
        return [activity for activity in ACTIVITIES if "balanced" in activity['tags'] or "activation" in activity['tags']][:2]

def build_system_prompt(profile, suggestions):
    sug_text = "\n".join(
        f"- {s['title']}" + (f" ({s['link']})" if s.get("link") else "")
        for s in suggestions
    )
    return f"""You are a supportive wellness assistant. Be empathetic, brief, and non-judgmental.
Do not diagnose. Offer one small, doable next step when appropriate.

Personalize responses using this profile:
Name: {profile['name']}
Mood score: {profile['mood_score']}
PHQ-9: {profile['phq9']}
Notes: {profile['notes']}

Prefer one of these options if relevant:
{sug_text}

End with a gentle check-in question.
"""

def main():
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    suggestions = pick_activities(profile)
    system_prompt = build_system_prompt(profile, suggestions)

    print(f"Chatbot started for {profile['name']}.\nType 'quit' to exit.\n")
    
    while True:
        user_input = input('You: ')
        if user_input.lower().strip() in ('quit', 'exit'):
            print("Goodbye!")
            break
        
        if is_crisis(profile, user_input):
            print("Bot:", CRISIS_MES, "\n")
            continue
        
        prompt = system_prompt + f'\nUser: {user_input}\nAssistant:'
        try:
            resp = model.generate_content(prompt)
            reply = (resp.text or "").strip() if resp else ""
            if not reply:
                reply = "Thanks for sharing. Would you like to try one of the steps above?"

        except Exception:
            reply = 'Sorry, I could not process that.'
        
        print(f'Bot: {reply}\n')
        
        intents = parse_intents(user_input)
        actions = simulate_actions(intents, user_input)
        for act in actions:
            print("Bot:", act)
        
if __name__ == "__main__":
    main()