import os
import sys
import unittest

# Add backend directory to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from analysis import compute_spending_summary, detect_recurring_payments, detect_anomalies_and_insights
from explain import generate_rule_based_fallback_explanation

SAMPLE_TXS = [
    # Travel
    {"id": 1, "merchant": "MakeMyTrip", "amount": 42000.0, "currency": "INR", "date": "2026-09-01", "category": "travel", "transaction_type": "one_time"},
    # Adobe Recurring Price Jump (4200 -> 4200 -> 6899)
    {"id": 2, "merchant": "Adobe", "amount": 4200.0, "currency": "INR", "date": "2026-07-10", "category": "software", "transaction_type": "recurring"},
    {"id": 3, "merchant": "Adobe", "amount": 4200.0, "currency": "INR", "date": "2026-08-10", "category": "software", "transaction_type": "recurring"},
    {"id": 4, "merchant": "Adobe", "amount": 6899.0, "currency": "INR", "date": "2026-09-10", "category": "software", "transaction_type": "recurring"},
    # High Spend New Merchant
    {"id": 5, "merchant": "Taj Hotels", "amount": 35000.0, "currency": "INR", "date": "2026-09-02", "category": "travel", "transaction_type": "one_time"},
    # Netflix Monthly
    {"id": 6, "merchant": "Netflix", "amount": 649.0, "currency": "INR", "date": "2026-07-05", "category": "subscriptions", "transaction_type": "recurring"},
    {"id": 7, "merchant": "Netflix", "amount": 649.0, "currency": "INR", "date": "2026-08-05", "category": "subscriptions", "transaction_type": "recurring"},
    {"id": 8, "merchant": "Netflix", "amount": 649.0, "currency": "INR", "date": "2026-09-05", "category": "subscriptions", "transaction_type": "recurring"},
]

class TestSpendAnalysis(unittest.TestCase):
    def test_compute_spending_summary(self):
        summary = compute_spending_summary(SAMPLE_TXS)
        self.assertEqual(summary["transaction_count"], 8)
        self.assertGreater(summary["total_spend"], 90000.0)
        self.assertGreater(len(summary["categories"]), 0)
        top_cat = summary["categories"][0]["category"]
        self.assertIn(top_cat, ["travel", "software"])

    def test_detect_recurring_payments(self):
        recurring = detect_recurring_payments(SAMPLE_TXS)
        merchants = [r["merchant"].lower() for r in recurring]
        self.assertIn("netflix", merchants)

    def test_detect_price_jump_anomaly(self):
        anomalies = detect_anomalies_and_insights(SAMPLE_TXS)
        price_jumps = [a for a in anomalies if a["flag_type"] == "price_jump"]
        self.assertGreaterEqual(len(price_jumps), 1)
        adobe_jump = price_jumps[0]
        self.assertEqual(adobe_jump["merchant"], "Adobe")
        self.assertEqual(adobe_jump["reason_data"]["current_amount"], 6899.0)
        self.assertEqual(adobe_jump["reason_data"]["avg_previous_amount"], 4200.0)
        self.assertGreater(adobe_jump["reason_data"]["jump_percentage"], 20.0)

    def test_detect_unseen_high_merchant(self):
        anomalies = detect_anomalies_and_insights(SAMPLE_TXS)
        unseen_flags = [a for a in anomalies if a["flag_type"] == "unseen_high_merchant"]
        self.assertGreaterEqual(len(unseen_flags), 1)
        merchants = [u["merchant"] for u in unseen_flags]
        self.assertTrue("Taj Hotels" in merchants or "MakeMyTrip" in merchants)

    def test_explanation_fallback(self):
        flag = {
            "flag_type": "price_jump",
            "reason_data": {
                "merchant": "Adobe",
                "current_amount": 6899.0,
                "avg_previous_amount": 4200.0,
                "jump_percentage": 64.3,
                "currency": "INR"
            }
        }
        explanation = generate_rule_based_fallback_explanation(flag)
        self.assertIn("Adobe", explanation)
        self.assertTrue("6,899" in explanation or "6899" in explanation)
        self.assertIn("64.3%", explanation)

if __name__ == "__main__":
    unittest.main()

