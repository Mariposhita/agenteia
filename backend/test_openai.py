import os
import openai
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

try:
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Hola"}],
        max_tokens=10
    )
    print("Respuesta OpenAI:", response.choices[0].message.content)
except Exception as e:
    print("Error al conectar con OpenAI:", e)