"""
payments.py

Thin wrapper around the Razorpay SDK for event ticket payments.

Keys come from environment variables (.env):
    RAZORPAY_KEY_ID=rzp_test_xxxxxxxx
    RAZORPAY_KEY_SECRET=xxxxxxxxxxxxxxxx

If these aren't set, paid activities simply can't be checked out yet —
free (price = 0) activities are completely unaffected and keep working
via the original instant-booking flow.
"""

import os
import razorpay
from dotenv import load_dotenv

load_dotenv()

RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "").strip()
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "").strip()


def is_configured():
    return bool(RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET)


def _client():
    return razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))


def create_order(amount_rupees, receipt):
    """
    Creates a Razorpay order. Returns (order_dict, error_message).
    amount_rupees: integer/float rupee amount (converted to paise for Razorpay).
    """

    if not is_configured():
        return None, "Payments aren't configured yet. Ask admin to add Razorpay API keys."

    try:
        order = _client().order.create({
            "amount": int(round(amount_rupees * 100)),  # paise
            "currency": "INR",
            "receipt": receipt,
            "payment_capture": 1,
        })
        return order, None
    except Exception as e:
        return None, f"Could not start payment: {e}"


def verify_signature(order_id, payment_id, signature):
    """
    Returns True if the payment signature is valid, False otherwise.
    """

    if not is_configured():
        return False

    try:
        _client().utility.verify_payment_signature({
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature,
        })
        return True
    except razorpay.errors.SignatureVerificationError:
        return False
    except Exception:
        return False
