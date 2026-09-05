import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from db import SessionLocal
from models import UserSession
from gmail_client import get_gmail_service

def search_test():
    db = SessionLocal()
    u = db.query(UserSession).filter(UserSession.access_token != None).first()
    if not u:
        print("No active logged-in user with access token found in database.")
        return


    service = get_gmail_service(u.access_token, u.refresh_token)
    
    # Try different targeted queries
    queries = [
        'from:googleplay-noreply@google.com',
        'subject:"Order Receipt"',
        'subject:"Google Play"',
        'subject:receipt OR subject:invoice OR subject:bill OR subject:debited OR subject:recharge OR subject:flipkart'
    ]

    for q in queries:
        print(f"\n--- Searching with query: [{q}] ---")
        res = service.users().messages().list(userId="me", q=q, maxResults=15).execute()
        msgs = res.get("messages", [])
        print(f"Found {len(msgs)} messages.")
        for m in msgs[:10]:
            msg = service.users().messages().get(userId="me", id=m["id"], format="full").execute()
            headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
            print(f"  * Date: {headers.get('date', '')[:16]} | Subj: {headers.get('subject')} | From: {headers.get('from')}")

if __name__ == "__main__":
    search_test()
