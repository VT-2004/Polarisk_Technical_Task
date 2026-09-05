import os
import datetime
import asyncio
import sys
from typing import Optional, List
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from dotenv import load_dotenv

# Ensure Windows stdout supports UTF-8 characters like ₹
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Load environment variables
load_dotenv()

from db import get_db, init_db, SessionLocal
from models import UserSession, Transaction, AnomalyFlag, ScanProgress, ScanRun
from auth import router as auth_router, require_current_user, get_current_user_email, COOKIE_NAME
from gmail_client import get_gmail_service, fetch_and_filter_emails
from extraction import extract_transaction_from_email
from analysis import compute_spending_summary, detect_recurring_payments, detect_anomalies_and_insights
from explain import generate_explanation_for_flag
from mock_data import get_demo_transactions

# Initialize Database tables
init_db()

app = FastAPI(
    title="Gmail Spend Intelligence API",
    description="Analyzes Gmail inbox for financial transactions, recurring subscriptions, and spending anomalies with isolated scan run history.",
    version="1.1.0"
)

# Configure CORS
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Auth Router
app.include_router(auth_router)

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "llm_provider": os.getenv("LLM_PROVIDER", "groq")
    }

def process_inbox_pipeline(user_email: str, db_session_factory, run_name: Optional[str] = None):
    """
    Background worker that executes an isolated scan session:
    1. Creates a new ScanRun record (so tests never overlap).
    2. Fetches & Pre-filters from Gmail.
    3. Structured LLM extraction.
    4. Deterministic analytics & recurring detection for this specific run.
    5. LLM explanation phrasing for anomalies in this run.
    """
    print(f"[SCAN] Starting isolated inbox scan session for {user_email}...")
    db = db_session_factory()
    try:
        user = db.query(UserSession).filter(UserSession.email == user_email).first()
        if not user or not user.access_token:
            print(f"[SCAN ERROR] User or access token not found for {user_email}")
            return

        progress = db.query(ScanProgress).filter(ScanProgress.user_email == user_email).first()
        if not progress:
            progress = ScanProgress(user_email=user_email)
            db.add(progress)

        # Stage 1: Create a distinct ScanRun record
        existing_runs_count = db.query(ScanRun).filter(ScanRun.user_email == user_email).count()
        now_str = datetime.datetime.now().strftime("%d %b, %I:%M %p")
        scan_name = run_name or f"Live Inbox Scan #{existing_runs_count + 1} ({now_str})"
        
        scan_run = ScanRun(
            user_email=user_email,
            run_name=scan_name,
            scan_type="live"
        )
        db.add(scan_run)
        db.commit()
        db.refresh(scan_run)

        # Stage 2: Fetching & Pre-filtering
        progress.is_scanning = True
        progress.stage = "fetching"
        progress.message = "Searching Gmail for financial emails (invoices, receipts, bills)..."
        db.commit()

        service = get_gmail_service(user.access_token, user.refresh_token)
        candidates = fetch_and_filter_emails(service, max_results=50, months_back=12)

        if not candidates:
            progress.is_scanning = False
            progress.stage = "complete"
            progress.message = "Scan complete: No financial invoices, receipts, or bills were found in this Gmail inbox."
            user.last_synced_at = datetime.datetime.utcnow()
            db.commit()
            print(f"[SCAN COMPLETE] No candidates found for {user_email}")
            return

        progress.total_count = len(candidates)
        progress.stage = "extracting"
        progress.message = f"Found {len(candidates)} candidate financial emails. Extracting transaction details..."
        db.commit()

        extracted_transactions = []
        for idx, email_data in enumerate(candidates, 1):
            progress.scanned_count = idx
            progress.message = f"Extracting transaction {idx} of {len(candidates)} via LLM..."
            db.commit()

            # LLM Extraction
            parsed = extract_transaction_from_email(email_data)
            if parsed and parsed.is_transaction and parsed.amount and parsed.amount > 0:
                print(f"[EXTRACTED TX {idx}/{len(candidates)}] {parsed.merchant} -> {parsed.currency} {parsed.amount} | Cat: {parsed.category} | Date: {parsed.date}")
                tx = Transaction(
                    user_email=user_email,
                    scan_run_id=scan_run.id,
                    message_id=email_data["message_id"],
                    thread_id=email_data.get("thread_id"),
                    subject=email_data.get("subject"),
                    sender=email_data.get("sender"),
                    merchant=parsed.merchant or "Unknown",
                    amount=parsed.amount,
                    currency=parsed.currency or "INR",
                    date=parsed.date or datetime.date.today().isoformat(),
                    category=parsed.category or "other",
                    transaction_type=parsed.transaction_type or "one_time",
                    confidence=parsed.confidence or "high",
                    gmail_permalink=email_data.get("permalink"),
                    snippet=email_data.get("snippet")
                )
                db.add(tx)
                db.flush()
                extracted_transactions.append({
                    "id": tx.id,
                    "message_id": tx.message_id,
                    "merchant": tx.merchant,
                    "amount": tx.amount,
                    "currency": tx.currency,
                    "date": tx.date,
                    "category": tx.category,
                    "transaction_type": tx.transaction_type,
                    "gmail_permalink": tx.gmail_permalink
                })

        db.commit()
        progress.extracted_count = len(extracted_transactions)

        # Stage 3: Deterministic Analytics for this Run
        progress.stage = "analyzing"
        progress.message = "Running financial analytics & detecting recurring subscriptions and anomalies..."
        db.commit()

        flags = detect_anomalies_and_insights(extracted_transactions)

        # Stage 4: LLM Explanation Phrasing
        progress.stage = "explaining"
        progress.message = "Generating natural language explanations for flagged insights..."
        db.commit()

        for flag in flags:
            explanation_sentence = generate_explanation_for_flag(flag)
            anomaly = AnomalyFlag(
                user_email=user_email,
                scan_run_id=scan_run.id,
                transaction_id=None,
                flag_type=flag["flag_type"],
                severity=flag["severity"],
                title=flag["title"],
                reason_data=flag["reason_data"],
                explanation=explanation_sentence,
                source_message_id=flag.get("source_message_id"),
                gmail_permalink=flag.get("gmail_permalink")
            )
            db.add(anomaly)

        # Update ScanRun totals
        total_spend = sum(t["amount"] for t in extracted_transactions)
        scan_run.total_spend = total_spend
        scan_run.transaction_count = len(extracted_transactions)
        scan_run.anomaly_count = len(flags)

        user.last_synced_at = datetime.datetime.utcnow()
        user.total_emails_scanned = len(candidates)
        progress.is_scanning = False
        progress.stage = "complete"
        progress.message = f"Scan complete! Extracted {len(extracted_transactions)} transactions."
        db.commit()
        print(f"[SCAN COMPLETED] Run '{scan_name}' saved with {len(extracted_transactions)} transactions and {len(flags)} anomalies.")

    except Exception as e:
        import traceback
        print(f"[SCAN EXCEPTION] Error during inbox scan for {user_email}: {e}")
        traceback.print_exc()
        db.rollback()
        progress = db.query(ScanProgress).filter(ScanProgress.user_email == user_email).first()
        if progress:
            progress.is_scanning = False
            progress.stage = "error"
            progress.error = str(e)
            progress.message = f"Scan failed: {str(e)}"
            db.commit()
    finally:
        db.close()

