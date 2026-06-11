import os
from dotenv import load_dotenv
import google.generativeai as genai

# Force reload .env
load_dotenv(override=True)

api_key = os.environ.get("GOOGLE_API_KEY")

if not api_key:
    print("❌ ERROR: No GOOGLE_API_KEY found in environment variables.")
else:
    print(f"🔑 Loaded API Key starting with: {api_key[:8]}...")

    try:
        genai.configure(api_key=api_key)
        print("📡 Attempting to connect to Google Gemini API...")
        
        # Try to list models (simplest authenticated call)
        models = list(genai.list_models())
        if models:
            print(f"✅ Success! Found {len(models)} models.")
            print(f"   First model: {models[0].name}")
        else:
            print("⚠️ Warning: Authentication successful but no models returned.")
            
    except Exception as e:
        print("\n❌ API KEY ERROR:")
        print(e)
