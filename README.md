# Mental Health Chatbot (Demo)

This is a simple Streamlit + Gemini chatbot prototype designed as a 24/7 wellness companion.  
It simulates assisting a member support team with basic tasks such as:
- Setting up an appointment (simulated)
- Helping with content/resources
- Suggesting activities when lonely
- Setting reminders (simulated)

## Features
- Powered by Google's Gemini API
- Personalized responses based on simulated user profiles
- Lightweight demo with Streamlit UI

## Setup
1. Clone the repo
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy the environment file and add your Gemini API key:
   ```bash
   cp .env.example .env
   ```
   Then open .env and replace with your actual key:
   ```text
   GEMINI_API_KEY=your_api_key_here
   ```

4. Run the app:
   ```python
   streamlit run app.py
   ```