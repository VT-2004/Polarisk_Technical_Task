import os
import json
import re
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv

load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")


class ExtractedTransaction(BaseModel):
    is_transaction: bool = True
    merchant: Optional[str] = "Unknown"
    amount: Optional[float] = 0.0
    currency: Optional[str] = "INR"
    date: Optional[str] = None # YYYY-MM-DD
    category: Optional[str] = "other" # travel, subscriptions, shopping, food, utilities, software, entertainment, other
    transaction_type: Optional[str] = "one_time" # one_time, recurring, bill, refund
    confidence: Optional[str] = "medium" # high, medium, low

    @field_validator("category")
    @classmethod
    def validate_category(cls, v):
        allowed = {"travel", "subscriptions", "shopping", "food", "utilities", "software", "entertainment", "other"}
        if not v or v.lower() not in allowed:
            return "other"
        return v.lower()

    @field_validator("transaction_type")
    @classmethod
    def validate_tx_type(cls, v):
        allowed = {"one_time", "recurring", "bill", "refund"}
        if not v or v.lower() not in allowed:
            return "one_time"
        return v.lower()

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v):
        allowed = {"high", "medium", "low"}
        if not v or v.lower() not in allowed:
            return "medium"
        return v.lower()

EXTRACTION_SYSTEM_PROMPT = """You are a financial transaction extraction engine.
Analyze the provided email subject, sender, date, and body text.
Extract structured transaction details.

Return ONLY a valid JSON object matching this exact schema with NO markdown fences, NO explanation, NO preamble:
{
  "is_transaction": true,
  "merchant": "Clean Business/Merchant Name (e.g. Flipkart, Google Play, Swiggy, Amazon, Steam, Codashop, Netflix, Uber)",
  "amount": 1234.56,
  "currency": "INR or USD or EUR etc. (Standard 3-letter ISO code)",
  "date": "YYYY-MM-DD (extract or infer from email date)",
  "category": "one of: travel, subscriptions, shopping, food, utilities, software, entertainment, other",
  "transaction_type": "one of: one_time, recurring, bill, refund",
  "confidence": "high, medium, or low"
}

RULES:
1. If the email is a receipt, invoice, purchase confirmation, voucher delivery with amount paid, or bill, set is_transaction: true.
2. If the email is general promotional spam or marketing without an actual purchase made, set is_transaction: false.
3. Extract the actual final amount paid or billed (numerical float).
4. If currency is in Indian Rupees (₹, Rs, INR), set currency to "INR".
5. Game vouchers or Google Play purchases should be categorized as 'entertainment' or 'software'. Flipkart purchases should be categorized as 'shopping'.
"""

def extract_transaction_with_groq(email_content: str) -> Optional[ExtractedTransaction]:
    """Calls Groq API with multi-model fallback for JSON extraction."""
    from groq import Groq
    client = Groq(api_key=GROQ_API_KEY)
    
    models_to_try = [
        GROQ_MODEL,
        "openai/gpt-oss-20b",
        "qwen/qwen3.8-27b",
        "openai/gpt-oss-120b"
    ]
    # Remove duplicates while preserving order
    seen = set()
    unique_models = [m for m in models_to_try if not (m in seen or seen.add(m))]

    last_err = None
    for model_name in unique_models:
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                    {"role": "user", "content": f"EMAIL CONTENT TO EXTRACT:\n{email_content}"}
                ],
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            raw_json = response.choices[0].message.content.strip()
            parsed = parse_json_to_transaction(raw_json)
            if parsed:
                return parsed
        except Exception as e:
            last_err = e
            print(f"[GROQ EXTRACTION RETRY] Model {model_name} failed: {e}. Trying fallback model...")
            continue
    
    print(f"[GROQ EXTRACTION ERROR] All Groq models failed. Last error: {last_err}")
    return None


def extract_transaction_with_anthropic(email_content: str) -> Optional[ExtractedTransaction]:
    """Calls Anthropic Claude API for JSON extraction."""
    from anthropic import Anthropic
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=500,
        temperature=0.0,
        system=EXTRACTION_SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": f"EMAIL CONTENT TO EXTRACT:\n{email_content}"}
        ]
    )
    
    raw_text = response.content[0].text.strip()
    return parse_json_to_transaction(raw_text)

def parse_json_to_transaction(text: str) -> Optional[ExtractedTransaction]:
    """Safely parses JSON string into ExtractedTransaction model."""
    try:
        # Strip markdown ```json codeblocks if present
        clean_text = re.sub(r"^```json\s*", "", text, flags=re.MULTILINE)
        clean_text = re.sub(r"```$", "", clean_text, flags=re.MULTILINE).strip()
        data = json.loads(clean_text)
        
        if not data.get("is_transaction", True):
            return None
        
        # Ensure numerical amount is valid
        if "amount" in data and data["amount"] is not None:
            if isinstance(data["amount"], str):
                # Clean currency symbols or commas
                cleaned_amt = re.sub(r"[^\d.]", "", data["amount"])
                data["amount"] = float(cleaned_amt) if cleaned_amt else 0.0
            else:
                data["amount"] = float(data["amount"])

        return ExtractedTransaction(**data)
    except Exception as e:
        return None

def extract_transaction_from_email(email_data: Dict[str, Any]) -> Optional[ExtractedTransaction]:
    """
    Main extraction entrypoint. Builds email context string and calls configured LLM provider.
    """
    email_text = (
        f"Subject: {email_data.get('subject', '')}\n"
        f"Sender: {email_data.get('sender', '')}\n"
        f"Date: {email_data.get('date_header', '')}\n"
        f"Snippet: {email_data.get('snippet', '')}\n\n"
        f"Body Text:\n{email_data.get('body', '')[:2000]}"
    )

    # Provider selection
    if LLM_PROVIDER == "anthropic" and ANTHROPIC_API_KEY:
        return extract_transaction_with_anthropic(email_text)
    elif GROQ_API_KEY:
        return extract_transaction_with_groq(email_text)
    else:
        # Fallback local heuristics parser if no API keys are supplied yet
        return heuristic_fallback_extractor(email_data)

def heuristic_fallback_extractor(email_data: Dict[str, Any]) -> Optional[ExtractedTransaction]:
    """
    Zero-config local regex fallback parser in case LLM API keys are empty during initial setup.
    """
    full_text = f"{email_data.get('subject', '')} {email_data.get('snippet', '')} {email_data.get('body', '')}"
    
    # Extract amount
    amt_match = re.search(r"(?:₹|rs\.?|inr|\$|€)\s*([\d,]+(?:\.\d{2})?)", full_text, re.IGNORECASE)
    if not amt_match:
        return None
    
    amount_str = amt_match.group(1).replace(",", "")
    amount = float(amount_str)
    
    # Extract merchant from sender or subject
    sender = email_data.get("sender", "")
    merchant = "Unknown Merchant"
    if "@" in sender:
        domain = sender.split("@")[-1].split(">")[0].split(".")[0].capitalize()
        merchant = domain

    # Extract date
    date_str = datetime.date.today().isoformat()
    
    return ExtractedTransaction(
        is_transaction=True,
        merchant=merchant,
        amount=amount,
        currency="INR" if "₹" in full_text or "rs" in full_text.lower() else "USD",
        date=date_str,
        category="other",
        transaction_type="one_time",
        confidence="medium"
    )
