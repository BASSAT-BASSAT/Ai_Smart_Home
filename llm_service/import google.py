import google.generativeai as genai
import os

API_KEY =""
genai.configure(api_key=API_KEY)
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"Model Name: {m.name}")
            print("-" * 20)
except Exception as e:
    print(f"\nAn error occurred: {e}")
    print("Please double-check that your API key is correct and has been pasted properly.")
print("\n--- Query Complete ---")
print("Please use one of the 'Model Names' listed above in your llm_service.py file.")