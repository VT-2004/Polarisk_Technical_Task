import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv("backend/.env")
api_key = os.getenv("GROQ_API_KEY")

client = Groq(api_key=api_key)
for model in ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"]:
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Return json: {\"status\": \"ok\"}"}],
            response_format={"type": "json_object"}
        )
        print(f"Model {model} SUCCESS: {resp.choices[0].message.content}")
        break
    except Exception as e:
        print(f"Model {model} failed: {e}")
