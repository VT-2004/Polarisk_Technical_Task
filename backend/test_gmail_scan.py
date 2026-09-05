import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(__file__))
from db import engine, SessionLocal
from models import UserSession, Transaction, AnomalyFlag
from gmail_client import get_gmail_service, fetch_and_filter_emails
from extraction import extract_transaction_from_email

def diagnose():
    db = SessionLocal()
    users = db.query(UserSession).all()
    print(f"Total users in DB: {len(users)}")
    for u in users:
        print(f"User email: {u.email} | Has token: {bool(u.access_token)}")
        if u.access_token:
            try:
                service = get_gmail_service(u.access_token, u.refresh_token)
                # Test simple list
                profile = service.users().getProfile(userId="me").execute()
                print(f"Connected to Gmail profile: {profile.get('emailAddress')} | Total messages: {profile.get('messagesTotal')}")
                
                # Test query 1: simple query
                q1 = 'receipt OR invoice OR "Google Play" OR order'
                res1 = service.users().messages().list(userId="me", q=q1, maxResults=10).execute()
                msgs1 = res1.get("messages", [])
                print(f"Query '{q1}' returned {len(msgs1)} messages.")

                for m in msgs1[:5]:
                    msg = service.users().messages().get(userId="me", id=m["id"], format="full").execute()
                    headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
                    print(f"  -> Found Message: Subject: '{headers.get('subject')}' | From: '{headers.get('from')}'")

            except Exception as e:
                import traceback
                print(f"Error accessing Gmail for {u.email}: {e}")
                traceback.print_exc()

if __name__ == "__main__":
    diagnose()
