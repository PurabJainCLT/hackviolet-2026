from google import genai

# Set API key directly
genai.api_key = "AIzaSyCm29SAS0T536s80lRQ_Stb3oOc6k2bYTE"

# Select model
model = "gemini-1.5-flash"

def ask_gemini(prompt: str) -> str:
    # generate_text is the current method for text generation
    response = genai.generate_text(model=model, prompt=prompt)
    return response.result
