import os
import re
import base64
import html
import datetime
from typing import List, Dict, Any, Optional, Tuple
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
TOKEN_URI = "https://oauth2.googleapis.com/token"

# High-precision Gmail search query covering Google Play, Flipkart, Invoices, Receipts, and Bills
DEFAULT_GMAIL_QUERY = (
    'subject:"Order Receipt" OR subject:Receipt OR subject:Invoice OR subject:Bill OR '
    'subject:Tax OR subject:Recharge OR from:googleplay-noreply@google.com OR subject:Flipkart OR '
    'subject:Swiggy OR subject:Zomato OR subject:Amazon OR subject:Uber OR subject:debited OR '
    'subject:subscription OR subject:payment'
)

# Strong financial keywords for pre-filtering
FINANCIAL_KEYWORDS = [
    r"₹", r"rs\.?", r"inr", r"\$", r"usd", r"eur", r"€", r"gbp", r"£",
    r"invoice", r"receipt", r"payment", r"order", r"amount", r"debited",
    r"charged", r"subscription", r"bill", r"transaction", r"paid",
    r"total", r"renewal", r"autopay", r"recharge", r"fare", r"ticket",
    r"voucher", r"gift card", r"flipkart", r"google play", r"purchase", r"delivered"
]

# Promotional noise patterns to discard
PROMOTIONAL_NOISE_KEYWORDS = [
    r"up to \d+%\s*off", r"coupon code", r"sale is live", r"flat \d+%\s*off",
    r"limited time offer", r"don't miss out", r"newsletter", r"job alert",
    r"digest", r"recommended for you"
]

def get_gmail_service(access_token: str, refresh_token: Optional[str] = None):
    """Build and return an authorized Gmail API service."""
    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri=TOKEN_URI,
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        scopes=["https://www.googleapis.com/auth/gmail.readonly"]
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("gmail", "v1", credentials=creds, cache_discovery=False)

def build_gmail_query(months_back: int = 24, custom_query: Optional[str] = None) -> str:
    """Builds search query covering last N months."""
    base_query = custom_query or DEFAULT_GMAIL_QUERY
    return base_query

def clean_html_to_text(html_content: str) -> str:
    """Strips HTML tags, scripts, and extra whitespace to minimize token usage."""
    # Remove script and style tags
    text = re.sub(r"<(script|style).*?>.*?</\1>", "", html_content, flags=re.DOTALL | re.IGNORECASE)
    # Replace line break tags with newlines
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</div>", "\n", text, flags=re.IGNORECASE)
    # Strip remaining HTML tags
    text = re.sub(r"<.*?>", " ", text)
    # Unescape HTML entities
    text = html.unescape(text)
    # Collapse consecutive whitespace and empty lines
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()

def extract_message_body(payload: Dict[str, Any]) -> str:
    """Extracts decoded text content from Gmail message payload parts."""
    body_text = ""
    mime_type = payload.get("mimeType", "")

    if "body" in payload and payload["body"].get("data"):
        data = payload["body"]["data"]
        try:
            decoded = base64.urlsafe_b64decode(data.encode("ASCII")).decode("utf-8", errors="replace")
            if "html" in mime_type:
                return clean_html_to_text(decoded)
            return decoded.strip()
        except Exception:
            pass

    if "parts" in payload:
        for part in payload["parts"]:
            part_mime = part.get("mimeType", "")
            if part_mime == "text/plain" and part.get("body", {}).get("data"):
                try:
                    data = part["body"]["data"]
                    decoded = base64.urlsafe_b64decode(data.encode("ASCII")).decode("utf-8", errors="replace")
                    return decoded.strip()
                except Exception:
                    pass
            elif part_mime == "text/html" and part.get("body", {}).get("data"):
                try:
                    data = part["body"]["data"]
                    decoded = base64.urlsafe_b64decode(data.encode("ASCII")).decode("utf-8", errors="replace")
                    body_text = clean_html_to_text(decoded)
                except Exception:
                    pass
            elif "parts" in part: # Nested multipart
                nested = extract_message_body(part)
                if nested:
                    return nested

    return body_text

