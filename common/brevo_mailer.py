import requests
from django.conf import settings

def brevo_send_email(*, to_email: str, subject: str, html: str, text: str = ""):
    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "accept": "application/json",
        "api-key": settings.BREVO_API_KEY,
        "content-type": "application/json",
    }
    payload = {
        "sender": {"name": settings.BREVO_SENDER_NAME, "email": settings.DEFAULT_FROM_EMAIL},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html,
        "textContent": text or " ",
    }

    res = requests.post(url, headers=headers, json=payload, timeout=15)
    res.raise_for_status()
    return res.json()
