import os
from dotenv import load_dotenv
from openai import OpenAI

# Încarcă .env
load_dotenv()

# Creează clientul
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_response(prompt: str) -> str:
    """Trimite prompt-ul la model și returnează răspunsul."""
    response = client.responses.create(
        model="gpt-4.1-nano", 
        input=prompt
    )
    return response.output_text.strip()

if __name__ == "__main__":
    print(" Scrie 'exit' ca să ieși.")
    while True:
        user_input = input("Tu: ")
        if user_input.lower() in ["exit", "quit"]:
            print(" La revedere!")
            break
        try:
            answer = get_response(user_input)
            print(f"GPT: {answer}\n")
        except Exception as e:
            print(f" Eroare: {e}\n")
