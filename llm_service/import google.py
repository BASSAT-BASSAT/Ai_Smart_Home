import google.generativeai as genai
import os

# --- IMPORTANT ---
# Paste your Gemini API key inside the quotes below
# It's the same key you put in your docker-compose.yml file
API_KEY =""

# Configure the library with your key
genai.configure(api_key=API_KEY)

print("--- Querying Google for available models... ---\n")

try:
    # Iterate through all models available to your API key
    for m in genai.list_models():
        # The error message mentioned 'generateContent', so let's check
        # which models actually support that method.
        if 'generateContent' in m.supported_generation_methods:
            print(f"Model Name: {m.name}")
            print("-" * 20)

except Exception as e:
    print(f"\nAn error occurred: {e}")
    print("Please double-check that your API key is correct and has been pasted properly.")

print("\n--- Query Complete ---")
print("Please use one of the 'Model Names' listed above in your llm_service.py file.")