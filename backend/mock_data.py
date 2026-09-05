import datetime
from typing import List, Dict, Any

def get_demo_transactions(user_email: str = "demo.user@example.com") -> List[Dict[str, Any]]:
    """
    Returns high-fidelity demo transactions covering all edge cases, recurring patterns,
    and anomaly detection rules specified in the Polarisk Technical Task brief.
    """
    today = datetime.date.today()
    
    # Generate dates relative to today
    d_this_month = today.strftime("%Y-%m-10")
    d_prev_month_1 = (today - datetime.timedelta(days=30)).strftime("%Y-%m-12")
    d_prev_month_2 = (today - datetime.timedelta(days=60)).strftime("%Y-%m-11")
    d_prev_month_3 = (today - datetime.timedelta(days=90)).strftime("%Y-%m-10")

    raw_items = [
        # Travel (High spend category leader)
        {
            "message_id": "demo_msg_travel_01",
            "subject": "Booking Confirmation: Flight to Bengaluru (BLR)",
            "sender": "confirmations@makemytrip.com",
            "merchant": "MakeMyTrip",
            "amount": 42000.00,
            "currency": "INR",
            "date": d_this_month,
            "category": "travel",
            "transaction_type": "one_time",
            "confidence": "high",
            "snippet": "Thank you for booking with MakeMyTrip. Total Amount Paid: ₹42,000.00 for Round Trip BOM - BLR."
        },
        # Adobe Creative Cloud (Price jump anomaly: 4,200 -> 4,200 -> 6,899)
        {
            "message_id": "demo_msg_adobe_01",
            "subject": "Invoice for your Adobe Creative Cloud Subscription",
            "sender": "billing@adobe.com",
            "merchant": "Adobe",
            "amount": 4200.00,
            "currency": "INR",
            "date": d_prev_month_2,
            "category": "software",
            "transaction_type": "recurring",
            "confidence": "high",
            "snippet": "Adobe Systems India: Monthly Creative Cloud All Apps membership fee of ₹4,200.00 charged."
        },
        {
            "message_id": "demo_msg_adobe_02",
            "subject": "Invoice for your Adobe Creative Cloud Subscription",
            "sender": "billing@adobe.com",
            "merchant": "Adobe",
            "amount": 4200.00,
            "currency": "INR",
            "date": d_prev_month_1,
            "category": "software",
            "transaction_type": "recurring",
            "confidence": "high",
            "snippet": "Adobe Systems India: Monthly Creative Cloud All Apps membership fee of ₹4,200.00 charged."
        },
        {
            "message_id": "demo_msg_adobe_03",
            "subject": "Invoice for your Adobe Creative Cloud Subscription (Price Update)",
            "sender": "billing@adobe.com",
            "merchant": "Adobe",
            "amount": 6899.00,
            "currency": "INR",
            "date": d_this_month,
            "category": "software",
            "transaction_type": "recurring",
            "confidence": "high",
            "snippet": "Adobe Systems: Your monthly subscription renewed at revised price ₹6,899.00. Payment successful."
        },
        # Unseen High-Spend Merchant (90th percentile anomaly)
        {
            "message_id": "demo_msg_unseen_01",
            "subject": "Tax Invoice: Purchase Receipt #INV-98231",
            "sender": "payments@tajhotels.com",
            "merchant": "Taj Palace & Resorts",
            "amount": 35000.00,
            "currency": "INR",
            "date": (today - datetime.timedelta(days=5)).strftime("%Y-%m-%d"),
            "category": "travel",
            "transaction_type": "one_time",
            "confidence": "high",
            "snippet": "Payment received for Luxury Staycation Package. Total paid: ₹35,000.00 via HDFC Credit Card."
        },
        # Netflix Recurring (Monthly ₹649)
        {
            "message_id": "demo_msg_netflix_01",
            "subject": "Your Netflix receipt",
            "sender": "info@mailer.netflix.com",
            "merchant": "Netflix",
            "amount": 649.00,
            "currency": "INR",
            "date": d_prev_month_2,
            "category": "subscriptions",
            "transaction_type": "recurring",
            "confidence": "high",
            "snippet": "Your Netflix Premium membership fee of ₹649.00 was charged to your card."
        },
        {
            "message_id": "demo_msg_netflix_02",
            "subject": "Your Netflix receipt",
            "sender": "info@mailer.netflix.com",
            "merchant": "Netflix",
            "amount": 649.00,
            "currency": "INR",
            "date": d_prev_month_1,
            "category": "subscriptions",
            "transaction_type": "recurring",
            "confidence": "high",
            "snippet": "Your Netflix Premium membership fee of ₹649.00 was charged to your card."
        },
        {
            "message_id": "demo_msg_netflix_03",
            "subject": "Your Netflix receipt",
            "sender": "info@mailer.netflix.com",
            "merchant": "Netflix",
            "amount": 649.00,
            "currency": "INR",
            "date": d_this_month,
            "category": "subscriptions",
            "transaction_type": "recurring",
            "confidence": "high",
            "snippet": "Your Netflix Premium membership fee of ₹649.00 was charged to your card."
        },
        # AWS Cloud Hosting (Recurring ~₹3,200 - ₹3,450)
        {
            "message_id": "demo_msg_aws_01",
            "subject": "Amazon Web Services Invoice #847291",
            "sender": "no-reply-aws@amazon.com",
            "merchant": "AWS",
            "amount": 3280.00,
            "currency": "INR",
            "date": d_prev_month_2,
            "category": "software",
            "transaction_type": "recurring",
            "confidence": "high",
            "snippet": "AWS Billing: Amount of ₹3,280.00 has been debited for cloud infrastructure services."
        },
        {
            "message_id": "demo_msg_aws_02",
            "subject": "Amazon Web Services Invoice #859124",
            "sender": "no-reply-aws@amazon.com",
            "merchant": "AWS",
            "amount": 3450.00,
            "currency": "INR",
            "date": d_prev_month_1,
            "category": "software",
            "transaction_type": "recurring",
            "confidence": "high",
            "snippet": "AWS Billing: Amount of ₹3,450.00 has been debited for cloud infrastructure services."
        },
        # Airtel Broadband Fiber (Monthly Utilities ₹1,178)
        {
            "message_id": "demo_msg_airtel_01",
            "subject": "Airtel Xstream Fiber e-Bill for Account #982144",
            "sender": "ebill@airtel.com",
            "merchant": "Airtel Fiber",
            "amount": 1178.00,
            "currency": "INR",
            "date": d_prev_month_1,
            "category": "utilities",
            "transaction_type": "bill",
            "confidence": "high",
            "snippet": "Dear Customer, your Airtel Broadband bill of ₹1,178.00 is paid. Thank you for paying on time."
        },
        {
            "message_id": "demo_msg_airtel_02",
            "subject": "Airtel Xstream Fiber e-Bill for Account #982144",
            "sender": "ebill@airtel.com",
            "merchant": "Airtel Fiber",
            "amount": 1178.00,
            "currency": "INR",
            "date": d_this_month,
            "category": "utilities",
            "transaction_type": "bill",
            "confidence": "high",
            "snippet": "Dear Customer, your Airtel Broadband bill of ₹1,178.00 is paid. Thank you for paying on time."
        },
        # Swiggy / Food orders
        {
            "message_id": "demo_msg_swiggy_01",
            "subject": "Your Swiggy order receipt for #SW-98124",
            "sender": "receipts@swiggy.in",
            "merchant": "Swiggy",
            "amount": 489.00,
            "currency": "INR",
            "date": (today - datetime.timedelta(days=2)).strftime("%Y-%m-%d"),
            "category": "food",
            "transaction_type": "one_time",
            "confidence": "high",
            "snippet": "Order delivered from Meghana Foods. Total paid: ₹489.00 via UPI."
        },
        {
            "message_id": "demo_msg_swiggy_02",
            "subject": "Your Swiggy order receipt for #SW-97451",
            "sender": "receipts@swiggy.in",
            "merchant": "Swiggy",
            "amount": 620.00,
            "currency": "INR",
            "date": (today - datetime.timedelta(days=8)).strftime("%Y-%m-%d"),
            "category": "food",
            "transaction_type": "one_time",
            "confidence": "high",
            "snippet": "Order delivered from Truffles. Total paid: ₹620.00 via Google Pay."
        },
        # Uber rides
        {
            "message_id": "demo_msg_uber_01",
            "subject": "Your Tuesday morning trip with Uber",
            "sender": "uber.india@uber.com",
            "merchant": "Uber",
            "amount": 342.00,
            "currency": "INR",
            "date": (today - datetime.timedelta(days=4)).strftime("%Y-%m-%d"),
            "category": "travel",
            "transaction_type": "one_time",
            "confidence": "high",
            "snippet": "Total: ₹342.00. Trip to Indiranagar completed successfully."
        },
        # Amazon Shopping
        {
            "message_id": "demo_msg_amazon_01",
            "subject": "Your Amazon.in order of Logitech MX Master 3S",
            "sender": "auto-confirm@amazon.in",
            "merchant": "Amazon",
            "amount": 8499.00,
            "currency": "INR",
            "date": (today - datetime.timedelta(days=18)).strftime("%Y-%m-%d"),
            "category": "shopping",
            "transaction_type": "one_time",
            "confidence": "high",
            "snippet": "Order confirmation: Logitech Wireless Mouse. Total: ₹8,499.00."
        }
    ]

    # Populate user_email and permalinks
    transactions = []
    for item in raw_items:
        item["user_email"] = user_email
        item["gmail_permalink"] = f"https://mail.google.com/mail/u/0/#inbox/{item['message_id']}"
        transactions.append(item)

    return transactions
