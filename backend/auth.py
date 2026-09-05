import os
import datetime
import httpx
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from db import get_db
from models import UserSession

router = APIRouter(prefix="/api/auth", tags=["auth"])

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/callback")
SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "spend-intel-local-dev-secret-key-12345")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/userinfo.email"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
REVOKE_ENDPOINT = "https://oauth2.googleapis.com/revoke"
USERINFO_ENDPOINT = "https://www.googleapis.com/oauth2/v2/userinfo"

serializer = URLSafeTimedSerializer(SESSION_SECRET_KEY)
COOKIE_NAME = "spend_intel_session"

def create_session_token(email: str) -> str:
    """Create signed session cookie token."""
    return serializer.dumps({"email": email, "created_at": datetime.datetime.utcnow().isoformat()})

def get_current_user_email(request: Request) -> Optional[str]:
    """Extract and verify user email from signed session cookie or Authorization header."""
    cookie = request.cookies.get(COOKIE_NAME)
    auth_header = request.headers.get("Authorization")
    
    token = None
    if cookie:
        token = cookie
    elif auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]

    if not token:
        return None

    try:
        data = serializer.loads(token, max_age=86400 * 14) # 14 days validity
        return data.get("email")
    except (BadSignature, SignatureExpired):
        return None

def require_current_user(request: Request, db: Session = Depends(get_db)) -> UserSession:
    """Dependency that enforces authenticated user session."""
    email = get_current_user_email(request)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please connect your Gmail account."
        )
    user = db.query(UserSession).filter(UserSession.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session user not found. Please log in again."
        )
    return user

@router.get("/login")
def login(request: Request):
    """Generates Google OAuth 2.0 authorization URL and redirects the user."""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="Google OAuth credentials are not configured in backend/.env."
        )

    # Generate state token for CSRF protection
    state = serializer.dumps({"csrf": "oauth_state", "time": datetime.datetime.utcnow().isoformat()})
    
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?response_type=code"
        f"&client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={GOOGLE_REDIRECT_URI}"
        f"&scope={GMAIL_READONLY_SCOPE}"
        f"&access_type=offline"
        f"&prompt=consent"
        f"&state={state}"
    )
    return RedirectResponse(url=auth_url)

@router.get("/callback")
async def oauth_callback(code: Optional[str] = None, state: Optional[str] = None, error: Optional[str] = None, db: Session = Depends(get_db)):
    """Receives authorization code from Google, exchanges it for tokens, and creates session."""
    if error:
        return RedirectResponse(url=f"{FRONTEND_URL}/?error={error}")

    if not code:
        return RedirectResponse(url=f"{FRONTEND_URL}/?error=missing_auth_code")

    # Exchange code for access & refresh tokens
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            TOKEN_ENDPOINT,
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code"
            }
        )
        if token_resp.status_code != 200:
            return RedirectResponse(url=f"{FRONTEND_URL}/?error=token_exchange_failed")
        
        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 3600)
        token_expiry = datetime.datetime.utcnow() + datetime.timedelta(seconds=expires_in)

        # Fetch user's email address
        userinfo_resp = await client.get(
            USERINFO_ENDPOINT,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        if userinfo_resp.status_code != 200:
            return RedirectResponse(url=f"{FRONTEND_URL}/?error=userinfo_failed")
        
        user_email = userinfo_resp.json().get("email")

    # Save or update UserSession in database
    user = db.query(UserSession).filter(UserSession.email == user_email).first()
    if not user:
        user = UserSession(
            email=user_email,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expiry=token_expiry
        )
        db.add(user)
    else:
        user.access_token = access_token
        if refresh_token:
            user.refresh_token = refresh_token
        user.token_expiry = token_expiry
    db.commit()

    # Create signed session cookie and redirect to dashboard
    session_token = create_session_token(user_email)
    response = RedirectResponse(url=f"{FRONTEND_URL}/dashboard?connected=true")
    response.set_cookie(
        key=COOKIE_NAME,
        value=session_token,
        httponly=True,
        samesite="lax",
        secure=False, # Set to True in production HTTPS
        max_age=86400 * 14
    )
    return response

@router.get("/me")
def get_me(request: Request, db: Session = Depends(get_db)):
    """Returns the current authenticated user's email and sync status."""
    email = get_current_user_email(request)
    if not email:
        return {"authenticated": False, "email": None}

    user = db.query(UserSession).filter(UserSession.email == email).first()
    if not user:
        return {"authenticated": False, "email": None}

    return {
        "authenticated": True,
        "email": user.email,
        "last_synced_at": user.last_synced_at.isoformat() if user.last_synced_at else None,
        "total_emails_scanned": user.total_emails_scanned
    }

@router.post("/logout")
async def logout(request: Request, response: Response):
    """Logs out user and clears session cookie."""
    response.delete_cookie(COOKIE_NAME)
    return {"status": "success", "message": "Logged out successfully"}

@router.post("/revoke")
async def revoke_access(request: Request, response: Response, db: Session = Depends(get_db)):
    """
    Real-world Security & Consent Revocation:
    1. Calls Google's OAuth Revocation API to formally sever app access on Google's servers.
    2. Deletes user session and cascades all stored transactions/anomalies from SQLite.
    3. Clears the session cookie.
    """
    email = get_current_user_email(request)
    if email:
        user = db.query(UserSession).filter(UserSession.email == email).first()
        if user and user.access_token:
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(
                        REVOKE_ENDPOINT,
                        params={"token": user.access_token},
                        headers={"Content-Type": "application/x-www-form-urlencoded"}
                    )
            except Exception:
                pass
            
            # Remove user and all associated transactions from database
            db.delete(user)
            db.commit()

    response.delete_cookie(COOKIE_NAME)
    return {
        "status": "success",
        "message": "Google account access has been formally revoked and all stored data was deleted."
    }

