import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=api_key)

# List available models
print("Available models:")
for model in genai.list_models():
    if 'generateContent' in model.supported_generation_methods:
        print(f"- {model.name}")

# Test a simple request
model = genai.GenerativeModel('gemini-1.5-flash')
response = model.generate_content("Say hello in a creative way")
print(f"Test response: {response.text}")