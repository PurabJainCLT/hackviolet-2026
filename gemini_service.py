from google import genai

# Initialize the client with your API key
client = genai.Client(api_key="API_KEY")

MODEL = "models/gemini-2.5-flash"   

def ask_gemini(prompt: str) -> str:
    """
    Send a prompt to Gemini and return the text response.
    """
    try:
        # The correct method is generate_content
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt
        )
        
        # Access the text directly from the response object
        return response.text
        
    except Exception as e:
        print(f"Gemini API error: {e}")
        return "Sorry, we couldn't generate advice at this time."