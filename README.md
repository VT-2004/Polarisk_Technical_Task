# Gmail Spend Intelligence

> An end-to-end full-stack financial intelligence application that securely connects to a user's Gmail account (read-only), scans past inbox communications for transaction receipts/invoices/bills, extracts structured financial details with an LLM, and presents interactive spending analytics, recurring subscription tracking, and deterministic anomaly alerts with traceable Gmail source links.

---

### 🌐 Live Deployments & Links

- **🚀 Live Web Application (Vercel):** [https://frontend-vt-2004s-projects.vercel.app](https://frontend-vt-2004s-projects.vercel.app)
- **⚡ Live Backend API (Render):** [https://polarisk-technical-task.onrender.com](https://polarisk-technical-task.onrender.com)
- **📦 GitHub Repository:** [https://github.com/VT-2004/Polarisk_Technical_Task](https://github.com/VT-2004/Polarisk_Technical_Task)
- **🎥 Video Walkthrough Demo:** *[Add your Loom/Drive link here]*

---


## Architecture Overview

```
[1] OAuth Connect (Google OAuth 2.0)
     │   └── Scoped strictly to `https://www.googleapis.com/auth/gmail.readonly`
     │
[2] Gmail Fetch & Targeted Pre-filtering
     │   ├── Query: 6–12 month financial keyword filter
     │   └── Regex Pre-filter: Drops promotional spam, newsletters, and marketing noise BEFORE LLM calls (saves ~80% tokens)
     │
[3] Structured LLM Extraction (Groq LLaMA 3.3 70B / Anthropic Claude)
     │   └── Extracts: Merchant, Amount, Currency, Date, Category, Transaction Type, Confidence
     │
[4] SQLite Database Storage (SQLAlchemy Models)
     │   └── Persists structured transactions and Gmail Message IDs (no raw email bodies stored)
     │
[5] Deterministic Python Analytics Engine
     │   ├── Category & Merchant Aggregations (Top category, merchant leaders)
     │   ├── Recurring Payment Detection (Clustering by merchant + amount tolerance + monthly interval)
     │   └── Statistical Anomaly Rules (Price jumps >20%, unseen high-amount merchants >90th percentile)
     │
[6] Narrow LLM Explanation Phrasing
     │   └── Phrasing engine: Produces a 1-sentence natural language explanation of the pre-computed mathematical facts
     │
[7] Modern Next.js Dashboard
         ├── Real-time scan progress bar (Fetching -> Filtering -> Extracting -> Analyzing -> Explaining)
         ├── Summary KPI cards, Category breakdown charts & monthly spending trajectories
         ├── Active recurring subscriptions panel & Flagged anomaly insight cards
         ├── Searchable/Filterable transaction list with direct "View in Gmail" permalinks
         └── "Disconnect & Purge Data" button to completely wipe all stored records
```

---

## AI & Architectural Rationale

| System Component | Technology Used | Architectural Rationale |
| :--- | :--- | :--- |
| **Email Pre-filtering** | Deterministic Python (Regex / Keywords) | Eliminates promotional spam, coupon codes, and newsletters without spending API tokens or introducing latency. |
| **Transaction Extraction** | LLM (`llama-3.3-70b-versatile` / `Claude`) | Email receipts have wildly inconsistent layouts across banks and merchants. LLMs reliably extract structured JSON from messy HTML/text. |
| **Financial Analytics & Anomaly Detection** | Pure Deterministic Python | **Strict Separation:** Anomaly detection is rule-based and inspectable (z-scores, mathematical price jump percentages, clustering). LLMs are NOT allowed to decide what counts as an anomaly. |
| **Explanation Generation** | Narrow LLM Prompting | Converts computed facts (e.g. `current: 6899, avg_prev: 4200, jump: 64.3%`) into a crisp, human-friendly 1-sentence explanation without hallucination. |

---

## Quick Start Guide

### Prerequisites
- **Python 3.11+**
- **Node.js 18+** & **npm**
- Free **Groq API Key** (or Anthropic API Key)
- **Google Cloud OAuth 2.0 Credentials** (`gmail.readonly`)

---

### Step 1: Backend Setup

1. Open a terminal in the `backend/` folder:
   ```bash
   cd backend
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate

   pip install -r requirements.txt
   ```

2. Configure environment variables in `backend/.env`:
   ```env
   GOOGLE_CLIENT_ID="your-client-id.apps.googleusercontent.com"
   GOOGLE_CLIENT_SECRET="your-client-secret"
   GOOGLE_REDIRECT_URI="http://localhost:8000/api/auth/callback"

   LLM_PROVIDER="groq"
   GROQ_API_KEY="gsk_your_groq_api_key"
   GROQ_MODEL="llama-3.3-70b-versatile"

   SESSION_SECRET_KEY="spend-intel-secret-key"
   FRONTEND_URL="http://localhost:3000"
   DATABASE_URL="sqlite:///./spend_intel.db"
   ```

3. Run backend tests to verify logic:
   ```bash
   python -m unittest backend/tests/test_analysis.py -v
   ```

4. Start the FastAPI backend server:
   ```bash
   uvicorn main:app --reload --port 8000
   ```

---

### Step 2: Frontend Setup

1. In a separate terminal, open the `frontend/` folder:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

2. Open **`http://localhost:3000`** in your browser.

---

## Scan History & Multi-Run Isolation

Each scan you perform (whether a live inbox scan or a quick demo dataset load) generates an isolated, named **ScanRun** session:
- **No Data Overlap:** Repeated scans or test runs are kept separate without polluting prior results.
- **Run Switcher:** Switch between any past scan or benchmark run directly from the top bar on the dashboard.
- **Session Management:** Delete unwanted past runs with one click or launch a fresh scan whenever desired.


---

## Demo Mode (Instant Evaluation)

If you wish to test the application or record a demonstration video without connecting a personal Gmail account:
1. Click **"Try Demo Mode"** on the landing page (`/`).
2. The application will immediately populate a realistic dataset with Indian and international transactions:
   - **High-spend Category Leader:** ₹42,000 on Travel (MakeMyTrip)
   - **Recurring Price Jump Anomaly:** Adobe subscription jumped from ₹4,200/mo to ₹6,899/mo (+64.3%)
   - **First-Time Unseen Merchant Anomaly:** ₹35,000 to Taj Palace & Resorts (90th percentile spend)
   - **Recurring Subscriptions:** Netflix (₹649/mo), AWS Cloud Hosting (~₹3,300/mo), Airtel Fiber (₹1,178/mo)
   - **Everyday Food & Travel:** Swiggy, Uber, Amazon Shopping

---

## Security & Privacy Safeguards

- **Minimal Permissions:** Only requests `https://www.googleapis.com/auth/gmail.readonly`. Never requests modify, send, or write scopes.
- **Server-Side Token Isolation:** Google OAuth access and refresh tokens are stored in the server-side SQLite database and never exposed to client-side JavaScript.
- **Zero Raw Email Body Persistence:** Only extracted numerical amounts, categories, and Gmail Message IDs are stored. Source verification is performed by deep-linking to Gmail directly.
- **1-Click Data Purge:** The dashboard includes a "Disconnect & Purge Data" button that immediately deletes all database records and destroys the session.