@app.post("/api/scan")
async def trigger_scan(
    background_tasks: BackgroundTasks,
    request: Request,
    run_name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Triggers an isolated inbox fetch, extraction, and analysis pipeline."""
    user = require_current_user(request, db)
    
    progress = db.query(ScanProgress).filter(ScanProgress.user_email == user.email).first()
    if progress and progress.is_scanning:
        return {"status": "in_progress", "message": "A scan is already currently running."}

    background_tasks.add_task(process_inbox_pipeline, user.email, SessionLocal, run_name)
    return {"status": "started", "message": "Email scan initiated successfully."}

@app.get("/api/scan/progress")
def get_scan_progress(request: Request, db: Session = Depends(get_db)):
    """Returns the live status of the ongoing or last scan."""
    email = get_current_user_email(request)
    if not email:
        return {"is_scanning": False, "stage": "idle", "message": "Not authenticated"}

    progress = db.query(ScanProgress).filter(ScanProgress.user_email == email).first()
    if not progress:
        return {"is_scanning": False, "stage": "idle", "message": "No scan initiated yet", "scanned_count": 0, "total_count": 0}

    return {
        "is_scanning": progress.is_scanning,
        "stage": progress.stage,
        "message": progress.message,
        "scanned_count": progress.scanned_count,
        "total_count": progress.total_count,
        "extracted_count": progress.extracted_count,
        "error": progress.error
    }

@app.get("/api/runs")
def list_scan_runs(request: Request, db: Session = Depends(get_db)):
    """Lists all distinct scan runs for the logged-in user."""
    email = get_current_user_email(request)
    if not email:
        raise HTTPException(status_code=401, detail="Authentication required")

    runs = db.query(ScanRun).filter(ScanRun.user_email == email).order_by(ScanRun.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "run_name": r.run_name,
            "scan_type": r.scan_type,
            "total_spend": r.total_spend,
            "transaction_count": r.transaction_count,
            "anomaly_count": r.anomaly_count,
            "created_at": r.created_at.isoformat()
        }
        for r in runs
    ]

@app.delete("/api/runs/{run_id}")
def delete_scan_run(run_id: int, request: Request, db: Session = Depends(get_db)):
    """Deletes an individual scan run and its associated transactions/anomalies."""
    email = get_current_user_email(request)
    if not email:
        raise HTTPException(status_code=401, detail="Authentication required")

    run = db.query(ScanRun).filter(ScanRun.id == run_id, ScanRun.user_email == email).first()
    if not run:
        raise HTTPException(status_code=404, detail="Scan run not found")

    db.delete(run)
    db.commit()
    return {"status": "success", "message": f"Scan run #{run_id} deleted."}

@app.get("/api/dashboard")
def get_dashboard(request: Request, run_id: Optional[int] = None, db: Session = Depends(get_db)):
    """
    Returns dashboard data scoped to a specific ScanRun.
    If no run_id is supplied, defaults to the most recent ScanRun.
    """
    email = get_current_user_email(request)
    if not email:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Fetch all available runs for the user
    available_runs = db.query(ScanRun).filter(ScanRun.user_email == email).order_by(ScanRun.created_at.desc()).all()
    
    selected_run = None
    if run_id:
        selected_run = db.query(ScanRun).filter(ScanRun.id == run_id, ScanRun.user_email == email).first()
    elif available_runs:
        selected_run = available_runs[0]

    if selected_run:
        tx_query = db.query(Transaction).filter(Transaction.user_email == email, Transaction.scan_run_id == selected_run.id)
        anomaly_query = db.query(AnomalyFlag).filter(AnomalyFlag.user_email == email, AnomalyFlag.scan_run_id == selected_run.id)
    else:
        # Fallback to general user transactions if no scan_run is attached yet
        tx_query = db.query(Transaction).filter(Transaction.user_email == email)
        anomaly_query = db.query(AnomalyFlag).filter(AnomalyFlag.user_email == email)

    tx_records = tx_query.order_by(Transaction.date.desc()).all()
    tx_dicts = [
        {
            "id": t.id,
            "message_id": t.message_id,
            "subject": t.subject,
            "sender": t.sender,
            "merchant": t.merchant,
            "amount": t.amount,
            "currency": t.currency,
            "date": t.date,
            "category": t.category,
            "transaction_type": t.transaction_type,
            "confidence": t.confidence,
            "gmail_permalink": t.gmail_permalink,
            "snippet": t.snippet
        }
        for t in tx_records
    ]

    summary = compute_spending_summary(tx_dicts)
    recurring = detect_recurring_payments(tx_dicts)
    
    anomalies_records = anomaly_query.order_by(AnomalyFlag.created_at.desc()).all()
    anomalies_list = [
        {
            "id": a.id,
            "flag_type": a.flag_type,
            "severity": a.severity,
            "title": a.title,
            "reason_data": a.reason_data,
            "explanation": a.explanation,
            "source_message_id": a.source_message_id,
            "gmail_permalink": a.gmail_permalink
        }
        for a in anomalies_records
    ]

    return {
        "user_email": email,
        "active_run": {
            "id": selected_run.id if selected_run else None,
            "run_name": selected_run.run_name if selected_run else "Default Run",
            "created_at": selected_run.created_at.isoformat() if selected_run else None
        } if selected_run else None,
        "available_runs": [
            {
                "id": r.id,
                "run_name": r.run_name,
                "scan_type": r.scan_type,
                "total_spend": r.total_spend,
                "transaction_count": r.transaction_count,
                "anomaly_count": r.anomaly_count,
                "created_at": r.created_at.isoformat()
            }
            for r in available_runs
        ],
        "summary": summary,
        "recurring_subscriptions": recurring,
        "anomalies": anomalies_list,
        "transactions": tx_dicts
    }

@app.post("/api/demo/load")
def load_demo_data(response: Response, db: Session = Depends(get_db)):
    """
    Loads demo evaluation dataset into an isolated ScanRun named 'Demo Evaluation Dataset'.
    Sets session cookie so evaluator can test the dashboard immediately without overlapping.
    """
    demo_email = "demo.user@polarisk.spendintel"
    
    user = db.query(UserSession).filter(UserSession.email == demo_email).first()
    if not user:
        user = UserSession(email=demo_email)
        db.add(user)
    user.last_synced_at = datetime.datetime.utcnow()
    user.total_emails_scanned = 15
    db.commit()

    # Create a distinct ScanRun
    now_str = datetime.datetime.now().strftime("%d %b, %I:%M %p")
    scan_run = ScanRun(
        user_email=demo_email,
        run_name=f"Demo Benchmark Dataset ({now_str})",
        scan_type="demo"
    )
    db.add(scan_run)
    db.commit()
    db.refresh(scan_run)

    # Load mock transactions tagged with this run
    demo_txs = get_demo_transactions(demo_email)
    for dt in demo_txs:
        tx = Transaction(
            user_email=demo_email,
            scan_run_id=scan_run.id,
            message_id=dt["message_id"],
            subject=dt["subject"],
            sender=dt["sender"],
            merchant=dt["merchant"],
            amount=dt["amount"],
            currency=dt["currency"],
            date=dt["date"],
            category=dt["category"],
            transaction_type=dt["transaction_type"],
            confidence=dt["confidence"],
            gmail_permalink=dt["gmail_permalink"],
            snippet=dt["snippet"]
        )
        db.add(tx)
    db.commit()

    # Run analysis & explanations
    flags = detect_anomalies_and_insights(demo_txs)
    for flag in flags:
        explanation = generate_explanation_for_flag(flag)
        anomaly = AnomalyFlag(
            user_email=demo_email,
            scan_run_id=scan_run.id,
            flag_type=flag["flag_type"],
            severity=flag["severity"],
            title=flag["title"],
            reason_data=flag["reason_data"],
            explanation=explanation,
            source_message_id=flag.get("source_message_id"),
            gmail_permalink=flag.get("gmail_permalink")
        )
        db.add(anomaly)

    scan_run.total_spend = sum(t["amount"] for t in demo_txs)
    scan_run.transaction_count = len(demo_txs)
    scan_run.anomaly_count = len(flags)
    db.commit()

    from auth import create_session_token
    session_token = create_session_token(demo_email)
    response.set_cookie(
        key=COOKIE_NAME,
        value=session_token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=86400 * 14
    )

    return {
        "status": "success",
        "message": "Demo data loaded into an isolated run successfully",
        "user_email": demo_email,
        "run_id": scan_run.id
    }

@app.delete("/api/purge")
def purge_user_data(request: Request, response: Response, db: Session = Depends(get_db)):
    """Permanently deletes all stored runs, transactions, and session data."""
    email = get_current_user_email(request)
    if not email:
        raise HTTPException(status_code=401, detail="Authentication required")

    user = db.query(UserSession).filter(UserSession.email == email).first()
    if user:
        db.delete(user)
        db.commit()

    response.delete_cookie(COOKIE_NAME)
    return {"status": "success", "message": "All user scan runs and transactions have been permanently purged."}
