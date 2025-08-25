import os, json, random
from joblib import load as joblib_load
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
print(f"Selected profile: {profile['name']} (Mood={profile['mood_score']}, PHQ-9={profile['phq9']})")

# ========== Crisis ==========
CRISIS_MES = """I’m really sorry you’re going through this. You’re not alone.
**If you’re in the US and in immediate danger, call 911.**
You can also call or text **988** (Suicide & Crisis Lifeline) to talk to someone now.
If you’d like, we can try a brief grounding exercise or identify a trusted person to reach out to.
"""

CRISIS_KW = {
    "suicide", "self-harm", "self harm", "kill myself", "end my life",
    "ending it", "end it all", "take my life", "take my own life",
    "can't go on", "cant go on", "hurt myself", "harm myself",
    "life isn’t worth living", "life isn't worth living", "no reason to live"
}


CRISIS_MODEL_PATH = os.getenv("CRISIS_MODEL_PATH", "models/model.joblib")
try:
    CRISIS_MODEL = joblib_load(CRISIS_MODEL_PATH)
except Exception:
    CRISIS_MODEL = None
    
CRISIS_MODEL_THRESHOLD = 0.6
    
def crisis_ml_score(text):
    """Return probability from ML model, or None if not available."""
    if CRISIS_MODEL is None:
        return None
    try:
        return float(CRISIS_MODEL.predict_proba([text])[0, 1])
    except Exception:
        return None

def is_crisis_message(text):
    """Hybrid rule+ML gate for crisis detection."""
    t_lower = (text or "").lower()
    # 1) Keyword override
    if any(keyword in t_lower for keyword in CRISIS_KW):
        return True
    # 2) ML probability
    score = crisis_ml_score(text)
    return (score is not None) and (score >= CRISIS_MODEL_THRESHOLD)

# ========== Reminders / Appointments ==========
REMINDERS = []
APPOINTMENTS = []

def parse_intents(user_input):
    """Naive keyword matching for demo"""
    return {
        'reminder': any(keyword in user_input for keyword in ['remind me', 'set reminder', 'reminder']),
        'appointment': any(keyword in user_input for keyword in ['appointment', 'book', 'schedule']),
        'content': any(keyword in user_input for keyword in ['article', 'content', 'resource', 'read', 'learn']),
    }

def simulate_actions(intents, text):
    outputs = []
    if intents['reminder']:
        REMINDERS.append(text)
        outputs.append('Reminder set (demo).')
    if intents['appointment']:
        APPOINTMENTS.append(text)
        outputs.append('Appointment scheduled (demo).')
    if intents['content']:
        link_items = [a for a in ACTIVITIES if a.get('link')]
        item = link_items[0]
        outputs.append(f"Content: {item['title']} — {item['link']}")

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
    return f"""You are a supportive wellness assistant.
- Be empathetic and natural. Vary your openings (don’t always greet).
- First acknowledge what the user said; suggest at most one activity only when helpful or asked.
- Keep replies short (2–3 sentences). End with a gentle check-in question.
- Do not claim you set reminders/appointments; those are handled by tools.

Personalize responses using this profile:
Name: {profile['name']}
Mood score: {profile['mood_score']}
PHQ-9: {profile['phq9']}
Notes: {profile['notes']}

Preferred options if relevant:
{sug_text}
"""

def main():    
    SEVERE_PROFILE = profile['phq9'] >= 20 or profile['mood_score'] <= 2
    CRISIS_BANNER_SHOWN = False
    
    suggestions = pick_activities(profile)
    system_prompt = build_system_prompt(profile, suggestions)

    print(f"Chatbot started for {profile['name']}.\nType 'quit' to exit.\n")
    
    model = genai.GenerativeModel(
        model_name='gemini-1.5-flash',
        system_instruction=system_prompt
    )
    
    chat = model.start_chat(history=[])
    
    while True:
        if SEVERE_PROFILE and not CRISIS_BANNER_SHOWN:
            print(
                f"Bot: I noticed your profile suggests you may be going through a really hard time "
                f"(Mood={profile['mood_score']}, PHQ-9={profile['phq9']})."
            )
            print("Bot:", CRISIS_MES, "\n")
            print("Bot: Let me know if you’d prefer to pause for now, or type 'continue' if you’d like to keep chatting with me.")
            CRISIS_BANNER_SHOWN = True
            continue

        raw_text = input('You: ')
        text = raw_text.strip()
        text_lower = text.lower()

        if text_lower in ('quit', 'exit'):
            print("Goodbye!")
            break
        
        if text_lower in {"show reminders", "show tasks"}:
            print("Bot: Reminders ->", REMINDERS or "none")
            print("Bot: Appointments ->", APPOINTMENTS or "none")
            print()
            continue
        
        if text_lower == "continue":
            pass
        elif is_crisis_message(text):
            print("Bot:", CRISIS_MES, "\n")
            continue

        intents = parse_intents(text_lower)
        if any(intents.values()):
            for act in simulate_actions(intents, text):
                print("Bot:", act)
            print()
            continue

        try:
            resp = chat.send_message(raw_text)
            reply = (resp.text or "").strip() if resp else ""
            if not reply:
                reply = "Thanks for sharing. Would you like to try one of the steps above?"
        except Exception:
            reply = "Sorry, I could not process that."
        
        print(f'Bot: {reply}\n')
        
if __name__ == "__main__":
    main()