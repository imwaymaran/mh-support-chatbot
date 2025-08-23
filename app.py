import os, json
from dotenv import load_dotenv
import google.generativeai as genai
import random

# --- Setup ---
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
    
profile_key = random.choice(list(PROFILES.keys()))
profile = PROFILES[profile_key]

# --- Suggestions ---
def pick_activities(profile):
    ms = profile.get("mood_score", 5)
    if ms <= 4:
        # low mood users: calming, reflective
        return [a for a in ACTIVITIES if "low_mood" in a.get("tags", []) or "anxiety" in a.get("tags", [])][:2]
    elif ms >= 8:
        # very positive: activation / growth
        return [a for a in ACTIVITIES if "balanced" in a.get("tags", []) or "learning" in a.get("tags", [])][:2]
    else:
        # mid-range: balanced / activation
        return [a for a in ACTIVITIES if "balanced" in a.get("tags", []) or "activation" in a.get("tags", [])][:2]

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
        
        prompt = system_prompt + f'\nUser: {user_input}\nAssistant:'
        try:
            resp = model.generate_content(prompt)
            reply = resp.text.strip()
        except Exception as e:
            reply = 'Sorry, I could not process that.'
        
        print(f'Bot: {reply}\n')
        
if __name__ == "__main__":
    main()