import datetime
from collections import defaultdict
from typing import List, Dict, Any, Optional
import numpy as np

def parse_iso_date(date_str: Optional[str]) -> datetime.date:
    """Safely parse YYYY-MM-DD or return today's date if missing."""
    if not date_str:
        return datetime.date.today()
    try:
        return datetime.datetime.strptime(date_str[:10], "%Y-%m-%d").date()
    except Exception:
        return datetime.date.today()

def compute_spending_summary(transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes summary totals, category breakdowns, merchant breakdowns, and monthly trends.
    """
    if not transactions:
        return {
            "total_spend": 0.0,
            "currency": "INR",
            "transaction_count": 0,
            "categories": [],
            "merchants": [],
            "monthly_trends": []
        }

    total_spend = sum(t.get("amount", 0.0) for t in transactions)
    currency = transactions[0].get("currency", "INR") if transactions else "INR"
    
    # Category totals
    cat_spend = defaultdict(float)
    cat_count = defaultdict(int)
    for t in transactions:
        cat = t.get("category", "other")
        cat_spend[cat] += t.get("amount", 0.0)
        cat_count[cat] += 1
        
    categories_list = [
        {"category": cat, "total": round(amount, 2), "count": cat_count[cat], "percentage": round((amount / total_spend * 100) if total_spend > 0 else 0, 1)}
        for cat, amount in sorted(cat_spend.items(), key=lambda x: x[1], reverse=True)
    ]

    # Merchant totals
    merchant_spend = defaultdict(float)
    merchant_count = defaultdict(int)
    for t in transactions:
        m = t.get("merchant", "Unknown")
        merchant_spend[m] += t.get("amount", 0.0)
        merchant_count[m] += 1

    merchants_list = [
        {"merchant": m, "total": round(amount, 2), "count": merchant_count[m]}
        for m, amount in sorted(merchant_spend.items(), key=lambda x: x[1], reverse=True)
    ]

    # Monthly trends
    month_spend = defaultdict(float)
    for t in transactions:
        d = parse_iso_date(t.get("date"))
        month_key = d.strftime("%Y-%m")
        month_spend[month_key] += t.get("amount", 0.0)

    monthly_trends = [
        {"month": m, "total": round(total, 2)}
        for m, total in sorted(month_spend.items())
    ]

    return {
        "total_spend": round(total_spend, 2),
        "currency": currency,
        "transaction_count": len(transactions),
        "categories": categories_list,
        "merchants": merchants_list,
        "monthly_trends": monthly_trends
    }

def detect_recurring_payments(transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Recurring payment detection:
    Clusters by merchant + amount within ~10% tolerance + roughly monthly interval (~20 to 45 days), seen 2+ times.
    """
    if not transactions:
        return []

    # Group transactions by normalized merchant
    by_merchant = defaultdict(list)
    for t in transactions:
        m = t.get("merchant", "Unknown").strip().title()
        by_merchant[m].append(t)

    recurring_subscriptions = []

    for merchant, txs in by_merchant.items():
        if len(txs) < 2:
            continue
        
        # Sort chronologically
        sorted_txs = sorted(txs, key=lambda x: parse_iso_date(x.get("date")))
        
        # Sub-cluster by amount tolerance (within 10%)
        amount_clusters = []
        for tx in sorted_txs:
            amt = tx.get("amount", 0.0)
            if amt <= 0:
                continue
            matched_cluster = None
            for cluster in amount_clusters:
                avg_cluster_amt = sum(c.get("amount", 0.0) for c in cluster) / len(cluster)
                if abs(amt - avg_cluster_amt) / avg_cluster_amt <= 0.15: # 15% tolerance
                    matched_cluster = cluster
                    break
            if matched_cluster is not None:
                matched_cluster.append(tx)
            else:
                amount_clusters.append([tx])

        # Check intervals for each cluster
        for cluster in amount_clusters:
            if len(cluster) >= 2:
                dates = [parse_iso_date(c.get("date")) for c in cluster]
                intervals = [(dates[i] - dates[i - 1]).days for i in range(1, len(dates))]
                
                # Check if average interval is monthly (20-45 days) or annual (330-390 days)
                avg_interval = sum(intervals) / len(intervals) if intervals else 0
                cadence = "monthly" if 20 <= avg_interval <= 45 else ("annual" if 330 <= avg_interval <= 390 else "recurring")
                
                latest_tx = cluster[-1]
                avg_amount = sum(c.get("amount", 0.0) for c in cluster) / len(cluster)
                
                recurring_subscriptions.append({
                    "merchant": merchant,
                    "cadence": cadence,
                    "average_amount": round(avg_amount, 2),
                    "latest_amount": round(latest_tx.get("amount", 0.0), 2),
                    "latest_date": latest_tx.get("date"),
                    "frequency_count": len(cluster),
                    "currency": latest_tx.get("currency", "INR"),
                    "category": latest_tx.get("category", "subscriptions"),
                    "latest_message_id": latest_tx.get("message_id"),
                    "gmail_permalink": latest_tx.get("gmail_permalink"),
                    "transaction_ids": [c.get("id") for c in cluster if c.get("id")]
                })

    return recurring_subscriptions

def detect_anomalies_and_insights(transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Deterministic anomaly & insight detection engine.
    Computes facts and returns structured flag objects:
    {flag_type, severity, title, merchant, amount, date, reason_data, source_message_id, gmail_permalink}
    """
    if not transactions:
        return []

    flags = []
    currency = transactions[0].get("currency", "INR") if transactions else "INR"
    sorted_txs = sorted(transactions, key=lambda x: parse_iso_date(x.get("date")))

    # 1. Category Leader (Recent Month vs Prior Month)
    today = datetime.date.today()
    this_month_key = today.strftime("%Y-%m")
    last_month_date = (today.replace(day=1) - datetime.timedelta(days=1))
    last_month_key = last_month_date.strftime("%Y-%m")

    this_month_cats = defaultdict(float)
    last_month_cats = defaultdict(float)

    for t in transactions:
        d = parse_iso_date(t.get("date"))
        m_key = d.strftime("%Y-%m")
        cat = t.get("category", "other")
        if m_key == this_month_key:
            this_month_cats[cat] += t.get("amount", 0.0)
        elif m_key == last_month_key:
            last_month_cats[cat] += t.get("amount", 0.0)

    # Fallback to all-time top category if this month is sparse
    if this_month_cats:
        top_cat, top_cat_spend = max(this_month_cats.items(), key=lambda x: x[1])
        prior_cat_spend = last_month_cats.get(top_cat, 0.0)
        change_pct = round(((top_cat_spend - prior_cat_spend) / prior_cat_spend * 100), 1) if prior_cat_spend > 0 else None
        
        flags.append({
            "flag_type": "category_leader",
            "severity": "info",
            "title": f"Highest Spend Category: {top_cat.capitalize()}",
            "merchant": None,
            "amount": round(top_cat_spend, 2),
            "date": today.isoformat(),
            "reason_data": {
                "category": top_cat,
                "current_month_spend": round(top_cat_spend, 2),
                "prior_month_spend": round(prior_cat_spend, 2),
                "percentage_change": change_pct,
                "currency": currency
            },
            "source_message_id": None,
            "gmail_permalink": None
        })

    # 2. Merchant Leader (Highest Cumulative Spend)
    merchant_spend = defaultdict(float)
    merchant_tx_sample = {}
    for t in transactions:
        m = t.get("merchant", "Unknown")
        merchant_spend[m] += t.get("amount", 0.0)
        merchant_tx_sample[m] = t

    if merchant_spend:
        top_merchant, top_spend = max(merchant_spend.items(), key=lambda x: x[1])
        flags.append({
            "flag_type": "merchant_leader",
            "severity": "info",
            "title": f"Top Merchant Spend: {top_merchant}",
            "merchant": top_merchant,
            "amount": round(top_spend, 2),
            "date": merchant_tx_sample[top_merchant].get("date"),
            "reason_data": {
                "merchant": top_merchant,
                "cumulative_spend": round(top_spend, 2),
                "transaction_count": len([t for t in transactions if t.get("merchant") == top_merchant]),
                "currency": currency
            },
            "source_message_id": merchant_tx_sample[top_merchant].get("message_id"),
            "gmail_permalink": merchant_tx_sample[top_merchant].get("gmail_permalink")
        })

    # 3. Price Jump on Recurring Payments
    # Group by merchant
    by_merchant = defaultdict(list)
    for t in transactions:
        by_merchant[t.get("merchant", "Unknown").strip().title()].append(t)

    for merchant, txs in by_merchant.items():
        if len(txs) >= 2:
            sorted_m_txs = sorted(txs, key=lambda x: parse_iso_date(x.get("date")))
            latest_tx = sorted_m_txs[-1]
            previous_txs = sorted_m_txs[:-1]
            
            avg_previous = sum(p.get("amount", 0.0) for p in previous_txs) / len(previous_txs)
            current_amt = latest_tx.get("amount", 0.0)

            # If current is > 20% higher than historical average
            if avg_previous > 0 and (current_amt - avg_previous) / avg_previous >= 0.20:
                jump_pct = round(((current_amt - avg_previous) / avg_previous) * 100, 1)
                flags.append({
                    "flag_type": "price_jump",
                    "severity": "warning",
                    "title": f"Recurring Price Jump: {merchant}",
                    "merchant": merchant,
                    "amount": round(current_amt, 2),
                    "date": latest_tx.get("date"),
                    "reason_data": {
                        "merchant": merchant,
                        "current_amount": round(current_amt, 2),
                        "avg_previous_amount": round(avg_previous, 2),
                        "jump_percentage": jump_pct,
                        "currency": currency,
                        "previous_payments_count": len(previous_txs)
                    },
                    "source_message_id": latest_tx.get("message_id"),
                    "gmail_permalink": latest_tx.get("gmail_permalink")
                })

    # 4. New / Unseen Merchant with High Amount (90th percentile threshold)
    amounts = [t.get("amount", 0.0) for t in transactions if t.get("amount", 0.0) > 0]
    p90_threshold = float(np.percentile(amounts, 90)) if len(amounts) >= 5 else 5000.0

    merchant_occurrences = defaultdict(list)
    for t in transactions:
        merchant_occurrences[t.get("merchant", "Unknown")].append(t)

    for merchant, txs in merchant_occurrences.items():
        if len(txs) == 1:
            single_tx = txs[0]
            amt = single_tx.get("amount", 0.0)
            if amt >= p90_threshold and amt > 1000.0:
                flags.append({
                    "flag_type": "unseen_high_merchant",
                    "severity": "alert",
                    "title": f"High Spend at New Merchant: {merchant}",
                    "merchant": merchant,
                    "amount": round(amt, 2),
                    "date": single_tx.get("date"),
                    "reason_data": {
                        "merchant": merchant,
                        "amount": round(amt, 2),
                        "threshold_90th_percentile": round(p90_threshold, 2),
                        "currency": currency,
                        "first_time_seen": True
                    },
                    "source_message_id": single_tx.get("message_id"),
                    "gmail_permalink": single_tx.get("gmail_permalink")
                })

    return flags
