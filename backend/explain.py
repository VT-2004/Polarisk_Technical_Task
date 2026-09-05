import os
import json
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")


EXPLANATION_SYSTEM_PROMPT = """You are a financial intelligence assistant.
You are given a pre-computed spending fact or anomaly flag detected by our rules engine.
Your sole job is to write a crisp, professional, human-friendly 1-sentence explanation of this fact.

CRITICAL RULES:
1. Do NOT decide if it is an anomaly. Only explain the pre-computed mathematical fact provided.
2. Output EXACTLY ONE single sentence. No bullet points, no extra text, no quotes.
3. Use currency symbols like ₹ or $ correctly based on the provided currency.

Examples of desired output style:
- "You spent ₹42,000 on travel this month, which is your highest spending category."
- "Your latest Adobe payment of ₹6,899 is 32% higher than your previous payments average of ₹5,200."
- "A ₹35,000 payment to MakeMyTrip was flagged because this merchant has not appeared in your previous transaction history."
"""

def generate_rule_based_fallback_explanation(flag: Dict[str, Any]) -> str:
    """Deterministic template fallback if LLM is unavailable."""
    f_type = flag.get("flag_type")
    reason = flag.get("reason_data", {})
    curr_sym = "₹" if reason.get("currency") == "INR" else "$"
    
    if f_type == "category_leader":
        cat = reason.get("category", "all categories").capitalize()
        spend = reason.get("current_month_spend", 0)
        return f"You spent {curr_sym}{spend:,.2f} on {cat} this month, making it your highest spending category."
    
    elif f_type == "merchant_leader":
        merchant = reason.get("merchant", "Top Merchant")
        spend = reason.get("cumulative_spend", 0)
        return f"{merchant} is your top merchant with a cumulative spend of {curr_sym}{spend:,.2f}."
    
    elif f_type == "price_jump":
        merchant = reason.get("merchant", "Merchant")
        curr_amt = reason.get("current_amount", 0)
        avg_amt = reason.get("avg_previous_amount", 0)
        jump = reason.get("jump_percentage", 0)
        return f"Your latest {merchant} payment of {curr_sym}{curr_amt:,.2f} is {jump}% higher than your previous average of {curr_sym}{avg_amt:,.2f}."
    
    elif f_type == "unseen_high_merchant":
        merchant = reason.get("merchant", "Unknown")
        amt = reason.get("amount", 0)
        return f"A {curr_sym}{amt:,.2f} payment to {merchant} was flagged because this is a first-time merchant with an unusually high amount."
    
    return f"A spending anomaly of {curr_sym}{flag.get('amount', 0):,.2f} was detected for {flag.get('merchant', 'your account')}."

def generate_explanation_for_flag(flag: Dict[str, Any]) -> str:
    """
    Calls LLM (Groq or Anthropic) to produce a 1-sentence natural language explanation.
    Falls back gracefully to deterministic template if needed.
    """
    user_prompt = f"Fact Data: {json.dumps(flag.get('reason_data', {}))}\nFlag Type: {flag.get('flag_type')}"

    try:
        if LLM_PROVIDER == "anthropic" and ANTHROPIC_API_KEY:
            from anthropic import Anthropic
            client = Anthropic(api_key=ANTHROPIC_API_KEY)
            resp = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=100,
                temperature=0.2,
                system=EXPLANATION_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}]
            )
            explanation = resp.content[0].text.strip()
            return explanation.strip('"')

        elif GROQ_API_KEY:
            from groq import Groq
            client = Groq(api_key=GROQ_API_KEY)
            models_to_try = [
                GROQ_MODEL,
                "openai/gpt-oss-20b",
                "qwen/qwen3.8-27b",
                "openai/gpt-oss-120b"
            ]
            seen = set()
            unique_models = [m for m in models_to_try if not (m in seen or seen.add(m))]

            for model_name in unique_models:
                try:
                    resp = client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": EXPLANATION_SYSTEM_PROMPT},
                            {"role": "user", "content": user_prompt}
                        ],
                        max_tokens=100,
                        temperature=0.2
                    )
                    explanation = resp.choices[0].message.content.strip()
                    return explanation.strip('"')
                except Exception as e:
                    print(f"[GROQ EXPLAIN RETRY] Model {model_name} failed: {e}. Trying fallback...")
                    continue
            
            return generate_rule_based_fallback_explanation(flag)
    except Exception as e:
        print(f"[EXPLANATION WARNING] LLM explanation failed: {e}. Using deterministic rule-based template.")
        return generate_rule_based_fallback_explanation(flag)

    # Fallback to deterministic template
    return generate_rule_based_fallback_explanation(flag)
