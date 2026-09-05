import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from db import SessionLocal
from main import process_inbox_pipeline
from models import Transaction, AnomalyFlag, UserSession

def run_test():
    db = SessionLocal()
    user = db.query(UserSession).filter(UserSession.access_token != None).first()
    if not user:
        print("No active logged-in user found in database.")
        return
    email = user.email
    print(f"Starting test pipeline for {email}...")
    process_inbox_pipeline(email, SessionLocal)

    
    db = SessionLocal()
    txs = db.query(Transaction).filter(Transaction.user_email == email).all()
    anomalies = db.query(AnomalyFlag).filter(AnomalyFlag.user_email == email).all()
    
    print(f"\n===== SCAN RESULTS FOR {email} =====")
    print(f"Total Transactions Extracted: {len(txs)}")
    for t in txs:
        print(f"  - {t.date} | {t.merchant} | {t.currency} {t.amount} | Cat: {t.category} | Subj: {t.subject}")
    
    print(f"\nTotal Anomalies / Insights: {len(anomalies)}")
    for a in anomalies:
        print(f"  * [{a.flag_type.upper()}] {a.title}: \"{a.explanation}\"")

if __name__ == "__main__":
    run_test()