def pre_filter_email(subject: str, sender: str, snippet: str, body: str) -> Tuple[bool, str]:
    """
    Deterministic regex/keyword pre-filter.
    Returns (is_candidate, reason). Drops irrelevant noise before calling LLM.
    """
    subject_lower = subject.lower()
    full_text = f"{subject} {sender} {snippet} {body[:2500]}".lower()

    # Fast track high-confidence receipt subjects
    if any(k in subject_lower for k in ["google play", "receipt", "invoice", "order receipt", "order confirmation", "bill", "payment confirmation", "tax invoice", "voucher"]):
        return True, "Passed as high-confidence receipt subject"

    # Discard if matches promotional spam patterns without explicit payment wording
    has_promo = any(re.search(pat, full_text) for pat in PROMOTIONAL_NOISE_KEYWORDS)
    has_hard_transaction_proof = any(re.search(pat, full_text) for pat in [
        r"order #", r"invoice #", r"receipt #", r"payment of", r"debited",
        r"transaction id", r"amount paid", r"bill amount", r"voucher",
        r"gift card", r"flipkart", r"google play", r"play store", r"purchase",
        r"order confirmed", r"successfully paid"
    ])
    
    if has_promo and not has_hard_transaction_proof:
        return False, "Filtered as promotional marketing newsletter"

    # Check for presence of financial terms or currency markers
    matches_financial = any(re.search(pat, full_text) for pat in FINANCIAL_KEYWORDS)
    if not matches_financial:
        return False, "No currency or financial transaction keywords found"

    # Check for presence of numbers (price candidates)
    if not re.search(r"\d+([.,]\d{2})?", full_text):
        return False, "No numerical price values found"

    return True, "Valid candidate transaction email"

def fetch_and_filter_emails(
    service,
    max_results: int = 60,
    months_back: int = 12
) -> List[Dict[str, Any]]:
    """
    Fetches emails matching targeted query, applies pre-filter, and returns parsed candidate list.
    """
    query = build_gmail_query(months_back=months_back)
    print(f"[GMAIL FETCH] Executing search query: {query}")
    
    # List message IDs
    try:
        result = service.users().messages().list(
            userId="me",
            q=query,
            maxResults=max_results
        ).execute()
    except Exception as e:
        print(f"[GMAIL FETCH ERROR] Failed to list messages: {e}")
        return []
    
    messages = result.get("messages", [])
    print(f"[GMAIL FETCH] Found {len(messages)} raw candidate messages matching query.")
    candidates = []

    for msg_meta in messages:
        msg_id = msg_meta["id"]
        try:
            msg = service.users().messages().get(
                userId="me",
                id=msg_id,
                format="full"
            ).execute()
        except Exception as e:
            continue

        headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
        subject = headers.get("subject", "(No Subject)")
        sender = headers.get("from", "")
        date_header = headers.get("date", "")
        snippet = msg.get("snippet", "")
        body = extract_message_body(msg.get("payload", {}))

        # Truncate body if very long to prevent blowing token budget (first 3000 chars is plenty for invoices)
        truncated_body = body[:3000] if body else snippet

        # Run pre-filter
        is_candidate, reason = pre_filter_email(subject, sender, snippet, truncated_body)
        print(f"[EMAIL PRE-FILTER] Subj: '{subject[:45]}' -> Keep: {is_candidate} ({reason})")
        
        if is_candidate:
            permalink = f"https://mail.google.com/mail/u/0/#inbox/{msg_id}"
            candidates.append({
                "message_id": msg_id,
                "thread_id": msg.get("threadId"),
                "subject": subject,
                "sender": sender,
                "date_header": date_header,
                "snippet": snippet,
                "body": truncated_body,
                "permalink": permalink
            })

    print(f"[GMAIL SUMMARY] Total surviving candidate emails for LLM extraction: {len(candidates)}")
    return candidates
