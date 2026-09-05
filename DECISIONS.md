# Architectural & Design Decisions Log

- **LLM Extraction over Regex:** Used LLM structured extraction (with JSON schema enforcement) instead of regex because bank and merchant email formats vary widely across Indian and global providers.
- **Deterministic Anomaly Engine:** Anomaly and recurring subscription detection are computed purely via deterministic Python algorithms (z-scores, tolerance clustering, price-jump delta formulas) for inspectability, zero hallucination, unit-testability, and cost control.
- **Narrow LLM Phrasing Role:** The LLM is strictly used to phrase a single human-friendly sentence for pre-computed facts; it is never permitted to make the decision of what qualifies as an anomaly.
- **Gmail Readonly Scope Only:** Enforced `https://www.googleapis.com/auth/gmail.readonly` exclusively. Never requested write, modify, or send permissions to guarantee user privacy.
- **Rule-Based Pre-filter Before LLM:** Implemented an aggressive regex/keyword pre-filter stage to discard promotional newsletters, job alerts, and marketing noise before LLM calls, cutting token usage and latency by over 80%.
- **Server-Side Token Isolation:** Google OAuth access and refresh tokens are stored exclusively in SQLite and never transmitted to client-side JavaScript. Session authentication is maintained using signed HTTP-only cookies.
- **No Raw Email Body Persistence:** Only extracted transaction metadata and Gmail Message IDs are stored in the database. Source verification is achieved via direct Gmail deep-links (`mail.google.com/mail/u/0/#inbox/{id}`).
- **Built-in Demo & Privacy Purge:** Added an instant demo mode with realistic Indian transaction samples for evaluation without live Gmail access, and a one-click data purge endpoint that permanently deletes all stored user records.
- **Isolated ScanRun Sessions & Result Switcher:** Replaced monolithic user state with an isolated `ScanRun` architecture. Every scan or demo load creates a distinct named run session. This prevents repeated scans or test benchmarks from overlapping, and allows users to seamlessly switch between and compare individual scan results in the UI.

