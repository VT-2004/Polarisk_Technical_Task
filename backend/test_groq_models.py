import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv("backend/.env")
api_key = os.getenv("GROQ_API_KEY")

client = Groq(api_key=api_key)
from extraction import EXTRACTION_SYSTEM_PROMPT, parse_json_to_transaction

sample_email = """
From: googleplay-noreply@google.com
Subject: Your Google Play Order Receipt from 8 Aug 2026
Date: Sat, 8 Aug 2026 14:30:00 +0530
Body:
Thank you. You've made a purchase from MOCO STUDIOS PRIVATE LIMITED on Google Play.
Order number: GPA.3392-1029-4412
Item: In-Game Voucher Pack (500 Gems)
Price: ₹499.00
Tax: ₹0.00
Total: ₹499.00
Payment method: Google Pay UPI
"""

for model in ["openai/gpt-oss-20b", "qwen/qwen3.8-27b", "openai/gpt-oss-120b"]:
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": f"EMAIL CONTENT TO EXTRACT:\n{sample_email}"}
            ],
            response_format={"type": "json_object"}
        )
        content = resp.choices[0].message.content
        parsed = parse_json_to_transaction(content)
        print(f"Model {model} SUCCESS: Merchant={parsed.merchant}, Amount={parsed.amount}, Currency={parsed.currency}, Cat={parsed.category}")
    except Exception as e:
        print(f"Model {model} failed: {e}")


