import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from db import Base

class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    token_expiry = Column(DateTime, nullable=True)
    last_synced_at = Column(DateTime, nullable=True)
    total_emails_scanned = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    scan_runs = relationship("ScanRun", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    anomalies = relationship("AnomalyFlag", back_populates="user", cascade="all, delete-orphan")

class ScanRun(Base):
    __tablename__ = "scan_runs"

    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, ForeignKey("user_sessions.email", ondelete="CASCADE"), index=True, nullable=False)
    run_name = Column(String, nullable=False) # e.g. "Live Inbox Scan #1", "Demo Run (Sep 5)"
    scan_type = Column(String, default="live") # live, demo
    total_spend = Column(Float, default=0.0)
    transaction_count = Column(Integer, default=0)
    anomaly_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("UserSession", back_populates="scan_runs")
    transactions = relationship("Transaction", back_populates="scan_run", cascade="all, delete-orphan")
    anomalies = relationship("AnomalyFlag", back_populates="scan_run", cascade="all, delete-orphan")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, ForeignKey("user_sessions.email", ondelete="CASCADE"), index=True, nullable=False)
    scan_run_id = Column(Integer, ForeignKey("scan_runs.id", ondelete="CASCADE"), index=True, nullable=True)
    message_id = Column(String, index=True, nullable=False)
    thread_id = Column(String, nullable=True)
    subject = Column(String, nullable=True)
    sender = Column(String, nullable=True)
    merchant = Column(String, index=True, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="INR", nullable=False)
    date = Column(String, index=True, nullable=False) # YYYY-MM-DD
    category = Column(String, index=True, nullable=False) # travel, subscriptions, shopping, food, utilities, software, entertainment, other
    transaction_type = Column(String, default="one_time") # one_time, recurring, bill, refund
    confidence = Column(String, default="high") # high, medium, low
    gmail_permalink = Column(String, nullable=True)
    snippet = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("UserSession", back_populates="transactions")
    scan_run = relationship("ScanRun", back_populates="transactions")
    anomalies = relationship("AnomalyFlag", back_populates="transaction", cascade="all, delete-orphan")

class AnomalyFlag(Base):
    __tablename__ = "anomaly_flags"

    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, ForeignKey("user_sessions.email", ondelete="CASCADE"), index=True, nullable=False)
    scan_run_id = Column(Integer, ForeignKey("scan_runs.id", ondelete="CASCADE"), index=True, nullable=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id", ondelete="CASCADE"), nullable=True)
    flag_type = Column(String, index=True, nullable=False) # category_leader, merchant_leader, recurring_detected, price_jump, unseen_high_merchant, unusual_timing
    severity = Column(String, default="info") # info, warning, alert
    title = Column(String, nullable=False)
    reason_data = Column(JSON, nullable=True)
    explanation = Column(Text, nullable=False)
    source_message_id = Column(String, nullable=True)
    gmail_permalink = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("UserSession", back_populates="anomalies")
    scan_run = relationship("ScanRun", back_populates="anomalies")
    transaction = relationship("Transaction", back_populates="anomalies")

class ScanProgress(Base):
    __tablename__ = "scan_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, unique=True, index=True, nullable=False)
    is_scanning = Column(Boolean, default=False)
    stage = Column(String, default="idle") # idle, fetching, filtering, extracting, analyzing, explaining, complete, error
    message = Column(String, default="")
    scanned_count = Column(Integer, default=0)
    total_count = Column(Integer, default=0)
    extracted_count = Column(Integer, default=0)
    error = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
